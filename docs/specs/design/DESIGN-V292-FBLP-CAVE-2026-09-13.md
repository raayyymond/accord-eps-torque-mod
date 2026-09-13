# DESIGN — V292: the error-feedback feedback-lag cave

**Agent:** `cavedesign` (firmware-codepath-tracer), subagent of `main`. **Date:** 2026-09-13.
**Status:** DESIGN ONLY. Nothing built, nothing flashed, nothing sent, no build script edited.
**Base:** V291 (C10), `_v291c10_…_plain_image.bin`, SHA256 `a66f9c54b21031d3948cf1f60fbcadc6ac44d422c01d5a357b19aa0d23144657`.
**Mirror:** `rlog-tools/studies/grind/v292_cave_mirror.py` (importable; `python …` runs the five proofs
and writes `_scratch/v292_cave_mirror.txt`).
**Tooling:** GhidraMCP for every disassembly (`disassemble_bytes dry_run:true`, `search_instructions`,
`get_bulk_xrefs`); raw-Python LE byte scans for every load-bearing count or null, each positively
controlled before its null was trusted. No mutating Ghidra call was made; nothing was saved to the
shared project.

Every claim below is marked **EVIDENCE** (with the address and the method) or **BELIEF**.

---

## 0. The one-paragraph version

V291 (C10) lowered the LKAS feedback-lag pole to 9.94 Hz by moving the cal pair
`0xC63E8 / 0xC63EA` from `(923, 1560)` to `(962, 958)`. Adversary B found that the smaller `b`
widens the filter's input quantiser from 0.66 to 1.07 raw counts, so at the 1–3 count wheel rates of
a grinding episode the feedback under-reads and the closed loop's steady state departs from its own
linear DC by ×1.34–1.80 (`ADV-V291-B-LOOP-2026-09-13.md` §5.2, §11.4). **V292 keeps the pole cells
byte-identical — the pole stays cal-visible — and fixes the quantiser instead**, by carrying each
`sar 0xa` floor's residue into the next tick in a 52-byte cave. The mean input gain becomes exactly
`b/1024` and the mean decay exactly `a/1024` at **every** amplitude, so the integer filter's mean
behaviour equals its linear model's. Measured: the closed-loop steady state at the B4 clause's own
operating point goes from ×1.4155 to **×1.00000**.

**The mechanism, stated plainly, because it is bigger than "a quantum of 1.07 counts":** each of the
two floors loses half an LSB per tick on average, the state integrates that loss to
`0.5·1024/(1024−a)` counts per term, and the two-sample sum doubles it. On C10 that is a **constant
−32-count DC offset** on the feedback signal, at every amplitude (measured: −32.67, −31.21, −32.24,
−32.93, −32.44 at A = 1, 3, 8, 64, 512). Against `E = 32·sp − fb`, a −32 offset in `fb` is **+32
counts of phantom error — one whole extra setpoint count, permanently.** At `sp = 3` (E = 96 nominal)
that is +33 % of demand. V282's own bias is −20 counts, which is why V282 is the smaller offender
rather than an innocent one.

---

## 1. The arithmetic

### 1.1 What V291 executes today

`disassemble_bytes(0x28F5E, 104, dry_run:true)` on `code.bin`; byte-identical in the V291 image
(§4.3). **EVIDENCE.**

```
28F86  ld.hu 0x73ea,tp,r16      b = [0xC63EA] = 958    UNSIGNED (cap 65535)
28F8A  ld.h  0x73e8,tp,r9       a = [0xC63E8] = 962    SIGNED   (cap 32767)
28F8E  mul   r16,r7,r0          r7 = low32(x * b)      <-- THE HOOK SITE
28F92  mul   r26,r9,r0          r9 = low32(s * a)
28F96  ld.hu 0x72e6,tp,r13      clamp = [0xC62E6] = 46080
28F9A  sar   0xa,r7             step_b = floor(x*b / 1024)      <-- floors toward -inf
28F9C  ld.hu 0x72e6,tp,r14      clamp again
28FA0  sar   0xa,r9             step_a = floor(s*a / 1024)      <-- a SEPARATE floor
28FA2  add   r7,r9              s_new = step_a + step_b         <-- THE RETURN POINT
28FA4  add   r9,r26             out = s_old + s_new
28FA6  cmp   r13,r26
28FA8  st.w  r9,-0x3d30,gp      s := s_new   (32-bit state cell)
28FAC..28FBC                    clamp out to +-[0xC62E6]
```

### 1.2 What V292 executes

```python
t_b = x * b + rem_b ;  step_b = t_b >> 10 ;  rem_b = t_b & 0x3FF
t_a = s * a + rem_a ;  step_a = t_a >> 10 ;  rem_a = t_a & 0x3FF
s_new = step_a + step_b          # 0x28FA2, unmodified Honda code
out   = s_old + s_new            # 0x28FA4, unmodified Honda code
```

`t & 0x3FF` **is** `t − ((t >> 10) << 10)`, exactly, for two's-complement `t` of either sign, because
arithmetic shift right satisfies `t == ((t >> k) << k) + (t & (2**k − 1))`. Worked both ways:
`t = −1025` → `sar 10` = −2, `−2<<10` = −2048, `t − (−2048)` = 1023; and `(−1025) & 0x3FF` =
`0xFFFFFBFF & 0x3FF` = 1023. ✔ **One `andi` replaces `mov`/`shl`/`sub` — 4 bytes instead of 6, and it
is the reason the cave fits in 52 bytes.**

### 1.3 Why the mean becomes exact

```
step_b[n] = (b·x[n] + rem_b[n−1] − rem_b[n]) / 1024
```

