"""Package the tested enhancement for an existing official Windows 0.1.4 install."""
from pathlib import Path
import hashlib, json, shutil

ROOT=Path(__file__).resolve().parents[1]
DELIVERY=Path('D:/soft/英语输入法/电脑版词汇补丁')
def sha(path):
    with path.open('rb') as stream:return hashlib.file_digest(stream,'sha256').hexdigest()
def main():
    DELIVERY.mkdir(parents=True,exist_ok=True)
    for source,name in [(ROOT/'target/release/qingjian-server.exe','qingjian-server.exe'),(ROOT/'data/pronunciation-en.qj','pronunciation-en.qj'),(ROOT/'scripts/install_desktop_ipa.ps1','install_desktop_ipa.ps1'),(ROOT/'desktop/NOTICE.txt','NOTICE.txt'),(ROOT/'LICENSE','LICENSE')]:
        shutil.copy2(source,DELIVERY/name)
    original='c9c3ac98a5b51f57fcbfd8ccec8ed25a96502592b7a40b498bc2a6447c54e554'
    shutil.copy2(ROOT/'scripts/vocabulary_settings.ps1',DELIVERY/'vocabulary_settings.ps1')
    (DELIVERY/'settings.cmd').write_text('@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0vocabulary_settings.ps1"\r\n',encoding='ascii')
    manifest=dict(version='0.1.2',base_version='Qingjian Windows 0.1.4',original_server_sha256=original,supported_previous_server_sha256=['2fcb6f5b467fc0dce46777fdb1723c807e04712c84c9e25718e43880e817396d'],artifacts={})
    for name in ['qingjian-server.exe','pronunciation-en.qj','install_desktop_ipa.ps1','vocabulary_settings.ps1','settings.cmd']:
        path=DELIVERY/name
        manifest['artifacts'][name]=dict(bytes=path.stat().st_size,sha256=sha(path))
    (DELIVERY/'SHA256.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    for name,extra in [('install.cmd',''),('rollback.cmd',' -Rollback')]:
        (DELIVERY/name).write_text('@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0install_desktop_ipa.ps1"'+extra+'\r\n',encoding='ascii')
    shutil.copy2(ROOT/'docs/电脑版音标补丁.md',DELIVERY/'使用说明.md')
    evidence=DELIVERY/'evidence';evidence.mkdir(exist_ok=True)
    for name in ['desktop-tests.json','desktop-tests.txt','pronunciation-tests.txt']:
        shutil.copy2(ROOT/'build'/name,evidence/name)
    shutil.copy2(ROOT/'docs/screenshots/desktop-ipa.png',DELIVERY/'desktop-ipa.png')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))
if __name__=='__main__':main()
