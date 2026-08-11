# TRACE 2026-08-10 — Is the LKAS command a KNOWN INPUT to the driver-torque / plant-model / observer path?

> # 🛑🛑 STATUS BANNER — READ BEFORE ACTING ON ANY LEVER IN THIS FILE (added 2026-08-10, late)
>
> **The LEAK HYPOTHESIS that this document's HEADLINE and §7 ranking are built on is DEAD.** `LeakDose`
> probed **`gp-0x6b70` directly** on-car (V86/V86B cave rungs, routes `6f`/`70`) and it failed three ways:
> **no engagement response** (+16 pp collapses to **+0.6 pp** under a motion screen — it was parked manual
> frames; speed/rate-matched the two routes disagree in *direction*); **the wrong axis, exactly inverted**
> (engaged-only `log|rate|` **+0.947 [+0.805, +1.960]** and **+0.573 [+0.333, +1.653]**, both excluding 0,
> while `log|cmd| rms` is **NULL** on both — the symptom is magnitude-proportional and rate-independent,
> the residual is the exact inverse); and **no sign coupling** at any lag.
>
> ⇒ **team-lead has taken `0xC40D4` AND `0xC63AC` off the table. DO NOT propose "`0xC63AC` 102 → 65" or
> any `0xC40D4` retune from §7 below.** The arithmetic in §3b is correct; the lever is dead anyway.
> The V86 retrodiction is separately a **NULL, underpowered 3.07×**
> (`docs/ANALYSIS-2026-08-10-v86-leak-retrodiction.md`) — where Round 1 called it *"weak counter-evidence"*,
> that **understated it**.
>
> ⚠ **Transport tick:** team-lead's and ObserverMatch's leak figures carry a **+1 tick** on Branch A that
> mine do not; theirs reproduce the golden model's independently-recorded **−36.06° at 7.79 Hz**, which
> requires it. **Use the +1 tick.**
>
> **WHAT IN THIS FILE STILL STANDS** — all of it structural, none of it dependent on the leak:
> §1 the LKAS command's full path and the 11-slot assist-channel framework · §2 the `gp-0x4f60` consumer
> map · §3 the crux (the model reads the total delivered command) · §4 the FIR de-ranking **and** field D
> as the observer's declared-disturbance slot · §5 the aggregator table · §6 `0xC646E` is a **lagged
> velocity damper**, not inertia compensation · the friction exact-zeros resolution and the gate-flag
> equivalence in the Round-2 addendum · and the METHOD CORRECTION, which is kit-wide.

Agent: `TorquePath` (firmware-codepath-tracer). Program: Ghidra `/code.bin` (stock `39990-TVA-A160`, 2086 fns,
the only program opened this session). Byte reads: `../accord-firmwares/analysis-2020accord/stock_fw_dump/code.bin`
(file offset == absolute address). `gp = 0xFEDF8000`, `tp = 0xBF000`.

**tp anchor verified before any tp claim**: `tp+0x50D2` computes to `0xC40D2` and that address byte-reads
**102** — the known K1 friction cal; `tp+0x50BC` → `0xC40BC` reads **600** — the known relay cal. Both match
the record exactly, so the off-by-0x1000 trap did not fire here.

---

## HEADLINE

**The operator's hypothesis is REFUTED in its literal form and RELOCATED — to a place that is arguably a
better bug and is reachable by ONE CAL BYTE PAIR.**

- The LKAS command **is** a known input. It reaches the disturbance observer **twice**, by two independent
  routes, both at **unity gain**. [EVIDENCE]
- But the observer's two arms **filter it differently** — a 2-pole EMA (α = 0.1399) on one side against a
  1-pole EMA (α = 0.0996) on the other. The difference of the two transfer functions peaks at
  **|ΔH| = 0.293** in the 18–28 Hz band and is **0.152** at 7.8 Hz. ⇒ **up to ~29 % of the LKAS command
  reappears in the residual as a phantom, unmodelled disturbance, with 27–35° of phase error, precisely in
  the two complaint bands.** [EVIDENCE for the filters and the arithmetic; BELIEF that this is the mechanism]
- ⚠ **The kit has already flown a dose on exactly this mismatch without knowing it — V86** (`0xC40D4`
  573 → 286) **raised the peak mismatch 0.293 → 0.661, i.e. 2.26× WORSE.** The operator's V86 report was
  *"grinding and micro-ratcheting maybe a smidge better, if at all; ratcheting definitely perceptible"* —
  **no clear worsening**, which is weak counter-evidence against this mechanism. It was a parking-lot-only
  route. This must be stated before anyone builds on the finding.

---

## §3 — CRUX: what is the plant model's "applied torque" input?

### **ANSWER: (a) THE TOTAL MOTOR COMMAND, INCLUDING LKAS.** [EVIDENCE]

`FUN_0003b8f6`, first instruction of the function:

```
0003b8f6: ld.h -0x6b98[gp],r7        <- gp-0x6b98 = the FOC motor command, last cell before the motor
0003b8fa: addi 0x2000,r7,r10         <- validity screen |cmd| <= 0x2000
0003b93e: mul r6,r7,r0               <- r6 = s8(gp-0x6752), polarity {-1,0,+1}
0003b942: cvtf.ws r7,r16             <- float(cmd x polarity)
0003b946: ld.w -0x3628[gp],r12
0003b94e: ld.hu 0x50d4[tp],r14       <- cal 0xC40D4 = 573  => alpha = 573/4096 = 0.13989
   ... EMA #1 into gp-0x3628 ... EMA #2 into gp-0x3624  (2 cascaded poles)
```

There is no separate "base assist only" or "measured current" source. The model's applied-torque branch is
the **delivered** command, so it necessarily contains the LKAS overlay.

### Full arithmetic of `FUN_0003b8f6`, mirrored (integer/float as in the code, addresses annotated)

