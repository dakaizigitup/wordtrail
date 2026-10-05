package org.wordtrail.ime;

import android.content.Context;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;

final class DataFiles {
    // 数据在应用私有目录中展开；升级只替换随包数据，不碰用户学习文件。
    static File prepare(Context context) throws Exception {
        File dir = new File(context.getFilesDir(), "data-0.1.4-ipa1");
        if (!dir.isDirectory() && !dir.mkdirs()) throw new IllegalStateException("Cannot create data directory");
        for (String name : context.getAssets().list("data")) {
            File target = new File(dir, name);
            if (target.isFile() && target.length() > 0) continue;
            File temporary = new File(dir, name + ".tmp");
            try (InputStream in = context.getAssets().open("data/" + name); FileOutputStream out = new FileOutputStream(temporary)) {
                byte[] buffer = new byte[65536]; int count;
                while ((count = in.read(buffer)) != -1) out.write(buffer, 0, count);
                out.getFD().sync();
            }
            Files.move(temporary.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING);
        }
        return dir;
    }
    private DataFiles() {}
}
