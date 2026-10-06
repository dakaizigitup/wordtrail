"""Read-only binary/data checks and an empty IPC session against the installed server."""
from pathlib import Path
import argparse,hashlib,json,struct

ROOT=Path(__file__).resolve().parents[1]
parser=argparse.ArgumentParser()
parser.add_argument('--patch-dir',type=Path,default=Path('D:/soft/英语输入法/电脑版四六级补词补丁'))
PATCH=parser.parse_args().patch_dir
INSTALL=Path('C:/Program Files/Qingjian')
manifest=json.loads((PATCH/'SHA256.json').read_text(encoding='utf-8-sig'))
checks=[]
for name,path in [('qingjian-server.exe',INSTALL/'qingjian-server.exe'),('pronunciation-en.qj',INSTALL/'data/pronunciation-en.qj')]:
    with path.open('rb') as stream:actual=hashlib.file_digest(stream,'sha256').hexdigest()
    assert actual==manifest['artifacts'][name]['sha256'],name
    checks.append(name+' installed checksum verified')
with open(r'\\.\pipe\qingjian','r+b',buffering=0) as pipe:
    def send(kind,payload):
        encoded=json.dumps({kind:payload}).encode()
        pipe.write(struct.pack('<I',len(encoded))+encoded)
    send('OpenSession',dict(session=91822,app='wordtrail-install-check.exe',protocol=7))
    header=pipe.read(4);assert len(header)==4
    size=struct.unpack('<I',header)[0];assert size<65536
    body=b''
    while len(body)<size:
        data=pipe.read(size-len(body));assert data;body+=data
    assert json.loads(body)['SessionOpened']['session']==91822
    send('CloseSession',dict(session=91822))
    checks.append('installed server answers protocol 7 without typing into a user app')
report=dict(passed=checks,installation=str(INSTALL))
(ROOT/'build/desktop-installed-tests.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(report,ensure_ascii=False,indent=2))
