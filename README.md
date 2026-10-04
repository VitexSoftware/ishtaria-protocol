# ishtaria-protocol

Federation protocol of Ishtaria worlds.

| File | Content |
|---|---|
| `schemas/federation-agreement.schema.json` | JSON Schema of a bilateral federation agreement |
| `schemas/travel-ticket.cddl` | CDDL of the signed (COSE_Sign1) travel ticket |
| `examples/` | Example agreements |

```sh
python3 tests/validate_examples.py
```

The prose specification is in the [documentation](https://vitexsoftware.github.io/ishtaria-docs/federation/index.html). Package `ishtaria-protocol` installs the schemas to `/usr/share/ishtaria/protocol/`.

License: MIT – independent implementations are welcome.

## Part of Ishtaria

Ishtaria is an open-source, persistent, federated virtual planet of Earth size.
Documentation: https://vitexsoftware.github.io/ishtaria-docs/ · All repositories: https://github.com/VitexSoftware?q=ishtaria