```python
# --- validity gates -------------------------------------------------
if abs(s16(gp_0x6b98)) > 0x2000:            goto FAIL   # 0x3b8fa
if not (-0x6400 <= s16(gp_0x4f60) < 0x6401): goto FAIL   # 0x3b910
if abs(s16(gp_0x6abc)) > 13000:              goto FAIL   # 0x3b920
pol = s8(gp_0x6752)                                       # 0x3b92e  {-1,0,1}
if not (-1 <= pol <= 1):                     goto FAIL

# --- A. APPLIED-TORQUE branch  (2-pole EMA, alpha = 0xC40D4/4096 = 0.13989) ---
aA  = u16(0xC40D4)/4096.0                                 # 573  -> 0.13989
x   = (s16(gp_0x6b98) * pol) / 1024.0                     # 0x3b8f6/0x3b93e   THE LKAS-BEARING INPUT
gp_0x3628 += (x          - gp_0x3628) * aA                # 0x3b956..0x3b97e
gp_0x3624 += (gp_0x3628  - gp_0x3624) * aA                # 0x3b98a..0x3b9fa
model_cmd  = gp_0x3624

# --- B. COLUMN-TORQUE branch (2-pole EMA, alpha = 0xC40D8/4096 = 0.89990) ---
aB  = u16(0xC40D8)/4096.0                                 # 3686 -> 0.89990   ~TRANSPARENT
c   = s16(gp_0x4f60) / 1024.0                             # 0x3b908
gp_0x3620 += (c         - gp_0x3620) * aB                 # 0x3b992..0x3b9b2
gp_0x361c += (gp_0x3620 - gp_0x361c) * aB                 # 0x3b9ba..0x3b9ce
y   = gp_0x361c * u16(0xC613A)/32768.0                    # 0x3b9b6  1159 -> 0.035370
# 3-tap FIR, taps are FLOATS, byte-read from the image:
#   0xC4048 = 1.0   0xC404C = 0.0   0xC4050 = 0.0    => PASS-THROUGH, NOT a derivative
lead = 1.0*y + 0.0*gp_0x363c + 0.0*gp_0x3638              # 0x3b9d2..0x3b9f6
gp_0x3638, gp_0x363c = gp_0x363c, y
lead = clamp(lead, -15.0, +15.0)                          # 0x3b9fe..0x3ba0e
w    = lerp_u16(u16(gp_0x6a10), table @ 0xC6B66/0xC6B80)  # 0x3ba12..0x3ba7a  (>=10001 -> 1024)
model = model_cmd + lead * w/1024.0                       # 0x3ba82..0x3ba8a

K    = u16(0xC6468)                                       # 2639  output scale, tp+0x7468
gp_0x6bf6 = clamp(int(K*model), -20000, +20000)           # 0x3bac0   MODEL, pre friction/inertia

# --- C. FRICTION (V89's lever) --------------------------------------
r    = pol * s16(gp_0x6abc) * 12                          # 0x3baae/0x3bab0  gp-0x6abc <- gp-0x4f50 motor rate
relay= clamp(r / u16(0xC40BC), -1.0, +1.0)                # 0x3bab4..0x3bae4   600 -> saturates at |r|>=600
K0   = u16(0xC4080)   #    0  <-- PURE COULOMB IS OFF IN STOCK
K1   = u16(0xC40D2)   #  102  <-- |model|-proportional, V89 doubles this
aF   = u16(0xC40D0)/4096.0                                # 408 -> 0.09961
gp_0x362c += ((abs(model)*relay*K1/1024.0 + K0/1024.0*relay) - gp_0x362c) * aF   # 0x3baf6..0x3bb38
friction   = clamp(gp_0x362c, -10.0, +10.0)

# --- D. INERTIA (cal 0xC646E) ---------------------------------------
aI   = u16(0xC40D6)/4096.0                                # 246 -> 0.06006
d    = (r - gp_0x3618) * 0.5 * 17.453293                  # 0x3bb4a..0x3bb58   d/dt(motor rate) = ACCEL
gp_0x3618 = r
gp_0x3634 += (d          - gp_0x3634) * aI                # 0x3bb5c..0x3bb86
gp_0x3630 += (gp_0x3634  - gp_0x3630) * aI                # 0x3bb7a..0x3bbb0
inertia    = clamp(gp_0x3630 * u16(0xC646E) * 2**-24, -10.0, +10.0)   # 0x3bb92  1428

# --- E. OUTPUT -------------------------------------------------------
gp_0x6bfc = clamp(int((model - (friction + inertia)) * K), -20000, +20000)  # 0x3bbc2..0x3bc1a
gp_0x6c00 = abs(gp_0x6bfc)
gp_0x6ae0 = int(inertia  * 1024)                          # 0x3bc00  mirror
gp_0x6ae2 = int(friction * 1024)                          # 0x3bc04  mirror (V89's probe source)
FAIL: gp_0x6bf6 = gp_0x6bfc = 0x7fff ; gp_0x6c00 = 0xffff
```

**Cal values, all byte-read little-endian from stock `code.bin`:**

| addr | value | role |
|---|---|---|
| `0xC40D4` | **573** | applied-command EMA α (×2 poles) = 0.13989 |
| `0xC40D8` | **3686** | column-torque EMA α (×2 poles) = 0.89990 |
| `0xC40D0` | 408 | friction EMA α = 0.09961 |
| `0xC40D6` | 246 | inertia EMA α = 0.06006 |
| `0xC4048 / 0xC404C / 0xC4050` | **1.0 / 0.0 / 0.0** (f32) | column 3-tap FIR — **pass-through; two taps ZEROED** |
| `0xC4080` | **0** | K0 pure Coulomb — **OFF in stock** |
| `0xC40D2` | 102 | K1 `|model|`-proportional friction (V89 → 204) |
| `0xC40BC` | 600 | friction relay normaliser |
| `0xC613A` | 1159 | column-torque scale into the model |
| `0xC646E` | 1428 | **inertia gain** |
| `0xC6468` | 2639 | model / reconstruction output scale (shared — see §3b) |

---

## §3b — THE REAL FINDING: the observer differences two DIFFERENTLY-FILTERED copies of the same command

`FUN_00038148` is the observer. Its "ACTUAL" side is **not** the motor command — it is a re-summation of six
named lanes, scaled by **the same `0xC6468` = 2639** as the model output, i.e. deliberately matched units.

```python
# FUN_00038148, all six gains byte-read = 1024 = UNITY
S = ( clampv(gp_0x6b4e, 0x2800)*u16(0xC63A8)         # 0x3817c   direct-injection lane
    + clampv(gp_0x6b4c, 0x2800)*u16(0xC63AA)         # 0x3816c   <-- THE LKAS LANE
    + clampv(gp_0x6b26, 0x400 )*u16(0xC63A6)         # 0x3815c   friction comp
    + clampv(gp_0x6b46, 0x400 )*u16(0xC63A4)         # 0x3814c
    + clampv(gp_0x6bd0, 0x800 )*u16(0xC63A0)         # 0x38150   damper
    + clampv(gp_0x6bbe, 0x800 )*u16(0xC63A2) ) >> 10 # 0x38148   boost
S = ((S * pol * u16(0xC6468)) >> 10) * 16
aR = u16(0xC63AC)/1024.0                             # 102 -> 0.09961   ONE POLE
gp_0x374c += (S - gp_0x374c) * aR                    # 32-bit accumulator state
recon = gp_0x374c >> 4

if abs(s16(gp_0x6bfe)) < 20000:                      # 0x38218  gp-0x6bfe = model, via FUN_0003bc20
    res = (s16(gp_0x6bfe) - recon) + clampv(gp_0x6bfa, 20000)   # 0x38208
    mag = lerp(abs(res) * u16(0xC63AE) >> 10, RAM table gp-0x64b8..gp-0x640a)
    out = sign(res) * mag
    out = clamp(out, -u16(0xC6200), +u16(0xC6200))   # 8192
else:
    out = 0x7fff
gp_0x6b70 = out                                      # 0x382d2
```

### The mismatch, computed

`H_model(f) = (α_m /(1-(1-α_m)z^-1))²` with α_m = 0.13989 · `H_recon(f) = α_r/(1-(1-α_r)z^-1)` with α_r = 0.09961.
At DC both are exactly 1, so the LKAS command cancels perfectly at DC. Away from DC it does not.

