package org.wordtrail.ime;

final class NativeBridge {
    static { System.loadLibrary("wordtrail_mobile"); }
    static native String request(String json);
    private NativeBridge() {}
}
