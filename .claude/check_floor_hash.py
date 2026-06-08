"""Pre-commit guard: verify CLAUDE-FLOOR.md matches its sha256 sidecar.

The floor is generated from the methodology hub and must not be hand-edited.
This guard recomputes the sha256 of the floor (after normalizing line
endings) and compares it to the 64-hex digest recorded in the sidecar. On
drift it fails the commit and points at the restore command.
"""

import hashlib
import re
import sys
from pathlib import Path

FLOOR = Path(".claude/CLAUDE-FLOOR.md")
SIDECAR = Path(".claude/CLAUDE-FLOOR.md.sha256")

HEX64 = re.compile(r"[0-9a-fA-F]{64}")


def main() -> int:
    # Floor not adopted in this repo -> nothing to verify.
    if not FLOOR.exists():
        return 0

    # Normalize CRLF and lone CR to LF so the digest is platform-independent.
    normalized = FLOOR.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n")
    computed = hashlib.sha256(normalized).hexdigest()

    match = HEX64.search(SIDECAR.read_text(encoding="utf-8")) if SIDECAR.exists() else None
    if match is None:
        print(
            f"floor-hash: no sha256 digest found in {SIDECAR}",
            file=sys.stderr,
        )
        return 1

    expected = match.group(0).lower()
    if computed != expected:
        print(
            "floor-hash: CLAUDE-FLOOR.md does not match its sha256 sidecar.\n"
            f"  expected (sidecar): {expected}\n"
            f"  computed (floor):   {computed}\n"
            "The floor is generated and must not be hand-edited. Restore it with:\n"
            "  git checkout HEAD -- .claude/CLAUDE-FLOOR.md",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
