//! 复用青简内核的移动会话，保存候选快照，避免点选时查询变化。
#[cfg(test)]
use crate::keypad::t9_readings;
use crate::keypad::{
    keypad_code, next_syllables, normalize_prefix, prefix_code, t9_readings_with_prefix,
};
use crate::model::{MobileCandidate, MobileState, Request, TranslationSense};
use qingjian_core::{Candidate, CandidateKind, Engine, Language, Translator};
use qingjian_dictionary::{Dictionary, WordList};
use qingjian_learning::{FrequencyLearner, VocabularyBook};
use qingjian_translate::Glossary;
use std::collections::HashMap;
use std::path::{Path, PathBuf};

const NORMAL_PAGE_SIZE: usize = 9;
const EXPANDED_PAGE_SIZE: usize = 36;
const MAX_T9_READINGS: usize = crate::keypad::MAX_READINGS;
const T9_CANDIDATES_PER_READING: usize = EXPANDED_PAGE_SIZE;
const MAX_T9_CANDIDATES: usize = MAX_T9_READINGS * T9_CANDIDATES_PER_READING;

#[derive(Clone, Debug)]
struct T9ChoicePreference {
    count: u32,
    reading: String,
}

pub struct Session {
    engine: Engine,
    pronunciation: Option<wordtrail_pronunciation::PronunciationDictionary>,
    data_dir: PathBuf,
    language: String,
    english: bool,
    visible: Vec<Candidate>,
    revision: u64,
    page: usize,
    vocabulary_targets: u16,
    expanded: bool,
    keypad_input: String,
    keypad_readings: Vec<String>,
    keypad_selected_reading: String,
    keypad_confirmed: Vec<String>,
    keypad_candidates: Vec<(Candidate, String)>,
    pinyin_frequencies: HashMap<String, u64>,
    visible_readings: Vec<String>,
    t9_choices_path: PathBuf,
    t9_choices: HashMap<(String, String), T9ChoicePreference>,
    t9_choices_dirty: bool,
    private: bool,
}

fn data_file(dir: &Path, stem: &str) -> PathBuf {
    let packed = dir.join(format!("{stem}.qj"));
    if packed.is_file() {
        packed
    } else {
        dir.join(format!("{stem}.tsv"))
    }
}

fn pinyin_frequencies(dictionary: &Dictionary) -> HashMap<String, u64> {
    let mut frequencies = HashMap::new();
    for entry in dictionary.entries() {
        *frequencies.entry(entry.pinyin.to_owned()).or_default() += u64::from(entry.frequency);
    }
    frequencies
}

fn glossary(dir: &Path, language: &str) -> Result<Box<dyn Translator>, String> {
    let lang = match language {
        "en" => Language::English,
        "ja" => Language::Japanese,
        "es" => Language::Spanish,
        _ => return Err("unsupported learning language".into()),
    };
    let base = Glossary::from_path(lang, data_file(dir, &format!("glossary-{language}")))
        .map_err(|e| e.to_string())?;
    Ok(Box::new(
        wordtrail_vocabulary::expansion::ExpandedTranslator::new(Box::new(base)),
    ))
}

