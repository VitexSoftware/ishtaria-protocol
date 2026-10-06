# ishtaria-protocol

Federation protocol of Ishtaria worlds.

| File | Content |
|---|---|
| `schemas/federation-agreement.schema.json` | JSON Schema of a bilateral federation agreement |
| `schemas/travel-ticket.cddl` | CDDL of the signed (COSE_Sign1) travel ticket |
| `schemas/server-info.schema.json` | `/.well-known/ishtaria/server.json` (identity key, API URL, federation policy) |
| `schemas/portal-link.schema.json` | Payload of the share link of a finished portal |
| `schemas/portal-link-request.schema.json` | Signed request to link a portal, sent to the world named by a pasted link |
| `schemas/portal-unlink.schema.json` | Signed message that the owner of an end broke the link |
| `DATADISK-SPEC.md` | Specification of the story datadisk format (layout, languages, spoken lines, how to create a disk) |
| `schemas/datadisk.schema.json` | JSON Schema definitions for story datadisk files (manifest, places, NPCs, dialogue trees, quests, lore, strings) |
| `examples/` | Example agreements and messages |

```sh
python3 tests/validate_examples.py
python3 tests/validate_datadisk.py [--allow-draft] [DISK_DIR ...]   # schema + reference checks, several dirs = one composition
```

The prose specification is in the [documentation](https://vitexsoftware.github.io/ishtaria-docs/federation/index.html). Package `ishtaria-protocol` installs the schemas to `/usr/share/ishtaria/protocol/`.

License: MIT – independent implementations are welcome.

## Part of Ishtaria

Ishtaria is an open-source, persistent, federated virtual planet of Earth size.
Documentation: https://vitexsoftware.github.io/ishtaria-docs/ · All repositories: https://github.com/VitexSoftware?q=ishtaria
