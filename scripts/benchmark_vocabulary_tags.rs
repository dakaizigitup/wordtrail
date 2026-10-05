//! Standalone host-only lookup prototype. Not linked into the keyboard.
//! rustc -O scripts/benchmark_vocabulary_tags.rs -o build/tag-bench.exe
//! build/tag-bench.exe research-only-tags.tsv
use std::{collections::HashMap, env, fs, hint::black_box, time::Instant};

fn preferred_order(masks: &[u16], selected: u16) -> Vec<usize> {
    let mut order: Vec<_> = (0..masks.len()).collect();
    // Stable ties: only matching senses move forward; no entry is removed.
    order.sort_by_key(|&i| (masks[i] & selected == 0, i));
    order
}

fn main() {
    let source = fs::read_to_string(env::args().nth(1).expect("TSV path required")).unwrap();
    let start = Instant::now();
    let mut table: Vec<(String, u16)> = source.lines().map(|line| {
        let (word, mask) = line.split_once('\t').expect("word TAB mask");
        (word.to_owned(), mask.parse().unwrap())
    }).collect();
    table.sort_unstable_by(|a,b| a.0.cmp(&b.0));
    let map: HashMap<&str,u16> = table.iter().map(|(w,m)| (w.as_str(),*m)).collect();
    let init_us = start.elapsed().as_micros();
    assert_eq!(preferred_order(&[1,32,0,34,2],32), vec![1,3,0,2,4]);
    assert_eq!(preferred_order(&[1,32,0,34,2],0), vec![0,1,2,3,4]);
    assert_eq!(preferred_order(&[1,32,0,34,2],2|32), vec![1,3,4,0,2]);
    let mut queries = Vec::new();
    for (n, (word,_)) in table.iter().enumerate().step_by(3) {
        queries.push(if n%2==0 { word.to_ascii_uppercase() } else { word.clone() });
        queries.push(format!("wordtrail-unknown-{n}"));
    }
    let mut result = Vec::new();
    for kind in ["binary-search", "hash-map"] {
        let mut times = Vec::new();
        for batch in 0..11000 {
            let start = Instant::now();
            for card in 0..9 {
                let masks: Vec<_> = (0..2).map(|sense| {
                    let q = black_box(&queries[(batch*18+card*2+sense)%queries.len()]);
                    let normalized = q.trim().to_ascii_lowercase();
                    let mask = if kind=="binary-search" {
                        table.binary_search_by(|(w,_)| w.as_str().cmp(normalized.as_str()))
                            .ok().map(|index| table[index].1).unwrap_or(0)
                    } else { map.get(normalized.as_str()).copied().unwrap_or(0) };
                    black_box(mask)
                }).collect();
                black_box(preferred_order(&masks, black_box(32)));
            }
            let elapsed = start.elapsed().as_nanos() as u64;
            if batch>=1000 { times.push(elapsed); }
        }
        times.sort_unstable();
        result.push(format!("{{\"kind\":\"{kind}\",\"p50_batch_ns\":{},\"p95_batch_ns\":{},\"p99_batch_ns\":{}}}", times[5000],times[9500],times[9900]));
    }
    println!("{{\"words\":{},\"tsv_bytes\":{},\"initialization_us\":{init_us},\"batch_lookups\":18,\"cards_per_batch\":9,\"batches_per_kind\":10000,\"results\":[{}],\"ordering_assertions\":3,\"scope\":\"Windows optimized Rust host prototype; no Android UI/JNI or cold-start measurement\"}}",table.len(),source.len(),result.join(","));
}
