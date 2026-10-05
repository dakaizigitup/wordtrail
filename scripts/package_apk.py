"""将 DEX、离线数据和原生库放入 aapt2 生成的资源 APK。"""
from pathlib import Path
import shutil, zipfile
ROOT=Path(__file__).resolve().parents[1]
BUILD=ROOT/'build/android'
shutil.copy2(BUILD/'base.apk',BUILD/'unsigned.apk')
with zipfile.ZipFile(BUILD/'unsigned.apk','a') as apk:
    for path in (BUILD/'dex').glob('*.dex'): apk.write(path,path.name,compress_type=zipfile.ZIP_DEFLATED)
    for path in (ROOT/'android/app/src/main/assets').rglob('*'):
        if path.is_file(): apk.write(path,'assets/'+path.relative_to(ROOT/'android/app/src/main/assets').as_posix(),compress_type=zipfile.ZIP_DEFLATED)
    for path in (ROOT/'android/app/src/main/jniLibs').rglob('*.so'):
        apk.write(path,'lib/'+path.relative_to(ROOT/'android/app/src/main/jniLibs').as_posix(),compress_type=zipfile.ZIP_STORED)

