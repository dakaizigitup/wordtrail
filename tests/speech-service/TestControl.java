package org.wordtrail.speechtest;

import android.content.*;
import org.json.JSONObject;

/** Only shipped in the separate emulator test APK, never in Wordtrail. */
public final class TestControl extends BroadcastReceiver {
    @Override public void onReceive(Context context,Intent request){
        SharedPreferences prefs=context.getSharedPreferences("speech-test",Context.MODE_PRIVATE);
        if(request.hasExtra("scenario"))prefs.edit().clear().putString("scenario",request.getStringExtra("scenario")).commit();
        if(request.hasExtra("service_enabled"))context.getPackageManager().setComponentEnabledSetting(new ComponentName(context,TestRecognitionService.class),request.getBooleanExtra("service_enabled",false)?android.content.pm.PackageManager.COMPONENT_ENABLED_STATE_ENABLED:android.content.pm.PackageManager.COMPONENT_ENABLED_STATE_DISABLED,android.content.pm.PackageManager.DONT_KILL_APP);
        setResultCode(0);setResultData(new JSONObject(prefs.getAll()).toString());
    }
}
