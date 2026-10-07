//! 中文词面精确匹配的考试译词补充；只初始化一次，不扫描原始词典。
mod translator;
use qingjian_core::{PartOfSpeech, Sense};
use std::{collections::HashMap, sync::LazyLock};
pub use translator::ExpandedTranslator;

pub const EXTRA_PER_WORD: usize = 8;
const DATA: &str = include_str!("../../data/english-expansion.tsv");
const WIKTIONARY_DATA: &str = include_str!("../../data/wiktionary-expansion.tsv");
const WIKTIONARY_2_DATA: &str = include_str!("../../data/wiktionary-expansion-2.tsv");
const CC_CEDICT_DATA: &str = include_str!("../../data/cccedict-expansion.tsv");
const CC_CEDICT_2_DATA: &str = include_str!("../../data/cccedict-expansion-2.tsv");
const CC_CEDICT_3_DATA: &str = include_str!("../../data/cccedict-expansion-3.tsv");
const CC_CEDICT_4_DATA: &str = include_str!("../../data/cccedict-expansion-4.tsv");
const EXAM_TARGET_ECDICT_DATA: &str = include_str!("../../data/exam-target-ecdict-expansion.tsv");
const EXAM_TARGET_KYLE_DATA: &str = include_str!("../../data/exam-target-kylebing-expansion.tsv");
const OPENETYMOLOGY_DATA: &str = include_str!("../../data/openetymology-exam-expansion.tsv");
const OPENETYMOLOGY_CET_DATA: &str = include_str!("../../data/openetymology-cet-expansion.tsv");
const EXAM_TARGET_BATCH_11_ECDICT_DATA: &str =
    include_str!("../../data/exam-target-batch-11-ecdict-expansion.tsv");
const EXAM_TARGET_BATCH_11_KYLE_DATA: &str =
    include_str!("../../data/exam-target-batch-11-kylebing-expansion.tsv");
const EXAM_TARGET_BATCH_11_DUAL_DATA: &str =
    include_str!("../../data/exam-target-batch-11-dual-expansion.tsv");
const EXAM_TARGET_BATCH_11_COW_DATA: &str =
    include_str!("../../data/exam-target-batch-11-cow-expansion.tsv");
const EXAM_TARGET_BATCH_11_KOREADER_COW_DATA: &str =
    include_str!("../../data/exam-target-batch-11-koreader-cow-expansion.tsv");
const EXAM_TARGET_BATCH_11_CC_BY_SA_DATA: &str =
    include_str!("../../data/exam-target-batch-11-cc-by-sa-expansion.tsv");
const EXAM_TARGET_BATCH_12_ECDICT_DATA: &str =
    include_str!("../../data/exam-target-batch-12-ecdict-expansion.tsv");
const PROFESSIONAL_DATA: &str = include_str!("../../data/professional-expansion.tsv");
const CJK_COMPSCI_DATA: &str = include_str!("../../data/cjk-compsci-expansion.tsv");
const BETTER_QUANT_DATA: &str = include_str!("../../data/better-quant-expansion.tsv");
const CFPB_FINANCE_DATA: &str = include_str!("../../data/cfpb-finance-expansion.tsv");
const FINANCE_I18N_DATA: &str = include_str!("../../data/finance-i18n-expansion.tsv");
const COMPUTERESE_DATA: &str = include_str!("../../data/computerese-expansion.tsv");
const MESH_MEDICAL_DATA: &str = include_str!("../../data/mesh-medical-expansion.tsv");
const WIKIDATA_MEDICAL_DATA: &str = include_str!("../../data/wikidata-medical-expansion.tsv");
const WIKIDATA_MEDICAL_2_DATA: &str = include_str!("../../data/wikidata-medical-expansion-2.tsv");
const NAER_MEDICAL_DATA: &str = include_str!("../../data/naer-medical-expansion.tsv");
const NAER_MEDICAL_2_DATA: &str = include_str!("../../data/naer-medical-expansion-2.tsv");
const NAER_LIFE_SCIENCE_DATA: &str = include_str!("../../data/naer-life-science-expansion.tsv");
const NAER_VETERINARY_DATA: &str = include_str!("../../data/naer-veterinary-expansion.tsv");
const NAER_ECONOMICS_DATA: &str = include_str!("../../data/naer-economics-expansion.tsv");
const NAER_ACCOUNTING_DATA: &str = include_str!("../../data/naer-accounting-expansion.tsv");
const NAER_MANAGEMENT_DATA: &str = include_str!("../../data/naer-management-expansion.tsv");
const NAER_COMPUTER_DATA: &str = include_str!("../../data/naer-computer-expansion.tsv");
const NAER_ADMINISTRATION_DATA: &str = include_str!("../../data/naer-administration-expansion.tsv");
const NAER_EDUCATION_DATA: &str = include_str!("../../data/naer-education-expansion.tsv");
const WORDLEVEL_TOEFL_IELTS_DATA: &str =
    include_str!("../../data/wordlevel-toefl-ielts-expansion.tsv");