Summing telescopes: `Σ step_b = (b·Σx + rem_b[0] − rem_b[N]) / 1024`, with `rem` bounded in `[0,1023]`.
The same holds for `step_a`. Writing `S_N = Σ_{1..N} s[n]`:

```
(1024 − a)·S_N = N·b·x + a·(s[0] − s[N]) + (bounded)      ⇒   mean(s) → b·x/(1024 − a)
mean(out) = 2·mean(s) → 2·b·x/(1024 − a)   EXACTLY, at every amplitude, x = ±1 included.
```

Equivalently: the quantisation error is a **first difference** of a bounded sequence, i.e.
`(1 − z⁻¹)`-shaped. It carries **exactly zero DC** and is bounded by 1 LSB per term.

---

## 2. The five proofs

All from `rlog-tools/studies/grind/v292_cave_mirror.py`. Python's `>>` on `int` floors toward −∞,
matching V850 `sar`; every filter value below is an exact integer computation, not a float model.

### (i) Mean gain exact at every amplitude — **PASS**

Each constant `x` is driven to its eventual periodic orbit (the state space is finite: `s` bounded,
`rem ∈ [0,1024)`), and the mean of `out` over one full period is taken as an **exact rational**.

| x | V291 mean/x | V292 mean/x (exact) | V292 period | V292 − linear DC | V291 / linear |
|---|---|---|---|---|---|
| 1 | 0.000000 | 958/31 = 30.903225806 | 15872 | **0** | 0.0000 |
| 2 | 1.000000 | 958/31 | 7936 | **0** | 0.0324 |
| 3 | 11.333333 | 958/31 | 15872 | **0** | 0.3667 |
| 5 | 20.000000 | 958/31 | 15872 | **0** | 0.6472 |
| 8 | 25.000000 | 958/31 | 1984 | **0** | 0.8090 |
| 16 | 26.875000 | 958/31 | 992 | **0** | 0.8697 |
| 100 | 30.400000 | 958/31 | 3968 | **0** | 0.9837 |
| 1000 | 30.854000 | 958/31 | 1984 | **0** | 0.9984 |

**EXHAUSTIVE, both signs: `x = −1491…−1` and `1…1491` (2,982 amplitudes) — max
`|mean/x − 2b/(1024−a)| = EXACTLY ZERO`.** The negative side is included deliberately: that is where
V291's floor is biased.

⚠ **Above `|x| = 1491` the exactness stops, and it is not the quantiser.** The pre-existing
`±[0xC62E6] = ±46080` **output clamp** binds for `|x| ≥ C(1024−a)/(2b) = 1491` counts = 186.4 deg/s.
There V291 and V292 sit on the rail **identically** (both read 11.25 at x = 4096, 3.84 at x = 12000).
A first run of this proof reported "FAIL" on those two rows; the cause was diagnosed rather than
rounded away.

**The `s = −1` absorbing state is released.** Pre-existing on stock, V282 and V291: `floor(−a/1024) =
−1` for every `a < 1024`, so a negative state below the decay threshold never returns to zero.

| | s₀ = −1, x = 0, 200 ticks | s₀ = −500, x = 0 |
|---|---|---|
| V291 | rests at **s = −1**, `out` = −2 forever | **NEVER reaches 0** (stuck at s = −16) |
| V292 | rests at **s = 0**, `out` = 0 | reaches exactly 0 in **110 ticks** |

### (ii) First-tick response to a 1-count `x` step — **PASS vs V291; the clause as written does not apply to V282**

| | out[1] |
|---|---|
| V282 (a=923, b=1560) | 1 |
| V291 (a=962, b=958) | **0** |
| V292 | 1 on 958/1024 phases, 0 on 66/1024; mean **0.9355** |

- **vs V291 (same pole — the like-for-like comparison): PASS.** Never worse, strictly better on
  93.6 % of remainder phases. V291 answers a sustained 1-count input with 0 on 100 % of phases,
  forever.
- **vs V282: the brief's clause is NOT met deterministically, and I am not claiming it is.** V292's
  first tick is 0.9355 of V282's *in mean* — which is exactly `b/1024`, because the quantum is 1.07
  counts, not 0.66. It meets or exceeds V282's on 93.6 % of phases. **The clause compares two
  different poles**; the shortfall is the pole V291 deliberately chose, not the cave.

Cumulative response to a sustained 1-count `x` (V292 range over 128 sampled remainder phases):

| K ticks | V282 | V291 | V292 (min…max) | V292 min / V282 |
|---|---|---|---|---|
| 1 | 1 | 0 | 0…1 | 0.000 |
| 2 | 3 | 0 | 1…3 | 0.333 |
| 5 | 9 | 0 | 11…18 | **1.222** |
| 20 | 39 | 0 | 239…263 | 6.128 |
| 200 | 399 | 0 | 5658…5692 | 14.180 |

V292 overtakes V282 by tick 5 and V291 never leaves zero.

### (iii) Describing-function gain at 20.3 Hz — **PASS**

Integer sine input, fundamental of `out` divided by (fundamental of the integer input actually
applied × `|H_linear(20.3 Hz)| = 13.572178`). 1.00 = behaving exactly like the linear model.

| A (counts) | V291 gain (phase) | V292 gain (phase) | V292 \|err\| |
|---|---|---|---|
| 1 | 0.0735 (+60.29°) | **0.9995** (+0.16°) | 0.0005 |
| 2 | 0.7251 (−1.09°) | **1.0009** (−0.12°) | 0.0009 |
| 3 | 0.8561 (−5.89°) | **0.9998** (−0.03°) | 0.0002 |
| 5 | 0.9530 (−2.55°) | **0.9994** (−0.00°) | 0.0006 |
| 8 | 0.9807 (+0.17°) | **0.9996** (−0.01°) | 0.0004 |
| 16 | 1.0065 (+0.06°) | **0.9998** (−0.00°) | 0.0002 |

