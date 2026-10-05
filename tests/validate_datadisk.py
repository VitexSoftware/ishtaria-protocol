#!/usr/bin/env python3
"""Validate datadisk directories against schemas/datadisk.schema.json and check references.

Usage: validate_datadisk.py [--allow-draft] [DISK_DIR ...]
Without arguments the bundled examples are checked: examples/datadisk-*/ must pass and
examples/datadisk-invalid-*/ must each fail. Several directories are checked as one
composition (dependencies, conflicts, duplicate ids).
"""
import json
import pathlib
import re
import sys

import jsonschema
import yaml

root = pathlib.Path(__file__).resolve().parent.parent
schema = json.loads((root / "schemas/datadisk.schema.json").read_text())
SEMVER = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")


def definition(name):
    return jsonschema.Draft202012Validator(
        {"$schema": schema["$schema"], "$ref": f"#/$defs/{name}", "$defs": schema["$defs"]},
        format_checker=jsonschema.FormatChecker(),
    )


def semver(text):
    return tuple(int(part) for part in SEMVER.match(text).groups())


def load(path):
    return yaml.safe_load(path.read_text())


def conditions(node):
    """Yield every condition dict nested inside a condition."""
    yield node
    for key in ("all", "any"):
        for child in node.get(key, []):
            yield from conditions(child)
    if "not" in node:
        yield from conditions(node["not"])


def effects(items):
    for item in items or []:
        yield item
        if "once" in item:
            yield from effects(item["once"]["effects"])


