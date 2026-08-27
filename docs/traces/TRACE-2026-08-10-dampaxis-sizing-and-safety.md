# TRACE 2026-08-10 — `DampAxis` (`gp-0x6b26`) sizing and safety, full census

Agent `fw-dampaxis`. GhidraMCP on stock `code.bin` only (`list_open_programs` confirmed single
program this session). `gp=0xFEDF8000`, `tp=0xBF000`. All addresses fresh-decompiled/disassembled
this session unless cited to a prior memory file. EVIDENCE = method given; BELIEF = flagged.

---

## Q1 — the lane, end to end

### Producer: `gp-0x6c2c`, `FUN_00041464` @`0x41464` (1 kHz, sole caller `FUN_0002214a`)

Decompiled fresh (`decompile_function 0x41464`). Confirmed byte-exact against inherited memory:

```
K0 = cal(0xC643C) = 37     (tp+0x743C, read fresh = 0x25 = 37)     alpha0 = 37/128
K2 = cal(0xC40DC) = 22     (tp+0x50DC, read fresh = 0x16 = 22)     alpha2 = 22/64
x  = gp-0x4f50                                    # motor-rate estimate (sole writer 0x68FDE)
y0 += ((x*1024) - y0) * K0 >> 7                   # 0x415F8  EMA #1
d   = y0[n] - y0[n-1]                             # 0x4160C  backward difference
d32 = clamp(d*32, +-0xFA0000)                     # 0x41614
yA += (d32 - yA) * K2 >> 6                         # 0x41640  EMA #2, applied to the DIFFERENCE
gp_6c2c = yA >> 9                                 # 0x41AC2
```

Fresh Python time-domain simulation of this exact integer cascade (fs=1000 Hz, 1000-count sine,
steady state after 20 cycles, gain by complex FFT correlation at drive frequency):

```
f= 7.79 Hz   gain=3.078x ( 9.77 dB)
f=21.09 Hz   gain=7.542x (17.55 dB)
f=28.10 Hz   gain=9.260x (19.33 dB)
```

**Matches the triple-verified prior figure to 3-4 sig figs** ([[reference_accord_gp6c2c_transfer_function_triple_verified]]). `|H(7.79)| = 3.08x`, `|H(21.09)| = 7.54x` relative to DC — **[EVIDENCE, independently re-derived, not merely cited]**. `FUN_00041464` also carries **FOUR of its own shadow-lockstep pairs** (`gp-0x6abc`/`gp-4cc0`, `gp-0x6abe`/`gp-4cc2`, `gp-0x6ac0`/`gp-4cc4`, `gp-0x6ac2`/`gp-4cc6`), each calling `FUN_0006b9fa` on mismatch — see Q3.

### `FUN_00036c12` @`0x36c12` (friction-comp lane, 1 kHz) — decompiled fresh

```python
sVar7 = LERP(gp-0x6a5e, X=0xCBE74[mode].X, Y=0xCBE74[mode].Y)   # speed-indexed magnitude
iVar4 = ((gate(gp-0x6c2c) * sVar7) >> 6) * 0x111                # 0x36cbe-cc4
iVar5 = iVar4 >> 0x12                                            # 0x36cca
iVar5 = clamp(iVar5, -cal(0xC407E), +cal(0xC407E))               # 0x36ccc-ce2, cal read 3x, all ld.h
# LOCKSTEP CHECK before commit -- fresh finding, see Q3:
if gp-0x6b26 == gp-0x4cd0 (shadow):
    gp-0x6b26 = iVar5 ; gp-0x4cd0 = iVar5           # 0x36ce4/0x36cf0
else:
    FUN_0006b9fa(&gp-0x4cd0)                        # STALE value kept, fault path taken
```

`0xC407E` read fresh = `ff 01` = **511** (stock). `gate(gp-0x6c2c)` is the dual-tail
`(gp-0x6c2c+32000) <u 64001` test — **architecturally a no-op**, `gp-0x6c2c`'s own producer already
clamps to ±32000 (see above). `0xCBE74 + mode*4` dereferenced fresh (Python, this session, on stock
AND V73-V77 images — table below): mode 24 (manual) `X 0xD6A66`, `Y 0xD6A6C`; mode 26 (engaged)
`X 0xD7A56`, `Y 0xD7A5C`. Stock: **both records byte-identical**, `Y=(-9830,-5734,-1966)`.

### Full reader census of `gp-0x6b26` — Ghidra ∪ Python, both encodings, register-indirect included

`search_instructions(operand_pattern="6b26")` → 7 raw hits, adjudicated:

| addr | function | role |
|---|---|---|
| `0x36cf0` | `FUN_00036c12` | **the ONLY writer**, `st.h r6,-0x6b26,gp` |
| `0x36ce4` | `FUN_00036c12` | self-shadow-lockstep READ (against `gp-0x4cd0`) — see Q3 |
| `0x36d78` | `FUN_00036d74` | **the DTC-0x1d monitor** — see Q3 |
| `0x3815c` | `FUN_00038148` | Path 2 — one of 6 weighted lanes into the residual mixer |
| `0x3ac98` | `FUN_0003aa2c` | **Path 1 — direct, UNWEIGHTED addend in the aggregator** (new finding, below) |
| `0x6b25a`,`0x6b25e` | `FUN_0006b162` | **FALSE POSITIVES** — `bge 0x6b26c`/`ble 0x6b266`, branch-target-text collision, unrelated function, no `gp`/`tp` in the instruction |

Python raw LE scan of disp16 (both `st.h`/`ld.h` opcode fields, `hw2=disp|1` handled), the 6-byte
extended form (0-indexed decoder), and `movhi 0xFEDF,r0,rN` + register-indirect — **zero additional
hits on any form**. Matches the V90 spec's inherited "1W/4R" census exactly, now with every address
resolved and every reader's role identified. **Zero aliasing found on `gp-0x6b26` or `gp-0x6c2c`.**

### 🛑 NEW FINDING — `gp-0x6b26` has its OWN Path-1, exactly parallel to `gp-0x6bd0`'s

The golden model documents `gp-0x6bd0` (the damper) reaching the motor **two ways**: Path 1, bare
and unity-weighted straight into `FUN_0003aa2c`'s sum, and Path 2, weighted (`0xC63A0`) through
`FUN_00038148`'s residual mixer. **`gp-0x6b26` has the identical structure**, confirmed by fresh
decompile of `FUN_0003aa2c` (`0x3aa2c`) — the reader at `0x3ac98`:

```c
// FUN_0003aa2c, the 'else' arm (gp-0x67ac != 1 -- the ONLY live arm, per
// [[reference_accord_gp67ac_reduced_branch_unreachable]]):
iVar19 = iVar9 + iVar19
       + gate(gp-0x6ad4, +-0x2800)              // Path-2 PID output, weight 1
       + iVar14
       + gate(gp-0x6b26, +-0x400)                // <-- Path 1, weight EXACTLY 1, no cal scaling
       + gate(gp-0x6bbe, +-0x800)                // boost
       + gate(gp-0x6bd0, +-0x800)                // damper Path 1
       + gate(gp-0x6b86, +-0x3000)                // peak-hold (FUN_000352b4), not velocity-proportional
       + iVar21 + iVar16;
iVar14 = FUN_00036682();
// then: gp-0x6b94 = clamp(iVar14 + iVar19, -10240, +10240), own shadow-lockstep vs gp-0x4ce0
```

