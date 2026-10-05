"""Pinned offline ASR resources; runtime never downloads or uploads anything."""
import hashlib,json,shutil,urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
SOURCE='https://huggingface.co/csukuangfj/sherpa-onnx-sense-voice-zh-en-ja-ko-yue-2024-07-17/resolve/2365baeacb507f821a0c8120fcee3d484dba7a07/'
FILES={'model.int8.onnx':(239233841,'c71f0ce00bec95b07744e116345e33d8cbbe08cef896382cf907bf4b51a2cd51'),'tokens.txt':(315894,'f449eb28dc567533d7fa59be34e2abca8784f771850c78a47fb731a31429a1dc')}
VAD_SOURCE='https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/silero_vad.onnx'
FILES['silero_vad.onnx']=(643854,'9e2449e1087496d8d4caba907f23e0bd3f78d91fa552479bb9c23ac09cbb1fd6')
def digest(path):
    with path.open('rb') as f:return hashlib.file_digest(f,'sha256').hexdigest()
def main():
    cache=ROOT/'build/voice-model';cache.mkdir(parents=True,exist_ok=True)
    assets=ROOT/'android/app/src/main/assets/voice';assets.mkdir(parents=True,exist_ok=True)
    for name,(size,sha) in FILES.items():
        file=cache/name
        if not file.is_file() or file.stat().st_size!=size or digest(file)!=sha:
            temporary=cache/(name+'.download')
            urllib.request.urlretrieve(VAD_SOURCE if name=='silero_vad.onnx' else SOURCE+name,temporary)
            assert temporary.stat().st_size==size and digest(temporary)==sha,name+' checksum mismatch'
            temporary.replace(file)
        output=assets/name
        if not output.exists() or output.stat().st_size!=size or output.stat().st_mtime!=file.stat().st_mtime:shutil.copy2(file,output)
    sdk=ROOT/'third-party/sherpa-onnx'
    manifest=json.loads((sdk/'provenance.json').read_text(encoding='utf-8'))
    for abi in ['arm64-v8a','x86_64']:
        destination=ROOT/'android/app/src/main/jniLibs'/abi;destination.mkdir(parents=True,exist_ok=True)
        for name in ['libonnxruntime.so','libsherpa-onnx-c-api.so']:
            key='jniLibs/'+abi+'/'+name;file=sdk/key
            assert digest(file)==manifest['files'][key]['sha256'],key+' checksum mismatch'
            shutil.copy2(file,destination/name)
    print('Offline speech: pinned SenseVoice int8 model + sherpa-onnx 1.13.8 prepared.')
if __name__=='__main__':main()
