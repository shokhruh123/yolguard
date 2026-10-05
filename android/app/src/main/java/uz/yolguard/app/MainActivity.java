package uz.yolguard.app;

import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import androidx.core.content.ContextCompat;
import androidx.core.content.FileProvider;
import java.io.File;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.Locale;

/** WebView shell: local mobile UI (assets/www) talks to backend API over LAN. */
public class MainActivity extends Activity {
    private WebView web;
    private ValueCallback<Uri[]> fileCb;
    private Uri cameraUri; // full-size photo target for EXTRA_OUTPUT
    private static final int REQ_FILE = 1001;
    private static final int REQ_CAM_PERM = 1002;

    @Override
    protected void onCreate(Bundle b) {
        super.onCreate(b);
        web = new WebView(this);
        setContentView(web);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(true); // required for file:///android_asset/www
        s.setAllowContentAccess(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView v, WebResourceRequest req) {
                String url = req.getUrl().toString();
                // keep the local app inside; open remote links in the system browser
                if (url.startsWith("file:///android_asset/")) return false;
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, req.getUrl()));
                } catch (Exception e) {
                    v.loadUrl(url);
                }
                return true;
            }
        });
        web.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(WebView v, ValueCallback<Uri[]> cb,
                                             FileChooserParams p) {
                if (fileCb != null) fileCb.onReceiveValue(null);
                fileCb = cb;
                if (ContextCompat.checkSelfPermission(MainActivity.this,
                        android.Manifest.permission.CAMERA)
                        != PackageManager.PERMISSION_GRANTED) {
                    requestPermissions(
                            new String[]{android.Manifest.permission.CAMERA}, REQ_CAM_PERM);
                    return true; // result continues in onRequestPermissionsResult
                }
                launchPicker();
                return true;
            }
        });
        if (b != null) web.restoreState(b);
        else web.loadUrl("file:///android_asset/www/index.html");
    }

    private void launchPicker() {
        Intent cam = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
        // full-size photo via FileProvider (without EXTRA_OUTPUT most devices
        // return only a thumbnail or null in data)
        try {
            File photo = createImageFile();
            cameraUri = FileProvider.getUriForFile(this,
                    getPackageName() + ".fileprovider", photo);
            cam.putExtra(MediaStore.EXTRA_OUTPUT, cameraUri);
            cam.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION);
        } catch (IOException e) {
            cameraUri = null;
        }
        Intent pick = new Intent(Intent.ACTION_GET_CONTENT);
        pick.addCategory(Intent.CATEGORY_OPENABLE);
        pick.setType("image/*");
        Intent ch = Intent.createChooser(pick, "Фото");
        ch.putExtra(Intent.EXTRA_INITIAL_INTENTS, new Intent[]{cam});
        startActivityForResult(ch, REQ_FILE);
    }

    private File createImageFile() throws IOException {
        String ts = new SimpleDateFormat("yyyyMMdd_HHmmss", Locale.US).format(new Date());
        File dir = getExternalFilesDir(Environment.DIRECTORY_PICTURES);
        if (dir == null) dir = getCacheDir();
        return File.createTempFile("yolguard_" + ts + "_", ".jpg", dir);
    }

    @Override
    public void onRequestPermissionsResult(int req, String[] perms, int[] grants) {
        super.onRequestPermissionsResult(req, perms, grants);
        if (req == REQ_CAM_PERM) launchPicker(); // with or without: picker still offers gallery
    }

    @Override
    protected void onActivityResult(int req, int res, Intent data) {
        super.onActivityResult(req, res, data);
        if (req != REQ_FILE || fileCb == null) return;
        Uri[] out = null;
        if (res == RESULT_OK) {
            if (data != null && data.getData() != null) {
                out = new Uri[]{data.getData()}; // gallery pick
            } else if (cameraUri != null) {
                out = new Uri[]{cameraUri}; // camera capture via EXTRA_OUTPUT
            }
        }
        fileCb.onReceiveValue(out);
        fileCb = null;
        cameraUri = null;
    }

    @Override
    protected void onSaveInstanceState(Bundle b) {
        super.onSaveInstanceState(b);
        web.saveState(b);
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) web.goBack();
        else super.onBackPressed();
    }
}
