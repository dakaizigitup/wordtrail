//! Shared exam/domain membership and stable sense priority. Never ranks Chinese candidates.
pub mod expansion;
use qingjian_core::{Candidate, Language};
use serde::{Deserialize, Serialize};
use std::{borrow::Cow, collections::HashMap, path::Path, sync::LazyLock};

pub const CATEGORIES: [(&str, &str); 10] = [
    ("cet4", "四级"),
    ("cet6", "六级"),
    ("tem4", "专四"),
    ("tem8", "专八"),
    ("toefl", "托福"),
    ("ielts", "雅思"),
    ("computer", "计算机"),
    ("business", "商务"),
    ("medical", "医学"),
    ("administration", "行政学"),
];
const TSV: &str = include_str!("../data/english-tags.tsv");
const OPENETYMOLOGY_TSV: &str = include_str!("../data/openetymology-exam-tags.tsv");
const OPENETYMOLOGY_CET_TSV: &str = include_str!("../data/openetymology-cet-tags.tsv");
const PROFESSIONAL_TSV: &str = include_str!("../data/professional-domain-tags.tsv");
const CJK_COMPSCI_TSV: &str = include_str!("../data/cjk-compsci-tags.tsv");
const FIBO_BUSINESS_TSV: &str = include_str!("../data/fibo-business-tags.tsv");
const BETTER_QUANT_BUSINESS_TSV: &str = include_str!("../data/better-quant-business-tags.tsv");
const CFPB_FINANCE_TSV: &str = include_str!("../data/cfpb-finance-tags.tsv");
const FINANCE_I18N_TSV: &str = include_str!("../data/finance-i18n-tags.tsv");
const COMPUTERESE_TSV: &str = include_str!("../data/computerese-tags.tsv");
const MESH_MEDICAL_TSV: &str = include_str!("../data/mesh-medical-tags.tsv");
const WIKIDATA_MEDICAL_TSV: &str = include_str!("../data/wikidata-medical-tags.tsv");
const WIKIDATA_MEDICAL_2_TSV: &str = include_str!("../data/wikidata-medical-tags-2.tsv");
const NAER_MEDICAL_TSV: &str = include_str!("../data/naer-medical-tags.tsv");
const NAER_MEDICAL_2_TSV: &str = include_str!("../data/naer-medical-tags-2.tsv");
const NAER_LIFE_SCIENCE_TSV: &str = include_str!("../data/naer-life-science-tags.tsv");
const NAER_VETERINARY_TSV: &str = include_str!("../data/naer-veterinary-tags.tsv");
const NAER_ECONOMICS_TSV: &str = include_str!("../data/naer-economics-tags.tsv");
const NAER_ACCOUNTING_TSV: &str = include_str!("../data/naer-accounting-tags.tsv");
const NAER_MANAGEMENT_TSV: &str = include_str!("../data/naer-management-tags.tsv");
const NAER_COMPUTER_TSV: &str = include_str!("../data/naer-computer-tags.tsv");
const NAER_ADMINISTRATION_TSV: &str = include_str!("../data/naer-administration-tags.tsv");
const WORDLEVEL_TOEFL_IELTS_TSV: &str = include_str!("../data/wordlevel-toefl-ielts-tags.tsv");
static WORDS: LazyLock<HashMap<&'static str, Membership>> = LazyLock::new(|| {
    let mut words: HashMap<_, _> = TSV
        .lines()
        .map(|line| {
            let mut fields = line.split('\t');
            let word = fields.next().unwrap();
            let ecdict = fields.next().unwrap().parse().expect("valid ECDICT mask");
            let kylebing = fields.next().unwrap().parse().expect("valid KyleBing mask");
            (
                word,
                Membership {
                    ecdict,
                    kylebing,
                    ..Membership::default()
                },
            )
        })
        .collect();
    for line in OPENETYMOLOGY_TSV.lines() {
        let (word, mask) = line.split_once('\t').expect("valid OpenEtymology tag row");
        words.entry(word).or_default().openetymology =
            mask.parse().expect("valid OpenEtymology mask");
    }
    for line in OPENETYMOLOGY_CET_TSV.lines() {
        let (word, mask) = line
            .split_once('\t')
            .expect("valid OpenEtymology CET tag row");
        words.entry(word).or_default().openetymology |=
            mask.parse::<u16>().expect("valid OpenEtymology CET mask");
    }
    for line in PROFESSIONAL_TSV.lines() {
        let mut fields = line.split('\t');
        let word = fields.next().expect("professional tag has a word");
        let mask: u16 = fields
            .next()
            .expect("professional tag has a mask")
            .parse()
            .expect("valid professional category mask");
        let source = fields.next().expect("professional tag has a source");
        assert_eq!(source, "Wiktionary CC BY-SA 4.0");
        assert!(
            fields.next().is_none(),
            "unexpected professional tag column"
        );
        words.entry(word).or_default().professional = mask;
    }
    for line in CJK_COMPSCI_TSV.lines() {
        let mut fields = line.split('\t');
        let word = fields.next().expect("CJK computer-science tag has a word");
        let mask: u16 = fields
            .next()
            .expect("CJK computer-science tag has a mask")
            .parse()
            .expect("valid CJK computer-science mask");
        let source = fields
            .next()
            .expect("CJK computer-science tag has a source");
        assert_eq!(source, "CJK computer science terms CC BY-SA 4.0");
        assert!(
            fields.next().is_none(),
            "unexpected CJK computer-science tag column"
        );
        words.entry(word).or_default().cjk_compsci = mask;
    }
    for line in FIBO_BUSINESS_TSV.lines() {
        let mut fields = line.split('\t');
        let word = fields.next().expect("FIBO tag has a word");
        let mask: u16 = fields
            .next()
            .expect("FIBO tag has a mask")
            .parse()
            .expect("valid FIBO category mask");
        let source = fields.next().expect("FIBO tag has a source");
        assert_eq!(source, "FIBO MIT");
        assert_eq!(mask, 1 << 7, "FIBO source only adds business tags");
        assert!(fields.next().is_none(), "unexpected FIBO tag column");
        words.entry(word).or_default().fibo_business = mask;
    }
    for line in BETTER_QUANT_BUSINESS_TSV.lines() {
        let mut fields = line.split('\t');
        let word = fields.next().expect("Better Quant tag has a word");
        let mask: u16 = fields
            .next()
            .expect("Better Quant tag has a mask")
            .parse()
            .expect("valid Better Quant category mask");
        let source = fields.next().expect("Better Quant tag has a source");
        assert_eq!(source, "Better Quant Wiki MIT");
        assert_eq!(mask, 1 << 7, "Better Quant source only adds business tags");
        assert!(
            fields.next().is_none(),
            "unexpected Better Quant tag column"
        );
        words.entry(word).or_default().better_quant_business = mask;
    }
    for line in CFPB_FINANCE_TSV.lines() {
        let mut fields = line.split('\t');
        let word = fields.next().expect("CFPB tag has a word");
        let mask: u16 = fields
            .next()
            .expect("CFPB tag has a mask")
            .parse()
            .expect("valid CFPB category mask");
        let source = fields.next().expect("CFPB tag has a source");
        assert_eq!(source, "CFPB 2024 public-domain glossary");
        assert_eq!(mask, 1 << 7, "CFPB source only adds business tags");
        assert!(fields.next().is_none(), "unexpected CFPB tag column");
        words.entry(word).or_default().cfpb_finance = mask;
    }
    for line in FINANCE_I18N_TSV.lines() {
        let mut fields = line.split('\t');
        let word = fields.next().expect("finance_i18n tag has a word");
        let mask: u16 = fields
            .next()
            .expect("finance_i18n tag has a mask")
            .parse()
            .expect("valid finance_i18n category mask");
        let source = fields.next().expect("finance_i18n tag has a source");
        assert_eq!(source, "finance_i18n MIT 2018");
        assert_eq!(mask, 1 << 7, "finance_i18n only adds business tags");
        assert!(
            fields.next().is_none(),
            "unexpected finance_i18n tag column"
        );
        words.entry(word).or_default().finance_i18n = mask;
    }
    for line in COMPUTERESE_TSV.lines() {
        let mut fields = line.split('\t');
        let word = fields.next().expect("computerese tag has a word");
        let mask: u16 = fields
            .next()
            .expect("computerese tag has a mask")
            .parse()
            .expect("valid computerese category mask");
        let source = fields.next().expect("computerese tag has a source");
        assert_eq!(source, "EarsEyesMouth Computerese MIT");
        assert_eq!(mask, 1 << 6, "computerese only adds computer tags");
        assert!(fields.next().is_none(), "unexpected computerese tag column");
        words.entry(word).or_default().computerese = mask;
    }
    for line in MESH_MEDICAL_TSV.lines() {
        let mut fields = line.split('\t');
        let word = fields.next().expect("MeSH medical tag has a word");
        let mask: u16 = fields
            .next()
            .expect("MeSH medical tag has a mask")
            .parse()
            .expect("valid MeSH medical category mask");
        let source = fields.next().expect("MeSH medical tag has a source");
        assert_eq!(source, "NLM MeSH 2026");
        assert_eq!(mask, 1 << 8, "MeSH only adds medical tags");
        assert!(
            fields.next().is_none(),
            "unexpected MeSH medical tag column"
        );
        words.entry(word).or_default().mesh_medical = mask;
    }
    for line in WIKIDATA_MEDICAL_TSV
        .lines()
        .chain(WIKIDATA_MEDICAL_2_TSV.lines())
    {
        let mut fields = line.split('\t');
        let word = fields.next().expect("Wikidata medical tag has a word");
        let mask: u16 = fields
            .next()
            .expect("Wikidata medical tag has a mask")
            .parse()
            .expect("valid Wikidata medical category mask");
        let source = fields.next().expect("Wikidata medical tag has a source");
        assert_eq!(source, "Wikidata CC0 + NLM MeSH 2026");
        assert_eq!(mask, 1 << 8, "Wikidata MeSH rows only add medical tags");
        assert!(
            fields.next().is_none(),
            "unexpected Wikidata medical tag column"
        );
        words.entry(word).or_default().wikidata_medical = mask;
    }
    for line in NAER_MEDICAL_TSV.lines().chain(NAER_MEDICAL_2_TSV.lines()) {
        let mut fields = line.split('\t');
        let word = fields.next().expect("NAER medical tag has a word");
        let mask: u16 = fields
            .next()
            .expect("NAER medical tag has a mask")
            .parse()
            .expect("valid NAER medical category mask");
        let source = fields.next().expect("NAER medical tag has a source");
        assert_eq!(source, "NAER Medical Academic Terms OGDL v1.0");
        assert_eq!(mask, 1 << 8, "NAER rows only add medical tags");
        assert!(
            fields.next().is_none(),
            "unexpected NAER medical tag column"
        );
        words.entry(word).or_default().naer_medical = mask;
    }
    for line in NAER_LIFE_SCIENCE_TSV.lines() {
        let mut fields = line.split('\t');
        let word = fields.next().expect("NAER life-science tag has a word");
        let mask: u16 = fields
            .next()
            .expect("NAER life-science tag has a mask")
            .parse()
            .expect("valid NAER life-science category mask");
        let source = fields.next().expect("NAER life-science tag has a source");
        assert_eq!(source, "NAER Life Science Academic Terms OGDL v1.0");
        assert_eq!(mask, 1 << 8, "NAER life-science rows only add medical tags");
        assert!(
            fields.next().is_none(),
            "unexpected NAER life-science tag column"
        );
        words.entry(word).or_default().naer_life_science = mask;
    }
    for line in NAER_VETERINARY_TSV.lines() {
        let mut fields = line.split('\t');
        let word = fields.next().expect("NAER veterinary tag has a word");
        let mask: u16 = fields
            .next()
            .expect("NAER veterinary tag has a mask")
            .parse()
            .expect("valid NAER veterinary category mask");
        let source = fields.next().expect("NAER veterinary tag has a source");
        assert_eq!(source, "NAER Veterinary Medical Terms OGDL v1.0");
        assert_eq!(mask, 1 << 8, "NAER veterinary rows only add medical tags");
        assert!(
            fields.next().is_none(),
            "unexpected NAER veterinary tag column"
        );
        words.entry(word).or_default().naer_veterinary = mask;
    }
    for line in NAER_ECONOMICS_TSV.lines() {
        let mut fields = line.split('\t');
        let word = fields.next().expect("NAER economics tag has a word");
        let mask: u16 = fields
            .next()
            .expect("NAER economics tag has a mask")
            .parse()
            .expect("valid NAER economics category mask");
        let source = fields.next().expect("NAER economics tag has a source");
        assert_eq!(source, "NAER Economics Academic Terms OGDL v1.0");
        assert_eq!(mask, 1 << 7, "NAER economics rows only add business tags");
        assert!(
            fields.next().is_none(),
            "unexpected NAER economics tag column"
        );
        words.entry(word).or_default().naer_economics = mask;
    }
    for line in NAER_ACCOUNTING_TSV.lines() {
        let mut fields = line.split('\t');
        let word = fields.next().expect("NAER accounting tag has a word");
        let mask: u16 = fields
            .next()
            .expect("NAER accounting tag has a mask")
            .parse()
            .expect("valid NAER accounting category mask");
        let source = fields.next().expect("NAER accounting tag has a source");
        assert_eq!(source, "NAER Accounting Academic Terms OGDL v1.0");
        assert_eq!(mask, 1 << 7, "NAER accounting rows only add business tags");
        assert!(
            fields.next().is_none(),
            "unexpected NAER accounting tag column"
        );
        words.entry(word).or_default().naer_accounting = mask;
    }
    for line in NAER_MANAGEMENT_TSV.lines() {
        let mut fields = line.split('\t');
        let word = fields.next().expect("NAER management tag has a word");
        let mask: u16 = fields
            .next()
            .expect("NAER management tag has a mask")
            .parse()
            .expect("valid NAER management category mask");
        let source = fields.next().expect("NAER management tag has a source");
        assert_eq!(source, "NAER Management Academic Terms OGDL v1.0");
        assert_eq!(mask, 1 << 7, "NAER management rows only add business tags");
        assert!(
            fields.next().is_none(),
            "unexpected NAER management tag column"
        );
        words.entry(word).or_default().naer_management = mask;
    }
    for line in NAER_COMPUTER_TSV.lines() {
        let mut fields = line.split('\t');
        let word = fields.next().expect("NAER computer tag has a word");
        let mask: u16 = fields
            .next()
            .expect("NAER computer tag has a mask")
            .parse()
            .expect("valid NAER computer category mask");
        let source = fields.next().expect("NAER computer tag has a source");
        assert_eq!(source, "NAER Computer Science Academic Terms OGDL v1.0");
        assert_eq!(mask, 1 << 6, "NAER computer rows only add computer tags");
        assert!(
            fields.next().is_none(),
            "unexpected NAER computer tag column"
        );
        words.entry(word).or_default().naer_computer = mask;
    }
    for line in NAER_ADMINISTRATION_TSV.lines() {
        let mut fields = line.split('\t');
        let word = fields.next().expect("NAER administration tag has a word");
        let mask: u16 = fields
            .next()
            .expect("NAER administration tag has a mask")
            .parse()
            .expect("valid NAER administration category mask");
        let source = fields.next().expect("NAER administration tag has a source");
        assert_eq!(source, "NAER Administration Academic Terms OGDL v1.0");
        assert_eq!(
            mask,
            1 << 9,
            "NAER administration rows only add administration tags"
        );
        assert!(
            fields.next().is_none(),
            "unexpected NAER administration tag column"
        );
        words.entry(word).or_default().naer_administration = mask;
    }
    for line in WORDLEVEL_TOEFL_IELTS_TSV.lines() {
        let mut fields = line.split('\t');
        let word = fields.next().expect("WordLevel tag has a word");
        let mask: u16 = fields
            .next()
            .expect("WordLevel tag has a mask")
            .parse()
            .expect("valid WordLevel exam-category mask");
        let source = fields.next().expect("WordLevel tag has a source");
        assert_eq!(source, "WordLevel TOEFL/IELTS Academic List");
        assert_eq!(
            mask,
            (1 << 4) | (1 << 5),
            "WordLevel only adds TOEFL and IELTS tags"
        );
        assert!(fields.next().is_none(), "unexpected WordLevel tag column");
        words.entry(word).or_default().wordlevel = mask;
    }
    words
});

