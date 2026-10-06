"""Apply checksum-pinned Wordtrail changes to the fixed Qingjian submodule.

Unrecognized local edits are never overwritten. --restore reverses only the
exact managed changes, for keeping the upstream checkout clean after building.
"""
from pathlib import Path
import argparse, hashlib, json

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--restore',action='store_true')
    args=parser.parse_args()
    manifest=json.loads((ROOT/'upstream/patches.json').read_text(encoding='utf-8'))
    pending=[]
    for item in manifest['files']:
        path=(ROOT/'vendor/qingjian'/item['path']).resolve()
        if not path.is_relative_to((ROOT/'vendor/qingjian').resolve()):raise ValueError('Invalid patch path')
        raw=path.read_bytes();sha=hashlib.sha256(raw.replace(b'\r\n',b'\n')).hexdigest()
        wanted=item['original_sha256'] if args.restore else item['patched_sha256']
        if sha==wanted:continue
        expected=item['patched_sha256'] if args.restore else item['original_sha256']
        if sha!=expected:raise ValueError('Unrecognized upstream edit: '+item['path'])
        newline='\r\n' if b'\r\n' in raw else '\n'
        text=raw.decode('utf-8').replace('\r\n','\n')
        for change in reversed(item['replacements']) if args.restore else item['replacements']:
            before,after=(change['after'],change['before']) if args.restore else (change['before'],change['after'])
            if text.count(before)!=1:raise ValueError('Patch context mismatch: '+item['path'])
            text=text.replace(before,after,1)
        payload=text.replace('\n',newline).encode('utf-8')
        if hashlib.sha256(payload.replace(b'\r\n',b'\n')).hexdigest()!=wanted:raise ValueError('Patched checksum mismatch')
        pending.append((path,payload))
    for path,payload in pending:path.write_bytes(payload)
    print(('Restored' if args.restore else 'Prepared')+' Wordtrail upstream compatibility patch')

if __name__=='__main__':main()
