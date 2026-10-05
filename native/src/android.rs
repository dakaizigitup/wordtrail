//! JNI 只搬运 JSON，输入逻辑在共用会话中。
use jni::JNIEnv;
use jni::objects::{JClass, JString};
use jni::sys::jstring;

#[unsafe(no_mangle)]
pub extern "system" fn Java_org_wordtrail_ime_NativeBridge_request(
    mut env: JNIEnv,
    _class: JClass,
    input: JString,
) -> jstring {
    let text = match env.get_string(&input) {
        Ok(value) => String::from(value),
        Err(_) => return std::ptr::null_mut(),
    };
    let response = crate::request_json(&text);
    env.new_string(response)
        .map(|s| s.into_raw())
        .unwrap_or(std::ptr::null_mut())
}
