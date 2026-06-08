#!/usr/bin/env python
"""Verify CLAUDE-FLOOR.md matches its .sha256 sidecar (LF-normalized; ADR-78)."""
import hashlib
import re
import sys
from pathlib import Path
floor = Path("CLAUDE-FLOOR.md")
if not floor.exists():
    sys.exit(0)  # floor not adopted
text = floor.read_text(encoding="utf-8").replace("\r\n", "\n").replace("\r", "\n")
actual = hashlib.sha256(text.encode("utf-8")).hexdigest()
sc = Path("CLAUDE-FLOOR.md.sha256")
m = re.search(r"[0-9a-f]{64}", sc.read_text(encoding="utf-8")) if sc.exists() else None
expected = m.group(0) if m else ""
if actual != expected:
    print(f"CLAUDE-FLOOR.md hash {actual[:12]} != sidecar {expected[:12] or '<missing>'}"
          " - regenerate from the hub and commit both files.")
    sys.exit(1)
