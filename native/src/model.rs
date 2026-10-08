//! 两端共用的请求与候选状态；平台只负责输入框和显示。
use serde::{Deserialize, Serialize};

#[derive(Deserialize)]
pub struct Request {
    pub op: String,
    #[serde(default)]
    pub handle: u64,
    #[serde(default)]
    pub text: String,
    #[serde(default)]
    pub index: usize,
    #[serde(default)]
    pub revision: Option<u64>,
    #[serde(default = "english")]
    pub language: String,
    #[serde(default)]
    pub data_dir: String,
    #[serde(default)]
    pub user_dir: String,
    #[serde(default)]
    pub private: bool,
    #[serde(default)]
    pub vocabulary_targets: Vec<String>,
    #[serde(default)]
    pub sense_index: usize,
    #[serde(default)]
    pub expanded: bool,
    #[serde(default)]
    pub reading: String,
}

fn english() -> String {
    "en".into()
}

#[derive(Serialize)]
pub struct VocabularyLevel {
    pub word: String,
    pub level: Option<String>,
}

#[derive(Serialize)]
pub struct MobileCandidate {
    pub id: usize,
    pub text: String,
    pub annotation: String,
    pub pronunciation: Option<wordtrail_pronunciation::Pronunciation>,
    pub vocabulary_levels: Vec<VocabularyLevel>,
    pub translation_senses: Vec<TranslationSense>,
    pub fresh: bool,
}

#[derive(Serialize)]
pub struct TranslationSense {
    pub index: usize,
    pub text: String,
    pub translation_source: Option<&'static str>,
    pub part_of_speech: Option<String>,
    pub reading: Option<String>,
    pub fresh: bool,
    pub tags: Vec<wordtrail_vocabulary::Tag>,
    pub pronunciation: Option<wordtrail_pronunciation::Pronunciation>,
}

#[derive(Default, Serialize)]
pub struct MobileState {
    pub revision: u64,
    pub input: String,
    pub preedit: String,
    pub candidates: Vec<MobileCandidate>,
    pub commit: Option<String>,
    pub delete_backward: bool,
    pub english: bool,
    pub language: String,
    pub page: usize,
    pub page_count: usize,
    pub expanded: bool,
    pub readings: Vec<String>,
    pub selected_reading: String,
    pub vocabulary_targets: Vec<&'static str>,
}

#[derive(Serialize)]
pub struct Response {
    pub handle: u64,
    pub state: Option<MobileState>,
    pub error: Option<String>,
}
