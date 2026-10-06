//! 将补充译词并入原译者，原译词保持在前，学习与落盘继续交给原内核。
use super::{EXTRA_PER_WORD, senses};
use qingjian_core::{Language, Translation, Translator};

pub struct ExpandedTranslator {
    base: Box<dyn Translator>,
}
impl ExpandedTranslator {
    pub fn new(base: Box<dyn Translator>) -> Self {
        super::initialize();
        Self { base }
    }
}
impl Translator for ExpandedTranslator {
    fn language(&self) -> Language {
        self.base.language()
    }
    fn translate(&self, text: &str) -> Option<Translation> {
        let original = self.base.translate(text);
        if self.language() != Language::English {
            return original;
        }
        let mut merged = original
            .as_ref()
            .map(|t| t.senses().to_vec())
            .unwrap_or_default();
        let old_len = merged.len();
        for sense in senses(text) {
            if !merged
                .iter()
                .any(|old| old.text.eq_ignore_ascii_case(&sense.text))
            {
                merged.push(sense);
                if merged.len() - old_len >= EXTRA_PER_WORD {
                    break;
                }
            }
        }
        if merged.is_empty() {
            None
        } else {
            Some(Translation::expanded(Language::English, merged))
        }
    }
    fn learn(&mut self, word: &str, translation: Translation) {
        self.base.learn(word, translation);
    }
    fn flush(&mut self) {
        self.base.flush();
    }
}
