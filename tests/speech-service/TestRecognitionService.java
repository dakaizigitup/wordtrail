package org.wordtrail.speechtest;

import android.content.Intent;
import android.content.SharedPreferences;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.speech.*;
import java.util.ArrayList;
import java.util.Arrays;

/** Synthetic callbacks through the actual Android RecognitionService binder. */
public final class TestRecognitionService extends RecognitionService {
    private final Handler main=new Handler(Looper.getMainLooper());
    private Callback current;
    private String scenario, locale;
    private SharedPreferences prefs(){return getSharedPreferences("speech-test",MODE_PRIVATE);}
    @Override protected void onStartListening(Intent request,Callback callback){
        current=callback;scenario=prefs().getString("scenario","success");locale=request.getStringExtra(RecognizerIntent.EXTRA_LANGUAGE);
        // The synthetic service does not open AudioRecord. Still establish the
        // caller attribution context expected by Android 12+ RecognitionService.
        if(android.os.Build.VERSION.SDK_INT>=31)createContext(new android.content.ContextParams.Builder().setNextAttributionSource(callback.getCallingAttributionSource()).build());
        prefs().edit().putString("locale",locale).putBoolean("prefer_offline",request.getBooleanExtra(RecognizerIntent.EXTRA_PREFER_OFFLINE,false)).putInt("starts",prefs().getInt("starts",0)+1).commit();
        try{callback.readyForSpeech(new Bundle());}catch(Exception ignored){}
        final String kind=scenario;
        main.postDelayed(()->{try{
            if(kind.equals("network"))callback.error(SpeechRecognizer.ERROR_NETWORK);
            else if(kind.equals("server"))callback.error(SpeechRecognizer.ERROR_SERVER);
            else if(kind.equals("client"))callback.error(SpeechRecognizer.ERROR_CLIENT);
            else if(kind.equals("disconnected"))callback.error(SpeechRecognizer.ERROR_SERVER_DISCONNECTED);
            else if(kind.equals("no-match"))callback.error(SpeechRecognizer.ERROR_NO_MATCH);
            else if(kind.equals("language"))callback.error(SpeechRecognizer.ERROR_LANGUAGE_UNAVAILABLE);
            else callback.partialResults(result("临时识别内容"));
        }catch(Exception ignored){}},400);
    }
    @Override protected void onStopListening(Callback callback){
        prefs().edit().putInt("stops",prefs().getInt("stops",0)+1).commit();
        final String text="en-US".equals(locale)?"Hello from voice input.":"你好，这是语音输入。";final String kind=scenario;
        try{callback.endOfSpeech();}catch(Exception ignored){}
        if(kind.equals("timeout"))return;
        main.postDelayed(()->{try{callback.results(result(text));if(kind.equals("double"))callback.results(result(text));}catch(Exception ignored){}},500);
    }
    @Override protected void onCancel(Callback callback){
        prefs().edit().putInt("cancels",prefs().getInt("cancels",0)+1).commit();
        if("late".equals(scenario))main.postDelayed(()->{try{callback.results(result("不应被输入的迟到结果"));}catch(Exception ignored){}},800);
        current=null;
    }
    private static Bundle result(String text){Bundle bundle=new Bundle();bundle.putStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION,new ArrayList<>(Arrays.asList(text)));return bundle;}
}
