# Memory Constellation — Honda EPS Firmware Project

> **Layout note (reorg 2026-08-26).** The four index files stay at `memory/` top level; the
> notes themselves are nested: `accord/{builds,mechanism,firmware,instruments,calibration,signals}/`,
> `reference/{firmware,builds,measurement,tooling,can}/`,
> `feedback/{process,measurement,tooling,builds}/`, plus `project/`, `builds/`, `dream/`, `misc/`.
> Every link in the indexes carries the full relative path — follow it rather than guessing.


This directory is the **auto-memory system** for Claude Code on this project. It's Joey's actual working memory from the reverse engineering effort, preserved as-is so an agent picking up this work has the same context Joey's agents had.

## What this is

Claude Code persists project context across conversations by reading files from `~/.claude/projects/<project-slug>/memory/`. When a session starts on this project, Claude Code automatically loads `MEMORY.md` (the index) and reads referenced files when their content becomes relevant to the work at hand. This is how an agent on day 30 of a project knows what was decided on day 3 without you having to recap.

## How to make it active

The install script in the kit root handles this automatically — it copies this directory into the right `~/.claude/projects/...` location for your machine. If you'd rather wire it up by hand, copy this `memory/` directory (contents, not the folder itself) into:

```
~/.claude/projects/<your-slug-for-this-project>/memory/
```

On Windows that's typically `C:\Users\<you>\.claude\projects\<slug>\memory\`. The slug Claude Code uses for a given project is the absolute project path with separators replaced by `-` (e.g., `C--claudecode-firmware-analysis-kit`).

## Where to start reading

1. **`MEMORY.md`** — the index. One line per memory node, linked. Read first.
2. **`MEMORY_CONSTELLATION.md`** — the synapse map. Where MEMORY.md lists what's known, this shows how the known things relate: which nodes are load-bearing, which clusters depend on which, which edges are tentative vs. structural. The accompanying `MEMORY_CONSTELLATION.svg` is the visual.
3. **Individual node files** — read on demand as the constellation points you to them.
4. **`dream_2026-05-22.md`** — the late-session reflection that produced the most recent batch of memories. Useful for seeing how new nodes get crystallized from session work.

## The three memory types

- **`feedback_*`** — How Joey works. Collaboration rules he's surfaced through correction. (e.g., "operator lived experience overrides analyst recs", "rigorous validation before flash".)
- **`reference_*`** — Firmware facts. Things that are true about the EPS code, the Honda variants, the cipher, the people working on this. (e.g., "Civic has no raw-value CAN branch", "Aragon = brettpakkala = nrdr".)
- **`project_*`** — Project state. What's flashed, what's pending, what was superseded. (e.g., "PROPER flashed and validated 2026-05-22".)

Together they encode: who knows what, what's been validated, what's been ruled out, what's load-bearing. The constellation map makes the relationships explicit so an agent doesn't have to re-derive them.