static INDEX: LazyLock<HashMap<&'static str, Vec<(&'static str, PartOfSpeech, &'static str)>>> =
    LazyLock::new(|| {
        let mut index: HashMap<_, Vec<_>> = HashMap::new();
        for data in [
            DATA,
            WIKTIONARY_DATA,
            CC_CEDICT_DATA,
            CC_CEDICT_2_DATA,
            CC_CEDICT_3_DATA,
            CC_CEDICT_4_DATA,
            EXAM_TARGET_ECDICT_DATA,
            EXAM_TARGET_KYLE_DATA,
            OPENETYMOLOGY_DATA,
            OPENETYMOLOGY_CET_DATA,
            EXAM_TARGET_BATCH_11_ECDICT_DATA,
            EXAM_TARGET_BATCH_11_KYLE_DATA,
            EXAM_TARGET_BATCH_11_DUAL_DATA,
            EXAM_TARGET_BATCH_11_COW_DATA,
            EXAM_TARGET_BATCH_11_KOREADER_COW_DATA,
            EXAM_TARGET_BATCH_11_CC_BY_SA_DATA,
            EXAM_TARGET_BATCH_12_ECDICT_DATA,
            WIKTIONARY_2_DATA,
            PROFESSIONAL_DATA,
            CJK_COMPSCI_DATA,
            BETTER_QUANT_DATA,
            CFPB_FINANCE_DATA,
            FINANCE_I18N_DATA,
            COMPUTERESE_DATA,
            MESH_MEDICAL_DATA,
            WIKIDATA_MEDICAL_DATA,
            WIKIDATA_MEDICAL_2_DATA,
            NAER_MEDICAL_DATA,
            NAER_MEDICAL_2_DATA,
            NAER_LIFE_SCIENCE_DATA,
            NAER_VETERINARY_DATA,
            NAER_ECONOMICS_DATA,
            NAER_ACCOUNTING_DATA,
            NAER_MANAGEMENT_DATA,
            NAER_COMPUTER_DATA,
            NAER_ADMINISTRATION_DATA,
            NAER_EDUCATION_DATA,
            WORDLEVEL_TOEFL_IELTS_DATA,
        ] {
            for row in data.lines() {
                let mut fields = row.split('\t');
                let chinese = fields.next().unwrap();
                let english = fields.next().unwrap();
                let pos = fields.next().unwrap().parse().expect("valid expansion POS");
                let source = fields.next().unwrap();
                index
                    .entry(chinese)
                    .or_default()
                    .push((english, pos, source));
            }
        }
        index
    });

pub fn initialize() {
    LazyLock::force(&INDEX);
}
pub fn senses(chinese: &str) -> impl Iterator<Item = Sense> {
    INDEX
        .get(chinese)
        .into_iter()
        .flatten()
        .map(|(word, pos, _)| Sense {
            text: (*word).to_owned(),
            part_of_speech: Some(*pos),
            reading: None,
            fresh: false,
        })
}
pub fn source(chinese: &str, english: &str) -> Option<&'static str> {
    INDEX
        .get(chinese)
        .and_then(|items| items.iter().find(|(word, _, _)| *word == english))
        .map(|(_, _, origin)| *origin)
}

/// 熟悉度只记录候选行实际展示的译词，不把详情里尚未看到的词计为曝光。
pub fn displayed(candidate: &qingjian_core::Candidate, count: usize) -> qingjian_core::Candidate {
    let mut shown = candidate.clone();
    if let Some(t) = &candidate.translation {
        shown.translation = Some(qingjian_core::Translation::new(
            t.language,
            t.senses().iter().take(count).cloned().collect(),
        ));
    }
    shown
}

