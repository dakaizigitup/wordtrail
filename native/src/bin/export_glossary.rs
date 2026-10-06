//! 从实际安装包释义表导出基线，供离线扩词构建去重与词性核对。
use qingjian_core::{Language, Translator};
use qingjian_translate::Glossary;
use std::{
    collections::BTreeSet,
    env, fs,
    io::{BufWriter, Write},
};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<String> = env::args().collect();
    if args.len() != 4 {
        return Err("usage: export_glossary packed.qj keys.tsv output.tsv".into());
    }
    let glossary = Glossary::from_path(Language::English, &args[1])?;
    let keys: BTreeSet<_> = fs::read_to_string(&args[2])?
        .lines()
        .filter(|l| !l.starts_with('#'))
        .filter_map(|l| l.split('\t').next().map(str::to_owned))
        .collect();
    let mut output = BufWriter::new(fs::File::create(&args[3])?);
    let mut count = 0;
    for key in keys {
        if let Some(t) = glossary.translate(&key) {
            write!(output, "{key}")?;
            for sense in t.senses() {
                write!(
                    output,
                    "\t{} {}",
                    sense.part_of_speech.map(|p| p.abbreviation()).unwrap_or(""),
                    sense.text
                )?;
            }
            writeln!(output)?;
            count += 1;
        }
    }
    println!("Exported {count} actual packed glossary entries");
    Ok(())
}
