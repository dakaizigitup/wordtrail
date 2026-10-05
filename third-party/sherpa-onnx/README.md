# Pinned Android offline ASR runtime

- sherpa-onnx: v1.13.8, Apache-2.0. Source: https://github.com/k2-fsa/sherpa-onnx/tree/v1.13.8
- Official Android SDK: https://github.com/k2-fsa/sherpa-onnx/releases/download/v1.13.8/sherpa-onnx-v1.13.8-android.tar.bz2
- The SDK's ONNX Runtime shared library reports version 1.28.2. MIT license and its ThirdPartyNotices are included here.
- `provenance.json` records SHA-256 and length for the downloaded SDK libraries. The APK uses only `libonnxruntime.so` and `libsherpa-onnx-c-api.so` for arm64-v8a / x86_64. The upstream JNI and C++ API libraries are unused.
- `c-api.h`, `c-api.cc` and `sense-voice-c-api.c` are pinned upstream source/reference files. Our JNI wrapper is `android/voice/local_voice.cpp`; build commands are in `scripts/build_android.ps1`.
- All packaged native ELF load segments and the APK's uncompressed libraries are aligned for 16 KB pages.

Model: sherpa-onnx SenseVoiceSmall int8 conversion from 2024-07-17. Exact source URLs, sizes and SHA-256 are pinned in `scripts/prepare_voice.py`. Weights are generated build assets, excluded from the source archive, and included in the delivered APK. Source builds fetch and verify the original files. Model license and the upstream SenseVoice code license are retained separately; they are not described as GPL.

No recording is downloaded, uploaded or written to disk. The application has no INTERNET permission. Test WAV files and instrumentation classes are excluded from the delivered APK.
