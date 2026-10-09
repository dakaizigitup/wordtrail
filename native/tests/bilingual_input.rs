//! 使用发布数据验证跨语言候选、符号、常用字及输入提交契约。
use serde_json::{Value, json};
use std::path::PathBuf;
use wordtrail_mobile::request_json;

struct Client { handle: u64, state: Value }
impl Client {
    fn send(&mut self, mut req: Value) -> Value {
        req["handle"] = json!(self.handle);
        let response: Value = serde_json::from_str(&request_json(&req.to_string())).unwrap();
        assert!(response["error"].is_null(), "{response}");
        self.state = response["state"].clone();
        self.state.clone()
    }
    fn type_word(&mut self, text: &str) -> Value {
        self.send(json!({"op":"clear"}));
        for ch in text.chars() { self.send(json!({"op":"key","text":ch.to_string()})); }
        self.state.clone()
    }
    fn candidate(&self, text: &str) -> Value {
        self.state["candidates"].as_array().unwrap().iter().find(|c|c["text"]==text)
            .unwrap_or_else(|| panic!("Missing {text}: {}", self.state)).clone()
    }
    fn select(&mut self, op: &str, text: &str) -> Value {
        self.send(json!({"op":op,"index":self.candidate(text)["id"],"revision":self.state["revision"]}))
    }
}

#[test]
fn release_data_bilingual_contracts() {
    let root=PathBuf::from(env!("CARGO_MANIFEST_DIR")).parent().unwrap().to_path_buf();
    let user=root.join("build/test-bilingual-user").join(format!("{}",std::process::id()));
    let response:Value=serde_json::from_str(&request_json(&json!({"op":"create","data_dir":root.join("data/generated"),"user_dir":user}).to_string())).unwrap();
    assert!(response["error"].is_null(),"{response}");
    let mut c=Client{handle:response["handle"].as_u64().unwrap(),state:response["state"].clone()};
    c.type_word("en"); c.candidate("嗯"); c.candidate("恩");
    assert_eq!(c.select("select","嗯")["commit"],"嗯");
    c.type_word("lambda");c.candidate("λ");c.candidate("Λ");
    assert_eq!(c.select("select","λ")["commit"],"λ");
    assert_eq!(c.state["input"],"");
    c.type_word("hello");let hello=c.candidate("hello");
    assert_eq!(hello["kind"],"english");assert!(!hello["annotation"].as_str().unwrap().is_empty());
    assert!(!hello["pronunciation"].is_null());
    let expected=hello["translation_senses"][0]["text"].clone();
    assert_eq!(c.select("translation","hello")["commit"],expected);
    c.send(json!({"op":"toggle"}));
    c.type_word("Comp");assert!(c.state["candidates"].as_array().unwrap().iter().any(|c|c["text"]=="Company"));
    c.type_word("helo");c.candidate("hello");
    assert_eq!(c.send(json!({"op":"space"}))["commit"],"helo ","suggestions must not autocorrect on space");
    c.type_word("WordtrailXYZ");assert_eq!(c.send(json!({"op":"key","text":"."}))["commit"],"WordtrailXYZ.");
    c.type_word("hello");assert_eq!(c.send(json!({"op":"literal","text":"λ"}))["commit"],"helloλ");
    c.type_word("World");assert_eq!(c.send(json!({"op":"enter"}))["commit"],"World");
    assert_eq!(c.send(json!({"op":"enter"}))["commit"],"\n");
    c.send(json!({"op":"language","language":"ja"}));
    c.type_word("hello");assert_eq!(c.candidate("hello")["translation_senses"][0]["text"],expected,"English annotations stay Chinese independent of learning language");
    c.type_word("LAMBDA");assert_eq!(c.select("select","Λ")["commit"],"Λ");
    c.send(json!({"op":"toggle"}));
    c.send(json!({"op":"keypad","text":"3"}));c.send(json!({"op":"keypad","text":"6"}));
    c.send(json!({"op":"keypad_syllable","index":0,"reading":"en"}));c.candidate("嗯");
    assert_eq!(c.select("select","嗯")["commit"],"嗯");
    c.send(json!({"op":"destroy"}));
}
