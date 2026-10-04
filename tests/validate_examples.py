#!/usr/bin/env python3
"""Validate all example agreements against the JSON Schema."""
import datetime
import json
import pathlib
import sys

import jsonschema
import yaml

root = pathlib.Path(__file__).resolve().parent.parent
schema = json.loads((root / "schemas/federation-agreement.schema.json").read_text())
validator = jsonschema.Draft202012Validator(
    schema, format_checker=jsonschema.FormatChecker()
)


def normalise(node):
    """YAML parses bare dates into date objects; the schema expects strings."""
    if isinstance(node, dict):
        return {k: normalise(v) for k, v in node.items()}
    if isinstance(node, list):
        return [normalise(v) for v in node]
    if isinstance(node, datetime.date):
        return node.isoformat()
    return node


failed = False
for path in sorted((root / "examples").glob("agreement-*.yaml")):
    doc = normalise(yaml.safe_load(path.read_text()))
    errors = list(validator.iter_errors(doc))
    for e in errors:
        failed = True
        print(f"{path.name}: {'/'.join(map(str, e.path))}: {e.message}")
    if not errors:
        print(f"{path.name}: OK")
sys.exit(1 if failed else 0)