#[derive(Clone, Copy, Default)]
pub struct Membership {
    pub ecdict: u16,
    pub kylebing: u16,
    pub openetymology: u16,
    pub professional: u16,
    pub cjk_compsci: u16,
    pub fibo_business: u16,
    pub better_quant_business: u16,
    pub cfpb_finance: u16,
    pub finance_i18n: u16,
    pub computerese: u16,
    pub mesh_medical: u16,
    pub wikidata_medical: u16,
    pub naer_medical: u16,
    pub naer_life_science: u16,
    pub naer_veterinary: u16,
    pub naer_economics: u16,
    pub naer_accounting: u16,
    pub naer_management: u16,
    pub naer_computer: u16,
    pub naer_administration: u16,
    pub wordlevel: u16,
}
impl Membership {
    pub fn mask(self) -> u16 {
        self.ecdict
            | self.kylebing
            | self.openetymology
            | self.professional
            | self.cjk_compsci
            | self.fibo_business
            | self.better_quant_business
            | self.cfpb_finance
            | self.finance_i18n
            | self.computerese
            | self.mesh_medical
            | self.wikidata_medical
            | self.naer_medical
            | self.naer_life_science
            | self.naer_veterinary
            | self.naer_economics
            | self.naer_accounting
            | self.naer_management
            | self.naer_computer
            | self.naer_administration
            | self.wordlevel
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
            if entry.openetymology & (1 << i) != 0 {
                sources.push("OpenEtymology");
            }
            if entry.professional & (1 << i) != 0 {
                sources.push("Wiktionary CC BY-SA 4.0");
            }
            if entry.cjk_compsci & (1 << i) != 0 {
                sources.push("CJK computer science terms CC BY-SA 4.0");
            }
            if entry.fibo_business & (1 << i) != 0 {
                sources.push("FIBO MIT");
            }
            if entry.better_quant_business & (1 << i) != 0 {
                sources.push("Better Quant Wiki MIT");
            }
            if entry.cfpb_finance & (1 << i) != 0 {
                sources.push("CFPB 2024 public-domain glossary");
            }
            if entry.finance_i18n & (1 << i) != 0 {
                sources.push("finance_i18n MIT 2018");
            }
            if entry.computerese & (1 << i) != 0 {
                sources.push("EarsEyesMouth Computerese MIT");
            }
            if entry.mesh_medical & (1 << i) != 0 {
                sources.push("NLM MeSH 2026");
            }
            if entry.wikidata_medical & (1 << i) != 0 {
                sources.push("Wikidata CC0 + NLM MeSH 2026");
            }
            if entry.naer_medical & (1 << i) != 0 {
                sources.push("NAER Medical Academic Terms OGDL v1.0");
            }
            if entry.naer_life_science & (1 << i) != 0 {
                sources.push("NAER Life Science Academic Terms OGDL v1.0");
            }
            if entry.naer_veterinary & (1 << i) != 0 {
                sources.push("NAER Veterinary Medical Terms OGDL v1.0");
            }
            if entry.naer_economics & (1 << i) != 0 {
                sources.push("NAER Economics Academic Terms OGDL v1.0");
            }
            if entry.naer_accounting & (1 << i) != 0 {
                sources.push("NAER Accounting Academic Terms OGDL v1.0");
            }
            if entry.naer_management & (1 << i) != 0 {
                sources.push("NAER Management Academic Terms OGDL v1.0");
            }
            if entry.naer_computer & (1 << i) != 0 {
                sources.push("NAER Computer Science Academic Terms OGDL v1.0");
            }
            if entry.naer_administration & (1 << i) != 0 {
                sources.push("NAER Administration Academic Terms OGDL v1.0");
            }
            if entry.wordlevel & (1 << i) != 0 {
                sources.push("WordLevel TOEFL/IELTS Academic List");
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
    use qingjian_core::{CandidateKind, PartOfSpeech, Sense, Translation};
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
    fn merges_separately_licensed_openetymology_wordlist_tags() {
        let entries = tags("add-on", 1 << 3);
        assert_eq!(entries.len(), 1);
        assert_eq!(entries[0].id, "tem8");
        assert!(entries[0].selected);
        assert_eq!(entries[0].sources, ["OpenEtymology"]);
        assert_eq!(lookup("ABANDON").openetymology & (1 << 4), 1 << 4);

        let cet4 = tags("abandon", 1 << 0);
        let tag = cet4.iter().find(|tag| tag.id == "cet4").unwrap();
        assert!(tag.selected);
        assert!(tag.sources.contains(&"OpenEtymology"));
        assert_eq!(lookup("abandon").openetymology & 1, 1);
    }

    #[test]
    fn professional_categories_are_independent_selectable_tags() {
        let selected = selection(&["cet6".into(), "computer".into(), "medical".into()]).unwrap();
        assert_eq!(selected, (1 << 1) | (1 << 6) | (1 << 8));
        assert_eq!(selected_ids(selected), ["cet6", "computer", "medical"]);

        let cerebrum_tags = tags("cerebrum", selected);
        assert_eq!(cerebrum_tags.len(), 1);
        assert_eq!(cerebrum_tags[0].id, "medical");
        assert_eq!(cerebrum_tags[0].label, "医学");
        assert!(cerebrum_tags[0].selected);
        assert!(
            cerebrum_tags[0]
                .sources
                .contains(&"Wiktionary CC BY-SA 4.0")
        );

        let mixed = tags("adapt", selected);
        assert!(mixed.iter().any(|tag| tag.id == "computer" && tag.selected));
    }

    #[test]
    fn fibo_adds_business_tags_without_changing_dictionary_candidates() {
        let selected = selection(&["business".into()]).unwrap();
        let loan = tags("loan", selected);
        let business = loan.iter().find(|tag| tag.id == "business").unwrap();
        assert!(business.selected);
        assert!(business.sources.contains(&"FIBO MIT"));

        let mut candidate = candidate(&["lend", "loan"], Language::English);
        prioritize(&mut candidate, selected);
        let translation = candidate.translation.unwrap();
        let senses = translation.senses();
        assert_eq!(senses[0].text, "loan");
        assert_eq!(senses.len(), 2);
    }

    #[test]
    fn better_quant_adds_finance_mappings_and_business_tags_without_reordering_chinese() {
        let selected = selection(&["business".into()]).unwrap();
        for (chinese, english) in [
            ("市值", "capitalization"),
            ("复利", "compounding"),
            ("回撤", "drawdown"),
            ("权益", "equity"),
            ("杠杆", "leverage"),
            ("报价", "quotation"),
            ("证券", "security"),
        ] {
            assert!(
                expansion::senses(chinese).any(|sense| sense.text == english),
                "missing Better Quant mapping {chinese} -> {english}"
            );
            assert_eq!(
                expansion::source(chinese, english),
                Some("Better Quant Wiki MIT")
            );
            assert!(tags(english, selected).iter().any(|tag| {
                tag.id == "business"
                    && tag.selected
                    && tag.sources.contains(&"Better Quant Wiki MIT")
            }));
        }
        assert!(tags("security", selected)[0].sources.contains(&"FIBO MIT"));

        let mut candidate = candidate(
            &["capitalization", "market capitalization"],
            Language::English,
        );
        let original_chinese = candidate.text.clone();
        prioritize(&mut candidate, selected);
        assert_eq!(candidate.text, original_chinese);
        assert_eq!(
            candidate.translation.unwrap().senses()[0].text,
            "capitalization"
        );
    }

    #[test]
    fn cfpb_adds_reviewed_finance_mappings_and_tags_without_reordering_chinese() {
        let selected = selection(&["business".into()]).unwrap();
        let mappings: Vec<_> = include_str!("../data/cfpb-finance-expansion.tsv")
            .lines()
            .collect();
        assert_eq!(mappings.len(), 67);
        for row in mappings {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let pos: PartOfSpeech = fields.next().unwrap().parse().unwrap();
            assert_eq!(
                fields.next(),
                Some("CFPB Chinese-English financial glossary 2024")
            );
            let sense = expansion::senses(chinese)
                .find(|sense| sense.text == english)
                .unwrap_or_else(|| panic!("missing CFPB mapping {chinese} -> {english}"));
            assert_eq!(sense.part_of_speech, Some(pos));
            assert_eq!(
                expansion::source(chinese, english),
                Some("CFPB Chinese-English financial glossary 2024")
            );
        }
        let tagged: Vec<_> = include_str!("../data/cfpb-finance-tags.tsv")
            .lines()
            .collect();
        assert_eq!(tagged.len(), 211);
        for row in tagged {
            let mut fields = row.split('\t');
            let english = fields.next().unwrap();
            assert_eq!(fields.next(), Some("128"));
            assert_eq!(fields.next(), Some("CFPB 2024 public-domain glossary"));
            assert!(tags(english, selected).iter().any(|tag| {
                tag.id == "business"
                    && tag.selected
                    && tag.sources.contains(&"CFPB 2024 public-domain glossary")
            }));
        }
        for (chinese, english, pos) in [
            ("减轻", "abatement", PartOfSpeech::Noun),
            ("废除", "abrogate", PartOfSpeech::Verb),
            ("经纪人", "broker", PartOfSpeech::Noun),
            ("动产", "chattel", PartOfSpeech::Noun),
            ("违约", "default", PartOfSpeech::Noun),
            ("透支", "overdraft", PartOfSpeech::Noun),
            ("汇款", "remittance", PartOfSpeech::Noun),
            ("结算", "settlement", PartOfSpeech::Noun),
            ("传票", "summons", PartOfSpeech::Noun),
            ("担保", "warranty", PartOfSpeech::Noun),
        ] {
            let sense = expansion::senses(chinese)
                .find(|sense| sense.text == english)
                .unwrap_or_else(|| panic!("missing CFPB mapping {chinese} -> {english}"));
            assert_eq!(sense.part_of_speech, Some(pos));
            assert_eq!(
                expansion::source(chinese, english),
                Some("CFPB Chinese-English financial glossary 2024")
            );
            assert!(tags(english, selected).iter().any(|tag| {
                tag.id == "business"
                    && tag.selected
                    && tag.sources.contains(&"CFPB 2024 public-domain glossary")
            }));
        }
        let mut candidate = candidate(&["unlabelled test", "settlement"], Language::English);
        let original_chinese = candidate.text.clone();
        prioritize(&mut candidate, selected);
        assert_eq!(candidate.text, original_chinese);
        assert_eq!(
            candidate.translation.unwrap().senses()[0].text,
            "settlement"
        );
    }

    #[test]
    fn finance_i18n_adds_reviewed_mappings_and_business_tags_without_reordering_chinese() {
        let selected = selection(&["business".into()]).unwrap();
        let mappings: Vec<_> = include_str!("../data/finance-i18n-expansion.tsv")
            .lines()
            .collect();
        assert_eq!(mappings.len(), 47);
        for row in mappings {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let pos: PartOfSpeech = fields.next().unwrap().parse().unwrap();
            assert_eq!(fields.next(), Some("finance_i18n MIT 2018"));
            let sense = expansion::senses(chinese)
                .find(|sense| sense.text == english)
                .unwrap_or_else(|| panic!("missing finance_i18n mapping {chinese} -> {english}"));
            assert_eq!(sense.part_of_speech, Some(pos));
            assert_eq!(
                expansion::source(chinese, english),
                Some("finance_i18n MIT 2018")
            );
            assert!(tags(english, selected).iter().any(|tag| {
                tag.id == "business"
                    && tag.selected
                    && tag.sources.contains(&"finance_i18n MIT 2018")
            }));
        }

        let tagged: Vec<_> = include_str!("../data/finance-i18n-tags.tsv")
            .lines()
            .collect();
        assert_eq!(tagged.len(), 47);
        let mut candidate = candidate(&["unlabelled test", "devaluation"], Language::English);
        let original_chinese = candidate.text.clone();
        prioritize(&mut candidate, selected);
        assert_eq!(candidate.text, original_chinese);
        assert_eq!(
            candidate.translation.unwrap().senses()[0].text,
            "devaluation"
        );
    }

    #[test]
    fn naer_economics_adds_reviewed_mappings_and_business_tags() {
        let selected = selection(&["business".into()]).unwrap();
        let mappings: Vec<_> = include_str!("../data/naer-economics-expansion.tsv")
            .lines()
            .collect();
        assert_eq!(mappings.len(), 28);
        for row in mappings {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let pos: PartOfSpeech = fields.next().unwrap().parse().unwrap();
            assert_eq!(
                fields.next(),
                Some("NAER Economics Academic Terms OGDL v1.0")
            );
            let sense = expansion::senses(chinese)
                .find(|sense| sense.text == english)
                .unwrap_or_else(|| panic!("missing NAER economics mapping {chinese} -> {english}"));
            assert_eq!(sense.part_of_speech, Some(pos));
            assert_eq!(
                expansion::source(chinese, english),
                Some("NAER Economics Academic Terms OGDL v1.0")
            );
            assert!(tags(english, selected).iter().any(|tag| {
                tag.id == "business"
                    && tag.selected
                    && tag
                        .sources
                        .contains(&"NAER Economics Academic Terms OGDL v1.0")
            }));
        }

        let tagged: Vec<_> = include_str!("../data/naer-economics-tags.tsv")
            .lines()
            .collect();
        assert_eq!(tagged.len(), 28);
        for row in tagged {
            let mut fields = row.split('\t');
            let english = fields.next().unwrap();
            assert_eq!(fields.next(), Some("128"));
            assert_eq!(
                fields.next(),
                Some("NAER Economics Academic Terms OGDL v1.0")
            );
            assert!(tags(english, selected).iter().any(|tag| {
                tag.id == "business"
                    && tag.selected
                    && tag
                        .sources
                        .contains(&"NAER Economics Academic Terms OGDL v1.0")
            }));
        }

        let mut candidate = candidate(&["unlabelled test", "merger"], Language::English);
        let original_chinese = candidate.text.clone();
        prioritize(&mut candidate, selected);
        assert_eq!(candidate.text, original_chinese);
        assert_eq!(candidate.translation.unwrap().senses()[0].text, "merger");
    }

    #[test]
    fn naer_accounting_adds_reviewed_mappings_and_business_tags_without_reordering_chinese() {
        let selected = selection(&["business".into()]).unwrap();
        let mappings: Vec<_> = include_str!("../data/naer-accounting-expansion.tsv")
            .lines()
            .collect();
        assert_eq!(mappings.len(), 22);
        for row in mappings {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let pos: PartOfSpeech = fields.next().unwrap().parse().unwrap();
            assert_eq!(
                fields.next(),
                Some("NAER Accounting Academic Terms OGDL v1.0")
            );
            let sense = expansion::senses(chinese)
                .find(|sense| sense.text == english)
                .unwrap_or_else(|| {
                    panic!("missing NAER accounting mapping {chinese} -> {english}")
                });
            assert_eq!(sense.part_of_speech, Some(pos));
            assert_eq!(
                expansion::source(chinese, english),
                Some("NAER Accounting Academic Terms OGDL v1.0")
            );
            assert!(tags(english, selected).iter().any(|tag| {
                tag.id == "business"
                    && tag.selected
                    && tag
                        .sources
                        .contains(&"NAER Accounting Academic Terms OGDL v1.0")
            }));
        }

        let tagged: Vec<_> = include_str!("../data/naer-accounting-tags.tsv")
            .lines()
            .collect();
        assert_eq!(tagged.len(), 133);
        for row in tagged {
            let mut fields = row.split('\t');
            let english = fields.next().unwrap();
            assert_eq!(fields.next(), Some("128"));
            assert_eq!(
                fields.next(),
                Some("NAER Accounting Academic Terms OGDL v1.0")
            );
            assert!(tags(english, selected).iter().any(|tag| {
                tag.id == "business"
                    && tag.selected
                    && tag
                        .sources
                        .contains(&"NAER Accounting Academic Terms OGDL v1.0")
            }));
        }

        let mut candidate = candidate(&["unlabelled test", "business"], Language::English);
        let original_chinese = candidate.text.clone();
        prioritize(&mut candidate, selected);
        assert_eq!(candidate.text, original_chinese);
        assert_eq!(candidate.translation.unwrap().senses()[0].text, "business");
    }

    #[test]
    fn naer_management_adds_reviewed_mappings_and_business_tags_without_reordering_chinese() {
        let selected = selection(&["business".into()]).unwrap();
        let mappings: Vec<_> = include_str!("../data/naer-management-expansion.tsv")
            .lines()
            .collect();
        assert_eq!(mappings.len(), 41);
        for row in mappings {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let pos: PartOfSpeech = fields.next().unwrap().parse().unwrap();
            assert_eq!(
                fields.next(),
                Some("NAER Management Academic Terms OGDL v1.0")
            );
            let sense = expansion::senses(chinese)
                .find(|sense| sense.text == english)
                .unwrap_or_else(|| {
                    panic!("missing NAER management mapping {chinese} -> {english}")
                });
            assert_eq!(sense.part_of_speech, Some(pos));
            assert_eq!(
                expansion::source(chinese, english),
                Some("NAER Management Academic Terms OGDL v1.0")
            );
            assert!(tags(english, selected).iter().any(|tag| {
                tag.id == "business"
                    && tag.selected
                    && tag
                        .sources
                        .contains(&"NAER Management Academic Terms OGDL v1.0")
            }));
        }

        let tagged: Vec<_> = include_str!("../data/naer-management-tags.tsv")
            .lines()
            .collect();
        assert_eq!(tagged.len(), 274);
        for row in tagged {
            let mut fields = row.split('\t');
            let english = fields.next().unwrap();
            assert_eq!(fields.next(), Some("128"));
            assert_eq!(
                fields.next(),
                Some("NAER Management Academic Terms OGDL v1.0")
            );
            assert!(tags(english, selected).iter().any(|tag| {
                tag.id == "business"
                    && tag.selected
                    && tag
                        .sources
                        .contains(&"NAER Management Academic Terms OGDL v1.0")
            }));
        }

        let mut candidate = candidate(&["unlabelled test", "management"], Language::English);
        let original_chinese = candidate.text.clone();
        prioritize(&mut candidate, selected);
        assert_eq!(candidate.text, original_chinese);
        assert_eq!(candidate.translation.unwrap().senses()[0].text, "management");
    }

    #[test]
    fn naer_administration_adds_reviewed_mappings_and_selectable_tags_without_reordering_chinese() {
        let selected = selection(&["administration".into()]).unwrap();
        assert_eq!(selected, 1 << 9);
        assert!(selected_ids(selected).contains(&"administration"));

        let mappings: Vec<_> = include_str!("../data/naer-administration-expansion.tsv")
            .lines()
            .collect();
        assert_eq!(mappings.len(), 17);
        for row in mappings {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let pos: PartOfSpeech = fields.next().unwrap().parse().unwrap();
            assert_eq!(
                fields.next(),
                Some("NAER Administration Academic Terms OGDL v1.0")
            );
            let sense = expansion::senses(chinese)
                .find(|sense| sense.text == english)
                .unwrap_or_else(|| {
                    panic!("missing NAER administration mapping {chinese} -> {english}")
                });
            assert_eq!(sense.part_of_speech, Some(pos));
            assert_eq!(
                expansion::source(chinese, english),
                Some("NAER Administration Academic Terms OGDL v1.0")
            );
            assert!(tags(english, selected).iter().any(|tag| {
                tag.id == "administration"
                    && tag.selected
                    && tag
                        .sources
                        .contains(&"NAER Administration Academic Terms OGDL v1.0")
            }));
        }

        let tagged: Vec<_> = include_str!("../data/naer-administration-tags.tsv")
            .lines()
            .collect();
        assert_eq!(tagged.len(), 76);
        for row in tagged {
            let mut fields = row.split('\t');
            let english = fields.next().unwrap();
            assert_eq!(fields.next(), Some("512"));
            assert_eq!(
                fields.next(),
                Some("NAER Administration Academic Terms OGDL v1.0")
            );
            assert!(tags(english, selected).iter().any(|tag| {
                tag.id == "administration"
                    && tag.selected
                    && tag
                        .sources
                        .contains(&"NAER Administration Academic Terms OGDL v1.0")
            }));
        }

        let mut candidate = candidate(&["unlabelled test", "officer"], Language::English);
        let original_chinese = candidate.text.clone();
        prioritize(&mut candidate, selected);
        assert_eq!(candidate.text, original_chinese);
        assert_eq!(candidate.translation.unwrap().senses()[0].text, "officer");
    }

    #[test]
    fn naer_computer_terms_add_reviewed_mappings_and_tags_without_reordering_chinese() {
        let selected = selection(&["computer".into()]).unwrap();
        let mappings: Vec<_> = include_str!("../data/naer-computer-expansion.tsv")
            .lines()
            .collect();
        assert_eq!(mappings.len(), 40);
        for row in mappings {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let pos: PartOfSpeech = fields.next().unwrap().parse().unwrap();
            assert_eq!(
                fields.next(),
                Some("NAER Computer Science Academic Terms OGDL v1.0")
            );
            let sense = expansion::senses(chinese)
                .find(|sense| sense.text == english)
                .unwrap_or_else(|| panic!("missing NAER computer mapping {chinese} -> {english}"));
            assert_eq!(sense.part_of_speech, Some(pos));
            assert_eq!(
                expansion::source(chinese, english),
                Some("NAER Computer Science Academic Terms OGDL v1.0")
            );
            assert!(tags(english, selected).iter().any(|tag| {
                tag.id == "computer"
                    && tag.selected
                    && tag
                        .sources
                        .contains(&"NAER Computer Science Academic Terms OGDL v1.0")
            }));
        }

        let tagged: Vec<_> = include_str!("../data/naer-computer-tags.tsv")
            .lines()
            .collect();
        assert_eq!(tagged.len(), 62);
        for row in tagged {
            let mut fields = row.split('\t');
            let english = fields.next().unwrap();
            assert_eq!(fields.next(), Some("64"));
            assert_eq!(
                fields.next(),
                Some("NAER Computer Science Academic Terms OGDL v1.0")
            );
            assert!(tags(english, selected).iter().any(|tag| {
                tag.id == "computer"
                    && tag.selected
                    && tag
                        .sources
                        .contains(&"NAER Computer Science Academic Terms OGDL v1.0")
            }));
        }

        let mut candidate = candidate(&["unlabelled test", "radix"], Language::English);
        let original_chinese = candidate.text.clone();
        prioritize(&mut candidate, selected);
        assert_eq!(candidate.text, original_chinese);
        assert_eq!(candidate.translation.unwrap().senses()[0].text, "radix");
    }

    #[test]
    fn computerese_adds_reviewed_mappings_and_computer_tags_without_reordering_chinese() {
        let selected = selection(&["computer".into()]).unwrap();
        let mappings: Vec<_> = include_str!("../data/computerese-expansion.tsv")
            .lines()
            .collect();
        assert_eq!(mappings.len(), 13);
        for row in mappings {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let pos: PartOfSpeech = fields.next().unwrap().parse().unwrap();
            assert_eq!(fields.next(), Some("EarsEyesMouth Computerese MIT"));
            let sense = expansion::senses(chinese)
                .find(|sense| sense.text == english)
                .unwrap_or_else(|| panic!("missing computerese mapping {chinese} -> {english}"));
            assert_eq!(sense.part_of_speech, Some(pos));
            assert_eq!(
                expansion::source(chinese, english),
                Some("EarsEyesMouth Computerese MIT")
            );
            assert!(tags(english, selected).iter().any(|tag| {
                tag.id == "computer"
                    && tag.selected
                    && tag.sources.contains(&"EarsEyesMouth Computerese MIT")
            }));
        }

        let tagged: Vec<_> = include_str!("../data/computerese-tags.tsv")
            .lines()
            .collect();
        assert_eq!(tagged.len(), 68);
        for row in tagged {
            let mut fields = row.split('\t');
            let english = fields.next().unwrap();
            assert_eq!(fields.next(), Some("64"));
            assert_eq!(fields.next(), Some("EarsEyesMouth Computerese MIT"));
            assert!(tags(english, selected).iter().any(|tag| {
                tag.id == "computer"
                    && tag.selected
                    && tag.sources.contains(&"EarsEyesMouth Computerese MIT")
            }));
        }

        let mut candidate = candidate(&["unlabelled test", "mainframe"], Language::English);
        let original_chinese = candidate.text.clone();
        prioritize(&mut candidate, selected);
        assert_eq!(candidate.text, original_chinese);
        assert_eq!(candidate.translation.unwrap().senses()[0].text, "mainframe");
    }

    #[test]
    fn cjk_computer_science_terms_add_reachable_mappings_and_source_tags() {
        let selected = selection(&["computer".into()]).unwrap();
        let graph_tags = tags("graph", selected);
        assert!(graph_tags.iter().any(|tag| {
            tag.id == "computer"
                && tag.selected
                && tag
                    .sources
                    .contains(&"CJK computer science terms CC BY-SA 4.0")
        }));
        assert!(expansion::senses("事务").any(|sense| sense.text == "transaction"));
        assert!(expansion::senses("字体").any(|sense| sense.text == "typeface"));
        assert!(expansion::senses("变量").all(|sense| sense.text != "value"));
        assert!(expansion::senses("常量").all(|sense| sense.text != "value"));
    }

    #[test]
    fn mesh_adds_reviewed_medical_mappings_and_tags_without_reordering_chinese() {
        let selected = selection(&["medical".into()]).unwrap();
        let mappings: Vec<_> = include_str!("../data/mesh-medical-expansion.tsv")
            .lines()
            .collect();
        assert_eq!(mappings.len(), 75);
        for row in mappings {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let pos: PartOfSpeech = fields.next().unwrap().parse().unwrap();
            assert_eq!(fields.next(), Some("NLM MeSH 2026 + ECDICT MIT"));
            let sense = expansion::senses(chinese)
                .find(|sense| sense.text == english)
                .unwrap_or_else(|| panic!("missing MeSH mapping {chinese} -> {english}"));
            assert_eq!(sense.part_of_speech, Some(pos));
            assert_eq!(
                expansion::source(chinese, english),
                Some("NLM MeSH 2026 + ECDICT MIT")
            );
            assert!(tags(english, selected).iter().any(|tag| {
                tag.id == "medical" && tag.selected && tag.sources.contains(&"NLM MeSH 2026")
            }));
        }

        let mut candidate = candidate(&["unlabelled test", "anesthetics"], Language::English);
        let original_chinese = candidate.text.clone();
        prioritize(&mut candidate, selected);
        assert_eq!(candidate.text, original_chinese);
        assert_eq!(
            candidate.translation.unwrap().senses()[0].text,
            "anesthetics"
        );

        let tagged: Vec<_> = include_str!("../data/mesh-medical-tags.tsv")
            .lines()
            .collect();
        assert_eq!(tagged.len(), 1079);
        for row in tagged {
            let mut fields = row.split('\t');
            let english = fields.next().unwrap();
            assert_eq!(fields.next(), Some("256"));
            assert_eq!(fields.next(), Some("NLM MeSH 2026"));
            assert!(tags(english, selected).iter().any(|tag| {
                tag.id == "medical" && tag.selected && tag.sources.contains(&"NLM MeSH 2026")
            }));
        }
    }

    #[test]
    fn wikidata_mesh_batch_adds_cc0_medical_mappings_and_tags() {
        let selected = selection(&["medical".into()]).unwrap();
        let mappings: Vec<_> = include_str!("../data/wikidata-medical-expansion.tsv")
            .lines()
            .collect();
        assert_eq!(mappings.len(), 25);
        for row in mappings {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let pos: PartOfSpeech = fields.next().unwrap().parse().unwrap();
            assert_eq!(fields.next(), Some("Wikidata CC0 + NLM MeSH 2026"));
            let sense = expansion::senses(chinese)
                .find(|sense| sense.text == english)
                .unwrap_or_else(|| panic!("missing Wikidata mapping {chinese} -> {english}"));
            assert_eq!(sense.part_of_speech, Some(pos));
            assert_eq!(
                expansion::source(chinese, english),
                Some("Wikidata CC0 + NLM MeSH 2026")
            );
            assert!(
                tags(english, selected)
                    .iter()
                    .any(|tag| tag.id == "medical" && tag.selected)
            );
        }

        let tagged: Vec<_> = include_str!("../data/wikidata-medical-tags.tsv")
            .lines()
            .collect();
        assert_eq!(tagged.len(), 24);
        for row in tagged {
            let mut fields = row.split('\t');
            let english = fields.next().unwrap();
            assert_eq!(fields.next(), Some("256"));
            assert_eq!(fields.next(), Some("Wikidata CC0 + NLM MeSH 2026"));
            assert!(tags(english, selected).iter().any(|tag| {
                tag.id == "medical"
                    && tag.selected
                    && tag.sources.contains(&"Wikidata CC0 + NLM MeSH 2026")
            }));
        }

        let mut candidate = candidate(&["unlabelled test", "infections"], Language::English);
        let original_chinese = candidate.text.clone();
        prioritize(&mut candidate, selected);
        assert_eq!(candidate.text, original_chinese);
        assert_eq!(
            candidate.translation.unwrap().senses()[0].text,
            "infections"
        );
    }

    #[test]
    fn wikidata_mesh_batch_23_adds_reviewed_mappings_and_new_medical_tags() {
        let selected = selection(&["medical".into()]).unwrap();
        let mappings: Vec<_> = include_str!("../data/wikidata-medical-expansion-2.tsv")
            .lines()
            .collect();
        assert_eq!(mappings.len(), 19);
        for row in mappings {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let pos: PartOfSpeech = fields.next().unwrap().parse().unwrap();
            let source_label = fields.next().unwrap();
            assert_eq!(source_label, "Wikidata CC0 + NLM MeSH 2026");
            let sense = expansion::senses(chinese)
                .find(|sense| sense.text == english)
                .unwrap_or_else(|| panic!("missing batch 23 mapping {chinese} -> {english}"));
            assert_eq!(sense.part_of_speech, Some(pos));
            assert_eq!(expansion::source(chinese, english), Some(source_label));
            assert!(
                tags(english, selected)
                    .iter()
                    .any(|tag| tag.id == "medical" && tag.selected)
            );
        }

        let tagged: Vec<_> = include_str!("../data/wikidata-medical-tags-2.tsv")
            .lines()
            .collect();
        assert_eq!(tagged.len(), 18);
        for row in tagged {
            let mut fields = row.split('\t');
            let english = fields.next().unwrap();
            assert_eq!(fields.next(), Some("256"));
            assert_eq!(fields.next(), Some("Wikidata CC0 + NLM MeSH 2026"));
            assert!(tags(english, selected).iter().any(|tag| {
                tag.id == "medical"
                    && tag.selected
                    && tag.sources.contains(&"Wikidata CC0 + NLM MeSH 2026")
            }));
        }

        let mut candidate = candidate(&["unlabelled test", "prescriptions"], Language::English);
        let original_chinese = candidate.text.clone();
        prioritize(&mut candidate, selected);
        assert_eq!(candidate.text, original_chinese);
        assert_eq!(
            candidate.translation.unwrap().senses()[0].text,
            "prescriptions"
        );
    }

    #[test]
    fn naer_batch_24_adds_reviewed_medical_mappings_and_tags() {
        let selected = selection(&["medical".into()]).unwrap();
        let mappings: Vec<_> = include_str!("../data/naer-medical-expansion.tsv")
            .lines()
            .collect();
        assert_eq!(mappings.len(), 57);
        for row in mappings {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let pos: PartOfSpeech = fields.next().unwrap().parse().unwrap();
            let source_label = fields.next().unwrap();
            assert_eq!(source_label, "NAER Medical Academic Terms OGDL v1.0");
            let sense = expansion::senses(chinese)
                .find(|sense| sense.text == english)
                .unwrap_or_else(|| panic!("missing batch 24 mapping {chinese} -> {english}"));
            assert_eq!(sense.part_of_speech, Some(pos));
            assert_eq!(expansion::source(chinese, english), Some(source_label));
            assert!(tags(english, selected).iter().any(|tag| {
                tag.id == "medical"
                    && tag.selected
                    && tag
                        .sources
                        .contains(&"NAER Medical Academic Terms OGDL v1.0")
            }));
        }

        let mut candidate = candidate(&["unlabelled test", "neoplasm"], Language::English);
        let original_chinese = candidate.text.clone();
        prioritize(&mut candidate, selected);
        assert_eq!(candidate.text, original_chinese);
        assert_eq!(candidate.translation.unwrap().senses()[0].text, "neoplasm");
    }

    #[test]
    fn naer_batch_25_adds_exact_medical_glosses_for_existing_headwords() {
        let selected = selection(&["medical".into()]).unwrap();
        let mappings: Vec<_> = include_str!("../data/naer-medical-expansion-2.tsv")
            .lines()
            .collect();
        assert_eq!(mappings.len(), 37);
        for row in mappings {
            let mut fields = row.split('\t');
            let chinese = fields.next().unwrap();
            let english = fields.next().unwrap();
            let pos: PartOfSpeech = fields.next().unwrap().parse().unwrap();
            let source_label = fields.next().unwrap();
            assert_eq!(source_label, "NAER Medical Academic Terms OGDL v1.0");
            let sense = expansion::senses(chinese)
                .find(|sense| sense.text == english)
                .unwrap_or_else(|| panic!("missing batch 25 mapping {chinese} -> {english}"));
            assert_eq!(sense.part_of_speech, Some(pos));
            assert_eq!(expansion::source(chinese, english), Some(source_label));
            assert!(
                tags(english, selected)
                    .iter()
                    .any(|tag| tag.id == "medical" && tag.selected)
            );
        }

        let tagged: Vec<_> = include_str!("../data/naer-medical-tags-2.tsv")
            .lines()
            .collect();
        assert_eq!(tagged.len(), 18);
        for row in tagged {
            let mut fields = row.split('\t');
            let english = fields.next().unwrap();
            assert_eq!(fields.next(), Some("256"));
            assert_eq!(fields.next(), Some("NAER Medical Academic Terms OGDL v1.0"));
            assert!(tags(english, selected).iter().any(|tag| {
                tag.id == "medical"
                    && tag.selected
                    && tag
                        .sources
                        .contains(&"NAER Medical Academic Terms OGDL v1.0")
            }));
        }

        let mut candidate = candidate(&["unlabelled test", "relapse"], Language::English);
        let original_chinese = candidate.text.clone();
        prioritize(&mut candidate, selected);
        assert_eq!(candidate.text, original_chinese);
        assert_eq!(candidate.translation.unwrap().senses()[0].text, "relapse");
    }

    #[test]
    fn naer_batches_26_and_27_add_reviewed_mappings_and_traceable_medical_tags() {
        let selected = selection(&["medical".into()]).unwrap();
        for (file, count, expected_source) in [
            (
                include_str!("../data/naer-life-science-expansion.tsv"),
                7,
                "NAER Life Science Academic Terms OGDL v1.0",
            ),
            (
                include_str!("../data/naer-veterinary-expansion.tsv"),
                6,
                "NAER Veterinary Medical Terms OGDL v1.0",
            ),
        ] {
            let rows: Vec<_> = file.lines().collect();
            assert_eq!(rows.len(), count);
            for row in rows {
                let mut fields = row.split('\t');
                let chinese = fields.next().unwrap();
                let english = fields.next().unwrap();
                let pos: PartOfSpeech = fields.next().unwrap().parse().unwrap();
                let source_label = fields.next().unwrap();
                assert_eq!(source_label, expected_source);
                let sense = expansion::senses(chinese)
                    .find(|sense| sense.text == english)
                    .unwrap_or_else(|| panic!("missing NAER mapping {chinese} -> {english}"));
                assert_eq!(sense.part_of_speech, Some(pos));
                assert_eq!(expansion::source(chinese, english), Some(expected_source));
                assert!(
                    tags(english, selected)
                        .iter()
                        .any(|tag| tag.id == "medical" && tag.selected)
                );
            }
        }

        for (file, expected_source) in [
            (
                include_str!("../data/naer-life-science-tags.tsv"),
                "NAER Life Science Academic Terms OGDL v1.0",
            ),
            (
                include_str!("../data/naer-veterinary-tags.tsv"),
                "NAER Veterinary Medical Terms OGDL v1.0",
            ),
        ] {
            let rows: Vec<_> = file.lines().collect();
            assert_eq!(rows.len(), 2);
            for row in rows {
                let mut fields = row.split('\t');
                let english = fields.next().unwrap();
                assert_eq!(fields.next(), Some("256"));
                assert_eq!(fields.next(), Some(expected_source));
                assert!(tags(english, selected).iter().any(|tag| {
                    tag.id == "medical" && tag.selected && tag.sources.contains(&expected_source)
                }));
            }
        }
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
    fn wordlevel_batch_adds_traceable_toefl_ielts_membership_and_reviewed_mappings() {
        let selected = selection(&["toefl".into(), "ielts".into()]).unwrap();
        let apathy_tags = tags("apathy", selected);
        for id in ["toefl", "ielts"] {
            let tag = apathy_tags.iter().find(|tag| tag.id == id).unwrap();
            assert!(tag.selected);
            assert!(tag.sources.contains(&"WordLevel TOEFL/IELTS Academic List"));
        }

        let expected = [
            ("畸变", "aberration", PartOfSpeech::Noun),
            ("课程", "curricula", PartOfSpeech::Noun),
            ("掩盖", "enshroud", PartOfSpeech::Verb),
            ("隐蔽", "enshroud", PartOfSpeech::Verb),
        ];
        for (chinese, english, pos) in expected {
            let sense = expansion::senses(chinese)
                .find(|sense| sense.text == english)
                .unwrap_or_else(|| {
                    panic!("missing WordLevel batch mapping {chinese} -> {english}")
                });
            assert_eq!(sense.part_of_speech, Some(pos));
            assert_eq!(expansion::source(chinese, english), Some("ECDICT MIT"));
            assert!(lookup(english).mask() & selected != 0);
        }
        for (chinese, english) in [
            ("色差", "aberration"),
            ("优势", "ascendancy"),
            ("装配", "configure"),
            ("目前", "immediacy"),
            ("爆裂", "implode"),
            ("利润", "markup"),
        ] {
            assert_eq!(expansion::source(chinese, english), None);
        }

        let mut translated = candidate(&["wordtrailuntaggedsense", "gestation"], Language::English);
        let original_text = translated.text.clone();
        prioritize(&mut translated, selection(&["toefl".into()]).unwrap());
        assert_eq!(translated.text, original_text);
        assert_eq!(
            translated.translation.as_ref().unwrap().senses()[0].text,
            "gestation"
        );
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

        let mut professional = candidate(&["unknownsense", "metastasis"], Language::English);
        prioritize(&mut professional, 1 << 8);
        assert_eq!(
            professional.translation.as_ref().unwrap().senses()[0].text,
            "metastasis"
        );
    }
}
