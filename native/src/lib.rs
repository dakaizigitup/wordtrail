//! JSON/C ABI 与 Android JNI。所有异常在 FFI 边界转成错误，不向系统展开栈。
#[cfg(target_os = "android")]
mod android;
mod model;
mod keypad;
mod session;
mod symbols;
mod vocabulary;

use model::{Request, Response};
use session::Session;
use std::collections::HashMap;
use std::ffi::{CStr, CString, c_char};
use std::panic::{AssertUnwindSafe, catch_unwind};
use std::sync::{Mutex, OnceLock};

struct Registry {
    next: u64,
    sessions: HashMap<u64, Session>,
}
static REGISTRY: OnceLock<Mutex<Registry>> = OnceLock::new();

pub fn request_json(json: &str) -> String {
    let result = catch_unwind(AssertUnwindSafe(|| execute(json)));
    let response = match result {
        Ok(Ok(response)) => response,
        Ok(Err(error)) => Response {
            handle: 0,
            state: None,
            error: Some(error),
        },
        Err(_) => Response {
            handle: 0,
            state: None,
            error: Some("engine panic caught at mobile boundary".into()),
        },
    };
    serde_json::to_string(&response)
        .unwrap_or_else(|_| "{\"handle\":0,\"error\":\"serialization failed\"}".into())
}

fn execute(json: &str) -> Result<Response, String> {
    if json.len() > 65536 {
        return Err("request too large".into());
    }
    let request: Request = serde_json::from_str(json).map_err(|e| e.to_string())?;
    let registry = REGISTRY.get_or_init(|| {
        Mutex::new(Registry {
            next: 1,
            sessions: HashMap::new(),
        })
    });
    let mut registry = registry.lock().map_err(|_| "engine registry is poisoned")?;
    if request.op == "create" {
        if registry.sessions.len() >= 8 {
            return Err("too many engine sessions".into());
        }
        let mut session = Session::new(&request)?;
        let state = session.state();
        let handle = registry.next;
        registry.next += 1;
        registry.sessions.insert(handle, session);
        return Ok(Response {
            handle,
            state: Some(state),
            error: None,
        });
    }
    if request.op == "destroy" {
        registry
            .sessions
            .remove(&request.handle)
            .ok_or("invalid engine handle")?;
        return Ok(Response {
            handle: request.handle,
            state: None,
            error: None,
        });
    }
    let session = registry
        .sessions
        .get_mut(&request.handle)
        .ok_or("invalid engine handle")?;
    let state = session.action(&request)?;
    Ok(Response {
        handle: request.handle,
        state: Some(state),
        error: None,
    })
}

/// 调用方必须传入以 NUL 结尾的 UTF-8 字串；返回值必须由 qjm_string_free 释放。
///
/// # Safety
/// 非空指针必须在调用期间指向有效的 NUL 结尾字串。
#[unsafe(no_mangle)]
pub unsafe extern "C" fn qjm_request(json: *const c_char) -> *mut c_char {
    let response = if json.is_null() {
        "{\"handle\":0,\"error\":\"null request\"}".to_string()
    } else {
        match unsafe { CStr::from_ptr(json) }.to_str() {
            Ok(text) => request_json(text),
            Err(_) => "{\"handle\":0,\"error\":\"invalid UTF-8\"}".to_string(),
        }
    };
    CString::new(response).unwrap_or_default().into_raw()
}

/// 只接受由 qjm_request 返回且尚未释放的指针。
///
/// # Safety
/// 非空指针必须来自 qjm_request，且只释放一次。
#[unsafe(no_mangle)]
pub unsafe extern "C" fn qjm_string_free(text: *mut c_char) {
    if !text.is_null() {
        drop(unsafe { CString::from_raw(text) });
    }
}
