fn main() {
    if std::env::var_os("CARGO_CFG_WINDOWS").is_some() {
        let manifest = embed_manifest::new_manifest("Wordtrail.DesktopIPA")
            .requested_execution_level(embed_manifest::manifest::ExecutionLevel::AsInvoker)
            .ui_access(false);
        embed_manifest::embed_manifest(manifest).expect("embed Windows manifest");
    }
}