| f (Hz) | \|H_model\| | \|H_recon\| | **\|ΔH\|** | Δphase |
|---|---|---|---|---|
| 2 | 0.9931 | 0.9929 | 0.041 | −2.4° |
| 6 | 0.9412 | 0.9412 | 0.120 | −7.3° |
| **7.8** | 0.9045 | 0.9061 | **0.152** | −9.6° |
| 15 | 0.7194 | 0.7442 | 0.249 | −19.5° |
| **21** | 0.5669 | 0.6229 | **0.285** | −27.2° |
| **28** | 0.4243 | 0.5129 | **0.293** | −34.8° |

(fs = 1000 Hz assumed — the control task is confirmed ~1 kHz; at fs = 500 Hz the same peak 0.293 simply
moves down to ~9–15 Hz, so the conclusion is **robust to the unresolved task rate**, only the band moves.)

**Interpretation [BELIEF]:** the observer knows the command but not *when* it was applied. Everything the
command does between ~6 Hz and ~28 Hz shows up in `gp-0x6b70` as an unexplained disturbance, is sign-LERPed,
and is fed into `gp-0x6ad6` — the torque-tracking reference the PID chases against the measured driver
torque. That is functionally the operator's self-interference picture, arriving through the filter mismatch
rather than through the torque sensor.

---

## §1 — THE LKAS COMMAND'S FULL INTERNAL PATH [EVIDENCE]

```
CAN 0x0E4  --(FUN_00052676, stores @0x5268c/0x526f2/0x52726/0x527c6)-->  gp-0x69ae   (LKAS setpoint)
   |  readers 0x29032, 0x29124 (FUN_00028ea6 = the LKAS/arbitration SM), 0x4e840
   v
FUN_00028ea6  (0x28ea6-0x2a30d)  arbitration + deliver-flag SM
   |  st.h @0x2a2ea  -->  gp-0x6b3c      (the arbitrated LKAS torque request)
   v
FUN_0002b422  (the 8-state ENABLE-byte FSM)
   0002b42e: ld.h -0x6b3c[gp],r12
   0002b42a/36/3c/46: clamp r12 to +-u16(0xC61B2)      <- "arbitration output clamp"
   0002b45c: st.h r12,-0x6b3a[gp]                       (mirror)
   0002b51e: st.b r14,-0x67a4[gp]                       (ENABLE byte, states 0..5)
   ---- builds an ASSIST-CHANNEL REQUEST STRUCT on the stack: ----
   0002b522: mov 0x1,r10          -> sst.b r10,0x0[ep]   CHANNEL ID = 1     <<<< LKAS IS CHANNEL 1
   0002b528: sst.b r14,0x1[ep]     channel command/state
   0002b52a: sst.h r0 ,0x2[ep]     field A (clamp +-0x4000) = 0
   0002b52c: sst.h r12,0x4[ep]     field B (clamp +-0x2800) = ** THE LKAS TORQUE **
   0002b52e: sst.h r0 ,0x6[ep]     field C (clamp +-900)    = 0
   0002b530: sst.h r0 ,0x8[ep]     field D (clamp +-20000)  = 0
   0002b532/38/3c: gains gp-0x697e, gp-0x697c, 0x400
   0002b53e: jarl 0x00025c32,lp
   v
FUN_00025c32  = the 11-channel REGISTRATION API.  For channel i it writes
   field A -> gp-0x62e0+2i    field B -> gp-0x62f8+2i    field C -> gp-0x6274+2i
   field D -> gp-0x633c+2i    gains   -> gp-0x6230/0x6218/0x6200 +2i
   v
FUN_00026c80  = the 11-CHANNEL MIXER (0x26c80-0x27801).  Per-channel static routing MODE
   from cal table 0xC4124..0xC412E (byte-read: [0,0,5,0,5,5,0,0,0,5,0]),
   per-channel ENABLE from 0xC4118..0xC4122 (byte-read: all 1).
   CHANNEL 1's mode = 0  =>  gp-0x62b0+2 <- gp-0x62f8+2 (the LKAS torque);  gp-0x62c8+2 = 0
   sum over enabled channels of gp-0x62b0+2i  ->  gp-0x3d88
   gp-0x6b4c = clamp(gp-0x3d88 + pol*((gp-0x6b4a * u16(0xC63CC)) >> 10), +-0x2800)   @0x276f0/0x27708/0x27716
        ** 0xC63CC byte-reads 0 **  => the second term contributes nothing in stock
   v
gp-0x6b4c  IS READ BY EXACTLY TWO CONSUMERS IN THE ASSIST PATH:
   (1) 0x3aa3e   FUN_0003aa2c  the aggregator  -> gp-0x6b94 -> governor -> ... -> gp-0x6b98 -> FOC
   (2) 0x3816c   FUN_00038148  the OBSERVER's reconstruction, gain 0xC63AA = 1024 = UNITY
   (other readers: 0x2785b4 region 0x285b4, 0x28b16, 0x276e2 - all inside the mixer/arb band)
```

**⇒ The LKAS command is a known input to the disturbance observer, at unity gain, by construction.**

### The parallel direct-injection route (also observer-visible)

Channels whose mode byte is **5** (channels **2, 4, 5, 9**) route their field-B torque to `gp-0x62c8+2i`
instead. That sum becomes:

```
gp-0x3d8c -> gp-0x6b4e  (clamp +-0x2800)                       st.h @0x27466
          -> FUN_00042ac6(sVar38)  called @0x277f6
             00042ac6: addi 0x2800,r6,r13 / addi -0x5001,r13,r0 / mov r6,r15
             00042ad0: bnc 0x42ad6 / movea 0x7fff,r0,r15
             00042ad6: st.h r15,-0x6afe[gp]           <- gp-0x6afe, ONE writer, ONE reader
   gp-0x6afe is read at 0x43ae0 in FUN_00042af8 and ADDED STRAIGHT INTO THE FINAL MOTOR COMMAND:
       iVar45 = clampv(gp-0x6afe, 0x2800) + uVar34         # uVar34 = corridor-bounded fwd command
       iVar18 = magnitude_bound(iVar45, gp-0x4f64)         # gp-0x4f64 = a current/torque ceiling
       gp-0x6b98 = clamp(iVar18, +-0x2000)                 # st.h @0x43b52 / 0x43dfc
```
`gp-0x6b4e` is **also** an observer lane (`0x3817c`, gain `0xC63A8` = 1024). So Honda covered this
bypass too. LKAS itself does **not** use it (channel 1 is mode 0).

**OPEN:** which subsystem owns channels 2/4/5/9 is not resolved. Callers of `FUN_00025c32` are
`FUN_00023ad2, FUN_00023fe2, FUN_0002b422 (=LKAS, ch1), FUN_0002c246, FUN_0002caa2, FUN_0002e52e,
FUN_000339cc, FUN_0003405a, FUN_0003a8a8, FUN_0003aff4` — 10 callers for 11 channels. Next step: read the
`mov N,r10` immediately before each `jarl 0x25c32`, exactly as done for `FUN_0002b422` at `0x2b522`.

