package PKG;
import android.app.Activity;import android.app.DownloadManager;import android.content.*;import android.content.pm.PackageManager;import android.net.Uri;import android.os.*;import android.view.WindowManager;import android.webkit.*;
public class MainActivity extends Activity {
  static final String URL="APPURL"; WebView w; ValueCallback<Uri[]> fc;
  @Override protected void onCreate(Bundle b){super.onCreate(b);
    getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
    if(Build.VERSION.SDK_INT>=23) requestPermissions(new String[]{"android.permission.RECORD_AUDIO","android.permission.ACCESS_FINE_LOCATION","android.permission.ACCESS_COARSE_LOCATION"},1);
    w=new WebView(this);setContentView(w);WebSettings s=w.getSettings();
    s.setJavaScriptEnabled(true);s.setDomStorageEnabled(true);s.setDatabaseEnabled(true);s.setMediaPlaybackRequiresUserGesture(false);s.setGeolocationEnabled(true);s.setAllowFileAccess(true);
    w.setWebViewClient(new WebViewClient(){public boolean shouldOverrideUrlLoading(WebView v,WebResourceRequest r){String u=r.getUrl().toString();if(u.startsWith("http"))return false;try{startActivity(new Intent(Intent.ACTION_VIEW,r.getUrl()));}catch(Exception e){}return true;}});
    w.setWebChromeClient(new WebChromeClient(){
      public void onPermissionRequest(PermissionRequest r){r.grant(r.getResources());}
      public void onGeolocationPermissionsShowPrompt(String o,GeolocationPermissions.Callback c){c.invoke(o,true,false);}
      public boolean onShowFileChooser(WebView v,ValueCallback<Uri[]> cb,FileChooserParams p){if(fc!=null)fc.onReceiveValue(null);fc=cb;try{startActivityForResult(p.createIntent(),2);}catch(Exception e){fc=null;return false;}return true;}});
    w.setDownloadListener((u,ua,cd,mt,len)->{try{if(u.startsWith("blob:")||u.startsWith("data:")){startActivity(new Intent(Intent.ACTION_VIEW,Uri.parse(u)));return;}DownloadManager.Request q=new DownloadManager.Request(Uri.parse(u));q.setMimeType(mt);q.addRequestHeader("User-Agent",ua);q.setNotificationVisibility(DownloadManager.Request.VISIBILITY_VISIBLE_NOTIFY_COMPLETED);q.setDestinationInExternalPublicDir(Environment.DIRECTORY_DOWNLOADS,URLUtil.guessFileName(u,cd,mt));((DownloadManager)getSystemService(DOWNLOAD_SERVICE)).enqueue(q);}catch(Exception e){}});
    if(b!=null)w.restoreState(b);else w.loadUrl(URL);}
  @Override protected void onActivityResult(int rq,int rc,Intent d){if(rq==2&&fc!=null){fc.onReceiveValue(WebChromeClient.FileChooserParams.parseResult(rc,d));fc=null;}}
  @Override protected void onSaveInstanceState(Bundle b){super.onSaveInstanceState(b);w.saveState(b);}
  @Override public void onBackPressed(){if(w.canGoBack())w.goBack();else super.onBackPressed();}
}
