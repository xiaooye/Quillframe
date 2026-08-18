#!/usr/bin/env python3
"""Build the Tauri external Core binary for the current Rust target.
Usage: python studio/scripts/build_tauri_sidecar.py <target-triple>
Requires PyInstaller in the build environment; it is never a runtime dependency.
"""
from __future__ import annotations
import shutil,subprocess,sys,tempfile
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]; TAURI=ROOT/"studio/app/src-tauri"; SOURCE=ROOT/"studio/core_sidecar_server.py"
def main()->int:
    if len(sys.argv)!=2: raise SystemExit("target triple required")
    target=sys.argv[1]; suffix=".exe" if "windows" in target else ""; destination=TAURI/"binaries"/f"quillframe-core-{target}{suffix}"; destination.parent.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="qf-sidecar-build-") as td:
        subprocess.run([sys.executable,"-m","PyInstaller","--clean","--onefile","--name","quillframe-core","--paths",str(ROOT),"--paths",str(ROOT/"studio"),"--distpath",str(Path(td)/"dist"),"--workpath",str(Path(td)/"work"),"--specpath",str(Path(td)/"spec"),str(SOURCE)],check=True,cwd=ROOT)
        built=Path(td)/"dist"/f"quillframe-core{suffix}"; shutil.copy2(built,destination)
    print(destination); return 0
if __name__=="__main__":raise SystemExit(main())
