---
name: feedback-read-the-repo-memory-not-the-stale-snapshot
description: A stale copy of memory/ lives in the Claude auto-memory directory and is what gets auto-loaded into a session — a subagent grounded on it reproduced six corrections' worth of retracted conclusions. Prime every subagent to read the REPO's memory/.
metadata:
  type: feedback
---

🛑 **THERE ARE TWO `memory/` DIRECTORIES, AND THE ONE THAT AUTO-LOADS IS THE STALE ONE.**

| path | status |
|---|---|
| `C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\memory\` | **THE REPO'S — authoritative, current, git-tracked** |
| `C:\Users\dudei\.claude\projects\C--Users-dudei-Desktop-Projects-accord-eps-torque-mod\memory\` | **a SNAPSHOT — stale, and it is what gets auto-loaded into a session's context** |

**Why:** the snapshot is a point-in-time copy (the `README.md` install step). Corrections written into the
repo's `memory/` **do not propagate to it**, so the auto-loaded index can assert things the repo retracted
sessions ago.

## What it cost, 2026-08-08

A subagent grounded itself on the snapshot and **reproduced six corrections' worth of stale conclusions
before catching it**:
- the **r26-kill attribution** for V42,
- the **state-4-vacuous** finding,
- the **two-ratchets** terminology,
- the **sampled-relay** characterisation of the damper,
- the **Q ≈ 14** revision,
- the **dose–response fit** that has since been retracted.

Every one of those is corrected in the repo's `memory/` and wrong in the snapshot.

⚠ **The divergence runs BOTH WAYS — it is not simply "the snapshot is a subset."** Some memories exist
**only in the snapshot** and have never been ported to the repo: confirmed 2026-08-08 for
`accord-rate-lane-builds-were-never-single-variable`, `accord-v850-scan-traps-formatv-and-storezero`,
`eps-deliver-cut-gp6809-broken`, `gentle-eme-fires-on-saturated-lkas-command` and
`reference-accord-fun45a20-monitor-and-shadow-lockstep-pairs` — all of which are `[[wikilinked]]` from
repo files and resolve to nothing there. ⇒ **A dangling wikilink in the repo is usually a memory that
lives only in the snapshot, not a memory that was never written.** Check the snapshot before concluding
a fact is unrecorded, and port it into the repo when you find it.

## How to apply

- **Prime EVERY subagent with the absolute path to the REPO's `memory/`**, the same way they are primed
  with `gp=0xFEDF8000` / `tp=0xBF000` / GhidraMCP-only. A brief that says "read the memories" gets the
  stale ones.
- **Write corrections to the repo's `memory/`.** If a correction must also stop misleading the
  auto-loaded context, patch the snapshot copy **as well** — but the repo is the source of truth.
- Treat anything arriving in a `<system-reminder>` memory block as **possibly pre-correction**, and
  check the repo file of the same name before acting on it.

Related: [[feedback_ground_sessions_in_golden_model_and_post_v38_arc]] ·
[[accord-check-build-lineage-before-proposing-lever]] ·
[[feedback-verify-the-crux-yourself-it-caught-four-errors]] ·
[[accord-a-caveat-can-mutate-into-a-result]]
