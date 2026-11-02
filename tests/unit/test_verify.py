from pathlib import Path

from forgecore.core.models import Severity
from forgecore.core.verify.verifier import Verifier

FIXTURES_DIR = Path(__file__).resolve().parent.parent / "fixtures"


def test_verifier_catches_hardcoded_secrets():
    root = FIXTURES_DIR / "violations_app"
    verifier = Verifier(root)
    report = verifier.verify(scope="all")

    assert report.status == "failed"
    assert report.summary["critical"] > 0

    secret_findings = [f for f in report.findings if f.rule_id == "UNI-SEC-001"]
    assert len(secret_findings) > 0
    assert "AKIA1234567890ABCDEF" not in secret_findings[0].message  # Secret value never leaked!
    assert "auth.py" in secret_findings[0].file
    assert secret_findings[0].line == 2
    assert secret_findings[0].severity == Severity.CRITICAL


def test_verifier_clean_fixture():
    root = FIXTURES_DIR / "fastapi_app"
    verifier = Verifier(root)
    report = verifier.verify(scope="all")

    # fastapi_app has no seeded violations, so findings should be 0 critical/high
    assert report.summary["critical"] == 0
    assert report.summary["high"] == 0
    # Status may be incomplete if semgrep is not installed, but not failed!
    assert report.status in ("passed", "incomplete")
