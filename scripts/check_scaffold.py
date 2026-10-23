"""Check maintained structure, syntax, policies and links without loading local data."""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DIRECTORIES = [
    "app", "app/components", "app/views", "config", "data", "docs", "scripts", "src", "src/fintrace",
    "src/fintrace/alerts", "src/fintrace/cases", "src/fintrace/graph", "src/fintrace/ingestion",
    "src/fintrace/investigations", "src/fintrace/replay", "src/fintrace/reporting",
    "src/fintrace/rules", "src/fintrace/scoring", "src/fintrace/storage", "src/fintrace/validation",
    "tests", "tests/integration", "tests/unit",
]
REQUIRED_DOCUMENTS = ["README.md", "docs/architecture.md", "docs/data_contracts.md",
                      "docs/services.md", "docs/validation.md"]
CODE_AND_DOC_ROOTS = ("app", "config", "docs", "scripts", "src", "tests")
IGNORED_DIRECTORIES = {"__pycache__", ".pytest_cache", ".venv"}
FORBIDDEN_DEPENDENCIES = {
    "scikit-learn", "sklearn", "torch", "pytorch", "tensorflow",
    "xgboost", "lightgbm", "catboost", "transformers", "shap",
    "openai", "anthropic", "sentence-transformers", "node2vec",
}
LINK = re.compile(r"(?<!!)\[[^\]]+\]\(([^)]+)\)")


def main() -> int:
    errors: list[str] = []
    for relative in REQUIRED_DIRECTORIES:
        if not (ROOT / relative).is_dir():
            errors.append(f"Missing directory: {relative}")
    for relative in REQUIRED_DOCUMENTS:
        if not (ROOT / relative).is_file():
            errors.append(f"Missing document: {relative}")
    # Keep one root guide; no per-folder README scaffolding.
    for relative in CODE_AND_DOC_ROOTS:
        for path in (ROOT / relative).rglob("README.md"):
            if not any(part in IGNORED_DIRECTORIES for part in path.relative_to(ROOT).parts):
                errors.append(f"Redundant folder document: {path.relative_to(ROOT)}")

    python_files = [
        path for relative in ("app", "scripts", "src", "tests")
        for path in (ROOT / relative).rglob("*.py")
        if not any(part in IGNORED_DIRECTORIES for part in path.relative_to(ROOT).parts)
    ]
    for path in python_files:
        try:
            ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError as error:
            errors.append(f"Python syntax: {path.relative_to(ROOT)}: {error}")

    markdown_files = [ROOT / "README.md"]
    for relative in CODE_AND_DOC_ROOTS:
        markdown_files.extend((ROOT / relative).rglob("*.md"))
    for path in markdown_files:
        if not path.is_file():
            continue
        content = path.read_text(encoding="utf-8")
        for match in LINK.finditer(content):
            target = match.group(1).strip().strip("<>")
            if "://" in target or target.startswith(("mailto:", "#")):
                continue
            target = target.split("#", 1)[0]
            if target and not (path.parent / target).exists():
                errors.append(f"Broken local link: {path.relative_to(ROOT)} -> {target}")

    parsed: dict[str, dict] = {}
    for path in [ROOT / "pyproject.toml", *sorted((ROOT / "config").glob("*.toml"))]:
        try:
            parsed[path.name] = tomllib.loads(path.read_text(encoding="utf-8"))
        except tomllib.TOMLDecodeError as error:
            errors.append(f"TOML syntax: {path.relative_to(ROOT)}: {error}")

    project = parsed.get("pyproject.toml", {}).get("project", {})
    dependencies = list(project.get("dependencies", []))
    for group in project.get("optional-dependencies", {}).values():
        dependencies.extend(group)
    for requirement in dependencies:
        name = re.split(r"[\s\[<>=!~;]", requirement, maxsplit=1)[0].strip().lower().replace("_", "-")
        if name in FORBIDDEN_DEPENDENCIES:
            errors.append(f"Excluded dependency: {name}")

    scoring = parsed.get("scoring.toml", {})
    rules = parsed.get("rules.toml", {})
    if scoring and rules and scoring.get("policy_version") != rules.get("policy_version"):
        errors.append("Detection and scoring policy versions differ")
    if scoring:
        families = scoring.get("families", {})
        rule_ids: set[str] = set()
        for family, policy in families.items():
            if not isinstance(policy.get("weight"), int) or not 0 <= policy["weight"] <= 100:
                errors.append(f"Invalid family weight: {family}")
            for rule_id in policy.get("rules", []):
                if rule_id in rule_ids:
                    errors.append(f"Rule appears in multiple scoring families: {rule_id}")
                rule_ids.add(rule_id)
                if rule_id not in rules:
                    errors.append(f"Scoring references unconfigured rule: {rule_id}")
        boundaries = [scoring.get(key) for key in (
            "low_minimum", "medium_minimum", "high_minimum", "critical_minimum"
        )]
        if not all(isinstance(value, int) for value in boundaries):
            errors.append("Missing integer priority boundaries")
        elif boundaries != sorted(set(boundaries)) or boundaries[0] != 0 or boundaries[-1] > 100:
            errors.append("Invalid priority band ordering")
        if scoring.get("maximum_score") != 100:
            errors.append("Priority maximum must be 100")

    contracts = ROOT / "docs/services.md"
    if contracts.is_file():
        content = contracts.read_text(encoding="utf-8")
        for heading in (
            "Ingestion and validation", "Transaction rules", "Temporal graphs", "Priorities and alerts",
            "Account and network investigation", "Cases", "Reports", "Historical replay",
            "Dashboard and acceptance checks",
        ):
            if f"## {heading}" not in content:
                errors.append(f"Missing service contract: {heading}")

    if errors:
        for error in sorted(set(errors)):
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        f"Structure checks passed: {len(REQUIRED_DIRECTORIES)} required directories, "
        f"{len(REQUIRED_DOCUMENTS)} maintained documents, "
        f"{len(python_files)} Python files, valid TOML and local links."
    )
    print("Structure checks do not verify runtime functionality; run the implemented feature tests separately.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
