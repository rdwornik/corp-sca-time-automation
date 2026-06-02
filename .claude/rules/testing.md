# Testing Standards

- pytest for all tests, never unittest
- Test files: tests/test_*.py
- Run: pytest
- Test-coverage expansion gap is tracked in BACKLOG.md P2 (do not hardcode a passing-test count here — it drifts)
- No silent failures — log warnings, raise on errors
