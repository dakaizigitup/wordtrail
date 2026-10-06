//! 中文词面精确匹配的考试译词补充；只初始化一次，不扫描原始词典。
mod translator;
use qingjian_core::{PartOfSpeech, Sense};
use std::{collections::HashMap, sync::LazyLock};
pub use translator::ExpandedTranslator;

pub const EXTRA_PER_WORD: usize = 8;
const DATA: &str = include_str!("../../data/english-expansion.tsv");
const WIKTIONARY_DATA: &str = include_str!("../../data/wiktionary-expansion.tsv");
const CC_CEDICT_DATA: &str = include_str!("../../data/cccedict-expansion.tsv");
static INDEX: LazyLock<HashMap<&'static str, Vec<(&'static str, PartOfSpeech, &'static str)>>> =
    LazyLock::new(|| {
        let mut index: HashMap<_, Vec<_>> = HashMap::new();
        for data in [DATA, WIKTIONARY_DATA, CC_CEDICT_DATA] {
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
        let rows: Vec<_> = include_str!("../../data/batches/02-additions.tsv").lines().collect();
        assert!(rows.len() > 32);
        for row in rows {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let _pos = fields.next().unwrap();
            let expected_source = fields.next().unwrap();
            assert!(
                senses(chinese).any(|sense| sense.text == english && source(chinese, english) == Some(expected_source)),
                "missing exact expansion {chinese} -> {english}"
            );
        }
    }

    #[test]
    fn wiktionary_batch_additions_are_queryable_with_source_and_exam_tags() {
        let rows: Vec<_> = include_str!("../../data/wiktionary-expansion.tsv").lines().collect();
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
            ("附属", "auxiliary"), ("衰退", "downturn"), ("流利", "fluently"),
            ("非常", "immensely"), ("行距", "leading"), ("大主教", "metropolitan"),
            ("移民", "migrant"), ("郊外", "outskirt"), ("大部分", "predominantly"),
            ("悲哀", "sadness"), ("造船", "shipbuilding"), ("下跌", "slump"),
            ("竟然", "surprisingly"), ("第三", "thirdly"), ("任何", "whatsoever"),
        ] {
            assert!(senses(chinese).any(|sense| sense.text == english));
        }
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
            assert!(crate::tags(english, 0).iter().any(|tag| {
                matches!(tag.id, "cet4" | "cet6")
            }));
        }
        assert!(crate::tags("collaborative", 0).iter().any(|tag| tag.id == "cet4"));
        assert!(crate::tags("collaborative", 0).iter().any(|tag| tag.id == "cet6"));
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
}