Worst `|gain − 1.00|` = **0.0009**, against a ±0.02 tolerance. Note the **phase** column too: V291
loses up to 60° of phase at A = 1 and 5.9° at A = 3 — an amplitude-dependent phase error inside a
loop whose stability margin is the whole point of C10. V292's is ≤ 0.16° everywhere.

### (iv) Byte-exact closed-loop steady state — **PASS at sp = 3 (the clause's own point) and sp = 330; MISS at sp = 33**

design290b's `Controller` with the feedback stage swapped for the cave; everything else (P, D, the
254/256 fade, the sum clamp, the output lag, the gain, the torque clamp) unchanged. Plant = the
family median fit (fp 21.49, zp 0.0989, τ 2 ms, f1 12.6, g0 0.0670, of 121 stable fits). 12,000
ticks, mean of the last 2,000.

| sp | V282 (ref) | V291 = C10 | V292 | V282 + cave (control) | V291/V282 | **V292/V282** |
|---|---|---|---|---|---|---|
| 3 | 0.26804 | 0.37942 | 0.26804 | 0.26219 | 1.4155 | **1.00000** |
| 33 | 3.10189 | 3.08251 | 3.05735 | 3.05470 | 0.9938 | **0.9856** |
| 330 | 30.81275 | 30.75805 | 30.69103 | 30.74615 | 0.9982 | **0.9960** |

- **`sp = 3` is the operating point `ADV-V291-B` names.** V291 = ×1.4155, inside the adversary's
  ×1.34–1.80 band. **V292 = ×1.00000 exactly. B4 is closed at its own operating point.**
- **`sp = 33`: V292 is 1.44 % low — OUTSIDE the brief's ±1 %. Reported as a miss.** The control
  column says why: V282's *own* cal pair with the same cave lands at ×0.9848, i.e. V282's integer
  reference is itself inflated ~1.5 % by ITS floor bias. V292 is within **0.09 %** of
  V282-with-the-same-correction. The ±1 % clause measures V292 against an uncorrected reference that
  carries the very bias V292 removes. **I am flagging this rather than redefining the clause to pass;
  the orchestrator should decide whether the corrected reference is the right target.**
- The tail is settled, not drifting: means over ticks 4000–6000 … 12000–14000 are 3.0558, 3.0560,
  3.0561, 3.0574, 3.0572 with std 0.026 — a stable ±0.04 deg/s ripple.

Peak wheel rate (transient authority — the cave does not change it in kind):

| sp | V282 | V291 | V292 |
|---|---|---|---|
| 3 | 0.4846 | 0.5975 (×1.233) | 0.4855 (**×1.002**) |
| 33 | 4.3241 | 4.8904 (×1.131) | 4.7954 (×1.109) |
| 330 | 37.0103 | 42.0579 (×1.136) | 41.9474 (×1.133) |

### (v) The linear part is unchanged, so every C10 gate carries over — **PASS**

**EVIDENCE:** the cal cells are byte-identical to C10 — `0xC63E8 = 962`, `0xC63EA = 958`, read from
the V291 image. The cave changes neither coefficient, neither multiply, the two-sample sum, the state
cell, nor the `±[0xC62E6]` clamp. It changes **only** how each `sar 0xa` disposes of its residue.

**DEDUCTION:** `gate73`, `Ms` and `pkR` are functions of `(a, b, structure)` only — the quantiser is
not represented in the linear model at all. Therefore **gate73 = 1.0099, Ms and pkR as scored for C10
are the same numbers for V292, not merely close to them.** No re-scoring is required. What V292
changes is the small-amplitude *nonlinear* behaviour, which those linear gates never measured.

**MEASURED** — each integer filter run against the exact linear filter in float alongside it, 20.3 Hz
sine, 20,000 scored ticks after a 10,000-tick warm-up:

| A (counts) | V292 − linear | V291 − linear (= C10 today) |
|---|---|---|
| 1 | mean **+0.0000** rms 0.6952 max 1.84 | mean **−32.6666** rms 10.2508 max 48.46 |
| 3 | mean **−0.0000** rms 0.6767 max 1.91 | mean **−31.2098** rms 5.3176 max 41.84 |
| 8 | mean **−0.0000** rms 0.5766 max 1.78 | mean **−32.2410** rms 2.1610 max 38.93 |
| 64 | mean **+0.0000** rms 0.5906 max 2.02 | mean **−32.9334** rms 1.7615 max 38.35 |
| 512 | mean **+0.0000** rms 0.5795 max 2.00 | mean **−32.4370** rms 2.2901 max 40.11 |

V292's mean deviation is zero to four decimals at every amplitude, rms under 0.7 counts, peak under
2 — exactly the ≤ 2-count bound §1.3 predicts. C10's is a constant −32-count offset. Arithmetic
check: `0.5·1024/(1024−962) = 8.26` per term × 2 terms × 2 (two-sample sum) = **33**. ✔

---

## 3. The hook

### 3.1 Site and displacement

| | |
|---|---|
| **Hook** | `0x28F8E`, the 4-byte `mul r16,r7,r0` (`f0 3f 20 02`) |
| **Replaced by** | `jr 0xC4C00` = `89 07 72 bc` (disp22 `+0x9BC72`) |
| **Return** | `jr 0x28FA2` = `b6 07 72 43` (disp22 `−0x9BC8E`), into Honda's own `add r7,r9` |
| **Displaced/skipped span** | `[0x28F8E, 0x28FA2)` — 6 instructions, all replicated in the cave |