#[cfg(test)]
mod tests {
    use super::*;
    use qingjian_core::{Candidate, Language, Translation, Translator};
    struct Base(Language);
    impl Translator for Base {
        fn language(&self) -> Language {
            self.0
        }
        fn translate(&self, text: &str) -> Option<Translation> {
            let words = match text {
                "放弃" => vec!["abandon", "give up"],
                "重要" => vec!["important", "crucial"],
                "陌生测试" => vec!["unknown"],
                _ => return None,
            };
            Some(Translation::new(
                self.0,
                words
                    .into_iter()
                    .map(|w| Sense {
                        text: w.into(),
                        part_of_speech: None,
                        reading: None,
                        fresh: false,
                    })
                    .collect(),
            ))
        }
    }
    #[test]
    fn retains_originals_deduplicates_and_keeps_extras() {
        let translator = ExpandedTranslator::new(Box::new(Base(Language::English)));
        let t = translator.translate("放弃").unwrap();
        assert_eq!(
            &t.senses()[..2]
                .iter()
                .map(|s| s.text.as_str())
                .collect::<Vec<_>>(),
            &["abandon", "give up"]
        );
        assert!(t.senses().iter().any(|s| s.text == "relinquish"));
        assert!(t.senses().len() > 2 && t.senses().len() <= 10);
        let important = translator.translate("重要").unwrap();
        assert_eq!(
            important
                .senses()
                .iter()
                .filter(|s| s.text == "crucial")
                .count(),
            1
        );
        assert_eq!(
            translator.translate("陌生测试").unwrap().senses()[0].text,
            "unknown"
        );
        assert!(translator.translate("完全不存在").is_none());
    }
    #[test]
    fn non_english_unchanged_and_hidden_senses_not_exposed() {
        let translator = ExpandedTranslator::new(Box::new(Base(Language::Japanese)));
        assert_eq!(translator.translate("放弃").unwrap().senses().len(), 2);
        let english = ExpandedTranslator::new(Box::new(Base(Language::English)));
        let c = Candidate {
            text: "放弃".into(),
            kind: qingjian_core::CandidateKind::Chinese,
            syllables: vec![],
            reading: None,
            aux_code: None,
            translation: english.translate("放弃"),
        };
        assert_eq!(displayed(&c, 1).translation.unwrap().senses().len(), 1);
        assert!(c.translation.unwrap().senses().len() > 2);
        assert_eq!(source("放弃", "relinquish"), Some("Wordtrail-reviewed"));
        assert!(senses("放弃").all(|s| s.text != "relinguish"));
        assert!(senses("丰富").all(|s| s.text != "affluent"));
    }
    #[test]
    fn batch02_additions_are_queryable_by_exact_candidate_text() {
        let rows: Vec<_> = include_str!("../../data/batches/02-additions.tsv")
            .lines()
            .collect();
        assert!(rows.len() > 32);
        for row in rows {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let _pos = fields.next().unwrap();
            let expected_source = fields.next().unwrap();
            assert!(
                senses(chinese).any(|sense| sense.text == english
                    && source(chinese, english) == Some(expected_source)),
                "missing exact expansion {chinese} -> {english}"
            );
        }
    }

    #[test]
    fn wiktionary_batch_additions_are_queryable_with_source_and_exam_tags() {
        let rows: Vec<_> = include_str!("../../data/wiktionary-expansion.tsv")
            .lines()
            .collect();
        assert_eq!(rows.len(), 15);
        for row in rows {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let _pos = fields.next().unwrap();
            let source_label = fields.next().unwrap();
            assert_eq!(source_label, "Wiktionary CC BY-SA 4.0");
            assert!(
                senses(chinese).any(|sense| sense.text == english),
                "missing Wiktionary expansion {chinese} -> {english}"
            );
            assert_eq!(source(chinese, english), Some("Wiktionary CC BY-SA 4.0"));
        }
        for (chinese, english) in [
            ("附属", "auxiliary"),
            ("衰退", "downturn"),
            ("流利", "fluently"),
            ("非常", "immensely"),
            ("行距", "leading"),
            ("大主教", "metropolitan"),
            ("移民", "migrant"),
            ("郊外", "outskirt"),
            ("大部分", "predominantly"),
            ("悲哀", "sadness"),
            ("造船", "shipbuilding"),
            ("下跌", "slump"),
            ("竟然", "surprisingly"),
            ("第三", "thirdly"),
            ("任何", "whatsoever"),
        ] {
            assert!(senses(chinese).any(|sense| sense.text == english));
        }
    }

