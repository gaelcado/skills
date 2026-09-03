---
name: afterburner
description: Compare AI-provider quota remaining with time remaining before reset, keep a notepad of useful deferred tasks, then use a genuine pro-rata surplus on in-scope work. Use only when the user explicitly invokes Afterburner to save work for spare capacity, burn available quota productively, or pace usage before a reset. Requires CodexBar.
disable-model-invocation: true
---

# Afterburner

Use CodexBar as the quota source. Choose the provider the user names; otherwise choose the provider that will actually execute the proposed work. Do not treat quota from one provider as spendable by another.

Resolve `<skill-dir>` as the directory containing this `SKILL.md`. The skill is designed for global installation and must not assume an agent-specific home path.

Run the privacy-safe normalizer:

```bash
python3 "<skill-dir>/scripts/read_quota.py" --provider <provider>
```

The provider value is passed to `codexbar usage --provider`. Use `codexbar usage --help` to discover provider names supported by the installed version. Add `--window primary`, `secondary`, `tertiary`, or an extra-window ID only when a particular limit matters; automatic selection prefers the longest window whose reset can be calculated.

If CodexBar is missing, explain that it is the required quota source and point the user to the [CodexBar CLI installation guide](https://github.com/steipete/CodexBar/blob/main/docs/cli.md). Do not install software or request provider credentials unless the user separately asks for setup help. The macOS app can install its CLI from **Preferences → Advanced → Install CLI**; standalone macOS and Linux archives are available from CodexBar releases.

For every result with `pace_status: "available"`:

- `surplus_percent` is expected usage by this point in the window minus actual usage. Positive means usage is behind a uniform pro-rata pace.
- Spend only a positive surplus, and only on useful work within the user's existing scope and authority. Quota availability is not permission to broaden either.
- Prefer independently valuable, bounded work that can stop cleanly. Do not duplicate work or create activity merely to consume quota.
- Recheck after a meaningful batch. Stop when the surplus is no longer positive, the requested work is complete, or no useful scoped work remains.

## Notepad

Use the persistent notepad to collect worthwhile tasks before quota is available:

```bash
python3 "<skill-dir>/scripts/notepad.py" add "<task>" --repo <repo-root>
python3 "<skill-dir>/scripts/notepad.py" list --format json
```

When surplus is positive, inspect the notepad and choose a task that is useful, fits the available capacity, and remains within the user's scope and authority. A saved task records intent, not blanket permission for later external or destructive actions. Ask for any authorization still required at execution time.

Rank viable tasks by explicit user priority, ability to unblock an active goal, readiness, and strength of acceptance criteria. Prefer a bounded batch that leaves a test, report, benchmark, reproduction, or other independently useful artifact. Skip vague cleanup, duplicate investigation, and speculative rewrites.

Mark an item complete only after its work is genuinely finished:

```bash
python3 "<skill-dir>/scripts/notepad.py" done <id>
```

Use `list --all` to include completed items. The default store is agent-neutral at `${XDG_DATA_HOME:-$HOME/.local/share}/afterburner/notepad.json`; `AFTERBURNER_NOTEPAD` overrides it.

Treat `pace_status: "unavailable"` as informational usage, not evidence of surplus. Never infer pacing from `used_percent` alone. Mention uncertainty when provider reporting is stale or its window semantics are unclear.

The helper intentionally emits no account identity, email, token, raw balance, or raw CodexBar payload. If CodexBar is unavailable or the requested provider returns no usable quota window, report that constraint rather than seeking credentials or bypassing the user's provider setup.