**Path 1 delivers `gp-0x6b26` to the aggregator with weight exactly 1.000, zero additional filtering,
same tick.** Path 2 (via `FUN_00038148`'s weighted 6-lane mixer, `0xC63A6=1024` stock, subtracted
from the plant-model residual, then LERP'd, then through `FUN_00037fe6`'s unity 7-term sum, then
`FUN_0003a382`'s gain-scheduled PID) is slower and carries the referred gain **×2.336 @7.79 Hz,
×1.601 @21 Hz, ×1.318 @28 Hz** to `gp-0x6b70` ([[reference_accord_fun36c12_sign_settled_dissipative]]).
**Path 1 is very likely the dominant delivery route for a dose** — it has zero extra phase, where
Path 2 stacks an EMA, a LERP and a full PID on top. Both share the SAME gating (`±1024` on the SUM_6ch
side, `±1024`-equivalent `±0x400→0x801` on Path 1) — **unreachable in both places**, since `0xC407E`
clamps `gp-0x6b26` to ±511 before either reader ever sees it (511 < 1024).

**Sign**: both paths carry the producer's dissipative sign (`gp-0x6b26 = -k·gp-0x6c2c`, structurally
dissipative to Nyquist, [[reference_accord_fun36c12_sign_settled_dissipative]]) unmodified — Path 1
by plain addition, Path 2 by the golden model's already-verified Path-2 sign-cancellation argument
(Stage-2 subtraction × PID `err=setpoint-feedback` × polarity² all cancel, `gp-0x6bd0`'s dissipative
producer sign survives to `gp-0x6b94` — [golden model lines 1366-1372]). **`gp-0x6b26` sits in the
structurally identical position (same summing node, same subtraction, same PID loop) as `gp-0x6bd0`,
so the same sign-preservation argument applies to it — [EVIDENCE by structural identity, not
independently re-derived term-by-term this session].**

### GATE 1 — RAM ownership, `gp-0x6b26` / `gp-0x6c2c`

`gp-0x6b26`: 1W (`0x36cf0`) / 4R (above), zero aliasing. `gp-0x6c2c`: 2W, both inside `FUN_00041464`
(`0x4184e` normal, `0x41ac2` fallback per prior census), 3 consumer domains (FOC float term,
this friction lane, the oscillation detector `FUN_000428d4`) — unchanged from
[[reference_accord_gp6c2c_transfer_function_triple_verified]], re-confirmed via the search above.

---

## Q3 — V73/V74/V75/V76/V77 safety verdict (answered first — it is the blocker)

### Fresh, independent byte diff (Python, this session) of the actual images

`ACCORD_FIRMWARE_ROOT` images, region `[0x13000,0x100000)`, run-length collapsed:

| build | file used | `0xCBE74[26].Y` (m26/engaged) | `0xCBE74[24].Y` (m24/manual) | `0xC407E` | total diff bytes / runs |
|---|---|---|---|---|---|
| stock | `stock_fw_dump/code.bin` | `(-9830,-5734,-1966)` | `(-9830,-5734,-1966)` | **511** | — |
| V73 | `_v73_plain_image.bin` | `(-9830,-5734,-1966)` Honda | `(-9830,-5734,-1966)` | **850** | 298 / 139 |
| V74 | `_v74_engagedcols_x0_12_addonly_plain_image.bin` | **`(-14745,-8601,-2949)` ×1.5** | Honda | **850** | 449 / 190 |
| V75 | `_v75_CY0.566_magprobe_plain_image.bin` | **`(-14745,-8601,-2949)` ×1.5** | Honda | **850** | 449 / 190 |
| V75 (alt file on disk) | `_v75_CY0.566-EX1.200_magprobe_plain_image.bin` | ×1.5 (same) | Honda | 850 | 475 |
| **V76 — flown** | `_v76_v38base_relu_damper_plain_image.bin` | Honda (reverted) | Honda | **511** | 213 |
| V76 — other (never flown) | `_v76_gate_fb_arm5244_gateprobe_plain_image.bin` | ×1.5 | Honda | 850 | 452 |
| V77 | `_v77_C63A0.1024_v74base_plain_image.bin` | ×1.5 | Honda | 850 | 448 |
| V77b | `_v77b_C63A0.1024_v75base_plain_image.bin` | ×1.5 | Honda | 850 | 474 |

**Mode 24 (manual) is byte-identical to stock on every single build in this table, with no
exception.** This is a fresh, independent reproduction of the lineage record in
[[reference_accord_fun36c12_sign_settled_dissipative]] and `docs/BUILD-LINEAGE.md` RULE 11 — I did
not merely cite it, I re-derived it from the files on disk this session.

**Full run-by-run diff of V74/V75 vs stock (449 B each) independently confirms the "14 friction
sites, 86 functional bytes" figure**: the friction-row `9ad9 9ae9 52f8` → `67c6 67de 7bf4` pattern
(exactly the mode-26 Y-triple ×1.5) appears at **exactly 14 addresses** — `0xCF6E0, 0xCF6F0, 0xD0A5C,
0xD2A4C(mode 10, inert), 0xD2A5C, 0xD3A5C, 0xD3A6C, 0xD4A5C, 0xD6A5C, 0xD7A5C, 0xD7A6C, 0xD8A5C,
0xD9A5C, 0xD9A6C` (6 B each = 84 B) + `0xC407E` (2 B) = **86 B**, matching the record exactly. **V73
carries only `0xD2A4C` (mode 10) of these 14** — independently confirmed: V73's diff list has no
`0xCF6E0`/`0xCF6F0`/other-engaged-mode entries. The remaining ~360-390 bytes in V74/V75/V77 belong to
unrelated levers (V57 gain repoint `0x2A1F0`, V42 ratchet fix `0x454FE`, the telemetry
cave+hook `0x55C0E`/`0xC4B34`, `0xC62EA` steer-to-zero, `0xC6CD0` private 4× LKAS, and several
FactorE/gain_A-family per-mode records at offsets *other than* the friction Y array within the
same 0xD0xxx-0xD9xxx blocks).

### The DTC-0x1d monitor — fresh decompile, `FUN_00036d74` @`0x36d74`

```c
fVar3 = (float)(short)gp[-0x6b26] * 0.0009765625;         // = gp-0x6b26 / 1024
if (fVar3 > cal(0xC4004) || fVar3 < -cal(0xC4004)) {
    FUN_000462e6(0x39bc, fVar3, 0, cal(0xC4004), -cal(0xC4004));
}
// unconditional shadow/telemetry writes to gp-0x6b24/-0x6b22/-0x6b20/-0x6b1e follow either way
```
`0xC4004` read fresh = `00 00 00 3f` = **float 0.5** ⇒ trip at **512 counts**. Chased one hop further
than the inherited record: **`FUN_000462e6` unconditionally calls `FUN_00016de6(0x1d, param_1, 1,
1)`** — decompiled fresh, `0x462e6` — this is Honda's generic DTC state-machine entry point (the same
routine manipulates a per-DTC status-bit array, confirmed/pending/test-fail counters). **Passing
`0x1d` sets DTC 0x1d, unconditionally, on every trip.** [EVIDENCE — both functions decompiled this
session, not merely cited.] `get_xrefs_to(0xC4004)` returns the MISLEADING ZERO the skill warns about
for tp-relative displacements (as previously seen for `0xC407E`); the real xref is the `tp+0x5004`
displacement inside `FUN_00036d74`'s own decompile.

### 🛑 Shadow-lockstep pairs — `gp-0x6b26` IS inside one, and it is NOT the fault mechanism

