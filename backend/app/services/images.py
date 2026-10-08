"""Image upload hardening: type allow-list via magic bytes, size cap, server-side
resize, and EXIF GPS extraction. Keeps untrusted uploads from becoming a hazard."""
from __future__ import annotations
import io
from typing import Optional
from PIL import Image, ExifTags

MAX_BYTES = 10 * 1024 * 1024          # 10 MB hard cap (photo/audio)
MAX_VIDEO_BYTES = 50 * 1024 * 1024    # 50 MB for short scene clips
MAX_DIM = 1600                        # longest side after resize
# content-type returned to clients, keyed by the format Pillow reports
_FMT_TO_MIME = {"JPEG": "image/jpeg", "PNG": "image/png", "WEBP": "image/webp"}
_FMT_TO_EXT = {"JPEG": ".jpg", "PNG": ".png", "WEBP": ".webp"}
# container magic -> (mime, ext) for video/audio (stored as-is, metadata only)
def _sniff_media(data: bytes) -> Optional[tuple[str, str]]:
    """Return (mime, ext) for supported video/audio containers, else None."""
    if len(data) < 12:
        return None
    # mp4/mov: ....ftyp
    if data[4:8] == b"ftyp" and data[8:12] in (b"isom", b"mp41", b"mp42", b"M4V ", b"qt  "):
        return ("video/mp4", ".mp4")
    # webm/mkv: EBML header
    if data[:4] == b"\x1a\x45\xdf\xa3":
        return ("video/webm", ".webm")
    if data[:3] == b"ID3" or (len(data) > 2 and data[:2] == b"\xff\xfb"):
        return ("audio/mpeg", ".mp3")
    if data[:4] == b"OggS":
        return ("audio/ogg", ".ogg")
    if data[:4] == b"RIFF" and data[8:12] == b"WAVE":
        return ("audio/wav", ".wav")
    if data[:4] == b"fLaC":
        return ("audio/flac", ".flac")
    return None


def process_media(data: bytes) -> dict:
    """Validate + store a video/audio upload without transcoding.

    Returns {"bytes", "mime", "ext", "gps_lat", "gps_lon"} (gps always None).
    Raises UploadError on empty/oversized/unsupported input.
    """
    if not data:
        raise UploadError("Пустой файл")
    if len(data) > MAX_VIDEO_BYTES:
        raise UploadError("Файл больше 50 МБ")
    found = _sniff_media(data)
    if found is None:
        raise UploadError("Только MP4/WEBM видео или MP3/OGG/WAV/FLAC аудио")
    mime, ext = found
    if mime.startswith("audio") and len(data) > MAX_BYTES:
        raise UploadError("Аудио больше 10 МБ")
    return {"bytes": data, "mime": mime, "ext": ext,
            "gps_lat": None, "gps_lon": None}

# EXIF tag ids (resolved once) for GPS lookup
_GPSINFO_TAG = next((k for k, v in ExifTags.TAGS.items() if v == "GPSInfo"), 34853)


class UploadError(ValueError):
    """Raised when an upload fails validation (maps to HTTP 400)."""


def _sniff_format(data: bytes) -> Optional[str]:
    """Return 'JPEG'|'PNG'|'WEBP' from magic bytes, else None. Does not trust
    the client-supplied filename or Content-Type."""
    if len(data) < 12:
        return None
    if data[:3] == b"\xff\xd8\xff":
        return "JPEG"
    if data[:8] == b"\x89PNG\r\n\x1a\n":
        return "PNG"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "WEBP"
    return None


def _dms_to_deg(dms, ref) -> Optional[float]:
    try:
        d, m, s = (float(x) for x in dms)
        deg = d + m / 60.0 + s / 3600.0
        if str(ref).upper() in ("S", "W"):
            deg = -deg
        return round(deg, 6)
    except Exception:
        return None


def _extract_gps(img: Image.Image) -> tuple[Optional[float], Optional[float]]:
    try:
        exif = img.getexif()
        gps = exif.get_ifd(_GPSINFO_TAG) if exif else None
        if not gps:
            return None, None
        g = {ExifTags.GPSTAGS.get(k, k): v for k, v in gps.items()}
        lat = _dms_to_deg(g.get("GPSLatitude"), g.get("GPSLatitudeRef", "N"))
        lon = _dms_to_deg(g.get("GPSLongitude"), g.get("GPSLongitudeRef", "E"))
        return lat, lon
    except Exception:
        return None, None


def process_upload(data: bytes) -> dict:
    """Validate + normalize an uploaded image.

    Returns {"bytes", "mime", "ext", "gps_lat", "gps_lon"}.
    Raises UploadError on empty/oversized/unsupported/corrupt input.
    """
    if not data:
        raise UploadError("Пустой файл")
    if len(data) > MAX_BYTES:
        raise UploadError("Файл больше 10 МБ")
    fmt = _sniff_format(data)
    if fmt is None:
        raise UploadError("Только JPEG, PNG или WEBP")
    try:
        img = Image.open(io.BytesIO(data))
        img.load()
    except Exception:
        raise UploadError("Файл не является корректным изображением")
    if img.format not in _FMT_TO_MIME:
        raise UploadError("Только JPEG, PNG или WEBP")

    gps_lat, gps_lon = _extract_gps(img)

    # resize longest side down to MAX_DIM (never upscale)
    if max(img.size) > MAX_DIM:
        img.thumbnail((MAX_DIM, MAX_DIM), Image.LANCZOS)

    out_fmt = img.format
    buf = io.BytesIO()
    save_img = img
    if out_fmt == "JPEG" and img.mode not in ("RGB", "L"):
        save_img = img.convert("RGB")
    # re-encode (this also strips EXIF; GPS is already captured in the DB)
    if out_fmt == "JPEG":
        save_img.save(buf, format="JPEG", quality=85, optimize=True)
    elif out_fmt == "PNG":
        save_img.save(buf, format="PNG", optimize=True)
    else:
        save_img.save(buf, format="WEBP", quality=85)

    return {
        "bytes": buf.getvalue(),
        "mime": _FMT_TO_MIME[out_fmt],
        "ext": _FMT_TO_EXT[out_fmt],
        "gps_lat": gps_lat,
        "gps_lon": gps_lon,
    }
