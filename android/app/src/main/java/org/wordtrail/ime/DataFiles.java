package org.wordtrail.ime;

import android.content.Context;
import java.io.File;
import java.io.FileOutputStream;
import java.io.InputStream;
import java.nio.file.Files;
import java.nio.file.StandardCopyOption;
import java.security.MessageDigest;
import java.nio.charset.StandardCharsets;
import org.json.JSONObject;

final class DataFiles {
    // 数据在应用私有目录中展开；升级只替换随包数据，不碰用户学习文件。
    static synchronized File prepare(Context context) throws Exception {
        byte[] manifest;
        try (InputStream in = context.getAssets().open("data/data-pack.json")) {
            java.io.ByteArrayOutputStream out = new java.io.ByteArrayOutputStream();
            byte[] buffer = new byte[8192]; int count;
            while ((count = in.read(buffer)) != -1) out.write(buffer, 0, count);
            manifest = out.toByteArray();
        }
        String fingerprint = hex(MessageDigest.getInstance("SHA-256").digest(manifest));
        JSONObject entries = new JSONObject(new String(manifest, StandardCharsets.UTF_8));
        File dir = new File(context.getFilesDir(), "data-" + fingerprint.substring(0, 24));
        if (!dir.isDirectory() && !dir.mkdirs()) throw new IllegalStateException("Cannot create data directory");
        java.util.Iterator<String> names = entries.keys();
        while (names.hasNext()) {
            String name = names.next();
            if (!name.matches("[a-zA-Z0-9._-]+")) throw new IllegalStateException("Invalid data name");
            JSONObject entry = entries.getJSONObject(name);
            File target = new File(dir, name);
            if (target.isFile() && target.length() == entry.getLong("bytes")) continue;
            File temporary = new File(dir, name + ".tmp");
            MessageDigest digest = MessageDigest.getInstance("SHA-256");
            try (InputStream in = context.getAssets().open("data/" + name); FileOutputStream out = new FileOutputStream(temporary)) {
                byte[] buffer = new byte[65536]; int count;
                while ((count = in.read(buffer)) != -1) { out.write(buffer, 0, count); digest.update(buffer, 0, count); }
                out.getFD().sync();
            }
            if (temporary.length() != entry.getLong("bytes") || !hex(digest.digest()).equals(entry.getString("sha256"))) {
                throw new IllegalStateException("Data checksum mismatch: " + name);
            }
            Files.move(temporary.toPath(), target.toPath(), StandardCopyOption.REPLACE_EXISTING);
        }
        return dir;
    }
    private static String hex(byte[] bytes) {
        StringBuilder text = new StringBuilder();
        for (byte value : bytes) text.append(String.format(java.util.Locale.ROOT, "%02x", value & 255));
        return text.toString();
    }
    private DataFiles() {}
}