Fresh finding, decompiling `FUN_0006b9fa` (@`0x6b9fa`, the generic mismatch handler used at every
site above): `{ gp[-0x4d6c] = shadow_addr; FUN_0006ce7c(4); }` — records which shadow pair failed and
calls a code-4 diagnostic routine. **This same idiom (`value == shadow ? commit : FUN_0006b9fa`) is
Honda's general-purpose RAM-corruption guard, used pervasively** — I found it independently guarding
`gp-0x6b26`/`gp-0x4cd0` (inside `FUN_00036c12`), `gp-0x6b94`/`gp-0x4ce0` (inside the aggregator
`FUN_0003aa2c`), and 4 more pairs inside `gp-0x6c2c`'s own producer `FUN_00041464`
(`gp-0x6abc`/`4cc0`, `gp-0x6abe`/`4cc2`, `gp-0x6ac0`/`4cc4`, `gp-0x6ac2`/`4cc6`) — **6+ instances, not
a narrow "4 pairs" specific to one monitor**, so team-lead's brief undercounted the pattern's reach.

**But it is a bit-flip/RAM-integrity check, not a magnitude/plausibility monitor**: it fires only if
the value currently in RAM differs from what the SAME function itself wrote there last cycle —
raising a calibration gain does not change whether last cycle's write survived to this cycle, so
**a `0xCBE74` dose cannot trip this check by construction.** It is orthogonal to the question asked.

### ✅✅ THE DECISIVE MECHANISM, confirmed structurally — `0xC407E` alone gates the fault, the dose cannot

`gp-0x6b26 = clamp(raw, -cal(0xC407E), +cal(0xC407E))` — **the stored value can never exceed
`cal(0xC407E)` in magnitude, regardless of the pre-clamp `raw` product or any gain multiplier applied
upstream of the clamp** (the `0xCBE74` Y-table is entirely upstream of this clamp — see Q1). The
DTC-0x1d monitor trips at `|gp-0x6b26| > 512`.

**⇒ At `0xC407E = 511` (stock, and every build in this table except V73–V75/V76-other/V77/V77b), the
monitor is untrippable BY CONSTRUCTION, for ANY value of the `0xCBE74` dose multiplier M** — M=1×,
10×, 1000×, it does not matter, because `gp-0x6b26` saturates at ±511 before the monitor ever reads
it. **The friction-gain dose and the DTC-0x1d fault are DECOUPLED as long as `0xC407E` is untouched.**
This is a *stronger* claim than "the fault requires raising `0xC407E`" — it is that **the dose,
by itself, structurally CANNOT reach this fault, at any multiplier.**

Independent corroboration from the table above: **V73 raised `0xC407E` to 850 alone (friction row
Honda-stock on the live column) and flew clean** — the clamp raise alone is necessary but the fault
needs a `raw` product that actually crosses into `(511, 850]`, which V73's stock-magnitude friction
row apparently never produced on that drive; **V74/V75 add the ×1.5 friction dose on TOP of the raised
clamp**, and both hard-faulted. The dose's role in the two observed faults was to make crossing
`512` *more likely* under the *raised* clamp — it played no independent role once the clamp constraint
is respected.

