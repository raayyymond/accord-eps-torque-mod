# HANDOFF 2026-07-30 — the V58 drive: the grinding is creep-only and engagement-gated, and the boost-amplitude index is the new mechanism

**Predecessor:** `handoffs/2026-07/HANDOFF-2026-07-30-v57-drive-two-symptoms-and-v58.md`.
**Session shape:** orchestrated. Three parallel rlog analysts (spectral A/B, probe decode, health/override)
plus one `firmware-codepath-tracer`. Every load-bearing claim below was re-derived by the orchestrator
with a second method before being written down — and two subagent claims did not survive that check.

---

## 1. What was driven

**V58 flashed and driven, route `2b` (`75604b0a432fdc89_0000002b--7926e8f7e5`), 14 segments, ~14 min,
83,959 frames.** A normal commute, deliberately *not* a probe route: the operator drove to work and
applied driver-side torque by hand to make the sharp turns, so **every large steering event on this route
is driver-applied, not comma-commanded.**

Route structure (verified; my first reading of it was wrong and a subagent corrected me):
- seg 0 — parked, LKAS off, 61 s.
- seg 1 — manual pull-out t<13; **LKAS engages t≈15**; *two* engagement runs, 15.0–47.3 and 56.6–60.0,
  with disengaged-**moving** stretches at 7.7–14.9 and 47.3–56.6.
- segs 2–12 — engaged; segs 7–10 highway at 100–110 km/h. **Engagement ends seg 12 t≈49.3.**
- seg 13 — 60 s of manual parking at 0.5–4.96 m/s.

### V58 is flight-clean

`steerUnavailable` / `steerTempUnavailable` / `canError` / `controlsMismatch` / `immediateDisable`:
**zero occurrences across all 14 segments.** The only flagged events are `commIssue` ×2 and
`selfdrivedLagging` ×1, all at seg 0 t≈8.5 s **while still in `wrongGear` before the drive started** —
a boot transient, unlike route 28 which produced a real mid-drive soft-disable. One `steerSaturated`
warning, no disable. `selfdriveState` never enters `softDisabling` during the drive.

`STEER_STATUS` (`0x18F` byte4 bits **7:4**) is **0 in 83,959/83,959 frames**. **`ST==4`: 0** — extends
V57's 0/37,922 to a combined 121,881 clean frames; the V42-fixed state-4 governor has not resurfaced.
`ST==3` is also 0 (V57 route 29 saw 120, all at `vEgo == 0.000`; this route simply never caught that
transient — absence of a rare condition, not a contradiction). Probe low bits `probe & 0x07 == 0b111`
with zero exceptions, checked two ways. `0x14A`/`0x18F` both lock at 100.00 Hz in every driving segment.

---

## 2. 🛑 The collinearity confound is BROKEN — the grinding requires applied LKAS torque

`STATE.md` has carried a caveat that invalidated every engagement ratio on record (877×, 786×, 14,750×,
27.7×): **engagement and motion were collinear**, no speed bin had windows in both arms, so those were
moving-vs-stopped contrasts wearing an engagement label.

**Route `2b` breaks it.** Segment 13 gives ~60 s of *moving but disengaged* at 0.5–4.8 m/s, against
engaged creep in segs 1/2/11/12 at overlapping speeds.

| statistic | value |
|---|---|
| amplitude ratio, speed-matched 1.5–2.0 / 4.0–4.5 / 4.5–5.0 m/s | 16.5× / 20.3× / 11.3× ⇒ pooled **13.4×** [boot 95% 3.9–19.8], MWU p = 6.1e-6 |
| speed **+ effort** matched (nearest-neighbour) | **16.9×** median, 17/18 pairs > 1 |
| time-occupancy, 18–26 Hz envelope > 300, matched creep 0.5–5.0 m/s | engaged **27.8%** of 53.4 s vs disengaged **0.15%** of 65.8 s ⇒ **184×** |
| share of all grinding time that is LKAS-applying | **99.3%** |

**The confounds run AGAINST the engaged arm**, so these are floors: at 1.0–3.0 m/s the *disengaged* arm
has |ang| 167.2° vs 9.0° and sustained effort 1638 vs 205. More angle, more driver input, less 18–26 Hz.