    #[test]
    fn third_cc_cedict_batch_is_queryable_with_separate_attribution() {
        let rows: Vec<_> = include_str!("../../data/cccedict-expansion-3.tsv")
            .lines()
            .collect();
        assert_eq!(rows.len(), 20);
        for row in rows {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let _pos = fields.next().unwrap();
            let source_label = fields.next().unwrap();
            assert_eq!(source_label, "CC-CEDICT CC BY-SA 4.0");
            assert!(
                senses(chinese).any(|sense| sense.text == english),
                "missing CC-CEDICT expansion {chinese} -> {english}"
            );
            assert_eq!(source(chinese, english), Some("CC-CEDICT CC BY-SA 4.0"));
        }
    }

    #[test]
    fn fourth_cc_cedict_batch_is_queryable_with_separate_attribution() {
        let rows: Vec<_> = CC_CEDICT_4_DATA.lines().collect();
        assert_eq!(rows.len(), 12);
        for row in rows {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let _pos = fields.next().unwrap();
            let source_label = fields.next().unwrap();
            assert_eq!(source_label, "CC-CEDICT CC BY-SA 4.0");
            assert!(
                senses(chinese).any(|sense| sense.text == english),
                "missing CC-CEDICT expansion {chinese} -> {english}"
            );
            assert_eq!(source(chinese, english), Some(source_label));
            assert!(
                crate::tags(english, 0)
                    .iter()
                    .any(|tag| { matches!(tag.id, "cet4" | "cet6") })
            );
        }
    }

    #[test]
    fn wiktionary_second_tranche_is_queryable_with_source_and_exam_tags() {
        let rows: Vec<_> = WIKTIONARY_2_DATA.lines().collect();
        assert_eq!(rows.len(), 7);
        for row in rows {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let _pos = fields.next().unwrap();
            let source_label = fields.next().unwrap();
            assert_eq!(source_label, "Wiktionary CC BY-SA 4.0");
            assert!(senses(chinese).any(|sense| sense.text == english));
            assert_eq!(source(chinese, english), Some(source_label));
            assert!(
                crate::tags(english, 0)
                    .iter()
                    .any(|tag| { matches!(tag.id, "cet4" | "cet6") })
            );
        }
        for (chinese, english) in [
            ("船上", "aboard"),
            ("冬眠", "dormant"),
            ("指引", "guideline"),
            ("先期", "premature"),
            ("加油", "refuel"),
            ("警司", "superintendent"),
            ("空想", "utopian"),
        ] {
            assert!(senses(chinese).any(|sense| sense.text == english));
        }
    }

    #[test]
    fn professional_batch_14_adds_queryable_medical_terms_and_domain_tags() {
        let rows: Vec<_> = PROFESSIONAL_DATA.lines().collect();
        assert_eq!(rows.len(), 10);
        for row in rows {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let _pos = fields.next().unwrap();
            let source_label = fields.next().unwrap();
            assert_eq!(source_label, "Wiktionary CC BY-SA 4.0");
            assert!(senses(chinese).any(|sense| sense.text == english));
            assert_eq!(source(chinese, english), Some(source_label));
            let medical = crate::tags(english, 1 << 8);
            assert!(
                medical
                    .iter()
                    .any(|tag| tag.id == "medical" && tag.selected)
            );
            assert_eq!(crate::lookup(english).professional & (1 << 8), 1 << 8);
        }
        assert!(senses("大脑").any(|sense| sense.text == "cerebrum"));
        assert!(senses("转移").any(|sense| sense.text == "metastasis"));
        assert!(!senses("疱疹").any(|sense| sense.text == "bleb"));
    }

