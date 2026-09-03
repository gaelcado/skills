---
name: ouroboros
description: Audit and repair entropy in repository instructions, skills, context files, and other agent-facing Markdown. Use only when the user explicitly invokes Ouroboros to inspect documentation drift, establish Markdown filename conventions, or review stale agent context.
disable-model-invocation: true
---

# Ouroboros

Keep the repository's agent-facing context aligned with what it describes. Measure drift first; treat the score as a review queue, not proof that prose is wrong.

Resolve `<skill-dir>` as the directory containing this `SKILL.md`. The skill is designed for global installation and must not assume an agent-specific home path.

## Audit

1. Locate the repository root. If it is not a Git repository, explain that history-based scoring is unavailable and perform a naming/reference review only.
2. Run:

   ```bash
   python3 "<skill-dir>/scripts/ouroboros.py" check <repo-root>
   ```

   Use `--format json` when another tool will consume the result. Pass `--doc PATH` one or more times to restrict an audit.
3. Review high-scoring edges first. Verify whether a changed target invalidates, extends, or leaves the source document unchanged. A new commit is evidence to inspect, never evidence to rewrite by itself.
4. Report the convention, overall score and scored-document count, critical/stale edges with point breakdowns, broken local references, case violations, and blind spots.

Read [references/scoring.md](references/scoring.md) when interpreting, tuning, or explaining the score.

## Establish a convention

Default to detecting the plurality convention among lowercase agentic Markdown filenames. Reserved uppercase entrypoints (`AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, `CODEX.md`, `CONTEXT.md`, `MEMORY.md`, and `SKILL.md`) are valid exceptions.

When the repository needs an explicit convention, run `init` only after confirming the desired case:

```bash
python3 "<skill-dir>/scripts/ouroboros.py" init <repo-root> --case kebab-case
```

This creates `.ouroboros.toml`; it never renames documents. Preserve an existing project convention unless the user asks to change it.

## Repair

Do not edit, rename, or delete user files merely because the audit reports entropy.

- Without an explicit repair request, run `plan` to produce non-mutating suggestions.
- With an explicit repair request, inspect each source and target, update only claims made stale by the target, and preserve intentional historical context.
- Use Git-aware moves for approved renames, then repair inbound links and verify them with another `check`.
- Apply the principles from `writing-for-agents` when it is installed or the user invokes it: prune no-op prose, keep a single source of truth, and put conditional detail behind precise pointers. Ouroboros does not require or duplicate that skill; it supplies drift evidence for its editing pass.

Finish by rerunning the audit. Describe score changes and any intentionally accepted high-scoring edges.

## Boundaries

- Never auto-edit documents or code.
- Do not claim semantic correctness from timestamps, commit counts, or a low score.
- Do not penalize external URLs; they are outside this local audit.
- Treat generated, vendored, dependency, build, and VCS directories as excluded unless the repository config deliberately includes them.
