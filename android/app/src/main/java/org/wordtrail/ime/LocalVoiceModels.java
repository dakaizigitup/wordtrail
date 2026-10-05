package org.wordtrail.ime;

import android.content.Context;
import java.io.*;
import java.security.MessageDigest;

/** Copy and verify bundled files once. No network or user recordings. */
final class LocalVoiceModels {
    private static final String MODEL_SHA="c71f0ce00bec95b07744e116345e33d8cbbe08cef896382cf907bf4b51a2cd51";
    private static final String TOKENS_SHA="f449eb28dc567533d7fa59be34e2abca8784f771850c78a47fb731a31429a1dc";
    interface Progress {void update(int percent);}
    static synchronized File prepare(Context context,Progress progress) throws Exception{
        File directory=new File(context.getFilesDir(),"sensevoice-int8-20240717");
        if(!directory.isDirectory() && !directory.mkdirs())throw new IOException("Cannot create model directory");
        copy(context,directory,"model.int8.onnx",239233841,MODEL_SHA,progress);
        copy(context,directory,"tokens.txt",315894,TOKENS_SHA,percent->{});
        copy(context,directory,"silero_vad.onnx",643854,"9e2449e1087496d8d4caba907f23e0bd3f78d91fa552479bb9c23ac09cbb1fd6",percent->{});
        return directory;
    }
    private static void copy(Context context,File directory,String name,long size,String sha,Progress progress) throws Exception{
        File target=new File(directory,name),marker=new File(directory,name+".verified");
        if(target.length()==size && marker.isFile() && sha.equals(new String(java.nio.file.Files.readAllBytes(marker.toPath()),java.nio.charset.StandardCharsets.US_ASCII)))return;
        File temporary=new File(directory,name+".tmp");
        MessageDigest digest=MessageDigest.getInstance("SHA-256");long count=0;int previous=-1;
        try(InputStream input=context.getAssets().open("voice/"+name);OutputStream output=new FileOutputStream(temporary)){
            byte[] buffer=new byte[65536];int read;
            while((read=input.read(buffer))!=-1){output.write(buffer,0,read);digest.update(buffer,0,read);count+=read;int percent=(int)(count*100/size);if(percent!=previous){previous=percent;progress.update(percent);}}
        }
        StringBuilder hash=new StringBuilder();for(byte b:digest.digest())hash.append(String.format(java.util.Locale.ROOT,"%02x",b&255));
        if(count!=size || !sha.equals(hash.toString())){temporary.delete();throw new IOException("Speech model checksum mismatch");}
        java.nio.file.Files.move(temporary.toPath(),target.toPath(),java.nio.file.StandardCopyOption.REPLACE_EXISTING);
        java.nio.file.Files.write(marker.toPath(),sha.getBytes(java.nio.charset.StandardCharsets.US_ASCII));
    }
}