---

## §2 — COLUMN-TORQUE SENSOR `gp-0x4f60`: writers and readers

🛑 **SELF-CORRECTION, 2026-08-10 round 2.** My first pass said *"no evidence the second encoding is used
for this cell."* **That was WRONG** and it was wrong for a specific, reusable reason — see
"METHOD CORRECTION" below. There are **7 real 6-byte accesses** to `gp-0x4f60`.

**Method (corrected):** whole-image Python LE byte scan over `[0x13000,0x100000)` for **both** encodings,
now validated against Ghidra (reproduces all 7 of Ghidra's 6-byte hits at the same addresses), plus
`search_instructions` as the cross-check.

**5 writers, all in the sensor-acquisition band** (`FUN_0007ec34` @`0x7f2ea`; `FUN_0007f3f8` @`0x7f934`,
`0x7f9c8`, `0x7fce6`, `0x7fd1a`). Both methods agree exactly on the writer set.

**≥76 reader instructions**, reconciled three ways:
- 66 four-byte, seen by **both** methods
- **7 six-byte** (`0x4c784` `FUN_0004c780`; `0x59bfa/0x59c02/0x59c44/0x59c4c` `FUN_00059912`;
  `0x5a0bc/0x5a0c4` `FUN_00059e7a`) — Ghidra sees these; my first Python scan did not
- **3 that PYTHON sees and GHIDRA DOES NOT**: `0x2d9a2`, `0x2dae6` (both `hw1=0x3724 hw2=0xb0a0` =
  `ld.h -0x4f60[gp],r6`) and `0x4f996` (`hw1=0x4f24` = `ld.h -0x4f60[gp],r9`). `get_function_by_address`
  returns **"No function found"** for all three ⇒ they sit in **unanalysed regions**, which
  `search_instructions` cannot scan while still reporting `truncated:false`
  (`instructions_scanned: 183570` against the ~185,693 the kit records). **Neither tool alone is complete
  here.**

The readers that matter for this question:

| addr | function | what it computes with the column torque |
|---|---|---|
| `0x3b908` | `FUN_0003b8f6` | plant model, branch B — 2-pole EMA α 0.8999, ×`0xC613A`, ±15, ×LERP(angle) |
| `0x36682` | `FUN_00036682` | `target = gp-0x6b48 + pol*((T_col * 0xC646C)>>15)`; slew-tracks it into `gp-0x6b46` |
| `0x3a6ca / 0x3a7ca` | `FUN_0003a382` | **the PID**: `error = T_col − clamp(gp-0x6ad6)` → `gp-0x6ad4` |
| `0x34392` | `FUN_00034350` | base-assist damper (`gp-0x6bd0`) |
| `0x34ace` | `FUN_00034a72` | boost shaper (`gp-0x6bbe`) |
| `0x36846` | `FUN_00036682` | second read in the hysteresis lane |
| `0x42c20` | `FUN_00042af8` | final-command former |
| `0x35aa4` | `FUN_000352b4` | `gp-0x6b86` lane |
| `0x2c480 / 0x2b69e / 0x2a992 / 0x29a90 / 0x28f26` | LKAS/arb band | arbitration gating |
| `0x1c09e / 0x1c0cc / 0x1c234` | diagnostics | DTC / reporting |
| `0x7e78e … 0x7fea8` | sensor band | acquisition, plausibility, shadow-compare |
| `0x4d8f6 · 0x4de12 · 0x4e452 · 0x4e8a2 · 0x4f996 · 0x4fc32 · 0x5004c · 0x55624 · 0x55c50 · 0x55f3e · 0x56542 · 0x5654a · 0x69c12 · 0x80f82 · 0x815c2` | UDS/CAN/telemetry | reporting copies |

**Other RAM copies of the column torque** (all confirmed by the record, re-seen here):
`gp-0x6a62` (voted, 5-coil MAX, decay-limited — indexes the mixer LERP at `0xC76FE`), `gp-0x6a5e`,
`gp-0x6a64`, `gp-0x3620`/`gp-0x361c` (the model's own two EMA states), `gp-0x4f68` (angular velocity,
**not** torque).

---

## §4 — IS THERE ANY FEED-FORWARD `T_driver_est = T_sensor ± K·T_cmd`?

### **NO — no such term exists anywhere in the driver-torque path.** [EVIDENCE, from the exhaustive
`gp-0x4f60` reader map above: every reader either filters it, LERPs it, or differences it against a
*reference*, and none of them adds a command-derived term to it.]

The nearest thing that exists is structurally different and already live: the PID's setpoint
`gp-0x6ad6` is built from the observer residual `gp-0x6b70`, so the *reference* — not the sensor — carries
command information.

### Disabled-but-present cells found (the §4 prize list)

| cell | stock | what enabling it would do | ever flown? |
|---|---|---|---|
| **`0xC404C`, `0xC4050`** (f32) | **0.0, 0.0** | Two zeroed taps of the **3-tap FIR on column torque inside the observer** (`0x3b9d2`–`0x3b9f6`). `[1,0,0]` is a pass-through; `[1,−1,0]` would make it a differencer, `[b0,b1,b2]` an arbitrary 2nd-order lead/lag. **This is a live, addressable filter with two spare coefficients sitting in the observer's column path.** | **never edited** — appears only in `KEEP`/verify loops of V58–V67 |
| **`0xC4080`** (K0) | **0** | pure-Coulomb friction in the model, relay-shaped | flagged NEVER-RAISE (relay hazard); untouched |
| **`0xC63CC`** | **0** | would feed the mixer output `gp-0x6b4a` into the `gp-0x6b4c` lane | never edited |
| **`0xC64C8`** (byte) + `0xC61D4` | test-mode selector | `==1` pins `gp-0x6b08` to cal `0xC61D4`; `==2` adds `0xC61D4` to `gp-0x6acc` and clamps ±0x3000. A **command-offset injection point** (`0x43c1c`–`0x43a44` region, decompile lines 633–645). | `0xC64C8` in 2 scripts, `0xC61D4` in **0** |

⚠ **None of these implements the compensation the brief hoped for.** The genuine finding is that the
compensation **already exists and is correct at DC** — it is the *filter matching* that is broken.

---

## §5 — THE AGGREGATOR AT `0x3ACA8` (`FUN_0003aa2c` → `gp-0x6b94`)

Normal path (`gp-0x67ac != 1`). No per-lane gain cals here — each lane is validity-clamped then summed.

