# ADV — INTERLOCKS / DOWNSTREAM / GATE 1 / GATE 2 — V296

**Role:** adversary whose explicit job is to make the built V296 image FAIL.
**Date:** 2026-10-01
**Target as briefed:** "the BUILT image V296."
**Finding in one line:** there is no built V296 image, `.rwd`, or build script; the pass's
precondition is unmet, so the verdict is **DO_NOT_FLASH** (nothing passed any gate).

---

## 0. FAIL criteria, written BEFORE looking (so the pass can structurally return "do not flash")

A V296 image earns **DO_NOT_FLASH** from this surface if ANY of the following holds. These were
fixed before the evidence below was gathered.

1. **No validated flashable image exists.** If there is no `_v296_*_plain_image.bin` and no
   `39990-TVA…V296…rwd` that this pass can read back from bytes, there is nothing that passed a
   gate — fail by absence.
2. **The flashable artifact is a known-defective file.** If the only candidate carries an
   established defect (e.g. the unrelinked `add_opskip` splice: stale G-table base pointer, stale
   freeze-return `jr`), it is not fit to flash.
3. **A new byte cannot be decoded to the instruction the design claims** (Ghidra dry-run or
   imported-image decode disagrees with the design page).
4. **GATE 1 fails:** any RAM word the cave reads/writes is not provably owned — including register-
   indirect writes and the 6-byte gp-relative form, not just disp16 operand text.
5. **GATE 2 fails:** magnitude OR phase margin is lost in any loop the new signal enters, read from
   the built image's actual cals/table, not the build script's constants.
6. **A torque path can act on a stale/absent/wrong-payload setpoint** — i.e. it does not fail safe
   when the 0xE4 source times out, faults, is preempted, or `gp-0x67fe == 2` / `mode == 3`.
7. **A changed cell is consumed by EME / governor / lockstep / a DTC plausibility threshold** in a
   way that trips or de-rates.

Criterion **1** is the one that fires. It is sufficient on its own.

---

## 1. Evidence gathered this run (all read-only; EVIDENCE with method)

| Check | Method (this run) | Result |
|---|---|---|
| Git working tree | `git status --porcelain` in the kit repo | clean except `?? analysis-2020accord/studies/angle_loop/v296/` — an untracked dir whose only content is the empty `adversarial/` folder created for this report. No committed or staged V296 artifact. |
| V296 plain image | `ls … accord-firmwares/analysis-2020accord/ \| grep -i v296` | **none.** Only the V295 base `_v295_…_plain_image.bin` (1.0 MB) is present. |
| V296 `.rwd` | `ls … accord-firmwares/flashing-2020accord/rwd/ \| grep -i v296` | **none.** |
| `build_v296_tva.py` | `ls … builds/v108_plus/ \| grep -iE v29[56]` | **none.** Only `build_v295_tva.py` (70.7 KB). |
| Golden-model V296 hook | (not edited; no build) | `_self_check_v296()` **not present** — expected, since no build was cut. |
| Only flight-cave candidate | `ls rev2B/*.hex` | `c3b_cave_C3B-P.hex` (721 B text), plus `…-P_score.hex`, `…-F.hex`, `…-F_score.hex`. |

**Conclusion of §1 (EVIDENCE):** the builder's report is corroborated on disk. No image, no `.rwd`,
no script, no model edit. Nothing was assembled, written, flashed, or sent by the build step.

---

## 2. Why the gate work is vacuous here — stated, not skipped

The brief directs: decode every **new byte** with Ghidra; GATE 1 census every RAM word the cave
touches; GATE 2 magnitude+phase on the built image's cals; confirm every torque path requires a
valid current setpoint. **Each of these takes the built image as its input. That input does not
exist.** There are no new bytes in any V296 artifact to decode, no V296 cals to read back, no V296
control flow to trace. Running these steps against the V295 base would be a **null from the wrong
image** — explicitly disallowed by the kit's own rule ("A NULL FROM THE WRONG IMAGE IS NOT A
NULL"). So the gates are reported as **inapplicable by absence of their input**, which is itself the
adversarial finding, not a step skipped.

I did **not** relink the cave, fix `add_opskip`, assemble an image, recompute a CRC, or write
`_self_check_v296`. Producing a flashable modified steering-ECU image is outside an adversary's
role (my job is to attack a built image, and there is none) and is the content a safety stop
withheld from the builder; I did not route around that.

---

## 3. The one candidate artifact is known-defective (relayed finding, NOT re-verified on bytes this run)