def check_disk(disk_dir, allow_draft):
    """Return (errors, summary) for one disk directory."""
    errors = []

    def err(path, message):
        errors.append(f"{path.relative_to(disk_dir) if path != disk_dir else '.'}: {message}")

    def validate(name, path, document):
        found = sorted(definition(name).iter_errors(document), key=lambda e: list(e.path))
        for e in found:
            err(path, f"{'/'.join(map(str, e.path))}: {e.message}")
        return not found

    manifest_path = disk_dir / "datadisk.yaml"
    if not manifest_path.is_file():
        return [f"{disk_dir}: datadisk.yaml missing"], None
    manifest = load(manifest_path)
    if not validate("manifest", manifest_path, manifest):
        return errors, None
    languages = manifest.get("languages", ["en"])

    places, npcs, dialogues, quests, lore, music = {}, {}, {}, {}, {}, {}
    for kind, store, defn, listed in (
        ("places", places, "places", True),
        ("npcs", npcs, "npcs", True),
        ("lore", lore, "lore", True),
        ("music", music, "music", True),
        ("dialogues", dialogues, "dialogue", False),
        ("quests", quests, "quest", False),
    ):
        for path in sorted((disk_dir / kind).glob("*.yaml")):
            document = load(path)
            if not validate(defn, path, document):
                continue
            for entry in document if listed else [document]:
                if entry["id"] in store:
                    err(path, f"duplicate id {entry['id']}")
                store[entry["id"]] = entry

    strings = {}
    for language in languages:
        path = disk_dir / "i18n" / f"{language}.yaml"
        if not path.is_file():
            err(disk_dir, f"i18n/{language}.yaml missing")
            continue
        document = load(path) or {}
        if validate("strings", path, document):
            strings[language] = document

    used = set()

    def key(path, value):
        used.add(value)
        for language, table in strings.items():
            if value not in table:
                err(path, f"text key {value} missing in {language}")

    def local(ref):
        return ":" not in ref

    for place in places.values():
        key(disk_dir / "places", place["name_key"])
        for ref in [place.get("parent")] + [n["place"] for n in place.get("requires", {}).get("near", [])]:
            if ref and local(ref) and ref not in places:
                err(disk_dir / "places", f"{place['id']}: unknown place {ref}")
        # A place cannot be its own ancestor.
        seen, current = set(), place
        while current and current.get("parent") and local(current["parent"]):
            if current["parent"] in seen or current["parent"] == place["id"]:
                err(disk_dir / "places", f"{place['id']}: parent cycle")
                break
            seen.add(current["parent"])
            current = places.get(current["parent"])
    if sum(1 for place in places.values() if place.get("spawn")) > 1:
        err(disk_dir / "places", "at most one place may be the spawn point")
    for npc in npcs.values():
        path = disk_dir / "npcs"
        key(path, npc["name_key"])
        if "bio_key" in npc:
            key(path, npc["bio_key"])
        if local(npc["place"]) and npc["place"] not in places:
            err(path, f"{npc['id']}: unknown place {npc['place']}")
        if local(npc["dialogue"]) and npc["dialogue"] not in dialogues:
            err(path, f"{npc['id']}: unknown dialogue {npc['dialogue']}")
    media_limits = {"png": 1 << 20, "jpg": 1 << 20, "ogg": 8 << 20}

    def media(path, relative, kind):
        file = disk_dir / relative
        if not file.is_file():
            err(path, f"media file {relative} missing")
            return
        extension = relative.rsplit(".", 1)[1]
        if (kind == "portrait") != (extension in ("png", "jpg")):
            err(path, f"{relative}: wrong type for a {kind}")
        if file.stat().st_size > media_limits[extension]:
            err(path, f"{relative} is larger than {media_limits[extension]} bytes")

    for npc in npcs.values():
        if "portrait" in npc:
            media(disk_dir / "npcs", npc["portrait"], "portrait")
    for track in music.values():
        key(disk_dir / "music", track["title_key"])
        media(disk_dir / "music", track["file"], "music")
    for entry in lore.values():
        key(disk_dir / "lore", entry["title_key"])
        key(disk_dir / "lore", entry["text_key"])

    for quest in quests.values():
        path = disk_dir / "quests"
        key(path, quest["title_key"])
        if quest["start_stage"] not in quest["stages"]:
            err(path, f"{quest['id']}: unknown start_stage")
        for stage in quest["stages"].values():
            key(path, stage["text_key"])
            reach = stage.get("reach")
            if reach and reach["goto"] not in quest["stages"]:
                err(path, f"{quest['id']}: reach goes to unknown stage {reach['goto']}")
            if reach and local(reach["place"]) and reach["place"] not in places:
                err(path, f"{quest['id']}: reach names unknown place {reach['place']}")

    for dialogue in dialogues.values():
        path = disk_dir / "dialogues" / f"{dialogue['id']}.yaml"
        nodes = dialogue["nodes"]
        if "music" in dialogue and dialogue["music"] not in music:
            err(path, f"unknown music {dialogue['music']}")
        if dialogue.get("status") == "draft" and not allow_draft:
            err(path, "draft dialogue (review it or pass --allow-draft)")
        if dialogue["start"] not in nodes:
            err(path, "unknown start node")
        edges = {}
        for name, node in nodes.items():
            targets = []
            for choice in node.get("choices", []):
                key(path, choice["text_key"])
                if "goto" in choice:
                    targets.append(choice["goto"])
            for entry in node.get("branch", []):
                targets.append(entry["goto"])
            if "text_key" in node:
                key(path, node["text_key"])
            for target in targets:
                if target not in nodes:
                    err(path, f"node {name}: unknown goto {target}")
            if "branch" in node and "if" in node["branch"][-1]:
                err(path, f"node {name}: the last branch entry needs no condition (fallback)")
            edges[name] = [t for t in targets if t in nodes]
        reachable, todo = set(), [dialogue["start"]]
        while todo:
            current = todo.pop()
            if current in reachable or current not in nodes:
                continue
            reachable.add(current)
            todo.extend(edges[current])
        for name in sorted(set(nodes) - reachable):
            err(path, f"node {name} is unreachable")
        # Branch-only cycles would never show a node to the player.
        for name, node in nodes.items():
            if "branch" in node:
                seen, current = set(), name
                while current in nodes and "branch" in nodes[current]:
                    if current in seen:
                        err(path, f"node {name}: branch cycle")
                        break
                    seen.add(current)
                    current = nodes[current]["branch"][-1]["goto"]
        for node in nodes.values():
            blocks = [c.get("if") for c in node.get("choices", [])] + [b.get("if") for b in node.get("branch", [])]
            lists = [c.get("effects") for c in node.get("choices", [])] + [node.get("effects")]
            for block in blocks:
                for cond in conditions(block) if block else []:
                    if "quest_stage" in cond:
                        ref, stage = cond["quest_stage"]["quest"], cond["quest_stage"]["stage"]
                        if local(ref) and (ref not in quests or stage not in quests[ref]["stages"]):
                            err(path, f"unknown quest stage {ref}/{stage}")
            for item in lists:
                for effect in effects(item):
                    if "set_stage" in effect:
                        ref, stage = effect["set_stage"]["quest"], effect["set_stage"]["stage"]
                        if local(ref) and (ref not in quests or stage not in quests[ref]["stages"]):
                            err(path, f"unknown quest stage {ref}/{stage}")

    unused = {k for table in strings.values() for k in table} - used
    summary = {
        "id": manifest["id"], "manifest": manifest, "places": set(places), "unused": len(unused),
        "counts": f"{len(places)} places, {len(npcs)} npcs, {len(dialogues)} dialogues, {len(quests)} quests",
    }
    return errors, summary


