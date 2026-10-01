# REFUTE C2 r1 — STABILITY lens (2026-10-01)

**Verdict: REFUTED. C2 was never produced, so there is nothing that could pass GATE 2.**
Do not read this as a stability finding about any loop. It is a finding that **the design under test does not exist.**

## 1. What was handed to this refuter

The design payload for C2 is the synthesis agent's own halt notice:

- `primary.id = "none (halted)"`, `fallback.id = "none (halted)"`.
- `edits`, `cave` and `cals` are all "none produced". `bytes_total = 0`.
- `gate2 = "not scored"`, `time_gates = "not scored"`, `misses = "not produced"`.
- `design_doc = "not written (halted)"`, `files = []`.

## 2. Absence checked (EVIDENCE, method: directory listing at the time of this review)

| Expected artefact | State |
|---|---|
| `analysis-2020accord/studies/angle_loop/c2/` | **does not exist** (`ls`: No such file or directory) |
| `docs/specs/design/DESIGN-ANGLE-LOOP-C2-2026-10-01.md` | **does not exist** (no `C2` entry in `docs/specs/design/`) |
| `docs/specs/design/panel/score_time.py` | **does not exist** (the panel holds only `score_freq.py`) |

## 3. Lens results

None of the lens items can be evaluated. There is no edit set, no cave, no Kp/Ki/Kd schedule, no gain table and no declared miss or stop band, so there is no loop to model:

- Sweep at ≤ 0.25 m/s including the plant knots 3.1/8.0/11.9/17.0/26.9 m/s: **not run, no loop**.
- Hold ages 1–20 on every member: **not run**.
- Credible-set members, including b_q × {nominal, J_hi, J1.0, tau6}, b_lo × J_hi × tau6, and bc: **not run**.
- 20 Hz and two-mass stress plants, and the 5–30 Hz peak: **not run**.
- Re(T/ω) over 5–25 Hz against V294/V295, and 20 Hz gain against V295: **not run**.
- Fork outer-loop stand-in at τ_o 0.3/0.5/1 s: **not run**.
- Declared misses against a pre-registered stop band: **none declared, because nothing was designed**.

This refuter also built no independent model. An independent model needs a design to mirror. Building one around a guessed design would be fabrication, so it was not done.

## 4. Why this is returned as REFUTED and not "no finding"

The brief says: *"If you cannot verify a decision-bearing claim yourself, say which and return refuted = true."*
Every decision-bearing claim C2 would need is unverifiable because none exists: stability margins, member coverage, stop-band declarations and byte edits. The pass must be able to return "do not flash" (CLAUDE.md, adversarial-pass rule), and here that is the only answer it can give. **There is no C2 image or edit set to flash.**

## 5. For the orchestrator (BELIEF, not checked further — out of this refuter's scope)

- Panel candidates do exist on disk: `docs/specs/design/panel/DESIGN-PANEL-{A,B,C,D}-*.md`, `SCORE-FREQ-2026-10-01.md` and `JUDGE-bytes-risk-2026-10-01.md`. The halt notice reports the bytes-risk ranking as D2a 82 and B0r 81, a tie. **This refuter did not verify those scores.**
- If the workflow wants this lens run on the panel's leading candidates instead of on C2, re-issue the brief naming those designs (for example D2a and B0r) and their scripts. This lens should then also be run as a full independent sweep, with every combined member and hold ages 1–20 on each, as specified above. Do not take it from `SCORE-FREQ` on trust.
- The time-domain scorer (`panel/score_time.py`) does not exist, so no candidate has common time-gate scoring yet.

No firmware bytes were read, no Ghidra program was touched, no simulation was run, and nothing was built, flashed or sent.
