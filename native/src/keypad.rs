//! 九键拼音的有界解码与逐音节筛选；数字编码只初始化一次。
use std::collections::{HashMap, HashSet};
use std::sync::OnceLock;

pub(crate) const MAX_READINGS: usize = 24;
const MAX_PARTIAL_READINGS: usize = 96;

struct SyllableCode {
    text: String,
    code: String,
    cost: u32,
}

pub(crate) fn keypad_code(letter: char) -> Option<char> {
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

fn letter_cost(letter: char) -> u32 {
    match letter {
        'a' | 'd' | 'h' | 'j' | 'n' | 's' | 't' | 'y' | 'z' => 0,
        'b' | 'e' | 'g' | 'i' | 'k' | 'm' | 'r' | 'u' => 1,
        'c' | 'f' | 'l' | 'o' | 'p' | 'v' | 'w' => 2,
        'q' | 'x' => 3,
        _ => 10,
    }
}

fn syllables() -> &'static [SyllableCode] {
    static TABLE: OnceLock<Vec<SyllableCode>> = OnceLock::new();
    TABLE.get_or_init(|| {
        let mut table = Vec::new();
        let mut known = HashSet::new();
        for text in qingjian_core::parser::SYLLABLES {
            known.insert((*text).to_owned());
            table.push(SyllableCode {
                text: (*text).to_owned(),
                code: text.chars().filter_map(keypad_code).collect(),
                cost: text.chars().map(letter_cost).sum(),
            });
        }
        // 单个声母也可以被锁定，支持“w'y'f'x”这类逐字简拼。
        for initial in "bpmfdtnlgkhjqxrzcswy".chars() {
            if known.insert(initial.to_string()) {
                table.push(SyllableCode {
                    text: initial.to_string(),
                    code: keypad_code(initial).unwrap().to_string(),
                    cost: letter_cost(initial) + 8,
                });
            }
        }
        table
    })
}

pub(crate) fn prefix_code(prefix: &[String]) -> String {
    prefix
        .iter()
        .flat_map(|s| s.chars())
        .filter_map(keypad_code)
        .collect()
}

pub(crate) fn normalize_prefix(digits: &str, prefix: &mut Vec<String>) {
    while !digits.starts_with(&prefix_code(prefix)) {
        prefix.pop();
    }
}

pub(crate) fn next_syllables(
    digits: &str,
    prefix: &[String],
    frequencies: &HashMap<String, u64>,
) -> Vec<String> {
    let code = prefix_code(prefix);
    if digits.is_empty() || !digits.starts_with(&code) {
        return Vec::new();
    }
    let tail = &digits[code.len()..];
    if tail.is_empty() {
        return Vec::new();
    }
    let mut options: HashMap<String, (u64, u32)> = HashMap::new();
    for syllable in syllables() {
        let value = if tail.starts_with(&syllable.code) {
            &syllable.text
        } else if syllable.code.starts_with(tail) {
            &syllable.text[..tail.len()]
        } else {
            continue;
        };
        let mut path = prefix.to_vec();
        path.push(value.to_owned());
        let score = frequencies
            .get(&path.join(" "))
            .copied()
            .unwrap_or(0)
            .saturating_mul(4)
            .saturating_add(frequencies.get(value).copied().unwrap_or(0));
        options
            .entry(value.to_owned())
            .and_modify(|entry| {
                entry.0 = entry.0.max(score);
                entry.1 = entry.1.min(syllable.cost);
            })
            .or_insert((score, syllable.cost));
    }
    let mut options: Vec<_> = options.into_iter().collect();
    options.sort_by(|a, b| {
        b.1.0
            .cmp(&a.1.0)
            .then_with(|| a.1.1.cmp(&b.1.1))
            .then_with(|| a.0.cmp(&b.0))
    });
    options.into_iter().map(|(s, _)| s).collect()
}

fn keep_partial(paths: &mut Vec<(String, u32)>, text: String, cost: u32) {
    if paths.iter().any(|(value, _)| value == &text) {
        return;
    }
    paths.push((text, cost));
    paths.sort_by(|a, b| a.1.cmp(&b.1).then_with(|| a.0.cmp(&b.0)));
    paths.truncate(MAX_PARTIAL_READINGS);
}

