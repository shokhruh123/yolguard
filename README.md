# Yo'l Guard — AI Accident Resolution (MVP)

## 1. Что это
Смартфон-ассистент при мелком ДТП: регистрация → фото с камеры → авто-анализ ИИ (Gemini: текст + схема) → ответ сотрудника в приложение. Метрика: время до освобождения полосы.

**Флоу:** сфоткал → ИИ анализирует сам (без кнопок) → видишь схему, довод, фото → сотрудник жмёт 1 из 2 кнопок («Зарегистрировано, агенты едут» / «Агенты едут, ждите») → текст приходит тебе. Твои кнопки «Понял, жду» / «Нужна помощь» уходят сотруднику.

**Готовые файлы:** `YolGuard-v1.2-release.apk` (Android, подписан release-ключом), `admin/dist/YolGuardAdmin.exe` (панель сотрудника, с фото-превью), `frontend/` (веб+мобильная вёрстка + веб-админка).
**Проверено:** pytest 23/23 (E2E флоу + 13 security-тестов), release-APK v1.2 подписан и проверен `apksigner`, EXE пересобран (с Pillow), `node --check` по JS чист, реальный Gemini-vision разбор фото проверен вручную.
**Gemini:** ключ в `backend/.env`. Разбор ДТП по фото работает (см. ниже). Без ключа — эвристика с пометкой.

## Разбор ИИ по фото (чинено 2026-10-01)
Модель `gemini-2.5-flash` была снята с публикации (ответ 404) — поэтому ИИ молча падал в эвристику. Теперь `services/ai.py` перебирает цепочку моделей **`gemini-flash-latest → gemini-flash-lite-latest → gemini-3-flash-preview`**: первая ответившая выигрывает, при 404/503/429 берётся следующая. Авторизация — `?key=` (не Bearer). Промпт просит обширный разбор: какие ТС, по какой части пришёлся удар, вероятный сценарий, сила повреждений — с оговоркой «предположительно». Число пострадавших ИИ **не выдумывает** (берёт из triage). Схема (SVG) и текст — черновик.
Переопределить модель: `GEMINI_MODEL=...` в `.env`. В тестах реальный вызов отключён (`tests/conftest.py`), чтобы суд был быстрым и оффлайн.

## Админ-панель сотрудника (web + EXE)
Сотрудник в досье видит: **фото-превью внутри** (не ссылки; web — `<img ?token=>`, EXE — через Pillow), **схему ИИ** (web — встроенный SVG, EXE — кнопка «Открыть схему ИИ» в браузере), данные водителя (пострадавшие, часть удара, комментарий), **текст-разбор ИИ**, переписку и **2 кнопки**: «✅ Регистрация завершена» (approved) и «🚓 Выезжаем для проверки» (needs_field). Новые поля triage (`impact_part`, `driver_comment`, `injured_count`) водитель вводит на шаге проверки.

## Что изменилось — итерация 2, блок P0 (безопасность и баги)
1. **`/uploads/` закрыт.** Публичная статика убрана. Фото отдаются только через `GET /api/v1/incidents/{iid}/evidence/{eid}/file` по JWT и только участникам инцидента + specialist/admin. Чужая ссылка → **403**, без токена → **401**. Токен принимается в заголовке `Authorization` или в `?token=` (для тегов `<img>`).
2. **Валидация загрузок.** Только JPEG/PNG/WEBP по **magic bytes** (не по имени/Content-Type), лимит **10 МБ**, серверный ресайз до **1600px**, EXIF-GPS сохраняется в БД (`evidence.gps_lat/gps_lon`). Битый файл с JPEG-магией → 400.
3. **CORS и SECRET_KEY.** CORS — явный список origins из `.env` (`CORS_ORIGINS`), без `*`. `SECRET_KEY` обязателен (≥32 символов, не плейсхолдер) — при дефолтном backend **не стартует** (fail-fast в `config.py`).
4. **APK release.** Подпись через `keystore.properties` (git-ignored), иконка-щит (янтарь на off-black) во всех mipmap-плотностях, `versionCode 1→2`, `versionName 1.1`.
5. **Тесты.** `tests/test_security.py` — отдельный тест на каждый фикс (чужое фото, тип файла, размер, CORS, SECRET_KEY).

## 2. Архитектура (modular monolith)
`FastAPI /api/v1` + `routers/{auth,incidents,misc,admin}`, `services/{rules,ai}`. APK = WebView-обёртка над `frontend/` + тот же API. EXE = tkinter-клиент к тому же API.

