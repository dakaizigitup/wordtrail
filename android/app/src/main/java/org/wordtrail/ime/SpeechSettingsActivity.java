package org.wordtrail.ime;

import android.app.Activity;
import android.app.AlertDialog;
import android.content.*;
import android.os.*;
import android.provider.Settings;
import android.view.*;
import android.view.inputmethod.InputMethodManager;
import android.widget.*;
import java.util.List;

/** Local settings and diagnostics; no audio, text fields or cloud credentials. */
public final class SpeechSettingsActivity extends Activity {
    private WordtrailStyle palette;
    private LinearLayout content;
    @Override public void onCreate(Bundle state){super.onCreate(state);}
    @Override public void onResume(){super.onResume();show();}
    private SharedPreferences prefs(){return getSharedPreferences("settings",MODE_PRIVATE);}
    private void show(){
        palette=WordtrailStyle.load(this);
        getWindow().setStatusBarColor(palette.background);getWindow().setNavigationBarColor(palette.background);
        ScrollView scroll=new ScrollView(this);scroll.setBackgroundColor(palette.background);scroll.setFitsSystemWindows(true);
        content=new LinearLayout(this);content.setOrientation(LinearLayout.VERTICAL);content.setPadding(dp(20),dp(24),dp(20),dp(24));scroll.addView(content);setContentView(scroll);
        text("语音输入设置",24,palette.ink);
        button("返回键盘",this::finish);
        boolean local=!prefs().getString("speech_engine","local").equals("system");
        text("默认使用随包的本机离线语音，不依赖系统服务、不需账号。录音仅在内存处理，不保存、不上传。",14,palette.muted);
        text("当前方式\n"+(local?"词伴本机离线识别（SenseVoice）":"手机系统语音服务（可能联网）"),14,palette.ink);
        button("选择语音方式",()->new AlertDialog.Builder(this).setTitle("语音识别方式").setSingleChoiceItems(new String[]{"词伴本机离线（推荐）","手机系统语音（设备需提供服务）"},local?0:1,(dialog,index)->{prefs().edit().putString("speech_engine",index==0?"local":"system").apply();dialog.dismiss();show();}).setNegativeButton("取消",null).show());
        text("本机离线支持普通话及英文，跟随键盘中/英模式。首次会准备随包模型；每次最长录音30秒，可提前点完成或取消。",12,palette.muted);
        if(!local){
        text("当前服务\n"+SpeechServices.description(this),14,palette.ink);
        boolean hasServices=!SpeechServices.available(this).isEmpty();
        if(hasServices)button("选择识别服务",this::choose);
        else text("没有发现可调用的系统语音服务。麦克风授权或切换离线优先无法补上缺失的服务。",14,palette.ink);
        Switch offline=new Switch(this);offline.setText("优先设备离线识别");offline.setTextColor(palette.ink);offline.setChecked(prefs().getBoolean("speech_prefer_offline",true));
        offline.setOnCheckedChangeListener((view,checked)->prefs().edit().putBoolean("speech_prefer_offline",checked).apply());add(offline);
        offline.setEnabled(hasServices || SpeechInput.offlineAvailable(this));
        text(hasServices?"选择具体服务后直接使用该服务。关闭离线优先，可避免缺少语言包时先尝试离线。":"这台设备的系统路径不可用，请选择词伴本机离线识别。",12,palette.muted);
        if(hasServices)button("打开手机语音设置",()->openSettings(Settings.ACTION_VOICE_INPUT_SETTINGS));
        }
        button("查看词伴麦克风权限",()->{try{startActivity(new Intent(Settings.ACTION_APPLICATION_DETAILS_SETTINGS,android.net.Uri.parse("package:"+getPackageName())));}catch(ActivityNotFoundException unavailable){Toast.makeText(this,"请到手机设置中查看词伴应用权限",Toast.LENGTH_LONG).show();}});
        button("切换输入法使用语音",()->((InputMethodManager)getSystemService(INPUT_METHOD_SERVICE)).showInputMethodPicker());
        text("诊断信息",17,palette.ink);
        TextView info=text(diagnostics(),12,palette.muted);info.setTextIsSelectable(true);
        button("复制诊断信息",()->{((ClipboardManager)getSystemService(CLIPBOARD_SERVICE)).setPrimaryClip(ClipData.newPlainText("词伴语音诊断",diagnostics()));Toast.makeText(this,"已复制，不含输入内容或录音",Toast.LENGTH_SHORT).show();});
        button("返回",this::finish);
    }
    private void choose(){
        List<SpeechServices.Provider> providers=SpeechServices.available(this);
        String[] names=new String[providers.size()+1];names[0]="跟随系统（默认失效且只有一个服务时自动选择）";
        String chosen=prefs().getString("speech_provider","");int selected=chosen.isEmpty()?0:-1;
        for(int i=0;i<providers.size();i++){
            SpeechServices.Provider provider=providers.get(i);names[i+1]=provider.label+"\n"+provider.component.getPackageName();
            if(chosen.equals(provider.component.flattenToString()))selected=i+1;
        }
        new AlertDialog.Builder(this).setTitle("选择识别服务").setSingleChoiceItems(names,selected,(dialog,index)->{
            prefs().edit().putString("speech_provider",index==0?"":providers.get(index-1).component.flattenToString()).apply();dialog.dismiss();show();
        }).setNegativeButton("取消",null).show();
    }
    private String diagnostics(){
        StringBuilder report=new StringBuilder("Wordtrail 0.1.18\n设备：").append(Build.MANUFACTURER).append(" / ").append(Build.MODEL)
            .append("\nAndroid：").append(Build.VERSION.RELEASE).append(" (API ").append(Build.VERSION.SDK_INT).append(")\n麦克风权限：")
            .append(checkSelfPermission(android.Manifest.permission.RECORD_AUDIO)==android.content.pm.PackageManager.PERMISSION_GRANTED?"已授权":"未授权")
            .append("\n离线优先：").append(prefs().getBoolean("speech_prefer_offline",true))
            .append("\n语音方式：").append(prefs().getString("speech_engine","local")).append("\n本机模型：SenseVoice int8 20240717")
            .append("\n系统默认：").append(SpeechServices.defaultComponent(this)).append("\n所选服务：").append(SpeechServices.description(this))
            .append("\n上次错误：").append(prefs().getString("speech_last_error","尚无记录")).append("\n公开服务列表：");
        List<SpeechServices.Provider> providers=SpeechServices.available(this);
        if(providers.isEmpty())report.append("无");
        for(SpeechServices.Provider provider:providers)report.append("\n").append(provider.label).append(" · ").append(provider.component.flattenToShortString());
        return report.toString();
    }
    private void openSettings(String action){try{startActivity(new Intent(action));}catch(ActivityNotFoundException unavailable){try{startActivity(new Intent(Settings.ACTION_SETTINGS));}catch(ActivityNotFoundException missing){Toast.makeText(this,"请到手机设置中搜索语音输入",Toast.LENGTH_LONG).show();}}}
    private int dp(int value){return WordtrailStyle.dp(this,value);}
    private void add(View view){LinearLayout.LayoutParams params=new LinearLayout.LayoutParams(-1,-2);params.topMargin=dp(14);content.addView(view,params);}
    private TextView text(String value,int size,int color){TextView view=new TextView(this);view.setText(value);view.setTextSize(size);view.setTextColor(color);view.setLineSpacing(dp(3),1);add(view);return view;}
    private void button(String label,Runnable action){Button button=new Button(this);button.setText(label);button.setTextSize(13);palette.style(button,palette.soft,palette.accent,12,false);button.setMinHeight(dp(44));button.setOnClickListener(view->action.run());add(button);}
}
