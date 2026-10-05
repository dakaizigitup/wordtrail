package org.wordtrail.ime;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Bundle;
import android.provider.Settings;
import android.widget.*;

/** A visible activity is needed for Android's microphone permission dialog. */
public final class SpeechPermissionActivity extends Activity {
    private static final int REQUEST=41;
    private TextView message;
    private Button allow;
    private boolean requested;
    @Override public void onCreate(Bundle state){
        super.onCreate(state);requested=state!=null && state.getBoolean("requested");
        WordtrailStyle palette=WordtrailStyle.load(this);
        LinearLayout body=new LinearLayout(this);body.setOrientation(LinearLayout.VERTICAL);body.setPadding(dp(24),dp(20),dp(24),dp(20));body.setBackgroundColor(palette.background);
        TextView title=new TextView(this);title.setText("开启语音输入");title.setTextSize(20);title.setTextColor(palette.ink);body.addView(title);
        message=new TextView(this);message.setText("只在你点击麦克风后开始识别。识别完成或取消后即停止。词伴不保存录音。");message.setTextColor(palette.muted);message.setTextSize(14);message.setPadding(0,dp(14),0,dp(16));body.addView(message);
        allow=new Button(this);allow.setText("允许麦克风");palette.style(allow,palette.accent,palette.onAccent,12,false);allow.setOnClickListener(v->requestOrSettings());body.addView(allow);
        Button back=new Button(this);back.setText("返回键盘");palette.style(back,palette.soft,palette.accent,12,false);back.setOnClickListener(v->finish());body.addView(back);setContentView(body);
        if(checkSelfPermission(Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED)finish();
        else if(state==null)requestOrSettings();
    }
    private void requestOrSettings(){
        if(requested && !shouldShowRequestPermissionRationale(Manifest.permission.RECORD_AUDIO)){
            startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,Uri.parse("package:"+getPackageName())));return;
        }
        requested=true;requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},REQUEST);
    }
    @Override public void onRequestPermissionsResult(int code,String[] permissions,int[] grants){
        super.onRequestPermissionsResult(code,permissions,grants);if(code!=REQUEST)return;
        if(grants.length>0 && grants[0]==PackageManager.PERMISSION_GRANTED){Toast.makeText(this,"已允许，返回键盘后点麦克风开始",Toast.LENGTH_LONG).show();finish();}
        else {message.setText("尚未允许麦克风，打字功能仍可正常使用。需要语音时再授权即可。");allow.setText(shouldShowRequestPermissionRationale(Manifest.permission.RECORD_AUDIO)?"重新授权麦克风":"去设置允许麦克风");}
    }
    @Override public void onResume(){super.onResume();if(message!=null && checkSelfPermission(Manifest.permission.RECORD_AUDIO)==PackageManager.PERMISSION_GRANTED)finish();}
    @Override public void onSaveInstanceState(Bundle state){state.putBoolean("requested",requested);super.onSaveInstanceState(state);}
    private int dp(int value){return WordtrailStyle.dp(this,value);}
}
