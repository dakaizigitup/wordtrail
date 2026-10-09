//! 希腊字母名称精确匹配；保留中文候选顺序，不参与用户词频学习。
use qingjian_core::{Candidate, CandidateKind};

const NAMES: &[(&str, &str)] = &[
    ("alpha", "αΑ"), ("beta", "βΒ"), ("gamma", "γΓ"),
    ("delta", "δΔ"), ("epsilon", "εΕ"), ("zeta", "ζΖ"),
    ("eta", "ηΗ"), ("theta", "θΘ"), ("iota", "ιΙ"),
    ("kappa", "κΚ"), ("lambda", "λΛ"), ("lamda", "λΛ"),
    ("mu", "μΜ"), ("nu", "νΝ"), ("xi", "ξΞ"),
    ("omicron", "οΟ"), ("pi", "πΠ"), ("rho", "ρΡ"),
    ("sigma", "σΣ"), ("tau", "τΤ"), ("upsilon", "υΥ"),
    ("phi", "φΦ"), ("chi", "χΧ"), ("psi", "ψΨ"), ("omega", "ωΩ"),
];

pub fn insert(input: &str, candidates: &mut Vec<Candidate>) {
    let Some((_, symbols)) = NAMES.iter().find(|(name, _)| input.eq_ignore_ascii_case(name)) else { return };
    let items = symbols.chars().map(|symbol| Candidate {
        text: symbol.to_string(), kind: CandidateKind::Shortcut, syllables: Vec::new(),
        reading: None, translation: None, aux_code: None,
    });
    // 常用拼音如 mu、pi 仍优先中文；符号固定在首屏，不挤掉原有首选。
    let position = candidates.len().min(1);
    candidates.splice(position..position, items);
}
