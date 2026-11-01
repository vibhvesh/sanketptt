package PKG;
import android.app.*;import android.content.Intent;import android.content.pm.ServiceInfo;import android.os.*;
/** Foreground service that keeps the CPU awake (PARTIAL_WAKE_LOCK) so the radio keeps running while the phone is locked. */
public class KeepAliveService extends Service {
  static final String CH="keepalive"; PowerManager.WakeLock wl;
  @Override public void onCreate(){super.onCreate();
    NotificationManager nm=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
    if(Build.VERSION.SDK_INT>=26)nm.createNotificationChannel(new NotificationChannel(CH,"Always on",NotificationManager.IMPORTANCE_LOW));
    Intent open=new Intent(this,MainActivity.class).setFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP);
    PendingIntent pi=PendingIntent.getActivity(this,0,open,Build.VERSION.SDK_INT>=23?PendingIntent.FLAG_IMMUTABLE:0);
    Notification.Builder nb=Build.VERSION.SDK_INT>=26?new Notification.Builder(this,CH):new Notification.Builder(this);
    Notification n=nb.setContentTitle(getApplicationInfo().loadLabel(getPackageManager())).setContentText("Running — staying on while locked")
      .setSmallIcon(getApplicationInfo().icon).setOngoing(true).setContentIntent(pi).build();
    if(Build.VERSION.SDK_INT>=29){int t=ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK;
      if(Build.VERSION.SDK_INT<34||checkSelfPermission("android.permission.RECORD_AUDIO")==0)t|=ServiceInfo.FOREGROUND_SERVICE_TYPE_MICROPHONE;
      try{startForeground(1,n,t);}catch(Exception e){startForeground(1,n,ServiceInfo.FOREGROUND_SERVICE_TYPE_MEDIA_PLAYBACK);}}
    else startForeground(1,n);
    wl=((PowerManager)getSystemService(POWER_SERVICE)).newWakeLock(PowerManager.PARTIAL_WAKE_LOCK,getPackageName()+":keepalive");
    wl.setReferenceCounted(false);wl.acquire();}
  @Override public int onStartCommand(Intent i,int f,int id){return START_STICKY;}
  @Override public void onDestroy(){try{if(wl!=null&&wl.isHeld())wl.release();}catch(Exception e){}wl=null;
    if(Build.VERSION.SDK_INT>=24)stopForeground(STOP_FOREGROUND_REMOVE);else stopForeground(true);super.onDestroy();}
  @Override public IBinder onBind(Intent i){return null;}
}