⚠ [BELIEF, unchanged from the inherited record] which of V74's (manual, friction row inert there) or
V75's (engaged, friction row live) fault was actually caused by this mechanism versus some other one
of the 449/298 differing bytes is not separately pinned — RULE 10 in `BUILD-LINEAGE.md` already covers
this split (V74 fault cannot be laid at this row; V75's can, but is not proven exclusive).

### VERDICT

**`0xCBE74` (the friction/comp gain table) is SAFE to dose to ANY multiplier with respect to the
DTC-0x1d monitor, PROVIDED `0xC407E` is left at its current value (511) and is not itself raised.**
The clamp is the sole gate on this fault path; the gain multiplier operates entirely downstream of it
and cannot un-gate it. **This is the clean "no [to raising 0xC407E], and here is why" the brief asked
for, plus a clean "yes [to dosing 0xCBE74 alone]" the record did not yet have** — verified in both
directions: (a) raising `0xC407E` past 512 removes the interlock (RULE 11, re-confirmed fresh this
session), and (b) raising the gain with the clamp untouched cannot reach the interlock at all,
regardless of magnitude, because the clamp binds first every time.

**What a large dose CAN still do, unrelated to DTC-0x1d**: increase rail duty (saturate more often —
Q2's `dose_headroom` quantifies this) and, past some multiplier, turn the lane into a harder relay
(describing-function gain falls below 1 — see Q2, reproduces the kit's own 1.000×@×4 / 0.881×@×6
figures exactly). Neither of those is a latched-fault mechanism; both are GATE-2/feel questions, not
GATE-1/safety questions. The `gp-0x6b94` aggregator clamp (±10240) and the Path-1 gate window (±1024,
itself unreachable) provide no additional headroom concern at any dose that keeps `0xC407E` = 511,
since Path 1's maximum possible contribution is bounded at exactly ±511 regardless of M.

---

## Q2 — sizing arithmetic

### `dose_headroom` — implemented, sanity-checked against the kit's own numbers

```python
import numpy as np
R = 511.0  # 0xC407E, stock

def dose_headroom(gain_multiplier, b26_distribution, clamp=R):
    """
    gain_multiplier: M applied to the 0xCBE74 Y-table (pre-clamp).
    b26_distribution: measured |gp-0x6b26| samples at STOCK gain (M=1), e.g. V90's 427 telemetry.
    Returns pin_fraction (frames that would rail at `clamp` under M) and the classical
    hard-clip describing-function gain at the distribution's own p99 magnitude.
    """
    x = np.asarray(b26_distribution, dtype=float)
    if np.mean(np.abs(x) >= clamp - 0.5) > 0.01:
        raise ValueError("input already >=1% railed at stock gain -- pre-clamp magnitude is not "
                          "recoverable from these samples; treat any answer as a LOWER BOUND")
    scaled = np.abs(x) * gain_multiplier
    pin_fraction = float(np.mean(scaled >= clamp))
    A = np.percentile(scaled, 99)
    if A <= clamp:
        N = 1.0
    else:
        r = clamp / A
        N = (2/np.pi) * (np.arcsin(r) + r*np.sqrt(1 - r**2))
    return {"pin_fraction": pin_fraction, "p99_scaled": A, "describing_function_gain": N}

def max_multiplier_for_pin_duty(target_duty, b26_distribution, clamp=R):
    """Largest M with P(|b26|*M >= clamp) <= target_duty, read off the empirical percentile --
    no assumed distribution shape. M_max = clamp / percentile(|b26|, 100*(1-target_duty))."""
    x = np.abs(np.asarray(b26_distribution, dtype=float))
    pct = np.percentile(x, 100*(1-target_duty))
    return np.inf if pct <= 0 else clamp / pct
```

**Sanity check against the kit's own recorded DF figures** — using the only two point-estimates on
record pre-V90 (measured ratchet amplitude 73-109 ct, [[reference_accord_fun36c12_sign_settled_dissipative]]):

```
M=1  pin=0.000  DF=1.0000        M=5  pin=0.500  DF=0.9828
M=2  pin=0.000  DF=1.0000        M=6  pin=0.500  DF=0.8834   <- matches the recorded 0.881 to 3 s.f.
M=3  pin=0.000  DF=1.0000        M=8  pin=1.000  DF=0.7029
M=4  pin=0.000  DF=1.0000
max M for <1% pin duty (2-point placeholder) = 4.70x
```
This reproduces "DF exactly 1.000 through ×4, first departure 0.881 at ×6" **exactly**, which is the
correctness check on the formula. **This is a placeholder run on 2 numbers, not a distribution — the
moment V90's `gp-0x6b26` telemetry lands, feed the real sample array into these two functions and the
answer updates without re-deriving anything.**

### The `gp-0x6b26 → gp-0x6b98` transfer, structural part only

**Path 1 (direct)**, confirmed this session: weight **1.000**, zero extra dynamics, into
`gp-0x6b94 = clamp(Σ..., ±10240)`. From `gp-0x6b94` to `gp-0x6b98` the chain is governor
(`FUN_0004503c`, a slew limiter — DC-transparent, non-linear only in fast transients) → comp-add
(`FUN_000456a4`, additive, "no-step" per [[reference_accord_fun456a4_gp6ad0_resolved_live_damping_no_step]])
→ shaper (`FUN_00042af8`, mode cal `0xC64C8=0` on every build ⇒ pass-through) → Q15 blend, scale
`0xC61DA/1024 = 1.066` at nominal blend → clamp ±0x2000(8192). **Structural DC gain, Path 1,
`gp-0x6b26 → gp-0x6b98` ≈ 1.000 × 1.066 ≈ 1.066 counts/count**, subject to the two clamps not binding
(golden model, "aggregator-leg gain from gp-0x6b08 to gp-0x6b98 near 0xC61DA/1024=1.066").

**Path 2 (via the residual mixer + PID)** is NOT a fixed scalar — referred gain to `gp-0x6b70` is
**×2.336 @7.79 Hz / ×1.601 @21 Hz / ×1.318 @28 Hz** (measured, [[reference_accord_fun36c12_sign_settled_dissipative]]),
then one more unity hop (`FUN_00037fe6`) and through `FUN_0003a382`'s P/I/D lanes, whose three gains
are all LERP-indexed on `gp-0x6ac0` (the SAME axis that indexes FactorE) — **gain-scheduled, not
reducible to one number without fixing an operating point.** This is knowable in principle (every
cal is on the calibration ROM) but is not a single scalar the way Path 1 is.

**The genuinely unmeasurable part, and I am naming it precisely per the "do not invent" instruction:
`gp-0x6b98 → column torque`.** Everything from `gp-0x6b26` to `gp-0x6b98` is firmware, decompiled and
addressed above. What happens after `gp-0x6b98` — FOC current control, the motor, the gearbox, the
rack, the column, the driver's hands/grip impedance — is the physical EPS plant, and the kit's own
attempt to identify that transfer from on-car logs (`cmd → column`, engaged) **returned a negative
group delay (feedback-dominated) and failed its own pre-registered coherence bar (max γ² = 0.475)** —
[[reference_accord_fun36c12_sign_settled_dissipative]], "THE REQUIREMENT AND THE MEASUREMENT ARE
INCOMMENSURABLE" section. **I am not inventing a number for it.** This is why any statement of
"N·m at the rim" below is qualified the way it is (Q5).

---

## Q4 — is there a better cal-only damping injection point?

Criteria: (a) proportional to a velocity/derivative, (b) dissipative sign into the motor command,
(c) cal-only reachable. Full census, with on-car status (`build_v*_tva.py` grepped):

| candidate | address | axis | mode-live? | blast radius | on-car | verdict |
|---|---|---|---|---|---|---|
| **`gp-0x6b26` (this lane)** | `0xCBE74`/mode records | `gp-0x6c2c` (motor-rate diff) | modes 24/26, both writable | Path 1 (direct, w=1) + Path 2 (mixer→PID) | ×1.5 on m26 flew V74/V75 (hard-faulted, but per Q3 the fault traces to `0xC407E`, not the dose itself) | **the standing candidate — now cleared of the fault mechanism provided `0xC407E` stays 511 (Q3)** |
| `gp-0x6bd0` (damper) | `0xC63A0` (Path-2 weight), `0xC9E9C` (FactorC/E) | `gp-0x6abc`/`gp-0x6abe` (rectified motor rate) | modes 24/26 | Path 1 + Path 2, same structure as above | **V80: relay, "worst grinding ever"**; V74/V83a/V86B all touched it | **KILLED — do not re-propose** (team-lead's own list; independently reconfirmed: same summing node as `gp-0x6b26`, already flown to failure) |
| r24/r26 rate lane (Lever A/B) | `0x3AA96`, `0xC6446` | rectified motor rate, inside the PID's D-term / a parallel gain arm | modes 24/26 | reaches `gp-0x6ad6`/`gp-0x6b98` | **flown 7× (V67,V68,V71c,V84,V85,V86,V86B); "CONFIRMED-FIX, AT ITS CEILING… tops out at V67's level, which the operator still calls grinding"** | **already at ceiling — nothing left to dose here without a new mechanism** |
| **`FUN_0003b8f6` INERTIA** (`0xC646E`) | inside the plant-model observer, alongside K1/FRICTION | `d/dt(rectified motor rate)` | mode-proof (bare `tp` scalar) | Path 2 ONLY, via `gp-0x6bfc→bc20→38148` — **no Path-1 equivalent** | **virgin — 0 build-script mentions, never dosed** — stock value read fresh this session = **1428** (u16 at `tp+0x746E`) | 🛑 **DO NOT PROPOSE — new finding this session, see below** |
| `gp-0x6b4e`/`gp-0x6b4c` (LKAS/LKAS-class), `gp-0x6b46` (torque-domain), `gp-0x6bbe` (boost) | `0xC63A8`/`AA`/`A4`/`A2` | LKAS command or driver torque, NOT rate | — | SUM_6ch siblings | — | **excluded on criterion (a)** — command/torque-proportional, not velocity-proportional |
| `gp-0x6b86` (peak-hold) | `FUN_000352b4` | not identified as rate-proportional this session (writer is a peak-hold routine per prior tag) | — | direct Path-1-style entry in `FUN_0003aa2c`, `±0x3000` window | — | **not excluded with confidence — flagged unexplored, not cleared** |

### 🛑 New finding: `0xC646E` (INERTIA's gain) looks like a candidate but is NOT one

`FUN_0003b8f6` (decompiled fresh, `0x3b8f6`) computes `INERTIA = clamp(EMA2(d/dt(polarity·gp-0x6abc·12)) * 0xC646E/2^24, ±10)`,
then **`gp-0x6bfc = clamp(cal(0xC6468) * (model − FRICTION − INERTIA), ±20000)`** — INERTIA is
**subtracted from the model inside the SAME observer, with the SAME polarity, as FRICTION (K1,
`0xC40D2`)**. The operator's own V89 finding, verified 5 ways this kit-cycle
([[accord-friction-polarity-more-assist]]), establishes that **subtracting more from this model makes
the residual more negative → `gp-0x6b70` more negative → PID error grows → assist INCREASES → the
wheel gets LIGHTER, not heavier.** Because INERTIA enters through the identical mechanism (same
function, same subtraction, same downstream residual chain, no Path-1 equivalent of its own),
**raising `0xC646E` almost certainly makes the wheel feel LIGHTER, not more damped — the opposite of
the intended effect for anti-ratchet work.** This is a new structural reading this session, not
previously on record for this specific cal (`0xC40D2`/K1 was already flagged; `0xC646E` had not been).
**I am not recommending it, and the reason is mechanistic, not merely "untested."**

**⇒ `gp-0x6b26` (0xCBE74) remains the only live, un-killed, additively-injected (Path-1), correctly-signed
candidate in this firmware that meets all three criteria.** Nothing found this session beats it.

---

## Q5 — cost accounting

**The arithmetic does NOT support an N·m-at-the-rim figure, and I am saying so plainly rather than
inventing one** — the blocking factor is exactly the `gp-0x6b98 → column torque` plant named in Q2,
which the kit's own on-car system-ID attempt could not close (negative group delay, coherence bar
failed). No Kt/gearing/rack-ratio constant for this EPS unit is on file anywhere in this kit (grepped
`docs/`, `memory/`, `analysis-2020accord/*.py` for `Nm`/`N·m`/torque-per-count conversions — zero
hits) and I am not inventing one.

**What the arithmetic DOES support — a relative, counts-domain comparison, all firmware-side and
therefore EVIDENCE:**
- `gp-0x6b26`'s hard ceiling (`0xC407E`=511, unconditionally, at any dose) is **511/8192 = 6.2 %** of
  the motor command's own full-scale clamp (`gp-0x6b98`, ±8192), and **511/1637 = 31.2 %** of the
  measured 99th-percentile engaged delivered command (V87 427 probe: p99 ≥1637 counts,
  [[reference_accord_v87_flew_the_probe_fired_and_6b98_is_broadband]]-class memory).
- At the measured stock operating amplitude (73-109 ct, 14-21 % of the ±511 clamp), Path 1 alone
  contributes **73-109 / 208 (V87's measured engaged median `|gp-0x6b98|`) ≈ 35-52 %** of a typical
  delivered command's magnitude — a substantial fraction even before any dose, structurally.
- A dose at the safety ceiling recorded in [[reference_accord_fun36c12_sign_settled_dissipative]]
  (×3, from the 1.56× clamp-binding margin and the int16 rail at ×4) would, via Path 1 alone,
  raise this contribution toward the full ±511 ceiling more often (duty rises — `dose_headroom`
  above quantifies exactly how much once V90's real distribution lands), **not** an unboundedly larger
  torque — the clamp is hard and dose-invariant.

**Qualitative direction the driver should expect, stated without a magnitude**: this is an added,
speed-shaped, rate-derivative-proportional resistive term entering additively (Path 1) on top of
Honda's own assist — the standard cost of any viscous-style damper, i.e. added steering effort
specifically during fast wheel-rate transients (which is where `gp-0x6c2c`'s gain rises, 3.08×@7.79 Hz
to 9.26×@28 Hz), largest at low speed (`k`=0.160 @0 km/h vs 0.032 @90 km/h, per Honda's own schedule)
and near-zero during slow, steady turns (the differencer has near-zero DC gain). **This matches the
"heavier wheel at creep" cost the operator reported for other dissipative-class levers in this kit
(V86B: "extra dampening on LKAS and in general at slow speed") — the same qualitative cost should be
expected here, unquantified in N·m.**

---

## ADDENDUM 1 — census re-confirmation, `0xC63A6`, and the band-aware dissipative-fraction table

### Census re-confirmed independently, from scratch, with a new adjudicated false positive

Re-ran the whole census as a fresh raw Python byte scan (not reused from above), set-differenced
against Ghidra. **Result unchanged: 1 writer (`0x36cf0`), 4 readers (`0x36ce4` self-shadow,
`0x36d78` DTC monitor, `0x3815c` Path 2, `0x3ac98` Path 1).** The raw scan surfaced **one more raw hit
Ghidra's `search_instructions` correctly excludes**: `0x0614A2`, bytes `bfffda94`. Disassembled with
`dry_run:true` — it is the tail two bytes of a single 4-byte `jarl 0x0005a97c,lp` (Format-V) inside
`FUN_0006129a`, a coincidental encoding collision, not a real access. Pointer-indirect (LE32 absolute
address `0xFEDF14DA`) and register-indirect (`movhi 0xFEDF` + `disp=0x14DA`) forms both checked and
return zero. **`gp-0x6b26` reaches the motor via Path 1, independent of the observer/residual chain —
it is NOT observer-only.**

### `0xC63A6` — verdict: interlock-immune (confirmed), but Path-2-only, and it IS structurally kin to K1

Full disassembly of `FUN_00038148` pulled (`0x38148-0x382d6`). Instruction-level confirmation of the
gate-before-weight claim:

```
0003815c: ld.h  -0x6b26[gp],r6        ; r6 = gp-0x6b26 (RAW)
00038184: addi  0x400,r6,r7           ; window test on the RAW value
00038188: addi  -0x801,r7,r0
0003818c: cmovc 0x0,r6,r10            ; r10 = gate(r6): 0 if |r6| would exceed ~1024, else r6 UNCHANGED
   ...
000381ca: ld.hu 0x73a6[tp],r15        ; r15 = cal(0xC63A6) -- loaded AFTER the gate already ran
000381ce: mul   r15,r10,r0            ; weight applied to the ALREADY-GATED r10
000381d2: sar   0xa,r10
000381d4: add   r12,r10               ; accumulate into the running SUM_6ch
```

**Confirmed exactly as hypothesized**: the gate depends only on the raw `gp-0x6b26` value (already
bounded ±511 by `0xC407E`, always inside the ±1024 window regardless of `0xC63A6`), and the weight
multiply happens strictly after — `0xC63A6` cannot move the gate, and (independently, from Q3) the
DTC monitor reads `gp-0x6b26` directly, upstream of `0xC63A6` entirely. **`0xC63A6` is genuinely
interlock-immune, mode-proof (bare `tp` scalar, `0x73A6`, no `+mode*4` anywhere near it), and its own
census is now closed the same way**: fresh raw Python disp16 scan for `tp+0x73A6` (positive
displacement, both the natural and `disp|1` encodings) finds **exactly 1 hit, `0x381CA`**, matching
Ghidra's `search_instructions` (2 raw hits, 1 real + 1 adjudicated branch-text false positive at
`0x473a0`). Zero writers anywhere (expected — `tp`-relative reaches the cal ROM, not RAM). **Team-lead's
"1024 on 87/87, never moved" claim is architecturally consistent with a virgin cal cell that has these
census properties — I did not re-derive the 87-image sweep myself, but the single-reader/zero-writer
structure is exactly what a truly-untouched cal cell should show, and it does.**

**But — pulling the rest of `FUN_00038148`'s disassembly settles the "is this K1 the other way"
question too, and the answer is a real, instruction-verified YES for its DIRECTION, on Path 2 only:**

```
000381fe: ld.w  -0x374c[gp],r6        ; EMA state (previous)
0003820c: shl   0x4,r14               ; new_term << 4
0003820e: sub   r6,r14                ; delta = new*16 - old_state
00038210: mul   r13,r14,r0            ; * alpha (0xC63AC)
00038220: sar   0xa,r14
00038222: add   r14,r6                ; new EMA state = old + delta*alpha>>10
00038230: st.w  r6,-0x374c[gp]        ; store
00038236: sar   0x4,r6                ; >>4  (cancels the earlier <<4)
00038238: subr  r15,r6                ; r6 = gp-0x6bfe - EMA_state    <-- resid, MINUS the SUM_6ch term
0003823a: add   r9,r6                 ; += gated gp-0x6bfa
```

`resid = gp-0x6bfe − EMA(SUM_6ch·polarity·2639) + gp-0x6bfa` — **raising `0xC63A6` increases
`SUM_6ch`'s `gp-0x6b26` contribution, which is SUBTRACTED here, so (holding polarity`=+1`, the
literal-`±1` value every `gp-0x6752` store writes) raising `0xC63A6` REDUCES `resid`.** Separately,
raising K1 (`FRICTION`, inside `FUN_0003b8f6`) reduces `gp-0x6bfc` directly (`model − FRICTION −
INERTIA`, more subtracted ⇒ smaller), which becomes `gp-0x6bfe` via a near-pass-through plausibility
check, which ALSO reduces `resid` (it's the minuend here). **Both act in the SAME direction on `resid`
— confirmed by instruction-level arithmetic, not inferred.** This is the same node V89's K1 already
flew and measured **flat** (band contrast 0.947 [0.827, 0.979], inside its own placebo band).

**The shape distinction is real, and applies squarely to Path 2, not just Path 1**: K1's `FRICTION` is
gated by a relay (`ratio`, saturates at 50 ct of rectified rate) multiplying **`|model|` — the
delivered COMMAND magnitude** — V89 measured `|friction|≥0.0625` at **0.000 at <1°/s, 0.009 at
1–13°/s** (the operator's own micro-ratcheting regime), i.e. near-zero exactly where he names the
symptom, because it's gated by command magnitude, not rate. `gp-0x6b26`'s Path-2 contribution is
gated by `gp-0x6c2c`, a genuine rate-derivative signal with **no command-magnitude gate at all** — it
is non-zero at essentially any rate transient, including ones where the delivered command is small.
**This is a real, defensible distinction on WHEN each term is non-zero, but it does not change that
they share the same downstream node and act in the same direction there.**

⇒ **Recommendation, reconciling both findings**: `0xCBE74` is the stronger, more independent lever —
it drives BOTH Path 1 (untouched by anything V89 ever flew, zero phase, weight exactly 1) AND Path 2
(kin to K1 in direction, but different in gating shape). `0xC63A6` alone drives ONLY Path 2 — its
entire contribution shares V89's already-flown-flat node, and its independence rests entirely on the
gating-shape argument above, which is real but weaker than Path 1's clean independence. **If a build is
cut, `0xCBE74` is the more defensible single lever; `0xC63A6` is a legitimate SECOND, INDEPENDENTLY-SAFE
knob for isolating Path 2's contribution specifically (e.g., to separate Path 1 from Path 2's
effect empirically), not a reason to prefer it over `0xCBE74`.**

### Band-aware dissipative fraction, 2–35 Hz, from a clean z-domain transfer function [EVIDENCE]

`H(f) = 64·H1(f)·(1−z⁻¹)·H2(f)`, `H1`/`H2` the two confirmed EMA poles (`α0=37/128`, `α2=22/64`),
evaluated at `z=e^{j2πf/fs}`, `fs=1000`. This is `gp-0x6c2c(f)/rate(f)` exactly, no time-domain
simulation ambiguity. **Cross-checked two ways**: (1) the resulting angle **exactly reproduces** the
inherited Leg-3 table (`76.43°/54.63°/44.31°/9.74°/−11.96°/−24.97°` at 7.79/21.09/28.1/60/100/200 Hz,
matching to 2 decimals) once the algebra is worked through (`gp-0x6b26 = −k·gp-0x6c2c` with `k>0`
contributes a further, constant 180°, and the reference damper `gp-0x6bd0 = −sign(rate)·|·|` has its
OWN fundamental 180° from rate — the two 180°s cancel, so **"deviation from the calibrated dissipative
reference" equals `phase(gp-0x6c2c/rate)` directly, unnegated** — this is exactly the angle Leg-3
reported); (2) it reproduces your own `cos(76°)=0.242` / `cos(44°)=0.719` to 3 decimals.

| f (Hz) | \|H\| rel. DC | deviation angle | **dissipative fraction** cos(θ) | **reactive fraction** \|sin(θ)\| | Re(H) | **M_rel vs 7.79 Hz** |
|---|---|---|---|---|---|---|
| 2.00 | 0.803 | 86.5° | 0.061 | 0.998 | 0.049 | 14.72 |
| 3.00 | 1.203 | 84.8° | 0.092 | 0.996 | 0.110 | 6.56 |
| 5.00 | 1.997 | 81.3° | 0.152 | 0.988 | 0.303 | 2.38 |
| **7.79 (ratchet)** | **3.080** | **76.4°** | **0.235** | **0.972** | **0.723** | **1.00** |
| 9.00 | 3.539 | 74.4° | 0.270 | 0.963 | 0.954 | 0.76 |
| 12.00 | 4.639 | 69.3° | 0.354 | 0.935 | 1.642 | 0.44 |
| 15.00 | 5.676 | 64.3° | 0.434 | 0.901 | 2.461 | 0.29 |
| 18.00 | 6.639 | 59.5° | 0.508 | 0.861 | 3.374 | 0.21 |
| **21.09 (grind #1)** | **7.546** | **54.6°** | **0.579** | **0.815** | **4.369** | **0.165** |
| 24.00 | 8.318 | 50.2° | 0.640 | 0.769 | 5.321 | 0.14 |
| **28.10 (grind #2)** | **9.267** | **44.3°** | **0.716** | **0.699** | **6.631** | **0.109** |
| 32.00 | 10.021 | 39.0° | 0.777 | 0.629 | 7.788 | 0.09 |
| 35.00 | 10.507 | 35.1° | 0.818 | 0.575 | 8.594 | 0.08 |

**`M_rel` = the multiplier needed at 7.79 Hz to deliver the SAME dissipative torque (in `gp-0x6b26`
counts, at gp-0x6b26 itself, Path 1) that ×1 delivers at that row's frequency** — i.e. `Re(H(7.79))
/Re(H(f))`. **Reading it your way: to match grind #1's (21.09 Hz) dissipative delivery, the ratchet
band needs `1/0.165 ≈ 6.1×` MORE gain than grind #1 does; to match grind #2 (28.1 Hz), `1/0.109 ≈ 9.2×`
more.** This is close to, and somewhat larger than, your "~4×" estimate — **[EVIDENCE for the ratio
itself]**, computed from the confirmed taps, not eyeballed.

🛑 **This ratio is plant-independent (the unmeasured `gp-0x6b98→column` transfer cancels out of a
ratio between two frequencies, AS LONG AS that plant's own gain/phase is roughly flat between the two
compared frequencies — an assumption, not verified, since the plant is exactly what's unmeasured).**
It covers Path 1 only (flat 1.066 DC gain, no extra shaping, so `M_rel` above transfers directly to
Path 1's contribution at `gp-0x6b98`). Path 2 needs its own frequency-dependent correction through the
gain-scheduled PID on top of the already-known referral trend (×2.336/×1.601/×1.318 to `gp-0x6b70` at
7.79/21/28 Hz — same qualitative direction, not yet reduced to one number).

### GATE-2: what the dominant reactive component DOES at 7.8 Hz — a real risk, sign not resolved

At 7.79 Hz the term is 97.2% reactive, 23.5% dissipative. **Working out what "reactive, deviation ≈
+90° from the reference" means physically**: the reference direction (0° deviation) is 180° antiphase
with rate (`gp-0x6bd0`'s own relay character, a textbook `F=−cv` damper). A +90° deviation from that
lands the force at phase **−90° relative to rate itself** — which is **in phase with `−dv/dt`**, i.e.
**`F ∝ −acceleration`, the classic form of an INERTIAL reaction force.** ⇒ **[reasoned extension,
consistent with, not independently re-deriving, the sibling `(J+k)α=T_driver` memory already on
file]: the dominant component at 7.79 Hz behaves as ADDED APPARENT INERTIA, not damping.**

**Why that is a real GATE-2 risk for a Q14–29 lightly-damped mode, not a nicety**: for a simple
resonance, `ω0 = √(k_stiff/J)` and `ζ = c_phys/(2√(k_stiff·J))`. **Adding inertia `ΔJ` at fixed
physical stiffness and fixed physical damping LOWERS both `ω0` AND `ζ`** — the mode gets slower *and*
less damped from the inertia term alone, and the SMALL genuine dissipative part (23.5%) has to
overcome that `√J` penalty on top of adding its own damping. **I cannot sign the net effect** — it
depends on the column's actual `J`/`c`/`k_stiff`, none of which are on file (same "unmeasurable plant"
limitation as Q2/Q5) — but the STRUCTURE of the risk is now precise: **a large dose at 7.79 Hz is not
simply "some damping, safely"; it is "a little damping bundled with a larger inertia term whose sign
of net effect on ζ is unresolved."** ⇒ **This favors sizing any dose toward the higher end of the
band (21–28 Hz, where dissipative fraction is 58–72% and reactive is a minority, not 97%) if the goal
is grind #1/#2, and argues for real caution — not a block, but a flagged unknown — if any dose is
specifically aimed at the 7.79 Hz ratchet.**

### `dose_headroom()` against the REAL V90 distribution — team-lead's arithmetic independently reproduced, one nuance added

V90 (route 77, 62,180 frames, 0.000% CAN saturation): `MOTOR_TORQUE` p50/p95/p99/max = 3/34/67/199 ⇒
`|gp-0x6b26|` (×8/5) = **4.8 / 54.4 / 107.2 / 318.4**. Feeding these into `max_multiplier_for_pin_duty`
reproduces your numbers exactly: **M≤1.605 (zero pin, off the route max) / M≤4.767 (pin<1%, off p99) /
M≤9.393 (pin<5%, off p95)** — **your arithmetic is correct, nothing to fix.**

**One nuance, from `dose_headroom`'s DF output, not a correction**: at `M=4.77` (the "<1% pin" choice,
sized off `p99`), the describing-function gain evaluated at the ROUTE MAX is already down to **0.42**
— i.e. the single largest sample on this 17.9-minute route would be substantially compressed at that
dose, even though the typical (p99) frame is exactly at the rail boundary and nothing beyond. **A
single route's observed max is a sample statistic, not a proven ceiling** — a longer or more varied
drive could produce a larger transient than 318.4 ct. **Recommend sizing off `p99` with a margin
factor (e.g. M≤3, giving DF@max=0.65, DF@p99=1.00) rather than treating the observed max as a hard
bound**, until more exposure (esp. the wheel-rate-split percentiles you've already asked for) is in.

⚠ **Adopted without independent re-derivation, per your instruction**: the corrected 12-engaged-mode
set `{2,3,5,10,11,14,15,17,23,26,27,29}` (includes m10, excludes m24) and the `_v76_v38base_relu_damper`
= 0 changed friction modes / other V76 file = 12 changed modes distinction — I did not re-run the
34-mode dereference myself this round; my own Q3 table above used the "14 sites / 13 engaged + m10"
figure from my own fresh V73–V77 diff, which is internally consistent for THOSE FIVE BUILDS specifically
(independently re-derived from the actual image bytes, not inherited) but I have not reconciled it
against the other agent's full 87-image, 34-mode sweep. **If the two disagree on the V73–V77 builds
specifically, that needs a direct byte-level reconciliation before either is trusted over the other —
flagging, not resolving.**

## Summary for the operator

1. **`0xCBE74` (the friction/comp gain table, `gp-0x6b26`'s lane) is SAFE to dose at any multiplier
   with respect to the DTC-0x1d hard-fault monitor, as long as `0xC407E` is left at 511.** The V74/V75
   faults required `0xC407E` to be raised past 512 first; the gain dose alone cannot reach that
   monitor because the clamp binds strictly upstream of it, unconditionally.
2. **`gp-0x6b26` has a direct, unweighted Path-1 route straight into the motor-command aggregator**,
   parallel to and structurally identical to the already-flown-and-killed damper `gp-0x6bd0` — new
   finding this session, previously the lane was described only via its slower Path-2 route.
3. **`0xC646E` (INERTIA) looked like a second candidate and is NOT one** — it shares FRICTION/K1's
   sign-inverting observer mechanism, so raising it likely makes the wheel LIGHTER, the opposite of
   the intended effect. Do not propose it.
4. **`gp-0x6b26` remains the only live, correctly-signed, cal-only, not-yet-killed candidate** for
   added damping in this class; r24/r26 (Lever A/B) is already at its measured ceiling, and `gp-0x6bd0`
   is a known relay hazard.
5. **Sizing is ready the moment V90's telemetry lands** — `dose_headroom()` and
   `max_multiplier_for_pin_duty()` above take the real `|gp-0x6b26|` distribution directly; both are
   sanity-checked against the kit's own recorded DF figures (reproduces 1.000×@×4 / 0.881×@×6 exactly).
6. **No N·m figure can be produced honestly** — the `gp-0x6b98 → column` plant is unmeasured on this
   car and I am not inventing a conversion constant.

Cave/build policy: **no cave is needed or proposed for any of this** — a dose is a pure calibration
edit to `0xCBE74`'s Y-arrays (already-existing records, same-size in-place edit) with `0xC407E`
explicitly asserted unchanged in the build script. GATE 1 (RAM ownership) is closed above. GATE 2
(sign, both paths) is closed above; GATE 2 (magnitude/stability margin) is bounded by the DF/pin-duty
functions in Q2 once real telemetry exists, not before.

## ADDENDUM 2 — 🛑 NEW SAFETY FINDING: an intermediate int32 overflow inside `FUN_00036c12`'s own arithmetic, quantified

While checking the int16 Y-storage headroom (team-lead's `×3.333` figure), I traced the arithmetic one
level deeper via raw P-code (`get_function_pcode`) — this is NOT visible from the C-level decompile,
which renders it as an ordinary-looking multiply chain.

```
0x36cbe: mulh r12,r13     ; iVar4a = sVar7 * gate(gp-0x6c2c)   -- P-CODE CONFIRMED: BOTH operands
                          ;   sign-extended to 32-bit FIRST (two INT_SEXT ops), then a 32x32->32
                          ;   INT_MULT. NOT a 16-bit-truncating multiply (my first hypothesis, based
                          ;   on the `mulh` mnemonic, was WRONG -- checked via raw P-code, not asserted).
0x36cc6: mul  r13,r6,r0   ; iVar4 = iVar4a * 0x111 (273)  -- P-CODE CONFIRMED: 32x32->32 INT_MULT,
                          ;   keeps only the low 32 bits (r0 = high half, discarded). STANDARD 2's-
                          ;   complement wraparound applies if the true product exceeds int32 range.
```

**This second multiply CAN overflow.** Solving `(Y_dosed·|gp-0x6c2c|) >> 6 · 273 > 2³¹−1` for
`|gp-0x6c2c|`:

| dose M | `Y_dosed` max | **overflow threshold on `\|gp-0x6c2c\|`** | vs its own producer ceiling (32000) |
|---|---|---|---|
| 1 (stock) | 9830 | 51,215 | 160% — **unreachable, producer clamp is tighter** |
| 1.6 | 15,728 | 32,009 | ≈100% — the producer's own ceiling |
| 2 | 19,660 | 25,607 | 80% |
| 3 | 29,490 | 17,072 | 53% |
| 3.333 (int16 ceiling) | 32,763 | 15,366 | 48% |

**At stock gain this is provably unreachable** (`gp-0x6c2c`'s own clamp is 32000, below the 51,215
overflow threshold — Honda's calibration has margin here, whether by design or accident). **Once
`M` exceeds ≈1.6, the overflow threshold drops below `gp-0x6c2c`'s own coded ceiling — reachable in
principle, if not necessarily in practice.**

**Cross-checked against realistic/measured `gp-0x6c2c`, inferred from V90's real `|gp-0x6b26|`
percentiles (`|gp-0x6b26| ≈ k(speed)·|gp-0x6c2c|`, `k ∈ [0.032, 0.160]` — using the LEAST sensitive row
as the conservative/larger-implied-gp6c2c case):**

| percentile | measured `\|gp-0x6b26\|` | implied `\|gp-0x6c2c\|` (worst-case row) |
|---|---|---|
| p99.9 | 184.7 | 5,772 |
| **max (17.9 real minutes)** | **319.1** | **9,972** |

**At `M=3`, the overflow threshold (17,072) is only 1.71× above the measured max-implied `gp-0x6c2c`
(9,972) — a real but not generous margin, comparable to other margins this kit has flagged as
load-bearing (e.g. the 1.56× clamp-binding margin already on record).** At `M=2` the margin widens to
2.57×. **I have NOT proven `gp-0x6c2c` can never exceed ~10,000 in some rarer or fault-adjacent
transient** (RULE 11's own lesson: a "practically unreachable" bound in this firmware has been wrong
before) — this needs either a direct measurement of `gp-0x6c2c`'s own real-world distribution (not yet
telemetered on any build) or an explicit decision to accept the margin as computed. **Flagging, not
resolving** — this is a GATE-1-adjacent arithmetic-safety question, structurally independent of the
DTC-0x1d/`0xC407E` story, and it was not on record before this session.

**What an overflow WOULD do, if triggered**: `iVar4` wraps to an arbitrary 32-bit value via standard
2's-complement overflow (not a clamp, not a saturate — a genuine sign-unpredictable wrap), which then
feeds the `>>0x12` and the `0xC407E` clamp COMPARISON itself — a wrapped value could in principle
produce a `gp-0x6b26` sample that does NOT reflect the intended clamped magnitude for that one tick
(self-correcting the next tick, since the lane has no memory of a single bad sample beyond the
shadow-lockstep check, which would itself very likely trip on such a sample and invoke `FUN_0006b9fa`).
**Likely self-limiting for a single-tick event, given the existing shadow-lockstep and DTC-0x1d checks,
but not zero-risk, and not yet closed.**

## ADDENDUM 3 — the operator's own question, and the sizing verdict (Q-A/Q-B)

### Does `0xCBE74` limit LKAS's top steering rate? NO — `H(0)=0` exactly, proven three ways

`H(f)=64·H1(f)·(1−z⁻¹)·H2(f)`: at DC, `H1(1)=α0/α0=1`, `H2(1)=α2/α2=1`, `(1−z⁻¹)|_{z=1}=0` exactly ⇒
`H(0)=0`. Confirmed numerically (`|H|/f` constant at 0.402 from 0.1–2 Hz) and, most conclusively, by
feeding the exact integer cascade a perfectly constant rate: `y0` converges, `d=y0[n]−y0[n−1]=0`
identically (no rounding residual survives, even accounting for the fixed-point EMA's own convergence
dead-zone), so `gp-0x6c2c=0` exactly at any sustained rate. **Simulated a realistic 50–100°/s ramp
through the exact cascade**: steady-state `gp-0x6c2c=0` in every case; peak DURING the ramp (0.2–1.0s
onset) is 27–125 counts, translating through Path 1 to **0.85–6.4% of the 208ct engaged median
command, lasting under ~70ms, then gone.** Not a rate limiter — a brief transient nudge on the ramp.

**Contrast**: the FactorC/E base-assist damper is indexed on RATE ITSELF (FactorE's own rate table),
so it delivers continuous opposing torque for as long as a fast turn is held — the opposite of this
lane in exactly the relevant respect.

**Historical pin**: fresh byte reads confirm V74/V75 both carried `0xC63A0` (damper Path-2 weight)
doubled 1024→2048 alongside the friction dose. **V81** (`_v81_C407E.511-FRICTION.STOCK_plain_image.bin`,
the build cut specifically to fix the faults) — checked directly: friction lane (`0xCBE74` m26) fully
reverted to stock `(-9830,-5734,-1966)`, `0xC407E`=511 reverted, **but `0xC63A0` still 2048 and FactorC
m26 `Y[0]` still 566 (stock=0) — the base-assist damper was fully live and undisturbed.** If the
operator's memory of "we fixed the faults and it turned out to just be a damper" is V81 (the only
fault-fix build that actually flew), the mechanics say it can only have been the FactorC/E damper.

### Q-A: clip envelope forces ≈×1.5–1.6, and it is Honda's own clamp, not a new relay

`dose_headroom` DF-vs-multiplier on the real route-77 array: DF≈1.000 at ×1.5–1.6 (clip-free, matches
the measured 478.7/510.6 ct peaks), DF@max=0.896 at ×2.0 — flat across the great majority of the range,
mild compression only at the extreme tail. **Not relay behavior** (V80's DF ROSE as amplitude fell —
opposite signature). `0xC407E` is Honda's pre-existing clamp, present and doing this at M=1 too; a dose
makes it bind somewhat more often, it does not introduce a new failure mode — the kerb-strike
counter-argument holds structurally.

### Q-B — THE DECISIVE FINDING: at ×1.5, delivered damping is below the 11% resolvability floor in EVERY band

| band | measured band rms | diss. frac | added `gp-0x6b26` (×0.5) | damping component | at `gp-0x6b98` | % of 208ct median | vs 11% floor |
|---|---|---|---|---|---|---|---|
| 6–9 Hz | 2.74 ct | 0.226 | 1.37 | 0.31 | 0.33 ct | **0.16%** | 69× below |
| 18–22 Hz (15–22 proxy) | 8.42 ct | 0.555 | 4.21 | 2.34 | 2.49 ct | **1.20%** | 9× below |
| 26–31 Hz (model-extrapolated) | 11.59 ct | 0.722 | 5.80 | 4.19 | 4.46 ct | **2.15%** | 5× below |

26–31 Hz extrapolated from the 15–22 Hz measurement via `|H|` ratio; cross-validated against all four
measured bands (2–4/6–9/9–12/15–22 Hz), model accuracy 0.50×–1.37× — **even at the high end of that
error range the 26–31 Hz answer only reaches ~2.9%, still 4× below the floor. Conclusion is robust to
the extrapolation uncertainty.** The column-domain comparison (`e_6-9`, `e_18-22`) could not be done
honestly — it needs the unmeasured `gp-0x6b98→column` plant; the command-domain comparison above is the
apples-to-apples version of the same question and it answers it.

**⇒ RECOMMENDATION: do not fly `0xCBE74` as a dose.** At the multiplier the clip envelope permits
(~×1.5), delivered damping is underpowered by construction in every band, by 5–69×. Combined with the
clip ceiling forcing ×1.5, the two latched faults with zero clean flights separating the dose from the
`0xC407E` interlock, the 97%-reactive risk to ζ at 7.79Hz, and the lane's own prior strike — five
independent reasons. This closes the DampAxis line of work for this session.

## Summary for the operator, ADDENDUM 1

7. **`gp-0x6b26` reaches the motor via Path 1, confirmed by two independent census methods with every
   disagreement adjudicated — it is NOT observer-only.**
8. **`0xC63A6` (the friction lane's weight in `FUN_00038148`) is genuinely interlock-immune**
   (instruction-confirmed: the ±1024 gate is evaluated on the RAW `gp-0x6b26` value, before the weight
   multiply ever runs) **but only reaches Path 2** — its full effect shares V89's already-flown-and-
   measured-flat node (both raising K1 and raising `0xC63A6` reduce the same `resid`, confirmed
   instruction-by-instruction), differing only in WHEN each is non-zero (K1: command-magnitude-gated;
   `gp-0x6b26`: rate-derivative, ungated). **`0xCBE74` remains the stronger single lever**; `0xC63A6` is
   a legitimate isolation tool for separating Path 1 from Path 2, not a reason to prefer it alone.
9. **Real V90 telemetry now exists and the team-lead's sizing arithmetic checks out exactly**
   (M≤1.61/4.77/9.39 for zero/1%/5% pin duty off max/p99/p95) — added nuance: size off `p99` with
   margin, not the single-route observed max.
10. **Band-aware sizing, computed fresh from the confirmed taps**: the ratchet (7.79 Hz) needs
    **~6.1× more gain than grind #1 (21 Hz) and ~9.2× more than grind #2 (28 Hz)** to deliver the same
    dissipative torque via Path 1, because 76–92% of the lane's output at 7.79 Hz is a REACTIVE,
    inertia-like component, not damping. **This is a real GATE-2 caution for the ratchet specifically**:
    added apparent inertia at fixed physical stiffness/damping LOWERS both the resonant frequency and
    ζ of a lightly-damped mode, so a 7.79 Hz-aimed dose bundles a small guaranteed damping gain with a
    larger, sign-uncertain risk to the mode's own Q. **This lane is structurally a better-supported bet
    for grind #1/#2 than for the ratchet.**