### 3.2 🛑 The property that makes this site the right one: **zero new liveness claims**

The span `0x28F8E…0x28FA0` is **straight-line** — no branches in, none out — and it unconditionally
**writes** `r7` (@0x28F8E), `r9` (@0x28F92), `r13` (@0x28F96) and `r14` (@0x28F9C) **before reading
any of them.** Therefore those four registers are dead at the hook **by the original code's own
structure**, not by a liveness argument I had to construct. The cave's entire register footprint is
exactly that set `{r7, r9, r13, r14}`, and it restores `r13`/`r14` to their intended clamp values with
the two replicated `ld.hu` before returning.

**The cave never touches:**

| register | why it matters |
|---|---|
| `r25` | `0x290AC mov 0x1,r25` / `0x290C0 mov 0x0,r25`, tested at `0x29A60` — **a filter bail forces skip 2**, so the PID cannot run on a tick where the filter bailed. Disturbing it would break the coupling. |
| `r1` | `0x28F74 mov 0x1,r1`, stored to the sentinel at `0x290D4 st.b r1,-0x3d2c[gp]` |
| `r6` | sibling filter state, loaded `0x28F78 ld.w -0x3d34,gp,r6` |
| `r26` | `s_old` — read by the cave's second `mul`, consumed by Honda's `add r9,r26` at `0x28FA4` |
| `r16` | `b`, read by the cave's first `mul`; Honda overwrites it at `0x28FBE` |
| `r2`, `r10` | live **via the bail path only** (`cmp r2,r10` @0x290C8, `cmp lp,r10` @0x290D2) |
| `lp` | untouched ⇒ `jr`, never `jarl` |

**No PSW hazard.** The first flag consumer after the return point is `ble` @`0x28FAC`, armed by `cmp
r13,r26` @`0x28FA6` — both downstream of `0x28FA2`. The cave's `add`/`andi`/`sar` all set flags; every
one is overwritten before any consumer. Nothing between `0x28F8E` and `0x28FA2` in the original
carries a flag forward either (`mul` does not affect flags on V850E2).

**No ±12000 exposure.** The hook is **after** Honda's plausibility bail at `0x28F50`–`0x28F58`, which
tests `r7` while `r7` still holds the raw `x`. The cave's output never re-enters that test. This is
the decisive advantage over hooking at `0x28F4C`, where a cave substituting a value into `r7` would
put its own output through Honda's sensor-implausibility bail and would have to clamp to ±12000
(see `reference_accord_0x28f4c_rate_operand_hook_runs_every_tick`).

**Alternatives considered and rejected.** `0x28F92` (the second `mul`, also 4 bytes) has identical
properties but replicates one fewer instruction at no saving. `0x28FA2` (`add r7,r9`) is 2 bytes —
too short for a `jr`. `0x28F4C` requires a new ±12000 clamp and a larger liveness claim. **`0x28F8E`
is the right and essentially unique choice.**

### 3.3 Nothing branches into the span — **EVIDENCE, both methods**

- **Ghidra:** `get_bulk_xrefs` (direction `to`) on all 11 half-word addresses `0x28F8E…0x28FA2`
  returns **empty for every one**.
- **Raw Python** (`scratchpad/v292_census.py`): a Format-V (`jr`/`jarl`, disp22) + Format-III
  (`Bcond`, disp9) branch-target scan over `[0x13000, 0xC5000)` with the recorded traps applied —
  Format-V opcode field `0x1E` collides with `prepare`, so **odd targets are rejected**; opcode fields
  `0x3C/0x3D` and `0x3F` are shared with loads, so a candidate with **`hw2` bit 0 set is a load, not a
  branch**. Result: **25,418 distinct targets found, ZERO of them inside `[0x28F8E, 0x28FA2)`**, and
  `0x28FA2` is not itself a target from anywhere.
- **Positive control, 12/12 PASS** before that null was trusted: BAIL 4 (`jr 0x290B0` @0x28F62), the
  three engagement skips (`0x29A5C`/`0x29A64` → `0x2A164`, `0x29A70` → `0x2A0C6`), the function's own
  caller (`jarl 0x28EA6` @0x22522), and six `Bcond` targets inside the filter block.

---

## 4. RAM, flash, CRC

### 4.1 RAM — two halfword remainder cells

| cell | displacement | address | width | contents |
|---|---|---|---|---|
| `rem_b` | `gp−0x6D74` | `0xFEDF128C` | halfword | `t_b & 0x3FF` ∈ [0,1023] |
| `rem_a` | `gp−0x6D72` | `0xFEDF128E` | halfword | `t_a & 0x3FF` ∈ [0,1023] |

Both inside the certified free run `gp−0x6D74 … gp−0x6D2D` = `0xFEDF128C…0xFEDF12D3` (72 bytes).

🛑 **Halfword, not word, and deliberately so.** `ld.hu` bounds anything the cell could hold to
65,535. Added to `b·x` (max 11,496,000) or `a·s` (max 178,374,040) that is harmless. A 32-bit
`ld.w` on the same cell could, if the cell ever held garbage, contribute up to 2³¹ and **overflow the
add**. The halfword form costs the same 4 bytes per access and removes the failure mode entirely.
(It also lifts the word-alignment constraint, though both cells happen to satisfy it.)

**GATE 1 — RAM ownership, EVIDENCE, both methods, on the V291 image, every scanner positively
controlled first:**

