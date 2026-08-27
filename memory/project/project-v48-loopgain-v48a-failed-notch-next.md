---
name: project-v48-loopgain-v48a-failed-notch-next
description: "V48 build state: V48A (cal-only mute of the two strongest carriers, type-8 0xC4120 + FUN_0003a382 uVar27) FLASHED and did NOT fix the vibration -> anti-damping is distributed -> the 21.4 Hz notch V48B (designed, unbuilt code cave) is the remaining lever. Route B is hygiene-only."
metadata:
  type: project
---

**In-flight build state after the 2026-07-21 loop-gain-characterization session. Supersedes the V47
candidate framing.**

**V48A — cal-only, BUILT + VERIFIED + FLASHED → did NOT fix the vibration.** `builds/v18_v49/build_v48a_tva.py` =
V38 + ratchet (`0x454FE`) + mute the type-8 carrier (mixer slot-8 sum gate `0xC4120` `1→0`) +
attenuate `FUN_0003a382` (post-sum gain `uVar27` `0xC67B8/BA/BC` `1024→256`, −12 dB). Cut from V38
(stock damper; V47 opening NOT carried). 4× forward gain untouched. Safety-GO (the type-8 gate's second
reader `FUN_00027b0a` is an int/float lockstep monitor that reads the SAME cal byte → matched-symmetric,
can't trip; `uVar27` pure-leaf). 50/50 CRC, RWD SHA `77574f9e…c5bc80`.

**Why the null matters:** V48A muted the **two strongest identified 21 Hz carriers** and did nothing.
The loop-gain model says each single carrier only cures the ring if it is ≥~50% of the loop gain; a null
on BOTH ⇒ the anti-damping is **distributed** across more collocated lanes (boost `FUN_00034a72`,
magnitude `FUN_000352b4`, damper, r24/r26), and/or the type-8 latch was inactive. **This is the model's
"→ notch" branch.**

**V48B — the 21.4 Hz NOTCH — BUILT + GHIDRA-VERIFIED, UNFLASHED (2026-07-21 late).**
`analysis-2020accord/builds/v18_v49/build_v48b_tva.py` + `studies/caves/v48b_cave_asm.py` + `studies/models/eps_v48b_cave_model.py`. V38 + ratchet +
a **138-byte, 41-instr code cave @`0xC4B34`** running DF-I Q12 (`b0=4045 b1=-7949 b2=3977 a1=-7949
a2=3926`) on a fresh `gp-0x4f60` read, storing the filtered copy to `gp-0x1500`; trampoline `jr @0x7FEAC`
(displaces `cmp r0,r8`/`mov r8,r14`, re-exec'd LAST so the `bge 0x7feb0` sees correct flags; return =
`0x7FEB0`, NOT `0x7feb4`); **7 live carrier repoints** `gp-0x4f60`→`gp-0x1500` (`FUN_0002c478` @2c480,
`FUN_000352b4` @354d2/@35aa4, `FUN_0003a382` @3a6ca/@3a7ca, `FUN_0003b49a` @3b4a8, `FUN_0003b66a` @3b672).
2 DORMANT reads (`0x34392`/`0x34ace`) left raw (dormant fallback arm of a cal-gated mux `0xC6498/99`=1 —
red-team confirmed correct to leave raw). RAM: y1/out=`gp-0x1500` (V31P flash-validated), x1/x2/y2=
`gp-0x14FC/FA/F8`. Notch **exactly unity at DC** (73/73). Verify: 50/50 CRC (single MAIN block) + RWD
round-trip + **every edit re-disassembled in Ghidra from the built image**. See
[[reference-accord-v48b-notch-cave-build]] and `docs/handoffs/2026-07/HANDOFF-2026-07-21-v48b-notch-build.md`.
- **Adversarial review — all monitor-asymmetry items CLOSED, SAFE.** type-8 lockstep `FUN_00027b0a`
  matched; all other repointed-lane consumers have 0 raw `gp-0x4f60` reads; damper/boost dormant reads =
  cal-gated mux (not comparator); DTC-0x1c/0x1d pair (`FUN_00042af8`/`FUN_00043e44`) = matched int/float
  lockstep recomputing the same cal-gated (`0xC64CB`) formula from the same already-notched `gp-0x6b4a`
  (±5-count tol) → a shared-input perturbation cannot erode their agreement; strictly-attenuating notch
  only shrinks the per-tick delta. No raw-vs-filtered divergence-trip mechanism at any monitor.
- ⚠ CODE CAVE = the kit's only bricked class (V24/V27). Ultimate check is first-minutes on-car
  observation. Flash only on explicit operator instruction naming file + bus.
- Corrections found building it: the old `gp-0x14E0` "4 free bytes" record was partly wrong (3 live);
  `gp-0x7F00` (page base, 433 `movhi 0xFEDF` sites) rejected; the handoff's `0x7feb4` return was wrong.

**Route B ("achieve 4× via a bigger setpoint + stock `0xC646C`") is HYGIENE-ONLY (ΔL(21Hz)=0)** by
gain-rescaling invariance — the delivered command is identical, so the carriers are unchanged. Cleaner
architecture, not a vibration fix.

Read `docs/research/VIBRATION-DOSSIER.md` + `docs/handoffs/2026-07/HANDOFF-2026-07-21-v48-vibration-loopgain-notch.md`.
Related: [[reference-accord-collocation-motor-rate-damper-dead]].