| # | RAM cell | clamp | written by | physically | live? | in the OBSERVER's recon? |
|---|---|---|---|---|---|---|
| 1 | `gp-0x6ade` | ±0x400 | **UNRESOLVED** — 0 writers by two independent methods (Python Format-VII scan **and** Ghidra `search_instructions -0x6ade`, which returns exactly 1 hit: the reader at `0x3aa48`). Must be register-indirect. | unknown | reads live | ✗ |
| 2 | `gp-0x6b4c` | ±0x2800 | `FUN_00026c80` @`0x276f0/0x27708/0x27716` | **Σ of assist channels routed in mode 0 — INCLUDES LKAS (channel 1)** | ✔ | **✔** gain `0xC63AA`=1024 |
| 3 | `gp-0x6ad4` | ±0x2800 | `FUN_0003a382` @`0x3a8a0` | the PID on `error = T_col − gp-0x6ad6` | ✔ | ✗ (correctly — it *is* the feedback) |
| 4 | `gp-0x6b62` | ±0x2000 | `FUN_00036388` @`0x36514/0x3652c/0x36544` | (not characterised this session) | ✔ | ✗ |
| 5 | `gp-0x6b26` | ±0x400 | `FUN_00036c12` @`0x36cf0` | friction compensation | ✔ | ✔ `0xC63A6`=1024 |
| 6 | `gp-0x6bbe` | ±0x800 | `FUN_00034a72` @`0x3508c/0x350a0/0x350ae` | **boost shaper** | ✔ | ✔ `0xC63A2`=1024 |
| 7 | `gp-0x6bd0` | ±0x800 | `FUN_00034350` @`0x34730/0x34744/0x34752` | **base-assist damper** | ✔ (mode-gated) | ✔ `0xC63A0`=1024 |
| 8 | `gp-0x6b86` | ±0x3000 | `FUN_000352b4` @`0x35ac0/0x35ace` | (not characterised) | ✔ | ✗ |
| 9 | `iVar21` → mirror `gp-0x6adc` | ±0x2000 | inline in `FUN_0003aa2c` | **rate lane A** (`gp-0x6ac0`-indexed LERP; cals `0xC743E/0x7444`) | ✔ | ✗ |
| 10 | `iVar16` → mirror `gp-0x6ada` | ±0x2000 | inline in `FUN_0003aa2c` | **rate lane B** (cals `0xC7440/0x7442/0x7446`, deadband `0xC71F6`) | ✔ | ✗ |
| 11 | return of `FUN_00036682` = `gp-0x6b46` | ±0x200×1024 | `FUN_00036682` @`0x3681a` | column-torque hysteresis / stick-slip tracker (cals `0xC719C`, `0xC71A6`, `0xC73D2`, `0xC646C`) | ✔ | ✔ `0xC63A4`=1024 |

Plus, **outside** the aggregator and added at the very end of `FUN_00042af8`:

| — | `gp-0x6afe` (= `gp-0x6b4e`) | ±0x2800 | `FUN_00042ac6` @`0x42ad6`, fed from `FUN_00026c80` @`0x277f6` | Σ of assist channels routed in **mode 5** (channels 2/4/5/9) — **direct injection, bypasses the aggregator, governor and corridor** | ✔ | ✔ `0xC63A8`=1024 |

⚠ **Correction to the record:** the memory `accord-aggregator-lane-mirrors-6ada-6adc` says `gp-0x6ada` = r24
and `gp-0x6adc` = r26. In the decompile it is the other way round: `gp-0x6adc = iVar21` (the
`0xC743E/0x7444` lane) and `gp-0x6ada = iVar16` (the `0xC7440/0x7442/0x7446` lane), stores at `0x3ad24`/
`0x3ad2c` region. Flagging, not editing — ask before changing that memory.