## 2. Архитектура (modular monolith)
`FastAPI /api/v1` + модули `routers/`, `services/rules.py`, SQLAlchemy. Почему монолит: MVP, одна команда, нет нужды в orchestration. Каждый модуль с четкой границей; CV/parts/repair — отдельные будущие модули.

## 3. ER (текст)
users 1:N vehicles, users 1:N incidents(creator), incidents 1:N participants/evidence, incidents 1:1 diagrams/claim_packages/review_cases. 3NF: факты разделены, транзитивных зависимостей нет.

## 4. Запуск
```powershell
cd C:\Users\WnlyPC\Downloads\yolguard\backend
py -m uvicorn app.main:app --port 8002
python -m pytest -q
```
- Веб: открыть `../frontend/index.html`, API=`http://127.0.0.1:8002/api/v1`
- APK: скинуть `YolGuard-v1.0-debug.apk` на телефон, установить; в приложении (Гараж → Сервер API) указать `http://IP-ПК:8002/api/v1` (телефон и ПК в одном Wi-Fi). Backend должен быть запущен на ПК.
- EXE: запустить `admin/dist/YolGuardAdmin.exe`, API=`http://127.0.0.1:8002/api/v1`, войти специалистом.
- Пересборка APK (release, подписанный):
  ```powershell
  cd android
  # 1) один раз — создать keystore (пароль сохранить в менеджере паролей!):
  keytool -genkeypair -v -keystore yolguard-release.jks -alias yolguard -keyalg RSA -keysize 2048 -validity 10000 -dname "CN=Yol Guard, O=Yol Guard, C=UZ"
  # 2) прописать пароли в android/keystore.properties (storeFile/storePassword/keyAlias/keyPassword), файл НЕ коммитить
  # 3) сборка (Gradle 8.10 + AGP 8.5.2 требуют JDK 17–21; системный JDK 25 не подходит):
  ..\android-sdk\gradle-8.10\bin\gradle :app:assembleRelease --no-daemon
  ```
  Путь к JDK задан в `android/gradle.properties` (`org.gradle.java.home`). Выход: `app/build/outputs/apk/release/app-release.apk`.
- Пересборка EXE: `cd admin` + `py -3 -m PyInstaller YolGuardAdmin.spec --noconfirm`.

## 5. API /api/v1
- POST /auth/register {phone,password,full_name} → 201 {user,access,refresh} | 409
- POST /auth/login → {user,access,refresh} | 401
- POST /auth/refresh → {access}
- POST /vehicles (Bearer) → 201 | 409
- POST /incidents → {id,code}
- POST /incidents/{id}/join?code= → side B | 404/409
- POST /incidents/{id}/triage (TriageIn) → {eligibility green|yellow|red, reason}
- POST /incidents/{id}/evidence {kind,file_path} → {sha256, completeness%}
- POST /incidents/{id}/evidence-upload (Bearer, multipart: kind+file) → валидирует JPEG/PNG/WEBP ≤10 МБ, ресайз 1600px, EXIF-GPS→БД → {evidence_id, url, gps, completeness, ai}
- GET /incidents/{id}/evidence/{eid}/file (Bearer или ?token=) → фото; 401 без токена, 403 чужому
- POST /incidents/{id}/diagram → {svg + disclaimer}
- POST /incidents/{id}/confirm → {confirmed}
- POST /incidents/{id}/claim-package (specialist) → {package_hash} | 400 если нет подтверждений
- GET /reviews/queue, POST /reviews/{id} (specialist)

## 6. Security
## 6. Security
PBKDF2-HMAC-SHA256 (200k итераций) для паролей, JWT с exp + Bearer, RBAC (driver/specialist/admin/insurer), Pydantic-валидация, параметризованные запросы SQLAlchemy (no SQLi), секреты в `.env`, sha256-цепочка evidence→claim.
**P0-ужесточение:** фото за JWT (403 чужим), валидация загрузок по magic bytes + лимит 10 МБ + ресайз, CORS по белому списку (без `*`), fail-fast при слабом `SECRET_KEY`, release-подпись APK через git-ignored keystore. Rate-limit — на reverse proxy (todo prod).

## 7. Структура
```
yolguard/backend/app/{main,config,db,models,schemas,security,routers/{auth,incidents,misc,deps},services/rules}.py
yolguard/backend/{seed.py,requirements.txt,.env.example,tests/}
yolguard/frontend/{index.html,app.js,styles.css}
yolguard/postman/*.json
```
