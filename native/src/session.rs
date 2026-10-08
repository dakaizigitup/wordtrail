//! 复用青简内核的移动会话，保存候选快照，避免点选时查询变化。
use crate::model::{MobileCandidate, MobileState, Request, TranslationSense};
use qingjian_core::{Candidate, Engine, Language, Translator};
use qingjian_dictionary::Dictionary;
use qingjian_learning::{FrequencyLearner, VocabularyBook};
use qingjian_translate::Glossary;
use std::collections::HashMap;
use std::path::{Path, PathBuf};

const NORMAL_PAGE_SIZE: usize = 9;
const EXPANDED_PAGE_SIZE: usize = 36;
const MAX_T9_READINGS: usize = 24;
const MAX_T9_PARTIAL_READINGS: usize = 96;
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

fn keypad_code(letter: char) -> Option<char> {
    match letter {
        'a'..='c' => Some('2'),
        'd'..='f' => Some('3'),
        'g'..='i' => Some('4'),
        'j'..='l' => Some('5'),
        'm'..='o' => Some('6'),
        'p'..='s' => Some('7'),
        't'..='v' => Some('8'),
        'w'..='z' => Some('9'),
        _ => None,
    }
}

fn keypad_letter_cost(letter: char) -> u32 {
    match letter {
        // A small Pinyin prior makes familiar initials such as n-, h-, and z- appear first.
        // Every letter still remains reachable through the reading selector.
        'a' | 'd' | 'h' | 'j' | 'n' | 's' | 't' | 'y' | 'z' => 0,
        'b' | 'e' | 'g' | 'i' | 'k' | 'm' | 'r' | 'u' => 1,
        'c' | 'f' | 'l' | 'o' | 'p' | 'v' | 'w' => 2,
        'q' | 'x' => 3,
        _ => 10,
    }
}

fn keep_reading(readings: &mut Vec<(String, u32)>, reading: String, cost: u32, limit: usize) {
    if readings.iter().any(|(known, _)| known == &reading) {
        return;
    }
    readings.push((reading, cost));
    readings.sort_by(|a, b| a.1.cmp(&b.1).then_with(|| a.0.cmp(&b.0)));
    readings.truncate(limit);
}

fn keep_finished_reading(
    readings: &mut Vec<(String, u32, u64)>,
    reading: String,
    cost: u32,
    frequency: u64,
) {
    if readings.iter().any(|(known, _, _)| known == &reading) {
        return;
    }
    readings.push((reading, cost, frequency));
    readings.sort_by(|a, b| {
        b.2.cmp(&a.2)
            .then_with(|| a.1.cmp(&b.1))
            .then_with(|| a.0.cmp(&b.0))
    });
    readings.truncate(MAX_T9_READINGS);
}

