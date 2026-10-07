"""Prepare the 0.1.30 release test report and attach focused test evidence."""
from __future__ import annotations

import hashlib
import json
import re
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / "build"
EVIDENCE = ROOT / "docs" / "evidence"
WINDOWS_PACKAGE = Path("D:/soft/英语输入法/电脑版四六级补词补丁")


def sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def main() -> None:
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    evidence_sources = {
        "0.1.30-android-ui-tests.json": BUILD / "android-ui-tests.json",
        "0.1.30-vocabulary-ui-tests.json": BUILD / "exam-vocabulary-ui-tests.json",
        "0.1.30-offline-speech-tests.json": BUILD / "local-speech-ui-tests.json",
        "0.1.30-windows-ipc-tests.json": BUILD / "desktop-tests.json",
        "0.1.30-rust-tests.log": BUILD / "final-rust-tests.log",
    }
    for name, source in evidence_sources.items():
        if not source.is_file():
            raise FileNotFoundError(source)
        shutil.copy2(source, EVIDENCE / name)

    apk = ROOT / "dist" / "wordtrail-0.1.30-debug.apk"
    dictionary = ROOT / "data" / "generated" / "dict.qj"
    windows_manifest = read_json(WINDOWS_PACKAGE / "SHA256.json")
    android_ui = read_json(BUILD / "android-ui-tests.json")
    vocabulary_ui = read_json(BUILD / "exam-vocabulary-ui-tests.json")
    speech = read_json(BUILD / "local-speech-ui-tests.json")
    desktop = read_json(BUILD / "desktop-tests.json")
    rust_log = (BUILD / "final-rust-tests.log").read_text(encoding="utf-8")
    rust_counts = [int(value) for value in re.findall(r"test result: ok\. (\d+) passed;", rust_log) if int(value)]
    if sorted(rust_counts) != [3, 10, 42]:
        raise AssertionError(f"Unexpected Rust test groups: {rust_counts}")
    if len(android_ui["passed"]) != 18 or len(vocabulary_ui["passed"]) != 13 or len(speech["passed"]) != 15:
        raise AssertionError("Android test counts changed; review the test evidence before reporting.")
    if len(desktop["passed"]) != 401:
        raise AssertionError("Desktop IPC test count changed; review the test evidence before reporting.")

    exe = windows_manifest["artifacts"]["qingjian-server.exe"]
    win_dict = windows_manifest["artifacts"]["dict.qj"]
    ipa = windows_manifest["artifacts"]["pronunciation-en.qj"]
    report = f"""# 词伴 0.1.30 / Windows 补丁 0.1.23 测试报告

测试日期：2026-10-07。Windows 补丁面向已安装青简 Windows 0.1.4 的用户；iOS 源码未在 Mac/Xcode 上编译或真机验证。

## 词库范围

本次收录批次30–37：新增265组中英对应、50个此前未有的英文词头，并补充计算机、商务、医学、行政学、教育和心理学目标标签。六类考试目标支持多选；命中目标时优先展示对应英文译词，中文候选顺序不变，其他译词仍保留。社区词单标签不等于官方完整考纲，也不代表专业领域覆盖率。

本地运行词库含94,254条拼音词条；运行词库 SHA-256 为 `{sha256(dictionary)}`。完整来源快照、许可、逐项复核、构建器及审计清单随源码包提供。

## 验证结果

- Rust：`wordtrail-vocabulary` 42 项、`wordtrail-mobile` 3 项、`wordtrail-windows-server` 10 项，均通过。
- Android 15 模拟器（x86_64）：常规输入/候选/音标/多语言/主题及崩溃检查18项；词汇目标与批次37标签检查13项；本机离线语音权限、取消、静音、敏感编辑框和超时检查15项，均通过。
- Windows 真实候选窗口与 IPC：401 项通过，包含词库目标热加载、考试译词排序、原译词保留及上屏行为。
- Android APK：versionCode 31，大小 {apk.stat().st_size:,} 字节，SHA-256 `{sha256(apk)}`；包含 arm64-v8a 与 x86_64；APK v2/v3 签名验证及16 KB ZIP 对齐验证通过。APK 权限检查未发现 `INTERNET` 权限。
- Windows 补丁词库：服务程序 `{exe['bytes']:,}` 字节，SHA-256 `{exe['sha256']}`；IPA 数据 SHA-256 `{ipa['sha256']}`；派生词库 `{win_dict['bytes']:,}` 字节，SHA-256 `{win_dict['sha256']}`。安装器会先校验并备份旧文件，可用回滚脚本恢复。

本报告对应的机器可读测试记录位于 `docs/evidence/0.1.30-*`。模拟器测试不能替代不同品牌实体设备的覆盖；Windows 补丁未获青简官方签名，安装需要管理员授权。
"""
    (ROOT / "docs" / "0.1.30测试报告.md").write_text(report, encoding="utf-8")

    readme_path = ROOT / "README.md"
    readme = readme_path.read_text(encoding="utf-8")
    replacements = {
        "批次30–37尚未打包或安装；共享词库 Rust 测试仍需在最终构建阶段运行。": "批次30–37已纳入 v0.1.30 Android 安装包与 Windows 0.1.23 补丁，Rust 与两端回归测试均已通过。",
        "Windows 依照你的安排尚未安装。": "",
        "这些共享源码批次尚未打包发布；Windows 电脑版仍按安排暂不安装。": "这些共享词库批次已纳入 v0.1.30 发布源码与 Windows 0.1.23 补丁。",
        "docs/0.1.23测试报告.md": "docs/0.1.30测试报告.md",
        "C:\\Downloads\\wordtrail-0.1.23-source.zip": "C:\\Downloads\\wordtrail-0.1.30-source.zip",
    }
    for old, new in replacements.items():
        if old not in readme:
            raise AssertionError(f"Expected README text not found: {old}")
        readme = readme.replace(old, new)
    readme_path.write_text(readme, encoding="utf-8")
    print(json.dumps({
        "report": "docs/0.1.30测试报告.md",
        "evidence_files": list(evidence_sources),
        "rust_test_groups": rust_counts,
        "android_checks": len(android_ui["passed"]) + len(vocabulary_ui["passed"]) + len(speech["passed"]),
        "desktop_ipc_checks": len(desktop["passed"]),
        "apk_sha256": sha256(apk),
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