| check | result |
|---|---|
| 4-byte gp-relative accesses (all of `ld.b`/`ld.h`/`ld.w`/`ld.bu`/`ld.hu`/`st.b`/`st.h`/`st.w`, with the `ld.bu` hw1-bit-5 parity rule and the `hw2` bit-0 load/branch discriminator) | **ZERO** on either cell, and **ZERO anywhere in the whole 72-byte run** |
| 6-byte extended-displacement form (`hw0 & 0xFFE0 ∈ {0x0780, 0x07A0}`) | **ZERO** |
| absolute LE32 pointer landing anywhere in the run, at any byte alignment | **ZERO** |
| `movhi 0xFEDF` + `movea` pair reaching the run | **ZERO** |
| Ghidra `search_instructions operand_pattern:"6d2d"` | 0 matches; `"6d70"`/`"6d74"` hit only branch-target digit coincidences in `FUN_00036c12`/`FUN_0006d5da` |

**Scanner controls, 8/8 PASS, chosen so the scanner is not self-controlled:** `ld.w −0x3d30` @0x28F7C,
`st.w −0x3d30` @0x28FA8, `ld.w −0x3d34` @0x28F78, `ld.bu −0x3d2c` @0x28F66 (an **odd** displacement,
exercising the parity trap), `ld.bu −0x674e` @0x28FC8, `ld.hu −0x6a98` @0x1982E, `ld.h −0x6a56`
@0x28F4C, and the 6-byte `gp−0x6752` @0x48E56. The scanner found 10,436 touched gp bytes image-wide,
so its zero on this run is a **verified** zero, not a tool zero. The absolute-pointer scanner was
separately controlled (it finds `0xCB844`, the imm32 at `0x28FCE`) and the `movhi`/`movea` scanner
finds 5 pairs elsewhere in the `0xFEDFxxxx` window.

**Boot value — EVIDENCE, not belief.** The `.data` initialiser maps `0xFEDF11B0 →` flash `0x86260`;
`rem_b`'s source is flash `0x8633C` = `00 00` and `rem_a`'s is `0x8633E` = `00 00`. The whole 72-byte
run's source is 72 zero bytes. **Control on the anchor:** `gp−0x6AB0`'s source reads `88 02 88 02 …`
(the known non-zero `.data` cell that falsified an earlier "free" claim), so the mapping is right.
⇒ **both cells boot to exactly 0.**

**Reset — decision: do NOT reset on the bail path, and here is why.** After a bail the sentinel
(`gp−0x3d2c := 2` @0x290D4) forces `s := 0` on the next tick that runs. A stale `rem_a ∈ [0,1023]`
then gives `t_a = 0·a + rem_a = rem_a < 1024`, so `step_a = 0` and `rem_a` is unchanged — **inert on
the first post-bail tick.** Thereafter it biases the a-term quantiser by at most 1 count of `s`, i.e.
2 counts of a two-sample sum whose range is ±46,080. Set against that: a reset costs two instructions
inside the bail block (code this design otherwise does not touch at all), and a bail already forces
skip 2, so the PID does not run on that tick regardless. **The remainders are self-healing by
construction — one `andi 0x3ff` puts any value, including boot garbage, into [0,1023] — so no reset
path is needed anywhere.**

### 4.2 Flash

**EVIDENCE, fresh Python read of the V291 image** (not inherited from the V289-era trace, which was
read from a *different* image):

```
0xC4B34 .. 0xC4BD8   the 0x14A telemetry cave, 164 bytes  (last non-0xFF byte 0xC4BD7 = 0x00,
                     the low half of `jmp [lp]` = 7f 00)
0xC4BD8 .. 0xC4FF0   1048 bytes, ALL 0xFF   -- V289's notch cave is ABSENT from this base
0xC4FF0 .. 0xC4FFC   01 01 01 01 00 00 c6 00 13 00 b2 00   -- the pre-existing 12-byte structure,
                     byte-identical to the V288/V289-era record, still unidentified, NOT disturbed
0xC4FFC .. 0xC5000   26 c4 ce 34   -- the block CRC
```

**Cave placed at `0xC4C00`**, 52 bytes, occupying `0xC4C00–0xC4C33`. That leaves 40 bytes of margin
below the 0x14A cave's end and 956 bytes free above the cave.

### 4.3 CRC

Two blocks, both `zlib.crc32`, both **verified to match on the V291 image today**:

| block | trailer cell | V291 value | owns |
|---|---|---|---|
| `[0x13000, 0xC4FFC)` | `0xC4FFC` | `34cec426` ✔ | the hook at `0x28F8E` **and** the cave at `0xC4C00` |
| `[0xC6000, 0xC6FFC)` | `0xC6FFC` | `ed9b12bb` ✔ | the cal block — **V292 changes nothing here** |

⇒ **V292 recomputes `0xC4FFC` only.** `0xC6FFC` must come out byte-identical to V291's, and a build
script should assert that as a guard against an accidental cal edit.

### 4.4 The V291 base, fully accounted for

V291 differs from V282 in exactly **15 bytes** in `[0x13000, 0x100000)` (full-range diff, never a
whole-file diff — the `0xFF` filler trap):

| offset | V282 → V291 | meaning |
|---|---|---|
| `0xC4BAA–AB` | `81 c9` → `d1 c2` | the 0x14A **bit-3 rung repointed** from `ld.w −0x3680` to **`ld.w −0x3d30` = the fb filter state `s`** |
| `0xC63E8` | `9b`→`c2` (923 → 962) | fb pole `a` |
| `0xC63EA–EB` | `18 06`→`be 03` (1560 → 958) | fb pole `b` |
| `0xC6446–47` | `7c 14`→`75 12` (5244 → 4725) | the r24 arm |
| `0xC4FFC–FF`, `0xC6FFC–FF` | — | the two CRCs |

