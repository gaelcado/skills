# Scoring model

Ouroboros scores each resolvable local `source document -> referenced target` edge. It uses Git history so a checkout's filesystem timestamps do not normally create false drift.

## Edge score

The score is capped at 100:

| Signal | Points | Meaning |
| --- | ---: | --- |
| Target is missing | 100 | The local pointer is broken. |
| Target's latest commit is newer | 5 per complete 7 days, max 60 | Time since the source was last committed while the target continued changing. |
| Commits to target after source | 6 each, max 30 | Repeated opportunities for the source to drift. |
| Target is dirty while source is clean | 10 | Uncommitted target work has no corresponding source edit. |

For a directory reference, Git history covers that path and the dirty signal covers descendants. New/untracked documents are treated as current rather than assigned artificial age.

A document score is the mean of its edges. The repository score is the mean of all edges, so a large document cannot hide behind a small number of fresh documents.

Labels: `low` 0–14, `watch` 15–39, `stale` 40–69, and `critical` 70–100.

Naming violations and unreferenced documents are reported but do not alter entropy. This keeps the score about evidence of reference drift.

## What the score cannot know

- A target change may not affect the claim that points to it.
- A source can be wrong even when it is newer than every target.
- References produced by templates, code, aliases, or prose without recognizable paths may be missed.
- Git history can be incomplete after shallow clones, rebases, squashes, or path renames.
- External links require a separate link or source audit.

Use the score to order human or agent review. Read both ends of an edge before changing either.

## Configuration

An optional `.ouroboros.toml` can pin the filename convention and extend discovery:

```toml
[conventions]
markdown_case = "kebab-case"

[discovery]
include = ["architecture/**/*.md"]
exclude = ["docs/archive/**"]
```

Supported cases are `kebab-case`, `snake_case`, and `camelCase`. Include patterns add agentic documents; excludes apply after discovery. Command-line `--doc` values override discovery.
