"""Check and package the exact Phase 1 deliverables without API calls or local secrets."""
import argparse
import hashlib
import json
import re
import sys
import zipfile
from pathlib import Path

from phase1.domain import SCENARIOS
from phase1.evidence import TraceError, render_markdown, verify_trace


ROOT = Path(__file__).resolve().parent.parent
REQUIRED = ["README.md", "requirements.md", "policies.md", "DEMO.md", "SUBMISSION.md", "REVIEW.md",
            "LICENSE", ".gitignore", ".gitattributes", ".env.example", ".github/workflows/ci.yml",
            "traces/README.md", "traces/FORMAT.md", "ENROLLMENT_RULES.md"]
SECRET_PATTERN = re.compile(rb"(?:sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})")


def submission_files(root=ROOT):
    paths = [root / name for name in REQUIRED]
    paths += list((root / "phase1").glob("*.py")) + list((root / "tests").glob("test_*.py"))
    for scenario in SCENARIOS:
        paths += [root / "traces" / "phase1" / f"{scenario}{suffix}" for suffix in (".json", ".md")]
    return sorted(set(paths))


def check(root=ROOT):
    files = submission_files(root)
    for path in files:
        if not path.is_file() or path.is_symlink():
            raise TraceError(f"Missing file or unexpected symlink: {path.relative_to(root)}")
        if SECRET_PATTERN.search(path.read_bytes()):
            raise TraceError(f"Possible credential in submission file: {path.relative_to(root)}")
    if ".env" not in (root / ".gitignore").read_text().splitlines():
        raise TraceError(".env must be excluded by .gitignore.")
    reports = []
    for scenario in SCENARIOS:
        path = root / "traces" / "phase1" / f"{scenario}.json"
        trace = json.loads(path.read_text())
        if trace["scenario"] != scenario:
            raise TraceError(f"Scenario filename mismatch: {path.name}")
        reports.append(verify_trace(trace, current_source=True))
        if path.with_suffix(".md").read_text() != render_markdown(trace):
            raise TraceError(f"Readable trace is stale: {path.with_suffix('.md').name}")
    manifest = {"phase": 1, "scenarios": reports,
                "files_sha256": {str(path.relative_to(root)): hashlib.sha256(path.read_bytes()).hexdigest()
                                 for path in files}}
    return files, manifest


def package(destination, root=ROOT):
    files, manifest = check(root)
    destination = Path(destination)
    if destination.exists():
        raise TraceError("Package already exists; choose a new output filename.")
    destination.parent.mkdir(parents=True, exist_ok=True)
    # An explicit file list excludes .env, caches, history, .git, and failed/local runs.
    with zipfile.ZipFile(destination, "x", compression=zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, arcname=str(path.relative_to(root)))
        archive.writestr("manifest.json", json.dumps(manifest, indent=2) + "\n")
    return destination


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, metavar="PATH", help="Create a ZIP from the verified file allowlist.")
    args = parser.parse_args()
    try:
        files, manifest = check()
        print(f"PASS: {len(files)} submission files, {len(manifest['scenarios'])} completed LLM traces, "
              "source hashes, replay, and credential scan.")
        for report in manifest["scenarios"]:
            print(f"  {report['scenario']}: {report['model_calls']} calls, {report['events']} events, "
                  f"audit policies {', '.join(report['policies']) or 'none'}")
        if args.package:
            print(f"Package: {package(args.package)}")
    except (TraceError, OSError, ValueError) as error:
        print(f"Submission check failed: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
