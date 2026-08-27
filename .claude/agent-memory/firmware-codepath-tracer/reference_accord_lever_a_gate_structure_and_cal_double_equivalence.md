---
name: reference_accord_lever_a_gate_structure_and_cal_double_equivalence
description: "Lever A's two sar sites (0x3AB76 r26, 0x3AC20 r24) are PROVEN outside the LKAS repoint gate (lp/gp-0x683c-then-gp-0x6806) -- the gate only muxes which cal feeds the multiply, never wraps the shift. Doubling the gated arm cal (0xC6446 for r24, 0xC6444 for r26) is BIT-EXACT identical to Lever A's sar 0xa->0x9 on the branch that cal feeds (2X>>10 == X>>9 exactly, proved not asserted). r24's gated arm (0xC6446) is ALREADY at 5244 on V67-V86B, a ~5x bigger dose than the raw gated-Lever-A-equivalent (1024) would be. 0xC6444 (r26's mirror) is the untried, exact, cal-only route -- 512->1024, but r26's own averaged input is reported elsewhere as near-zero (cal base 0xC6564, 40 bytes of exact zero), so its real-world payoff is capped independent of the gate question. Corrects a live arithmetic trap: tp+0x74FA = 0xC64FA, not 0xC63FA (self-caught mid-session)."
metadata:
  type: reference
---

# Can Lever A be LKAS-gated? Definitive structural answer (2026-08-08, team-lead brief via LEVERA)

Fresh `decompile_function`/`disassemble_function` on `FUN_0003aa2c` (0x3aa2c-0x3ad73), stock `code.bin`,
cross-checked against `builds/v50_v79/build_v62_tva.py`, `builds/v50_v79/build_v67_tva.py`, `build_v84/86_tva.py` (which independently
derive the same structure — three-way agreement, not just my own read).

## The gate never wraps the shift — proved from the disasm, not inferred

```
R26: 0x3AB56 cmp r0,lp / 0x3AB5E ld.hu 0x7444[tp],r8   <- mux picks r8 (which cal)
     0x3AB72 mul r8,r6,r0 ; 0x3AB76 sar 0xa,r6          <- LEVER A site, UNCONDITIONAL w.r.t. lp
     (this sar DOES sit inside a *different*, non-LKAS "zero-force" gate:
      skipped only when (gp-0x6b5e!=0) && (sVar7==1) both true — orthogonal to lp/683c/6806)

R24: 0x3AC04 cmp r0,lp / 0x3AC08 ld.hu 0x7446[tp],r10   <- mux picks r10 (which cal)
     0x3AC18 mul r10,r8,r0 ; 0x3AC20 sar 0xa,r8          <- LEVER A site, TRULY unconditional, no gate at all
```

The `lp`-gate (tested at 0x3AB56/0x3AC04) only selects which cal loads into the multiply's second
operand; it never brackets the `mul`/`sar` pair. **This settles the "is leg (a) an artefact of where the
edit landed" question: no — it's structural.** The shift is common to every arm of the 4-way priority
mux (r24: `671d!=0→0xC6442` / `lp!=0→0xC6446` / `!bVar1→0xC6440` / else natural LERP), so editing the
shift immediate is inescapably a blanket multiplier across all four arms, gated or not.

## Doubling the gated cal == Lever A's shift edit, BIT-EXACT, proved

Both lanes compute `out = (A * C) >> 10` (Q10 fixed point). `2X >> 10 == X >> 9` for every integer X,
including negative (V850 `sar` is a floor arithmetic shift, and `floor(2X/1024) == floor(X/512)`
identically — no rounding-bit discrepancy). So:

```python
def stock(A, C):       return (A * C) >> 10
def lever_a(A, C):      return (A * C) >> 9          # V62/V65's sar 0xa->0x9
def cal_doubled(A, C):  return (A * (2*C)) >> 10      # double the CAL, leave shift at 0xa
assert lever_a(A, C) == cal_doubled(A, C)              # holds for ALL A, C -- proved, not approximate
```