**Coverage summary:** the observer reconstructs **6 of the 12** contributions. It is missing
`gp-0x6ade`, `gp-0x6b62`, `gp-0x6b86`, and **both rate lanes** — and deliberately excludes `gp-0x6ad4`.
Every one of those missing lanes also lands in the residual as an unmodelled disturbance, on top of the
filter mismatch. (The two rate lanes are Lever B's territory — which may be part of why V88's r24 change
moved the delivered command's 15–22 Hz content.) [BELIEF on the last clause.]

---

## §6 — `0xC646E`, the INERTIA gain

- **Value: 1428** (u16, `tp+0x746e`). **One reader**: `0003bb92: ld.hu 0x746e[tp],r7`, inside `FUN_0003b8f6`.
- **What it multiplies** (`0x3bb96`–`0x3bbaa`): a **double-EMA'd time derivative of the motor rate** —
  i.e. **motor angular ACCELERATION**:
  `d = (pol*s16(gp-0x6abc)*12 − gp-0x3618) * 0.5 * 17.453293` (17.453293 = 1000·π/180, deg/s→mrad/s),
  EMA'd twice at α = `0xC40D6`/4096 = 0.06006, then `× 1428 × 2^-24`, then clamped ±10.
- **Its input signal is the MEASURED motor rate `gp-0x6abc` ← `gp-0x4f50` (resolver/motor electrical rate).
  It is NEVER fed the LKAS command.** [EVIDENCE — `gp-0x6abc` is the only rate source in the function,
  loaded once at `0x3b91c`.]
- **Would raising it add motor-acceleration feedback?** It already **is** motor-acceleration feedback, and
  it is **subtractive**: `model − (friction + inertia)`. Because the measured acceleration includes
  acceleration caused by the LKAS overlay, **the inertial part of the operator's coupling is already
  cancelled — in the observer.** Raising `0xC646E` makes the observer *credit more* of the residual to
  inertia, i.e. shrinks the residual during accelerations.
  🛑 **But it is inside the observer only. It does NOT add an inertia-compensation torque to the motor
  command** — nothing in `FUN_0003b8f6` writes a command; its outputs are `gp-0x6bf6`, `gp-0x6bfc`,
  `gp-0x6c00` and the two mirrors. So "inertia compensation is the textbook cancellation and may already
  exist as a single cal" is **half true**: it exists, but it compensates the *estimate*, not the *plant*.
- **Sizing check:** the term is hard-clamped at ±10.0 in model units, and the model output scale is 2639,
  so its authority is ±26,390 pre-clamp against a ±20,000 output clamp ⇒ **the inertia term can single-
  handedly saturate the model output**. At stock 1428 the clamp is reached when the double-EMA'd
  acceleration exceeds 10·2²⁴/1428 ≈ 1.175e5 internal units. **I have not converted that to a physical
  °/s²** — that needs the `gp-0x4f50` counts-per-rad/s scale, which the record marks unresolved.
- Lineage: `0xC646E` appears in 5 build scripts; V87's row records *"`0xC646E`'s sizing figure is an
  unmeasured estimate"* and it has **never been edited**.

---

## §7 — MINIMAL-EDIT OPPORTUNITIES, ranked by implementation cost

### TIER 1 — SINGLE-CAL EDITS (no code change)

| rank | edit | effect | evidence / risk |
|---|---|---|---|
| **1** | **`0xC63AC` 102 → 65** (1 byte: `66 00` → `41 00`) | Best 1-pole fit of the reconstruction filter to the model's 2-pole filter. **Peak \|ΔH\| 0.293 → 0.182 (−38 %); at 7.8 Hz 0.152 → 0.108; at 21 Hz 0.285 → 0.180.** Exhaustive search over all 1024 values; 65 is the optimum at both fs = 1000 and fs = 500. | 🛑 **`0xC63AC` is on `build_v83a_tva.py`'s explicit must-not-move list** (line 337/369) — a "≤1.32× bound" in V83a depends on it. **That bound must be re-derived before this flies.** Lowering α also slows the reconstruction's DC settling, so a step in base assist briefly reads as a residual. |
| **2** | **`0xC40D4` 573 → 4096 AND `0xC63AC` 102 → 1024** (both filters transparent) | **\|ΔH\| = 0 at every frequency** — the LKAS command cancels *exactly* out of the residual. | 🛑 **HIGH RISK, do not fly blind.** `0xC40D4` also scales the friction and inertia terms via `model`, and removing the actuator-lag model changes what the observer thinks the plant is. Also α = 1 makes both filters memoryless ⇒ full HF noise into the residual. **GATE 2 (closed-loop stability) applies.** |
| **3** | **`0xC404C` / `0xC4050` 0.0 → non-zero** | Turns the observer's column-torque pass-through into a real 2nd-order FIR. This is the *only* frequency-shaping freedom the observer has that costs zero code. | Two f32 cells, 8 bytes, never touched. **Requires a design pass** — the taps sit *before* a ±15 clamp and a LERP, so a large `b1` will clip. |
| **4** | `0xC646E` 1428 → higher | More motor-acceleration credit inside the observer ⇒ smaller residual during transients | ±10 clamp is close; see §6. Sizing is an **unmeasured estimate** — the record already says so. |

### TIER 2 — SINGLE IN-PLACE LOAD REPOINT (change one 16-bit displacement)

**The brief asked specifically: is there a load in the driver-torque path whose source could be repointed
to a cell already holding the LKAS command or a scaled version of it?**

**Answer: YES, and there are two clean candidates.** [EVIDENCE for the encodings; BELIEF that either is
*desirable*]

| site | current instruction | repoint to | what it would build |
|---|---|---|---|
| `0x3b908` | `ld.h -0x4f60[gp],r9` (model branch B input) | `-0x6b4c` (LKAS lane) or `-0x6b3a` (the clamped LKAS torque mirror, `st.h` @`0x2b45c`) | Replaces the column-torque term in the model with an explicit LKAS feed-forward. **Changes the model's meaning entirely** — not recommended, but it is the cheapest possible "make the command visible here" edit. |
| `0x3816c` | `ld.h -0x6b4c[gp],r14` (observer's LKAS lane) | `-0x6b3a` | Feeds the observer the **pre-mixer, pre-clamp** LKAS torque instead of the post-mixer channel sum, removing the mixer's own clamp/latency from the reconstruction arm. |

⊕ **Free, zero-blast-radius telemetry for testing any of this:** `gp-0x6ada` and `gp-0x6adc` are post-clamp
mirrors with 1 writer / 0 readers, and `gp-0x6ae0`/`gp-0x6ae2` (inertia×1024 / friction×1024) are the same.
`gp-0x6bf6` (model **before** friction/inertia) vs `gp-0x6bfc` (**after**) is a ready-made A/B pair, and
`gp-0x374c >> 4` is the reconstruction itself — **probing `gp-0x6bfe − (gp-0x374c>>4)` directly measures
the residual this whole finding is about.**

### TIER 3 — CODE CAVE
Not required for anything above. **Do not.**

---

## OPEN QUESTIONS / WHAT I COULD NOT CLOSE

1. **`gp-0x6ade`'s writer is UNRESOLVED.** Two independent methods return zero (Python Format-VII scan over
   `[0x13000,0x100000)`; Ghidra `search_instructions -0x6ade` = 1 hit, the reader). It is an aggregator lane
   that reaches the motor. **Next step:** Ghidra `analyze_dataflow` / pointer analysis on `0xFEDF1522`, or a
   scan for `movhi 0xfedf` + `movea`/`st.h` pairs — Ghidra does not resolve those into xrefs.
2. **Which subsystems own assist channels 2/4/5/9** (the mode-5 direct-injection channels). **Next step:**
   read the `mov N,r10` before the `jarl 0x25c32` in each of the other nine callers.
3. **`FUN_00036388` (`gp-0x6b62`) and `FUN_000352b4` (`gp-0x6b86`)** are un-characterised aggregator lanes
   that the observer does **not** reconstruct. **Next step:** `decompile_function` on each.
4. **The task rate of `FUN_0003b8f6` / `FUN_00038148`** is assumed 1 kHz. The mismatch **peak magnitude is
   rate-invariant (0.293)** but the band it sits in is not. **Next step:** find the scheduler slot that
   calls `FUN_0003b8f6`.
5. **Physical scale of `gp-0x4f50`** (counts per rad/s) — needed to size `0xC646E` in real units. The record
   already marks this unresolved.
6. **V83a's "≤1.32× bound"** that depends on `0xC63AC` = 102 must be re-read before Tier-1 rank 1 flies.

---
---

# ROUND 2 — 2026-08-10, after team-lead resolved `gp-0x6b4e` = `gp-0x6afe`

Accepted and folded in: the LKAS overlay **is** cancelled in Branch B, and `docs/FEASIBILITY-SELF-INTERFERENCE-CANCELLATION.md` §2.1 ("no compensation, decoupling or cancellation term anywhere") is
**REFUTED**. My channel-1 result and team-lead's `gp-0x6afe` result are the two halves of the same
architecture: **every assist channel's torque is covered in Branch B, whichever of the two routes it takes.**
LKAS specifically takes the `gp-0x6b4c` route (channel 1, mode byte `0xC4125` = 0), **not** the
`gp-0x6b4e`/`gp-0x6afe` route (that is for the mode-5 channels 2/4/5/9).

⚠ **One reconciliation for team-lead:** his leak figures (0.005 DC / 0.196 @7.79 / 0.360 @21) include a
"+1 tick" on Branch A that mine (0.000 DC / 0.152 / 0.285) does not. The extra tick is presumably the
`gp-0x6bfc` -> `FUN_0003bc20` -> `gp-0x6bfe` hand-off landing in a later task pass. **I have not verified that
tick.** It moves the leak the same direction, only larger. Whoever quotes a number should say which.

---

## §4 — THE THREE ZEROED FIR TRIPLES: what they can and cannot do

### There are THREE, not two [EVIDENCE — f32 sweep of `0xC4000`-`0xC4060`]

| triple | c1 | c0 | c2 | sole readers | branch |
|---|---|---|---|---|---|
| `0xC4018/1C/20` | **1.0** | **0.0** | **0.0** | `0x3b6c0 / 0x3b6c4 / 0x3b6d4` — **`FUN_0003b66a`** | a SECOND column-torque estimator (`FUN_0003b66a` also reads `gp-0x4f60` @`0x3b672`), immediately preceding `FUN_0003b8f6` |
| `0xC4024/28/2C` | **1.0** | **0.0** | **0.0** | `0x2389e / 0x2396a / 0x23926+0x2392e+0x2394a` — `FUN_00023xxx` (an assist-channel caller band) | third instance |
| `0xC4048/4C/50` | **1.0** | **0.0** | **0.0** | `0x3b9d2 / 0x3b9de / 0x3b9ee` — **`FUN_0003b8f6`** | **the observer's column branch** |

**Width trap confirmed and defused:** all six of the zero/one cells read `0x0000` as u16 because
`1.0f = 0x3F800000` puts its non-zero bytes in the *upper* halfword. Read as f32. Sibling set
`0xC4018/1C/20` verified as requested.

The exact arithmetic (`0x3b9c6`-`0x3b9f6`), states confirmed:

```python
out[n] = f32(0xC4048)*y[n] + f32(0xC404C)*y[n-1] + f32(0xC4050)*y[n-2]
#        gp-0x363c = y[n-1]   gp-0x3638 = y[n-2]     then clamp(out, -15, +15)
```

### Q: can `c0`/`c2` phase-align Branch A against Branch B? **NO — twice over.** [EVIDENCE]

**Reason 1 — wrong branch, structural.** The model is
`model = EMA2(cmd*pol/1024) + FIR(EMA2(T_col))*K*w(angle)`. The A-vs-B leak lives **entirely in the first
term**. The FIR multiplies `T_col`, an *additive* term. **It cannot alter the command's transfer function
at all**, at any coefficient. This kills the lead item as a phase-alignment lever outright.

**Reason 2 — no phase authority, even in principle.** The taps are **one sample apart**. Whatever the task
rate, a 3-tap FIR spans **2 samples**. To supply the -30.9 deg that V88 measured between command and column
at 7.79 Hz you need **11.0 samples (11.0 ms) of delay**. Not representable:

| f (Hz) | deg/tap @1 kHz | samples needed for 30.9 deg |
|---|---|---|
| 7.79 | 2.80 | **11.02** |
| 21 | 7.56 | 4.09 |
| 28 | 10.08 | 3.07 |

### Q: what CAN the taps do? [EVIDENCE — swept]

| taps (c1,c0,c2) | abs H 7.8 Hz | ph 7.8 | abs H 21 Hz | ph 21 | abs H DC |
|---|---|---|---|---|---|
| **(1, 0, 0)** stock | 1.0000 | 0.00 | 1.0000 | 0.00 | 1.000 |
| (1, -1, 0) differencer | **0.0490** | +88.6 | 0.1319 | +86.2 | **0.000** |
| (1, -0.5, 0) | 0.5012 | +2.8 | 0.5086 | +7.4 | 0.500 |
| (2, -1, 0) | 1.0024 | +2.8 | 1.0172 | +7.4 | 1.000 |
| (1.5, -1, 0.5) | 0.9988 | 0.00 | 0.9914 | +0.07 | 1.000 |

Three honest readings:

1. **A differencer annihilates the band** (abs H = 0.049 at 7.8 Hz) rather than shaping it. At 1 ms spacing
   a first difference is a 1 kHz-scale operator; at 8 Hz it is essentially a null.
2. **Any tap set whose sum is not 1 rescales DC**, i.e. changes the *steady* driver-torque estimate the whole
   assist law is built on. That is a much bigger change than the frequency shaping it buys.
3. The most you can buy in-band is a few degrees of lead (**+2.8 deg at 7.8 Hz**) for a full unit of
   coefficient. **The taps are a gain trim, not a filter, at the frequencies of interest.**

=> **RECOMMENDATION: the FIR taps should be DE-RANKED from "most interesting candidate in the kit" to
"gain trim with a DC side-effect."** They are cheap (a float write, no cave) but they have no authority
where the problem is. **I would not spend a build on them.** [BELIEF, resting on the two EVIDENCE
arguments above.]

---

## §4 — WHAT I FOUND INSTEAD: the observer HAS a per-channel declared-disturbance input, and LKAS declares ZERO

This is the real answer to *"a disabled-but-present compensation path"*.

`FUN_00025c32`'s **field D** (struct offset **+8**, clamp **+-20000**) is not a command field at all:

```
field D  -> gp-0x633c+2i                                     (FUN_00025c32)
         -> gp-0x6324+2i   in modes 0,1,2,3,5 ; forced 0 in modes 4,6,7   (FUN_00026c80 loop 1)
         -> SUM over all 11 channels, *** UNGATED by the enable byte ***  (FUN_00026c80 loop 2)
         -> gp-0x3d90  (32-bit accumulator)
         -> clamp +-20000 -> gp-0x6bfa (+ shadow gp-0x4cfa)  st.h @0x273b0/0x273c8/0x273d6
         -> FUN_00038148 @0x38208 :   res = (model - recon) + gp-0x6bfa
```

**Why this is the declared-disturbance slot and not just another torque lane** [EVIDENCE]:

- Fields A/B/C carry **command-side** clamps (+-0x4000, +-0x2800, +-900). **Field D's clamp is +-20000 —
  bit-for-bit the model's OWN output clamp** at `gp-0x6bf6`/`gp-0x6bfc` (`0x3ba96`/`0x3bbce`). It is
  denominated in **observer units**, not command units.
- It is summed **without** the per-channel enable gate that fields A and B pass through.
- Its only destination is the residual sum. It touches nothing else.

=> **Honda gave every assist channel a slot to say "expect this much torque I am applying that your
reconstruction cannot see."** `gp-0x3d90` — which ObserverMatch flagged as unresolved and load-bearing —
is exactly that sum. **RESOLVED.**

**LKAS passes ZERO into it:** `0002b530: sst.h r0,0x8[ep]` (bytes `84 04`).

**And that is almost certainly CORRECT as shipped**, because LKAS's torque is *already* fully in the
reconstruction via `gp-0x6b4c` at unity. Filling field D with the command would **double-count** it.
Recording the mechanism, not recommending the edit.

### The one-byte edit, derived and stated for the record (NOT a recommendation)

From the seven `sst.h` encodings in `FUN_0002b422`, the Format-IV field layout resolves cleanly —
`hw = (reg2 << 11) | 0x480 | (disp >> 1)`:

| addr | insn | bytes | hw | reg2 |
|---|---|---|---|---|
| `0x2b52a` | `sst.h r0, 0x2[ep]` | `81 04` | `0x0481` | 0 |
| `0x2b52c` | `sst.h r12,0x4[ep]` | `82 64` | `0x6482` | 12 |
| `0x2b530` | `sst.h r0, 0x8[ep]` | `84 04` | `0x0484` | 0 |
| `0x2b532` | `sst.h r16,0xa[ep]` | `85 84` | `0x8485` | 16 |

=> `sst.h r12,0x8[ep]` = `0x0484 | (12<<11)` = `0x6484` = bytes **`84 64`**, i.e. a **single byte**
`0x04 -> 0x64` at file offset **`0x2B531`**.

**Scale mismatch if anyone ever does this:** `r12` is in raw command counts (+-0x2800) while field D is in
model units (x `0xC6468`/1024 = x2.577). It would land at **1/2.577 of nominal**. And it double-counts. I am
recording the encoding because it is the architecturally-correct injection point for *any* future
observer-bias term — not because this particular payload is right.

---

## §5 — the aggregator table

Unchanged from Round 1 above (12 contributions, writers, clamps, observer coverage). Two updates:

- **`gp-0x6ade`'s null is now on a VALIDATED method.** Re-run with the corrected 6-byte decoder:
  **0 writers in the 4-byte form AND 0 in the 6-byte form**, whole-image, against a decoder that
  reproduces all 7 of Ghidra's `gp-0x4f60` 6-byte hits exactly. Ghidra independently returns 1 hit total
  (the reader at `0x3aa48`). => **`gp-0x6ade` is written register-indirect or never written.** Still OPEN,
  but the null is now trustworthy rather than tool-shaped.
- `gp-0x6b46`'s writer (mine to keep) is `FUN_00036682` @`0x3681a`, self-referential: the function reads
  `gp-0x6b46` at entry (`0x3668a`), computes `target = gp-0x6b48 + pol*((T_col*0xC646C)>>15)`, slew-tracks
  toward it with cals `0xC719C`/`0xC71A6`/`0xC73D2` and a dwell counter `gp-0x6a80`, then writes back.
  **A stick-slip / hysteresis tracker on the column torque**, and it is both an aggregator contribution
  (the 11th) and a Branch-B lane at unity.

---

## §6 — `0xC646E`: team-lead's "lagged velocity damper" reading is **CONFIRMED** [EVIDENCE]

`term = EMA2(diff(rate), alpha = 0xC40D6/4096 = 0.06006) * 0xC646E * 2^-24`, **subtracted** from the model.
The `diff` supplies +90 deg; the 2-pole EMA (corner **9.56 Hz** at fs = 1 kHz) eats it.

| f (Hz) | phase vs RATE | Re/abs H | reading |
|---|---|---|---|
| 1 | +78.6 | 0.198 | inertia-like (leads rate) |
| 2 | +67.4 | 0.384 | already turning |
| 4 | +46.5 | 0.688 | mixed |
| **7.79** | **+14.7** | **0.967** | **damper (in phase with rate)** |
| 12 | -9.1 | 0.987 | damper |
| **21** | **-36.0** | **0.809** | damper |
| **28.5** | **-46.8** | **0.684** | damper |

**Real part vs rate is positive and large (0.68-0.99) across the whole 7.79-28.5 Hz span.** True inertia
compensation would need Re = 0, Im = 1. It is inertia-like **only below ~1 Hz**. => **team-lead's golden-model
note is right; `0xC646E` is a lagged velocity damper as delivered.**

**What raising it would actually do:** increase a rate-proportional term that is **subtracted** from the
model => residual falls with rate => `gp-0x6b70` falls => the tracking reference `gp-0x6ad6` falls =>
`error = T_col - ref` rises => the PID commands **more** assist as the motor moves faster. Following the
verified polarity chain, **raising `0xC646E` makes the wheel LIGHTER with rate** — it is not damping the
delivered torque, it is un-damping it. **[BELIEF]** — the polarity chain is EVIDENCE
(`accord-friction-polarity-more-assist`), but I have not re-walked all nine links this session, and the
+-10.0 clamp (= +-26,390 against a +-20,000 output clamp) means the term can saturate the model output on
its own, which would change the answer in the large-signal regime.
Frozen at **1428 on every image V38-V89** per team-lead's byte read — never written in 51 builds.

---

## §7 — MINIMAL-EDIT RANKING, re-ranked after Round 2

| tier | lever | verdict |
|---|---|---|
| **cal, 1 cell** | `0xC63AC` 102 -> 65 (Branch-B IIR) | **still the best single-cal lever.** Peak leak 0.293 -> 0.182 (-38%), optimal over all 1024 values at fs 1000 **and** 500. Blocked on V83a's "<=1.32x bound". ObserverMatch owns the GATE-2 call. |
| **cal, 1 cell** | `0xC40D4` 573 -> 842 (ObserverMatch's proposal) | his to size; note V86 already flew 573->**286** = the *wrong direction*, 2.26x worse leak, and read null on frequency |
| **cal, 2 cells** | `0xC40D4`->4096 **and** `0xC63AC`->1024 | leak = 0 at every frequency, but deletes the actuator-lag model and makes both arms memoryless. GATE 2. |
| **float, 2 cells** | `0xC404C` / `0xC4050` | **DE-RANKED — wrong branch and no phase authority.** ~+2.8 deg/unit at 7.8 Hz, and any non-unity tap sum rescales the DC driver-torque estimate. Do not spend a build. |
| **1 byte, in place** | `0x2B531` `04`->`64` (LKAS -> observer field D) | mechanism recorded, **not recommended** — double-counts and is 2.577x under-scaled |
| **cal, 1 cell** | `0xC646E` | it is a velocity damper, not inertia comp; raising it lightens the wheel with rate. Frozen 51 builds. |
| **cave** | — | not required for anything above |

---

## METHOD CORRECTION — worth propagating to the skill file

**1. The 6-byte extended-displacement formula's halfword indices are off by one as commonly applied.**
The memory `accord-gp4f60-two-encodings-enumeration-trap` gives
`disp = (sext16(hw2)<<7) | ((hw1>>4)&0x7F)`. Applied to the **first** two halfwords of the instruction that
yields garbage. The correct reading is that `hw1`/`hw2` in that formula mean the **second and third**
halfwords:

```
6-byte form:  [hw0 = opcode/reg]  [hw1]  [hw2]
disp = (sext16(hw2) << 7) | ((hw1 >> 4) & 0x7F)      # hw2 = THIRD halfword, hw1 = SECOND
reg1 (base) = hw0 & 0x1F   (= 4 for gp)   opcode = (hw0 >> 5) & 0x3F   (0x3C / 0x3D seen)
```

Worked example, `0x59bfa` = `ld.h -0x4f60[gp],r6`: bytes `84 07 07 32 61 ff` => hw0=`0x0784`, hw1=`0x3207`,
hw2=`0xff61` => `(sext16(0xff61)<<7) | ((0x3207>>4)&0x7F)` = `(-159<<7) | 0x20` = `-20352 + 32` = **-0x4F60** OK.
**Validated:** the corrected scanner reproduces all 7 of Ghidra's 6-byte `gp-0x4f60` hits at the same
addresses, and finds **12 more 6-byte accesses to `gp-0x6b98`** (`0x59a44`-`0x5a0aa`, the CAN telemetry
packer band) that a 4-byte-only scan misses entirely.
**Every "no 6-byte form" null I reported in Round 1 was computed with the broken decoder and is VOID.**
Re-run with the corrected one, `gp-0x6ade` still reads 0 — that null survives.

**2. Fresh reproduction of the `search_instructions` undercount, with adjudication.**
`search_instructions -0x4f60` returned 73 matches, `truncated: false`, `instructions_scanned: 183570`.
Python found **3 more**: `0x2d9a2`, `0x2dae6` (`hw1=0x3724 hw2=0xb0a0`) and `0x4f996` (`hw1=0x4f24`), all
decoding as valid `ld.h -0x4f60[gp]`. `get_function_by_address` returns **"No function found"** for all
three => unanalysed regions, invisible to Ghidra, real in the bytes.
=> **On this program neither tool alone is complete.** Ghidra sees the 6-byte form Python misses; Python
sees the unanalysed regions Ghidra misses. **A load-bearing enumeration needs BOTH, with the set
difference adjudicated address by address.**
