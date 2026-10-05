//! Independent offline IPA dictionary. Pronunciations never modify committed text.
use qingjian_core::{Language, Translator};
use qingjian_translate::Glossary;
use serde::Serialize;
use std::path::Path;

#[derive(Clone, Debug, Serialize)]
pub struct Pronunciation {
    pub word: String,
    pub uk: Option<String>,
    pub us: Option<String>,
}

pub struct PronunciationDictionary(Glossary);

impl PronunciationDictionary {
    pub fn open(path: &Path) -> Result<Self, String> {
        Glossary::from_path(Language::English, path)
            .map(Self)
            .map_err(|error| error.to_string())
    }

    pub fn lookup(&self, word: &str) -> Option<Pronunciation> {
        // Exact word/phrase matching; do not guess a pronunciation for missing terms.
        let word = word.trim().to_lowercase();
        let translation = self.0.translate(&word)?;
        let mut result = Pronunciation {
            word,
            uk: None,
            us: None,
        };
        for sense in translation.senses() {
            match sense.reading.as_deref() {
                Some("UK") => result.uk = Some(sense.text.clone()),
                Some("US") => result.us = Some(sense.text.clone()),
                _ => {}
            }
        }
        (result.uk.is_some() || result.us.is_some()).then_some(result)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn dictionary() -> PronunciationDictionary {
        PronunciationDictionary::open(
            &Path::new(env!("CARGO_MANIFEST_DIR")).join("../data/pronunciation-en.qj"),
        )
        .expect("prepared offline dictionary")
    }

    #[test]
    fn lookup_normalizes_word_and_preserves_regional_variants() {
        let result = dictionary().lookup("  HeLLo  ").unwrap();
        assert_eq!(result.word, "hello");
        assert!(result.uk.as_ref().unwrap().starts_with('/'));
        assert!(result.us.as_ref().unwrap().starts_with('/'));
        assert_ne!(result.uk, result.us);
    }

    #[test]
    fn us_only_entry_is_never_labelled_as_british() {
        let result = dictionary().lookup("'bout").unwrap();
        assert!(result.uk.is_none());
        assert!(result.us.is_some());
    }

    #[test]
    fn missing_words_and_phrases_are_not_guessed() {
        let dictionary = dictionary();
        assert!(dictionary.lookup("wordtrail_missing_ipa_91821").is_none());
        assert!(
            dictionary
                .lookup("hello wordtrail_missing_ipa_91821")
                .is_none()
        );
    }
}
