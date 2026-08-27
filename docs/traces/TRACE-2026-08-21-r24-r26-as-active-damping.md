# TRACE 2026-08-21 — Is r24/r26 the active-damping term, and is its live gain a cal cell?

Subagent trace (`firmware-codepath-tracer`), GhidraMCP only, `code.bin` (stock), `gp=0xFEDF8000`,
`tp=0xBF000`. All addresses/values below marked **[EVIDENCE]** were read fresh this session
(`decompile_function`, `disassemble_function`/`disassemble_bytes` with `dry_run:true`, `read_memory`,
`search_instructions`, plus an independent raw-Python LE scan of
`../accord-firmwares/analysis-2020accord/stock_fw_dump/code.bin`). Everything marked **[RELAYED]** is
carried from the orchestrator's brief or the kit's memory/`BUILD-LINEAGE.md`/handoffs and was **not**
re-derived by me this session — I cite the source each time.

## Headline answer

**Yes — r24/r26 IS the live active-damping-shaped term, and its live gain is a pure cal-data LERP
table, not any of the four override cal cells this kit has already fought over.** All three "gain
override" arms (`0xC6442`/`0xC6446`/`0xC6440` for r24; `0xC6444`/`0xC643E` for r26) are dead or
starved — confirmed structurally this session AND matching prior on-car telemetry. The **DEFAULT
arm** — a mode/speed/rate-indexed LERP table Honda ships in the same ROM-record family as everything
else in this cal block — is what actually sets the gain, essentially 100% of the time.

**But the sign question (Task 5/6) does NOT close cleanly.** My own arithmetic, run on the
premises the orchestrator supplied, says *raising* the gain is favorable. The kit's standing
"r24/r26 pumps at 6–9 Hz" finding implies the opposite. The two don't reconcile to a simple sign
flip — they look like genuinely different reference frames. See §6. **This is why I am not
recommending a build.**

---

## 1. What r24 and r26 compute [EVIDENCE — fresh decompile+disassembly this session]

### 1.1 The shared input, verified against the brief's own documented formula