### The statistic that actually settles it is presence, not amplitude

| | engaged | disengaged |
|---|---|---|
| 18–26 Hz peak prominence | median **122.7×**, max 1894× | median **3.6×**, max 13.3× |
| peak-frequency scatter | sd **1.08 Hz** | sd 2.49 Hz |

The disengaged "peak" wanders 15–29.9 Hz window to window — it is the argmax of a broadband floor, not a
mode. **There is no 20–25 Hz resonance in the disengaged arm at all.** That is immune to the angle and
effort confounds a ratio has to argue around. Parked floor for scale: seg 0 envelope p99 = 6.7.

**Sharpest single evidence — the disengage at seg 12 t≈49.3, same road, one second apart, constant speed:**

```
t=48.75  SCA=1  v=4.94  env18-26 = 750.4   driver effort  101
t=49.75  SCA=0  v=5.08  env18-26 =  36.5   driver effort 2193    <- 20.6x collapse
```

It stays collapsed for 6 s while the driver works the wheel *harder*. Averaged over 2 s windows the same
transition gives a conservative 8.5×. Only one transition survives strict speed-matching, so treat n=1.

🛑 **Hands-off could not be conditioned on.** Zero windows in any qualifying speed bin were fully
hands-off in *either* arm — the operator had hands on the wheel throughout a normal commute. Every number
above is "any hands", matched on effort instead. Reported, not worked around.

---

## 3. Three corrections to the record

### 3a. The frequency law does not reproduce — it is a FIXED ~20.9 Hz line

Recorded: `f ≈ 0.177·v + 20.48`. Strict 18–26 Hz band, sub-bin interpolated peak, speed stable within
1.5 m/s:

| prominence cut | n | v span | slope a | |a−0| | |a−0.177| |
|---|---|---|---|---|---|
| >5× | 75 | 1.13–17.54 | −0.0045 ± 0.0362 | 0.12σ | **5.01σ** |
| >10× | 51 | 1.13–17.54 | −0.0467 ± 0.0316 | 1.48σ | **7.09σ** |
| >20× | 31 | 1.13–17.54 | +0.0162 ± 0.0433 | 0.37σ | **3.72σ** |
| >50× | 23 | 1.13–15.64 | +0.0312 ± 0.0453 | 0.69σ | **3.22σ** |

Model-free per bin: 20.65 / 20.83 / 21.90 / 21.50 / 21.61 / 20.46 Hz over 0–20 m/s, against a predicted
20.66 → 23.49. **a = 0.177 is rejected at 3.2–7.1σ; a = 0 is not.**

⚠ **Two wrong fits were produced on the way to this, both from search-band leakage**, and the lesson is
worth keeping: a 15–30 Hz or even 17–28 Hz band catches the **ratchet's 2nd harmonic** (2×8.0–8.9 Hz =
16–17.8 Hz) at road speed, and the argmax then steps from the 20.9 Hz grinding down to ~15 Hz, faking a
*negative* slope. A creep-only window with a 3.35 m/s lever arm fakes a *positive* one. **Use a strict
18–26 Hz band plus a presence test.**

⚠ Provenance worth citing before rewriting anything: the recorded law came from a **pooled cross-route**
fit (r = +0.650) whose own source warned *"steering angle shifts it ±2 Hz."* On this route
`spearman(v, |ang|) = −0.728`. A pooled fit could manufacture a speed slope out of an angle gradient.
**Re-run the strict-band test over the V55/V56/V57 routes before declaring the law dead** — this is one
route.

### 3b. The grinding is CREEP-ONLY on V58, not road-speed

| v m/s | 1–2 | 2–3 | 3–4 | 4–6 | 6–10 | 10–14 | 14–18 |
|---|---|---|---|---|---|---|---|
| 18–26 Hz prominence, median | **141×** | **138×** | **518×** | 29× | 11× | 8× | 7× |
| peak-frequency sd | 1.31 | 0.48 | 0.55 | 1.65 | 1.47 | 1.89 | 2.16 |

