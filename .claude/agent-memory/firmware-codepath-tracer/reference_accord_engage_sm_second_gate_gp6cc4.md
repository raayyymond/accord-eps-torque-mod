---
name: reference-accord-engage-sm-second-gate-gp6cc4
description: FUN_00040d58 (Accord TVA-A160 engage-SM decider) ENGAGED/HOLDING branches have a SECOND independent disengage gate beyond gp-0x6a62/cal-0xC6312 -- an accumulator gp-0x6cc4 gated by cal 0xC6354=4825, via FUN_000406ae (ENGAGED, 4-way consensus check) and FUN_00049a5a (HOLDING, direct ABS test). V33 (which raised 0xC6312 to 65535) did NOT touch this gate, which is the leading candidate for why the gentle EME survived V33.
metadata:
  type: reference
---

# FUN_00040d58 second disengage gate — `gp-0x6cc4` / cal `0xC6354` (2020 Accord TVA-A160)

Found 2026-07-03 while investigating why **V33** (which raised the known torque-disengage cal `0xC6312`
320→65535, disabling the `gp-0x6a62` gate) **did not fix the gentle EME**. Full byte-level walk of
`FUN_00040d58` (0x40d58–0x40e78) via radare2 `v850.gnu` (`code.bin`, gp=0xFEDF8000, tp=0xBF000).

## The finding [V — disasm, byte-level]

In BOTH the ENGAGED (param==2) and HOLDING (param==3) branches, AFTER the `gp-0x6a62 >= cal 0xC6312` check
(the one V33 patched), there is a SECOND, structurally independent gate that can also force the SM out of
"stay engaged" (`r12 = 4`, a state distinct from both "stay" (0) and "hard disengage" (2), but which still
means leaving the delivering state — functionally an alternate disengage/dropout path):

### ENGAGED (param==2), at `0x40ddc`:
```
0x40dd8  st.b  r0, -13750[gp]        ; clear substate gp-0x35b6 (stay marker)
0x40ddc  jarl  0x000406ae, lp        ; call FUN_000406ae() -- NO PARAMS PASSED (pure global-state read)
0x40de0  cmp   r0, r10               ; test return value
0x40de2  be    0x00040e1a            ; if FUN_000406ae()==0 -> r12=4  (LEAVE ENGAGED)
0x40de4  ld.bu -13750[gp], r12       ; else r12 = 0 (stay)
```

### HOLDING (param==3), at `0x40e08`:
```
0x40e00  ld.w  -27844[gp], r6        ; r6 = gp-0x6cc4  ("current" accumulator)
0x40e04  st.b  r0, -13750[gp]
0x40e08  jarl  0x00049a5a, lp        ; r10 = ABS(r6) = ABS(gp-0x6cc4)
0x40e0c  ld.hu 0x7354[r5=tp], r16    ; cal tp+0x7354 = 0xC6354  <-- ⚠ NOT 0xC7354 (off-by-0x1000 trap, self-corrected this session)
0x40e10  cmp   r16, r10
0x40e12  bh    0x00040e1a            ; if |gp-0x6cc4| > cal(0xC6354) -> r12=4  (LEAVE HOLDING)
0x40e14  ld.bu -13750[gp], r12       ; else stay
```

**Cal `0xC6354` = 4825** (`d9 12` LE, `read_memory`/`px` verified). This is in the SAME `0xC6300`-ish cal
region as `0xC6312`=320, but is a DIFFERENT halfword, untouched by V32/V33 (which only edited `0xC6312`).

**ENGAGING (param==1) and RE-ARM (param==4) do NOT have this gate** — confirmed by full disasm of those
branches (0x40d78–0x40dc4 and 0x40e1e–0x40e64): no reference to `gp-0x6cc4`, `FUN_000406ae`, or
`FUN_00049a5a` in either. The gate is specific to sustained delivery (ENGAGED/HOLDING), exactly where a
gentle-EME would present.

## `FUN_00049a5a` — generic ABS() helper [V]
```
0x49a5a cmp r0,r6 / cmov ge,r6,r10,r10 / bge 0x49a6e / (INT_MIN guard) / mov r6,r10 / subr r0,r10 / jmp[lp]
```
`r10 = |r6|` (param in r6, INT32_MIN-safe). Used by both branches above and internally by `FUN_000406ae`.

## `FUN_000406ae` — 4-channel consensus/plausibility monitor on `gp-0x6cc4` [V structure, INFERRED semantics]
Entry 0x406ae. No call-site params (r6/r7/r8 not set up before the `jarl` at 0x40ddc) — operates purely on
global state. Structure (cross-checked against 4 nearly-identical unrolled loop blocks 0x406b4–0x407a2):

