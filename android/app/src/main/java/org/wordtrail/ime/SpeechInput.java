package org.wordtrail.ime;

import android.content.Context;
import android.content.Intent;
import android.os.Build;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.RecognitionListener;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import java.util.ArrayList;

/** One short dictation session. All calls and callbacks run on the main thread. */
final class SpeechInput {
    interface Listener {
        void ready();
        void partial(String text);
        void waiting();
        void result(String text);
        void error(int code);
    }
    private final Context context;
    private final Handler main = new Handler(Looper.getMainLooper());
    private SpeechRecognizer recognizer;
    private Listener listener;
    private int generation;
    private boolean waiting;
    private Runnable timeout;

    SpeechInput(Context context){this.context=context;}
    static boolean offlineAvailable(Context context){
        try{return Build.VERSION.SDK_INT>=31 && systemAvailable(context) && context.getSharedPreferences("settings",Context.MODE_PRIVATE).getBoolean("speech_prefer_offline",true)
            && context.getSharedPreferences("settings",Context.MODE_PRIVATE).getString("speech_provider","").isEmpty()
            && SpeechRecognizer.isOnDeviceRecognitionAvailable(context);}
        catch(RuntimeException unavailable){return false;}
    }
    static boolean systemAvailable(Context context){
        try{return SpeechServices.selected(context)!=null;}
        catch(RuntimeException unavailable){return false;}
    }
    boolean active(){return recognizer!=null;}
    void start(boolean offline,String locale,Listener callbacks){
        cancel();listener=callbacks;waiting=false;final int token=++generation;
        try{
            SpeechServices.Provider provider=offline?null:SpeechServices.selected(context);
            if(!offline && provider==null){fail(SpeechRecognizer.ERROR_CLIENT);return;}
            recognizer=offline ? SpeechRecognizer.createOnDeviceSpeechRecognizer(context) : SpeechRecognizer.createSpeechRecognizer(context,provider.component);
            recognizer.setRecognitionListener(new RecognitionListener(){
                private boolean valid(){return token==generation && recognizer!=null;}
                @Override public void onReadyForSpeech(Bundle params){if(valid() && !waiting)listener.ready();}
                @Override public void onBeginningOfSpeech(){}
                @Override public void onRmsChanged(float rms){}
                @Override public void onBufferReceived(byte[] buffer){}
                @Override public void onEndOfSpeech(){if(valid())awaitResult();}
                @Override public void onError(int code){if(valid())fail(code);}
                @Override public void onResults(Bundle results){
                    if(!valid())return;String text=first(results);Listener done=listener;cancel();
                    if(text.isEmpty())done.error(SpeechRecognizer.ERROR_NO_MATCH);else done.result(text);
                }
                @Override public void onPartialResults(Bundle results){if(valid() && !waiting){String text=first(results);if(!text.isEmpty())listener.partial(text);}}
                @Override public void onEvent(int type,Bundle params){}
            });
            Intent request=new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)
                .putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM)
                .putExtra(RecognizerIntent.EXTRA_LANGUAGE,locale)
                .putExtra(RecognizerIntent.EXTRA_PARTIAL_RESULTS,true)
                .putExtra(RecognizerIntent.EXTRA_MAX_RESULTS,1)
                .putExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE,offline);
            armTimeout(45000,SpeechRecognizer.ERROR_SPEECH_TIMEOUT);
            recognizer.startListening(request);
        }catch(RuntimeException error){fail(SpeechRecognizer.ERROR_CLIENT);}
    }
    void stop(){
        if(!active() || waiting)return;
        awaitResult();
        try{recognizer.stopListening();}catch(RuntimeException error){fail(SpeechRecognizer.ERROR_CLIENT);}
    }
    private void awaitResult(){
        if(waiting)return;waiting=true;listener.waiting();armTimeout(10000,SpeechRecognizer.ERROR_NETWORK_TIMEOUT);
    }
    private void armTimeout(int millis,int error){
        if(timeout!=null)main.removeCallbacks(timeout);final int token=generation;
        timeout=()->{if(token==generation && active())fail(error);};main.postDelayed(timeout,millis);
    }
    private void fail(int error){Listener failed=listener;cancel();if(failed!=null)failed.error(error);}
    void cancel(){
        generation++;if(timeout!=null){main.removeCallbacks(timeout);timeout=null;}
        SpeechRecognizer old=recognizer;recognizer=null;listener=null;waiting=false;
        if(old!=null){try{old.cancel();}catch(RuntimeException ignored){}try{old.destroy();}catch(RuntimeException ignored){}}
    }
    private static String first(Bundle results){
        if(results==null)return "";
        ArrayList<String> values=results.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION);
        if(values==null)return "";for(String value:values)if(value!=null && !value.trim().isEmpty())return value.trim();return "";
    }
    static String errorMessage(int code){
        switch(code){
            case 100:return "离线语音加载或识别失败，请重启词伴再试";
            case SpeechRecognizer.ERROR_INSUFFICIENT_PERMISSIONS:return "未获麦克风权限，请重新授权";
            case SpeechRecognizer.ERROR_AUDIO:return "麦克风不可用，请检查是否被其他应用占用";
            case SpeechRecognizer.ERROR_NO_MATCH:
            case SpeechRecognizer.ERROR_SPEECH_TIMEOUT:return "没有听清，请靠近麦克风再试一次";
            case SpeechRecognizer.ERROR_NETWORK:
            case SpeechRecognizer.ERROR_NETWORK_TIMEOUT:return "识别服务连接超时，请检查网络后重试";
            case SpeechRecognizer.ERROR_RECOGNIZER_BUSY:return "语音服务正忙，请稍后重试";
            case SpeechRecognizer.ERROR_LANGUAGE_NOT_SUPPORTED:return "语音服务不支持当前语言";
            case SpeechRecognizer.ERROR_LANGUAGE_UNAVAILABLE:return "当前语言的语音包尚未准备好";
            case SpeechRecognizer.ERROR_SERVER:return "系统服务返回服务器错误，请检查该服务的网络";
            case SpeechRecognizer.ERROR_SERVER_DISCONNECTED:return "系统语音服务连接已断开，请启用或更换服务";
            case SpeechRecognizer.ERROR_CLIENT:return "无法启动系统语音服务，请检查服务选择与授权";
            case SpeechRecognizer.ERROR_TOO_MANY_REQUESTS:return "系统语音调用过于频繁，请稍后重试";
            default:return "系统语音识别失败，请检查服务设置";
        }
    }
}
