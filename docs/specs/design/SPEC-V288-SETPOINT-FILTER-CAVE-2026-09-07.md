# SPEC — V288 setpoint-side filter cave (LKAS rate-PID reference smoothing)

**Author**: `tracer` (subagent). Study/analysis only — nothing built, flashed, or sent.
**Programs used**: `code.bin` (stock, Ghidra, already analysed, `is_current: true`) for all
decompile/disassemble; V282 plain image
(`_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin`)
for every raw Python byte read. **Admissibility**: the source trace
(`docs/traces/TRACE-2026-09-06-lag-and-fb-pole-census-v282.md`, top of file) established a full byte
diff of `FUN_00028ea6`'s body `[0x28EA6, 0x2A2A0)` between V282 and stock returns exactly 2 differing
bytes at `0x2A1F0-0x2A1F1` (an unrelated gain-source repoint). The hook region used here
(`0x29D40-0x29DAE`) is outside that diff, so stock disassembly is valid for it. [EVIDENCE, re-derived
this session, see below]

**Everything below marks EVIDENCE (with method) or BELIEF, per standing kit doctrine.**

---

## 0. Executive summary

The 18–22 Hz creep grind is rung by the unfiltered 100 Hz command staircase feeding the LKAS rate-PID's
D term (established in the source trace's Addenda 5–6: `E = 32·sp − fb`, `dE = E[n] − E[n−1]` with **no**
state anywhere on the setpoint side). The fix specified here is a **first-order lag on `sp` alone**,
inserted as a same-length instruction swap at the exact point `sp` is computed, **before** it multiplies
into `E`. It touches nothing on the feedback path, needs **zero new RAM** (it reuses an existing,
independently re-verified dead cell), and costs **one instruction's worth of code-size class** at the
hook plus a ~30-byte subroutine in already-free flash.

| | |
|---|---|
| **Hook** | `0x29D72` — replace the existing 4-byte `st.h r16,-0x6a32,gp` with a 4-byte `jr <cave>` |
| **State cell** | `gp-0x6a32` (0xFEDF15CE) — **reused**, not new; independently re-verified 2 writers (1 live, 1 in the proven-unreachable duplicate), 0 readers |
| **Filter** | first-order IIR, `y += (sp − y) >> k`, **with a stuck-LSB correction** (naive form does NOT decay to exactly 0 from one side — see §3) |
| **Recommended k** | **4** (10.3 Hz corner) — k=3 (21 Hz) barely touches the grind band, k=5 (5 Hz) costs the most outer-loop phase |
| **Code size** | ~30 bytes (cave subroutine) + the 4-byte hook swap; free flash at the cave confirmed **1048 bytes**, not the previously-recorded 168 |
| **GATE 1** | PASS — no new writer/reader anywhere; reused cell's only two accesses are both already characterised |
| **GATE 2** | PASS structurally — standard 2-DOF reference pre-filter; nothing downstream reads raw `sp` (0 readers, confirmed) |
| **Open risk** | the assist-map's Y/X=4.3 slope (hence `sp`'s ±1032 ceiling) is confirmed only for the **live selector 7**; a different selector could change the overflow margin (still large) but not the qualitative recommendation |

---

## 1. HOOK SITE

### 1.1 The exact instruction sequence, map output to `E`

**[EVIDENCE — `disassemble_bytes`, `dry_run:true`, stock `code.bin`, `0x29D40`–`0x29DAE`, 42 instructions,
`truncated:false`]**