    #[test]
    fn cc_cedict_first_tranche_is_queryable_with_exam_tags_and_source() {
        let rows: Vec<_> = CC_CEDICT_DATA.lines().collect();
        assert_eq!(rows.len(), 58);
        for row in rows {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let _pos = fields.next().unwrap();
            let source_label = fields.next().unwrap();
            assert_eq!(source_label, "CC-CEDICT CC BY-SA 4.0");
            assert!(senses(chinese).any(|sense| sense.text == english));
            assert_eq!(source(chinese, english), Some(source_label));
            assert!(
                crate::tags(english, 0)
                    .iter()
                    .any(|tag| { matches!(tag.id, "cet4" | "cet6") })
            );
        }
        assert!(
            crate::tags("collaborative", 0)
                .iter()
                .any(|tag| tag.id == "cet4")
        );
        assert!(
            crate::tags("collaborative", 0)
                .iter()
                .any(|tag| tag.id == "cet6")
        );
    }

    #[test]
    fn cc_cedict_second_tranche_is_queryable_with_exam_tags_and_source() {
        let rows: Vec<_> = CC_CEDICT_2_DATA.lines().collect();
        assert_eq!(rows.len(), 66);
        for row in rows {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let _pos = fields.next().unwrap();
            let source_label = fields.next().unwrap();
            assert_eq!(source_label, "CC-CEDICT CC BY-SA 4.0");
            assert!(senses(chinese).any(|sense| sense.text == english));
            assert_eq!(source(chinese, english), Some(source_label));
            assert!(
                crate::tags(english, 0)
                    .iter()
                    .any(|tag| { matches!(tag.id, "cet4" | "cet6") })
            );
        }
        assert!(crate::tags("hurl", 0).iter().any(|tag| tag.id == "cet6"));
        assert!(crate::tags("hurl", 0).iter().any(|tag| tag.id == "toefl"));
    }
    #[test]
    fn expanded_constructor_is_bounded_default_stays_two() {
        let senses: Vec<_> = (0..30)
            .map(|i| Sense {
                text: i.to_string(),
                part_of_speech: None,
                reading: None,
                fresh: false,
            })
            .collect();
        assert_eq!(
            Translation::new(Language::English, senses.clone())
                .senses()
                .len(),
            2
        );
        assert_eq!(
            Translation::expanded(Language::English, senses)
                .senses()
                .len(),
            12
        );
    }

    #[test]
    fn exam_target_batch_09_is_queryable_with_ipa_source_and_tags() {
        for (data, expected_source) in [
            (EXAM_TARGET_ECDICT_DATA, "ECDICT MIT"),
            (EXAM_TARGET_KYLE_DATA, "KyleBing BSD-3-Clause"),
        ] {
            let rows: Vec<_> = data.lines().collect();
            assert!(!rows.is_empty());
            for row in rows {
                let mut fields = row.split('\t');
                let chinese = fields.next().unwrap();
                let english = fields.next().unwrap();
                let _pos = fields.next().unwrap();
                let source_label = fields.next().unwrap();
                assert_eq!(source_label, expected_source);
                assert!(
                    senses(chinese).any(|sense| sense.text == english),
                    "missing batch 09 expansion {chinese} -> {english}"
                );
                assert!(
                    crate::tags(english, 0)
                        .iter()
                        .any(|tag| matches!(tag.id, "tem4" | "tem8" | "toefl" | "ielts")),
                    "missing target exam tag for {english}"
                );
            }
        }
    }

    #[test]
    fn openetymology_batch_10_is_queryable_and_target_tagged() {
        let rows: Vec<_> = OPENETYMOLOGY_DATA.lines().collect();
        assert_eq!(rows.len(), 136);
        for row in rows {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let _pos = fields.next().unwrap();
            let source_label = fields.next().unwrap();
            assert_eq!(source_label, "ECDICT MIT + KyleBing BSD-3-Clause");
            assert!(
                senses(chinese).any(|sense| sense.text == english),
                "missing batch 10 expansion {chinese} -> {english}"
            );
            assert!(
                crate::tags(english, 0)
                    .iter()
                    .any(|tag| matches!(tag.id, "tem8" | "toefl")),
                "missing OpenEtymology target tag for {english}"
            );
        }
        assert!(crate::tags("add-on", 0).iter().any(|tag| tag.id == "tem8"));
        assert!(
            crate::tags("obligatory", 1 << 3)
                .iter()
                .find(|tag| tag.id == "tem8")
                .unwrap()
                .sources
                .contains(&"OpenEtymology")
        );
    }

