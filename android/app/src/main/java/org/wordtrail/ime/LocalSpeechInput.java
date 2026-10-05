package org.wordtrail.ime;

import android.content.Context;
import android.media.*;
import android.os.*;
import java.io.File;
import java.util.*;
import java.util.concurrent.*;
import java.util.concurrent.atomic.AtomicBoolean;

/** Independent local recording/ASR. Audio lives in memory; callbacks stay on main. */
final class LocalSpeechInput {
    private final Context context;
    private final Handler main=new Handler(Looper.getMainLooper());
    private final ExecutorService inference=Executors.newSingleThreadExecutor();
    private volatile Session current;
    private long recognizer;
    private long vad;
    private String modelLanguage="";
    private static final int RATE=16000,MAX_SECONDS=30;
    private static final class Session {
        final SpeechInput.Listener listener;final String language;
        final List<float[]> chunks=new ArrayList<>();final AtomicBoolean previewPending=new AtomicBoolean();
        volatile boolean recording=true,finish;volatile AudioRecord recorder;int count;
        volatile String lastPreview="";
        Session(String locale,SpeechInput.Listener listener){this.listener=listener;language=locale.startsWith("en")?"en":"zh";}
        synchronized void append(float[] values){chunks.add(values);count+=values.length;}
        synchronized float[] snapshot(){float[] all=new float[count];int offset=0;for(float[] values:chunks){System.arraycopy(values,0,all,offset,values.length);offset+=values.length;}return all;}
    }
    LocalSpeechInput(Context context){this.context=context.getApplicationContext();}
    private boolean valid(Session session){return current==session;}
    private void post(Session session,Runnable action){main.post(()->{if(valid(session))action.run();});}
    void start(String locale,SpeechInput.Listener listener){
        cancel();Session session=new Session(locale,listener);current=session;
        inference.execute(()->{
            try{
                post(session,()->listener.partial("正在准备离线语音…"));
                File models=LocalVoiceModels.prepare(context,percent->post(session,()->listener.partial("准备离线模型 · "+percent+"%")));
                if(!valid(session))return;
                if(vad==0)vad=LocalVoiceBridge.createVad(new File(models,"silero_vad.onnx").getAbsolutePath());
                if(recognizer==0 || !modelLanguage.equals(session.language)){
                    if(recognizer!=0){LocalVoiceBridge.destroy(recognizer);recognizer=0;}
                    post(session,()->listener.partial("正在加载离线语音…"));
                    recognizer=LocalVoiceBridge.create(new File(models,"model.int8.onnx").getAbsolutePath(),new File(models,"tokens.txt").getAbsolutePath(),session.language);modelLanguage=session.language;
                }
                if(valid(session))new Thread(()->capture(session),"wordtrail-local-microphone").start();
            }catch(Throwable error){post(session,()->listener.error(100));}
        });
    }
    private void capture(Session session){
        AudioRecord audio=null;
        try{
            int minimum=AudioRecord.getMinBufferSize(RATE,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT);
            if(minimum<=0)throw new IllegalStateException("Unsupported microphone format");
            audio=new AudioRecord(MediaRecorder.AudioSource.VOICE_RECOGNITION,RATE,AudioFormat.CHANNEL_IN_MONO,AudioFormat.ENCODING_PCM_16BIT,Math.max(minimum,8192));
            session.recorder=audio;
            if(audio.getState()!=AudioRecord.STATE_INITIALIZED)throw new IllegalStateException("Microphone is unavailable");
            if(!valid(session) || !session.recording)return;
            audio.startRecording();post(session,session.listener::ready);
            short[] buffer=new short[1024];int nextPreview=RATE*4;
            while(valid(session) && session.recording && session.count<RATE*MAX_SECONDS){
                int read=audio.read(buffer,0,buffer.length,AudioRecord.READ_BLOCKING);
                if(!valid(session))break;
                if(read<=0){if(session.recording)throw new IllegalStateException("Microphone read failed");else break;}
                float[] values=new float[read];for(int i=0;i<read;i++)values[i]=buffer[i]/32768f;session.append(values);
                if(!session.recording)break;
                if(session.count>=nextPreview){nextPreview+=RATE*4;preview(session);}
            }
            if(valid(session) && session.recording){session.finish=true;session.recording=false;}
        }catch(SecurityException error){post(session,()->session.listener.error(9));session.finish=false;}
        catch(Throwable error){if(valid(session) && session.recording){session.finish=false;post(session,()->session.listener.error(3));}}
        finally{
            session.recorder=null;
            if(audio!=null){try{audio.stop();}catch(IllegalStateException ignored){}audio.release();}
            if(valid(session) && session.finish){post(session,session.listener::waiting);inference.execute(()->decode(session));}
        }
    }
    private void preview(Session session){
        if(!session.previewPending.compareAndSet(false,true))return;
        float[] samples=LocalSpeechResult.speechWindow(session.snapshot());
        inference.execute(()->{
            try{
                if(!valid(session) || !session.recording || samples.length==0)return;
                float[] voice=LocalVoiceBridge.speechWindow(vad,samples);if(voice.length==0)return;
                String text=LocalVoiceBridge.decode(recognizer,voice).trim();
                if(!text.isEmpty() && valid(session)){session.lastPreview=text;post(session,()->{if(session.recording)session.listener.partial(text);});}
            }catch(Throwable ignored){/* A failed preview does not prevent final recognition. */}
            finally{session.previewPending.set(false);}
        });
    }
    private void decode(Session session){
        if(!valid(session))return;
        try{
            float[] samples=LocalSpeechResult.speechWindow(session.snapshot());
            if(samples.length>0)samples=LocalVoiceBridge.speechWindow(vad,samples);
            String text=samples.length==0?"":LocalVoiceBridge.decode(recognizer,samples);
            complete(session,text,7);
        }catch(Throwable error){complete(session,"",100);}
    }
    private void complete(Session session,String finalText,int errorCode){
        String text=LocalSpeechResult.completedText(finalText,session.lastPreview);
        if(text.isEmpty())post(session,()->session.listener.error(errorCode));
        else post(session,()->session.listener.result(text));
    }
    void stop(){Session session=current;if(session==null)return;session.finish=true;session.recording=false;stopRecorder(session);}
    void cancel(){Session session=current;current=null;if(session!=null){session.finish=false;session.recording=false;stopRecorder(session);}}
    private void stopRecorder(Session session){AudioRecord audio=session.recorder;if(audio!=null)try{audio.stop();}catch(IllegalStateException ignored){}}
    void destroy(){cancel();inference.execute(()->{if(recognizer!=0){LocalVoiceBridge.destroy(recognizer);recognizer=0;}if(vad!=0){LocalVoiceBridge.destroyVad(vad);vad=0;}});inference.shutdown();}
}
