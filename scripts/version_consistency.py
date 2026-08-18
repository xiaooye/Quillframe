#!/usr/bin/env python3
from __future__ import annotations
import json, re, sys
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
EXPECTED="0.9.0"
values={}
values["VERSION"]=(ROOT/"VERSION").read_text().strip()
manifest=(ROOT/"HARNESS_MANIFEST.yaml").read_text(encoding="utf-8")
m=re.search(r"(?m)^version:\s*['\"]?([^'\"\s]+)",manifest); values["HARNESS_MANIFEST.yaml"]=m.group(1) if m else None
cli=(ROOT/"quillframe.py").read_text(encoding="utf-8")
m=re.search(r'FRAMEWORK_VERSION\s*=\s*"([^"]+)"',cli); values["quillframe.py"]=m.group(1) if m else None
for path in (ROOT/"site/package.json",ROOT/"studio/app/package.json"):
    if path.exists(): values[path.relative_to(ROOT).as_posix()]=json.loads(path.read_text())["version"]
errors=[f"{k}={v!r}" for k,v in values.items() if v!=EXPECTED]
print(json.dumps({"schema":"quillframe_version_consistency_v1","expected":EXPECTED,"values":values,"ok":not errors,"errors":errors},indent=2))
raise SystemExit(0 if not errors else 1)
