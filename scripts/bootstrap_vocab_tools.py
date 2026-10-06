"""Restore the hash-pinned, build-only OpenCC Python dependency."""
from __future__ import annotations

import hashlib
import io
import urllib.request
import zipfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "build/vocab-tools"
URL = "https://files.pythonhosted.org/packages/py2.py3/o/opencc-python-reimplemented/opencc_python_reimplemented-0.1.7-py2.py3-none-any.whl"
SHA256 = "41b3b92943c7bed291f448e9c7fad4b577c8c2eae30fcfe5a74edf8818493aa6"


def main() -> None:
    request = urllib.request.Request(URL, headers={"User-Agent": "Wordtrail-build"})
    with urllib.request.urlopen(request, timeout=60) as response:
        payload = response.read()
    if hashlib.sha256(payload).hexdigest() != SHA256:
        raise SystemExit("OpenCC build wheel SHA-256 mismatch")

    DEST.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(io.BytesIO(payload)) as wheel:
        for entry in wheel.infolist():
            if entry.is_dir():
                continue
            relative = PurePosixPath(entry.filename)
            if relative.is_absolute() or ".." in relative.parts or "\\" in entry.filename:
                raise ValueError("Unsafe wheel member: " + entry.filename)
            target = (DEST / Path(*relative.parts)).resolve()
            if not target.is_relative_to(DEST.resolve()):
                raise ValueError("Wheel member outside build directory")
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(wheel.read(entry))
    print(f"Restored OpenCC Python 0.1.7 to {DEST}; wheel SHA-256 verified.")


if __name__ == "__main__":
    main()
