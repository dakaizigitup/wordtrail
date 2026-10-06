//! 组句中「修饰键 + 数字」的快捷键：上屏译词、删候选。与 macOS 壳对齐。

use qingjian_core::{Candidate, CandidateList};
use qingjian_platform::protocol::KeyModifiers;

use super::Effect;
use crate::dispatch::Router;

impl Router {
    /// 配到哪组就上屏第一 / 第二个译词或删候选；哪组都不是返回 `None`，按普通键处理。
    pub(super) fn apply_digit_shortcut(
        &mut self,
        digit: usize,
        chord: KeyModifiers,
    ) -> Option<Effect> {
        if chord == KeyModifiers::default() {
            return None;
        }
        let (first, second) = self.config.translation_keys;
        let effect = if chord == first {
            self.commit_translation_on_page(digit, 0)
        } else if chord == second {
            self.commit_translation_on_page(digit, 1)
        } else if chord == self.config.delete_keys {
            self.forget_on_page(digit)
        } else if chord.ctrl && chord.alt && !chord.shift && !chord.win {
            self.cycle_translation_on_page(digit)
        } else {
            return None;
        };
        Some(effect)
    }

    pub(in crate::dispatch) fn browse_translation(&self, candidate: &mut Candidate) {
        if let Some((word, offset)) = &self.translation_browse {
            if candidate.text == *word {
                if let Some(t) = candidate.translation.as_mut() {
                    let len = t.senses().len();
                    if t.language == qingjian_core::Language::English && len > 2 {
                        t.senses_mut().rotate_left(offset % len);
                    }
                }
            }
        }
    }

    fn cycle_translation_on_page(&mut self, digit: usize) -> Effect {
        if let Some(candidate) = self.annotated_candidate_on_page(digit) {
            let len = candidate
                .translation
                .as_ref()
                .map_or(0, |t| t.senses().len());
            if len > 2 {
                let offset = self
                    .translation_browse
                    .as_ref()
                    .filter(|(w, _)| *w == candidate.text)
                    .map_or(0, |(_, n)| *n);
                self.translation_browse = Some((candidate.text.clone(), (offset + 2) % len));
                self.notice = Some(format!(
                    "「{}」译词 {}/{}；继续 Ctrl+Alt+{}，按原译词快捷键输入",
                    candidate.text,
                    (offset + 2) % len + 1,
                    len,
                    digit
                ));
            }
        }
        Effect::Navigated
    }

    /// 上屏第 `digit` 个候选的第 `sense` 条译文；没有那条译文就吞掉按键不动。
    fn commit_translation_on_page(&mut self, digit: usize, sense: usize) -> Effect {
        let Some(candidate) = self.annotated_candidate_on_page(digit) else {
            tracing::debug!(digit, "这一格没有候选");
            return Effect::Navigated;
        };
        match self.engine.commit_translation(&candidate, sense) {
            Some(text) => Effect::Changed(Some(text)),
            None => {
                tracing::debug!(digit, sense, "这个候选没有这条译文");
                Effect::Navigated
            }
        }
    }

    /// 删第 `digit` 个候选（用户词整删、词库词清学习记录），提示随下一帧下发。
    fn forget_on_page(&mut self, digit: usize) -> Effect {
        let Some(candidate) = self.candidate_on_page(digit) else {
            tracing::debug!(digit, "这一格没有候选，没什么可删");
            return Effect::Navigated;
        };
        let forgotten = self.engine.forget(&candidate);
        let text = &candidate.text;
        let message = if forgotten.user_word {
            format!("已删除用户词「{text}」")
        } else if forgotten.learning {
            format!("已忘掉对「{text}」的学习记录")
        } else {
            format!("「{text}」是词库里的词，也没有学习记录，没什么可删")
        };
        tracing::info!(%message);
        self.notice = Some(message);
        Effect::Changed(None)
    }

    /// 当前页第 `digit` 个候选（1 起）。
    fn candidate_on_page(&self, digit: usize) -> Option<Candidate> {
        let page_size = self.config.page_size;
        let page = self.highlight / page_size;
        let index = page * page_size + digit.checked_sub(1)?;
        self.layout_candidate(index)
    }

    /// 同上，补上译文（布局里存的是查询原样，译文画页时才补）。
    fn annotated_candidate_on_page(&self, digit: usize) -> Option<Candidate> {
        let candidate = self.candidate_on_page(digit)?;
        let mut list = CandidateList {
            items: vec![candidate],
        };
        self.engine.annotate(&mut list);
        for candidate in &mut list.items {
            wordtrail_vocabulary::prioritize(candidate, self.vocabulary_targets);
            self.browse_translation(candidate);
        }
        list.items.pop()
    }
}