fn keep_finished(
    paths: &mut Vec<(String, u32, u64)>,
    text: String,
    cost: u32,
    frequencies: &HashMap<String, u64>,
) {
    if paths.iter().any(|(value, _, _)| value == &text) {
        return;
    }
    let frequency = frequencies
        .get(&text.replace('\'', " "))
        .copied()
        .unwrap_or(0);
    paths.push((text, cost, frequency));
    paths.sort_by(|a, b| {
        b.2.cmp(&a.2)
            .then_with(|| a.1.cmp(&b.1))
            .then_with(|| a.0.cmp(&b.0))
    });
    paths.truncate(MAX_READINGS);
}

#[cfg(test)]
pub(crate) fn t9_readings(digits: &str, frequencies: &HashMap<String, u64>) -> Vec<String> {
    t9_readings_with_prefix(digits, frequencies, &[])
}

pub(crate) fn t9_readings_with_prefix(
    digits: &str,
    frequencies: &HashMap<String, u64>,
    prefix: &[String],
) -> Vec<String> {
    if digits.is_empty() || !digits.bytes().all(|key| (b'2'..=b'9').contains(&key)) {
        return Vec::new();
    }
    let code = prefix_code(prefix);
    if !digits.starts_with(&code) {
        return Vec::new();
    }
    if code.len() == digits.len() {
        return vec![prefix.join("'")];
    }
    let mut paths = vec![Vec::<(String, u32)>::new(); digits.len() + 1];
    let mut finished = Vec::new();
    paths[code.len()].push((prefix.join("'"), 0));
    for start in code.len()..digits.len() {
        let tail = &digits[start..];
        for (head, cost) in paths[start].clone() {
            for syllable in syllables() {
                if tail.starts_with(&syllable.code) {
                    let end = start + syllable.code.len();
                    let text = if head.is_empty() {
                        syllable.text.clone()
                    } else {
                        format!("{head}'{}", syllable.text)
                    };
                    if end == digits.len() {
                        keep_finished(&mut finished, text, cost + syllable.cost, frequencies);
                    } else {
                        keep_partial(&mut paths[end], text, cost + syllable.cost);
                    }
                } else if syllable.code.starts_with(tail) {
                    let partial = &syllable.text[..tail.len()];
                    let text = if head.is_empty() {
                        partial.to_owned()
                    } else {
                        format!("{head}'{partial}")
                    };
                    keep_finished(
                        &mut finished,
                        text,
                        cost + partial.chars().map(letter_cost).sum::<u32>() + 6,
                        frequencies,
                    );
                }
            }
        }
    }
    finished.into_iter().map(|(s, _, _)| s).collect()
}

#[cfg(test)]
mod tests {
    use super::{next_syllables, normalize_prefix, prefix_code, t9_readings_with_prefix};
    use std::collections::HashMap;

    #[test]
    fn long_input_can_be_resolved_one_syllable_at_a_time() {
        let digits = "96968329";
        let mut prefix = Vec::new();
        for syllable in ["wo", "you", "fa", "x"] {
            let choices = next_syllables(digits, &prefix, &HashMap::new());
            assert!(
                choices.contains(&syllable.to_string()),
                "{prefix:?}: {choices:?}"
            );
            assert!(choices.iter().all(|s| !s.contains('\'')));
            prefix.push(syllable.to_owned());
            let readings = t9_readings_with_prefix(digits, &HashMap::new(), &prefix);
            assert!(!readings.is_empty());
            assert!(readings.iter().all(|s| s.starts_with(&prefix.join("'"))));
        }
        assert_eq!(prefix_code(&prefix), digits);
        assert!(next_syllables(digits, &prefix, &HashMap::new()).is_empty());
        assert_eq!(
            t9_readings_with_prefix(digits, &HashMap::new(), &prefix),
            vec!["wo'you'fa'x"]
        );
    }

    #[test]
    fn deleting_digits_rolls_back_only_affected_confirmed_syllables() {
        let mut prefix = vec!["wo".into(), "you".into(), "fa".into(), "x".into()];
        normalize_prefix("9696832", &mut prefix);
        assert_eq!(prefix, vec!["wo", "you", "fa"]);
        normalize_prefix("969683", &mut prefix);
        assert_eq!(prefix, vec!["wo", "you"]);
    }
}