def check_composition(summaries):
    errors, by_id = [], {}
    for summary in summaries:
        if summary["id"] in by_id:
            errors.append(f"duplicate disk id {summary['id']}")
        by_id[summary["id"]] = summary
    for summary in summaries:
        manifest = summary["manifest"]
        for dep in manifest.get("requires", []):
            other = by_id.get(dep["disk"])
            if other is None:
                errors.append(f"{summary['id']}: requires missing disk {dep['disk']}")
                continue
            have, need = semver(other["manifest"]["version"]), semver(dep["version"])
            if have[0] != need[0] or have < need:
                errors.append(f"{summary['id']}: needs {dep['disk']} >= {dep['version']} (same major)")
        for other in manifest.get("conflicts", []):
            if other in by_id:
                errors.append(f"{summary['id']}: conflicts with {other}")
    return errors


def run(dirs, allow_draft):
    summaries, errors = [], []
    for disk_dir in dirs:
        disk_errors, summary = check_disk(disk_dir, allow_draft)
        errors += [f"{disk_dir.name}/{e}" for e in disk_errors]
        if summary:
            summaries.append(summary)
    if not errors:
        errors += check_composition(summaries)
    return errors, summaries


def main(argv):
    allow_draft = "--allow-draft" in argv
    dirs = [pathlib.Path(a).resolve() for a in argv if not a.startswith("--")]
    if dirs:
        errors, summaries = run(dirs, allow_draft)
        for e in errors:
            print(e)
        for s in summaries:
            print(f"{s['id']}: {s['counts']}" + (" OK" if not errors else ""))
        return 1 if errors else 0
    failed = False
    examples = root / "examples"
    for disk_dir in sorted(examples.glob("datadisk-*/")):
        if disk_dir.name.startswith(("datadisk-invalid-", "datadisk-compose-")):
            continue
        errors, _ = run([disk_dir], False)
        failed |= bool(errors)
        print(f"{disk_dir.name}: {'FAIL' if errors else 'OK'}")
        for e in errors:
            print(f"  {e}")
    for disk_dir in sorted(examples.glob("datadisk-invalid-*/")):
        errors, _ = run([disk_dir], False)
        if errors:
            print(f"{disk_dir.name}: rejected as expected ({errors[0]})")
        else:
            failed = True
            print(f"{disk_dir.name}: FAIL, the invalid disk was accepted")
    composition = sorted(examples.glob("datadisk-compose-*/"))
    if composition:
        errors, _ = run(composition, False)
        failed |= bool(errors)
        print(f"composition of {len(composition)} disks: {'FAIL' if errors else 'OK'}")
        for e in errors:
            print(f"  {e}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
