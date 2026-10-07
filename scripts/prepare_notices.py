"""保留软件和数据的署名、许可全文；把同一文本放入安卓与 iOS 资源。"""
from pathlib import Path
import csv, json, shutil

ROOT = Path(__file__).resolve().parents[1]
def write_notice(path, text):
    normalized='\n'.join(line.rstrip(' \t\r') for line in text.splitlines())+'\n'
    path.write_text(normalized,encoding='utf-8',newline='\n')

HEADER = """词伴输入法 / Wordtrail 0.1.29
独立移动实验版，非青简官方产品。

新增移动层代码：GPL-3.0-or-later，详见下面 GPL 全文。
青简内核：https://github.com/qingjian-team/qingjian
版本 v0.1.4；提交 f7abaefcb1a3aeaca5c01692941a64a7b1f43eb5。
青简名称和 logo 不在代码授权范围，本应用未使用其品牌资产。

对应源码随交付包 wordtrail-0.1.29-source.zip 提供，包括移动层、
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
    cet_manifest = json.loads((ROOT/'vocabulary/data/openetymology-cet-manifest.json').read_text(encoding='utf-8'))
    cet_rows = []
    with (ROOT/'vocabulary/data/batches/29-openetymology-cet-reviewed.tsv').open(encoding='utf-8', newline='') as stream:
        cet_rows = list(csv.DictReader(stream, delimiter='\t'))
    parts.append("\n=== OpenEtymology CET4/CET6 补充（批次29；CC BY-SA 4.0名单 + ECDICT MIT释义）===\n")
    parts.append(
        "署名：openetymology/OpenEtymology contributors；固定提交 "
        f"{cet_manifest['source_commit']}。CET4 与 CET6 社区词单声明 CC BY-SA 4.0；本项目仅提取规范化词头及成员关系，不复制释义、例句或词源。"
        f"从{cet_manifest['candidate_gate']['unmapped_source_headwords']}个未映射词头中筛出{cet_manifest['candidate_gate']['fully_eligible_pairs']}组同时具备ECDICT释义、本机IPA、可拼音输入键和容量的候选；"
        f"接受{cet_manifest['review']['accepted_pairs']}组映射（{cet_manifest['review']['new_english_headwords']}个新英文词头）。新增词单关系与筛选映射表按CC BY-SA 4.0署名；中文释义来源为ECDICT MIT。"
        "详情见 vocabulary/data/OPENETYMOLOGY-CET-DATA-ATTRIBUTION.md、openetymology-cet-tags-manifest.json、openetymology-cet-manifest.json 与 batches/29-openetymology-cet-reviewed.tsv。\n"
    )
    for row in cet_rows:
        parts.append(f"{row['chinese']} -> {row['word']} ({row['pos']}); decision: {row['decision']}; {row['review_note']}\n")
    wiktionary_rows = []
    for filename in ('03-wiktionary-reviewed.tsv', '06-wiktionary-zh-reviewed.tsv'):
        with (ROOT/'vocabulary/data/batches'/filename).open(encoding='utf-8', newline='') as stream:
            wiktionary_rows.extend(csv.DictReader(stream, delimiter='\t'))
    parts.append(f"\n=== Wiktionary 词汇补充（{len(wiktionary_rows)} 组，CC BY-SA 4.0）===\n")
    parts.append("署名：English Wiktionary contributors；https://en.wiktionary.org/ 。\n许可：https://creativecommons.org/licenses/by-sa/4.0/ 。修改：从固定修订的英汉翻译义项及汉语词条释义中选择与词性/义项相符、且可由本机拼音候选输入的考试词，整理为精简中英词条。第二批候选发现使用固定 Kaikki 派生快照，校验散列与许可边界见 vocabulary/data/wiktionary-manifest-2.json 和 WIKTIONARY-ATTRIBUTION.md。\n以下列出各原始词条和修订版本；完整审校记录随 wordtrail-0.1.21-source.zip 的 vocabulary/data/batches/03-wiktionary-reviewed.tsv 与 06-wiktionary-zh-reviewed.tsv 提供。\n")
    for row in wiktionary_rows:
        parts.append(f"{row['english']} ({row['pos']}) -> {row['chinese']}; {row['source_url']}\n")
    professional_rows = []
    with (ROOT/'vocabulary/data/batches/14-professional-reviewed.tsv').open(encoding='utf-8', newline='') as stream:
        professional_rows = list(csv.DictReader(stream, delimiter='\t'))
    professional_manifest = json.loads((ROOT/'vocabulary/data/professional-vocabulary-manifest.json').read_text(encoding='utf-8'))
    accepted_professional = [row for row in professional_rows if row['review_decision'] == 'accept']
    parts.append("\n=== 专业词汇领域标签及医学新增译词（批次14，CC BY-SA 4.0）===\n")
    parts.append("署名：English Wiktionary contributors；https://en.wiktionary.org/ 。候选发现数据来自 Kaikki/Wiktextract 固定中文—英文快照；上游来源、快照 SHA-256、修改说明及 CC BY-SA 4.0 链接见 vocabulary/data/professional-vocabulary-manifest.json 与 vocabulary/data/WIKTIONARY-ATTRIBUTION.md。\n"
                 "修改：按精确中文—英文词面对应筛选计算机、商务、医学主题标签；繁体中文键转为简体，只保留真实拼音候选可达的条目，不复制定义、例句或音频。新增映射另经相同词性 ECDICT 完整短义、随包 IPA、拼音键和人工审校筛选。运行标签索引有 {tagged} 个英文词面，其中计算机{computer}、商务{business}、医学{medical}；此数是固定快照的可达交集，不代表完整专业课程覆盖。\n"
                 "接受的医学映射及来源 sense ID 见 vocabulary/data/batches/14-professional-reviewed.tsv 与 14-professional-domain-evidence.tsv；所有候选的逐项接受/排除理由均保留。\n".format(
                     tagged=professional_manifest['outputs']['professional-domain-tags.tsv']['rows'],
                     computer=professional_manifest['categories'][0]['tagged_terms'],
                     business=professional_manifest['categories'][1]['tagged_terms'],
                     medical=professional_manifest['categories'][2]['tagged_terms']))
    for row in accepted_professional:
        parts.append(f"{row['chinese']} -> {row['english']} ({row['pos']}); Wiktionary snapshot entry {row['source_entry_ids']} / sense {row['source_sense_ids']}\n")
    cjk_reviewed = []
    with (ROOT/'vocabulary/data/batches/15-cjk-compsci-reviewed.tsv').open(encoding='utf-8', newline='') as stream:
        cjk_reviewed = list(csv.DictReader(stream, delimiter='\t'))
    cjk_accepted = [row for row in cjk_reviewed if row['review_decision'] == 'accept']
    cjk_manifest = json.loads((ROOT/'vocabulary/data/cjk-compsci-manifest.json').read_text(encoding='utf-8'))
    parts.append("\n=== 计算机术语第二段（批次15，CC BY-SA 4.0）===\n")
    parts.append(
        "署名：dahlia 与贡献者，[CJK computer science terms comparison](https://github.com/dahlia/cjk-compsci-terms)，"
        f"固定提交 {cjk_manifest['upstream']['commit']}。许可：CC BY-SA 4.0，"
        "https://creativecommons.org/licenses/by-sa/4.0/ 。\n"
        "修改：只筛选简体中文完整词面和本机实际拼音候选可达项；已有译词须有上游组件逐词对应证据，新映射必须有本地 IPA、ECDICT 词性、每键余量并经逐项审核。"
        "保留来源头词与组成对应，未复制定义、例句或音频。上游28份固定 YAML 与 LICENSE 随源码保留在 vocabulary/data/sources/cjk-compsci-terms/；"
        "输入和输出 SHA-256、修改说明与结果统计见 vocabulary/data/CJK-COMPSCI-ATTRIBUTION.md、cjk-compsci-manifest.json、"
        "batches/15-cjk-compsci-reviewed.tsv 和 batches/15-cjk-compsci-evidence.tsv。"
        f"候选{len(cjk_reviewed)}组，接受{len(cjk_accepted)}组，排除{len(cjk_reviewed)-len(cjk_accepted)}组。\n"
    )
    for row in cjk_accepted:
        parts.append(f"{row['chinese']} -> {row['english']} ({row['pos']}); {row['source_tables']}\n")
    fibo_reviewed = []
    with (ROOT/'vocabulary/data/batches/16-fibo-business-reviewed.tsv').open(encoding='utf-8', newline='') as stream:
        fibo_reviewed = list(csv.DictReader(stream, delimiter='\t'))
    fibo_accepted = [row for row in fibo_reviewed if row['decision'] == 'accept']
    fibo_manifest = json.loads((ROOT/'vocabulary/data/fibo-business-manifest.json').read_text(encoding='utf-8'))
    parts.append("\n=== FIBO 商务/金融标签（批次16，MIT）===\n")
    parts.append(
        "署名：EDM Council，Financial Industry Business Ontology (FIBO)，"
        f"[固定提交 {fibo_manifest['commit']}]({fibo_manifest['upstream']}/tree/{fibo_manifest['commit']})。"
        "许可：MIT，随包保留 vocabulary/data/sources/fibo/LICENSE。FIBO 是 EDM Council 的商标；本项目未使用其标志或暗示官方背书。\n"
        "修改：从固定 RDF 文件中筛选单词类标签，与现有本机拼音可达译词求交集，并人工复核是否属于商务/金融词。"
        "只新增英文词头的商务标签，不复制定义到运行索引，不新增中英映射，也不改变中文候选顺序。"
        "52 个源 RDF 文件、来源散列、修改口径及完整审校见 vocabulary/data/FIBO-ATTRIBUTION.md、"
        "fibo-business-manifest.json、batches/16-fibo-business-candidates.tsv 与 batches/16-fibo-business-reviewed.tsv。\n"
        f"候选{len(fibo_reviewed)}个，接受{len(fibo_accepted)}个，排除{len(fibo_reviewed)-len(fibo_accepted)}个；"
        f"其中{fibo_manifest['new_business_category_memberships']}个是新增商务分类成员，不是新增词条。\n"
    )
    for row in fibo_accepted:
        parts.append(f"{row['headword']} -> 商务（FIBO class label）\n")
    better_quant_reviewed = []
    with (ROOT/'vocabulary/data/batches/17-better-quant-reviewed.tsv').open(encoding='utf-8', newline='') as stream:
        better_quant_reviewed = list(csv.DictReader(stream, delimiter='\t'))
    better_quant_accepted = [row for row in better_quant_reviewed if row['decision'] == 'accept']
    with (ROOT/'vocabulary/data/batches/17-better-quant-candidates.tsv').open(encoding='utf-8', newline='') as stream:
        better_quant_candidates = list(csv.DictReader(stream, delimiter='\t'))
    better_quant_sources = {
        (row['chinese'], row['english']): row['source_url']
        for row in better_quant_candidates if row['decision'] == 'accept'
    }
    better_quant_manifest = json.loads((ROOT/'vocabulary/data/better-quant-manifest.json').read_text(encoding='utf-8'))
    parts.append("\n=== Better Quant 商业金融词汇（批次17，MIT）===\n")
    parts.append(
        "署名：Tomortec，[Better Quant Wiki](https://github.com/Tomortec/better-quant-wiki)，"
        f"固定提交 {better_quant_manifest['commit']}。许可：MIT；随包保留 vocabulary/data/sources/better-quant-wiki/LICENSE。\n"
        "修改：从固定双语量化金融术语表中筛出本机拼音可达的精确中文词面，逐项核对词义和本地 IPA；"
        "仅保留短中英映射及商务标签，不复制定义、例句或音频。运行索引仅加入7组映射和7条标签记录，"
        "不加载完整术语表。来源文件 SHA-256、审校表、全部候选及修改说明见 vocabulary/data/BETTER-QUANT-ATTRIBUTION.md、"
        "better-quant-manifest.json、batches/17-better-quant-reviewed.tsv 与 batches/17-better-quant-candidates.tsv。\n"
        f"候选{len(better_quant_reviewed)}组，接受{len(better_quant_accepted)}组，排除{len(better_quant_reviewed)-len(better_quant_accepted)}组；"
        f"其中{better_quant_manifest['new_english_headwords']}个新英文词头，{better_quant_manifest['new_business_tag_memberships']}个新增商务标签成员。\n"
    )
    for row in better_quant_accepted:
        source_url = better_quant_sources[(row['chinese'], row['english'])]
        parts.append(f"{row['chinese']} -> {row['english']} (n.); {source_url}\n")
    cfpb_manifest = json.loads((ROOT/'vocabulary/data/cfpb-finance-manifest.json').read_text(encoding='utf-8'))
    cfpb_reviewed = []
    with (ROOT/'vocabulary/data/batches/18-cfpb-finance-reviewed.tsv').open(encoding='utf-8', newline='') as stream:
        cfpb_reviewed = list(csv.DictReader(stream, delimiter='\t'))
    cfpb_accepted = []
    with (ROOT/'vocabulary/data/batches/18-cfpb-finance-candidates.tsv').open(encoding='utf-8', newline='') as stream:
        cfpb_accepted = [row for row in csv.DictReader(stream, delimiter='\t') if row['decision'] == 'accept']
    parts.append("\n=== CFPB 消费金融词汇（批次18，公共领域来源）===\n")
    parts.append(
        f"署名：Consumer Financial Protection Bureau (CFPB), March 2024，[Chinese-English glossary of financial terms]({cfpb_manifest['source_url']})。"
        "CFPB 网站政策说明其原创内容属于公共领域，除非另有标注；参见 https://www.consumerfinance.gov/privacy/website-privacy-policy/ 。\n"
        "修改：将词表中的繁体中文转换为简体，保留拼音可达且有本地 IPA 的词项，并以 ECDICT 的完整中文短义和词性交叉核验。"
        f"不复制定义、例句或长解释。审查{cfpb_manifest['candidate_mappings_with_pinyin_ipa_exact_ecdict']}组候选，接受{cfpb_manifest['accepted_new_mappings']}组映射，新增{cfpb_manifest['accepted_new_english_headwords']}个英文词头；"
        f"词表成员标签共{cfpb_manifest['cfpb_finance_tag_words']}项，其中{cfpb_manifest['new_business_tag_memberships']}项新增商务归属。"
        f"固定文本快照 SHA-256：{cfpb_manifest['source_snapshot_sha256']}。来源、处理说明、逐项审核表、候选表与数据清单见 vocabulary/data/CFPB-ATTRIBUTION.md、"
        "cfpb-finance-manifest.json、batches/18-cfpb-finance-reviewed.tsv 与 batches/18-cfpb-finance-candidates.tsv。\n")
    for row in cfpb_accepted:
        parts.append(f"{row['chinese']} -> {row['english']} ({row['pos']}); CFPB glossary line {row['source_line']}\n")
    finance_i18n_manifest = json.loads((ROOT/'vocabulary/data/finance-i18n-manifest.json').read_text(encoding='utf-8'))
    finance_i18n_accepted = []
    with (ROOT/'vocabulary/data/batches/19-finance-i18n-candidates.tsv').open(encoding='utf-8', newline='') as stream:
        finance_i18n_accepted = [row for row in csv.DictReader(stream, delimiter='\t') if row['decision'] == 'accept']
    parts.append("\n=== finance_i18n 金融与商务词汇（批次19，MIT）===\n")
    parts.append(
        f"署名：Vincent、[hotvulcan/finance_i18n]({finance_i18n_manifest['source_url']})，"
        f"固定提交 {finance_i18n_manifest['source_commit']}。上游仓库声明 MIT 许可，完整文本见 vocabulary/data/sources/finance_i18n/LICENSE。"
        "上游 README 没有注明术语表的更早来源，故只用于候选发现；新增项另以 ECDICT 精确中文义项/词性、本机拼音、IPA 和逐项审校交叉核验。"
        f"从 {finance_i18n_manifest['candidate_pairs_with_exact_ecdict_pinyin_ipa']} 组候选中接受 {finance_i18n_manifest['accepted_new_mappings']} 组映射，"
        f"新增 {finance_i18n_manifest['accepted_new_english_headwords']} 个英文词头和 {finance_i18n_manifest['new_business_tag_memberships']} 个商务标签归属。"
        f"README 固定快照 SHA-256：{finance_i18n_manifest['source_snapshot_sha256']}。仅分发精简对应，不复制定义；"
        "全部来源边界和审校理由见 vocabulary/data/FINANCE-I18N-ATTRIBUTION.md、"
        "vocabulary/data/finance-i18n-manifest.json、batches/19-finance-i18n-reviewed.tsv 与 batches/19-finance-i18n-candidates.tsv。\n"
    )
    for row in finance_i18n_accepted:
        parts.append(f"{row['chinese']} -> {row['english']} ({row['pos']}); finance_i18n README line {row['source_line']}\n")
    computerese_manifest = json.loads((ROOT/'vocabulary/data/computerese-manifest.json').read_text(encoding='utf-8'))
    computerese_reviewed = []
    with (ROOT/'vocabulary/data/batches/20-computerese-evidence.tsv').open(encoding='utf-8', newline='') as stream:
        computerese_reviewed = list(csv.DictReader(stream, delimiter='\t'))
    computerese_accepted = [row for row in computerese_reviewed if row['mapping_decision'] == 'accept']
    parts.append("\n=== 计算机术语补充批次20（MIT）===\n")
    parts.append(
        f"署名：[EarsEyesMouth/computerese-cross-references]({computerese_manifest['upstream']['repository']})，"
        f"固定提交 {computerese_manifest['upstream']['commit']}。许可：MIT，全文见 vocabulary/data/sources/computerese-cross-references/LICENSE。"
        f"上游 README SHA-256：{computerese_manifest['upstream']['readme_sha256']}。README 注明部分条目摘自书籍；本批排除带来源脚注和长解释的条目，"
        f"仅保留{computerese_manifest['filtered_source_terms']['rows']}条短词条作候选。逐项审核{computerese_manifest['candidate_pairs_with_exact_ecdict_pinyin_ipa']}组精确 ECDICT/拼音/IPA 候选，"
        f"其中{computerese_manifest['already_mapped_candidate_pairs']}组映射原已存在；新增{computerese_manifest['accepted_new_mappings']}组中英映射，"
        f"新增英文词头{computerese_manifest['accepted_new_english_headwords']}个，新增计算机标签{computerese_manifest['new_computer_tag_memberships']}项。"
        "运行数据只含精简映射及已审核标签，不含上游长解释。来源、逐项理由、候选、固定输入与散列见 vocabulary/data/COMPUTERESE-ATTRIBUTION.md、"
        "computerese-manifest.json、batches/20-computerese-reviewed.tsv 与 batches/20-computerese-evidence.tsv。\n"
    )
    for row in computerese_accepted:
        parts.append(f"{row['chinese']} -> {row['english']} ({row['pos']}); computerese README line(s) {row['source_lines']}\n")
    with (ROOT/'vocabulary/data/computerese-tags.tsv').open(encoding='utf-8', newline='') as stream:
        computerese_tags = list(csv.DictReader(stream, delimiter='\t', fieldnames=('english', 'mask', 'source')))
    parts.append(
        f"本来源记录{len(computerese_tags)}个计算机标签词头，其中{computerese_manifest['new_computer_tag_memberships']}项是此前没有的类别归属；词头清单："
        + ", ".join(row['english'] for row in computerese_tags) + "。\n"
    )
    mesh_manifest = json.loads((ROOT/'vocabulary/data/mesh-medical-manifest.json').read_text(encoding='utf-8'))
    parts.append("\n=== 医学词汇批次21（NLM MeSH 2026 + ECDICT MIT）===\n")
    parts.append(
        "署名：U.S. National Library of Medicine (NLM), Medical Subject Headings (MeSH), 2026; "
        "https://www.nlm.nih.gov/mesh/ 。官方数据下载与使用条款："
        "https://www.nlm.nih.gov/databases/download/mesh.html 和 "
        "https://www.nlm.nih.gov/databases/download/terms_and_conditions_mesh.html 。"
        "MeSH 数据可免费使用，需署名 NLM 并标明版本；本项目使用英文 Descriptor XML，不使用 MeSH 中文翻译/MTMS 文件。"
        "MeSH 提供英文主题词与分类树，新增中文映射由 ECDICT MIT 短义及词性匹配并逐项审核。"
        f"候选{mesh_manifest['candidate_mappings_with_pinyin_ipa_and_exact_ecdict']}组，接受{mesh_manifest['accepted_new_mappings']}组映射"
        f"（{mesh_manifest['accepted_new_english_headwords']}个新英文词头），排除{mesh_manifest['rejected_candidates']}组、"
        f"暂缓{mesh_manifest['deferred_candidates']}组；新增{mesh_manifest['new_medical_tag_memberships']}个医学标签归属。"
        f"归档 SHA-256：{mesh_manifest['source']['archive_sha256']}。固定来源、修改和逐项证据见"
        "vocabulary/data/MESH-ATTRIBUTION.md、vocabulary/data/mesh-medical-manifest.json、"
        "batches/21-mesh-medical-reviewed.tsv 与 batches/21-mesh-medical-tags-evidence.tsv。\n"
    )
    wikidata_manifest = json.loads((ROOT/'vocabulary/data/wikidata-medical-manifest.json').read_text(encoding='utf-8'))
    with (ROOT/'vocabulary/data/batches/22-wikidata-medical-reviewed.tsv').open(encoding='utf-8', newline='') as stream:
        wikidata_rows = list(csv.DictReader(stream, delimiter='\t'))
    wikidata_accepted = [row for row in wikidata_rows if row['decision'] == 'accept']
    parts.append("\n=== 医学译词第二段（Wikidata CC0 + NLM MeSH 2026）===\n")
    parts.append(
        "署名：Wikidata contributors，结构化数据按 CC0 1.0 提供，https://www.wikidata.org/wiki/Wikidata:Licensing 。"
        "MeSH 英文主题和版本来自美国国家医学图书馆 NLM 2026；遵守 NLM 署名及版本标注要求，"
        "https://www.nlm.nih.gov/databases/download/terms_and_conditions_mesh.html 。"
        "中文标签经 Wikidata 项目的 MeSH P486 编号与 MeSH 主题精确关联；修改为仅保留已有拼音键、"
        "有本地音标且逐项审核接受的短映射，不复制定义、例句或整库词条。"
        f"候选{wikidata_manifest['candidates']}组，接受{wikidata_manifest['accepted_mappings']}组映射、"
        f"排除{wikidata_manifest['rejected_candidates']}组、暂缓{wikidata_manifest['deferred_candidates']}组；"
        f"新增{wikidata_manifest['new_medical_tag_memberships']}个医学标签归属。"
        "固定 CC0 标签快照、Wikidata QID/修订、MeSH 编号、逐条审核和散列见"
        "vocabulary/data/WIKIDATA-MEDICAL-ATTRIBUTION.md、vocabulary/data/wikidata-medical-manifest.json、"
        "vocabulary/data/sources/wikidata/ 与 vocabulary/data/batches/22-wikidata-medical-reviewed.tsv。\n"
    )
    for row in wikidata_accepted:
        parts.append(
            f"{row['chinese']} -> {row['mesh_english'].casefold()} ({row['pos']}); "
            f"MeSH {row['mesh_id']}; Wikidata {row['wikidata_qid']} revision {row['wikidata_revision']}\n"
        )
    wikidata2_manifest = json.loads((ROOT/'vocabulary/data/wikidata-medical-manifest-2.json').read_text(encoding='utf-8'))
    with (ROOT/'vocabulary/data/batches/23-wikidata-medical-reviewed.tsv').open(encoding='utf-8', newline='') as stream:
        wikidata2_rows = list(csv.DictReader(stream, delimiter='\t'))
    wikidata2_accepted = [row for row in wikidata2_rows if row['decision'] == 'accept']
    parts.append("\n=== 医学译词第三段（Wikidata CC0 + NLM MeSH 2026）===\n")
    parts.append(
        "扩展到1,326个本地有音标及名词词性的 MeSH 主题编号，固定1,964条 Wikidata 中文/英文标签关联和870个实体修订。"
        "在157组本地拼音可达的标签候选中，已存在于基础运行词头的条目不重复送审；剩余48组经逐项审核。"
        f"接受{wikidata2_manifest['accepted_mappings']}组映射、排除{wikidata2_manifest['rejected_candidates']}组、"
        f"暂缓{wikidata2_manifest['deferred_candidates']}组；其中{wikidata2_manifest['accepted_new_english_headwords']}个此前未映射词头，"
        f"新增{wikidata2_manifest['new_medical_tag_memberships']}个医学标签归属。"
        "保留原中文候选顺序；按键时只查编译后的短映射和标签，不读取来源快照。"
        "固定完整标签快照、修订记录、1,326个 MeSH 编号范围、SHA-256、逐条审核和构建器见"
        "vocabulary/data/WIKIDATA-MEDICAL-ATTRIBUTION.md、vocabulary/data/wikidata-medical-manifest-2.json、"
        "vocabulary/data/sources/wikidata/ 与 vocabulary/data/batches/23-wikidata-medical-reviewed.tsv。\n"
    )
    for row in wikidata2_accepted:
        parts.append(
            f"{row['chinese']} -> {row['mesh_english'].casefold()} ({row['pos']}); "
            f"MeSH {row['mesh_id']}; Wikidata {row['wikidata_qid']} revision {row['wikidata_revision']}\n"
        )
    naer_manifest = json.loads((ROOT/'vocabulary/data/naer-medical-manifest.json').read_text(encoding='utf-8'))
    with (ROOT/'vocabulary/data/batches/24-naer-medical-reviewed.tsv').open(encoding='utf-8', newline='') as stream:
        naer_rows = list(csv.DictReader(stream, delimiter='\t'))
    naer_accepted = [row for row in naer_rows if row['decision'] == 'accept']
    parts.append("\n=== 医学词汇第四段（NAER Medical Academic Terms / 國家教育研究院医学学术名词，2026）===\n")
    parts.append(
        "署名：國家教育研究院，2026，《國家教育研究院-醫學學術名詞》（2026-06-24釋出版本）。"
        "本開放資料依政府資料開放授權條款（Open Government Data License）第1版提供；"
        "遵守條款後得利用。授權：https://data.gov.tw/license 。"
        "資料集：https://taic.moda.gov.tw/datasets/4ca6b322-b160-41dd-a16a-02249f540bf8 。"
        f"固定CSV含{naer_manifest['counts']['source_records']}筆資料列，SHA-256：{naer_manifest['source']['sha256']}。"
        f"篩選後745組本機可達新對應中，591組屬已存在英文詞頭，留待後續審查；"
        f"另154組新詞頭候選逐項審核，接受{naer_manifest['counts']['accepted_mappings']}組、"
        f"排除{naer_manifest['counts']['rejected_candidates']}組、暫緩{naer_manifest['counts']['deferred_candidates']}組，"
        f"新增{naer_manifest['counts']['new_medical_tag_memberships']}個醫學標籤成員。"
        "繁體中文以 OpenCC t2s 轉簡體；要求本機拼音、IPA、ECDICT名詞詞性和每鍵容量檢查。"
        "原CSV逐筆「來源網站」欄為字面值 [url]，不聲稱獨立追溯原始網站。"
        "來源快照、來源輸出散列、審校理由及建構器見 vocabulary/data/NAER-MEDICAL-ATTRIBUTION.md、"
        "vocabulary/data/sources/naer/、vocabulary/data/naer-medical-manifest.json、"
        "vocabulary/data/batches/24-naer-medical-reviewed.tsv 與 scripts/build_naer_medical_batch.py。\n"
    )
    for row in naer_accepted:
        parts.append(
            f"{row['chinese']} -> {row['english']} ({row['noun_evidence']}); "
            f"NAER record {row['source_records']}\n"
        )
    naer2_manifest = json.loads((ROOT/'vocabulary/data/naer-medical-manifest-2.json').read_text(encoding='utf-8'))
    with (ROOT/'vocabulary/data/batches/25-naer-medical-existing-headwords-reviewed.tsv').open(encoding='utf-8', newline='') as stream:
        naer2_rows = list(csv.DictReader(stream, delimiter='\t'))
    naer2_accepted = [row for row in naer2_rows if row['decision'] == 'accept']
    parts.append("\n=== 医学词汇第五段（NAER + NLM MeSH 2026 + ECDICT）===\n")
    parts.append(
        "NAER 原始资料署名與政府開放資料授權第1版同批次24；資料集：https://taic.moda.gov.tw/datasets/4ca6b322-b160-41dd-a16a-02249f540bf8 。"
        "NLM MeSH 2026 僅用英文主題詞/樹編號確認醫學範圍，遵守 NLM 版本及署名要求："
        "https://www.nlm.nih.gov/mesh/ 與 https://www.nlm.nih.gov/databases/download/terms_and_conditions_mesh.html 。"
        "ECDICT MIT 僅用作精確中文名詞義核對，不複製完整詞典或定義。"
        f"從591組已有英文詞頭的 NAER 對應中，以 MeSH 交集與 ECDICT 精確名詞義篩出45組；"
        f"接受{naer2_manifest['counts']['accepted_mappings']}組映射，0個新英文詞頭；"
        f"排除{naer2_manifest['counts']['rejected_candidates']}組、暫緩{naer2_manifest['counts']['deferred_candidates']}組，"
        f"新增{naer2_manifest['counts']['new_medical_tag_memberships']}個醫學標籤成員。"
        "來源快照、交叉證據、逐項理由和 SHA-256 見 vocabulary/data/NAER-MEDICAL-ATTRIBUTION.md、"
        "vocabulary/data/naer-medical-manifest-2.json、vocabulary/data/batches/25-naer-medical-existing-headwords-reviewed.tsv。\n"
    )
    for row in naer2_accepted:
        parts.append(
            f"{row['chinese']} -> {row['english']} (n.); NAER record {row['source_records']}; "
            f"MeSH {row['mesh_term_ids']}\n"
        )
    for batch, title, source_name, attribution, reviewed_name, manifest_name in [
        (
            "26-naer-life-science",
            "NAER Life Science Academic Terms",
            "life-science-academic-terms.csv",
            "NAER-LIFE-SCIENCE-ATTRIBUTION.md",
            "26-naer-life-science-reviewed.tsv",
            "naer-life-science-manifest.json",
        ),
        (
            "27-naer-veterinary-medical",
            "NAER Veterinary Medical Terms",
            "veterinary-academic-terms.csv",
            "NAER-VETERINARY-ATTRIBUTION.md",
            "27-naer-veterinary-reviewed.tsv",
            "naer-veterinary-manifest.json",
        ),
    ]:
        manifest = json.loads((ROOT/'vocabulary/data'/manifest_name).read_text(encoding='utf-8'))
        with (ROOT/'vocabulary/data/batches'/reviewed_name).open(encoding='utf-8', newline='') as stream:
            reviewed = list(csv.DictReader(stream, delimiter='\t'))
        accepted = [row for row in reviewed if row['decision'] == 'accept']
        parts.append(f"\n=== 医学词汇批次 {batch[:2]}（{title}）===\n")
        parts.append(
            f"署名：國家教育研究院（National Academy for Educational Research）；数据集：{manifest['source']['dataset_url']}。"
            f"许可：政府資料開放授權條款第1版（Open Government Data License v1.0），{manifest['source']['license_url']}。"
            f"固定来源文件 {source_name}，SHA-256：{manifest['source']['snapshot_sha256']}；"
            f"共{manifest['counts']['source_records']}条数据记录。"
            f"候选审查{manifest['counts']['new_candidates']}组，接受{manifest['counts']['accepted_mappings']}组、"
            f"排除{manifest['counts']['rejected_candidates']}组、暂缓{manifest['counts']['deferred_candidates']}组；"
            f"新增{manifest['counts']['new_english_headwords']}个英文词头和{manifest['counts']['new_medical_tag_memberships']}个医学标签成员。"
            "筛选要求本机 IPA、ECDICT 精确名词义、拼音可达及 MeSH 主题；运行时只载入经审校的精简 TSV。"
            f"来源与修改说明、输入/输出散列、逐项理由见 vocabulary/data/{attribution}、"
            f"vocabulary/data/{manifest_name}、vocabulary/data/batches/{reviewed_name} 和 scripts/build_{'naer_life_science_batch.py' if batch.startswith('26') else 'naer_veterinary_batch.py'}。\n"
        )
    for row in accepted:
        parts.append(
            f"{row['chinese']} -> {row['english']} (n.); NAER source record {row['source_records']}; "
            f"MeSH {row['mesh_ids']}\n"
        )
    economics_manifest = json.loads((ROOT/'vocabulary/data/naer-economics-manifest.json').read_text(encoding='utf-8'))
    with (ROOT/'vocabulary/data/batches/30-naer-economics-reviewed.tsv').open(encoding='utf-8', newline='') as stream:
        economics_reviewed = list(csv.DictReader(stream, delimiter='\t'))
    economics_accepted = [row for row in economics_reviewed if row['decision'] == 'accept']
    parts.append("\n=== 商务词汇批次30（NAER Economics Terminology）===\n")
    parts.append(
        "署名：National Academy for Educational Research, 2025, Economics Terminology（dataset 15405，页面更新于2025-12-16）。"
        "来源：https://data.gov.tw/en/datasets/15405 。许可：Open Government Data License v1.0，https://data.gov.tw/license 。"
        f"固定 CSV 含{economics_manifest['counts']['source_records']}条数据记录，SHA-256：{economics_manifest['source']['snapshot_sha256']}。"
        f"253组本地精确名词/拼音/音标候选中，189组已有对应；其余63组审校后纳入{economics_manifest['counts']['accepted_mappings']}组、"
        f"排除{economics_manifest['counts']['rejected_candidates']}组、暂缓{economics_manifest['counts']['deferred_candidates']}组。"
        f"纳入{economics_manifest['counts']['new_english_headwords']}个新英文词头，并新增{economics_manifest['counts']['new_business_tag_memberships']}个商务标签成员。"
        "繁体中文以 OpenCC t2s 转简体。项目只保留审校通过的短映射及分类，不含源定义和例句。"
        "完整来源、修改说明、SHA-256、候选决定与构建器见 vocabulary/data/NAER-ECONOMICS-ATTRIBUTION.md、"
        "vocabulary/data/naer-economics-manifest.json、vocabulary/data/batches/30-naer-economics-reviewed.tsv 和 scripts/build_naer_economics_batch.py。\n"
    )
    for row in economics_accepted:
        parts.append(
            f"{row['chinese']} -> {row['english']} (n.); NAER economics record {row['source_records']}\n"
        )
    computer_manifest = json.loads((ROOT/'vocabulary/data/naer-computer-manifest.json').read_text(encoding='utf-8'))
    with (ROOT/'vocabulary/data/batches/31-naer-computer-reviewed.tsv').open(encoding='utf-8', newline='') as stream:
        computer_reviewed = list(csv.DictReader(stream, delimiter='\t'))
    computer_accepted = [row for row in computer_reviewed if row['decision'] == 'accept']
    parts.append("\n=== 计算机词汇批次31（NAER Computer Science Terms）===\n")
    parts.append(
        "署名：National Academy for Educational Research, 2026, Cross-Strait Comparative Terminology - Computer Science "
        "（dataset 15275，页面元数据更新于2026-08-12）。来源：https://data.gov.tw/dataset/15275 。"
        "许可：Open Government Data License v1.0，https://data.gov.tw/license 。"
        f"固定 CSV 含{computer_manifest['source']['records']}条数据记录，SHA-256：{computer_manifest['source']['snapshot_sha256']}。"
        f"{computer_manifest['candidate_exact_pairs']}组有本机精确词义/拼音/音标证据，{computer_manifest['already_mapped_pairs']}组原已映射；"
        f"其余{computer_manifest['new_mapping_candidates_with_capacity']}组审校后纳入{computer_manifest['accepted_new_mappings']}组、"
        f"排除{computer_manifest['rejected_new_mappings']}组、暂缓{computer_manifest['deferred_new_mappings']}组。"
        f"纳入{computer_manifest['accepted_new_headwords']}个新英文词头，并新增{len(computer_manifest['new_unique_computer_tag_headwords'])}个计算机分类成员。"
        "繁体中文以 OpenCC t2s 转简体，并分别审核两岸译名；项目只保留审核通过的精简映射和标签，不含源定义。"
        "完整来源、修改说明、SHA-256、逐项决定和构建器见 vocabulary/data/NAER-COMPUTER-ATTRIBUTION.md、"
        "vocabulary/data/naer-computer-manifest.json、vocabulary/data/batches/31-naer-computer-reviewed.tsv、"
        "vocabulary/data/batches/31-naer-computer-tags-reviewed.tsv 和 scripts/build_naer_computer_batch.py。\n"
    )
    for row in computer_accepted:
        parts.append(
            f"{row['chinese']} -> {row['english']} ({row['runtime_pos']}); "
            f"NAER computer-science records {row['source_records']}\n"
        )
    accounting_manifest = json.loads((ROOT/'vocabulary/data/naer-accounting-manifest.json').read_text(encoding='utf-8'))
    with (ROOT/'vocabulary/data/batches/32-naer-accounting-reviewed.tsv').open(encoding='utf-8', newline='') as stream:
        accounting_reviewed = list(csv.DictReader(stream, delimiter='\t'))
    accounting_accepted = [row for row in accounting_reviewed if row['decision'] == 'accept']
    accounting_counts = accounting_manifest['counts']
    parts.append("\n=== 商务会计词汇批次32（NAER Accounting Academic Terms）===\n")
    parts.append(
        "署名：National Academy for Educational Research, 2026, Accounting Academic Terms "
        "（dataset 15404，页面元数据更新于2026-08-12）。来源：https://data.gov.tw/dataset/15404 。"
        "许可：Open Government Data License v1.0，https://data.gov.tw/license 。"
        f"固定 CSV 含{accounting_counts['source_records']}条数据记录，SHA-256：{accounting_manifest['source']['snapshot_sha256']}。"
        f"{accounting_counts['eligible_exact_pairs']}组有本机精确名词/拼音/音标证据，{accounting_counts['already_mapped_pairs']}组原已映射；"
        f"其余{accounting_counts['new_review_candidates']}组审校后纳入{accounting_counts['accepted_mappings']}组、"
        f"排除{accounting_counts['rejected_candidates']}组、暂缓{accounting_counts['deferred_candidates']}组。"
        f"纳入{accounting_counts['new_english_headwords']}个新英文词头；{accounting_counts['reviewed_tag_headwords']}个有本地候选的来源词头逐项审查后，"
        f"{accounting_counts['accounting_tag_source_memberships']}个加入商务来源归属（新增{accounting_counts['new_business_tag_memberships']}个商务成员）、"
        f"{accounting_counts['rejected_tag_headwords']}个排除、{accounting_counts['deferred_tag_headwords']}个暂缓。"
        "繁体中文以 OpenCC t2s 转简体；源定义和例句不进入应用。完整快照、许可、SHA-256、逐项审校和构建器见 "
        "vocabulary/data/NAER-ACCOUNTING-ATTRIBUTION.md、vocabulary/data/naer-accounting-manifest.json、"
        "vocabulary/data/batches/32-naer-accounting-reviewed.tsv、vocabulary/data/batches/32-naer-accounting-tags-reviewed.tsv "
        "和 scripts/build_naer_accounting_batch.py。\n"
    )
    for row in accounting_accepted:
        parts.append(
            f"{row['chinese']} -> {row['english']} (n.); NAER accounting record {row['source_records']}\n"
        )
    management_manifest = json.loads((ROOT/'vocabulary/data/naer-management-manifest.json').read_text(encoding='utf-8'))
    with (ROOT/'vocabulary/data/batches/33-naer-management-reviewed.tsv').open(encoding='utf-8', newline='') as stream:
        management_reviewed = list(csv.DictReader(stream, delimiter='\t'))
    management_accepted = [row for row in management_reviewed if row['decision'] == 'accept']
    management_counts = management_manifest['counts']
    parts.append("\n=== 商务管理学术词汇批次33（NAER Management Academic Terms）===\n")
    parts.append(
        "署名：National Academy for Educational Research, 2026, Management Academic Terms "
        "（dataset 15440，页面元数据更新于2026-08-12）。来源：https://data.gov.tw/dataset/15440 。"
        "许可：Open Government Data License v1.0，https://data.gov.tw/license 。"
        f"固定 CSV 含{management_counts['source_records']}条数据记录，SHA-256：{management_manifest['source']['snapshot_sha256']}。"
        f"{management_counts['eligible_exact_pairs']}组有本机精确名词/拼音/音标证据，{management_counts['already_mapped_pairs']}组原已映射；"
        f"其余{management_counts['new_review_candidates']}组审校后纳入{management_counts['accepted_mappings']}组、"
        f"排除{management_counts['rejected_candidates']}组、暂缓{management_counts['deferred_candidates']}组。"
        f"纳入{management_counts['new_english_headwords']}个新英文词头；"
        f"{management_counts['reviewed_tag_headwords']}个来源词头加入商务来源归属（新增{management_counts['new_business_tag_memberships']}个商务成员）。"
        "繁体中文以 OpenCC t2s 转简体；源定义和例句不进入应用。完整快照、许可、SHA-256、逐项审校和构建器见 "
        "vocabulary/data/NAER-MANAGEMENT-ATTRIBUTION.md、vocabulary/data/naer-management-manifest.json、"
        "vocabulary/data/batches/33-naer-management-reviewed.tsv、vocabulary/data/batches/33-naer-management-tags-reviewed.tsv "
        "和 scripts/build_naer_management_batch.py。\n"
    )
    for row in management_accepted:
        parts.append(
            f"{row['chinese']} -> {row['english']} (n.); NAER management records {row['source_records']}\n"
        )
    administration_manifest = json.loads((ROOT/'vocabulary/data/naer-administration-manifest.json').read_text(encoding='utf-8'))
    with (ROOT/'vocabulary/data/batches/34-naer-administration-reviewed.tsv').open(encoding='utf-8', newline='') as stream:
        administration_reviewed = list(csv.DictReader(stream, delimiter='\t'))
    administration_accepted = [row for row in administration_reviewed if row['decision'] == 'accept']
    administration_counts = administration_manifest['counts']
    parts.append("\n=== 行政学词汇批次34（NAER Administration Academic Terms）===\n")
    parts.append(
        "署名：National Academy for Educational Research, 2026, Administration Academic Terms "
        "（dataset 15262，页面元数据更新于2026-08-12）。来源：https://data.gov.tw/dataset/15262 。"
        "许可：Open Government Data License v1.0，https://data.gov.tw/license 。"
        f"固定 CSV 含{administration_counts['source_records']}条数据记录，SHA-256：{administration_manifest['source']['snapshot_sha256']}。"
        f"{administration_counts['eligible_exact_pairs']}组有本机精确名词/拼音/音标证据，{administration_counts['already_mapped_pairs']}组原已映射；"
        f"其余{administration_counts['new_review_candidates']}组经逐项审校，接受{administration_counts['accepted_mappings']}组、"
        f"暂缓{administration_counts['deferred_candidates']}组，新增{administration_counts['new_english_headwords']}个英文词头。"
        f"另有{administration_counts['reviewed_tag_headwords']}个可核验来源词头加入行政学标签；运行标签来源名为 NAER Administration Academic Terms OGDL v1.0。"
        "项目只保留审核通过的短映射和来源成员关系，不载入来源 CSV、定义或例句进行按键查询。"
        "完整来源、修改说明、SHA-256、逐项决定和构建器见 vocabulary/data/NAER-ADMINISTRATION-ATTRIBUTION.md、"
        "vocabulary/data/naer-administration-manifest.json、vocabulary/data/batches/34-naer-administration-reviewed.tsv、"
        "vocabulary/data/batches/34-naer-administration-tags-reviewed.tsv 和 scripts/build_naer_administration_batch.py。\n"
    )
    for row in administration_accepted:
        parts.append(
            f"{row['chinese']} -> {row['english']} (n.); NAER administration record {row['source_records']}\n"
        )
    wordlevel_manifest = json.loads((ROOT/'vocabulary/data/wordlevel-toefl-ielts-manifest.json').read_text(encoding='utf-8'))
    with (ROOT/'vocabulary/data/batches/28-wordlevel-reviewed.tsv').open(encoding='utf-8', newline='') as stream:
        wordlevel_reviewed = list(csv.DictReader(stream, delimiter='\t'))
    wordlevel_accepted = [row for row in wordlevel_reviewed if row['decision'] == 'accept']
    wordlevel_counts = wordlevel_manifest['counts']
    parts.append("\n=== WordLevel TOEFL/IELTS 学术词表（批次28）===\n")
    parts.append(
        "署名：Gungor Kaya / WordLevel；来源仓库："
        f"{wordlevel_manifest['source']['repository']}，固定提交 {wordlevel_manifest['source']['commit']}。"
        "上游 GitHub 仓库声明 MIT，并要求提供指向 https://wordlevel.net 的可点击链接；"
        "对应 Mendeley DOI 记录标示 CC BY 4.0（https://creativecommons.org/licenses/by/4.0/）。"
        "因两处许可元数据不同，本项目保留上游 MIT 文本并同时提供 CC BY 署名。"
        f"CSV SHA-256：{wordlevel_manifest['source']['source_sha256']['toefl_essential_vocabulary.csv']}。"
        f"来源共{wordlevel_counts['source_records']}词；运行索引限于有本地映射及 IPA 的{wordlevel_counts['runtime_tagged_source_headwords']}词。"
        f"筛选候选{wordlevel_counts['candidates_reviewed']}组，接受{wordlevel_counts['accepted_mappings']}组、"
        f"排除{wordlevel_counts['rejected_candidates']}组、暂缓{wordlevel_counts['deferred_candidates']}组。"
        "该社区词表不是官方完整考纲。只提取目标列表成员关系；不将 WordLevel 定义、例句或同义词复制到运行索引。"
        "ECDICT MIT 提供新增中文短义；完整来源、输入输出哈希和逐项理由见 "
        "vocabulary/data/WORDLEVEL-ATTRIBUTION.md、vocabulary/data/wordlevel-toefl-ielts-manifest.json、"
        "vocabulary/data/batches/28-wordlevel-reviewed.tsv 和 vocabulary/data/batches/28-wordlevel-tag-evidence.tsv。\n"
    )
    for row in wordlevel_accepted:
        parts.append(f"{row['chinese']} -> {row['english']} ({row['pos']}); ECDICT MIT; WordLevel TOEFL/IELTS list membership\n")
    parts.append("\n=== vocabulary/data/sources/wordlevel/LICENSE ===\n")
    parts.append((ROOT/'vocabulary/data/sources/wordlevel/LICENSE').read_text(encoding='utf-8'))
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
                 'RIME-ICE-LICENSE.txt','sources/cjk-compsci-terms/LICENSE','sources/fibo/LICENSE','sources/better-quant-wiki/LICENSE',
                 'sources/finance_i18n/LICENSE','sources/computerese-cross-references/LICENSE']:
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
    desktop_parts=["Windows 音标与词汇目标补丁 0.1.22：用于现有青简 0.1.4 安装。\n非官方发布；不分发青简品牌图标。保持已安装官方资源。\n对应源码在 wordtrail-0.1.29-source.zip，包含 desktop/、vocabulary/ 与独立音标库。\n"]+list(parts)
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