**Nothing else.** The hook site `0x28F8E` is still the stock `mul r16,r7,r0` on V291 — verified
directly.

---

## 5. The cave

Every form below is proven against a **stock instance carrying the same `hw1`/`hw2` pattern that
Ghidra itself decodes** — 19/19 controls PASS (`scratchpad/v292_encctl.py`).

```
HOOK   0x28F8E   89 07 72 bc   jr 0xC4C00        replaces `mul r16,r7,r0` (f0 3f 20 02)

0xC4C00  f0 3f 20 02   mul   r16,r7,r0        ; r7 = t_b = x*b              [verbatim 0x28F8E]
0xC4C04  fa 4f 20 02   mul   r26,r9,r0        ; r9 = t_a = s*a              [verbatim 0x28F92]
0xC4C08  e4 6f 8d 92   ld.hu -0x6d74,gp,r13   ; r13 = rem_b   (bounded 0..65535 by ld.hu)
0xC4C0C  cd 39         add   r13,r7           ; r7 = t_b + rem_b
0xC4C0E  c7 6e ff 03   andi  0x3ff,r7,r13     ; r13 = rem_b' = t_b & 0x3FF   -- BEFORE the sar
0xC4C12  64 6f 8c 92   st.h  r13,-0x6d74,gp   ; rem_b := rem_b'
0xC4C16  aa 3a         sar   0xa,r7           ; r7 = step_b                 [verbatim 0x28F9A]
0xC4C18  e4 6f 8f 92   ld.hu -0x6d72,gp,r13   ; r13 = rem_a
0xC4C1C  cd 49         add   r13,r9           ; r9 = t_a + rem_a
0xC4C1E  c9 6e ff 03   andi  0x3ff,r9,r13     ; r13 = rem_a' = t_a & 0x3FF
0xC4C22  64 6f 8e 92   st.h  r13,-0x6d72,gp   ; rem_a := rem_a'
0xC4C26  aa 4a         sar   0xa,r9           ; r9 = step_a                 [verbatim 0x28FA0]
0xC4C28  e5 6f e7 72   ld.hu 0x72e6,tp,r13    ; r13 := clamp -- RESTORES r13 [verbatim 0x28F96]
0xC4C2C  e5 77 e7 72   ld.hu 0x72e6,tp,r14    ; r14 := clamp                [verbatim 0x28F9C]
0xC4C30  b6 07 72 43   jr    0x28FA2          ; back into Honda's `add r7,r9`
```

**52 bytes, 15 instructions.** Honda executed 6 instructions in the displaced span; V292 executes
1 `jr` + 15 = 16. **Net +10 instructions per 1 ms tick.**

### 5.1 Encoding proofs

| cave form | stock control | address | bytes |
|---|---|---|---|
| `mul r16,r7,r0` | itself (the displaced instruction) | `0x28F8E` | `f0 3f 20 02` |
| `mul r26,r9,r0` | itself | `0x28F92` | `fa 4f 20 02` |
| `sar 0xa,r7` / `sar 0xa,r9` | itself | `0x28F9A` / `0x28FA0` | `aa 3a` / `aa 4a` |
| `ld.hu 0x72e6,tp,r13/r14` | itself | `0x28F96` / `0x28F9C` | `e5 6f e7 72` / `e5 77 e7 72` |
| `add r13,r7` | `add r13, r7` | `0x17B74` | `cd 39` — pins reg1 = 13, reg2 = 7 |
| `add r13,r9` | `add r7, r9` | `0x28FA2` | `c7 49` — pins reg2 = 9; reg1 pinned by `0x17B74` |
| `andi 0x3ff,r7,r13` | `andi 0x2, r7, r13` | `0xAD7E` | `c7 6e 02 00` — **same `hw1`**, only the imm16 differs |
| `andi 0x3ff,r9,r13` | `andi 0x3, r13, r10` | `0x2378` | `cd 56 03 00` — pins the `andi` reg1 field = 13 |
| `ld.hu −0x6d74/−0x6d72,gp,r13` | `ld.hu -0x6a98, gp, r13` | `0x1982E` | `e4 6f 69 95` — **same `hw1`**; displacement takes `\|1` per the `ld.hu` rule |
| `st.h r13,−0x6d74/−0x6d72,gp` | `st.h r13, -0x3ee4, gp` | `0x19C84` | `64 6f 1c c1` — **same `hw1`**; displacement EVEN ⇒ `st.h`, not `st.w` |
| both `jr` | Format-V round trip over **all 2,261 `jr` sites** in the code block — 2,261/2,261 match | — | — |

**Whole-window control:** the stock window `0x28F86–0x28FAB` (38 bytes, covering `ld.hu`-tp,
`ld.h`-tp, `mul`, `sar`, `add`, `cmp`, `st.w`) **re-encodes byte-identically** from the same encoder.

### 5.2 Overflow — no new exposure

Worst case, `|x| = 12000` sustained (a ±12000 square wave, measured): `max |s| = 185,420`.

| term | V291 bound | V292 bound | margin |
|---|---|---|---|
| `a·s (+ rem_a)` | 178,374,040 | 178,375,063 | **×12.0** |
| `b·x (+ rem_b)` | 11,496,000 | 11,497,023 | **×186.8** |

The error feedback adds **0.00057 %** to the binding bound. Both `mul` instructions already discard
the high word into `r0` on stock, so nothing about the width changes.