impl Session {
    pub fn new(request: &Request) -> Result<Self, String> {
        let vocabulary_targets = wordtrail_vocabulary::selection(&request.vocabulary_targets)?;
        wordtrail_vocabulary::initialize();
        let data_dir = PathBuf::from(&request.data_dir);
        let user_dir = PathBuf::from(&request.user_dir);
        if request.data_dir.is_empty() || request.user_dir.is_empty() {
            return Err("data_dir and user_dir are required".into());
        }
        std::fs::create_dir_all(&user_dir).map_err(|e| e.to_string())?;
        let t9_choices_path = user_dir.join("user-t9-choices.tsv");
        let t9_choices = load_t9_choices(&t9_choices_path);
        let dictionary =
            Dictionary::from_path(data_file(&data_dir, "dict")).map_err(|e| e.to_string())?;
        let pinyin_frequencies = pinyin_frequencies(&dictionary);
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
            .with_translator(translator)
            .with_learner(Box::new(learner))
            .with_vocabulary_tracker(Box::new(VocabularyBook::open(
                user_dir.join("user-vocab.tsv"),
            )));
        // 兼容不含英文数据的旧测试夹具；正式数据包同时包含词表和英中释义。
        if data_dir.join("english.tsv").is_file() {
            engine = engine.with_english(WordList::from_path(data_dir.join("english.tsv")).map_err(|e| e.to_string())?);
        }
        if data_file(&data_dir, "glossary-zh").is_file() {
            engine = engine.with_english_translator(Box::new(Glossary::from_path(Language::Chinese, data_file(&data_dir, "glossary-zh")).map_err(|e| e.to_string())?));
        }
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
            vocabulary_targets,
            expanded: false,
            keypad_input: String::new(),
            keypad_readings: Vec::new(),
            keypad_selected_reading: String::new(),
            keypad_confirmed: Vec::new(),
            keypad_candidates: Vec::new(),
            pinyin_frequencies,
            visible_readings: Vec::new(),
            t9_choices_path,
            t9_choices,
            t9_choices_dirty: false,
            private: request.private,
        })
    }

    fn restore_reading(&mut self, reading: &str) {
        self.engine.clear();
        for key in reading.chars() {
            self.engine.push(key);
        }
    }

    fn learn_t9_choice(&mut self, candidate: &Candidate, reading: &str) {
        if !self.private && !self.keypad_input.is_empty() {
            let key = (self.keypad_input.clone(), candidate.text.clone());
            let preference = self
                .t9_choices
                .entry(key)
                .or_insert_with(|| T9ChoicePreference {
                    count: 0,
                    reading: String::new(),
                });
            preference.count = preference.count.saturating_add(1);
            preference.reading = reading.to_owned();
            self.t9_choices_dirty = true;
        }
    }

    fn refresh_keypad(&mut self) {
        if self.keypad_input.is_empty() {
            self.keypad_readings.clear();
            self.keypad_selected_reading.clear();
            self.keypad_confirmed.clear();
            self.keypad_candidates.clear();
            self.visible_readings.clear();
            self.engine.clear();
            return;
        }
        normalize_prefix(&self.keypad_input, &mut self.keypad_confirmed);
        self.keypad_readings = t9_readings_with_prefix(
            &self.keypad_input,
            &self.pinyin_frequencies,
            &self.keypad_confirmed,
        );
        let input = self.keypad_input.clone();
        if !self.keypad_readings.contains(&self.keypad_selected_reading) {
            self.keypad_selected_reading.clear();
        }
        if let Some(preferred) = self
            .t9_choices
            .iter()
            .filter(|((digits, _), preference)| {
                digits == &input && self.keypad_readings.contains(&preference.reading)
            })
            .max_by_key(|(_, preference)| preference.count)
            .map(|(_, preference)| preference.reading.clone())
        {
            self.keypad_readings
                .sort_by_key(|reading| reading != &preferred);
        }
        self.keypad_candidates.clear();
        for reading in self.keypad_readings.clone() {
            self.restore_reading(&reading);
            let Ok(mut query) = self.engine.query() else {
                continue;
            };
            self.engine.annotate(&mut query.candidates);
            for mut candidate in query
                .candidates
                .items
                .into_iter()
                .take(T9_CANDIDATES_PER_READING)
            {
                wordtrail_vocabulary::prioritize(&mut candidate, self.vocabulary_targets);
                if self
                    .keypad_candidates
                    .iter()
                    .any(|(known, _)| known.text == candidate.text && known.kind == candidate.kind)
                {
                    continue;
                }
                self.keypad_candidates.push((candidate, reading.clone()));
                if self.keypad_candidates.len() >= MAX_T9_CANDIDATES {
                    break;
                }
            }
            if self.keypad_candidates.len() >= MAX_T9_CANDIDATES {
                break;
            }
        }
        self.keypad_candidates.sort_by(|a, b| {
            let a_count = self
                .t9_choices
                .get(&(input.clone(), a.0.text.clone()))
                .map(|preference| preference.count)
                .unwrap_or_default();
            let b_count = self
                .t9_choices
                .get(&(input.clone(), b.0.text.clone()))
                .map(|preference| preference.count)
                .unwrap_or_default();
            b_count.cmp(&a_count)
        });
    }

    fn raw(&mut self) -> String {
        if !self.keypad_input.is_empty() {
            let digits = std::mem::take(&mut self.keypad_input);
            self.keypad_readings.clear();
            self.keypad_candidates.clear();
            self.keypad_selected_reading.clear();
            self.keypad_confirmed.clear();
            self.visible_readings.clear();
            self.engine.clear();
            return digits;
        }
        let text = self.engine.composition().text().to_string();
        self.engine.clear();
        self.engine.note_displayed(std::iter::empty());
        self.visible.clear();
        text
    }

    fn commit_keypad_candidate(
        &mut self,
        candidate: &Candidate,
        reading: &str,
        sense: Option<usize>,
    ) -> Result<String, String> {
        if let Some(index) = sense {
            if candidate
                .translation
                .as_ref()
                .and_then(|t| t.senses().get(index))
                .is_none()
            {
                return Err("candidate has no translation".into());
            }
        } else {
            self.learn_t9_choice(candidate, reading);
        }
        let original_len = self.keypad_input.len();
        self.restore_reading(reading);
        let text = if let Some(index) = sense {
            self.engine
                .commit_translation(candidate, index)
                .ok_or("candidate has no translation")?
        } else {
            self.engine.commit(candidate)
        };
        let remaining: String = self
            .engine
            .composition()
            .text()
            .chars()
            .filter_map(keypad_code)
            .collect();
        let mut consumed = original_len.saturating_sub(remaining.len());
        while !self.keypad_confirmed.is_empty() && consumed > 0 {
            consumed = consumed.saturating_sub(self.keypad_confirmed.remove(0).len());
        }
        self.keypad_input = remaining;
        self.keypad_selected_reading.clear();
        self.page = 0;
        self.refresh_keypad();
        Ok(text)
    }

    fn first(&mut self) -> String {
        if let Some(candidate) = self.visible.first().cloned() {
            if let Some(reading) = self.visible_readings.first().cloned() {
                return self
                    .commit_keypad_candidate(&candidate, &reading, None)
                    .unwrap_or_default();
            }
            self.engine.commit(&candidate)
        } else {
            self.raw()
        }
    }

    pub fn action(&mut self, request: &Request) -> Result<MobileState, String> {
        let mut commit = None;
        let mut delete_backward = false;
        match request.op.as_str() {
            "literal" => {
                let mut chars = request.text.chars();
                let symbol = chars.next().ok_or("empty literal")?;
                if chars.next().is_some() {
                    return Err("literal must be one character".into());
                }
                let mut text = if self.english { self.raw() } else { self.first() };
                text.push(symbol);
                commit = Some(text);
                self.page = 0;
            }
            "key" => {
                if !self.keypad_input.is_empty() {
                    let mut text = if self.english { self.raw() } else { self.first() };
                    let key = request.text.chars().next().ok_or("empty key")?;
                    text.push(if !self.english {
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
                    });
                    commit = Some(text);
                    self.page = 0;
                } else {
                    self.page = 0;
                    let mut chars = request.text.chars();
                    let key = chars.next().ok_or("empty key")?;
                    if chars.next().is_some() {
                        return Err("key must be one character".into());
                    }
                    if key.is_ascii_alphabetic() || key == '\'' {
                        if self.engine.composition().text().len() < 96 {
                            self.engine.push(if self.english { key } else { key.to_ascii_lowercase() });
                        }
                    } else {
                        let mut text = if self.english { self.raw() } else { self.first() };
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
            }
            "keypad" => {
                if request.text.len() != 1 || !matches!(request.text.as_bytes()[0], b'2'..=b'9') {
                    return Err("九键只接受 2 到 9".into());
                }
                if self.keypad_input.len() < 48 {
                    self.keypad_input.push_str(&request.text);
                    self.page = 0;
                    self.refresh_keypad();
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
                let sense = (request.op == "translation").then_some(request.sense_index);
                commit = if let Some(reading) = self.visible_readings.get(request.index).cloned() {
                    Some(self.commit_keypad_candidate(&candidate, &reading, sense)?)
                } else if let Some(index) = sense {
                    Some(
                        self.engine
                            .commit_translation(&candidate, index)
                            .ok_or("candidate has no translation")?,
                    )
                } else {
                    Some(self.engine.commit(&candidate))
                };
            }
            "space" => {
                commit = Some(if self.english {
                    format!("{} ", self.raw())
                } else if self.engine.composition().is_empty() {
                    " ".into()
                } else {
                    self.first()
                })
            }
            "enter" => {
                commit = Some(if !self.keypad_input.is_empty() {
                    self.first()
                } else if self.engine.composition().is_empty() {
                    "\n".into()
                } else {
                    self.raw()
                })
            }
            "backspace" => {
                self.page = 0;
                if !self.keypad_input.is_empty() {
                    self.keypad_input.pop();
                    self.refresh_keypad();
                } else {
                    delete_backward = !self.engine.backspace();
                }
            }
            "toggle" => {
                let mut text = if self.keypad_input.is_empty() {
                    self.raw()
                } else {
                    self.first()
                };
                if !self.keypad_input.is_empty() {
                    text.push_str(&self.raw());
                }
                commit = Some(text);
                self.english = !self.english;
                self.engine.set_english_mode(self.english);
            }
            "clear" => {
                self.raw();
                self.page = 0;
                self.expanded = false;
            }
            "reset" => {
                self.expanded = false;
                self.raw();
                self.page = 0;
                self.private = request.private;
                self.engine.set_private(request.private);
            }
            "candidate_layout" => {
                self.expanded = request.expanded;
                self.page = 0;
            }
            "keypad_syllable" => {
                if request.index != self.keypad_confirmed.len()
                    || !next_syllables(
                        &self.keypad_input,
                        &self.keypad_confirmed,
                        &self.pinyin_frequencies,
                    )
                    .contains(&request.reading)
                {
                    return Err("拼音选择已更新，请重新选择".into());
                }
                self.keypad_confirmed.push(request.reading.clone());
                self.keypad_selected_reading.clear();
                self.page = 0;
                self.refresh_keypad();
            }
            "keypad_reading_back" => {
                self.keypad_confirmed.pop();
                self.keypad_selected_reading.clear();
                self.page = 0;
                if !self.keypad_input.is_empty() {
                    self.refresh_keypad();
                }
            }
            "keypad_reading" => {
                if !request.reading.is_empty() && !self.keypad_readings.contains(&request.reading) {
                    return Err("九键读音已更新，请重新选择".into());
                }
                self.keypad_confirmed.clear();
                self.keypad_selected_reading = request.reading.clone();
                self.page = 0;
                if !self.keypad_input.is_empty() {
                    self.refresh_keypad();
                }
            }
            "next_page" => self.page += 1,
            "previous_page" => self.page = self.page.saturating_sub(1),
            "language" => {
                let translator = glossary(&self.data_dir, &request.language)?;
                self.engine.set_translator(translator);
                self.language = request.language.clone();
                if !self.keypad_input.is_empty() {
                    self.refresh_keypad();
                }
            }
            "flush" => {
                self.engine.flush_learning();
                self.flush_t9_choices();
            }
            "vocabulary" => {
                self.vocabulary_targets =
                    wordtrail_vocabulary::selection(&request.vocabulary_targets)?;
                if !self.keypad_input.is_empty() {
                    self.refresh_keypad();
                }
            }
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
        let input = if self.keypad_input.is_empty() {
            self.engine.composition().text().to_string()
        } else {
            self.keypad_input.clone()
        };
        if input.is_empty() {
            self.expanded = false;
        }
        let mut preedit = if self.keypad_input.is_empty() {
            input.clone()
        } else if self.keypad_selected_reading.is_empty() {
            self.keypad_readings.first().cloned().unwrap_or_default()
        } else {
            self.keypad_selected_reading.clone()
        };
        self.visible.clear();
        self.visible_readings.clear();
        let mut page_count = 0;
        if !self.keypad_input.is_empty() {
            let pool: Vec<(Candidate, String)> = if self.keypad_selected_reading.is_empty() {
                self.keypad_candidates.clone()
            } else {
                self.keypad_candidates
                    .iter()
                    .filter(|(_, reading)| reading == &self.keypad_selected_reading)
                    .cloned()
                    .collect()
            };
            let page_size = if self.expanded {
                EXPANDED_PAGE_SIZE
            } else {
                NORMAL_PAGE_SIZE
            };
            page_count = pool.len().div_ceil(page_size);
            self.page = self.page.min(page_count.saturating_sub(1));
            let start = self.page * page_size;
            for (candidate, reading) in pool.into_iter().skip(start).take(page_size) {
                self.visible.push(candidate);
                self.visible_readings.push(reading);
            }
        } else if !input.is_empty()
            && let Ok(mut query) = self.engine.query()
        {
            preedit = query.marked_text();
            crate::symbols::insert(&input, &mut query.candidates.items);
            let page_size = if self.expanded {
                EXPANDED_PAGE_SIZE
            } else {
                NORMAL_PAGE_SIZE
            };
            page_count = query.candidates.items.len().div_ceil(page_size);
            self.page = self.page.min(page_count.saturating_sub(1));
            query.candidates.items = query
                .candidates
                .items
                .into_iter()
                .skip(self.page * page_size)
                .take(page_size)
                .collect();
            self.engine.annotate(&mut query.candidates);
            for candidate in &mut query.candidates.items {
                if candidate.kind != CandidateKind::English {
                    wordtrail_vocabulary::prioritize(candidate, self.vocabulary_targets);
                }
            }
            self.visible = query.candidates.items;
        }
        let shown: Vec<_> = self
            .visible
            .iter()
            .map(|c| wordtrail_vocabulary::expansion::displayed(c, 1))
            .collect();
        self.engine.note_displayed(shown.iter());
        let candidates = self
            .visible
            .iter()
            .enumerate()
            .map(|(id, candidate)| {
                let english_word = candidate.kind == CandidateKind::English;
                let english_senses = !english_word && self.language == "en";
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
                    kind: if english_word { "english" } else if candidate.kind == CandidateKind::Shortcut { "symbol" } else { "chinese" },
                    word_tags: if english_word { wordtrail_vocabulary::tags(&candidate.text.to_lowercase(), self.vocabulary_targets) } else { Vec::new() },
                    annotation,
                    vocabulary_levels: if english_senses {
                        crate::vocabulary::english_levels(
                            senses.iter().map(|sense| sense.text.as_str()),
                        )
                    } else {
                        Vec::new()
                    },
                    translation_senses: senses
                        .iter()
                        .enumerate()
                        .map(|(index, sense)| TranslationSense {
                            index,
                            text: sense.text.clone(),
                            part_of_speech: sense
                                .part_of_speech
                                .map(|pos| pos.abbreviation().to_owned()),
                            reading: sense.reading.clone(),
                            fresh: sense.fresh,
                            tags: if english_senses {
                                wordtrail_vocabulary::tags(&sense.text, self.vocabulary_targets)
                            } else {
                                Vec::new()
                            },
                            pronunciation: if english_senses {
                                self.pronunciation
                                    .as_ref()
                                    .and_then(|dictionary| dictionary.lookup(&sense.text))
                            } else {
                                None
                            },
                            translation_source: if english_senses {
                                wordtrail_vocabulary::expansion::source(
                                    &candidate.text,
                                    &sense.text,
                                )
                            } else {
                                None
                            },
                        })
                        .collect(),
                    pronunciation: if english_word {
                        self.pronunciation.as_ref().and_then(|dictionary| dictionary.lookup(&candidate.text.to_lowercase()))
                    } else if english_senses {
                        senses
                            .first()
                            .and_then(|sense| self.pronunciation.as_ref()?.lookup(&sense.text))
                    } else {
                        None
                    },
                    fresh: senses.first().is_some_and(|s| s.fresh),
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
            expanded: self.expanded,
            readings: if self.keypad_input.is_empty() {
                Vec::new()
            } else {
                self.keypad_readings
                    .iter()
                    .take(MAX_T9_READINGS)
                    .cloned()
                    .collect()
            },
            selected_reading: self.keypad_selected_reading.clone(),
            reading_prefix: self.keypad_confirmed.clone(),
            syllable_choices: next_syllables(
                &self.keypad_input,
                &self.keypad_confirmed,
                &self.pinyin_frequencies,
            ),
            reading_complete: !self.keypad_input.is_empty()
                && prefix_code(&self.keypad_confirmed).len() == self.keypad_input.len(),
            vocabulary_targets: wordtrail_vocabulary::selected_ids(self.vocabulary_targets),
            ..Default::default()
        }
    }

    fn flush_t9_choices(&mut self) {
        if !self.t9_choices_dirty {
            return;
        }
        let mut rows: Vec<_> = self.t9_choices.iter().collect();
        rows.sort_by(|a, b| a.0.0.cmp(&b.0.0).then_with(|| a.0.1.cmp(&b.0.1)));
        let result = qingjian_core::storage::write_atomic(&self.t9_choices_path, |file| {
            use std::io::Write;
            writeln!(file, "# 词伴九键个人选择：按键码\t候选词\t选择次数")?;
            for ((digits, word), preference) in &rows {
                writeln!(
                    file,
                    "{digits}\t{word}\t{}\t{}",
                    preference.count, preference.reading
                )?;
            }
            Ok(())
        });
        match result {
            Ok(()) => self.t9_choices_dirty = false,
            Err(error) => eprintln!(
                "九键学习数据保存失败：{}：{error}",
                self.t9_choices_path.display()
            ),
        }
    }
}

impl Drop for Session {
    fn drop(&mut self) {
        self.engine.flush_learning();
        self.flush_t9_choices();
    }
}

fn load_t9_choices(path: &Path) -> HashMap<(String, String), T9ChoicePreference> {
    let Ok(source) = std::fs::read_to_string(path) else {
        return HashMap::new();
    };
    source
        .lines()
        .filter(|line| !line.trim().is_empty() && !line.trim_start().starts_with('#'))
        .filter_map(|line| {
            let mut fields = line.split('\t');
            let digits = fields.next()?.to_owned();
            let word = fields.next()?.to_owned();
            let count = fields.next()?.parse::<u32>().ok()?;
            let reading = fields.next().unwrap_or_default().to_owned();
            (!digits.is_empty()
                && digits.bytes().all(|key| (b'2'..=b'9').contains(&key))
                && !word.is_empty()
                && count > 0)
                .then_some(((digits, word), T9ChoicePreference { count, reading }))
        })
        .collect()
}

#[cfg(test)]
mod tests {
    use super::{Session, data_file, pinyin_frequencies, t9_readings};
    use crate::model::Request;
    use qingjian_dictionary::Dictionary;
    use std::collections::HashMap;
    use std::path::PathBuf;

    #[test]
    fn t9_decoder_keeps_the_common_ni_hao_reading() {
        let project = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .expect("workspace root")
            .to_owned();
        let dictionary = Dictionary::from_path(data_file(&project.join("data"), "dict"))
            .expect("load the bundled dictionary");
        let frequencies = pinyin_frequencies(&dictionary);
        let readings = t9_readings("64426", &frequencies);
        assert!(
            readings.iter().any(|reading| reading == "ni'hao"),
            "{readings:?}"
        );
        assert_eq!(
            readings.first().map(String::as_str),
            Some("ni'hao"),
            "{readings:?}"
        );
    }

    #[test]
    fn t9_decoder_returns_abbreviated_readings_for_partial_input() {
        let readings = t9_readings("6", &HashMap::new());
        assert!(
            readings.iter().any(|reading| reading == "n"),
            "{readings:?}"
        );
    }

    #[test]
    fn t9_decoder_rejects_non_keypad_input() {
        assert!(t9_readings("20", &HashMap::new()).is_empty());
        assert!(t9_readings("", &HashMap::new()).is_empty());
    }

    #[test]
    fn nine_key_session_can_surface_ni_hao_candidates() {
        let project = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .expect("workspace root")
            .to_owned();
        let user_dir = std::env::temp_dir().join(format!(
            "wordtrail-mobile-t9-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        let request = Request {
            op: "create".into(),
            handle: 0,
            text: String::new(),
            index: 0,
            revision: None,
            language: "en".into(),
            data_dir: project.join("data").to_string_lossy().into_owned(),
            user_dir: user_dir.to_string_lossy().into_owned(),
            private: false,
            vocabulary_targets: Vec::new(),
            sense_index: 0,
            expanded: false,
            reading: String::new(),
        };
        let mut session = Session::new(&request).expect("load the bundled local dictionary");
        let mut elapsed = std::time::Duration::ZERO;
        for digit in "64426".chars() {
            let start = std::time::Instant::now();
            session
                .action(&Request {
                    op: "keypad".into(),
                    text: digit.to_string(),
                    ..request_for_action()
                })
                .expect("accept a 9-key digit");
            elapsed += start.elapsed();
        }
        let state = session.state();
        assert!(
            state.readings.iter().any(|reading| reading == "ni'hao"),
            "{:?}",
            state.readings
        );
        let selected = session
            .action(&Request {
                op: "keypad_reading".into(),
                reading: "ni'hao".into(),
                ..request_for_action()
            })
            .expect("choose the nihao reading");
        assert!(
            selected
                .candidates
                .iter()
                .any(|candidate| candidate.text.starts_with("你好")),
            "{:?}",
            selected
                .candidates
                .iter()
                .map(|candidate| candidate.text.as_str())
                .collect::<Vec<_>>()
        );
        let picked = selected.candidates[0].text.clone();
        let commit = session
            .action(&Request {
                op: "select".into(),
                index: selected.candidates[0].id,
                revision: Some(selected.revision),
                ..request_for_action()
            })
            .expect("commit a selected 9-key candidate");
        assert_eq!(commit.commit.as_deref(), Some(picked.as_str()));
        for digit in "64426".chars() {
            session
                .action(&Request {
                    op: "keypad".into(),
                    text: digit.to_string(),
                    ..request_for_action()
                })
                .expect("repeat the 9-key input");
        }
        assert_eq!(session.state().candidates[0].text, picked);
        drop(session);
        let learned = std::fs::read_to_string(user_dir.join("user-t9-choices.tsv"))
            .expect("persist local 9-key preference");
        assert!(learned.contains(&format!("64426\t{picked}\t1")));
        let mut reopened = Session::new(&request).expect("reload local 9-key learning");
        for digit in "64426".chars() {
            reopened
                .action(&Request {
                    op: "keypad".into(),
                    text: digit.to_string(),
                    ..request_for_action()
                })
                .expect("type after reopening the session");
        }
        assert_eq!(reopened.state().candidates[0].text, picked);
        reopened.private = true;
        reopened.engine.set_private(true);
        reopened.expanded = true;
        let cleared = reopened
            .action(&Request {
                op: "clear".into(),
                ..request_for_action()
            })
            .expect("clear only the current composition");
        assert!(cleared.input.is_empty());
        assert!(cleared.commit.is_none());
        assert!(!cleared.delete_backward);
        assert!(!cleared.expanded);
        assert!(reopened.private, "clear must preserve privacy mode");
        for symbol in ["M", "6", "?", "."] {
            let literal = reopened
                .action(&Request {
                    op: "literal".into(),
                    text: symbol.into(),
                    ..request_for_action()
                })
                .expect("commit the exact long-press character");
            assert_eq!(literal.commit.as_deref(), Some(symbol));
            assert!(literal.input.is_empty(), "letters must not become pinyin");
            assert!(!literal.english, "long press must not change input mode");
            assert!(reopened.private, "long press must preserve privacy mode");
        }
        for digit in "64426".chars() {
            reopened
                .action(&Request {
                    op: "keypad".into(),
                    text: digit.to_string(),
                    ..request_for_action()
                })
                .unwrap();
        }
        let literal = reopened
            .action(&Request {
                op: "literal".into(),
                text: "M".into(),
                ..request_for_action()
            })
            .expect("finalize composing Chinese before a literal character");
        assert_eq!(
            literal.commit.as_deref(),
            Some(format!("{picked}M").as_str())
        );
        assert!(literal.input.is_empty());
        drop(reopened);
        let _ = std::fs::remove_dir_all(user_dir);
    }

    #[test]
    fn progressive_reading_filters_can_backtrack_and_keep_uncommitted_digits() {
        let project = PathBuf::from(env!("CARGO_MANIFEST_DIR"))
            .parent()
            .unwrap()
            .to_owned();
        let user_dir = std::env::temp_dir().join(format!(
            "wordtrail-step-test-{}-{}",
            std::process::id(),
            std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap()
                .as_nanos()
        ));
        let request = Request {
            data_dir: project.join("data").to_string_lossy().into_owned(),
            user_dir: user_dir.to_string_lossy().into_owned(),
            private: true,
            ..request_for_action()
        };
        let mut session = Session::new(&request).unwrap();
        for digit in "96968329".chars() {
            session
                .action(&Request {
                    op: "keypad".into(),
                    text: digit.to_string(),
                    ..request_for_action()
                })
                .unwrap();
        }
        let initial = session.state();
        assert!(initial.syllable_choices.iter().any(|s| s == "wo"));
        for (step, syllable) in ["wo", "you", "fa", "x"].into_iter().enumerate() {
            let state = session
                .action(&Request {
                    op: "keypad_syllable".into(),
                    index: step,
                    reading: syllable.into(),
                    ..request_for_action()
                })
                .unwrap();
            assert_eq!(state.reading_prefix.len(), step + 1);
            assert!(state.commit.is_none());
            assert_eq!(state.input, "96968329");
            assert!(state.syllable_choices.iter().all(|s| !s.contains('\'')));
            assert!(session.private);
        }
        let complete = session.state();
        assert!(complete.reading_complete);
        assert!(complete.syllable_choices.is_empty());
        assert_eq!(complete.readings, vec!["wo'you'fa'x"]);
        assert!(
            session
                .action(&Request {
                    op: "keypad_syllable".into(),
                    index: 0,
                    reading: "wo".into(),
                    ..request_for_action()
                })
                .is_err()
        );
        let back = session
            .action(&Request {
                op: "keypad_reading_back".into(),
                ..request_for_action()
            })
            .unwrap();
        assert_eq!(back.reading_prefix, vec!["wo", "you", "fa"]);
        assert!(back.syllable_choices.iter().any(|s| s == "x"));
        let reset = session
            .action(&Request {
                op: "keypad_reading".into(),
                ..request_for_action()
            })
            .unwrap();
        assert!(reset.reading_prefix.is_empty());
        assert_eq!(reset.input, "96968329");
        session
            .action(&Request {
                op: "keypad_syllable".into(),
                reading: "wo".into(),
                ..request_for_action()
            })
            .unwrap();
        let expanded = session
            .action(&Request {
                op: "candidate_layout".into(),
                expanded: true,
                ..request_for_action()
            })
            .unwrap();
        let wo = expanded
            .candidates
            .iter()
            .find(|c| c.text == "我")
            .expect("我 is available after locking wo");
        let committed = session
            .action(&Request {
                op: "select".into(),
                index: wo.id,
                revision: Some(expanded.revision),
                ..request_for_action()
            })
            .unwrap();
        assert_eq!(committed.commit.as_deref(), Some("我"));
        assert_eq!(committed.input, "968329");
        assert!(committed.reading_prefix.is_empty());
        assert!(committed.syllable_choices.iter().any(|s| s == "you"));
        assert!(
            !session.t9_choices_dirty,
            "private progressive input must not learn choices"
        );
        let english = session
            .action(&Request {
                op: "toggle".into(),
                ..request_for_action()
            })
            .unwrap();
        assert!(english.english);
        assert!(english.input.is_empty());
        assert!(english.reading_prefix.is_empty());
        drop(session);
        let resolved = user_dir.canonicalize().unwrap();
        assert!(resolved.starts_with(std::env::temp_dir().canonicalize().unwrap()));
        std::fs::remove_dir_all(resolved).unwrap();
    }

    fn request_for_action() -> Request {
        Request {
            op: String::new(),
            handle: 0,
            text: String::new(),
            index: 0,
            revision: None,
            language: "en".into(),
            data_dir: String::new(),
            user_dir: String::new(),
            private: false,
            vocabulary_targets: Vec::new(),
            sense_index: 0,
            expanded: false,
            reading: String::new(),
        }
    }
}