Doubling the gated arm's cal therefore reproduces Lever A's ×2 exactly, but ONLY on the branch that cal
feeds — never universally like the raw shift edit.

## Where this lands on the actual cal cluster

- **r24 (`0xC6446`, tp+0x7446, reached iff `gp-0x671d==0 && lp!=0`)**: stock 512; gated-Lever-A-equivalent
  would be 1024. **Already exceeded** — V67/V68/V71c and V84/V85/V86/V86B carry `0xC6446=5244`
  (bytes `7C 14`), chosen as 2.00× the *natural LERP* value at grind #1's operating point, not 2.00× the
  stock arm — i.e. ~10.24× stock, ~5× the raw gated-Lever-A dose. Already measured 0.40 [0.27,0.58] on
  grind #1, creep grind #2 → 0 bursts.
- **r26 (`0xC6444`, tp+0x7444, reached iff `lp!=0`, unconditionally overrides the natural LERP/0xC643E
  arm — confirmed independently from the decompile, matches V86's own comment "gain_A rec0/rec1 DEAD...
  armed path OVERWRITES gain_A with [0xC6444]")**: stock 512 on every repoint-carrying build to date
  (V67→V86B) — this is the cell V86's own comments call "the untried S3 lever." 512→1024 is the exact,
  untested, cal-only route. Caveat: `builds/v50_v79/build_v67_tva.py` records r26's own averaged input's cal base
  (`0xC6564`) as 40 bytes of exact zero — if that holds, r26 is near-input-starved regardless of what
  multiplier sits on 0xC6444, capping this route's real-world payoff independent of the arithmetic.

## GATE 1 / GATE 2 for the cal-only route

Both `0xC6444`/`0xC6446` are single-reader (`FUN_0003aa2c`-exclusive, confirmed 2-method in
[[reference_accord_gp683c_repoint_hypothesis_and_v850_bit5_encoding_rule]]), inside the existing
CRC-covered `CAL_BLOCK=(0xC6000,0xC6FFC)` (`builds/v50_v79/build_v53_tva.py:147`). GATE 1 is vacuous — pure ROM cal
read, no RAM cell, no register-indirect access. GATE 2 passes on the same sign/phase argument as the
already-flown Lever A/Lever B (lead/damping term, same mechanism) — for r24 this is moot since a bigger
dose is already flying; for r26 it's a real but likely low-yield open item.

## Route ranking (risk)

Moving the `sar` itself inside the gate (duplicating the mul/shift pair or inserting a second branch) is
**cave-class** — the shift has no existing branch to land inside, so this needs new instructions, not a
field edit. This is correctly the blocked route. The cal-doubling routes are the kit's proven-safe class
(single halfword, existing CRC discipline) and for r24 are not hypothetical — already on the car.

## 🛑 Address-arithmetic trap self-caught this session

Computed `tp+0x74FA` as `0xC63FA` first (dropped the leading 7 vs 6 sloppily) — WRONG. Correct:
`tp=0xBF000`, `0xBF000+0x74FA=0xC64FA`. Verified by `read_memory(0xC64FA)`=byte `05`, which matches the
"state>=5" persistence-ramp threshold framing in `builds/v50_v79/build_v62_tva.py`'s docstring exactly, confirming the
fix. `0xC61F6` (tp+0x71F6, the rate-lane deadband) = byte `03`, independently matches
`build_v66/67_tva.py`'s "0xC61F6 3 -> 0 MUST NOT BE MADE" record. Both corroborations came from a fresh
`read_memory`, not from re-trusting the earlier wrong arithmetic.

## Related
[[reference_accord_gp683c_repoint_hypothesis_and_v850_bit5_encoding_rule]] — the repoint's exact byte
mechanics (0x3AA96 C5→FB, hw1-bit5-even rule) this session reused and reconfirmed.
[[reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain]] — r24's producer (pure finite
difference, no low-pass), the structural basis for this session's Q4 mechanism argument.
[[reference_accord_fun3aa2c_is_gp6b94_writer_and_r24arm_gate]] — prior partial mapping of the same
function this session completed with the sar-site/gate-independence proof.
