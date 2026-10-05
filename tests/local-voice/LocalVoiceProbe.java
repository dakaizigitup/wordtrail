package org.wordtrail.voicetest;

import android.app.*;
import android.os.*;
import android.content.Context;
import java.io.*;
import java.lang.reflect.*;
import java.nio.*;
import org.json.*;
import java.util.concurrent.*;

/** Uses the release APK's actual model, native library and C API, without network. */
public final class LocalVoiceProbe extends Instrumentation {
    private float[] speechForPreview;
    private long vad;
    @Override public void onCreate(Bundle arguments){super.onCreate(arguments);start();}
    @Override public void onStart(){
        Bundle output=new Bundle();long handle=0;Class<?> bridge=null;
        try{
            Context target=getTargetContext();ClassLoader loader=target.getClassLoader();
            Class<?> models=Class.forName("org.wordtrail.ime.LocalVoiceModels",true,loader);
            Class<?> progress=Class.forName("org.wordtrail.ime.LocalVoiceModels$Progress",true,loader);
            Object callback=Proxy.newProxyInstance(loader,new Class<?>[]{progress},(p,m,args)->null);
            Method prepare=models.getDeclaredMethod("prepare",Context.class,progress);prepare.setAccessible(true);
            long start=SystemClock.elapsedRealtime();File directory=(File)prepare.invoke(null,target,callback);
            JSONObject report=new JSONObject().put("prepare_ms",SystemClock.elapsedRealtime()-start).put("internet_permission",target.checkSelfPermission("android.permission.INTERNET"));
            bridge=Class.forName("org.wordtrail.ime.LocalVoiceBridge",true,loader);
            vad=(Long)bridge.getMethod("createVad",String.class).invoke(null,new File(directory,"silero_vad.onnx").getAbsolutePath());
            Method create=bridge.getMethod("create",String.class,String.class,String.class),decode=bridge.getMethod("decode",long.class,float[].class),destroy=bridge.getMethod("destroy",long.class);
            JSONArray cases=new JSONArray(),completionCases=new JSONArray();
            for(String language:new String[]{"zh","en"}){
                start=SystemClock.elapsedRealtime();
                handle=(Long)create.invoke(null,new File(directory,"model.int8.onnx").getAbsolutePath(),new File(directory,"tokens.txt").getAbsolutePath(),language);
                long load=SystemClock.elapsedRealtime()-start;
                float[] samples=readWave(language+".wav");start=SystemClock.elapsedRealtime();
                String text=(String)decode.invoke(null,handle,samples);
                cases.put(new JSONObject().put("language",language).put("text",text).put("audio_seconds",samples.length/16000.0).put("load_ms",load).put("decode_ms",SystemClock.elapsedRealtime()-start));
                if(language.equals("zh")){
                    speechForPreview=samples;
                    float[] quiet=quietWithTail(samples);double energy=0;for(float value:quiet)energy+=value*value;
                    if(energy/quiet.length>=1e-6)throw new AssertionError("Regression audio must fail the old whole-recording energy gate");
                    JSONObject real=completion(target,handle,quiet,"",false).put("name","quiet speech followed by a long pause").put("old_mean_power",energy/quiet.length);
                    if(!real.optString("text").equals(text))throw new AssertionError(real.toString());completionCases.put(real);
                    JSONObject fallback=completion(target,handle,new float[16000],text,false).put("name","valid preview survives an empty final recording");
                    if(fallback.optString("real_preview").isEmpty() || !fallback.optString("text").equals(fallback.optString("real_preview")))throw new AssertionError(fallback.toString());completionCases.put(fallback);
                    JSONObject silent=completion(target,handle,new float[16000],"",false).put("name","new silent session cannot reuse a previous preview");
                    if(silent.optInt("error")!=7)throw new AssertionError(silent.toString());completionCases.put(silent);
                    float[] noise=new float[16000];java.util.Random random=new java.util.Random(42);for(int i=0;i<noise.length;i++)noise[i]=(random.nextFloat()-.5f)*.01f;
                    JSONObject background=completion(target,handle,noise,"",false).put("name","non-speech background noise cannot hallucinate text");
                    if(background.optInt("error")!=7)throw new AssertionError(background.toString());completionCases.put(background);
                    JSONObject cancelled=completion(target,handle,quiet,text,true).put("name","cancellation suppresses late completion");
                    if(!cancelled.optBoolean("cancelled_without_callback"))throw new AssertionError(cancelled.toString());completionCases.put(cancelled);
                }
                destroy.invoke(null,handle);handle=0;
            }
            report.put("cases",cases);report.put("completion_cases",completionCases);report.put("pss_kb",Debug.getPss());output.putString("result",report.toString());finish(Activity.RESULT_OK,output);
        }catch(Throwable error){output.putString("error",android.util.Log.getStackTraceString(error));finish(Activity.RESULT_CANCELED,output);}
        finally{if(handle!=0 && bridge!=null)try{bridge.getMethod("destroy",long.class).invoke(null,handle);}catch(Exception ignored){}if(vad!=0 && bridge!=null)try{bridge.getMethod("destroyVad",long.class).invoke(null,vad);}catch(Exception ignored){}}
    }
    private float[] quietWithTail(float[] original){
        double peak=0;for(int offset=0;offset<original.length;offset+=320){double power=0;int end=Math.min(original.length,offset+320);for(int i=offset;i<end;i++)power+=original[i]*original[i];peak=Math.max(peak,power/(end-offset));}
        double gain=Math.sqrt(2e-6/peak);float[] result=new float[16000*30];
        for(int i=0;i<original.length;i++)result[i]=(float)(Math.round(original[i]*gain*32768)/32768.0);
        return result;
    }
    /** Actual production Java completion and native model; synthetic PCM only replaces the microphone. */
    private JSONObject completion(Context target,long recognizer,float[] samples,String preview,boolean cancel)throws Exception{
        ClassLoader loader=target.getClassLoader();Class<?> input=Class.forName("org.wordtrail.ime.LocalSpeechInput",true,loader),session=Class.forName("org.wordtrail.ime.LocalSpeechInput$Session",true,loader),listener=Class.forName("org.wordtrail.ime.SpeechInput$Listener",true,loader);
        JSONObject result=new JSONObject();CountDownLatch done=new CountDownLatch(1),previewDone=new CountDownLatch(1);
        Object callback=Proxy.newProxyInstance(loader,new Class<?>[]{listener},(p,m,args)->{if(m.getName().equals("partial")){result.put("real_preview",args[0]);previewDone.countDown();}if(m.getName().equals("result")){result.put("text",args[0]);done.countDown();}if(m.getName().equals("error")){result.put("error",args[0]);done.countDown();}return null;});
        Constructor<?> constructor=input.getDeclaredConstructor(Context.class);constructor.setAccessible(true);Object local=constructor.newInstance(target);
        Constructor<?> sessionConstructor=session.getDeclaredConstructor(String.class,listener);sessionConstructor.setAccessible(true);Object current=sessionConstructor.newInstance("zh-CN",callback);
        Method append=session.getDeclaredMethod("append",float[].class);append.setAccessible(true);
        Field active=input.getDeclaredField("current");active.setAccessible(true);active.set(local,current);
        Field nativeHandle=input.getDeclaredField("recognizer");nativeHandle.setAccessible(true);nativeHandle.setLong(local,recognizer);
        Field vadHandle=input.getDeclaredField("vad");vadHandle.setAccessible(true);vadHandle.setLong(local,vad);
        if(!preview.isEmpty()){
            append.invoke(current,(Object)speechForPreview);
            Method recognizePreview=input.getDeclaredMethod("preview",session);recognizePreview.setAccessible(true);recognizePreview.invoke(local,current);
            if(!previewDone.await(10,TimeUnit.SECONDS) || result.optString("real_preview").isEmpty())throw new AssertionError("Real production preview failed: "+result);
            Field chunks=session.getDeclaredField("chunks"),count=session.getDeclaredField("count");chunks.setAccessible(true);count.setAccessible(true);
            // Replace only fixture PCM to force an empty final pass after a real preview.
            synchronized(current){((java.util.List<?>)chunks.get(current)).clear();count.setInt(current,0);}
        }
        append.invoke(current,(Object)samples);
        Method stop=input.getDeclaredMethod("stop");stop.setAccessible(true);stop.invoke(local);
        if(cancel){Method cancelMethod=input.getDeclaredMethod("cancel");cancelMethod.setAccessible(true);cancelMethod.invoke(local);}
        Method decode=input.getDeclaredMethod("decode",session);decode.setAccessible(true);decode.invoke(local,current);
        boolean called=done.await(cancel?500:10000,TimeUnit.MILLISECONDS);
        if(cancel)result.put("cancelled_without_callback",!called);else if(!called)throw new AssertionError("Completion callback timed out");
        nativeHandle.setLong(local,0);vadHandle.setLong(local,0);Method destroy=input.getDeclaredMethod("destroy");destroy.setAccessible(true);destroy.invoke(local);
        return result;
    }
    private float[] readWave(String name)throws Exception{
        ByteArrayOutputStream out=new ByteArrayOutputStream();try(InputStream input=getContext().getAssets().open(name)){byte[] block=new byte[8192];int n;while((n=input.read(block))>0)out.write(block,0,n);}
        ByteBuffer wave=ByteBuffer.wrap(out.toByteArray()).order(ByteOrder.LITTLE_ENDIAN);wave.position(12);
        boolean format=false;
        while(wave.remaining()>=8){int id=wave.getInt(),length=wave.getInt(),offset=wave.position();
            if(id==0x20746d66){int encoding=wave.getShort()&65535,channels=wave.getShort()&65535,rate=wave.getInt();wave.position(offset+14);int bits=wave.getShort()&65535;format=encoding==1&&channels==1&&rate==16000&&bits==16;}
            if(id==0x61746164){if(!format)throw new IOException("Expected mono 16kHz PCM16 WAV");float[] samples=new float[length/2];for(int i=0;i<samples.length;i++)samples[i]=wave.getShort()/32768f;return samples;}
            wave.position(offset+length+(length&1));
        }
        throw new IOException("WAV contains no audio");
    }
}
