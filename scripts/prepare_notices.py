"""保留软件和数据的署名、许可全文；把同一文本放入安卓与 iOS 资源。"""
from pathlib import Path
import csv, json, shutil

ROOT = Path(__file__).resolve().parents[1]
def write_notice(path, text):
    normalized='\n'.join(line.rstrip(' \t\r') for line in text.splitlines())+'\n'
    path.write_text(normalized,encoding='utf-8',newline='\n')

HEADER = """词伴输入法 / Wordtrail 0.1.23
独立移动实验版，非青简官方产品。

新增移动层代码：GPL-3.0-or-later，详见下面 GPL 全文。
青简内核：https://github.com/qingjian-team/qingjian
版本 v0.1.4；提交 f7abaefcb1a3aeaca5c01692941a64a7b1f43eb5。
青简名称和 logo 不在代码授权范围，本应用未使用其品牌资产。

对应源码随交付包 wordtrail-0.1.23-source.zip 提供，包括移动层、
固定上游、构建脚本、Cargo.lock 和第三方 Rust 源码。

随包数据来自青简官方 v0.1.4 安装包：dict.qj、glossary-en/ja/es.qj。
词库来源：通用规范汉字表、现代汉语常用词表（liuxilu 校对版）、
THUOCL（清华大学自然语言处理实验室，MIT），读音取自 Unihan
（Unicode License v3）。上游说明指出字表与常用词表的转录仓库
未附许可证；不能把这些数据统称为 GPL。完整来源记录见上游
docs/design/landscape.md 和 assets/lexicon。
释义由青简利用大语言模型离线生成，不是联网词典抓取。
本版未打包桌面语言模型或 emoji 数据；英语标签和译词扩充分别列明来源。

英语词汇参考等级：CEFR A1–C2，8,845 个词，嵌入共享本机引擎。
A1–B2：The CEFR-J Wordlist Version 1.5，Yukio Tono（Tokyo University
of Foreign Studies），http://www.cefr-j.org/download.html；研究与商业用途免费，须署名。
C1/C2：Octanove Vocabulary Profile C1/C2 1.0，CC BY-SA 4.0，
https://github.com/openlanguageprofiles/olp-en-cefrj；许可：
https://creativecommons.org/licenses/by-sa/4.0/ 。
保留上游等级表和来源说明于 vendor/qingjian/assets/levels；未更改等级数据。
同一拼写多个词性取词表最低等级；未收录不推断。非六级或雅思专项词表。

独立英语音标库：open-dict-data/ipa-dict。
固定提交 43c3570eb3553bdd19fccd2bd0091534889af023。
英式 RP 数据来源 leoboiko/ipacards，GPL-3.0-only；
美式 GA 数据来源 lingz/cmudict-ipa，MIT。
保留全部上游发音变体；缺词时不猜测发音；不包含音频。
原始数据、校验清单、来源说明和许可原文见 pronunciation/source。

第三方 Rust 依赖保留各自许可。以下包含依赖声明及可用的许可原文。
"""

