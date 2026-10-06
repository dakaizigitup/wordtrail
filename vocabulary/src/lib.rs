//! Shared exam membership and stable sense priority. Never ranks Chinese candidates.
pub mod expansion;
use qingjian_core::{Candidate, Language};
use serde::{Deserialize, Serialize};
use std::{borrow::Cow, collections::HashMap, path::Path, sync::LazyLock};

pub const CATEGORIES: [(&str, &str); 6] = [
    ("cet4", "四级"),
    ("cet6", "六级"),
    ("tem4", "专四"),
    ("tem8", "专八"),
    ("toefl", "托福"),
    ("ielts", "雅思"),
];
const TSV: &str = include_str!("../data/english-tags.tsv");
static WORDS: LazyLock<HashMap<&'static str, Membership>> = LazyLock::new(|| {
    TSV.lines()
        .map(|line| {
            let mut fields = line.split('\t');
            let word = fields.next().unwrap();
            let ecdict = fields.next().unwrap().parse().expect("valid ECDICT mask");
            let kylebing = fields.next().unwrap().parse().expect("valid KyleBing mask");
            (word, Membership { ecdict, kylebing })
        })
        .collect()
});

#[derive(Clone, Copy, Default)]
pub struct Membership {
    pub ecdict: u16,
    pub kylebing: u16,
}
impl Membership {
    pub fn mask(self) -> u16 {
        self.ecdict | self.kylebing
    }
}

/// Load once during worker initialization, not on the first visible keystroke.
pub fn initialize() {
    LazyLock::force(&WORDS);
}
pub fn lookup(word: &str) -> Membership {
    let word = word.trim();
    let normalized = if word.chars().any(char::is_uppercase) {
        Cow::Owned(word.to_lowercase())
    } else {
        Cow::Borrowed(word)
    };
    WORDS.get(normalized.as_ref()).copied().unwrap_or_default()
}

pub fn selection(ids: &[String]) -> Result<u16, String> {
    let mut mask = 0;
    for id in ids {
        let index = CATEGORIES
            .iter()
            .position(|(code, _)| id == code)
            .ok_or_else(|| format!("unknown vocabulary target: {id}"))?;
        mask |= 1 << index;
    }
    Ok(mask)
}
pub fn selected_ids(mask: u16) -> Vec<&'static str> {
    CATEGORIES
        .iter()
        .enumerate()
        .filter(|(i, _)| mask & (1 << i) != 0)
        .map(|(_, (id, _))| *id)
        .collect()
}

#[derive(Serialize)]
pub struct Tag {
    pub id: &'static str,
    pub label: &'static str,
    pub selected: bool,
    pub sources: Vec<&'static str>,
}
pub fn tags(word: &str, selected: u16) -> Vec<Tag> {
    let entry = lookup(word);
    let mut tags: Vec<_> = CATEGORIES
        .iter()
        .enumerate()
        .filter(|(i, _)| entry.mask() & (1 << i) != 0)
        .map(|(i, (id, label))| {
            let mut sources = Vec::new();
            if entry.ecdict & (1 << i) != 0 {
                sources.push("ECDICT");
            }
            if entry.kylebing & (1 << i) != 0 {
                sources.push("KyleBing/english-vocabulary");
            }
            Tag {
                id,
                label,
                sources,
                selected: selected & (1 << i) != 0,
            }
        })
        .collect();
    tags.sort_by_key(|tag| !tag.selected);
    tags
}

/// Move complete senses together: text, reading, part of speech and freshness.
pub fn prioritize(candidate: &mut Candidate, selected: u16) {
    if selected == 0 {
        return;
    }
    if let Some(translation) = &mut candidate.translation {
        if translation.language == Language::English {
            translation
                .senses_mut()
                .sort_by_key(|sense| lookup(&sense.text).mask() & selected == 0);
        }
    }
}

#[derive(Default, Deserialize, Serialize)]
#[serde(deny_unknown_fields)]
pub struct Preferences {
    pub targets: Vec<String>,
}
pub fn load_preferences(path: &Path) -> Result<u16, String> {
    match std::fs::read_to_string(path) {
        Ok(json) => {
            let prefs: Preferences = serde_json::from_str(json.trim_start_matches('\u{feff}'))
                .map_err(|e| e.to_string())?;
            selection(&prefs.targets)
        }
        Err(error) if error.kind() == std::io::ErrorKind::NotFound => Ok(0),
        Err(error) => Err(error.to_string()),
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use qingjian_core::{CandidateKind, Sense, Translation};
    fn candidate(words: &[&str], language: Language) -> Candidate {
        Candidate {
            text: "中文".into(),
            kind: CandidateKind::Chinese,
            syllables: vec![],
            reading: None,
            aux_code: None,
            translation: Some(Translation::new(
                language,
                words
                    .iter()
                    .map(|w| Sense {
                        text: (*w).into(),
                        part_of_speech: None,
                        reading: None,
                        fresh: false,
                    })
                    .collect(),
            )),
        }
    }
    #[test]
    fn exact_matches_multitag_and_sources() {
        let tags = tags(" Abandon ", 1 << 5);
        assert_eq!(tags.len(), 6);
        assert_eq!(tags[0].id, "ielts");
        assert!(tags[0].selected);
        assert!(tags.iter().all(|tag| !tag.sources.is_empty()));
        assert_eq!(lookup("abandon a task").mask(), 0);
        assert_eq!(lookup("wordtrailunknownword").mask(), 0);
    }
    #[test]
    fn validates_and_deduplicates_selection() {
        assert_eq!(
            selection(&["cet4".into(), "ielts".into(), "cet4".into()]).unwrap(),
            33
        );
        assert!(selection(&["imaginary".into()]).is_err());
        assert_eq!(selected_ids(33), ["cet4", "ielts"]);
    }
    #[test]
    fn stable_priority_preserves_senses_and_non_english() {
        let mut c = candidate(&["wordtrailunknownword", "abandon"], Language::English);
        let original = c.clone();
        prioritize(&mut c, 0);
        assert_eq!(c, original);
        prioritize(&mut c, 1 << 5);
        assert_eq!(c.text, original.text);
        assert_eq!(c.translation.as_ref().unwrap().senses()[0].text, "abandon");
        assert_eq!(
            c.translation.as_ref().unwrap().senses()[1],
            original.translation.as_ref().unwrap().senses()[0]
        );
        let matched = candidate(&["abandon", "environment"], Language::English);
        let mut tie = matched.clone();
        prioritize(&mut tie, 33);
        assert_eq!(tie, matched);
        let mut ja = candidate(&["wordtrailunknownword", "abandon"], Language::Japanese);
        let before = ja.clone();
        prioritize(&mut ja, 33);
        assert_eq!(ja, before);
    }
}