A ~20× collapse between 3–4 and 6–10 m/s, and above 6 m/s the frequency scatter shows there is no
coherent line. `STATE.md` listed the grinding's home as *"road speed; present at creep too."* **On V58 it
is the reverse**, which is exactly where the operator said to look.

### 3c. ~21 Hz IS in openpilot's command

`STATE.md`'s two-symptoms table says *"in openpilot's command? no."* Not what V58 shows. Verified on the
**native 0xE4 grid** so it is not a held-last resampling artifact:

```
seg 11, t 23-34 (creep, engaged)
  command, native 0xE4 grid    20.89 Hz   prominence  34.0x
  command, held-last on 0x14A  20.96 Hz   prominence  34.0x     <- identical => real
  torsion bar                  20.96 Hz   prominence 241.4x
  coherence(cmd, bar) = 0.917 at 20.96 Hz, K=4, 95% null 0.632
```

Co-located command peak in **8 of 21** strong-line windows vs 1 of 11 weak-line windows;
`spearman(bar prom, cmd prom) = +0.486`. The bar's line is 6–7× sharper, which reads as an echo — but
**direction is NOT settled**. Carrier phase cannot settle it (a one-sample skew between two 100 Hz
mailboxes is 75° at 21 Hz). An **envelope cross-correlation** was run specifically because bursts rise
over ~100 ms, 10× coarser than the skew — and it was **inconclusive**: 2 of 4 runs bar-leads (+59, +79 ms),
2 command-leads (−10, −474 ms), peak correlations only 0.33–0.44.

⇒ openpilot is inside this loop. With no-openpilot-modifications standing, that is a constraint on any
firmware fix, not an action.

---

## 4. What V58's probe returned

**Cave fired: bit7 set in 83,959/83,959 frames, `field == 0` never.**

### bit5 — the ceiling is ELIMINATED
`gp-0x6bbe == +512` in **0 of 35,964** frames. `BUILD-LINEAGE.md` flagged this as the branch point: if the
lane pinned, the damping derivative would be zero at the peaks and the lever would become the ceiling
`0xD20C0` rather than `K1`. **It does not pin.** `K1` @`0xD200C` = 43 keeps its headroom.

### bit6 — VOID BY CONSTRUCTION, and the failure is instructive
`gp-0x6bbe` transitions sign **0.00–1.10 /s** route-wide; a 22 Hz flip needs ~44/s. Within the four
low-speed engaged runs it has **5 / 0 / 0 / 1** transitions — constant *within* runs, different *across*
them.

🛑 **Pooling the runs manufactures an answer.** Concatenated, bit6 has std 0.5 and returns "coherence
0.5 at 25.24 Hz" — pure step discontinuity at the splices. Per-run it vanishes. **Always check whether a
1-bit channel varies within runs before pooling.**