def main():
    parts = [HEADER, "\n英语考试标签：ECDICT（MIT）及 KyleBing/english-vocabulary（BSD-3-Clause）。\n固定提交、输入文件 SHA-256、去重统计见 vocabulary/data/manifest.json。\n标签索引仅提取词条及收录标签。新增英文译词从 ECDICT 与 KyleBing 提取短中文词义对应，\n不复制例句或音频；构建时用 WordNet 3.0 拼写与同义关系校验，运行时不加载 WordNet。\n繁简转换构建辅助工具 opencc-python-reimplemented 0.1.7（Apache-2.0）只用于审计脚本，\n不进入运行程序；固定 wheel SHA-256、署名及许可见 vocabulary/data/OPENCC-PYTHON-ATTRIBUTION.md。\n扩词输入校验、数量及人工补充见 vocabulary/data/expansion-manifest.json。标签不代表难度或官方完整考试范围。\n0.1.20 专四、专八、托福、雅思派生数据分别保存在 exam-target-ecdict-expansion.tsv 与\nexam-target-kylebing-expansion.tsv；逐词来源、固定提交、许可和筛选边界见\nvocabulary/data/EXAM-TARGETS-ATTRIBUTION.md、batches/09-exam-target-reviewed.tsv 与 exam-target-manifest.json。\n本批为自动交叉筛选，未逐条人工审校；完整来源词表不随包重分发。\n"]
    parts.append("\n=== 专四、专八、托福、雅思考试词汇补充批次 11–13 ===\n"
                 "batch 11 新增 1,592 组整词映射，来源文件按许可证分开保存：ECDICT MIT、KyleBing BSD-3-Clause、\n"
                 "二者共同命中、Chinese Open Wordnet、KOReader CC BY-SA 4.0 及含 KOReader/COW 双来源的独立文件。\n"
                 "KOReader 来源为 DanielGregorini/koreader-dicts en-zh v1.2.0，归档 SHA-256：\n"
                 "910d8fc3bf054f7a36f5db134f0624619711e5b414ebf7de45a3c0e04e98232c；随包保留其 LICENSE 与 ATTRIBUTION。\n"
                 "Chinese Open Wordnet 固定提交 406bf83b3c507a3d1f26e88252d5d66893fd36bf，许可全文见\n"
                 "vocabulary/data/CHINESE-OPEN-WORDNET-LICENSE.txt。CC-CEDICT 与 FMLD 派生行单独按 CC BY-SA 4.0 署名。\n"
                 "batch 12 新增 699 组带词性 ECDICT 完整短义，其中专四64、专八308、托福438、雅思112；\n"
                 "类别有交集。拼音 overlay 每行保留 CC-CEDICT/Rime ICE 来源，新增频率为0，不改变青简已有候选顺序。\n"
                 "Rime ICE 固定提交 da1fbe602e38f26db846fa10120ee64c2b0324c0；GPL-3.0 全文见\n"
                 "vocabulary/data/RIME-ICE-LICENSE.txt。自动筛选说明、逐词来源、SHA-256 与覆盖口径见\n"
                 "vocabulary/data/EXAM-TARGETS-ATTRIBUTION.md、batches/11-exam-target-reviewed.tsv、\n"
                 "exam-target-batch-11-manifest.json、batches/12-ecdict-new-pinyin-reviewed.tsv 与\n"
                 "exam-target-batch-12-manifest.json；均未声称对每条新记录完成逐词人工审校。\n"
                 "批次12的映射覆盖率仍为97.56%/95.85%/90.81%/96.20%。复核可达率时补计了新拼音键\n"
                 "解锁的原词库及既有扩展释义，批次12修正后的六类拼音可触达率\n"
                 "（四级/六级/专四/专八/托福/雅思）为95.62%/94.38%/94.35%/92.19%/86.55%/92.68%。\n"
                 "批次13只补中文拼音入口，不新增中英释义：从已存在的考试译词中文面中选入407个新拼音键，\n"
                 "托福拼音可触达率达到90.01%。全部读音由固定 CC-CEDICT/Rime ICE 精确词条唯一解析；\n"
                 "其中1条仅有 CC-CEDICT 记录、244条仅有 Rime ICE 记录、162条由两边独立确认且完全一致。\n"
                 "歧义或来源冲突的候选不收录。三项拼音数据均保留逐行来源、散列和许可证。\n"
                 "逐词决策、统计和来源散列见 batches/13-exam-pinyin-reachability.tsv\n"
                 "及 exam-target-batch-13-manifest.json。批次11–13均未声称自动筛选数据已逐条人工审校。\n")
    open_rows = []
    with (ROOT/'vocabulary/data/batches/10-openetymology-reviewed.tsv').open(encoding='utf-8', newline='') as stream:
        open_rows = list(csv.DictReader(stream, delimiter='\t'))
    parts.append(f"\n=== OpenEtymology 专八/托福名单及译词补充（{len(open_rows)} 组）===\n")
    parts.append("署名：openetymology/OpenEtymology contributors；固定提交 "
                 "7d89f3697abf26e305fe2627f181b692c2c10b28。TEM8 与 TOEFL 公布词表声明 CC BY-SA 4.0；"
                 "本项目只提取小写词头与名单成员关系，不复制上游释义、例句、词源或音频。\n"
                 "新增 136 组映射由固定 ECDICT 与 KyleBing 提供一致词义/词性的字典证据，并人工核对后保留；"
                 "名单筛选映射表与派生名单索引按 CC BY-SA 4.0 提供。完整来源修订、散列及修改说明见 "
                 "vocabulary/data/OPENETYMOLOGY-DATA-ATTRIBUTION.md、openetymology-tags-manifest.json、"
                 "openetymology-expansion-manifest.json 与 batches/10-openetymology-reviewed.tsv。\n")
    for row in open_rows:
        parts.append(f"{row['word']} ({row['pos']}) -> {row['chinese']}; target: {row['targets']}\n")
    wiktionary_rows = []
    for filename in ('03-wiktionary-reviewed.tsv', '06-wiktionary-zh-reviewed.tsv'):
        with (ROOT/'vocabulary/data/batches'/filename).open(encoding='utf-8', newline='') as stream:
            wiktionary_rows.extend(csv.DictReader(stream, delimiter='\t'))
    parts.append(f"\n=== Wiktionary 词汇补充（{len(wiktionary_rows)} 组，CC BY-SA 4.0）===\n")
    parts.append("署名：English Wiktionary contributors；https://en.wiktionary.org/ 。\n许可：https://creativecommons.org/licenses/by-sa/4.0/ 。修改：从固定修订的英汉翻译义项及汉语词条释义中选择与词性/义项相符、且可由本机拼音候选输入的考试词，整理为精简中英词条。第二批候选发现使用固定 Kaikki 派生快照，校验散列与许可边界见 vocabulary/data/wiktionary-manifest-2.json 和 WIKTIONARY-ATTRIBUTION.md。\n以下列出各原始词条和修订版本；完整审校记录随 wordtrail-0.1.21-source.zip 的 vocabulary/data/batches/03-wiktionary-reviewed.tsv 与 06-wiktionary-zh-reviewed.tsv 提供。\n")
    for row in wiktionary_rows:
        parts.append(f"{row['english']} ({row['pos']}) -> {row['chinese']}; {row['source_url']}\n")
    cedict_rows = []
    for batch in ('04-cc-cedict-reviewed.tsv', '05-cc-cedict-reviewed.tsv', '07-cc-cedict-reviewed.tsv', '08-cc-cedict-reviewed.tsv'):
        with (ROOT/'vocabulary/data/batches'/batch).open(encoding='utf-8', newline='') as stream:
            cedict_rows.extend(csv.DictReader(stream, delimiter='\t'))
    parts.append("\n=== CC-CEDICT 词汇补充（独立 CC BY-SA 4.0 数据）===\n")
    parts.append(f"署名：MDBG 与 CC-CEDICT contributors；https://cc-cedict.org/editor/editor.php?handler=Download 。许可：CC BY-SA 4.0，https://creativecommons.org/licenses/by-sa/4.0/ 。采用 TeaPearce/chinese-english-dictionary 固定提交 a9aea223269eb9820590e5bca783eb299c317439 中的 2026-06 CC-CEDICT 文本镜像；原始文件 SHA-256：8172061b2a647dd8a179788830ef233944baee479bc7018f111064ad16d8f46f。修改：从中文到英文的整词释义中筛选四六级词，人工核对义项；补充本地拼音键与考试标签，并用 ECDICT（MIT）交叉检查词性。CC-CEDICT 不提供词性。本源码包分批交付 {len(cedict_rows)} 条精简对应，不分发完整词典。运行词条及本表中的 CC-CEDICT 派生部分按 CC BY-SA 4.0 提供；POS 交叉核对来源与完整记录见随包 vocabulary/data/CC-CEDICT-ATTRIBUTION.md、vocabulary/data/batches/04-cc-cedict-reviewed.tsv、vocabulary/data/batches/05-cc-cedict-reviewed.tsv、vocabulary/data/batches/07-cc-cedict-reviewed.tsv、vocabulary/data/batches/07-cc-cedict-review-input.tsv、vocabulary/data/batches/08-cc-cedict-reviewed.tsv、vocabulary/data/batches/08-cc-cedict-review-input.tsv、vocabulary/data/batches/08-cc-cedict-candidate-decisions.tsv 及四份 cccedict-manifest。\n")
    for row in cedict_rows:
        parts.append(f"{row['word']} ({row['pos']}) -> {row['chinese']}; CC-CEDICT line {row['source_line']}; {row['source_url']}\n")
    for name in ['ECDICT-LICENSE','KyleBing-LICENSE','OPENETYMOLOGY-DATA-LICENSE.txt','WordNet-LICENSE',
                 'OPENCC-PYTHON-LICENSE.txt','OPENCC-PYTHON-NOTICE.txt',
                 'CHINESE-OPEN-WORDNET-LICENSE.txt','KOReader-LICENSE.txt','KOReader-ATTRIBUTION.txt',
                 'RIME-ICE-LICENSE.txt']:
        file=ROOT/'vocabulary/data'/name
        parts.append(f'\n=== {file.relative_to(ROOT)} ===\n'+file.read_text(encoding='utf-8'))
    fixed = [ROOT/'LICENSE', ROOT/'vendor/qingjian/assets/lexicon/00_meta/THUOCL_LICENSE.txt', ROOT/'vendor/qingjian/assets/emoji/LICENSE-unicode.txt', ROOT/'pronunciation/source/LICENSE', ROOT/'pronunciation/source/ipacards-LICENSE', ROOT/'pronunciation/source/cmudict-ipa-LICENSE']
    for file in fixed:
        parts.append(f'\n\n=== {file.relative_to(ROOT)} ===\n'+file.read_text(encoding='utf-8'))
    metadata = json.loads((ROOT/'build/cargo-metadata.json').read_text(encoding='utf-8-sig'))
    packages={p['id']:p for p in metadata['packages']}
    nodes={n['id']:n for n in metadata['resolve']['nodes']}
    mobile={p['id'] for p in metadata['packages'] if p['name'] in {'wordtrail-mobile','wordtrail-pronunciation','wordtrail-vocabulary'}}
    pending=list(mobile)
    while pending:
        for dependency in nodes[pending.pop()]['dependencies']:
            if dependency not in mobile:mobile.add(dependency);pending.append(dependency)
    desktop_parts=["Windows 音标与考试词汇补丁 0.1.16：用于现有青简 0.1.4 安装。\n非官方发布；不分发青简品牌图标。保持已安装官方资源。\n对应源码在 wordtrail-0.1.23-source.zip，包含 desktop/、vocabulary/ 与独立音标库。\n"]+list(parts)
    for package in sorted(metadata['packages'],key=lambda p:(p['name'],p['version'])):
        if package.get('source') is None: continue
        current=[f"\n\n=== {package['name']} {package['version']} ===\n许可：{package.get('license') or '见源文件'}\n仓库：{package.get('repository') or ''}\n"]
        folder = Path(package['manifest_path']).parent
        texts = set()
        for file in sorted(folder.iterdir()):
            if not file.is_file() or not file.name.upper().startswith(('LICENSE','COPYING','NOTICE')): continue
            value = file.read_text(encoding='utf-8',errors='replace')
            if value not in texts: current.append(f'\n{file.name}\n{value}'); texts.add(value)
        desktop_parts.extend(current)
        if package['id'] in mobile:parts.extend(current)
    notice = '\n'.join(parts)
    voice_parts=['\n\n=== 安卓独立离线语音 ===\nsherpa-onnx 1.13.8（Apache-2.0）及 ONNX Runtime（MIT）。\n模型：SenseVoiceSmall，20240717 sherpa int8 转换，模型许可见下文。\n模型来源及固定 SHA-256 见 scripts/prepare_voice.py；代码及二进制来源见 third-party/sherpa-onnx。\n录音仅在内存中处理，不上传或保存。\n']
    voice_parts.append('Silero VAD：MIT；https://github.com/snakers4/silero-vad 。仅检测有效人声，模型来源和校验见 scripts/prepare_voice.py。\n')
    for name in ['LICENSE','ONNXRUNTIME-LICENSE','ONNXRUNTIME-ThirdPartyNotices.txt','SENSEVOICE-LICENSE','FUNASR-MODEL-LICENSE','SILERO-VAD-LICENSE']:
        file=ROOT/'third-party/sherpa-onnx'/name
        voice_parts.append(f'\n=== {file.relative_to(ROOT)} ===\n'+file.read_text(encoding='utf-8'))
    voice_notice='\n'.join(voice_parts)
    write_notice(ROOT/'desktop/NOTICE.txt','\n'.join(desktop_parts))
    write_notice(ROOT/'NOTICE.txt',notice+voice_notice)
    for folder in (ROOT/'android/app/src/main/assets',ROOT/'ios/App'):
        folder.mkdir(parents=True,exist_ok=True)
        write_notice(folder/'NOTICE.txt',notice+(voice_notice if 'android' in folder.parts else ''))
    print(f'Notices generated: {len(notice)} characters')

if __name__ == '__main__': main()
