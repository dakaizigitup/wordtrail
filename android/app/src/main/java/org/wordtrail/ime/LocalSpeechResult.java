package org.wordtrail.ime;

import java.util.Arrays;

/** Audio preparation shared by preview and completion; never averages over long pauses. */
final class LocalSpeechResult {
    static final int RATE=16000,FRAME=320;
    static float[] speechWindow(float[] samples){
        if(samples.length<RATE/4)return new float[0];
        double peak=0;
        for(int offset=0;offset<samples.length;offset+=FRAME)peak=Math.max(peak,power(samples,offset));
        // Reject digital silence/very faint noise, but retain quiet phone recordings.
        if(peak<1e-8)return new float[0];
        double threshold=Math.max(1e-8,Math.min(1e-6,peak*.08));
        int first=-1,last=0;
        for(int offset=0;offset<samples.length;offset+=FRAME){
            if(power(samples,offset)>=threshold){if(first<0)first=offset;last=Math.min(samples.length,offset+FRAME);}
        }
        if(first<0)return new float[0];
        int padding=RATE/4;
        return Arrays.copyOfRange(samples,Math.max(0,first-padding),Math.min(samples.length,last+padding));
    }
    private static double power(float[] samples,int offset){
        int end=Math.min(samples.length,offset+FRAME);double energy=0;
        for(int i=offset;i<end;i++)energy+=samples[i]*samples[i];
        return energy/(end-offset);
    }
    static String completedText(String finalText,String preview){
        String text=finalText==null?"":finalText.trim();
        return text.isEmpty()?(preview==null?"":preview.trim()):text;
    }
    private LocalSpeechResult(){}
}