`decompile_function(0x7e74a)` (`FUN_0007e74a`, gp-0x4f62's sole producer):

```c
// 8-slot circular buffer of torque samples (gp-0x2814+2*i) and their tick-timestamps (gp-0x27f4+2*i)
sVar1 = gp-0x4f60                       // current raw torque-sensor sample
N = *(ushort*)(tp+0x7c42)               // cal 0xC6C42
if (N < 8):
    sVar4 = torque_buf[(idx-N) mod 8]   // T[n-N]
    sVar2 = ticks_buf[(idx-N) mod 8]    // timestamp[n-N]
    dt = ticks[n] - sVar2               // elapsed ticks (mod-30000 wrap handled)
    gp-0x4f62 = (dt < 1) ? 0 : ((sVar1 - sVar4) << 1) / dt      // = 2*(T[n]-T[n-N])/dt
else:
    gp-0x4f62 = 0
```

**This is exactly the brief's documented formula**, `((T[n]−T[n−4])<<1)/Δticks`, confirmed instruction
for instruction. `read_memory(0xC6C40,8)` → bytes `f4 01 04 00 00 00 19 00`; offset+2 (`0xC6C42`) =
LE16(`04 00`) = **N = 4**, confirmed. The write is shadow-lockstep verified against `gp-0x4488`
(`FUN_0006b9ee` on mismatch) — same redundancy-vote pattern used elsewhere in this kit (e.g.
`gp-0x6b94`/`gp-0x4ce0`).

Deadband: `read_memory(0xC61F0,16)` → offset+6 (`0xC61F6`) = LE16(`03 00`) = **D = 3 counts**,
confirmed.

### 1.2 FUN_0003aa2c — fresh full decompile + full disassembly, both pulled this session

`decompile_function(0x3aa2c)` and `disassemble_function(0x3aa2c)` (0x3aa2c–0x3ad74, 168 instructions).
Confirms, address-exact:

- **`gp-0x4f62` is clamped once, ±0x1400 (5120), into a register (`r1`, held via `pcVar10` in the
  decompile) at `0x3aaac–0x3aac0`.** No filtering of any kind touches it before either lane consumes
  it.
- **r24 lands in register `r24`, stored `st.h r24,-0x6ada[gp]` at `0x3ad5a`.**
- **r26 lands in register `r26`, stored `st.h r26,-0x6adc[gp]` at `0x3ad4e`.**
  *(These V850 register names coincidentally match the kit's "r24"/"r26" lane names — a naming
  coincidence in the disassembly, not a hint about the lanes' identity.)*
- **Both are summed, with 8 other lanes, into `gp-0x6b94`** at `0x3acc8–0x3acda`
  (`mov r26,r6; add r24,r6; add r6,r8; ...`), clamped ±0x2800, shadow-verified against `gp-0x4ce0` via
  `FUN_0006b9fa` on mismatch (`0x3ad2c`).
- **Exactly ONE `ld.b -0x6752[gp]` in the whole function, at `0x3ab78`.** The same register (`r14`)
  is reused unmodified for r26's polarity multiply (`0x3ab7c-7e`) and, still held, for r24's
  (`0x3ac3e`) — reconfirms both lanes share the identical single polarity load, odd parity, matching
  the kit's `gp-0x6752 = −1` finding.
- **`FUN_0003aa2c` contains ZERO references to `gp-0x6806`** (I read the full decompile text; not an
  xref-null claim). This upgrades the kit's prior "not engaged-gated" finding
  (`reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain.md`) from relayed to **independently
  reconfirmed this session**: **r24/r26 run identically whether LKAS is engaged or not, at the CODE
  level.** (§5 shows the DATA level is different — see the mode-partition finding.)

---

## 2. The live gain path — the crux [EVIDENCE, fresh disassembly, all four addresses byte-read]

### 2.1 r24's 4-way priority mux, address-pinned this session

```
0x3ab98  ld.bu -0x671d[gp],r6           ; gate 0
0x3ab9c-3abfa  mode-indexed LERP (curve-A, DEFAULT) computed unconditionally -> r10/r11
0x3aba2  cmp r0,r6 ; setfne r6          ; r6 = (gp-0x671d != 0)
0x3ac04  cmp r0,lp                      ; lp = (gp-0x683c != 0), loaded earlier at 0x3aaa6-a8
0x3ac0e  cmp r0,r2                      ; r2 = (gp-0x671a >= cal(0xC64FA)=5), computed at 0x3aa70-8a
0x3abfc  be -> uVar11 = cal(tp+0x7442) = 0xC6442      [if gp-0x671d != 0]
0x3ac08  -> uVar11 = cal(tp+0x7446) = 0xC6446         [elif gp-0x683c != 0]
0x3ac12  -> uVar11 = cal(tp+0x7440) = 0xC6440         [elif gp-0x671a >= 5]
0x3ac16  else: uVar11 STAYS = curve-A (DEFAULT)
```

`read_memory(0xC6438,24)` decodes all four cal cells at once:
`0xC6440=2048, 0xC6442=1024, 0xC6444=512(r26), 0xC6446=512, 0xC643E=1536(r26)`.

### 2.2 r26's 3-way mux (no `gp-0x671d`-equivalent), same read confirms its two override cals

```
0x3ab56  cmp r0,lp -> uVar12 = cal(0xC6444)=512     [if gp-0x683c != 0]
0x3ab64  cmp r0,r2 -> uVar12 = cal(0xC643E)=1536    [elif gp-0x671a >= 5]
else: uVar12 STAYS = the FIXED (non-mode-indexed) default table
```

**Correction to an older memory note this session, in passing:** the r26 block (boxcar-average +
gain-mux + multiply) is NOT skipped whenever `gp-0x6b5e != 0` alone — tracing the raw branch at
`0x3ab2a-34` (`cmp r0,r6 / be / cmp r0,r10 / cmovne 0x0,r6,r6 / bne`) shows the skip needs **BOTH**
`gp-0x6b5e != 0` **AND** the rare `gp-0x671a >= 5` state — i.e. it inherits the same near-zero duty as
§2.3 below. Not load-bearing for this trace; flagged so the older "hard zero-force gate" framing in
`reference_accord_r26_adaptive_lane_full_trace_and_sign.md` isn't over-read.

### 2.3 Every override arm is dead or starved — structural (this session) + on-car (relayed)

| arm | cal cell | gate | structural status [this session] | on-car duty [RELAYED] |
|---|---|---|---|---|
| r24 arm 0 | `0xC6442`=1024 | `gp-0x671d != 0` | live encoding, confirmed reachable | **0/402,424 frames, 4 routes** — `BUILD-LINEAGE.md` RULE 4 (2026-08-05); `0xC6442` "written by 0 of 65 images" |
| r24 arm 1 / r26 arm 1 | `0xC6446`=512 / `0xC6444`=512 | `gp-0x683c != 0` | `gp-0x683c` has **zero `st.*` writers** anywhere in the image (prior sessions, `search_instructions`, `truncated:false`) | dead by construction — never written, must be 0 |
| r24 arm 2 / r26 arm 2 | `0xC6440`=2048 / `0xC643E`=1536 | `gp-0x671a >= cal(0xC64FA)=5` | confirmed exact gate this session (`0x3aa70-8a`, `bc`/`r2` derivation) | **0/186,321 (V67) and 0/53,991 (V68 precursor)** — `reference_accord_gp671a_shared_starved_gate_biquad_and_r24r26.md` |

⇒ **In ordinary, fault-free driving, all three override arms are unreachable for both lanes.** The
DEFAULT arm — the mode/speed/rate LERP table — is what's actually in force, essentially 100% of the
time. This directly answers Task 2 and closes the orchestrator's own open item O27
(`docs/handoffs/2026-08/HANDOFF-2026-08-20-v103-f0-is-the-endpoint.md` §8.1: *"G (r24's gain, 1–3× range) never
pinned... decode curve-A's mode-indexed LERP at the real operating point"*).

`gp-0x671d`'s true identity — **[RELAYED]**, `docs/STATE.md:1776-1778`: *"a saturating rising-edge
counter on a torque-residual/observer check (`FUN_00041d56`)... feeding DTC dispatch... reset only by
`FUN_0003bcb2`'s resync — not every tick."* I did not re-decompile `FUN_00041d56` this session
(time-boxed); the empirical 0/402,424 duty plus this structural identity (a fault-residual counter,
not a control-loop signal) are mutually consistent and I did not find any reason to doubt either.

---

## 3. The DEFAULT tables, decoded exactly [EVIDENCE — fresh `decompile_function(0x3ad74)` + read_memory]

`FUN_0003ad74` is the sole producer (**confirmed this session** via `search_instructions
operand_pattern="7a68"` → exactly 1 hit, `FUN_0003ad74@0x3aecc`, `movea 0x7a68,tp,r8`,
`instructions_scanned:183569, truncated:false`). It runs a two-stage LERP:

1. **Speed-axis blend** (cross-axis breakpoints `tp+0x7010`=`0xC6010`, `read_memory` confirms
   `X=[0,640,3200,6400]` = 0/10/50/100 km/h at 64 ct/km/h): for r24, blends between 2 of 4
   **mode-indexed** ROM records (pointer arrays at `0xCBF5C`/`0xCC044`/`0xCC12C`/`tp+0xD214=0xCC214`,
   each `mode*4`-indexed); for r26, between 2 of 4 **FIXED** records at `tp+0x7a68/7a7c/7a90/7aa4` =
   `0xC6A68/7C/90/A4` (no mode index — same structure, literal addresses).
2. **Rate-axis LERP** (inside `FUN_0003aa2c` itself, keyed on `sVar20 = min(|gp-0x6ac0|, 0x32c8)`,
   the resolver/motor-rate magnitude at the established 4.7121 ct/(°/s) scale) — over the 4-point
   X/Y arrays this stage 1 just populated.

### 3.1 r24's mode-indexed table — THIS CAR's actual mode 24/26, not mode 10

**This car's mode is 24 (manual/disengaged) / 26 (engaged), and the mode toggles on engagement edges**
— **[RELAYED]**, `memory/reference/firmware/reference-accord-car-is-tvca4-mode-24-26.md`: V73's own on-car probe,
104,061 frames, 18 transitions, 99.09% lag-matched to engagement. (Every r24 table edit V69–V73
targeted mode 10's addresses and was **inert on this car** — already recorded.)

I read mode 24's and mode 26's own pointer-array slots and record contents fresh this session
(`read_memory` at `0xCBFBC/0xCC0A4/0xCC18C/0xCC274`, offsets `mode*4`), then a **whole-image raw
Python LE32 pointer scan** (independent second method) confirming each of the 8 record addresses has
**exactly 1 pointer reference, at the expected array slot — fully private, zero blast radius outside
its own mode**:

```
                    mode 24 record        mode 26 record         private? [Python LE32 scan]
0 km/h    (array1)  0xD6A9C                0xD7A88                1 hit each, at 0xCBFBC/0xCBFC4
10 km/h   (array2)  0xD6AD8                0xD7AC4                1 hit each, at 0xCC0A4/0xCC0AC
50 km/h   (array3)  0xD6B14                0xD7B00                1 hit each, at 0xCC18C/0xCC194
100 km/h  (array0)  0xD6B50                0xD7B3C                1 hit each, at 0xCC274/0xCC27C
```

**Record contents (count/X[4]/Y[4], all 8 read this session) — mode 24 and mode 26 are BYTE-IDENTICAL
at every one of the 4 speed breakpoints:**

| speed | X (raw rate counts) | X (°/s, ÷4.7121) | Y (Q10 gain×1024) | G = Y/1024 |
|---|---|---|---|---|
| 0 km/h  | 0, 400, 1400, 3000 | 0, 84.9, 297.1, 636.7 | 3072, 3072, 2322, 1536 | **3.000**, 3.000, 2.268, 1.500 |
| 10 km/h | 0, 400, 1500, 3000 | 0, 84.9, 318.3, 636.7 | 2560, 2560, 2246, 1946 | **2.500**, 2.500, 2.193, 1.900 |
| 50 km/h | 0, 400, 1500, 3000 | 0, 84.9, 318.3, 636.7 | 2303, 2303, 2151, 1947 | **2.249**, 2.249, 2.101, 1.901 |
| 100 km/h| 0, 400, 1500, 3000 | 0, 84.9, 318.3, 636.7 | 2150, 2150, 2049, 1947 | **2.100**, 2.100, 2.001, 1.901 |

This is a **new confirmation** (not previously address-verified at these specific mode-26 addresses)
that Honda ships the r24 default gain surface identically for manual and engaged — consistent with,
and extending, `accord/calibration/accord-stock-mode24-equals-mode26-damper-is-ours.md`'s finding for the other
mode-indexed factor families.

**Practical reading: G_r24 is essentially FLAT at its plateau value (Y0=Y1) for any rate from 0 up to
~85°/s** — i.e. for the great majority of ordinary, non-aggressive steering. It ranges **3.000×
(creep) down to 2.100× (highway)** — narrower and more precisely pinned than the kit's prior "1–3×"
placeholder range (`reference_accord_r24r26_driver_torque_lane_reZ_estimate.md`'s `G` sweep).

### 3.2 r26's FIXED table — re-confirmed byte-exact against prior memory

`read_memory` at `0xC6A68/7C/90/A4`, 20 bytes each — **matches
`reference-accord-r26-adaptive-lane-full-trace-and-sign.md`'s 2026-07-19 byte-read exactly**:

| speed | X (raw rate counts) | Y (Q10 gain×1024) |
|---|---|---|
| 0 km/h   | 0, 400, 1600, 3000 | 3072, 3072, 2434, 2048 |
| 10 km/h  | 0, 250, 1200, 3000 | 3072, 3072, 2488, 1536 |
| 50 km/h  | 0, 400, 1250, 3000 | 2664, 2664, 2243, 1436 |
| 100 km/h | 0, 400, 1250, 3000 | 2560, 2560, 2145, 1331 |

**r26's table is NOT mode-indexed** — it is read via a literal `movea 0x7a68,tp,r8`-family address,
not a mode-keyed pointer array. **This is a structural asymmetry worth flagging: r24 CAN be made
engagement-conditional by a pure data edit (§5.3); r26 CANNOT.**

r26's full formula carries an **extra factor** beyond this table: `r26 = ((r1 × a_smoothed) >> 10) ×
gain_A >> 10`, where `a_smoothed` is a 2-tap boxcar average of `gp-0x69a4`. I traced `gp-0x69a4`'s
producer (`disassemble_bytes(0x35520,0x355d0,dry_run:true)`, inside `FUN_000352b4`) far enough to
confirm it is **forced to 0 outside a ±25600-count plausibility window on `gp-0x4f60`**, else set from
a *different* LERP table at `gp-0x37fc` whose own ROM source I did not chase down this session
(time-boxed). **This remains OPEN — matches the orchestrator's own O28** (`gp-0x69a4`'s typical
magnitude "not established"). I could not close it; r26's magnitude relative to r24's is therefore
still not independently pinned by a first-principles read, only by the on-car phase/dominance
measurement in §4.

---

## 4. Editable? Blast radius? [EVIDENCE]

**Yes, fully cal-data-editable, zero code cave, zero new RAM.** All 12 candidate addresses
(r24's 8 mode-24/26 records + r26's 4 fixed records) live inside the established ROM-record cal
region (`0xC6000–0xC7000` and the `0xD6000–0xD8000` mode-record blocks) that this kit has edited
successfully since V29, under the kit's standard per-0x1000 CRC-block/trailer convention. **GATE 1
(RAM ownership) is trivially satisfied** — this is a pure data edit, not a cave; no new state cell,
no register-indirect access, nothing for GATE 1 to police.

**Blast radius, both lanes, both methods:**
- r24's 8 mode-24/26 addresses: **1 pointer reference each, whole-image**, confirmed by an
  independent raw Python LE32 scan (§3.1 table) — private to their own mode slot, no sharing between
  mode 24 and mode 26 (they are physically separate flash records that merely hold equal values on
  this car), and no sharing with any other mode (unlike the old mode-10 edits, whose addresses were
  simply the wrong ones for this car).
- r26's 4 fixed addresses: **1 code-level xref each**, `search_instructions operand_pattern="7a68"`
  → exactly 1 hit (`FUN_0003ad74` itself), `truncated:false` over 183,569 instructions — matches and
  re-confirms the prior session's finding. *(A raw bare-halfword Python scan for `0x7a68` found 6
  coincidental hits elsewhere in the image; per this kit's own trap catalogue, an un-adjudicated
  2-byte immediate match is expected to produce false positives and is not treated as a real xref —
  the `search_instructions` result, which parses full instructions with base-register context, is the
  trustworthy count here.)*

---

## 5. The dose, and the engagement-conditional option [EVIDENCE for the mechanism; the target ΔG is RELAYED]

### 5.1 What ΔG=0.047 means in MY units

The brief's loop-identification numbers (`P=0.630∠163.0°`, `A=1+P=0.440∠+25.0°`,
`ΔP=c·ΔG` with `|c|=13.09∠+145.3°`, `r24+r26 = 0.1173∠−89.9°`, target `ΔG=0.047`) are **[RELAYED]**
from the orchestrator's own fresh loop analysis this session — I did not re-derive `κ`, `P`, `c`, or
the `0.1173∠−89.9°` figure myself, and I could not reconcile the brief's own "89% of sum / 49% of one
lane / ~4× over" percentages from the numbers given (0.047/0.1173 = 40.1%, not 49%) — flagged, not
fatal to what follows, but the arithmetic below is only as good as those inputs.

Treating `r24+r26 = 0.1173∠−89.9°` as **this lane's own contribution to the same G-sum**, a uniform
real multiplier `m` on both lanes' Y-tables scales that contribution linearly:
`ΔG = (m−1) × 0.1173∠−89.9°`. Solving `|ΔG| = 0.047`:

```
m − 1 = 0.047 / 0.1173 = 0.401   ⇒   m ≈ 1.40   (a ~40% increase)
```

**Sensitivity**: `dY/dΔG = Y0/0.1173`. Anchored at the creep plateau `Y0=3072` (shared by both
lanes' 0 km/h record): **26,188 counts per unit ΔG ⇒ ≈262 counts per 0.01 of ΔG.**

**Resulting cell values at m≈1.40** (uniform scale, preserving Honda's existing rate-falloff shape):

| | 0 km/h | 10 km/h | 50 km/h | 100 km/h |
|---|---|---|---|---|
| r24 Y0 (plateau) | 3072→**4301** | 2560→**3584** | 2303→**3224** | 2150→**3010** |
| r26 Y0 (plateau) | 3072→**4301** | 3072→**4301** | 2664→**3730** | 2560→**3584** |

(Every Y-point in each touched record scales by the same 1.40, not just the plateau, to preserve
shape.) **Headroom check**: the lane's own ±0x2000 clamp is reported at only 3–10% utilized even at
the 8×-era amplitude (`docs/handoffs/2026-08/HANDOFF-2026-08-20-v103-f0-is-the-endpoint.md` §6.3, "rejected suggestion"
note) — a 40% gain increase raises that to roughly 4–14%, still far from the rail. **Not independently
re-verified by me this session** — relayed, flagged as a check any build must re-run against its own
telemetry rather than assume.

### 5.2 GATE 1 is trivial; GATE 2 is NOT closed — this is O31, unchanged

`docs/handoffs/2026-08/HANDOFF-2026-08-20-v103-f0-is-the-endpoint.md` O31: *"GATE 1 and GATE 2 have NOT been run for
r24/r26 as a compensator target... not build-ready."* **This trace does not change that verdict.**
GATE 1 is closed by this session's work (pure cal data, no RAM). **GATE 2 (the sign) is the subject
of §6, and it does not close.**

### 5.3 ⭐ The engagement-conditional option — a genuinely new finding this session

Because r24's DEFAULT table is **mode-indexed** and mode 24 (manual) / mode 26 (engaged) are
**physically separate flash records** (§3.1 — different addresses, only coincidentally equal
content), **editing ONLY the mode-26 addresses (`0xD7A88/0xD7AC4/0xD7B00/0xD7B3C`) and leaving mode
24's (`0xD6A9C/0xD6AD8/0xD6B14/0xD6B50`) at Honda's stock bytes gives a cal-only lever whose effect is
present ONLY while the EPS is in its engaged mode** — despite `FUN_0003aa2c` itself containing zero
`gp-0x6806`/engagement reads (§1.2). The DATA is already partitioned even though the CODE path is
shared.

This directly addresses the operator's constraint (i) for **r24 specifically**: a mode-26-only edit
leaves manual/LKAS-off steering byte-stock. **r26 has no such option** — its table is mode-flat, so
any r26 edit is always-on, felt identically in manual and engaged driving. Given the on-car finding
that **r24 dominates r26 on 89.9% of engaged frames, rising to 99.2% at 25–50°/s**
(`docs/handoffs/2026-08/HANDOFF-2026-08-20-v103-f0-is-the-endpoint.md` §6.3, `b6` comparator — **[RELAYED]**, not
re-measured this session), an **r24-only, mode-26-only edit** captures most of the lane's effect while
respecting constraint (i) as far as this firmware's structure allows.

**On constraint (i) more directly**: this is a static Q10 gain multiplier on an already-existing,
memoryless (no filter state — confirmed §1.2/§3, `FUN_0003aa2c` has zero `ld`/`st` to any persistent
cell in either lane's gain path) term. It does not insert a new low-frequency filter or lag stage, so
it does not by itself slow down anything LKAS commands. **What it WOULD change** is the magnitude of
an existing torque-derivative contribution that rides in the same summing node as LKAS's own command
— at any gain setting this is felt as a change in how "notchy" or "heavy" the steering responds to
a fast torque change, in BOTH manual (if r26 or mode-24 is touched) and engaged driving. I cannot
respons­ibly call a 40% change "unfelt" — it is 4× larger than the −431…−1294 ct effect the kit has
already estimated for this lane at 6–9 Hz (§6), which the kit's own record ties to the ratchet/pump
symptom the operator already notices.

---

## 6. 🛑 THE SIGN — my arithmetic, and why it does NOT reconcile with "r24/r26 pumps" [mixed EVIDENCE/BELIEF — see below]

### 6.1 The favorable direction, computed from the brief's own numbers

Standard feedback framing: `A = 1+P` is the closed-loop denominator; `|A|→0` is the resonant pole.
Moving `P` **away** from `−1` (increasing `|A|`) needs `ΔP` pointed toward `A`'s own direction (to
first order, `d|A|/dΔP` is maximized when `arg(ΔP) = arg(A)`).

```
arg(A) = +25.0°                                          [given]
arg(ΔP)_favorable ≈ arg(A) = +25.0°
ΔP = c·ΔG  ⇒  arg(ΔG)_favorable = arg(ΔP) − arg(c) = 25.0° − 145.3° = −120.3°
```
r24+r26's own phase is fixed at **−89.9°** (a positive real multiplier `m` cannot rotate it):

```
RAISE (m>1): ΔG phase = −89.9°.  Offset from favorable: |−89.9−(−120.3)| = 30.4°.  cos(30.4°) = +0.863
LOWER (m<1): ΔG phase = −89.9+180 = +90.1°.  Offset: |90.1−(−120.3)| = 210.4°.  cos(210.4°) = −0.863
```

**⇒ By this arithmetic, RAISING r24/r26's gain is favorable (positive projection onto the stabilizing
direction); LOWERING is unfavorable.** This is a plain re-derivation from the brief's own `P`, `c`,
`A` — the arithmetic is mine and I checked it twice, but **the inputs (`P`, `c`, `A`, and the very
existence of the `A=1+P` closed-loop identification) are [RELAYED]**, not something I derived or
verified this session.

### 6.2 🛑🛑 This does not reconcile with the kit's "r24/r26 pumps" finding — I flag it, not resolve it

`reference_accord_r24r26_driver_torque_lane_reZ_estimate.md` (same-day gp-0x6752 correction) computes
r24's phase differently: `H_diff(7.79Hz)` phase `+84.39°` + `Z_measured(6–9Hz)` phase `−125.3°`
(route 77, `_scratch/logs/v92_rez.log`) `= −40.9°`, then the polarity flip (`gp-0x6752=−1`, `+180°`) gives
**`139.1°`**, `cos(139.1°) = −0.756` ⇒ **negative Re(Z) ⇒ PUMPING**, i.e. `r24 = −431…−1294 ct` at
6–9 Hz — the kit's basis for "if they pump, reducing helps."

**`139.1°` and the brief's given `−89.9°` are ~229° apart (or ~131° the short way) — not 0° (same
answer) and not a clean 180° (a simple missed sign flip).** I checked for the two obvious explanations
and neither fits:
- Not "someone forgot the polarity flip": `139.1° − 180° = −40.9°`, still `50.8°` from `−89.9°`.
- Not "the same figure before/after correction": the pre-correction estimate was `−40.9°`, itself
  `49°` from `−89.9°`.

**My honest read**: these are plausibly two *different* quantities. `139.1°` is r24's own **mechanical
impedance** phase (driver-torque-derivative to wheel-rate, `Re(Z)`), built by piggybacking the
whole-car's measured `Z`. `−89.9°`, in a `P=κG` closed-loop framework, is r24+r26's contribution to
the **open-loop gain sum `G`** — which reaches the pole condition only after an *additional* phase
contribution from `κ` (the rest of the loop: motor/PWM/plant dynamics) that a bare `Z`-piggyback does
not include. A term can have negative `Re(Z)` (pumping, in isolation) while its correct
closed-loop-margin direction is still "raise" — these are not guaranteed to agree, and I do not have
`κ`'s own phase or the derivation behind the `−89.9°` figure to check whether they are, in this case,
actually the same axis viewed two ways.

**⇒ I cannot tell you which is right. I can tell you exactly what would settle it**: is
`r24+r26 = 0.1173∠−89.9°` a *fresh, this-session* cross-spectral measurement (in which case it's
likely referenced to something other than `Z` — worth stating what) or is it built via the *same*
`H_diff(f)·Z_measured(f)` piggyback the `139.1°` figure uses (in which case the two SHOULD agree and
one of them has an arithmetic error worth finding)? **This is the single blocking item before any
r24/r26 gain edit is cut** — squarely inside the orchestrator's own O31 ("GATE 2 has not been run").

### 6.3 The V39 null does not reach this proposal — [EVIDENCE for the mechanism, RELAYED for V39's history]

`memory/MEMORY.md`: *"V39 flashed: neither symptom fixed... direct-derivative lane r24 falsified for
both."* Per `docs/BUILD-LINEAGE.md` RULE 4, **V39's entire delta vs V38 is a single 4-byte cave hook
at `0x3AC78`** — a conditional CODE zero, not a Y-table cal edit, and it predates this session's
mode-24-vs-26 discovery (2026-08-05), so — like V69–V73's mode-10 table edits — there is no
established proof V39's hook even landed on live silicon for THIS car's mode. Independent of that:

- V39 touched **r24 only**; r26 (§3.2, same input, same polarity, its own gain table) was **live and
  unaffected** the whole time.
- `reference-accord-r26-is-structurally-inert.md` / the V61 record cited in the brief: *"NO build ever
  had both r24 and r26 dead ⇒ each recorded null was uninformative about the lane."*

**⇒ Yes, that reasoning reaches here directly.** V39's null cannot distinguish "the DEFAULT-table gain
doesn't matter" from "r26 alone carried the whole effect" from "the hook never fired on this car's
mode." **It does not clear my proposal, and it does not indict it either — it is simply uninformative,
exactly as the kit's own V61 entry already says.**

---

## 7. What I could not resolve — open items, and what would close each

| # | open item | what would close it |
|---|---|---|
| **A** | 🛑🛑 **The `139.1°` vs `−89.9°` phase discrepancy (§6.2).** Blocks the sign call entirely. | Get the derivation behind `r24+r26 = 0.1173∠−89.9°` from whoever computed it this session (was it a fresh cross-spectral measurement, or the same `H_diff·Z_measured` piggyback?). If the latter, re-run both and find the arithmetic divergence. |
| **B** | `gp-0x69a4`'s typical magnitude (r26's extra `a_smoothed/1024` factor) — traced its gate (§3.2) but not its ROM source table at `gp-0x37fc`. Matches the orchestrator's own O28. | Decompile the callers that populate `gp-0x37fc` in `FUN_000352b4`, or an on-car telemetry read of `gp-0x69a4` itself. |
| **C** | Whether `gp+0x63fd` (mode 24⇄26) toggles on LKAS lateral engagement specifically, vs. some broader EPS-assist-active state — I relied on the existing V73 on-car probe (§3.1), not a fresh re-derivation of the mode-selector writers this session. | If a mode-26-only build is cut, a cheap comparator on `gp+0x63fd` vs the established `gp-0x6806`/`latActive` signal, on the SAME drive, would directly confirm the correlation this session assumed. |
| **D** | The brief's own "89% of sum / 49% of one lane / ~4× over" arithmetic — I could not reproduce these percentages from `ΔG=0.047`, `sum=0.048`, `lane=0.1173` (0.047/0.1173=40.1%, not 49%). Not fatal to §5's multiplier, but a real unreconciled discrepancy. | Ask the orchestrator for the intermediate arithmetic behind those two percentages. |
| **E** | The `0.1173∠−89.9°` figure's own measurement basis/route/gain-level — relayed without a method I can independently check. | The orchestrator's own citation for it (not yet in any handoff file I could find — likely still in-session). |

**Bottom line for the operator's decision**: the live gain path is found, it is cal-only, it is
private/low-blast-radius, and (for r24 specifically) it can be made engagement-conditional. **The one
thing standing between this and a buildable spec is §6 — I do not know, and cannot currently
determine, whether raising or lowering this gain is the safe direction.** Cutting a build on my §6.1
arithmetic alone, without resolving the phase discrepancy against the kit's own pumping finding, would
repeat exactly the failure class CLAUDE.md's calibration-discipline section exists to prevent.
