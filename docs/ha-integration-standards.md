# Home Assistant integration standards

<!-- Managed by ha-integration-standards. Do not edit: `ha-standards sync`
     rewrites this file. Project-specific guidance belongs in CLAUDE.md, which
     imports this one. -->

The ground rules for developing this integration. Every one of them exists
because the obvious approach fails silently, so read the reason, not just the
code it produces.

## Language

Everything that ends up in the repository is **English**: code, comments,
docstrings, documentation, commit messages, PR titles and bodies. Commits
follow [Conventional Commits](https://www.conventionalcommits.org/) — a
release tool derives the version and the changelog from them, and the
changelog is published.

Only the chat reply to the user is German.

The `commit-message` gate rejects a message that misses its type or reads as
German.

## The quality tier is held, not claimed

`custom_components/vallox_rs485/quality_scale.yaml` is a promise. The
`quality-scale` gate checks the part of it a machine can check and fails the
commit when the code has drifted below the claim. Rules that need a human are
listed in the package's `NOT_CHECKABLE`, so the gap between *checked* and
*claimed* stays visible; a rule that only this project cannot prove goes under
`unenforceable` in `[tool.ha_standards]`.

Marking a rule `done` without a check is only acceptable when the rule is
genuinely a judgement call. Otherwise: write the check, in the standards
package, where every integration gets it.

**`manifest.json` must declare `"quality_scale": "custom"`.** Home Assistant
reports `custom` for every integration outside core (`loader.py`,
`Integration.quality_scale`), whatever the manifest says. A core tier there is
a claim the runtime never repeats. The tier actually met is recorded in
`quality_scale.yaml`.

## Patterns the scale enforces

- **`entry.runtime_data`, never `hass.data[DOMAIN]`**, with a typed alias:
  `type MyConfigEntry = ConfigEntry[MyCoordinator]`.
- **`PARALLEL_UPDATES` in every platform module.** Absent means unbounded.
- **`_attr_has_entity_name = True`** on the base entity, plus
  `_attr_unique_id` and `_attr_translation_key`. The unique id is derived from
  something stable — an address, a serial — never from the name.
- **No `icon="mdi:…"` on an EntityDescription.** It bypasses `icons.json` and
  the user cannot theme it. Icons live in `icons.json`, keyed by translation
  key.
- **Every user-visible string in `strings.json`**, including `exceptions`.
  Raising with a `translation_key` that has no entry there is a silent English
  leak. Every shipped `translations/<lang>.json` carries every key
  `strings.json` has.
- **`ConfigEntryNotReady` in `async_setup_entry`** when the device is not
  reachable yet — not a swallowed error, not a retry loop of your own. Home
  Assistant retries with backoff and tells the user why.
- **`async_unload_entry`** forwarding to `async_unload_platforms`, and
  `entry.async_on_unload(...)` for everything started during setup.
- **`diagnostics.py` redacts.** Addresses, serial numbers, PINs and tokens
  never leave the device: a diagnostics file ends up in public issue trackers.
- **Start the coordinator last.** Forward the platforms first so every entity
  has subscribed, then start polling. The other order loses the first update.

## The brand icon

Every integration ships its own icon, and every icon looks like it came from
the same place. That recognisability is the point: a user scrolling a list of
integrations should be able to tell which ones are ours without reading a
name.

**The icon lives in the integration, not in a pull request.** Since Home
Assistant 2026.3 a custom integration carries its brand images itself:

```
custom_components/<domain>/brand/
├── icon.png       # 256x256
└── icon@2x.png    # 512x512
```

No manifest key, no configuration. Local images take precedence over the
brands CDN, and `custom_integrations/` in home-assistant/brands is marked
legacy for exactly this reason. Opening a PR there is only right when the
integration is on its way into core - and then the local images come out
again.

Two traps:

- **`hacs.json` has to require 2026.3 or newer.** An older floor means the
  icons ship and are never served. The `quality-scale` gate fails on the
  mismatch.
- **A 200 from `brands.home-assistant.io/_/<domain>/icon.png` proves
  nothing.** That endpoint generates a letter placeholder for any domain it
  has never heard of. The path without `_/` is the one that returns 404.

### What the icons have in common

- A flat ground in the house colour, edge to edge - no gradient, no border,
  no transparent margin. It is the single strongest signal that two icons
  belong together, and it is why the gate reads the corner pixels.
- The subject in white, the medium in `#9FE2FC`: air, water, radio, a bus.
  Every icon shows the device *and* the channel Home Assistant talks to it
  over. That is the thematic bracket, and it costs no space.
- Cutouts in the ground colour rather than an outline style.
- Round caps and joins throughout; generous corner radii on tiles and
  housings.
- A slight top-down view. A cylinder gets an ellipse of roughly 0.3 axis
  ratio - at the top **and** at the bottom. A straight edge under an
  elliptical cap is the one mistake that is visible at any size.
- A 512 viewBox, the subject centred by measurement rather than by eye.

The ground colour is `#0A7EE8` unless a project says otherwise:

```toml
[tool.ha_standards]
brand_color = "#0A7EE8"   # "" turns the colour check off, sizes still apply
```

### Draw it as a vector, ship it as PNG

The PNG is a build product; the source is an SVG. Keeping it the other way
round means every later change is a repaint. The gate reads the ground colour
straight out of the file, so the PNG has to be **8-bit and not interlaced** -
which is what any normal SVG renderer produces, and the reason the gate can
check the house style at all instead of taking it on trust.

## Tests run in Docker, against the targeted Home Assistant

`python3 scripts/_ha_standards/run.py tests` builds `Dockerfile.test` and runs
pytest inside it. This is not ceremony:

- Home Assistant needs **Python 3.14.2 from 2026.3 onwards**. Most systems do
  not have it, and testing on an older interpreter means testing an API that
  is not the one users run.
- The source is mounted **read-only**, the container runs as the calling user
  and with `--network none`. A test run cannot leave anything in the working
  tree or reach the internet. Everything it produces lands in `.artefakte/`.

`pytest-homeassistant-custom-component` installs Home Assistant but **not the
requirements of the components it pulls in** (bluetooth, usb, …). Do not pin
those by hand — they drift from the release being tested and a dependency bot
will keep proposing bumps that must never be taken on their own.
`scripts/ha_test_requirements.py` reads them out of the installed release
instead, using the dependencies this integration's own manifest declares.

Coverage: `pytest` fails below the overall floor, and the `coverage` gate adds
the per-module floors a single number hides — a config flow at 88% still passes a
95% average, and the Bronze rule asks for all of it. The floors live in
`[tool.ha_standards.coverage]`.

## Release

Conventional Commits → release-please opens a release PR → merging it tags,
writes `CHANGELOG.md` and raises the version in `manifest.json`.

Two traps:

- **A tag created by release-please starts no workflow.** Tags pushed with the
  `GITHUB_TOKEN` deliberately do not trigger `on: push: tags`. Anything that
  must happen on release belongs in the *same* workflow, gated on
  `needs.release-please.outputs.releases_created`.
- **Versions that must move together belong in `extra-files`.** If the
  integration pins a library that lives in this repository, release-please
  raises the pin in `manifest.json` and the version in `lib/` in one commit.
  Renovate must be told to leave that package alone, or its PR races the
  release commit. The `quality-scale` gate fails when the two drift apart.

PyPI publishing uses **Trusted Publishing** — no token is stored anywhere; the
trust is configured once on pypi.org for that workflow.

## The branch protection names the checks

A required status check is a **name**, not a reference to a workflow. Rename a
job, split a workflow, or adopt this package and drop the one the repository
started with, and the protection waits for a context nobody reports any more.
GitHub shows that as *"Expected — Waiting for status to be reported"* with no
job behind it, and nothing can be merged: the checks that do run are green and
irrelevant, because they are not the ones named.

So the names are never written down twice:

```bash
ha-standards protect            # --dry-run prints them, changes nothing
```

It reads every job of every workflow that runs on a pull request and requires
exactly those on the default branch, with `strict` set so a branch catches up
with the base before it merges. Run it after adopting this package, and again
whenever a job is added or renamed.

**A new repository is unprotected until this runs.** Nothing else sets the
protection up, and nothing complains while it is missing: `main` accepts a
direct push, a force-push, a deletion. So `ha-standards protect` belongs to
creating the repository, straight after the first push of `main`, as much as
`git init` does. The same run also sets up what every integration here needs
around the checks:

- a **ruleset** on the default branch: pull requests only, no force-push, no
  deletion, the same checks. No approval is required and administrators may
  bypass it — one maintainer has nobody to wait for;
- **workflow permissions** that let release-please open its release pull
  request, which GitHub otherwise refuses;
- where `lib/` builds a package, the **`pypi` environment** its publishing job
  runs in, limited to the default branch and to `v*` tags.

Each step reads what is there and writes what is wanted, so running it again
is always safe.

Matrix jobs are left out. They report one context per combination, with the
values in brackets (`test (3.13)`), and guessing that spelling wrongly is the
exact failure the command exists to fix. A job that must be required and is a
matrix has to be named by hand.

## Bluetooth

Applies to an integration that talks BLE; ignore it otherwise.

- The device is reachable only while it advertises. Say so with
  `bluetooth.async_set_fallback_availability_interval`, or Home Assistant
  declares the device dead long before it is.
- Connect through `bleak_retry_connector.establish_connection`, never
  `BleakClient` directly. It handles the retries, the transient `BleakError`s
  and the adapter quirks you would otherwise rediscover one by one.
- **Active scan is mandatory if you need the device name** — it sits in the
  scan response, not in the advertisement.
- Check `async_scanner_count` and `async_address_present` before setup and
  fail with `ConfigEntryNotReady`; both produce a far better message than a
  connection timeout.
- Poll rarely. A battery device that advertises every few minutes gains
  nothing from a shorter interval and loses battery and connect windows.
- **Range is an antenna problem, not a code problem.** ESP32 boards with a PCB
  antenna measured -86 dBm where a board with an external antenna in the same
  spot measured -36 dBm. For a proxy, take a board with a u.FL socket and
  check that the solder jumper points at the socket rather than at the PCB
  trace.

## Reverse engineering a device protocol

- The wire format lives in **its own published package** under `lib/`, not
  inside the integration. The quality scale calls this *dependency
  transparency*: a user can read and audit what talks to their device.
- `docs/protocol.md` records **how each byte offset was established** — a real
  device, the vendor app, a capture. Changing the format and not the document
  makes the next person start over.
- **Vendor binaries stay out of the repository.** `reference/` and `*.apk` are
  in `.gitignore`; the write-up is ours, the material it came from is not.
- **Destructive commands are left out on purpose.** A factory reset byte that
  is known and deliberately absent needs a comment saying so, or someone will
  helpfully add it back.

## Before a commit

`pre-commit` runs ruff, `mypy --strict`, the full suite in Docker, the quality
gate and the coverage gate. Install it once:

```bash
python3 -m venv .venv && .venv/bin/pip install pre-commit && .venv/bin/pre-commit install
```

Never `--no-verify`.

The gates under `scripts/_ha_standards/` are **written by
ha-integration-standards, not maintained here**. They are vendored rather than
fetched because this repository is public and its CI runs on GitHub: a hook
that cloned a private tool would need a secret, and a pull request from a fork
never gets one.

So do not edit them. `run.py verify` hashes each file and runs before the
other gates, precisely so that "make the check pass" cannot mean "change the
check". If a rule is wrong, fix it in the standards repository and run:

```bash
ha-standards sync     # rewrites the gates and the files it manages
git diff              # the rules that changed, before they are in force
```

The same command updates this document, `Dockerfile.test`,
`scripts/ha_test_requirements.py` and `.github/workflows/quality.yml`.

## Deploying to a real installation

`./deploy.sh` mirrors `custom_components/vallox_rs485/` onto the Home Assistant
host over SSH, using `SERVER` and `HA_CONFIG` from `.env` (template:
`.env.example`). It is a development shortcut — users install through HACS.
Home Assistant has to be restarted afterwards; do that only when asked.
