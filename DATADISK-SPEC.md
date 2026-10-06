# Ishtaria datadisk specification, format 1

A **datadisk** is a directory of data (no code) that adds a story to Ishtaria worlds: places, characters,
dialogue trees, quests, lore, music, portraits, spoken lines and translations. Several disks combine in one
world. The server evaluates a disk; clients only display what the server sends. The machine-readable source
of truth is [`schemas/datadisk.schema.json`](schemas/datadisk.schema.json); this document explains how the
parts fit and is normative where the schema cannot say it. Validate a disk with
`python3 tests/validate_datadisk.py DISK_DIR [DISK_DIR ...]` (several directories = one composition);
`examples/datadisk-minimal` is a small valid disk to copy.

## 1. Layout

```
datadisk.yaml          manifest
places/*.yaml          places (list)             -> $defs/places
npcs/*.yaml            characters (list)         -> $defs/npcs
dialogues/<id>.yaml    one decision tree each    -> $defs/dialogue
quests/<id>.yaml       one stage machine each    -> $defs/quest
lore/*.yaml            codex entries (list)      -> $defs/lore
music/*.yaml           tracks (list)             -> $defs/music
i18n/<language>.yaml   every text key, per language the disk declares -> $defs/strings
media/portraits/       PNG/JPEG (<= 1 MiB), named by an NPC's `portrait`
media/music/           OGG Vorbis (<= 8 MiB), named by a track's `file`
media/models/          glTF binary `.glb` (<= 4 MiB), named by an NPC's `character.model`; `pack`/`skin` stay the fallback
media/cover/           PNG/JPEG cover (<= 1 MiB), named by the manifest's `cover`
media/voice/<language>/<text_key>.ogg   spoken lines (<= 2 MiB each), see section 6
voice/voices.yaml      settings of the voice synthesizer (build tool only)  -> $defs/voices
```

Media paths are `media/...` of lowercase ASCII (`a-z 0-9 _ . -`); no traversal, no symlinks. Only files
that a manifest, NPC, track or dialogue node names are served.

## 2. Manifest (`datadisk.yaml`)

`id` (`[a-z][a-z0-9_]{1,31}`), `version` (semver), `name`, `requires_ruleset`, `license`, `attribution`;
optional `description`, `rating`, `cover`, `languages` (two-letter codes; default `en`), `requires`
(`{disk, version}` minimum version, same major), `conflicts`, and `format` (this specification; `1`
when absent). Every language listed needs `i18n/<language>.yaml` containing every key the disk uses.

## 3. Identifiers

Ids are local (`[a-z][a-z0-9_]*`); the loader qualifies them as `<disk>:<id>`. A reference to another disk
is allowed only for a disk named in `requires`. Text keys (`[a-z][a-z0-9_.]*`) are qualified the same way.
Content ids and the ruleset version are stable contracts: an incompatible change needs a new major version.

## 4. Content

* **Places** may be placed by constraints (biome, height, slope, distance to other places) and are persisted
  once; one place may be the `spawn` point; a child place of a walled town (`size: town`) may be pinned with `at: gate` or `at: alley`. **NPCs** stand at a place, choose a character model and name a
  dialogue. **Quests** are stage machines (`reach` stages advance when the player arrives). A quest may name a
  `start_place` and a stage a `guide` place; the server shows them as markers once the player holds the aetherglass.
* **Dialogues** are trees: a node shows a `text_key` with `choices`, or is a `branch` (automatic routing,
  last entry unconditional). Conditions (`flag`, `quest_stage`, `has_item`, `gold_at_least`, `all/any/not`)
  and effects (gold, items, flags, quest stages, `once`) are structured data, never scripts. The server applies
  effects in one transaction. `status: draft` content is refused by release builds.
* Only the NPC's lines (`text_key` of a node) are spoken; the player's choices are not.

## 4a. Placeholders

A text may contain `{player}`: the client replaces it with the name the player chose when creating the
character (`…` when unknown). Nothing else is substituted; the server never sees the replacement. A recorded line
cannot contain a name, so for the voice the placeholder is replaced by a form of address given in
`voice/voices.yaml` (`placeholders.player.<language>`), or the whole line is replaced by an i18n key
`<text_key>.say` that is only spoken, never shown. Human recordings are free to say anything.

## 5. Languages

The client names its interface language (two letters) in each dialogue request; the server sends text keys
and the spoken line **in that language**, and never stores the language. A language the disk does not
declare simply gets no spoken line; texts fall back to English on the client. Adding a language to a disk:
(1) `i18n/<language>.yaml`, (2) list it in `languages`, (3) a model for it in `voice/voices.yaml`,
(4) a build dependency on that voice model, (5) optionally recordings in `media/voice/<language>/`.

## 6. Spoken lines

A line is the file `media/voice/<language>/<text_key>.ogg` (OGG Vorbis, mono, any rate up to 48 kHz) for the
`text_key` of a dialogue node. A missing file means the node is silent; nothing else needs to be declared.

* **Synthetic voices** are produced while the package is built by `render_voices.py` (Piper + ffmpeg) using
  `voice/voices.yaml`: a Piper `model` per language, a `default` profile and a profile per NPC
  (`length_scale`, `noise_scale`, `noise_w`, `speaker`, `pitch` in semitones, `tempo`, `eq`, `echo`;
  an entry keyed by a language overrides the profile for that language). They are build output, not committed.
* **Human recordings** (a community dub, the author's own voice) are committed under `media/voice/` with
  the same file name. A key with a recording in the source tree is never synthesized, so a recording replaces
  a synthetic line by adding one file, without touching the engine or the profiles.

## 7. Packaging

A disk is installed to `/usr/share/ishtaria/datadisks/<id>/` (Debian package `ishtaria-datadisk-<id>`).
The server pins the content hash of each applied disk when it first loads it and refuses a changed disk.

## 8. Creating a new disk

1. Copy `examples/datadisk-minimal`; set a unique `id`, `license` and `attribution`.
2. Write places, NPCs, dialogues (a local LLM may draft them once, as `status: draft`; review before release),
   quests and `i18n/<language>.yaml` for every language.
3. Add portraits and music; add `voice/voices.yaml` to have the lines spoken.
4. Validate with `tests/validate_datadisk.py`, install the package, and tick the disk when generating a world.
