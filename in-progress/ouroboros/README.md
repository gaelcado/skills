# Ouroboros

Fight entropy in agent-facing repository context. Ouroboros scores drift between Markdown instructions, docs, and skills and the local files they reference, then produces an explainable review queue.

> **Status:** In progress. The scoring model and workflow may change while the skill is being shaped.

![Ouroboros](assets/ouroboros.png)

## Install globally

Install Ouroboros globally to make it available in every repository. The installer detects supported agents and places the skill in the appropriate global directory:

```bash
npx skills add gaelcado/skills --full-depth --skill ouroboros -g
```

Requires Python 3.10+ and works best in a Git repository. Restart active agent sessions after installation so they discover the skill.

## Use it

Ouroboros does not activate automatically. Invoke it by name to audit context drift, establish a Markdown filename convention, or prepare a non-mutating repair plan. The exact invocation UI differs by agent.

Example requests:

- “Use Ouroboros to audit this repository's agent documentation.”
- “Establish kebab-case for agentic Markdown and show me violations.”
- “Plan repairs for stale context, but do not edit anything.”

## Workflows

### Triage context after code churn

Run a JSON audit after a large refactor or dependency change. Start with broken references, then inspect the highest-scoring source-to-target edges. Read both files and the relevant Git history before deciding whether a claim is stale; recency determines review order, not correctness.

The useful output is a short queue divided into: update now, intentionally unchanged, and needs domain-owner review.

### Review a pull request without timestamp theater

Restrict the audit with repeated `--doc` arguments to agent-facing files affected by the change. Treat broken local references as actionable failures. Treat entropy scores as prompts for semantic review, never as an automatic merge gate.

If code changed without its referenced guidance, verify the exact claims and request only the documentation edits supported by the diff.

### Establish a filename convention safely

Use `check` to detect the repository's existing plurality convention. If the project needs to make it explicit, confirm the desired case and run `init`. Use `plan` before renaming anything; approved renames should use Git-aware moves, repair inbound links, and finish with another audit.

### Pair with writing-for-agents

Use Ouroboros to locate likely drift, then apply [writing-for-agents](https://github.com/mattpocock/skills/blob/main/docs/productivity/writing-for-agents.md) to the selected documents: remove no-op prose, restore one source of truth, and replace duplicated detail with precise pointers. Rerun Ouroboros and record any high-scoring edges intentionally left unchanged.

Direct analyzer usage:

In these commands, `<skill-dir>` is the installed `ouroboros` directory containing `SKILL.md`.

```bash
python3 "<skill-dir>/scripts/ouroboros.py" check /path/to/repo
python3 "<skill-dir>/scripts/ouroboros.py" plan /path/to/repo
```

Scores are triage evidence, not proof that prose is semantically wrong. See [the scoring model](references/scoring.md) for the exact formula and limitations.
