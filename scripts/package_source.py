"""提供与 APK 对应的源码，包括依赖和数据；排除工具链、私钥和重复生成物。"""
from pathlib import Path
import hashlib, json, shutil, zipfile, os

ROOT=Path(__file__).resolve().parents[1]
DELIVERY=Path('D:/soft/英语输入法/手机版')
SKIP_ROOT={'target','build','dist'}
SKIP_PREFIXES=('third-party/rust/','android/app/src/main/assets/data/','android/app/src/main/assets/voice/','android/app/src/main/jniLibs/',
               'android/app/build/','android/.gradle/','ios/Keyboard/Data/','ios/Frameworks/')

GUIDES=('安装与测试指南.md', '测试报告.md', 'GitHub调研.md', '主题预览.html', '0.1.2界面更新.md', '0.1.3语音更新.md', '0.1.4语音更新.md', '0.1.5布局更新.md', '0.1.6词汇分级.md', '0.1.7图标更新.md', '0.1.8词汇目标.md', '0.1.8测试报告.md', '0.1.9标签精简.md', '0.1.10实际扩词.md', '0.1.10测试报告.md', '分批补词计划.md', '0.1.11四六级补词.md', '0.1.11测试报告.md', '0.1.12四六级补词.md', '0.1.12测试报告.md', '0.1.13四六级补词.md', '0.1.13测试报告.md', '0.1.14四六级补词.md', '0.1.14测试报告.md', '0.1.15四六级补词.md', '0.1.15测试报告.md', '0.1.16四六级补词.md', '0.1.16测试报告.md', '0.1.17四六级补词.md', '0.1.17测试报告.md', '0.1.18四六级补词.md', '0.1.18测试报告.md', '0.1.19四六级补词.md', '0.1.19测试报告.md', '0.1.20专四专八雅思托福补词.md', '0.1.21专八托福雅思补词.md', '0.1.22专四专八雅思托福补词.md', '0.1.23专四专八雅思托福补词.md', '0.1.23测试报告.md', '0.1.24专业词汇首批.md', '0.1.25计算机术语第二段.md', '0.1.26商务金融标签.md', '0.1.26测试报告.md', '0.1.27商业金融词汇.md', '0.1.27测试报告.md', '0.1.28商业金融词汇.md', '0.1.28测试报告.md', '21-MeSH医学词汇.md', '22-Wikidata医学译词.md', '23-Wikidata医学译词补充.md', '24-NAER医学学术词汇.md', '25-NAER医学词条补充.md')
GUIDES += ('26-NAER生命科学词汇.md', '27-NAER兽医学词汇.md', '28-WordLevel考试词汇.md')
GUIDES += ('29-OpenEtymology四六级补词.md', '0.1.29测试报告.md')
GUIDES += ('30-NAER经济学术语补充.md', '31-NAER计算机学术名词补充.md', '32-NAER会计学术名词补充.md', '33-NAER管理学术名词补充.md', '34-NAER行政学术名词补充.md', '35-NAER教育词汇补充.md', '36-NAER心理学词汇补充.md')

def main():
    for name in GUIDES:
        if not (ROOT/'docs'/name).is_file():raise FileNotFoundError('Missing delivery guide: '+name)
    dist=ROOT/'dist'; dist.mkdir(exist_ok=True)
    archive=dist/'wordtrail-0.1.29-source.zip'
    count=0
    with zipfile.ZipFile(archive,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=1,strict_timestamps=False) as output:
        # Prune build/cache trees before walking; their contents never belong
        # in a source release and can contain hundreds of thousands of files.
        source_files=[]
        for directory,folders,names in os.walk(ROOT):
            parent=Path(directory)
            folders[:]=[name for name in folders if name not in {'.git','__pycache__'}
                       and not (parent==ROOT and name in SKIP_ROOT)
                       and not ((parent/name).relative_to(ROOT).as_posix()+'/').startswith(SKIP_PREFIXES)]
            source_files.extend(parent/name for name in names)
        for file in sorted(source_files):
            if not file.is_file(): continue
            relative=file.relative_to(ROOT); path=relative.as_posix()
            if relative.parts[0] in SKIP_ROOT or any(p in {'.git','__pycache__'} for p in relative.parts): continue
            if file.name.lower().startswith('.env') or file.name.lower() in {'.npmrc','.pypirc','.netrc'}: continue
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
    files=[archive,dist/'wordtrail-0.1.29-debug.apk']
    for file in files: shutil.copy2(file,DELIVERY/file.name)
    for name in GUIDES:shutil.copy2(ROOT/'docs'/name,DELIVERY/name)
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
