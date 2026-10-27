"""Validate every JSON file of the Power BI project under dashboards/ against its schema.

Each PBIR / PBIP JSON file names its schema in "$schema" (an https URL under
developer.microsoft.com/json-schemas/). The schemas are read from a local copy of
github.com/microsoft/json-schemas, so the check runs offline:

    uv run python scripts/validate_pbip.py --schemas /path/to/json-schemas

Without --schemas (and without the PBIP_SCHEMAS environment variable) the script prints
that it skipped and exits 0, so CI does not need network access. jsonschema and
referencing are imported only when a schema folder is given.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DASHBOARDS = ROOT / "dashboards"
PREFIX = "https://developer.microsoft.com/json-schemas/"


def project_files(folder: Path) -> list[Path]:
    """Every JSON file of the project: *.json, *.pbir, *.pbism and the *.pbip shortcut."""
    suffixes = {".json", ".pbir", ".pbism", ".pbip"}
    skip = {".pbi"}  # Desktop's local settings and cache, never committed
    return sorted(
        p for p in folder.rglob("*")
        if p.is_file() and p.suffix in suffixes and not skip & set(p.parts)
        and "html" not in p.relative_to(folder).parts
    )


def local_path(schema_root: Path, url: str) -> Path:
    """Map a schema URL to the local copy (the embedded variants use a dash on disk)."""
    rel = url.split("#", 1)[0][len(PREFIX):]
    path = schema_root / rel
    if not path.exists() and path.name == "schema.embedded.json":
        path = path.with_name("schema-embedded.json")
    return path


def validate(folder: Path, schema_root: Path) -> list[str]:
    from jsonschema import Draft7Validator
    from referencing import Registry, Resource
    from referencing.jsonschema import DRAFT7

    def retrieve(uri: str) -> Resource:
        if not uri.startswith(PREFIX):
            raise LookupError(uri)
        contents = json.loads(local_path(schema_root, uri).read_text(encoding="utf-8"))
        return Resource.from_contents(contents, default_specification=DRAFT7)

    registry = Registry(retrieve=retrieve)
    errors: list[str] = []
    for path in project_files(folder):
        rel = path.relative_to(folder)
        raw = path.read_bytes()
        if raw.startswith(b"\xef\xbb\xbf"):
            errors.append(f"{rel}: UTF-8 byte order mark")
        doc = json.loads(raw.decode("utf-8"))
        url = doc.get("$schema") if isinstance(doc, dict) else None
        if not url:
            if "StaticResources" in rel.parts:
                continue  # theme files carry no $schema
            errors.append(f"{rel}: no $schema")
            continue
        schema_file = local_path(schema_root, url)
        if not schema_file.exists():
            errors.append(f"{rel}: schema not found locally: {url}")
            continue
        schema = json.loads(schema_file.read_text(encoding="utf-8"))
        schema.setdefault("$id", url)
        validator = Draft7Validator(schema, registry=registry)
        for err in sorted(validator.iter_errors(doc), key=lambda e: list(e.path)):
            where = "/".join(str(p) for p in err.absolute_path) or "(root)"
            errors.append(f"{rel}: {where}: {err.message[:200]}")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--schemas", default=os.environ.get("PBIP_SCHEMAS"),
                        help="local root of github.com/microsoft/json-schemas")
    parser.add_argument("--project", default=str(DASHBOARDS))
    args = parser.parse_args()
    if not args.schemas:
        print("validate_pbip: no schema folder given (--schemas or PBIP_SCHEMAS); skipped")
        return 0
    folder = Path(args.project)
    files = project_files(folder)
    errors = validate(folder, Path(args.schemas))
    for e in errors:
        print(e)
    print(f"validate_pbip: {len(files)} files, {len(errors)} errors")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
