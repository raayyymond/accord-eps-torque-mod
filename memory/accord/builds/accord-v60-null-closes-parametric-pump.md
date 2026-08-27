# ★★ V60 FLASHED → NULL. The parametric pump is CLOSED, and `0xC63BA` goes with it.

**Operator drove V60, 2026-07-31: "It did not fix the vibration issue."** No rlogs (V60 carries V59's
probe unchanged, so there was no new telemetry to upload).

## Why this null is a result, not a wasted drive

V60 (`0xD2006` 102 → 43, the boost-amplitude blend rate) was built explicitly as a **discriminator, not
a fix** — the record predicted the null in advance: *"Expect it to be NULL. It attacks the pump, and the
pump now looks like a passenger. Fly it as a DISCRIMINATOR — a null closes the parametric mechanism and
leaves the loop standing."* Causality on the pump was **not settleable observationally** (the index is
`|x|` of a bar-derived signal, so 2f coupling is arithmetically forced), and `eps_crit = 2/Q` needed a
**passive Q** that V59 could not measure (no ring-down exists — 66 candidates, longest 0.63 cycles).
Only an intervention could separate drive from echo. It did.

⇒ **The V58/V59/V60 parametric-pump arc is closed.** The 42.19 Hz index modulation is real, is
engagement-gated, and does **not** drive the grinding.

## ★ Load-bearing consequence: `0xC63BA` is pre-falsified by the same null

`0xC63BA` (= 512, a 2-stage cascaded EMA α = 0.5, ~−0.30 dB at 21 Hz — effectively wide open) filters
the raw torque into `FUN_0003b66a`, which produces `gp-0x6b9a` / `gp-0x6ba6`. It looked like the ideal
next lever: cal-only, 2 readers (byte-verified at `0x3B7BA` / `0x3B7D4`, both in `FUN_0003b66a`), never
edited by any build, and explicitly reserved — `builds/v50_v79/build_v59_tva.py:444` asserts it stock with the comment
*"a V60 candidate, must NOT move here."*

**But a byte scan of its consumers closes it.** Readers of `gp-0x6b9a` (8 sites) and `gp-0x6ba6`
(7 sites) are confined to `FUN_00034350` (damping, `0x34414-0x3443E`), `FUN_00034a72` (boost,
`0x34B5E-0x34CB6`), their producer `FUN_0003b66a`, and V59's probe cave (`0xC4B38`). ⇒ **the amplitude
index drives ONLY the boost/damping amplitude LERPs — the exact mechanism V60 attacked and falsified.**
Filtering the index's input attacks the same modulation from the other end.

🛑 **Do not propose `0xC63BA` as a grinding fix.** It would be the V44/FactorC pattern again: an
adjacent lever on a mechanism that has just been falsified, made to look fresh by a new rationale.
It remains legitimate for a *different* target (it changes assist gain-scheduling dynamics).

## Also closed or corrected this session
- `0xC6499` (tp+0x7499) = **1** byte-verified ⇒ `FUN_00034a72`'s local torque EMA (`0x34ACE`, cal
  `0xC6372` = 205) is the **dead** branch; the live index comes from `gp-0x6ba6`.
- `0xC64BE` (tp+0x74be) = **0** byte-verified ⇒ `FUN_0003b66a`'s `gp-0x4f62` **magnitude** term
  (`0x3B736-0x3B758`) is dead code. The rate's only live role there is a validity gate.
- `FUN_00036c12` (`gp-0x6b26`) and `FUN_00036388` (`gp-0x6b62`, the return-centre lane the operator
  hypothesised) read **no torque signal at all** — speed- and motor-rate-keyed only. Structurally
  irrelevant to the torque-feedback hypothesis. Two lanes removed from the search.

⚠ **`0xD2834` / `0xCA154` (the base-assist boost curve = loop GAIN) has ZERO build-script hits** — never
touched. It is the only remaining lever that reduces loop *gain* rather than deleting a lane, and it is
a direct trade against steering weight ⇒ **an operator decision, not an analyst's.**

Related: [[accord-torque-rate-lane-v52c-structurally-blind]],
[[accord-a-caveat-can-mutate-into-a-result]], [[accord-v59-parametric-pump-marginal]],
[[accord-check-build-lineage-before-proposing-lever]].
