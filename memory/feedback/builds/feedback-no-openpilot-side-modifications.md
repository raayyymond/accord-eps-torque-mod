---
name: feedback-no-openpilot-side-modifications
description: "AMENDED 2026-09-10 -- openpilot-side changes ARE now allowed FOR THE GRINDING ISSUE ONLY, provided they do not limit the model's connection or steering authority (no LPF, no added lag, no slew clipping). The 2026-07-28 blanket ban is superseded. Everywhere else the EPS must still act faithfully on openpilot's commands."
metadata:
  node_type: memory
  type: feedback
---

🛑 **AMENDED BY THE OPERATOR, 2026-09-10. The 2026-07-28 blanket ban below is SUPERSEDED for the
grinding workstream.** Read the amendment first; the original is kept underneath as the record of why
the ban existed, because the reasoning still governs every other workstream.

## The current instruction (2026-09-10)

**Operator, verbatim:** *"I am fine with openpilot-side changes. That memory was only relevant to that
specific section. But in general, I think the EPS should act faithfully on the openpilot commands. Only
for the grinding issue, it's been so pervasive and after so much hard work on the EPS-side we still
can't seem to get rid of it. So I'm willing to accept openpilot changes if the model's connection /
steering authority is not limited (like by a LPF for example)."*

**What is now allowed — for the GRINDING issue only:**
- Fork-side changes are **in scope as fixes**, not only as measurement.
- ✅ **Allowed:** anything that removes 12–26 Hz content **without costing command authority or lag** —
  slope-continuous reconstruction of `desiredCurvature` between model frames (zero lag by slope
  extrapolation; **lag-NEGATIVE** if driven from the model's own published future trajectory),
  measurement-side filtering/notching (costs no command authority at all, since it is in the feedback
  path), quantiser dither / error-feedback noise shaping, fixing an aliasing fold.
- 🛑 **Still forbidden, and this is the binding constraint:** anything that **limits the model's
  connection or steering authority**. Named explicitly by the operator: **a low-pass filter on the
  command**. By extension: added command lag, clipped output slew, reduced `STEER_MAX`, or a lowered
  `STEER_DELTA_UP`. A colleague's fork fixes a *different* symptom this way (τ 0.10–0.28 s, costing
  100–280 ms of group delay and −32° to −59° at 1 Hz); **the operator has rejected that class by name.**
- **Scope is the grinding issue.** Outside it, the default stands: **the EPS should act faithfully on
  openpilot's commands**, and a fork-side change is not the way to fix an EPS defect.

**Why the change:** the grinding has survived ~60 EPS-side builds. The 2026-09-10 session then found
that the one experiment believed to have cleared the command path (V288 rev 2) was **transparent at the
ring's amplitude** and never tested it — see [[accord-v288-null-is-void-filter-was-transparent-at-the-ring]] —
and that a sustained 20 Hz forcing comb, locked to the camera clock, is present on the wire on every
build. That puts a real candidate mechanism on the openpilot side for the first time.

**How to apply:** for a grinding candidate, score fork-side and firmware-side levers side by side, and
state each one's **added lag in ms** and **authority cost** explicitly — those are the gates he will
judge it on. An openpilot-side fix also has a real advantage worth stating: **it needs no flash**, so it
carries none of this kit's bricking exposure. Do not resurrect fork-side levers for the ratcheting or
micro-ratcheting workstreams on the strength of this amendment.

Related: [[accord-lkas-commands-rate-not-torque]] · [[feedback-openpilot-means-starpilot-dom-branch]] ·
[[feedback-the-operator-runs-force-torque-controller-check-toggles-not-defaults]]

---

## SUPERSEDED — the original instruction, 2026-07-28 (kept as the record)

**Operator, 2026-07-28: "I do not want openpilot side modifications."**

Do not propose, build, or recommend fork-side changes as a fix -- no notch filters, no low-pass, no
`STEER_DELTA` / rate-limit retuning, no `steerActuatorDelay` changes, no lateral-controller edits. This
**retires the "openpilot-side 21 Hz notch"** that sat at #1 in `docs/STATE.md` across several handoffs.

**Why:** the operator wants the fix in the EPS firmware, where the defect is. A fork-side workaround masks
the symptom on one vehicle/software combination and does not advance the reverse engineering.

**How to apply:** when a fix candidate is fork-side, drop it and find the firmware-side lever instead.
openpilot remains fully in scope as a *measurement instrument* -- rlogs, CAN decode, correlation -- just
not as a place to change behaviour. Re-check `docs/STATE.md`'s next-steps list whenever a fork-side item
creeps back in.
