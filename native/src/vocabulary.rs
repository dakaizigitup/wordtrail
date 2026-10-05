//! Reference levels belong to individual translated words, never Chinese candidates.
use crate::model::VocabularyLevel;
use qingjian_translate::LevelTable;
use std::sync::LazyLock;

const SOURCE: &str = include_str!("../../vendor/qingjian/assets/levels/levels-en.tsv");
static ENGLISH: LazyLock<LevelTable> =
    LazyLock::new(|| LevelTable::parse(SOURCE).expect("bundled CEFR table is valid"));

pub fn english_levels<'a>(words: impl Iterator<Item = &'a str>) -> Vec<VocabularyLevel> {
    let mut result: Vec<VocabularyLevel> = Vec::new();
    for word in words {
        let word = word.trim();
        if word.is_empty()
            || result
                .iter()
                .any(|item| item.word.eq_ignore_ascii_case(word))
        {
            continue;
        }
        result.push(VocabularyLevel {
            word: word.to_owned(),
            level: ENGLISH.level(word).map(str::to_owned),
        });
    }
    result
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn covers_all_six_reference_levels_and_normalizes_case() {
        assert_eq!(ENGLISH.levels(), ["A1", "A2", "B1", "B2", "C1", "C2"]);
        assert_eq!(ENGLISH.len(), 8845);
        for rank in 0..6 {
            assert!(ENGLISH.size(rank) > 0);
        }
        assert_eq!(
            english_levels([" Hello "].into_iter())[0].level.as_deref(),
            Some("A1")
        );
    }

    #[test]
    fn preserves_individual_senses_and_deduplicates_words() {
        let result = english_levels(["hello", "sustainable", "HELLO"].into_iter());
        assert_eq!(result.len(), 2);
        assert_eq!(result[0].word, "hello");
        assert_eq!(result[0].level.as_deref(), Some("A1"));
        assert_eq!(result[1].level.as_deref(), ENGLISH.level("sustainable"));
    }

    #[test]
    fn unknown_words_and_phrases_are_not_assigned_guessed_levels() {
        let result = english_levels(["wordtrailunknownword", "hello world", ""].into_iter());
        assert_eq!(result.len(), 2);
        assert!(result.iter().all(|item| item.level.is_none()));
    }
}
