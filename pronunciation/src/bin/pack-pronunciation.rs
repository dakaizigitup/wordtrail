use qingjian_core::Language;
use qingjian_format::Metadata;
use qingjian_translate::Glossary;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut args = std::env::args().skip(1);
    let source = args.next().ok_or("input TSV required")?;
    let target = args.next().ok_or("output QJ required")?;
    let glossary = Glossary::from_path(Language::English, source)?;
    glossary.write_qj(
        std::path::Path::new(&target),
        &Metadata {
            name: "Wordtrail independent English IPA (UK / US)".into(),
            license: "GPL-3.0-only (UK); MIT (US)".into(),
            attribution:
                "open-dict-data contributors; UK: leoboiko/ipacards; US: lingz/cmudict-ipa".into(),
            source: "open-dict-data/ipa-dict commit 43c3570eb3553bdd19fccd2bd0091534889af023"
                .into(),
            ..Metadata::default()
        },
    )?;
    println!("Packed {} pronunciation entries", glossary.len());
    Ok(())
}