- 4 small history arrays, bases `gp-0x635C`, `gp-0x6374`, `gp-0x6368`, `gp-0x6380` (32-bit elements), each
  with its own count byte `gp-0x6725`, `gp-0x6727`, `gp-0x6726`, `gp-0x6728`.
- For each array, scans `i=0..count-1`: `diff = ABS(gp-0x6cc4 - arr[i])` (via `FUN_00049a5a`), compares
  against the SAME cal `0xC6354`=4825 (loaded once, cached in r24). Tracks (a) the most-recent index where
  `diff < 4825` ("agrees") in r27/r25/r22/r20 respectively, and (b) sets a bit (8/4/2/1) in a 4-bit mask r26
  if the LAST-scanned (most recent) sample agreed.
- **Early-bypass** (0x4080e): if any of the 4 "most-recent-agreeing" array slots still holds the sentinel
  `0x7FFFFFFF` (uninitialized), OR any counter byte equals `0xFF`, OR `gp-0x6cc4` itself reads the sentinel
  → skip straight to return with `r21` still 0 (its init value) = **function returns 0**.
- If mask `r26==15` (all 4 channels' most-recent samples agree with current): computes a new rounded
  4-way average, stores it to `gp-0x35AC` (a persistent "confirmed reference"). Otherwise reuses the STALE
  average from `gp-0x35AC`.
- Final check: `|gp-0x6cc4 − reference_average| vs cal 0xC6354` again; sets return `r21=1` ONLY if the
  deviation is < 4825 (i.e., current value is corroborated by the 4-way consensus).
- **Return 0 = "cannot confirm consistency"** (either not enough history yet, or current value has drifted
  from the 4-channel consensus by ≥4825). **Return 1 = "confirmed consistent."**

**Net effect:** `FUN_00040d58`'s ENGAGED branch leaves the engaged state (r12=4) whenever this consensus
monitor CANNOT confirm `gp-0x6cc4` is consistent — including transiently right after any event that
resets/perturbs the 4 history arrays, or whenever `gp-0x6cc4` genuinely diverges from its own recent
history by ≥4825.

## `gp-0x6cc4` identity [INFERRED, not fully labeled]
Sole writer located at `0x3bcee` (`st.w r7,-27844[gp]`), with lockstep shadow `gp-0x4cf4` (`0x3bcf2`,
mismatch → `FUN_0006b9fa` fault, `0x3bcf8`). `r7` is computed a few instructions earlier (0x3bcbc–0x3bcd8) as
a **difference between two operands with an explicit `sar 11 / shl 11 / sub` MODULO-2048 wraparound
correction** — the classic idiom for a Q11 angle/position delta (2048 = one full 11-bit revolution). This
function is called from a large, frequently-executed cluster: **44 total references to `gp-0x6cc4`** span
addresses `0x3bce6`–`0x40e02`, overlapping the FOC/PI-controller code region documented in
`reference_accord_lkas_path_wiring.md` (`FUN_0003b8f6` FOC PI controller sits at 0x3b8f6, inside this same
cluster).

**Working hypothesis (NOT proven): `gp-0x6cc4` is a rotor/column ANGLE or POSITION-TRACKING ERROR/DELTA**,
not a torque value — separate in kind from both sensor-A (`gp-0x6a62`) and sensor-B (`gp-0x4f60`) torque
signals. If correct, this would make it PLAUSIBLY bump-sensitive: a mechanical shock (hard turn + bump)
would directly perturb a position/angle-tracking signal, unlike the far-out-of-range coil/CAN-torque
ceiling checks in `FUN_00028ea6` (which sit at 25600–32000, far above real torque magnitudes ~3400).

## Why this matters for the gentle-EME investigation
**V33 raised `0xC6312` (320→65535) and disabled the `gp-0x6a62` torque-disengage gate — but did NOT touch
`0xC6354`=4825 or the `FUN_000406ae`/`FUN_00049a5a` mechanism.** This is the leading structural candidate for
why the gentle EME reportedly persisted after V33 was flashed. To confirm: (a) pin `gp-0x6cc4`'s physical
identity via further data-flow tracing of its writer's callers/params, (b) live-RAM read `gp-0x6cc4`
(`0xFEDF133C` = gp−0x6CC4, verified: 0xFEDF8000−0x6CC4) during a hard-turn+bump event to see if it crosses
4825, (c) if confirmed, the
lever is cal `0xC6354` (same block region as `0xC6312`, recompute the same `0xC6000`-block CRC).

## Related
[[reference-accord-lkas-engage-sm-disengage-trigger]] — the FIRST gate (`gp-0x6a62`/`0xC6312`), V33's target.
[[reference-accord-lkas-path-wiring]] — FOC PI controller region (`FUN_0003b8f6`) overlapping this cluster.