### 5.3 GATE 2 — closed-loop stability

**The linear loop is unchanged.** V292 alters no coefficient, no structure and no clamp; it removes a
nonlinearity. §2(v) shows the integer filter's deviation from its own linear model falls from a
constant −32-count offset to a zero-mean ±2-count dither, and §2(iii) shows the describing-function
gain at 20.3 Hz goes from 0.07–1.01 (amplitude-dependent, with up to 60° of amplitude-dependent phase
error) to 0.9994–1.0009 with ≤ 0.16° of phase error at every amplitude.

⇒ **V292 makes the loop MORE like the linear model that C10's gates were scored against, not less.**
`gate73 = 1.0099`, `Ms` and `pkR` carry over unchanged — same numbers, not approximations. The
measured closed-loop peaks (§2(iv)) confirm it: at `sp = 3` the peak goes from ×1.233 (V291) to
×1.002 (V292) of V282's.

**BELIEF, stated as such:** removing an amplitude-dependent gain/phase nonlinearity from inside a
feedback loop is a stabilising change in the cases this mirror covers, and I have not found a case
where it is not. I have **not** proved it cannot interact adversely with the *other* nonlinearities
in the loop (the P clamp, the D clamp, the sum clamp, the `sar 5` on the output lag), which V292 does
not touch. That is the honest boundary.

### 5.4 Timing

+10 instructions on a 1,874-instruction function that runs at 1 kHz — **+0.53 % of its instruction
count**. For scale against a flown precedent: the V289 notch cave was 53 instructions and flew on
r62/r63 with no fault. V292's is 15 and its hook runs every tick where V289's ran on the engaged
path only, so at 100 % engagement V292 costs about **one fifth** of what V289 already proved safe.
I did **not** convert this to cycles or microseconds — that would need the core clock and the wait
states, neither of which I verified.

---

## 6. ⭐ A free positive control that the cave is live

V291's `0x14A` **bit 3** publishes `sign(gp−0x3d30)` — the fb filter state `s` — set when `s < 0`
(`ld.w −0x3d30,gp,r6 ; cmp 0 ; bge +4 ; addi5 8,r7`). That rung is already on the wire.

The `s = −1…−16` absorbing state exists on V291 and **not** on V292 (§2(i)). Measured: a symmetric
oscillation stopped at 400 different phases, then `x = 0` for 2,000 ticks —

| oscillation amplitude | V291 bit-3 duty at rest (s range) | V292 bit-3 duty at rest (s range) |
|---|---|---|
| 1 count | **1.000** (−16…−16) | **0.000** (0…0) |
| 2 | **1.000** (−16…−4) | **0.000** (0…0) |
| 3 | 0.805 (−16…0) | **0.000** (0…0) |
| 5 | 0.655 (−16…0) | **0.000** (0…0) |
| 16 | 0.547 (−16…0) | **0.000** (0…0) |
| 64 | 0.517 (−16…0) | **0.000** (0…0) |

⇒ **Pre-registered prediction: 0x14A bit-3 duty, measured over wheel-still / near-still intervals,
falls from 0.52–1.00 on V291 to 0.000 on V292.** Deterministic on the V292 side — `s` rests at
exactly 0 on all 400 phases at every amplitude, because with `x = 0` and `s = 0` the recurrence is
`t_a = rem_a < 1024 ⇒ step_a = 0`, a true fixed point. **Zero telemetry bits spent.**

⚠ **My own correction, recorded.** My first single-phase test of this showed V291 resting at 0 for
amplitudes ≥ 3 and I was about to weaken the claim to "small excursions only". The phase sweep above
shows that was an unlucky sample: the duty is ≥ 0.517 at every amplitude tested. **The interim
message I sent `main` stated this as a clean ~100 % → ~0 % flip; the correct figure is 0.52–1.00 →
0.000**, which is still a decisive instrument but not a binary one.

---

## 7. What a build script must assert

1. **Edit exactly 56 bytes**: 4 at the hook `0x28F8E`, 52 at the cave `0xC4C00–0xC4C33`. Plus the 4
   CRC bytes at `0xC4FFC`. Read back and assert every one.
2. **`base[0x28F8E:0x28F92] == f0 3f 20 02`** before writing — the hook site is the stock `mul`.
3. **`base[0xC4C00:0xC4C40]` is all `0xFF`** before writing (52 bytes + 12 bytes margin).
4. **Re-encode the whole stock window `0x28F86–0x28FAB` byte-identically** from the build script's own
   encoder, and assert it matches the image. This is the encoder's positive control; without it a
   mis-encoded cave byte can pass silently.
5. **Assert each cave form against its stock control** (§5.1 table) — not just the assembled bytes
   against a hard-coded literal, which is tautological.
6. **Assert `0xC63E8 == 962` and `0xC63EA == 958` are UNCHANGED**, and `0xC6446 == 4725` unchanged.
   **Assert `0xC6FFC` comes out byte-identical to V291's `ed9b12bb`** — a changed cal-block CRC means
   a cal byte moved by accident.
7. **Recompute `0xC4FFC` = `zlib.crc32(img[0x13000:0xC4FFC])`** and assert it differs from V291's
   `34cec426` (it must, since the hook and cave are inside the block).
8. **Assert the 12-byte structure at `0xC4FF0`** still reads `01 01 01 01 00 00 c6 00 13 00 b2 00`.
9. **Assert the 0x14A cave `0xC4B34–0xC4BD8` is untouched**, including the bit-3 rung at `0xC4BAA`
   (`d1 c2`).
