#!/usr/bin/env bash
set -euo pipefail
if [[ "$(uname -s)" != "Darwin" ]]; then
  echo "iOS 构建需要 macOS、Xcode 与 XcodeGen。" >&2
  exit 1
fi
cd "$(dirname "$0")/.."
command -v xcodegen >/dev/null || { echo "请先安装 XcodeGen（brew install xcodegen）。" >&2; exit 1; }
python3 scripts/prepare_data.py
rustup target add aarch64-apple-ios aarch64-apple-ios-sim x86_64-apple-ios
for target in aarch64-apple-ios aarch64-apple-ios-sim x86_64-apple-ios; do
  cargo build --locked --release -p wordtrail-mobile --target "$target"
done
mkdir -p build/ios ios/Frameworks
lipo -create target/aarch64-apple-ios-sim/release/libwordtrail_mobile.a target/x86_64-apple-ios/release/libwordtrail_mobile.a -output build/ios/libwordtrail_mobile.a
# xcodebuild 不覆盖现有框架；保留旧产物供对比，避免递归删除。
if [[ -e ios/Frameworks/WordtrailCore.xcframework ]]; then
  mv ios/Frameworks/WordtrailCore.xcframework "ios/Frameworks/WordtrailCore.$(date +%s).xcframework"
fi
xcodebuild -create-xcframework \
  -library target/aarch64-apple-ios/release/libwordtrail_mobile.a -headers native/include \
  -library build/ios/libwordtrail_mobile.a -headers native/include \
  -output ios/Frameworks/WordtrailCore.xcframework
(cd ios && xcodegen generate)
xcodebuild -project ios/Wordtrail.xcodeproj -scheme Wordtrail -sdk iphonesimulator -configuration Debug CODE_SIGNING_ALLOWED=NO build
echo "模拟器编译通过。真机安装请在 Xcode 中为主应用和键盘扩展设置 Signing Team。"