The pre-build validation (V57's bit3 scoring coherence 0.958) did not transfer, because *that* signal
oscillated about zero and this one does not. **A sign comparator is a phase probe only for a signal that
crosses zero at the frequency of interest.** `gp-0x6bbe` is the base assist boost curve — DC-dominated
during a turn. The damping-sign question is **still open**.

⚠ Note the distinction: "does not cross zero" ≠ "carries no 20–25 Hz content". A lane at +300 with ±50
ripple has real AC and never crosses zero. The probe is blind to it; the lane is not necessarily inert.

### bit4 — fired, and it is the lead
`sign(gp-0x6b9a)` at 20.93 Hz, per-run (no splicing) coherence **0.649 / 0.970 / 0.769 / 0.881** against
the bus angle rate at 20.57–22.15 Hz; own-spectrum peak 10.8× median; toggle rate to 42/s inside the
strongest bursts (44/s = a clean 21 Hz flip); `corr(18–26 Hz envelope, toggle rate) = +0.834` over 30
one-second blocks. And decisively, at **matched creep speed**:

| | duration | bit4 toggles/s | own 18–26 Hz line |
|---|---|---|---|
| LKAS applying | 50.0 s | **13.69** | **20.93 Hz, prominence 12.8×** |
| LKAS off | 65.7 s | **0.61** | 22.73 Hz, prominence 1.3× — none |

Duty cycle barely moves (0.492 vs 0.575): the gate is not resting elsewhere, it is *oscillating*. The
disengaged arm has more driver angle and effort and stays quiet, so this is not the wheel merely shaking.

**Pipeline validation worth reusing:** bit4's phase against the `0x18F` rate copy is consistently ~75°
offset from the `0x14A`-native copy across all four runs, and one sample at 100 Hz is
21.29 × 360 × 0.01 = **76.6°**. That confirms the pairing and identifies `rate_c` as the skew-free
reference — **and caps phase resolution at ±1 sample ≈ ±77° at 21 Hz**, which is not enough to call any
sign question. Say so rather than reading a number off it.

---

## 5. 🛑 The trace: `builds/v50_v79/build_v58_tva.py` was wrong, and correcting it produced the mechanism

`builds/v50_v79/build_v58_tva.py` described `gp-0x6b9a` as *"the FIR chain's output, indexing boost's NON-flat table
0xD28DC."* **Wrong on both counts.** Byte-verified against `_v58_plain_image.bin`
(SHA `4311174…`, matches the record).

**(1) `0xD28DC` hangs off `0xca4f4`, not `0xca23c`.** All 34 modes, LE:
```
0xca4f4 -> 0xCE5E8 0xCE604 0xCF5E8 0xCF604, then triples 0xD08DC/0xD08F8/0xD0914 … 0xD98DC/…
           0xD28DC PRESENT (mode 10)
0xca23c -> 0xCE5B0 0xCE5CC 0xCF5B0 0xCF5CC, then triples 0xD0888/0xD08A4/0xD08C0 … 0xD9888/…
           0xD28DC ABSENT
0xca154 / 0xc7970 / 0xca06c / 0xca40c / 0xca324:  ABSENT
```

**(2) `gp-0x6b9a` indexes nothing.** Its only live consumer in `FUN_00034a72` is a **five-input
plausibility gate**: `|gp-0x6b9a| ≤ 25600` (`addi 0x6400 / ori 0xc801 / cmp / bnc` @`0x34c9c-cb4`,
symmetric) ANDed with checks on `gp-0x6ba6`, `gp-0x4f68`, `gp-0x4f60`, `gp-0x6c2e` into r21, which zeroes
r24 @`0x34fc8`. r15 is overwritten at `0x34ca4`, so no value path survives. **Its sign has no effect on
the output.** Two of its three reads there (`0x34b5e`, `0x34b68`) are **dead** — `tp+0x7499 = 1`
(byte-verified `0xC6499`) takes the branch @`0x34b3c`.

### ★★ `gp-0x6ba6 == |gp-0x6b9a|` — the actual index

```
0x3b874  cmp   r0,r28
0x3b876  mov   r28,r13
0x3b878  bge   0x3b886        ; r28 >= 0 -> r13 = r28
0x3b87a  subr  r0,r13         ; else     -> r13 = -r28        r13 = |r28|
0x3b87e  ori   0xffff,r0,r13  ; FAULT path: r13 = 0xFFFF
0x3b882  movea 0x7fff,r0,r28  ; FAULT path: r28 = 0x7FFF
0x3b892  st.h  r13,-0x6ba6[gp]     ; SOLE writer image-wide
0x3b8b0  st.h  r28,-0x6b9a[gp]     ; SOLE writer image-wide
```

Writer sets byte-scanned for **both** gp-relative encodings (`disp` and `disp|1`), reg1 == r4 filtered:
`gp-0x6b9a` = 1 write + 8 reads (3 in `FUN_00034350`, 3 in `FUN_00034a72`, 1 in `FUN_0003b66a`, **1 in
V58's own cave @`0xC4B4E`**); `gp-0x6ba6` = 1 write + 5 reads.

⚠ **`search_instructions` reported 8 sites where the byte scan finds 9** — it missed the cave read, since
that region was not analysed in Ghidra. Exactly the documented undercount. The sole-writer conclusion
holds only because it was re-derived in Python.

`gp-0x6ba6` indexes **both** LERPs, relayed via scratch cell `gp-0x6bba` (`st.h` @`0x34b8e`, reloaded at
6 FSM exit sites because the 4-state debounce FSM clobbers r9):

```
LERP1 0xD28DC  count=6  X=(0,512,1490,2529,3645,5120)  Y=(16384,14657,11672,9365,8244,8187)
LERP4 0xD2888  count=6  X=(0,307,1024,1741,3072,6144)  Y=(16384,14392,10265,8997,8176,8176)
```

### ⇒ The mechanism

V58 measured the **signed** sibling crossing zero at 20.93 Hz, only when LKAS applies. The table index is
therefore that signal **full-wave rectified** — a minimum at every zero crossing — so it **sweeps the boost
amplitude curve at ~2× the mode frequency (≈41.9 Hz), on the BASE ASSIST path, across a 2:1 range**.

**INFERENCE, arithmetically forced but unmeasured in depth.** A sign bit carries no amplitude, and the
delivered swing depends on how far up the curve the index climbs:

```
index stays < 512   ->  Y 16384..14657   swing <= 1.12x   (weak)
index reaches 1024  ->  Y 16384..12938   swing ~  1.27x
index reaches 2048  ->  Y 16384..10360   swing ~  1.58x
index reaches 2529  ->  Y 16384.. 9365   swing ~  1.75x   (X3, steepest part)
index >= 5120       ->  Y 16384.. 8187   swing ~  2.00x   (full range)
```

⚠ **An earlier framing in this session called "below 512" INERT. That is wrong** — the LERP interpolates
from X = 0, so the coefficient is pinned at 16384 only at exactly zero. A 12% gain modulation at ~2× the
mode frequency is a weak parametric drive, not no drive. Caught by exercising the golden model against
the dumped curves; corrected in `builds/v50_v79/build_v59_tva.py`, the decoder, `STATE.md` and `BUILD-LINEAGE.md`.

### Two subagent claims that did NOT survive checking

- **"a genuine floating-point 2-pole biquad" in `FUN_0003b66a` — NO.** `tp+0x5018/501c/5020` =
  `0xC4018/1C/20` read **(1.0, 0.0, 0.0)**, identity, exactly as `BUILD-LINEAGE.md` already records. The
  code is `y = b0·x[n] + b1·x[n−1] + b2·x[n−2]` with two *input* delay states (`gp-0x365c`, `gp-0x3658`).
  Persisted input delays are a delay line, **not feedback**; stateful ≠ recursive. It is the 3-tap FIR on
  record, and it is a pass-through. **`STATE.md`'s "no biquad anywhere" survives. No new notch candidate.**
- **The sole-writer enumeration**, made on `search_instructions` alone — right answer, wrong method.
  See above.

New: **`tp+0x74be` = 0** (`0xC64BE`), so the branch @`0x3b720` is taken and `0x3b736–0x3b758` (the
`divf.s` block) is **dead code** — a third dead branch in this pair of functions.

---

## 6. Built this session: V59 (UNFLASHED)

**V59 = V58 with the cave payload replaced by the BOOST-INDEX DEPTH probe.** `0x14A` byte4:

```
bit7 = 1                          LIVENESS
bit6 = (gp-0x6ba6 <  0)           the 0xFFFF FAULT SENTINEL from FUN_0003b66a
bit5 = ((gp-0x6ba6 >>  9) == 0)   index < 512    <- BELOW X1: nothing modulates
bit4 = ((gp-0x6ba6 >> 10) == 0)   index < 1024
bit3 = ((gp-0x6ba6 >> 11) == 0)   index < 2048
bits 2:0 = stock STEER_SENSOR_STATUS, preserved
```

A **thermometer**: bit5 ⇒ bit4 ⇒ bit3 in every valid frame, so a wrong build on the car is detectable
rather than silently plausible. Reading `gp-0x6ba6` **signed** is deliberate — the cell is a magnitude, so
bit6 can only set on the `0xFFFF` sentinel, which both tests the fault hypothesis free and disambiguates
a fault (which would read as "index ≥ 2048", since −1 >> 9 = −1) from the loudest normal reading.

*Why thermometer and not a binary field:* the binding constraint is the **68-byte proven cave extent**,
not bit width. Fixed overhead 36 B + 10 B per comparison ⇒ **3 comparisons max ⇒ 4 levels either way**.
A uniform binary code is strictly worse: the cell spans 0..32767, so a 4-bit code with no saturation
logic (shift 11) gives 2048-count buckets and puts X1/X2/X3 all in bucket 0; useful placement needs
saturation, i.e. `BLE` or `cmov`, neither pinned in this image. Note `movea 0x8,r7,r7` is an **add**, so
the same pattern is already a unary counter (up to 15 levels in 4 bits) — the upgrade path is paid in
cave length and DTC-0x18 timing budget, not bits.

```
RWD    SHA256 ce7f6af6d7475a94462505a5f989d282966e00c9717cf6f2bbbc8b43ccdd3fc7
image  SHA256 c6020a32780c1c8d952782426deef25ae390afee4606f319b0aa3c3998158d6d
19 bytes off V58 (cave payload + MAIN CRC only; CAL CRC UNCHANGED = machine proof no cal moved)
86 bytes off V38.  50/50 CRC blocks pass.  RWD round-trips.  Cave re-disassembled from the built image.
GATE 1: inherited — same base 0xC4B34 / hook 0x55C0E / 68-byte extent as V55/V57/V58, all flown clean.
        Read-only, no new RAM, r6/r7 only. No new encoder and NO new condition code (BGE + BNE, both
        pinned to real instances).
GATE 2: vacuous — writes nothing to any control path, changes no calibration byte.
```

The build **asserts what makes the probe interpretable**: both LERPs still resolve to `0xD28DC` (via
`0xca4f4`) and `0xD2888` (via `0xca23c`) **at the same mode**, and `tp+0x7498/0x7499` are both still 1 so
`gp-0x6ba6` is still the live index. If any of that moves the build fails rather than shipping a probe
calibrated against the wrong curve.

Decoder: `rlog-tools/probe/decode_v59_boostindex.py`. It **hard-stops** above 1% non-monotonic frames rather
than reporting a verdict on the surviving subset — smoke-tested against a V58 log, where it correctly
refuses (56.2% non-monotonic) instead of printing the plausible-looking "LIVE, 1.26×" it produced before
that guard was added.

---

## 7. Recommended next steps

1. ★★ **Flash V59 and drive the creep route.** The whole question is depth: read the thermometer to
   bracket the swept Y range and hence the delivered gain swing. ⚠ A "stays below 512" result is
   **weak (≤1.12×), not inert** — so the decision is whether the swing justifies a GATE-2 review of a
   base-assist lever, not a clean yes/no.
   **Route spec:** parking-lot / low-speed creep with LKAS applying, v ≤ 5 m/s (the mode is creep-only),
   and — the thing route `2b` could not give — **sustained hands-off stretches ≥ 3 s**. Add deliberate
   LKAS-on/off passes at matched speed and angle.
2. **Re-run the strict-band (18–26 Hz + presence test) frequency analysis over V55/V56/V57 routes**
   before rewriting the frequency law. One route is not enough to kill a cross-route fit, but the
   cross-route fit is now suspect.
3. **The damping sign is still open.** `gp-0x6bbe` needs a *magnitude* probe (thermometer), not a sign
   bit. That is V60, and it only matters once V59 says whether the amplitude path is live.
4. **Do not move `0xD28DC`, `0xD2888` or `tp+0x73ba` (`0xC63BA` = 512) yet.** All three sit on the
   **base assist** path, so they change manual feel, not just the LKAS lane, and all need GATE 2.
   `tp+0x73ba` is the cascaded EMA alpha (0.5 at 1 kHz ⇒ corner ≈120 Hz for the pair, i.e. **wide open at
   21 Hz**) and is the *upstream* candidate: attenuate there and the index stops carrying 21 Hz at all.
5. **The ratchet is untouched by this route and cannot be.** Hands-off + engaged + `|e4tq| ≥ 3500` +
   v ≤ 3.0 m/s yields **9 runs / 139 frames**, all inside one 8 s window that overlaps a hands-on
   manoeuvre. **Zero clean episodes.** A dedicated comma-commanded route is required.
6. `gp-0x6c2e` and `gp-0x4f68` are unresolved — they appear only as r21 gate inputs. Not blocking.

🛑 **Flash only on explicit operator instruction naming the file and the bus. Kill openpilot/pandad first.**
