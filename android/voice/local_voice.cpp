#include <jni.h>
#include <memory>
#include <exception>
#include <algorithm>
#include <cmath>
#include <vector>
#include "c-api.h"

static void fail(JNIEnv *env,const char *message){env->ThrowNew(env->FindClass("java/lang/IllegalStateException"),message);}

extern "C" JNIEXPORT jlong JNICALL Java_org_wordtrail_ime_LocalVoiceBridge_create(JNIEnv *env,jclass,jstring model,jstring tokens,jstring language){
    const char *m=env->GetStringUTFChars(model,nullptr),*t=env->GetStringUTFChars(tokens,nullptr),*l=env->GetStringUTFChars(language,nullptr);
    SherpaOnnxOfflineRecognizerConfig config{};
    config.decoding_method="greedy_search";
    config.feat_config.sample_rate=16000;config.feat_config.feature_dim=80;
    config.model_config.num_threads=2;config.model_config.provider="cpu";
    config.model_config.tokens=t;config.model_config.sense_voice.model=m;
    config.model_config.sense_voice.language=l;config.model_config.sense_voice.use_itn=1;
    const SherpaOnnxOfflineRecognizer *recognizer=nullptr;
    try{recognizer=SherpaOnnxCreateOfflineRecognizer(&config);}catch(const std::exception &e){fail(env,e.what());}
    env->ReleaseStringUTFChars(model,m);env->ReleaseStringUTFChars(tokens,t);env->ReleaseStringUTFChars(language,l);
    if(!recognizer && !env->ExceptionCheck())fail(env,"Cannot load local speech model");
    return reinterpret_cast<jlong>(recognizer);
}

extern "C" JNIEXPORT jstring JNICALL Java_org_wordtrail_ime_LocalVoiceBridge_decode(JNIEnv *env,jclass,jlong handle,jfloatArray samples){
    if(!handle){fail(env,"Speech model is not ready");return nullptr;}
    const auto *recognizer=reinterpret_cast<const SherpaOnnxOfflineRecognizer*>(handle);
    std::unique_ptr<const SherpaOnnxOfflineStream,decltype(&SherpaOnnxDestroyOfflineStream)> stream(SherpaOnnxCreateOfflineStream(recognizer),&SherpaOnnxDestroyOfflineStream);
    if(!stream){fail(env,"Cannot create speech stream");return nullptr;}
    jfloat *data=env->GetFloatArrayElements(samples,nullptr);
    if(!data)return nullptr;
    try{SherpaOnnxAcceptWaveformOffline(stream.get(),16000,data,env->GetArrayLength(samples));}
    catch(const std::exception &e){env->ReleaseFloatArrayElements(samples,data,JNI_ABORT);fail(env,e.what());return nullptr;}
    env->ReleaseFloatArrayElements(samples,data,JNI_ABORT);
    try{
        SherpaOnnxDecodeOfflineStream(recognizer,stream.get());
        std::unique_ptr<const SherpaOnnxOfflineRecognizerResult,decltype(&SherpaOnnxDestroyOfflineRecognizerResult)> result(SherpaOnnxGetOfflineStreamResult(stream.get()),&SherpaOnnxDestroyOfflineRecognizerResult);
        return env->NewStringUTF(result && result->text?result->text:"");
    }catch(const std::exception &e){fail(env,e.what());return nullptr;}
}
extern "C" JNIEXPORT void JNICALL Java_org_wordtrail_ime_LocalVoiceBridge_destroy(JNIEnv*,jclass,jlong handle){if(handle)SherpaOnnxDestroyOfflineRecognizer(reinterpret_cast<const SherpaOnnxOfflineRecognizer*>(handle));}

extern "C" JNIEXPORT jlong JNICALL Java_org_wordtrail_ime_LocalVoiceBridge_createVad(JNIEnv *env,jclass,jstring model){
    const char *path=env->GetStringUTFChars(model,nullptr);
    SherpaOnnxVadModelConfig config{};
    config.silero_vad.model=path;config.silero_vad.threshold=.3f;
    config.silero_vad.min_silence_duration=.2f;config.silero_vad.min_speech_duration=.12f;
    config.silero_vad.max_speech_duration=30;config.silero_vad.window_size=512;
    config.sample_rate=16000;config.num_threads=1;config.provider="cpu";
    const SherpaOnnxVoiceActivityDetector *vad=nullptr;
    try{vad=SherpaOnnxCreateVoiceActivityDetector(&config,35.0f);}catch(const std::exception &e){fail(env,e.what());}
    env->ReleaseStringUTFChars(model,path);
    if(!vad && !env->ExceptionCheck())fail(env,"Cannot load speech activity detector");
    return reinterpret_cast<jlong>(vad);
}

// Run on the same inference worker as ASR. Reset state per snapshot/session.
// VAD analyses normalized audio; ASR receives original samples and context.
extern "C" JNIEXPORT jfloatArray JNICALL Java_org_wordtrail_ime_LocalVoiceBridge_speechWindow(JNIEnv *env,jclass,jlong handle,jfloatArray samples){
    if(!handle){fail(env,"Speech activity detector is not ready");return nullptr;}
    auto *vad=reinterpret_cast<const SherpaOnnxVoiceActivityDetector*>(handle);
    int length=env->GetArrayLength(samples);jfloat *data=env->GetFloatArrayElements(samples,nullptr);if(!data)return nullptr;
    int first=length,last=0;
    try{
        SherpaOnnxVoiceActivityDetectorReset(vad);
        float peak=0;for(int i=0;i<length;i++)peak=std::max(peak,std::abs(data[i]));
        float gain=peak>0 && peak<.25f?.25f/peak:1.f;
        std::vector<float> analysis(length+8192,0.f);for(int i=0;i<length;i++)analysis[i]=data[i]*gain;
        for(int i=0;i+512<=static_cast<int>(analysis.size());i+=512)SherpaOnnxVoiceActivityDetectorAcceptWaveform(vad,analysis.data()+i,512);
        SherpaOnnxVoiceActivityDetectorFlush(vad);
        while(!SherpaOnnxVoiceActivityDetectorEmpty(vad)){
            std::unique_ptr<const SherpaOnnxSpeechSegment,decltype(&SherpaOnnxDestroySpeechSegment)> segment(SherpaOnnxVoiceActivityDetectorFront(vad),&SherpaOnnxDestroySpeechSegment);
            if(segment){first=std::min(first,segment->start);last=std::max(last,segment->start+segment->n);}
            SherpaOnnxVoiceActivityDetectorPop(vad);
        }
        bool found=last>first;
        first=std::max(0,first-4000);last=std::min(length,last+4000);
        int count=found && last>first?last-first:0;jfloatArray result=env->NewFloatArray(count);
        if(result && count)env->SetFloatArrayRegion(result,0,count,data+first);
        env->ReleaseFloatArrayElements(samples,data,JNI_ABORT);return result;
    }catch(const std::exception &e){env->ReleaseFloatArrayElements(samples,data,JNI_ABORT);fail(env,e.what());return nullptr;}
}
extern "C" JNIEXPORT void JNICALL Java_org_wordtrail_ime_LocalVoiceBridge_destroyVad(JNIEnv*,jclass,jlong handle){if(handle)SherpaOnnxDestroyVoiceActivityDetector(reinterpret_cast<const SherpaOnnxVoiceActivityDetector*>(handle));}