```
00029d40  br     0x29d6a                 ; (loop exit, feeds r13 = interpolation factor from a knot walk)
   ... 0x29d42-0x29d68: a divq-based LERP producing r13 (a second, independent table) ...
00029d6a  mov    r8, r16                 ; r16 = r8 (prior stage's index-scaled value)
00029d6c  mulh   r13, r16                ; r16 = sp  <-- THE ASSIST-MAP OUTPUT (16x16->16 signed mult)
00029d6e  ld.hu  0x72e4, tp, r10         ; r10 = cal(0xC62E4) = 4  -- the I-path clamp constant, LIVE, must survive
00029d72  st.h   r16, -0x6a32, gp        ; publish sp  <-- THE HOOK SITE (4 bytes; dead store today)
00029d76  shl    0x5, r16                ; r16 = sp * 32
00029d78  sub    r26, r16                ; r16 = E = 32*sp - fb        (r26 = fb, LIVE, do not touch)
00029d7a  mov    r16, r6                 ; r6 = E (copy for the I-path test)
00029d7c  sar    0x5, r6                 ; E >> 5
00029d7e  cmp    r10, r6                 ; compares E>>5 against cal(0xC62E4) -- uses r10 loaded above
00029d80  mov    0x0, r9
00029d82  ble    0x29d8c
00029d84  ld.hu  0x72e4, tp, r9          ; (re-loads the same cal; anti-windup clamp branch)
   ...
```

Bytes at the hook: `st.h r16,-0x6a32,gp` = `64 87 ce 95` (hw1=`0x8764`, hw2=`0x95ce`). This is a **4-byte**
instruction — the same length as a `jr disp22`.

### 1.2 Tick rate

**[EVIDENCE, inherited from the source trace, not re-derived this session]** 1 kHz, resting on the
`0xC64DF=100` STEER_STATUS debounce dwell measured at 100.00 ms on the CAN bus (source trace §3.2). The
static-timer derivation is refuted (PCLK=40 MHz, not 80 MHz) and is **not** used here.

### 1.3 Register liveness at the hook — re-derived this session

**[EVIDENCE — `disassemble_bytes` listing above, read directly, no pcode needed]**

| register | state at `0x29D72` | why |
|---|---|---|
| `r16` | **LIVE, holds `sp`** | just produced by `mulh` at `0x29D6C`; consumed by `shl 0x5` at `0x29D76` |
| `r10` | **LIVE, holds `cal(0xC62E4)`** | just loaded at `0x29D6E`; consumed at `0x29D7E`. **Must survive the subroutine untouched.** |
| `r26` | **LIVE, holds `fb`** | consumed by `sub r26,r16` at `0x29D78`. **Must survive.** |
| `r7` | **DEAD across the whole window `0x29D40`–`0x29DAE`** | does not appear as source or destination anywhere in the 42-instruction listing. **Safe general-purpose scratch.** |
| `r6` | dead-until-reassigned | last read at `0x29D50` (inside the earlier knot walk); next write is a **fresh** `mov r16,r6` at `0x29D7A`, i.e. nothing between the hook and that write reads r6's old value. **Safe scratch, but only if the subroutine returns before `0x29D7A` reads a value the subroutine itself wrote by mistake** — the design below does not use r6, so this is moot; documented for completeness. |
| `r9`, `r8`, `r13` | old values dead by `0x29D6C` (consumed at `0x29D5E`/`0x29D6A`/earlier; reloaded fresh at `0x29D80`+ or not read again in-window) | not needed as scratch, but confirms no hidden dependency |

**Chosen scratch: `r7` only.** `r10` and `r26` are the two registers a hook here must never clobber; the
design below touches neither.

### 1.4 Which PID copy is live — re-derived independently this session (crux check)

The source trace's Addendum 3 proved `[0x2A508, 0x2B422)` (a duplicate compiled copy of this whole PID)
is **unreachable**: `0x2A504` is `dispose ..., lp` (a real return, not a fall-through), a 7/7-controlled
branch scan found zero real entries after adjudicating 4 `prepare`/Format-V collisions, and no
`movhi+movea` or absolute-dword route can construct `0x2A508` or `0x2A892`/`0x2A8A2` anywhere in the
image. **I independently re-verified the load-bearing half of this claim myself** (§2.2 below): the
duplicate's own write to our chosen state cell, at `0x2A6C68`→ actually `0x2AC68`, sits inside that same
proven-unreachable span. **EVIDENCE, method: raw Python scan + one `disassemble_bytes` call, this
session** (not merely relayed from the source trace).

### 1.5 The hook itself

