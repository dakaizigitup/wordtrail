//! 候选窗口的一行：[`Candidate`] → 渲染器的 [`Row`]（序号、候选词、annotation 片段），与 macOS 端 `candidates/row.rs` 一致。
//! GDI 画法也用同一个类型。

use qingjian_core::{Candidate, CandidateKind, Language};
use qingjian_render::{Row, Tone};
use std::sync::OnceLock;
use wordtrail_pronunciation::PronunciationDictionary;

fn pronunciation_dictionary() -> Option<&'static PronunciationDictionary> {
    static DICTIONARY: OnceLock<Option<PronunciationDictionary>> = OnceLock::new();
    DICTIONARY
        .get_or_init(|| {
            let path = std::env::current_exe()
                .ok()?
                .parent()?
                .join("data/pronunciation-en.qj");
            match PronunciationDictionary::open(&path) {
                Ok(dictionary) => Some(dictionary),
                Err(error) => {
                    tracing::warn!(%error, "Independent IPA dictionary unavailable");
                    None
                }
            }
        })
        .as_ref()
}

/// `position` 是页内下标（从 0 起）。`show_code` 是 `[general] aux_code_show`：
/// 打开且候选带码时，码用方括号括起来紧跟在候选词后面（`鹤[rbm]`），不进 annotation。
pub(crate) fn from_candidate(position: usize, candidate: &Candidate, show_code: bool) -> Row {
    let code = candidate
        .aux_code
        .as_ref()
        .filter(|_| show_code)
        .map(|code| format!("[{code}]"));
    let mut annotation = Vec::new();
    if let Some(reading) = &candidate.reading {
        annotation.push((reading.clone(), Tone::Gloss));
    }
    if let Some(translation) = &candidate.translation {
        for (i, sense) in translation.senses().iter().enumerate() {
            if i > 0 || !annotation.is_empty() {
                annotation.push((" · ".to_owned(), Tone::Faint));
            }
            if let Some(pos) = sense.part_of_speech {
                annotation.push((format!("{pos} "), Tone::Faint));
            }
            let tone = if sense.fresh {
                Tone::Fresh
            } else {
                Tone::Gloss
            };
            for segment in sense.furigana() {
                annotation.push((segment.text, tone));
                if let Some(reading) = segment.reading {
                    annotation.push((format!("({reading})"), Tone::Faint));
                }
            }
            if translation.language == Language::English {
                let tags = wordtrail_vocabulary::tags(&sense.text, 0);
                if !tags.is_empty() {
                    annotation.push((
                        format!(
                            " [{}]",
                            tags.iter()
                                .map(|tag| tag.label)
                                .collect::<Vec<_>>()
                                .join("/")
                        ),
                        Tone::Faint,
                    ));
                }
                if let Some(pronunciation) =
                    pronunciation_dictionary().and_then(|dictionary| dictionary.lookup(&sense.text))
                {
                    if let Some(uk) = pronunciation.uk {
                        annotation.push((format!(" 英 {uk}"), Tone::Gloss));
                    }
                    if let Some(us) = pronunciation.us {
                        annotation.push((format!(" 美 {us}"), Tone::Gloss));
                    }
                }
            }
        }
    }
    Row {
        index: (position + 1).to_string(),
        text: candidate.text.clone(),
        code,
        annotation,
        cloud: candidate.kind == CandidateKind::Cloud,
    }
}
