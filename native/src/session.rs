//! 复用青简内核的移动会话，保存候选快照，避免点选时查询变化。
use crate::model::{MobileCandidate, MobileState, Request};
use qingjian_core::{Candidate, Engine, Language};
use qingjian_dictionary::Dictionary;
use qingjian_learning::{FrequencyLearner, VocabularyBook};
use qingjian_translate::Glossary;
use std::path::{Path, PathBuf};

pub struct Session {
    engine: Engine,
    pronunciation: Option<wordtrail_pronunciation::PronunciationDictionary>,
    data_dir: PathBuf,
    language: String,
    english: bool,
    visible: Vec<Candidate>,
    revision: u64,
    page: usize,
}

fn data_file(dir: &Path, stem: &str) -> PathBuf {
    let packed = dir.join(format!("{stem}.qj"));
    if packed.is_file() {
        packed
    } else {
        dir.join(format!("{stem}.tsv"))
    }
}

fn glossary(dir: &Path, language: &str) -> Result<Glossary, String> {
    let lang = match language {
        "en" => Language::English,
        "ja" => Language::Japanese,
        "es" => Language::Spanish,
        _ => return Err("unsupported learning language".into()),
    };
    Glossary::from_path(lang, data_file(dir, &format!("glossary-{language}")))
        .map_err(|e| e.to_string())
}

impl Session {
    pub fn new(request: &Request) -> Result<Self, String> {
        let data_dir = PathBuf::from(&request.data_dir);
        let user_dir = PathBuf::from(&request.user_dir);
        if request.data_dir.is_empty() || request.user_dir.is_empty() {
            return Err("data_dir and user_dir are required".into());
        }
        std::fs::create_dir_all(&user_dir).map_err(|e| e.to_string())?;
        let dictionary =
            Dictionary::from_path(data_file(&data_dir, "dict")).map_err(|e| e.to_string())?;
        let translator = glossary(&data_dir, &request.language)?;
        let pronunciation_path = data_dir.join("pronunciation-en.qj");
        let pronunciation = if pronunciation_path.is_file() {
            Some(wordtrail_pronunciation::PronunciationDictionary::open(
                &pronunciation_path,
            )?)
        } else {
            None // Older data packs continue to work without IPA.
        };
        let learner =
            FrequencyLearner::from_path(user_dir.join("user.tsv")).map_err(|e| e.to_string())?;
        let mut engine = Engine::new(dictionary)
            .with_translator(Box::new(translator))
            .with_learner(Box::new(learner))
            .with_vocabulary_tracker(Box::new(VocabularyBook::open(
                user_dir.join("user-vocab.tsv"),
            )));
        engine.set_private(request.private);
        Ok(Self {
            engine,
            pronunciation,
            data_dir,
            language: request.language.clone(),
            english: false,
            visible: Vec::new(),
            revision: 0,
            page: 0,
        })
    }

    fn raw(&mut self) -> String {
        let text = self.engine.composition().text().to_string();
        self.engine.clear();
        self.engine.note_displayed(std::iter::empty());
        self.visible.clear();
        text
    }

    fn first(&mut self) -> String {
        if let Some(candidate) = self.visible.first().cloned() {
            self.engine.commit(&candidate)
        } else {
            self.raw()
        }
    }

