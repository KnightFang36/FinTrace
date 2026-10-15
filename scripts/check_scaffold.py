"""Check scaffold contracts with the standard library; does not test detection."""

from __future__ import annotations

import ast
import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_DIRECTORIES = ["app","app/components","app/views","config","data","data/processed","data/raw","data/raw/ibm","data/reference","docs","docs/features","docs/features/account_investigation","docs/features/alerts","docs/features/cases","docs/features/dashboard","docs/features/entity_context","docs/features/evaluation","docs/features/ingestion","docs/features/network_investigation","docs/features/priority_scoring","docs/features/replay","docs/features/reporting","docs/features/screening","docs/features/temporal_graphs","docs/features/transaction_rules","docs/features/validation","outputs","scripts","src","src/fintrace","src/fintrace/alerts","src/fintrace/cases","src/fintrace/context","src/fintrace/evaluation","src/fintrace/graph","src/fintrace/ingestion","src/fintrace/investigations","src/fintrace/replay","src/fintrace/reporting","src/fintrace/rules","src/fintrace/scoring","src/fintrace/screening","src/fintrace/storage","src/fintrace/validation","tests","tests/fixtures","tests/integration","tests/unit"]
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
    checked_directories = 0
    for relative in [".", *REQUIRED_DIRECTORIES]:
        directory = ROOT / relative
        if not directory.is_dir():
            errors.append(f"Missing directory: {relative}")
        elif not (directory / "AGENTS.md").is_file():
            errors.append(f"Missing folder instructions: {relative}/AGENTS.md")
        checked_directories += 1

    for relative in CODE_AND_DOC_ROOTS:
        for directory in (ROOT / relative).rglob("*"):
            if not directory.is_dir():
                continue
            if any(part in IGNORED_DIRECTORIES or part.startswith(".") for part in directory.relative_to(ROOT).parts):
                continue
            if not (directory / "AGENTS.md").is_file():
                errors.append(f"Missing folder instructions: {directory.relative_to(ROOT)}")

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

    markdown_files = [ROOT / "README.md", ROOT / "AGENTS.md"]
    for relative in CODE_AND_DOC_ROOTS:
        markdown_files.extend((ROOT / relative).rglob("*.md"))
    markdown_files.extend((ROOT / "data").rglob("AGENTS.md"))
    markdown_files.extend((ROOT / "outputs").rglob("AGENTS.md"))
    for path in markdown_files:
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

    feature_directories = sorted(
        path for path in (ROOT / "docs/features").iterdir() if path.is_dir()
    )
    for feature in feature_directories:
        readme = feature / "README.md"
        if not readme.is_file():
            errors.append(f"Missing feature contract: {feature.name}")
            continue
        content = readme.read_text(encoding="utf-8")
        for heading in (
            "## Inputs", "## Outputs", "## Functionality",
            "## Errors and edge cases", "## Acceptance criteria", "## Data availability",
        ):
            if heading not in content:
                errors.append(f"Incomplete feature contract {feature.name}: {heading}")

    if errors:
        for error in sorted(set(errors)):
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        f"Scaffold checks passed: {checked_directories} required directories, "
        f"{len(feature_directories)} feature contracts, "
        f"{len(python_files)} Python files, valid TOML and local links."
    )
    print("Detection, persistence, exports and dashboard functionality remain unimplemented.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