/// Convert an ambiguous 9-key sequence into a small, ranked set of legal Pinyin readings.
/// The dynamic program only follows complete syllables at internal boundaries, avoiding a
/// Cartesian expansion of every key's letters. The last syllable may remain abbreviated.
fn t9_readings(digits: &str, pinyin_frequencies: &HashMap<String, u64>) -> Vec<String> {
    if digits.is_empty() || !digits.bytes().all(|key| (b'2'..=b'9').contains(&key)) {
        return Vec::new();
    }
    let bytes = digits.as_bytes();
    let mut paths = vec![Vec::<(String, u32)>::new(); bytes.len() + 1];
    let mut finished = Vec::<(String, u32, u64)>::new();
    paths[0].push((String::new(), 0));

    for start in 0..bytes.len() {
        let prefixes = paths[start].clone();
        if prefixes.is_empty() {
            continue;
        }
        let remainder = &digits[start..];
        for (prefix, prefix_cost) in prefixes {
            for syllable in qingjian_core::parser::SYLLABLES {
                let code: String = syllable.chars().filter_map(keypad_code).collect();
                if code.len() <= remainder.len() && remainder.starts_with(&code) {
                    let end = start + code.len();
                    let reading = if prefix.is_empty() {
                        (*syllable).to_owned()
                    } else {
                        format!("{prefix}'{syllable}")
                    };
                    let cost = prefix_cost + syllable.chars().map(keypad_letter_cost).sum::<u32>();
                    if end == bytes.len() {
                        let frequency = pinyin_frequencies
                            .get(&reading.replace('\'', " "))
                            .copied()
                            .unwrap_or_default();
                        keep_finished_reading(&mut finished, reading, cost, frequency);
                    } else {
                        keep_reading(&mut paths[end], reading, cost, MAX_T9_PARTIAL_READINGS);
                    }
                }

                if code.len() > remainder.len() && code.starts_with(remainder) {
                    let partial_len = remainder.len();
                    let partial = &syllable[..partial_len];
                    if qingjian_core::parser::is_syllable(partial)
                        || qingjian_core::parser::is_syllable_prefix(partial)
                    {
                        let reading = if prefix.is_empty() {
                            partial.to_owned()
                        } else {
                            format!("{prefix}'{partial}")
                        };
                        let cost =
                            prefix_cost + partial.chars().map(keypad_letter_cost).sum::<u32>() + 6;
                        let frequency = pinyin_frequencies
                            .get(&reading.replace('\'', " "))
                            .copied()
                            .unwrap_or_default();
                        keep_finished_reading(&mut finished, reading, cost, frequency);
                    }
                }
            }
        }
    }
    finished
        .into_iter()
        .map(|(reading, _, _)| reading)
        .collect()
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
            self.keypad_candidates.clear();
            self.visible_readings.clear();
            self.engine.clear();
            return;
        }
        self.keypad_readings = t9_readings(&self.keypad_input, &self.pinyin_frequencies);
        let input = self.keypad_input.clone();
        self.keypad_selected_reading = self
            .t9_choices
            .iter()
            .filter(|((digits, _), preference)| {
                digits == &input && self.keypad_readings.contains(&preference.reading)
            })
            .max_by_key(|(_, preference)| preference.count)
            .map(|(_, preference)| preference.reading.clone())
            .or_else(|| self.keypad_readings.first().cloned())
            .unwrap_or_default();
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

    fn first(&mut self) -> String {
        if let Some(candidate) = self.visible.first().cloned() {
            if let Some(reading) = self.visible_readings.first().cloned() {
                self.learn_t9_choice(&candidate, &reading);
                self.restore_reading(&reading);
                self.keypad_input.clear();
                self.keypad_readings.clear();
                self.keypad_candidates.clear();
                self.keypad_selected_reading.clear();
                self.visible_readings.clear();
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
                let mut text = self.first();
                text.push(symbol);
                commit = Some(text);
                self.page = 0;
            }
            "key" => {
                if !self.keypad_input.is_empty() {
                    let mut text = self.first();
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
                if let Some(reading) = self.visible_readings.get(request.index).cloned() {
                    if request.op == "select" {
                        self.learn_t9_choice(&candidate, &reading);
                    }
                    self.restore_reading(&reading);
                    self.keypad_input.clear();
                    self.keypad_readings.clear();
                    self.keypad_candidates.clear();
                    self.keypad_selected_reading.clear();
                    self.visible_readings.clear();
                }
                commit = if request.op == "translation" {
                    Some(
                        self.engine
                            .commit_translation(&candidate, request.sense_index)
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
                commit = Some(if self.keypad_input.is_empty() {
                    self.raw()
                } else {
                    self.first()
                });
                self.english = !self.english;
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
            "keypad_reading" => {
                if !request.reading.is_empty() && !self.keypad_readings.contains(&request.reading) {
                    return Err("九键读音已更新，请重新选择".into());
                }
                self.keypad_selected_reading = request.reading.clone();
                self.page = 0;
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
                wordtrail_vocabulary::prioritize(candidate, self.vocabulary_targets);
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
                            tags: if self.language == "en" {
                                wordtrail_vocabulary::tags(&sense.text, self.vocabulary_targets)
                            } else {
                                Vec::new()
                            },
                            pronunciation: if self.language == "en" {
                                self.pronunciation
                                    .as_ref()
                                    .and_then(|dictionary| dictionary.lookup(&sense.text))
                            } else {
                                None
                            },
                            translation_source: if self.language == "en" {
                                wordtrail_vocabulary::expansion::source(
                                    &candidate.text,
                                    &sense.text,
                                )
                            } else {
                                None
                            },
                        })
                        .collect(),
                    pronunciation: if self.language == "en" {
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
        let cleared = reopened.action(&Request {
            op: "clear".into(),
            ..request_for_action()
        }).expect("clear only the current composition");
        assert!(cleared.input.is_empty());
        assert!(cleared.commit.is_none());
        assert!(!cleared.delete_backward);
        assert!(!cleared.expanded);
        assert!(reopened.private, "clear must preserve privacy mode");
        for symbol in ["M", "6", "?", "."] {
            let literal = reopened.action(&Request {
                op: "literal".into(),
                text: symbol.into(),
                ..request_for_action()
            }).expect("commit the exact long-press character");
            assert_eq!(literal.commit.as_deref(), Some(symbol));
            assert!(literal.input.is_empty(), "letters must not become pinyin");
            assert!(!literal.english, "long press must not change input mode");
            assert!(reopened.private, "long press must preserve privacy mode");
        }
        for digit in "64426".chars() {
            reopened.action(&Request {
                op: "keypad".into(),
                text: digit.to_string(),
                ..request_for_action()
            }).unwrap();
        }
        let literal = reopened.action(&Request {
            op: "literal".into(),
            text: "M".into(),
            ..request_for_action()
        }).expect("finalize composing Chinese before a literal character");
        assert_eq!(literal.commit.as_deref(), Some(format!("{picked}M").as_str()));
        assert!(literal.input.is_empty());
        drop(reopened);
        let _ = std::fs::remove_dir_all(user_dir);
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