    #[test]
    fn openetymology_batch_29_adds_reviewed_cet_mappings_and_tags() {
        let rows: Vec<_> = OPENETYMOLOGY_CET_DATA.lines().collect();
        assert_eq!(rows.len(), 6);
        for row in rows {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let pos: PartOfSpeech = fields.next().unwrap().parse().unwrap();
            assert_eq!(fields.next(), Some("ECDICT MIT"));
            let sense = senses(chinese)
                .find(|sense| sense.text == english)
                .unwrap_or_else(|| panic!("missing batch 29 mapping {chinese} -> {english}"));
            assert_eq!(sense.part_of_speech, Some(pos));
            assert_eq!(source(chinese, english), Some("ECDICT MIT"));
            assert!(
                crate::tags(english, 0)
                    .iter()
                    .any(|tag| matches!(tag.id, "cet4" | "cet6"))
            );
        }
        let sufficient = senses("充分")
            .find(|sense| sense.text == "sufficiently")
            .unwrap();
        assert_eq!(sufficient.part_of_speech, Some(PartOfSpeech::Adverb));
    }

    #[test]
    fn exam_target_batches_11_and_12_are_queryable_and_tagged() {
        let batch_11 = [
            (EXAM_TARGET_BATCH_11_ECDICT_DATA, "ECDICT MIT", 160),
            (EXAM_TARGET_BATCH_11_KYLE_DATA, "KyleBing BSD-3-Clause", 98),
            (
                EXAM_TARGET_BATCH_11_DUAL_DATA,
                "ECDICT MIT + KyleBing BSD-3-Clause",
                260,
            ),
            (EXAM_TARGET_BATCH_11_COW_DATA, "Chinese Open Wordnet", 184),
            (
                EXAM_TARGET_BATCH_11_KOREADER_COW_DATA,
                "KOReader dictionaries CC BY-SA 4.0 + Chinese Open Wordnet",
                137,
            ),
        ];
        let mut checked = 0;
        for (data, expected_source, expected_rows) in batch_11 {
            let rows: Vec<_> = data.lines().collect();
            assert_eq!(rows.len(), expected_rows);
            for row in rows {
                let mut fields = row.split('\t');
                let chinese = fields.next().unwrap();
                let english = fields.next().unwrap();
                let _pos = fields.next().unwrap();
                let source_label = fields.next().unwrap();
                assert_eq!(source_label, expected_source);
                assert!(senses(chinese).any(|sense| sense.text == english));
                assert!(crate::tags(english, 0).iter().any(|tag| {
                    matches!(
                        tag.id,
                        "cet4" | "cet6" | "tem4" | "tem8" | "toefl" | "ielts"
                    )
                }));
                checked += 1;
            }
        }
        let cc_rows: Vec<_> = EXAM_TARGET_BATCH_11_CC_BY_SA_DATA.lines().collect();
        assert_eq!(cc_rows.len(), 753);
        for row in cc_rows {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let _pos = fields.next().unwrap();
            let source_label = fields.next().unwrap();
            assert!(matches!(
                source_label,
                "CC-CEDICT CC BY-SA 4.0"
                    | "FMLD CC BY-SA 4.0"
                    | "KOReader dictionaries CC BY-SA 4.0"
            ));
            assert!(senses(chinese).any(|sense| sense.text == english));
            assert!(
                crate::tags(english, 0)
                    .iter()
                    .any(|tag| { matches!(tag.id, "tem4" | "tem8" | "toefl" | "ielts") })
            );
            checked += 1;
        }
        let batch_12: Vec<_> = EXAM_TARGET_BATCH_12_ECDICT_DATA.lines().collect();
        assert_eq!(batch_12.len(), 699);
        for row in batch_12 {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let _pos = fields.next().unwrap();
            assert_eq!(fields.next().unwrap(), "ECDICT MIT");
            assert!(senses(chinese).any(|sense| sense.text == english));
            assert!(
                crate::tags(english, 0)
                    .iter()
                    .any(|tag| { matches!(tag.id, "tem4" | "tem8" | "toefl" | "ielts") })
            );
            checked += 1;
        }
        assert_eq!(checked, 2291);
        assert!(senses("一氧化物").any(|sense| sense.text == "monoxide"));
        let monoxide_tags = crate::tags("monoxide", 0);
        assert!(monoxide_tags.iter().any(|tag| tag.id == "toefl"));
        assert_eq!(source("一氧化物", "monoxide"), Some("ECDICT MIT"));
    }
}