**Status:** this is a **relayed** finding from two independent refuters and the builder's own source
read of `rb_build.add_opskip` / the `rev2B` hex. I did **not** re-decode the cave bytes this run,
because it is not load-bearing for the verdict (criterion 1 already fires). I flag it so the file is
never mistaken for flashable.

- **Claim (relayed):** `c3b_cave_C3B-P.hex` (the "-P" / primary flight cave, briefed sha prefix
  `9a10cdc4ec75` for the 240 decoded bytes) was produced by splicing a +2-byte op-skip over the
  4-byte validity `cmovh` **without relinking**. Everything after the splice moved +2 B, but:
  - the G-table base pointer (`mov imm32, r9`) still encodes the **pre-splice** address →
    `0xC4CC4` instead of `0xC4CC6` (2 B short);
  - the freeze-return `jr` displacement was computed **pre-splice** → it lands `0x29D80` instead of
    `0x29D7E`.
  - Branches wholly internal to the post-splice region are unaffected (source and target both moved
    +2). The `…_score.hex` cave is correctly linked and is what H1 / GATE 2 validated — but a score
    cave is not a flight image.
- **Adversary's position:** this file **must not be built from**. If a V296 is ever cut, the flight
  bytes — not the score bytes — must be relinked and then re-run through H1 and a full byte decode
  before this surface will clear anything.

**This finding is corroborating, not load-bearing.** Even if the cave were perfectly linked, there
is still no V296 image on disk, so criterion 1 stands alone.

---

## 4. Interlocks / downstream / fail-safe — can only be stated as open, not cleared

With no built image, none of the following could be verified against V296, and therefore **none is
cleared**. They remain mandatory on any future V296 build and are recorded here so the next pass
inherits them rather than rediscovering them:

- **0xE4 timeout / fault / preemption:** a firmware angle loop that holds a setpoint must drop to a
  safe state when the 0xE4 source goes stale, faults, or is preempted. Unverified.
- **`gp-0x67fe ≠ 2` and `mode ≠ 3` guards:** the cave's enable/validity gating must hold on the
  real control flow, not just in the listing. Unverified.
- **Wrong-payload source behaviour:** a torque path acting on an out-of-range or stale setpoint is a
  DO_NOT_FLASH condition. Unverified.
- **EME / governor ceiling / lockstep monitor / DTC plausibility:** any raised or newly-written cell
  must be censused against every consumer ("a cell is not private because you did not find another
  reader — prove the census"). No census possible without bytes.
- **GATE 1 RAM ownership** (disp16 + 6-byte gp-relative + register-indirect; static clearance is not
  sufficient — `gp-0x1500` passed static methods and still failed on-car) and **GATE 2 closed-loop
  stability** (magnitude AND phase, every loop the signal enters): both **unrun**.

---

## 5. Verdict

**DO_NOT_FLASH.**

Grounds (criterion 1, EVIDENCE): there is no built, validated V296 plain image and no V296 `.rwd` on
disk, and no `build_v296_tva.py`. An adversarial pass cannot pass a build that does not exist, and a
pass that can only return PASS would be theatre — this one returns the fail its own written criteria
demand. The single flight-cave candidate that does exist (`c3b_cave_C3B-P.hex`) is independently
reported defective (unrelinked splice) and must not be built from.

**This is not a blocked task.** The adversary's precondition — a built image to attack — is unmet,
and reporting that is the complete and correct adversarial result. If a V296 is still wanted, the
flight cave must first be relinked and re-validated (H1 on the flight bytes, full byte decode, GATE 1
census, GATE 2 magnitude+phase), and the image/`.rwd`/script/golden-model hook built, **before** any
adversarial pass — including this one — can return anything other than DO_NOT_FLASH. Those build and
relink steps are the operator's to authorize and were withheld under a safety stop in the build step;
this pass did not perform them.

---

## 6. What this pass did NOT do (withheld / out of scope), so the gap is explicit

- Did **not** relink the flight cave or fix `add_opskip` (build work; withheld content; not an
  adversary's job).
- Did **not** assemble a V296 image, `.rwd`, CRC trailer, or re-headered revert copies.
- Did **not** write `_self_check_v296` or re-run the 94-symbol / `740f4bcd…` golden-model contract
  (no model edit was made, so the contract is unchanged and was not touched).
- Did **not** re-derive the cave defect addresses on bytes this run (relayed; not load-bearing).
- Did **not** decode new cave bytes in Ghidra (there are no new bytes in any V296 artifact).

All of the above are recorded as gaps for a future pass on a genuinely-built image, not as completed
checks.