10. **Re-run the GATE 1 RAM census ON THE BUILT IMAGE** for `gp−0x6D74` and `gp−0x6D72`, both
    encodings plus absolute-pointer and `movhi`/`movea`, and assert zero accessors **other than the
    cave's own four**. *A null from the V291 image is not a null for a modded one.*
11. **Re-run the branch-target scan on the BUILT image** and assert nothing targets
    `[0x28F92, 0x28FA2)` — the now-orphaned instructions.
12. **Disassemble the built cave back** with an independent decoder (not by inverting the encoder) and
    assert the 15 mnemonics match the listing in §5.
13. **Assert the arithmetic behaviourally**, by emulating the built cave's bytes: mean gain exactly
    `2b/(1024−a)` for constant `x` over the unclamped range, and `s → 0` from `s₀ = −500, x = 0`.
14. **Assert the overflow bound** `a·(b·12000/(1024−a)) + 1023 < 2³¹` (margin ×12.0).
15. **Do not raise `0xC61BE` above 32767** — the pre-existing `ld.hu`/`ld.h` mismatch at
    `0x2A142`/`0x2A146`. Unchanged by V292, but it is a standing trap on this path.

---

## 8. What I did **not** verify

1. **`Ts = 1 ms`** is EVIDENCE-by-consistency (two independent label↔byte agreements: stock `a = 923`
   → 16.53 Hz matches the record's "16.5 Hz"; V289's `a = 875` → 25.03 Hz matches its own build tag
   `FBPOLE.25HZ`). It is **not** a scheduler read. Every frequency in this document inherits that.
   To close it: read the timer ISR period.
2. **The cold-boot RAM clear.** I proved both remainder cells' `.data` **source** is zero and that the
   `.data` mapping anchor is right (the `gp−0x6AB0` control). I did **not** locate the startup clear
   loop and confirm its extent. This is why the design uses `ld.hu` rather than `ld.w`: it makes the
   question moot rather than leaving it open.
3. **Cycle cost in real time.** Bounded only relative to the flown V289 cave (§5.4). No core clock, no
   wait-state count, no measurement.
4. **GATE 2 against the loop's other nonlinearities.** §5.3 states the boundary: V292 removes one
   nonlinearity and I have shown it makes the loop more linear at every amplitude tested, but I have
   not proved the absence of an adverse interaction with the P/D/sum clamps or the output-lag `sar 5`,
   none of which V292 touches.
5. **The `sp = 33` residual (§2(iv)).** I established it is the cave removing V282's own floor bias
   (the control row lands within 0.09 %), not a V292 defect. I did **not** establish which reference —
   V282-as-shipped or V282-corrected — the B4 clause ought to be measured against. **That is an
   orchestrator decision, and I am flagging it rather than resolving it myself.**
6. **The first-tick clause vs V282 (§2(ii)).** Measured honestly at 0.9355 in mean. A
   round-to-nearest variant (`t + 512` before the shift, `−512` after the mask) would make it
   deterministic at the cost of **+16 bytes and +4 instructions**, with **identical** mean exactness —
   the telescoping identity is unchanged. I rejected it as not worth the bytes given proofs (i), (iii)
   and (v), but it is a real option if the orchestrator wants the deterministic first tick.
7. **Rlog corroboration.** The describing-function amplitudes (A = 1…16 counts) were chosen from the
   brief, not re-derived from the measured `x` distribution during a grinding episode. The mirror is
   amplitude-exact; whether those are the right amplitudes is an rlog question.

---

## 9. Files

| file | contents |
|---|---|
| `rlog-tools/studies/grind/v292_cave_mirror.py` | the importable mirror (`fb_lag_v292`, `FbLag`, `make_controller`, `closed_loop_ss`, the encoder, `build_cave`) and `run_proofs()` |
| `rlog-tools/studies/grind/_scratch/v292_cave_mirror.txt` | the full proof run |
| `analysis-2020accord/verify/v292_cave_census.py` | the branch-target / gp-access / boot-value census with its 20 positive controls |
| `analysis-2020accord/verify/v292_cave_encoder_controls.py` | the 19 encoding controls |

All three are re-runnable with no arguments (`python <file>`), using the `bin_decompile` conda env.
The census and encoder-control scripts exit non-zero on any control failure.


---

## ERRATA — 2026-09-13, from the adversarial pass (surface D, `ADV-V292-D-INTERLOCKS-2026-09-13.md` §7)

1. **§3.2 "zero new liveness claims" is mis-stated.** `r7` and `r9` are LIVE-IN to the displaced span
   (`mul r16,r7,r0` reads r7 = x; `mul r26,r9,r0` reads r9 = a) — the "writes before reading" claim holds
   only for r13 and r14. The conclusion survives because the cave replicates both `mul`s verbatim as its
   first two instructions, consuming the live-in values identically. The correct statement: *nothing after
   0x28FA2 needs the pre-hook values of r7/r9/r13/r14, and the cave preserves the two live-in reads by
   replicating the muls first.* Do NOT reuse the §3.2 argument at a site whose live-in operands are not
   replicated.
2. **§4.1's GATE 1 "zero writers" has one register-indirect writer the operand scan cannot see:** the boot
   `.data` copy loop at 0x1476C–0x14794 (`sst.w` with `ep` walking from 0xFEDF11B0) covers 0xFEDF128C/8E and
   writes 00 00 once at boot, before the 1 kHz task — harmless, and it is the boot initialiser §4.1 could not
   locate.
3. §5.1's two `andi` encoding controls at 0xAD7E and 0x2378 sit below 0x13000 (outside the flashed region);
   the build script uses in-region controls at 0x1537C and 0x34566 instead (adversary C verified).
