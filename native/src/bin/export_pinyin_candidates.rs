//! 导出固定汉字词库的候选词面和拼音，用于核查扩词映射是否能从键盘触达。
use qingjian_dictionary::Dictionary;
use std::{
    collections::BTreeMap,
    env,
    fs::File,
    io::{BufWriter, Write},
    path::Path,
};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = env::args().collect();
    if args.len() != 3 {
        return Err("usage: export_pinyin_candidates dict.qj output.tsv".into());
    }
    let dictionary = Dictionary::open_qj(Path::new(&args[1]))?;
    let mut candidates: BTreeMap<&str, (&str, u32)> = BTreeMap::new();
    let mut entry_count = 0usize;
    for entry in dictionary.entries() {
        entry_count += 1;
        let old = candidates
            .entry(entry.text)
            .or_insert((entry.pinyin, entry.frequency));
        if entry.frequency > old.1 {
            *old = (entry.pinyin, entry.frequency);
        }
    }
    let mut output = BufWriter::new(File::create(&args[2])?);
    for (word, (pinyin, frequency)) in &candidates {
        writeln!(output, "{word}\t{pinyin}\t{frequency}")?;
    }
    eprintln!(
        "Exported {} unique candidate surfaces from {entry_count} pinned pinyin entries",
        candidates.len()
    );
    Ok(())
}
