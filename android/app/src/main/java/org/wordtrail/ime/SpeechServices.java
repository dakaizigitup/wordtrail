package org.wordtrail.ime;

import android.content.*;
import android.content.pm.*;
import android.provider.Settings;
import android.speech.RecognitionService;
import java.util.*;

/** Discover public recognizers, and never bind a stale or private component. */
final class SpeechServices {
    static final class Provider {
        final ComponentName component;
        final String label;
        Provider(ComponentName component,String label){this.component=component;this.label=label;}
    }
    static List<Provider> available(Context context){
        List<Provider> values=new ArrayList<>();
        for(ResolveInfo resolved:context.getPackageManager().queryIntentServices(new Intent(RecognitionService.SERVICE_INTERFACE),0)){
            ServiceInfo service=resolved.serviceInfo;
            if(service==null || !service.exported || !service.enabled || !service.applicationInfo.enabled
                || !"android.permission.BIND_SPEECH_RECOGNITION_SERVICE".equals(service.permission))continue;
            values.add(new Provider(new ComponentName(service.packageName,service.name),resolved.loadLabel(context.getPackageManager()).toString()));
        }
        values.sort(Comparator.comparing(value->value.component.flattenToString()));return values;
    }
    static String defaultComponent(Context context){
        try{return Settings.Secure.getString(context.getContentResolver(),"voice_recognition_service");}
        catch(SecurityException unavailable){return null;}
    }
    static Provider selected(Context context){
        List<Provider> providers=available(context);
        String chosen=context.getSharedPreferences("settings",Context.MODE_PRIVATE).getString("speech_provider","");
        // An explicitly selected provider which has been removed must not silently
        // redirect a recording to a different app.
        if(!chosen.isEmpty())return match(providers,chosen);
        Provider configured=match(providers,defaultComponent(context));
        return configured!=null?configured:providers.size()==1?providers.get(0):null;
    }
    private static Provider match(List<Provider> providers,String flattened){
        ComponentName wanted=flattened==null?null:ComponentName.unflattenFromString(flattened);
        for(Provider provider:providers)if(provider.component.equals(wanted))return provider;return null;
    }
    static String description(Context context){
        Provider provider=selected(context);
        return provider==null?(available(context).isEmpty()?"未检测到公开的系统识别服务":"请在语音设置中选择识别服务"):
            provider.label+" · "+provider.component.getPackageName();
    }
}
