fn main() {
    // tauri-build tracks the config but not its default Windows icon. Without
    // these inputs, an incremental build can keep the previous EXE resources.
    println!("cargo:rerun-if-changed=icons/icon.ico");
    println!("cargo:rerun-if-changed=icons/icon.png");
    tauri_build::build()
}
