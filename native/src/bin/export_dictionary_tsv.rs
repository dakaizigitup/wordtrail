//! Export every dictionary entry without collapsing homographs or readings.
//! Used only by the reproducible runtime dictionary overlay build.

use qingjian_dictionary::Dictionary;
use std::{
    env,
    fs::File,
    io::{BufWriter, Write},
    path::Path,
};

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let args: Vec<_> = env::args_os().collect();
    if args.len() != 3 {
        return Err("usage: export_dictionary_tsv input.qj output.tsv".into());
    }
    let dictionary = Dictionary::from_path(Path::new(&args[1]))?;
    let mut output = BufWriter::new(File::create(&args[2])?);
    for entry in dictionary.entries() {
        writeln!(
            output,
            "{}\t{}\t{}",
            entry.text, entry.pinyin, entry.frequency
        )?;
    }
    eprintln!("Exported {} dictionary entries", dictionary.len());
    Ok(())
}
