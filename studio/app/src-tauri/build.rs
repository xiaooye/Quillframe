fn main() {
    #[cfg(target_os = "windows")]
    {
        // Keep the bootstrap icon reproducible and independent from an untracked binary asset.
        // This is a valid 1x1, 32-bit ICO used only by the Windows resource compiler; the
        // distributable brand icon can replace it through the same build attribute later.
        const BOOTSTRAP_ICO: &[u8] = &[
            0x00, 0x00, 0x01, 0x00, 0x01, 0x00, 0x01, 0x01, 0x00, 0x00, 0x01, 0x00, 0x20, 0x00,
            0x30, 0x00, 0x00, 0x00, 0x16, 0x00, 0x00, 0x00, 0x28, 0x00, 0x00, 0x00, 0x01, 0x00,
            0x00, 0x00, 0x02, 0x00, 0x00, 0x00, 0x01, 0x00, 0x20, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x04, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x40, 0x36, 0x2e, 0xff, 0x00, 0x00, 0x00, 0x00,
        ];
        let icon_path = std::path::PathBuf::from(std::env::var_os("OUT_DIR").expect("OUT_DIR"))
            .join("quillframe-bootstrap.ico");
        std::fs::write(&icon_path, BOOTSTRAP_ICO).expect("write bootstrap Windows icon");
        tauri_build::try_build(
            tauri_build::Attributes::new().windows_attributes(
                tauri_build::WindowsAttributes::new().window_icon_path(icon_path),
            ),
        )
        .expect("build Tauri application");
    }

    #[cfg(not(target_os = "windows"))]
    tauri_build::build()
}