    pub fn action(&mut self, request: &Request) -> Result<MobileState, String> {
        let mut commit = None;
        let mut delete_backward = false;
        match request.op.as_str() {
            "key" => {
                self.page = 0;
                let mut chars = request.text.chars();
                let key = chars.next().ok_or("empty key")?;
                if chars.next().is_some() {
                    return Err("key must be one character".into());
                }
                if !self.english && (key.is_ascii_alphabetic() || key == '\'') {
                    if self.engine.composition().text().len() < 96 {
                        self.engine.push(key.to_ascii_lowercase());
                    }
                } else {
                    let mut text = self.first();
                    let punctuation = if !self.english {
                        match key {
                            ',' => '，',
                            '.' => '。',
                            '?' => '？',
                            '!' => '！',
                            ':' => '：',
                            ';' => '；',
                            _ => key,
                        }
                    } else {
                        key
                    };
                    text.push(punctuation);
                    commit = Some(text);
                }
            }
            "select" | "translation" => {
                if request.revision != Some(self.revision) {
                    return Err("candidates changed; select again".into());
                }
                let candidate = self
                    .visible
                    .get(request.index)
                    .cloned()
                    .ok_or("candidate index out of range")?;
                commit = if request.op == "translation" {
                    Some(
                        self.engine
                            .commit_translation(&candidate, 0)
                            .ok_or("candidate has no translation")?,
                    )
                } else {
                    Some(self.engine.commit(&candidate))
                };
            }
            "space" => {
                commit = Some(if self.engine.composition().is_empty() {
                    " ".into()
                } else {
                    self.first()
                })
            }
            "enter" => {
                commit = Some(if self.engine.composition().is_empty() {
                    "\n".into()
                } else {
                    self.raw()
                })
            }
            "backspace" => {
                self.page = 0;
                delete_backward = !self.engine.backspace();
            }
            "toggle" => {
                commit = Some(self.raw());
                self.english = !self.english;
            }
            "reset" => {
                self.raw();
                self.page = 0;
                self.engine.set_private(request.private);
            }
            "next_page" => self.page += 1,
            "previous_page" => self.page = self.page.saturating_sub(1),
            "language" => {
                let translator = glossary(&self.data_dir, &request.language)?;
                self.engine.set_translator(Box::new(translator));
                self.language = request.language.clone();
            }
            "flush" => self.engine.flush_learning(),
            "state" => {}
            _ => return Err("unknown operation".into()),
        }
        if !matches!(request.op.as_str(), "state" | "flush") {
            self.revision += 1;
        }
        let mut state = self.state();
        state.commit = commit.filter(|text| !text.is_empty());
        state.delete_backward = delete_backward;
        Ok(state)
    }

    pub fn state(&mut self) -> MobileState {
        let input = self.engine.composition().text().to_string();
        let mut preedit = input.clone();
        self.visible.clear();
        let mut page_count = 0;
        if !input.is_empty()
            && let Ok(mut query) = self.engine.query()
        {
            preedit = query.marked_text();
            page_count = query.candidates.items.len().div_ceil(9);
            self.page = self.page.min(page_count.saturating_sub(1));
            query.candidates.items = query
                .candidates
                .items
                .into_iter()
                .skip(self.page * 9)
                .take(9)
                .collect();
            self.engine.annotate(&mut query.candidates);
            self.visible = query.candidates.items;
        }
        self.engine.note_displayed(self.visible.iter());
        let candidates = self
            .visible
            .iter()
            .enumerate()
            .map(|(id, candidate)| {
                let senses = candidate
                    .translation
                    .as_ref()
                    .map(|t| t.senses())
                    .unwrap_or(&[]);
                let annotation = senses
                    .iter()
                    .map(|sense| {
                        let pos = sense.part_of_speech.map(|p| p.abbreviation()).unwrap_or("");
                        let reading = sense.reading.as_deref().unwrap_or("");
                        format!("{pos} {} {reading}", sense.text).trim().to_string()
                    })
                    .collect::<Vec<_>>()
                    .join(" / ");
                MobileCandidate {
                    id,
                    text: candidate.text.clone(),
                    annotation,
                    vocabulary_levels: if self.language == "en" {
                        crate::vocabulary::english_levels(
                            senses.iter().map(|sense| sense.text.as_str()),
                        )
                    } else {
                        Vec::new()
                    },
                    pronunciation: if self.language == "en" {
                        senses
                            .first()
                            .and_then(|sense| self.pronunciation.as_ref()?.lookup(&sense.text))
                    } else {
                        None
                    },
                    fresh: senses.iter().any(|s| s.fresh),
                }
            })
            .collect();
        MobileState {
            revision: self.revision,
            input,
            preedit,
            candidates,
            english: self.english,
            language: self.language.clone(),
            page: self.page,
            page_count,
            ..Default::default()
        }
    }
}

impl Drop for Session {
    fn drop(&mut self) {
        self.engine.flush_learning();
    }
}
