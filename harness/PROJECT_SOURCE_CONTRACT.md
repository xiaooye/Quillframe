# Project / Policy Source Contract · v1

The Agent Runtime does not assume the current book Canon is vendored into this repository.

A Harness manager resolves two external authority roles:

1. **policy source** — Story/Surface/Reader/Context/Settlement rules;
2. **project source** — Project Adapter, Novel Bible, Accepted/Canon/current state.

They may be the same checkout (as in current `frostloom`) or separate repositories later.

## Required project bootstrap handles

A project source must resolve:
- `PROJECT.md`
- `START_HERE.md`
- Context/Settlement protocol
- project profile/regressions for modes that require them
- authoritative current state / Canon objects selected by Context Manifest

A policy source must resolve the current Story/Surface/Reader modules required by the project bootstrap.

## Current 《从唐人街到白宫》 mapping

Repository: `xiaooye/frostloom` branch `master`.

When cloned locally as `<frostloom>`:

```text
project_root = <frostloom>/new cards/chinaboy_webnovel
policy_root  = <frostloom>/new cards/novel_production_os
```

Current required project files include:
- `novel_bible/PROJECT.md`
- `novel_bible/START_HERE.md`
- `novel_bible/shared/database/CONTEXT_AND_SETTLEMENT_PROTOCOL.md`
- `novel_bible/shared/PROSE_PROFILE.md` when required by DRAFT/REVISE.

## Authority snapshot

A run should record:
- source repo/branch when known;
- commit SHA or equivalent revision when available;
- resolved project/policy root;
- selected authoritative paths;
- Canon cutoff.

Session persistence never freezes authority forever. Resume must re-resolve current live source and decide whether the checkpoint is still compatible.

## No silent fallback

If required project/policy files cannot be resolved, return `context_fail` / source-resolution failure. Do not silently use an old copied prompt, chat memory or generated replacement.

## Future split

Story/Surface policy may later move to another dedicated repository. That is a separate migration with parity/eval gates. This runtime contract already permits it without changing session/Control Plane semantics.
