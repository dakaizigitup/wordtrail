# GitHub 仓库与发布

维护仓库：`https://github.com/dakaizigitup/wordtrail`。
维护版本为 v0.1.13：Android 0.1.13、Windows 增强补丁 0.1.5（适用于青简官方 0.1.4）和未经编译验证的 iOS 源码。各发布附件与校验和见对应 GitHub Release。

## 日常开发

本机项目目录就是工作仓库。修改后先核对 `git diff`，提交源码和文档，不提交私钥、令牌、SDK、模型、备份、录音或 APK。大型数据和固定第三方依赖可通过 `scripts/bootstrap_dependencies.py` 从对应完整源码恢复，日常功能修改不需要重新下载。

每次发布在 README、CHANGELOG 和平台构建脚本中填写真实版本，完成适合该改动的验证；不要重复引用旧报告作为新版本测试结果。

## 组装发布附件

1. 编译并验证 Android APK；Windows 有改动时另行编译、验证补丁。
2. 运行 `python scripts/package_source.py`，生成包括固定依赖、数据和许可的完整对应源码。
3. 运行 `python scripts/prepare_github_release.py --version 0.1.13`，在 `dist/github-release/` 准备 APK、Windows 补丁 ZIP、源码 ZIP 和 `SHA256SUMS.txt`。
4. 用 Git 提交、推送源码，创建对应标签，通过 GitHub Releases 上传上述四个附件，并核对远程文件数量、大小和校验和。

发布说明明确各平台版本和安装前提。Windows 补丁需要先安装官方青简 0.1.4；它不是独立的全新 Windows 安装器。iOS 尚无 IPA。

同一签名的 APK 可覆盖安装，发布应沿用已存在的私有 keystore。新电脑构建出的其他签名 APK 不能被误当成保留数据的覆盖升级包，私钥始终不随源码发布。

本机交付位置默认仍为 `D:\soft\英语输入法\手机版`；公开下载通过 Releases，普通使用者不需要下载源码或手动配置开发环境。
