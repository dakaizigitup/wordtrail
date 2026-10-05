"""提供与 APK 对应的源码，包括依赖和数据；排除工具链、私钥和重复生成物。"""
from pathlib import Path
import hashlib, json, shutil, zipfile

ROOT=Path(__file__).resolve().parents[1]
DELIVERY=Path('D:/soft/英语输入法/手机版')
SKIP_ROOT={'target','build','dist'}
SKIP_PREFIXES=('third-party/rust/','android/app/src/main/assets/data/','android/app/src/main/assets/voice/','android/app/src/main/jniLibs/',
               'android/app/build/','android/.gradle/','ios/Keyboard/Data/','ios/Frameworks/')

def main():
    dist=ROOT/'dist'; dist.mkdir(exist_ok=True)
    archive=dist/'wordtrail-0.1.7-source.zip'
    count=0
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1,strict_timestamps=False) as output:
        for file in sorted(ROOT.rglob('*')):
            if not file.is_file(): continue
            relative=file.relative_to(ROOT); path=relative.as_posix()
            if relative.parts[0] in SKIP_ROOT or any(p in {'.git','__pycache__'} for p in relative.parts): continue
            if path.startswith(SKIP_PREFIXES) or file.suffix in {'.keystore','.jks','.pyc'}: continue
            if path.startswith('docs/screenshots/') and any(word in file.name for word in ['failure','retry','debug']):continue
            if path in {'android/local.properties','android/app/src/main/assets/NOTICE.txt','ios/App/NOTICE.txt'}: continue
            output.write(file,'wordtrail-mobile/'+path); count+=1
        # Include generated notices required by the host application resources.
        output.write(ROOT/'ios/App/NOTICE.txt','wordtrail-mobile/ios/App/NOTICE.txt')
        output.write(ROOT/'android/app/src/main/assets/NOTICE.txt','wordtrail-mobile/android/app/src/main/assets/NOTICE.txt')
    with zipfile.ZipFile(archive) as source:
        assert source.testzip() is None
    DELIVERY.mkdir(parents=True,exist_ok=True)
    files=[archive,dist/'wordtrail-0.1.7-debug.apk']
    for file in files: shutil.copy2(file,DELIVERY/file.name)
    shutil.copy2(ROOT/'docs/安装与测试指南.md',DELIVERY/'安装与测试指南.md')
    shutil.copy2(ROOT/'docs/测试报告.md',DELIVERY/'测试报告.md')
    shutil.copy2(ROOT/'docs/GitHub调研.md',DELIVERY/'GitHub调研.md')
    shutil.copy2(ROOT/'docs/主题预览.html',DELIVERY/'主题预览.html')
    shutil.copy2(ROOT/'docs/0.1.2界面更新.md',DELIVERY/'0.1.2界面更新.md')
    shutil.copy2(ROOT/'docs/0.1.3语音更新.md',DELIVERY/'0.1.3语音更新.md')
    shutil.copy2(ROOT/'docs/0.1.4语音更新.md',DELIVERY/'0.1.4语音更新.md')
    shutil.copy2(ROOT/'docs/0.1.5布局更新.md',DELIVERY/'0.1.5布局更新.md')
    shutil.copy2(ROOT/'docs/0.1.6词汇分级.md',DELIVERY/'0.1.6词汇分级.md')
    shutil.copy2(ROOT/'docs/0.1.7图标更新.md',DELIVERY/'0.1.7图标更新.md')
    shutil.copy2(ROOT/'branding/wordtrail-warm-icon.png',DELIVERY/'词伴暖色图标.png')
    previews=DELIVERY/'screenshots';previews.mkdir(exist_ok=True)
    for image in (ROOT/'docs/screenshots').glob('*.png'):
        if not any(word in image.name for word in ['failure','retry','debug']):shutil.copy2(image,previews/image.name)
    evidence=DELIVERY/'evidence';evidence.mkdir(exist_ok=True)
    for result in (ROOT/'docs/evidence').iterdir():
        if result.is_file():shutil.copy2(result,evidence/result.name)
    checksums={file.name:{'bytes':file.stat().st_size,'sha256':hashlib.file_digest(file.open('rb'),'sha256').hexdigest()} for file in files}
    (DELIVERY/'SHA256.json').write_text(json.dumps(checksums,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'source_files':count,'delivery':str(DELIVERY),'artifacts':checksums},ensure_ascii=False,indent=2))

if __name__=='__main__': main()