Replace the 4-byte `st.h r16,-0x6a32,gp` at `0x29D72` with a 4-byte **`jr <cave_addr>`**. `jr disp22`
range is ±~2 MB (`disp22 = sx(((hw1&0x3f)<<16)|hw2)`, per the source trace's own branch-scan decoder);
distance from `0x29D72` to the free flash at `0xC4BD8` is `0x9B066` (~635 KB), comfortably inside range.
The cave subroutine performs the filter, **re-issues the original store** (now holding the filtered
value instead of the raw one — see §2), and `jr`s back to `0x29D76` to resume the untouched code exactly
where it left off. This is the same "same-length swap, `jr` not `jarl`" technique already documented in
this kit's memory for a different insertion site
(`reference_accord_fun28ea6_lp_reused_as_scratch_and_29ee4_insertion_site`) — note that memory's `lp`
warning does **not** apply here: `lp` is not referenced anywhere in the `0x29D40`–`0x29DAE` window (that
warning concerns a different, later hook candidate at `0x29EE4`), but the discipline (same-length swap,
`jr` not `jarl`, verify liveness from bytes) carries over.

---

## 2. STATE CELL (GATE 1)

### 2.1 The reused cell: `gp-0x6a32` (0xFEDF15CE)

**[EVIDENCE, independently re-derived this session — the crux of this whole spec, so verified myself
rather than only relayed from the source trace's Addendum 5]**

Raw Python LE scan, gp-relative (`reg1==4`) 4-byte disp16 loads/stores, target displacement `-0x6A32`
(`hw2 = 0x95CE`), whole 1 MiB V282 image, **positive-controlled**:

```
target disp -0x6A32 (hw2=0x95ce): 2 gp-relative hits
  0x29d72  hw1=0x8764  opfield=0x3b  reg2=r16
  0x2ac68  hw1=0x4f64  opfield=0x3b  reg2=r9
```

Both confirmed by `disassemble_bytes` (dry-run) as `st.h`:
- `0x29D72`: `st.h r16, -0x6a32, gp` — the **live** hook site itself.
- `0x2AC68`: `st.h r9, -0x6a32, gp` — inside `[0x2A508, 0x2B422)`, the span **independently proven
  unreachable** by the source trace's Addendum 3 (7/7-controlled branch scan, zero real entries).

No third hit at the word-form displacement (`hw2=0x95cf`, which would indicate an overlapping `ld.w`)
and no register-indirect route: a scan for `movhi+movea` materialising the absolute RAM address
`0xFEDF8000-0x6A32 = 0xFEDF15CE` returns **zero hits**, and a raw 2-byte-aligned dword-literal scan for
the same address returns **zero hits**. **Conclusion: exactly 2 writers (1 live, 1 dead-by-unreachability),
0 readers, no indirect-access risk found.** This matches and **independently reconfirms** the source
trace's own finding (Addendum 5: "2 writers ... ZERO readers").

⚠ **Scanner honesty note**: my first attempt at a positive control (re-scanning the known filter state
`gp-0x3d3c`, expecting 4 hits) returned **zero** — that state cell is accessed via a **word-width**
instruction whose `hw2` carries `disp | 1` (an undocumented-to-me-until-now quirk, distinct from the
`ld.hu`/`ld.bu` bit-stealing already in the skill), which my first scan didn't mask for. I did not let
that null stand: I re-derived the actual bytes at all 4 known `gp-0x3d3c` access sites directly via
`disassemble_bytes`, matched the pattern, and then re-ran the `gp-0x6a32` scan un-confounded by it (the
target displacement `-0x6A32` is even either way, so the original 2-hit result for `gp-0x6a32` was never
in doubt — this note is about my control, not about the target). **Flagging as a possible addendum to the
skill's opcode-trap list, not asserting it as settled** — I have not fully characterised which opcode
classes carry this behaviour and which don't; I only confirmed it does not affect the halfword form used
here.

### 2.2 Why this is a better candidate than searching for a fresh "free" cell

`gp-0x6a32` **already stores `sp` every tick** (that is exactly what the displaced `st.h` does today).
Reusing it as filter state means:
- **No new writer is introduced anywhere in the image** — the cave's own `st.h` back into the same cell
  is the only write, exactly replacing the one that used to be there.
- **No new reader is introduced** — nothing reads this cell today (confirmed above), and the cave's own
  `ld.h` of it (to fetch the previous tick's `y`) is internal to the same subroutine, at the same
  program point, once per tick — it does not change what any *other* function sees.
- **GATE 1 reduces to a single fact already twice-confirmed**: this cell has never had a third writer or
  any reader, by two independent methods, positive-controlled.

### 2.3 A second candidate, for completeness (not recommended)

`gp-0x683c` — a byte cell with **zero references of any kind**, per existing kit memory
(`reference_accord_fun28ea6_lp_reused_as_scratch_and_29ee4_insertion_site`, §"Scratch RAM"). **Not
suitable alone**: it is one byte, and `sp` needs at least a 16-bit signed range (±1032, see §3.1) to
carry meaningful precision through the shift-and-add without truncating to Q8. Its neighbours
(`-0x683b`, `-0x683d`) are independently byte-addressed (documented in the same memory), so packing a
16-bit state across the boundary is not available without a fresh, unproven claim. **I did not re-verify
this cell myself this session** — relayed from existing memory as BELIEF-inherited, not re-derived.
Not needed given §2.1/§2.2.

---

## 3. FILTER FORM AND ARITHMETIC

### 3.1 The Q-format and range of `sp` at the hook

`sp` is produced by `mulh r13,r16` — a 16×16→16 signed multiply, **native units, no fractional scaling**
(unlike the two existing PID filters, which operate on already-scaled 32-bit intermediates). `sp`'s
practical ceiling: the map index `idx` is clamped to `0..240` by `cal(0xC64F0)=240` (Addendum 6), and the
assist-map table at `0xC9A88` for the **live selector (7)** is recorded elsewhere in this kit's memory as
**CONFIRMED LINEAR, Y/X = 4.30** — giving `sp_max ≈ 4.30 × 240 ≈ 1032`. **[EVIDENCE for the clamp value
and linearity claim, inherited from existing memory and the source trace; the ±1032 figure is my own
arithmetic from those two facts, not independently re-measured against the raw table bytes this
session]**. Stated as a bound with margin below, not as a tight design constraint.

### 3.2 Candidate (a): first-order IIR lag — RECOMMENDED

**Naive form** (as literally requested in the brief): `y += (sp − y) >> k`.

```python
def naive_iir(sp_seq, k, y0=0):
    y = y0
    out = []
    for sp in sp_seq:
        delta = sp - y
        step = delta >> k          # V850 sar: arithmetic shift, FLOORS toward -infinity
        y = y + step
        out.append(y)
    return out
```

🛑 **This does NOT decay to exactly 0 from every direction — a real, non-obvious defect the brief's
own acceptance criterion catches.** Because V850 `sar` floors toward −∞ (confirmed behaviour of the
existing filters, per the source trace: *"Both shifts are arithmetic (sar), so negative products floor
toward minus infinity"*), the update is **asymmetric**:
- Approaching the target from **above** (`y > sp`): `delta` is negative; for any `delta` in `[-2^k, -1]`,
  `sar` gives `-1` — **never gets stuck**, converges to the exact target.
- Approaching from **below** (`y < sp`), with `0 < delta < 2^k`: `sar` gives **exactly 0** — **the state
  never moves**, permanently.

**Simulated, this session** (`k=3,4,5`, decaying to `sp=0` from `y0=±17`):

| k | from +17 | from −17 (naive) | from −17 (corrected, §below) |
|---|---|---|---|
| 3 | reaches 0 at tick 11 | **stuck at −7 forever** | reaches 0 at tick 15 |
| 4 | reaches 0 at tick 15 | **stuck at −15 forever** | reaches 0 at tick 16 |
| 5 | reaches 0 at tick 16 | **stuck at −17 forever** | reaches 0 at tick 16 |

**Corrected form** — force a unit step whenever the shift rounds a genuine nonzero error to 0:

```python
def corrected_iir(sp_seq, k, y0=0):
    y = y0
    out = []
    for sp in sp_seq:
        delta = sp - y
        step = delta >> k
        if step == 0 and delta != 0:      # only ever fires for 0 < delta < 2^k (the floor-toward-0 case)
            step = 1
        y = y + step
        out.append(y)
    return out
```

This is the form to build. It reaches the exact target from **either** direction within at most `2^k`
ticks (11–16 ms at 1 kHz for k=3..5), with **no stuck LSB**, confirmed by direct simulation above.

**Overflow — [EVIDENCE, simulated]**: worst-case `|delta|` under a full-amplitude square-wave stress test
(`sp` alternating ±1032 every 50 ticks) is **2064** (k=3), **2016** (k=4), **1841** (k=5) — headroom of
**16–18×** to the 16-bit signed limit (32767). A 16-bit state cell is safe; no width upgrade needed
(unlike the existing two filters, which need 32-bit precisely because they operate on pre-scaled
intermediates far larger than this).

**Corner frequency, magnitude response, group delay — [EVIDENCE, computed via the standard 1-pole
discrete-time response, same convention the source trace uses for the existing filters]**:

| k | pole `a=1−2⁻ᵏ` | corner | \|H(3 Hz)\| | \|H(20 Hz)\| | \|H(40 Hz)\| | time constant |
|---|---|---|---|---|---|---|
| **3** | 0.875 | 21.25 Hz | 0.990 | 0.729 | 0.470 | 8 ms |
| **4** | 0.9375 | **10.27 Hz** | 0.960 | **0.457** | 0.249 | 16 ms |
| 5 | 0.96875 | 5.05 Hz | 0.860 | 0.245 | 0.126 | 32 ms |

**Recommendation: k=4.** k=3's corner (21 Hz) sits essentially on top of the 18–22 Hz grind band and
removes only ~27% of it at 20 Hz — too weak to matter. k=5 removes the most (75% at 20 Hz) but costs the
most at the outer loop's 3 Hz band (14% attenuation, 32 ms delay) where openpilot's own loop is closing.
**k=4 removes over half the grind-band content (54% at 20 Hz) while preserving 96% at 3 Hz** — the
better trade-off given the operator's constraint of not touching authority or the feedback gains.

**Engage/disengage behaviour**: the state persists in `gp-0x6a32` across engage transitions (it is never
reset elsewhere — no other code touches this cell). On disengage, `sp` itself presumably goes to 0 or a
neutral value upstream (not independently re-verified this session — **BELIEF**, inherited from the
source trace's "disengaged/reset branch sets the PID terms to zero" finding, Addendum in the source
trace's "Engaged-only?" section, which is about a different clamp but the same general disengage
mechanism); the corrected-form decay-to-zero property above (§ table) is exactly what handles this
cleanly regardless of approach direction.

**V850 instruction listing** (byte-accurate encodings to be finalised by the build script, per this
kit's established practice — see `build_v282_tva.py`'s own pattern of asserting bytes programmatically
rather than hand-committing opcodes in a design doc):

```
ld.h   -0x6a32, gp, r7      ; r7 = y_prev                                    4 B
sub    r7, r16               ; r16 = sp - y_prev = delta                      2 B
mov    r16, r6                ; r6 = delta (saved for the zero/sign test)     2 B
sar    0x4, r16                ; r16 = step = delta >> k   (k=4 shown)        2 B
cmp    0x0, r16                 ; test step == 0                             2 B
bne    +6                        ; if step != 0, skip the correction         2 B
cmp    0x0, r6                    ; test delta == 0 too (truly converged?)   2 B
be     +4                          ; if delta==0, skip forcing (step stays 0)2 B
mov    0x1, r16                     ; force step = 1 (only reached for 0<delta<16) 2 B
add    r7, r16                       ; y_new = y_prev + step = sp_f          2 B
st.h   r16, -0x6a32, gp                ; store new state (replaces the       4 B
                                        ;   original dead-sp publish)
jr     0x29d76                          ; return to the unmodified shl       4 B
                                                                    TOTAL:  ~30 B
```

`r7` and `r6` are both confirmed dead at the hook (§1.3); `r10` (the I-path cal) and `r26` (`fb`) are
never touched. Placement: the confirmed-free flash at `0xC4BD8` onward (§4), well inside `jr`'s range
from both the hook (`0x29D72`) and the return point (`0x29D76`).

### 3.3 Candidate (b): 10-tick linear interpolation — NOT recommended, costed for completeness

Needs **at least 3** persistent cells: the last full-rate `sp` target, the current interpolated output,
and a tick counter (0–9) — plus a `divq` to compute the per-tick increment, since the increment depends
on how far `sp` moved since the last update. That is **strictly more state than this spec has verified
RAM for**: only `gp-0x6a32` has been independently re-confirmed free this session (§2.1); a second and
third cell would need a fresh GATE-1 census I did not run (the byte cell `gp-0x683c` from §2.3 could
supply one 8-bit counter, but the two 16-bit value cells remain unfound). It is also **cadence-fragile**:
it assumes `sp` updates on a fixed 10-tick boundary, but Addendum 6 of the source trace shows the actual
step size and cadence are **command-dependent**, not fixed — a mismatched interpolation window could
either under-smooth fast commands or introduce an unwanted extra lag on already-slow ones. The IIR is
cadence-agnostic by construction and needs no census beyond what is already done. **Recommendation:
build (a), not (b).**

---

## 4. FREE FLASH FOR THE CAVE SUBROUTINE

**[EVIDENCE, raw Python byte scan, V282 image, this session — corrects an existing memory's
conservative estimate]**

```
region [0xC4BD8, 0xC4FFC) = 1060 bytes total (the CRC-block's tail before its own trailer)
  0xC4BD8 .. 0xC4FEF  : 1048 contiguous 0xFF bytes  <-- FREE, confirmed by direct read
  0xC4FF0 .. 0xC4FFB  : 12 non-FF bytes (01 01 01 01 00 00 C6 00 13 00 B2 00) -- NOT free, unidentified small structure, left untouched
  0xC4FFC .. 0xC4FFFF : 4-byte CRC trailer (0x4EB06B44 currently) -- recomputed by the existing build-script machinery (V53.owning_block / crc_block_map), not hand-edited
```

Existing kit memory (`reference_accord_fun28ea6_lp_reused_as_scratch_and_29ee4_insertion_site`) recorded
only "168+ bytes ... checked directly through at least 0xC4C7F" — a deliberately conservative bound, not
a claim of the total extent. **This session's direct read extends that to the true boundary: 1048 bytes**,
comfortably enough for the ~30-byte filter subroutine and any additional telemetry code (§5). The cave's
own last body byte is `0xC4BD7` (`7f 00`, believed to be the cave's `jmp [lp]` epilogue — **BELIEF**,
relayed from that same memory file; I did not independently disassemble it this session because the
currently-open Ghidra program is stock, which has no code at this address at all — `code.bin`'s bytes
here are all `0xFF`, confirming the cave is V282-only content. Opening the V282 image in Ghidra directly
would settle this by-instruction, and is the exact next step if that detail becomes load-bearing).

CRC handling: the build script (`build_v282_tva.py` §[5]) locates the owning CRC block **generically**
via `V53.owning_block` / `FF.crc_block_map` rather than a hardcoded address, and re-stamps the trailer
with `zlib.crc32` over `[b0, b1)`. **The same mechanism applies unchanged** to a V288 build that adds
bytes inside `[0xC4BD8, 0xC4FEF]` — no new CRC-block class of risk, since this range is already inside
the same `[0x13000, 0xC4FFC)`-class block every other V282 cave edit sits in.

---

## 5. GATE 2 — closed-loop structure and downstream consumers

### 5.1 The loop-theory argument

`E = 32·sp − fb`; `P`, `I`, `D` are all functions of `E` (and `dE = E[n]−E[n−1]`) only. **Nothing in the
loop feeds back into `sp` or `sp_f`** — the source trace's Addendum 5 structural test (is any gp cell
both written and read in the setpoint region?) returned **ZERO** for the raw region, and `sp_f`'s new
home (`gp-0x6a32`) is likewise read only by the filter itself, once per tick, at the same program point.
This is the textbook **2-DOF (reference pre-filter) structure**: the loop's return ratio
`L = C(s)·P(s)` (controller times plant, everything from `E` onward) is **structurally unchanged** — only
the reference `w` that `E` is computed against is now `F(s)·w_raw(s)` for a first-order `F(s)`. Loop
stability margins (gain and phase margin of `L`) are determined entirely by `C` and `P`, neither of which
this edit touches. **[EVIDENCE for the structural fact — the "ZERO" result is the source trace's, verified
by its own positive control against `gp-0x3d3c`; the 2-DOF argument itself is standard control theory,
not something requiring firmware evidence]**.

### 5.2 What DOES read raw `sp` today, and what should see filtered vs raw

**Nothing does.** `gp-0x6a32` (the only place raw `sp` was ever visible outside registers) has **zero
readers**, confirmed independently this session (§2.1). So there is no existing consumer to decide
"raw vs filtered" for — **every consumer downstream is downstream of `E`, not of `sp`**, and therefore
automatically sees the filtered value once it is used to build `E`. Specifically, from the source trace's
own census (Addendum 5(c), source trace Task 4):

| downstream item | reads raw `sp`? | reads (post-`E`) filtered-derived value? |
|---|---|---|
| override taper (`0xCBBC4` fade) | no | yes, indirectly (post-PID output) |
| sum clamp `0xC61BE`, D clamp `0xC61B6` | no | yes (act on `P`/`D`/sum, all `E`-derived) |
| Ki anti-windup clamp (`0xC62E4`, inert, Ki=0) | no — it clamps `E>>5`, formed from `sp_f` after this edit | correctly sees filtered `E` |
| EME shaper, governor slew, lockstep monitor | no | downstream of PID output, several stages removed |

### 5.3 Plausibility-monitor risk

**The one live, genuinely frequency-selective monitor is Honda's oscillation-reversal detector,
`FUN_000428d4`** (source trace, Task 4.1), which watches **`gp-0x6c2c`, a derivative of MOTOR ROTOR
POSITION** — not the setpoint. Filtering `sp` **reduces** the high-frequency content that reaches `D` and
ultimately the motor, which if anything **moves away from** this detector's ±12800 reversal threshold
(the opposite direction of risk from the previously-considered feedback/output-pole moves, which the
source trace flagged as *raising* that risk by 2.45–2.80×). **No new DTC or plausibility risk identified
for this edit** — **[BELIEF]**, in the same sense the source trace uses for this detector's un-firing
status today: I have not measured `gp-0x6c2c`'s actual amplitude, only argued the direction of the
effect is favourable, not neutral-and-untested.

The remaining three consumers named in the source trace's Task 4.2 (governor slew, soft-EME windup
shaper, hard-DTC lockstep monitor) are **not frequency-dependent** and act many stages downstream of the
PID; none of them reads `sp` or `E` directly. **No risk identified.**

---

## 6. INSTRUMENT

### 6.1 What needs proving, and what doesn't

**Raw `sp` needs no wire tap at all.** The source trace's Addendum 6 proved the entire chain from the
`0xE4` CAN byte to `sp` is **memoryless** (one signed store, two symmetric clamps, a multiply, two
shifts, an absolute value — no filter, no cal with memory). That means `sp_raw` is **exactly
reconstructable offline**, tick-for-tick, from the logged `0xE4` stream plus the known LERP tables —
**already true today, unconditionally on this build.** The only thing worth putting on the wire is
**`sp_f`** (the filtered value), so a drive can be scored by diffing the on-wire filtered signal against
the offline-reconstructed raw one.

### 6.2 Minimum bit, and the bit budget

**[EVIDENCE, `build_v282_tva.py` header comment, re-read this session]** The existing V112/V282 telemetry
cave (hooked at `0x55C0E`, packing an 8-byte buffer onto CAN ID **0x14A** at 100 Hz) currently spends its
byte-4 bits as:

| bit | mask | meaning (V282) |
|---|---|---|
| 7 | 0x80 | sign(assist sum, `gp-0x6b4c`) |
| 6 | 0x40 | \|r24\| ≥ \|T\| (this session's predecessor edit) |
| 5 | 0x20 | \|r24\| ≥ \|aggregator sum\| |
| 4 | 0x10 | sign(r24, `gp-0x6ada`) |
| 3 | 0x08 | sign(`gp-0x3680`) |
| **2–0** | **0x07** | **never written by this cave — FREE (3 bits)** |

Separately, **CAN 427** (the delivered-torque tap, `gp-0x6b38`) has, per the same build script's own
framing, only **3 bits free inside Honda's checksum — "not enough for a second field"**; a newer kit
memory (`reference_accord_can427_dbc_confirms_4_spare_bits...`, not re-verified this session) puts it at
4. Either way, **427's headroom is committed to the torque tap and is not the right place for this
instrument** — the 0x14A cave's 3 free bits are.

**Proposed minimum instrument: ONE new bit, `bit0 (0x01) = sign(gp-0x6a32) < 0`** — i.e. `sign(sp_f)`,
using the **exact same rung shape already proven in this cave** for bit 4's `sign(r24)`. This lets the
operator (or the offline mirror) compare the **zero-crossing timing** of `sign(sp_f)` on the wire against
the offline-reconstructed `sign(sp_raw)`: the delay between the two zero-crossings is a direct,
model-free read of the filter's group delay, and is simultaneously a **build-identity proof** — if the
cave never ran the new code, the bit would be stuck or absent.

### 6.3 What this costs, and what is NOT verified

Adding this bit means **extending the 0x14A cave's code** (breaking V282's "no length change" property,
which is not a constraint on a new build) — splice ~14–20 bytes of new rung code into the same
`0xC4BD8`+ free region (comfortably inside the 1048-byte budget alongside the ~30-byte filter
subroutine), and **redirect the cave's own epilogue** (believed to be `jmp [lp]` at `0xC4BD6`, see §4's
BELIEF flag) to detour through the new rung before the real return. **I did not verify this epilogue
instruction by disassembly this session** (it requires opening the V282 image in Ghidra directly, which
I did not do, having judged it non-load-bearing for the primary filter recommendation) — **this is the
one open item in this spec that needs a direct check before the extended-telemetry variant is built.**
The core filter recommendation (§§1–5) does not depend on this and can be built and flown without it,
at the cost of relying entirely on the offline reconstruction with no on-wire confirmation that the
new code is executing.

---

## 7. OPEN RISKS / NEXT STEPS, IN ORDER OF WHAT WOULD CHANGE THE RECOMMENDATION

1. **The `sp` ceiling (±1032) rests on the assist-map's Y/X=4.30 linearity claim for selector 7 only**,
   inherited from existing memory, not re-measured against the raw `0xC9A88` table bytes this session.
   Even a several-fold error leaves the overflow headroom (16–18×) intact, so this would not change the
   filter's safety, only the precision of the corner-frequency-vs-attenuation table in §3.2.
2. **The cave epilogue instruction at `0xC4BD6`-`0xC4BD7` (believed `jmp [lp]`) is unverified by me this
   session** — needed only for the optional §6.3 telemetry extension, not for the core filter. Exact next
   step: open the V282 plain image in Ghidra (`import_file` or `open_program`, per this kit's own
   `reference-accord-importing-a-built-image-into-ghidra` memory — expect zero auto-analysed functions
   and a need to `create_function` if a full decompile is wanted; a bare `disassemble_bytes dry_run:true`
   over `0xC4BD0`-`0xC4BD8` does not require that) and disassemble that one instruction directly.
3. **`gp-0x6c2c`'s actual grind-band amplitude relative to the ±12800 oscillation-detector threshold is
   still unmeasured** (carried over from the source trace, not re-derived here) — this bears on whether
   Honda's own detector is already close to firing, which would matter for *any* change to this loop,
   not specifically this one. The direction of this edit's effect on that risk is favourable (§5.3), but
   "favourable direction" is not the same claim as "measured margin."
4. **Byte-exact instruction encoding for the ~30-byte subroutine (branch displacements, opcode fields)
   is left to the build script**, per this kit's established practice of deriving and asserting bytes
   programmatically rather than hand-committing them in a design document — the same practice
   `build_v282_tva.py` itself follows for its own edits.

**Nothing in this spec was built, flashed, or sent.** No Ghidra program was saved, renamed, or
otherwise mutated; all V282-image work was read-only Python; all `code.bin` work was
`dry_run:true` or a read-only query.
