# Device libraries

The wire protocol belongs here, as a package of its own that is published to
PyPI and pinned in `custom_components/vallox_rs485/manifest.json` with `==`.
That is the quality scale's *dependency transparency* rule: a user can read
and audit what talks to their device, and can install it without installing
Home Assistant.

A package here looks like:

```
lib/vallox_rs485_protocol/
  pyproject.toml            name = "vallox-rs485-protocol"
  README.md
  src/vallox_rs485_protocol/
    __init__.py             re-exports the public names
    protocol.py             the only place that knows the wire format
    py.typed
  tests/test_protocol.py    its own tests, run by their own CI job
```

Two things then have to move together, and release-please is told to do it in
one commit: the `version` in that `pyproject.toml`, and the `==` pin in
`manifest.json`. `ha-quality-scale` fails when they drift apart. Add both to
`extra-files` in `release-please-config.json`, and switch the package off in
`renovate.json` so its PR does not race the release commit.
