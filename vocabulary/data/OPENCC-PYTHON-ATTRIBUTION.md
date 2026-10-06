# OpenCC Python build dependency

The reproducible exam-list audit uses `opencc-python-reimplemented` 0.1.7 to
convert CC-CEDICT traditional forms to simplified forms while matching
existing Chinese glosses. It is a build-time helper only; its code and lookup
tables are not bundled in Wordtrail runtime packages.

- Author/project: Yichen Huang, [opencc-python](https://github.com/yichen0831/opencc-python)
- Fixed wheel: [opencc_python_reimplemented-0.1.7-py2.py3-none-any.whl](https://pypi.org/project/opencc-python-reimplemented/0.1.7/)
- Wheel SHA-256: `41b3b92943c7bed291f448e9c7fad4b577c8c2eae30fcfe5a74edf8818493aa6`
- License: Apache-2.0; the wheel's license text is retained in [`OPENCC-PYTHON-LICENSE.txt`](OPENCC-PYTHON-LICENSE.txt).
- Notice: [`OPENCC-PYTHON-NOTICE.txt`](OPENCC-PYTHON-NOTICE.txt)

Restore the verified wheel into the ignored build directory with
`python scripts/bootstrap_vocab_tools.py`.
