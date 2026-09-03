# Afterburner

Turn genuine quota surplus into useful work. Afterburner reads provider limits through CodexBar, compares remaining quota with time before reset, and keeps a persistent notepad of tasks worth doing when capacity is available.

![A GPU rack fused with a jet afterburner](assets/afterburner.jpg)

## CodexBar is required

Afterburner does not query provider accounts itself. It relies on the [CodexBar CLI](https://github.com/steipete/CodexBar/blob/main/docs/cli.md) to fetch quota windows and normalizes that output without exposing account identities, credentials, balances, or the raw payload.

Check whether the CLI is ready:

```bash
codexbar --version
codexbar usage --provider codex --format json
```

If `codexbar` is missing:

- **macOS app:** install [CodexBar](https://github.com/steipete/CodexBar), open **Preferences → Advanced**, and choose **Install CLI**. Homebrew users can install the app with `brew install --cask steipete/tap/codexbar`. Afterburner also recognizes the CLI bundled in a standard `/Applications/CodexBar.app` installation.
- **Standalone macOS or Linux CLI:** use the platform archive from [CodexBar releases](https://github.com/steipete/CodexBar/releases). Homebrew on Linux also supports `brew install steipete/tap/codexbar`.

Enable and authenticate the provider through CodexBar before invoking Afterburner. Afterburner will report a missing or unusable provider rather than requesting credentials.

## Install globally

Install Afterburner globally to make it available across projects. The installer detects supported agents and places the skill in the appropriate global directory:

```bash
npx skills add gaelcado/skills --skill afterburner -g
```

Requires Python 3.10+. Restart active agent sessions after installation so they discover the skill.

## Use it

Afterburner does not activate automatically. Invoke it by name to check quota, spend an available surplus, or save work for later. The exact invocation UI differs by agent.

Example requests:

- “Add a deep dependency audit to my Afterburner notepad for this repository.”
- “/goal (/loop) Use my Afterburner notepad while there is surplus, then stop at pace.”

## Workflows

### Capture now, burn later

Queue work with a repository and concrete completion notes while the need is fresh. Prefer tasks that remain useful if picked up cold: map test gaps for one subsystem, investigate a recurring failure, benchmark a known bottleneck, or audit a dependency boundary. Avoid vague entries such as “improve the codebase.”

When quota is available, Afterburner reads the queue as JSON, chooses a ready task whose effort fits the surplus, completes one verifiable batch, marks it done only after validation, and checks quota again.

### Prepare a deep maintenance run

Use the notepad to stage a sequence with independent outcomes, for example:

1. Characterize an intermittent test and preserve a reproduction.
2. Compare plausible root causes against logs and code history.
3. Implement the narrowest supported fix.
4. Run the relevant test matrix and record remaining uncertainty.

Afterburner should stop at any blocked step rather than spending quota on speculative rewrites.

### Route work to the right provider

Check the quota of the provider that will actually execute the task. A surplus from one provider is not capacity on another. When several queued tasks are viable, prefer explicit user priority, work that unblocks an active goal, and tasks with observable acceptance criteria.

### Use a no-surplus session well

Do not execute queued work merely to create activity. A no-surplus pass can still improve the notepad by splitting oversized entries, adding missing reproduction steps, or removing tasks that are no longer valuable.

The notepad is stored at `${XDG_DATA_HOME:-$HOME/.local/share}/afterburner/notepad.json` by default. Set `AFTERBURNER_NOTEPAD` to choose another location.

In the commands below, `<skill-dir>` is the installed `afterburner` directory containing `SKILL.md`.

```bash
python3 "<skill-dir>/scripts/notepad.py" add "Audit dependency boundaries" --repo /path/to/repo
python3 "<skill-dir>/scripts/notepad.py" list
python3 "<skill-dir>/scripts/notepad.py" done 1
```

Afterburner never treats spare quota or a queued task as permission to broaden scope or bypass approvals.
