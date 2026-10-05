package org.wordtrail.ime;

/** Minimal JNI bridge to the pinned sherpa-onnx C API. Calls are serialized. */
public final class LocalVoiceBridge {
    static {System.loadLibrary("wordtrail_voice");}
    private LocalVoiceBridge(){}
    public static native long create(String model,String tokens,String language);
    public static native String decode(long handle,float[] samples);
    public static native void destroy(long handle);
    public static native long createVad(String model);
    public static native float[] speechWindow(long handle,float[] samples);
    public static native void destroyVad(long handle);
}
