# TRACE 2026-08-21 — the LKAS gain ceiling, and the road to 16×

**Status: analysis only. Nothing built, flashed, or sent on CAN/UDS to produce this document.**
Subagent trace, GhidraMCP against `code.bin` (stock, analysed) plus fresh Python byte reads of
`_v101…`, `_v102…`, `_v103…_plain_image.bin` (`ACCORD_FIRMWARE_ROOT/analysis-2020accord/`). Current
kit state at time of writing: **V103 (6×) flew as route `0x9e`** — operator verbatim: *grind #1 present,
ratcheting present, "seems like 6x torque available."* V104 (fix-only, gain frozen at 6×) is in
progress elsewhere in this session; **V105 is where the kit's own plan next raises gain, capped at 9×**
by the same convention this trace interrogates.

**Evidence legend:** **[EVIDENCE]** = read or computed this session (Ghidra, raw byte read, or exact
arithmetic) or an independently-reproduced prior result. **[prior EVIDENCE]** = established earlier in
the kit, cited not re-derived. **[BELIEF]** = inference, flagged as such.

---

## 0. HEADLINE

**16× is not reachable by any precedented, cal-only method — and going there would not buy the peak
torque a naive "16×" label implies, because a completely separate, gain-agnostic clamp already
flattens peak output above roughly 10.7×.** Below that, the wall the kit's build scripts already
enforce (10×, refusing to cut) turns out to be **a convention this kit invented, not a firmware-executed
comparison** — confirmed by exhaustive Ghidra tracing this session: no instruction anywhere in the
~1 MB image compares the cal cell that convention reads (`0xC674E`) against the cal cell it compares it
to (`0xC61B2`/`0xC61B4`). But relaxing that convention does **not** open the door to 16×, because of what
task 6 found:

**🛑 Task 6 verdict: this is a STABILITY problem, not a clamp problem, and it is not theoretical — it
already happened on the road.** V101 (8×, byte-identical gain to what a future V105 would re-fly) is on
record as **"the operator's worst vibration report in the corpus"** [prior EVIDENCE, `SPEC-2026-08-20-
v104.md` §0.3], attributed with a de-confounded 2×2 design to the gain step alone, with **the resonance
peak MOVING (20.3 Hz → 23.0 Hz)** — a root-locus signature, not just more excitation. Independently, a
same-day loop identification (`GATE2-2026-08-20-boost-direction.md`) bounds the **assist loop's own
return ratio at 6–9 Hz: `|κG| = 0.63 [0.51, 1.00]` at the 4×-equivalent operating point, rising to
`0.75` at 8×**, i.e. **gain margin already only 1.2–1.6× (1.5–4 dB)** — and **100% of the measured
anti-damping `Re(Z) = −3761` is loop-generated**, not a passive mechanical mode. Both clamp-style walls
(governor saturation ≈10.7×, the kit's paper convention =10×) sit **above** the gain (8×) where this
already manifested audibly. **The instability signature arrives before either clamp binds.**

---

## 1. Where the `0xC674E > clamp` assert comes from — and whether the firmware makes it

**[EVIDENCE, grep]** The check lives in every gain-stepped build script since V101/V102
(`analysis-2020accord/build_v102_tva.py:698-700`, `build_v103_tva.py:555`, reproduced verbatim in
`SPEC-2026-08-20-v104.md` §2.1):
```python
floor, clamp = u16(img, 0xC674E), u16(img, CLAMP_B2_ADDR)
check(floor == 5120 and floor > clamp,
      f"{label}: soft-EME boost floor INT = {floor} > {clamp} (the fwd-path clamp) "
      f"=> authority sufficient  [this gate caps the gain below 10×]")
```
This is a **Python `check()` in the build tooling** — an assertion the *build script* refuses to violate,
not a comparison the *firmware* performs at runtime.

**[EVIDENCE, exhaustive Ghidra trace this session]** I traced both cal cells to their actual readers:

- **`0xC674E`** (tp+0x774E, the corridor/boost "authority floor") has **exactly one reader in the entire
  stock image**: `0x43066 ld.h 0x774e,tp,r15` inside `FUN_00042af8` (`soft_eme_windup_shaper`).
  Confirmed **two independent ways**: `search_instructions` operand-text scan (1 real hit; the only
  other match, `FUN_000757a2`'s `bgt 0x774e2`, is a branch-target text coincidence, excluded) **and** a
  raw Python little-endian byte scan of `code.bin` for the exact halfword encoding (`4e 77` at offset
  `2:4`) — **1 occurrence in the 1 MB image, at `0x43066`, nothing else.**
- I decompiled `FUN_00042af8` in full (1423 lines) and grepped the entire body for `0x21b2`/`0xc61b2`
  (the tp-relative and absolute forms of the clamp address): **zero hits.** The function reads only
  the corridor/boost/IIR family (`tp+0x774a..0x776e`) and a hardcoded `0x2000` (see §2).
- **`0xC61B4`** (the clamp `FUN_00042af8` would need to read to make this comparison) is read
  **only inside `FUN_00028ea6`** (`steer_torque_arbitration`), at `0x2a1f8 ld.hu 0x71b4,tp,r16` —
  a **completely different function**, immediately after the gain-multiply and Q15 requantizer (§2, §3).
- **`0xC61B2`** is read **only inside `FUN_0002b422`/`FUN_0002b57a`** — again, neither is
  `FUN_00042af8` nor `FUN_00043e44`.
- I also checked the one function architecturally positioned to enforce a cross-check —
  `FUN_00043e44` (`hard_dtc_lockstep_monitor`, the DTC-0xF00049 float mirror, §5). Its 977 instructions
  include **47 tp-relative reads**; I matched **6 of the 7** `EME_FLOATS` cal addresses directly by
  displacement text (`0xC6598, 0xC659C, 0xC65AC, 0xC65B0, 0xC65C4, 0xC65CC`) — but **none of
  `0xC61B2`/`0xC61B4`/`0xC6CD0`/`0xC646C`.**

**Conclusion: [EVIDENCE] `floor > clamp` is a KIT-INVENTED SAFETY CONVENTION, not a firmware
requirement.** No instruction anywhere compares these two cal cells, directly or via any intermediate
value. Nothing in the firmware would fault, trap, or misbehave the instant `0xC61B2` numerically exceeds
`0xC674E` — the two cells are consumed by unrelated functions, at unrelated points in the pipeline,
separated by the aggregator, mixer and governor (§2).

**[BELIEF, but closely reasoned from evidence in §2/§5]** The convention is also **comparing the wrong
two quantities for a literal safety guarantee**, and the kit's own golden model already says so: the
`soft_eme_windup_shaper` docstring states *"the conservative assist-inclusive envelope (4762 governor +
2560 compensation = 7322) exceeds the 5120 floor, so this model does not claim every combination is
contained."* **Even today, at flown gains, the shaper's input can exceed 5120 under ordinary
governor+compensation combinations** — the floor was never an absolute ceiling; it is the threshold
above which a **slow integrator starts winding toward a graceful SM2/SM3 soft-cut**, not an instant
fault. Crossing it more often at higher gain means the soft-cut fires more often (see §5), not that the
ECU faults the instant `clamp > floor`.

---

## 2. The full clamp chain, address by address

| # | stage | address | cal or literal | stock value | mechanism | binds at 16×? |
|---|---|---|---|---|---|---|
| 1 | CAN intake | (openpilot DBC) | n/a | ±4096 | `STEER_MAX`, unaffected by firmware gain | no — untouched by 0xC6CD0 |
| 2 | setpoint scale+clamp | `0x526cc-0x526f2`, `FUN_00052676` | **CODE literal** `±0x4000` | ±16384 | **[EVIDENCE, fresh disasm]** `sxh r6`(0x526cc)→`shl 0x2,r6`+`subr r0,r6`(×−4)→`clamp(·,±0x4000)`→`gp-0x69ae`. Reads only the raw CAN value; **never reads `0xC6CD0`** | no — identical at every gain |
| 3 | `arb_setpoint_limit` LERP | `0xCB844`→ this car's record `0xE51A8` | **cal**, per-part-number | this car: raised, 16384 (8/12 records raised; [prior EVIDENCE, fully traced §4 of `FEASIBILITY-8X-LKAS.md`]) | selects a per-mode ceiling on the pre-gain setpoint | no — headroom already spent, doesn't change with gain |
| 4 | **Q15 gain multiply** | `0x2a1ee-0x2a202`, `FUN_00028ea6` | **cal** `0xC6CD0` (fwd, since V57) / `0xC646C` (4 feedback readers, stock 891) | 891 | **[EVIDENCE, fresh disasm]** `ld.h 0x746c,tp,r7`(gain)→`ld.b -0x6752,gp,r13`(sign, =−1)→`mulh r7,r13`→`mul r13,r11,r0`→**`0x2a202 sar 0xf,r11`** (Q15 requantizer) | **the lever itself** |
| 5 | **arb/pack clamp** | `0x2a1f8-0x2a220` (`0xC61B4`, `FUN_00028ea6`) · `0x2b42a-0x2b44a` (`0xC61B2`, `FUN_0002b422`/`FUN_0002b57a`) | **cal**, tracks gain: `clamp=GAIN×512//891` | 512 | **[EVIDENCE, fresh disasm]** `ld.hu 0x71b4,tp,r16` loaded in the SAME basic block, immediately after the SAR — `cmp r16,r11`→`ble`/two `cmovc`-style branches implementing `clamp(x,±0xC61B4)` | **[EVIDENCE, derived]** NEVER — proportional scaling holds the margin at a constant **13.0%** at every integer gain step 1×-16× (verified 1×,4×,6×,7×,8×,9×,10×,16× — see §4 table) |
| 6 | distribute/mixer gate | golden model `distribute_lkas_lane_clamp`/`mixer_gate_clamp` | **CODE literal** `±0x2800`=10240 | — | range-gate idiom (same shape as §7) | no — 16×'s own-clamp max ≈7128 (§4), well under 10240 |
| 7 | aggregator LKAS-lane **DROPOUT** | `0x3acbc-0x3acc4`, `FUN_0003xxx` (the aggregator) | **CODE literal** `±0x2800`=10240 | — | **[EVIDENCE, fresh disasm]** `addi 0x2800,r6,r9`→`addi -0x5001,r9,r0`(unsigned-wraparound range test)→**`0x3acc4 cmovc 0x0,r6,r13`** — zeroes the lane (not clamps) when `\|gp-0x6ad4\|>10240` | no — same headroom as #6 |
| 8 | aggregator total clamp | (golden model) | CODE literal `±0x2800` | — | sum of all lanes | possible only WITH concurrent base assist; LKAS alone still under it |
| 9 | **governor flat ceiling** | `0x453f0-0x453f8`, `FUN_0004503c` | **cal** `0xC6202` | **4762** — [EVIDENCE, fresh `read_memory` on V103 image: `9a12`LE=4762, unchanged since stock] | **[EVIDENCE, fresh disasm]** `ld.hu -0x4f64,gp,r8`→`mul r26,r8,r0`→**`0x453f8 sar 0xf,r8`** | **YES — the real, gain-independent ceiling (§4)** |
| 10 | governor **adaptive rate cap** | `0x453fa-0x4540a`, same function; table `0xC520C` | **cal**, `Y=(5325,3584,2406,1587,512)` keyed on measured motor electrical rate | unchanged (fresh read, V103 image: `5,1050,1700,2500,3700,…` count+X-breakpoints match golden model) | **[EVIDENCE, fresh disasm]** `mul r28,r10,r0`→**`0x4540a sar 0xf,r10`** | tighter than #9 under any fast correction — binds **sooner** than 16× |
| 11 | governor **slew** | `0x4540e-0x4541e`, same function; `0xC6206`/`0xC6208` | **cal**, selector `gp-0x67f5` | 512 / 205, unchanged (fresh V103 read) | **[EVIDENCE, fresh disasm]** `ld.hu 0x7206/0x7208,tp,r16`→`mul r23,r16,r0`→**`0x4541e sar 0xf,r16`** | rate-of-change only, doesn't change §9's ceiling |
| 12 | soft-EME corridor/boost | `FUN_00042af8`, cal family §5 | **cal**, `0xC674E` + 6 siblings | 5120 (flat since V38, unchanged through V103 — fresh read) | integrator winds on **pre-governor-ish** command exceeding this; graceful SM2/SM3 cut, not instant fault (§1, §5) | at 16× the pre-shaper command CAN sustain excess more easily (§5) |
| 13 | soft-EME **final clamp** | inside `FUN_00042af8` (`iVar45=0x2000` in the decompile) | **CODE LITERAL**, `±0x2000`=8192 | — | **[EVIDENCE, fresh decompile]** `iVar45 = 0x2000;` and `iVar45 = (iVar18<-0x1fff)*-0x2000 + iVar18*(-0x2000<iVar18)`; no memory dereference anywhere near it — a bare immediate | **unreachable at every gain tested (§4)** — the governor (#9/#10) already bounds the input to this clamp at ≤4762, below 8192, so it never binds |
| 14 | integrator → `gp-0x6b98` → FOC | `merged_command`→`gp-0x6b98` | RAM | — | final FOC current-loop demand, 30+ touches per kit landmark record | delivers whatever survives #9-#13 |

**⭐ The "key question" from the brief — is the final ±8192 a cal or a literal:** **[EVIDENCE] It is a
bare code literal (`0x2000`), confirmed fresh this session by decompiling `FUN_00042af8` and finding no
memory dereference anywhere near either `iVar45 = 0x2000` assignment.** But this matters less than it
looks: **the governor's flat 4762 ceiling sits upstream of it and never lets the signal get close.** At
every gain step through 16× (§4), the value arriving at this clamp is already bounded by the governor to
≤4762 — **56.8% of the 8192 literal, unreached at every tested and extrapolated gain.**

---

## 3. Is the `891` denominator meaningful?

**[EVIDENCE, fresh disasm]** Yes, but not the way "the firmware computes 512/891" would mean. `0xC646C`
(shared_sensor_scale, Honda's 891) and `0xC61B4` (the clamp, Honda's 512) are **two independent cal
cells**, read by **two separate instructions 10 bytes apart in the same basic block**
(`0x2a1ee ld.h 0x746c,tp,r7` then, after the gain multiply and `0x2a202 sar 0xf`, `0x2a1f8 ld.hu
0x71b4,tp,r16`) — the firmware does **not** compute `clamp = gain*512/891` at runtime; it applies two
**separately calibrated** values, multiply-then-clamp, in immediate succession. `512/891` is simply
**Honda's own stock proportion between two cells that happen to be consumed sequentially** — and because
the relationship is a pure ratio, scaling both cal cells by the same integer multiplier preserves the
**exact same 13.0% headroom** at every step (verified 1×→16× in §4's table; no rounding perturbs it,
since `891×m×512//891 = 512m` exactly for every integer `m`). The kit's "twice-precedented pattern of
doubling both together" is therefore a **structurally sound convention** (it genuinely keeps the arb
clamp from ever binding) even though it is not something the firmware itself derives.

---

## 4. The true maximum gain, and the ladder to 16×

**[EVIDENCE, exact integer arithmetic, cross-validated against 5 real built images in
`SPEC-2026-08-20-v104.md` §2.1 — V87/V99/V100 (4×), V101 (8×), V102/V103 (6×), all reproduce the rule
exactly]**

| × | `0xC6CD0` | clamp `0xC61B2`/`4` | arb-clamp margin | fs output (=gain÷2) | vs floor 5120 | vs governor 4762 | status |
|---|---|---|---|---|---|---|---|
| 1 (stock) | 891 | 512 | 13.0% | 445 | +900.0% | +90.7% | flown, years |
| 4 | 3564 | 2048 | 13.0% | 1782 | +150.0% | +62.6% | flown (V38–V100) |
| **6** | **5346** | **3072** | 13.0% | 2673 | +66.7% | +43.9% | **ON CAR, V103, route 0x9e — grind #1 + ratcheting BOTH still present** |
| 7 | 6237 | 3584 | 13.0% | 3118 | +42.9% | +34.5% | never flown |
| **8** | **7128** | **4096** | 13.0% | 3564 | +25.0% | +25.2% | **flown as V101 — "operator's worst vibration report in the corpus"; would be a RE-RUN if repeated** |
| **9** | **8019** | **4608** | 13.0% | 4009 | **+11.1%** | +15.8% | **legal, never flown — the kit's own current maximum** |
| 9.5 | 8464 | 4863 | 13.0% | 4232 | +5.3% | +11.1% | untested |
| 10 | 8910 | 5120 | 13.0% | 4455 | **0.0% → ABORTS** | +6.4% | build script refuses to cut |
| 10.69 | 9524 | 5472 | 13.0% | **4762 (exact)** | −6.4% | **0.0% — governor saturates HERE** | — |
| 12 | 10692 | 6144 | 13.0% | 5346 | −16.7% | −12.3% (49.7%.. wait see below) | — |
| **16** | **14256** | **8192** | 13.0% | **7128** | **−37.5%** | **−49.7%** | **the operator's target** |

*(the 12× governor-margin column above reads −12.3%, meaning fs output 5346 exceeds 4762 by 12.3%; the
16× row is the one to read carefully: fs output 7128 exceeds governor 4762 by 49.7%.)*

**Two independent ceilings, and they are close but NOT the same wall:**
1. **The kit's own convention (`floor > clamp`) fails exactly at 10×** — `0xC674E` (5120, frozen since
   V38, unchanged through 17 images including V103) would need to become **≥8192 (a 60.0% rise) just to
   restore parity with a 16× clamp, or ≈9102 (a 77.8% rise) to keep the SAME 11.1% cushion the kit
   accepted as "legal" at 9×.** Nothing has ever tested raising this cell — see §5.
2. **The governor's flat ceiling (`0xC6202`=4762, untouched, [EVIDENCE, fresh read on the V103
   image]) saturates full-scale LKAS-alone at ≈10.69×**, independent of the clamp/floor question
   entirely — this cell has its own cal, is read by a different function (`FUN_0004503c`), and doesn't
   care what `0xC6CD0` is set to. **At 16×, 66.8% of openpilot's command range (everything above
   `\|x\|>0.668×STEER_MAX`) delivers the exact same 4762-count output a ~10.7× build would ALSO deliver
   at ITS full scale — the "extra" gain from ~10.7× to 16× buys ZERO additional peak torque if the
   governor is left alone**, and instead makes ordinary (not just extreme) commands hit that ceiling.
3. **The adaptive rate cap (table `0xC520C`, unchanged) is tighter than the flat ceiling under any fast
   correction** — [prior EVIDENCE] "at TODAY's 4× moderately fast steering already clips" this table
   before the flat 4762 even matters. Real dynamic driving would hit an effective ceiling **below**
   10.7× — the flat-ceiling number is a best-case (slow, gentle-steering-only) estimate.

**⇒ [EVIDENCE] The maximum gain that delivers something NEW over what a lower gain already delivers is
bounded near ≈10.7×, by a cal cell (`0xC6202`) nobody has proposed touching and that has ZERO
relationship to the `0xC674E`/clamp convention. 16× is roughly 1.5× past that point — it is not merely
"blocked by a paper rule," it is architecturally redundant with a build around 10-11× for anything but
the bottom two-thirds of the command range, UNLESS the governor itself is also raised (§5's highest-risk
item, explicitly flagged REJECTED in `docs/BUILD-LINEAGE.md`: "buys nothing, and `gp-0x4f64` is
shadowed → fault `0x17`, hard-fault-eligible").**

**The ladder to a literal 16×, cal cells only, in order of what must move:**

| step | cell(s) | from → to | cal/literal | precedent | risk |
|---|---|---|---|---|---|
| 1 | `0xC6CD0` | 891 → 14256 | cal | V9→V101 lineage, 5 prior steps | none by itself — see step 2 |
| 2 | `0xC61B2`+`0xC61B4` | 512 → 8192 | cal, in lockstep | twice-precedented (V22→V38, V31→V38) doubling pattern | none — never binds on real signal (§2, §4) |
| 3 | `0xC674E`,`0xC6750`,`0xC675A`,`0xC675C` (dir1/dir2 corridor Y, int) | 5120 → ≥8192 | cal, 4 halfwords | **UNPRECEDENTED beyond 5120** — frozen since V38 across 17 images | moderate — see §5; not a hard fault by itself if float-matched |
| 4 | `0xC6768`,`0xC676A`,`0xC676C` (boost Y0-2, int) | 5120 → same new value | cal, 3 halfwords | same family, same freeze | moderate, same class |
| 5 | `0xC6598`,`0xC659C`,`0xC65AC`,`0xC65B0`,`0xC65C4`,`0xC65C8`,`0xC65CC` (float mirrors, ALL 7) | 5.0f → new/1024 | cal, 7×4-byte floats | V29→V38 precedent for the FIRST move (1.0f→5.0f); this would be the SECOND move ever | **HIGH if done asymmetrically** — this is exactly the V25-V27 brick class (§5) |
| 6 | governor `0xC6202` (only if peak torque above ~10.7× is actually wanted) | 4762 → higher | cal | **explicitly REJECTED in `BUILD-LINEAGE.md`**: "buys nothing, `gp-0x4f64` shadowed → fault 0x17, hard-fault-eligible" | **HIGH — do not** |

Steps 1-2 are the "9× legal, cal-only" territory the kit already occupies. **Steps 3-5 are wholly
unprecedented past V38's single move** and are where the real, non-trivial engineering risk of a 16×
gain build actually lives — not in the gain cell itself.

---

## 5. The fault surface — the EME lockstep family, enumerated

**[EVIDENCE, this session's Ghidra trace, §1]** Two independently-read halves, matched by design:

**INT side — read exclusively by `FUN_00042af8` (`soft_eme_windup_shaper`), single instruction per
cell, confirmed for `0xC674E` two ways (search + raw byte scan), inferred for the 6 siblings by their
presence in the same decompiled LERP block:**
`0xC674E`/`0xC6750` (dir1 corridor Y[0]/Y[1]) · `0xC675A`/`0xC675C` (dir2, negated) ·
`0xC6768`/`0xC676A`/`0xC676C` (boost Y[0..2]) — **7 halfwords, currently flat at 5120** (fresh read,
V103 image, all 7 confirmed identical).

**FLOAT side — read by `FUN_00043e44` (`hard_dtc_lockstep_monitor`, DTC-0xF00049), confirmed this
session (6 of 7 addresses hit directly by tp-relative displacement text; the 7th is very likely reached
via base+offset indexing from an adjacent `movea`, not independently confirmed):**
`0xC6598`/`0xC659C` (dir1) · `0xC65AC`/`0xC65B0` (dir2) · `0xC65C4`/`0xC65C8`/`0xC65CC` (boost) —
**7 floats, matched at `int/1024`, i.e. 5.0f each.**

**What "no debounce, hard motor-off" actually means, precisely:** `FUN_00043e44` independently
recomputes the same corridor/boost MAX in float, spot-checked this session (float arithmetic —
`cvtf.ws`/`mulf.s`/`subf.s` — operating on `gp-0x6af6`, `gp-0x6b00`, `gp-0x6acc` near `0x44640`,
consistent with the golden model's documented ±5 LSB tolerance test [prior EVIDENCE, tag `[VERIFIED]`]
— not independently re-derived byte-for-byte this session). If the int wall and the float twin diverge
beyond tolerance, `DTC_0xF00049` latches and the motor is cut — **this is the exact mechanism that
bricked V25-V27** (an int-only or float-only edit desynced the pair).

**⇒ Any edit to the 5120 family MUST move all 7 int halfwords AND all 7 float words together, to the
matched value (`float = int/1024`), in the same build.** This is mechanically simple (all 14 cells sit
in ONE CRC block, `[0xC6000,0xC6FFC)`, trailer `0xC6FFC` — [EVIDENCE, `SPEC-2026-08-20-v104.md` §2.3]
— alongside the gain and clamp cells, so one CRC recompute, already routine, covers everything) but has
**never been done past the single V29→V38 move.**

**Consequence of crossing the threshold more often (not a hard fault by itself):** raising `0xC61B2`/`4`
above `0xC674E` without also raising the floor means the pre-shaper command more easily and more
sustainedly exceeds the corridor/boost bound. The documented consequence is **graceful, not
catastrophic**: the integrator winds toward `authority`; if it sustains past `sm3_clamp` (30720 for 20
cycles), `SM3` selects `sm3_cut_factor_q15` — **currently `0`, i.e. a FULL zero-authority cut**, not a
partial one — until the integrator recovers to 0. **Separately**, `SM2`'s entry condition
(`authority>=16384`, gated off by `sm2_variant_gate==3` which V38/V39 carry) leads to a state whose
**recovery/ramp path the golden model explicitly flags as "not reconstructed... remains replayable
state"** — **[OPEN]**, this session did not resolve it.

**Does the floor's V38 raise (1024→5120) cost anything at gains flown so far?** **[EVIDENCE, prior]**
V54 measured `authority` staying in `[0,127]` (~0.39% of saturation) with **zero variation** across a
flown drive — the corridor/boost bound has **never been observed to bind** at any gain flown to date
(1×-8×). **⇒ [BELIEF, well-supported]** raising the floor cost nothing observable then, because the
mechanism wasn't engaging at either value; by the same token it has never been *tested* against a
condition that would trip 1024 but not 5120, so "no cost" is a statement about the *flown* envelope,
not a general guarantee.

---

## 6. Clamp problem or stability problem — the verdict, in full

**[EVIDENCE] Stability problem.** Three independent lines converge:

1. **It already happened, on-car, below any clamp.** V101 (8×) — governor margin still +25.2%, arb
   clamp margin still 13.0%, the kit's own convention still 25.0% short of its 10× abort — nonetheless
   produced *"the operator's worst vibration report in the corpus"* [prior EVIDENCE], with the resonance
   **peak moving 20.3 Hz → 23.0 Hz** (a pole shifting under gain, the signature of a feedback loop, not
   of a saturating clamp) and a **measured** single-step contrast (6×→8×, the SAME re-run a future
   V105 would fly) predicting the 22-26 Hz band at **×1.64 [1.52, 1.75]** — a number derived from flown
   telemetry, not a model.
2. **`V101`'s own stated premise was measured false.** Its build header (`build_v101_tva.py`) argued:
   *"The LKAS command enters the control loop as an EXOGENOUS INPUT, not part of the feedback — so
   doubling the gain doubles the EXCITATION but does NOT change any closed-loop pole."* **[prior
   EVIDENCE, `STATE.md` corrections list]**: *"V101's GATE 2 premise is MEASURED FALSE... The pole
   moved and the demand oscillates."* The kit built and flew 8× on an assumption its own later
   measurement overturned.
3. **The loop margin is quantified, and it shrinks with gain.** `GATE2-2026-08-20-boost-direction.md`
   §3 identifies, from the measured G4/G8 transfer at 6-9 Hz (`gp-0x6b94`, the aggregator sum, on two
   real builds): `|κG| = 0.630 [0.512, 1.001]` at the 4×-equivalent point, **rising to `0.749` at 8×**.
   `|1+κG|` (inverse closed-loop amplification of driver-felt impedance) is **0.44 at 4×**, meaning the
   loop already **amplifies driver-felt impedance 2.3× [1.5, 9×]** at exactly the ratchet frequency —
   and **the CI's upper bound is already 1.001, i.e. at the edge of encircling −1, at the LOWER of the
   two measured points.** The identification was validated **within one single drive** (stratifying by
   command-amplitude percentile at fixed gain, `|P|` 0.53-0.86 across bins) — not solely a cross-build
   artifact — and a firmware-blind consistency check (`arg(c)`) landed within 34.7° of the sign the
   decompiled polarity chain predicts. **[prior EVIDENCE]** *"`Z0` is a lossless spring... 100% of
   `Re(Z) = −3761` is loop-generated."*

**Extrapolation to 16× is genuinely uncertain, and I will not pretend otherwise.** `|κG|` scales as
`c·G`, where `c` is fixed and `G` (the fitted, MEASURED aggregate lane gain) grew only **1.19×** between
the 4×-cal build and the 8×-cal build (`G8/G4 = 0.0572/0.0481`) despite the **cal ratio doubling** —
i.e. the mapping from firmware cal gain to the loop's effective forward gain is **sub-linear and
partially confounded with command amplitude** (the SAME-DAY `f0`-vs-gain finding: *"pooled, the gain
term goes non-significant... most of the march this kit attributed to `0xC6CD0` may be openpilot
winding up on a weaker car"*). Two honest brackets, from 6× (current, cal=5346) toward 16× (cal=14256,
a further 2.67× cal step):
- **naive-proportional** (`|κG|` scales with the raw cal ratio): `0.749 × 2.67 ≈ 2.0` — deep Nyquist
  encirclement of −1.
- **sub-linear fit** (using the empirically observed `p≈0.245` power law from the two-point G4/G8 fit,
  itself built on only 2 points): `0.749 × 2.67^0.245 ≈ 0.97` — still marginal, still inside the
  CI-touches-1.0 zone already seen at the LOWER measured point.

**Both brackets point the same direction (margin shrinks further), and neither says "safe."** I am not
resolving which is closer to truth — that needs a THIRD measured gain point above 8× (which the kit's
own convention currently prevents past 9×) or a controlled command-amplitude-matched design that
isolates cal-gain from confounded command amplitude (flagged as an open item, `HANDOFF-2026-08-20-
v103…` §recommendation).

**What changes qualitatively above ≈10.7×, not covered by any of the above:** §4 showed the governor
begins hard-clipping the top third of the command range. Below that crossover the system behaves as
the (already marginal) LINEAR resonance GATE2 characterizes; above it, ordinary steering corrections
would routinely saturate the governor, which could — description-function reasoning, **[BELIEF]**,
not measured — either (a) act as an amplitude limiter that *caps* the resonance's growth (a relay/
limit-cycle regime, bounded but audible, arguably a worse *felt* symptom than an unbounded-looking
lightly-damped ring) or (b) interact with the slew/rate-cap dynamics in a way nothing in this kit's
record has tested, since **no build to date has pushed LKAS-alone routinely into the governor's clipped
region** (V101 at 8× still had 25.2% margin). **16× would be the first build to operate mostly inside
this untested regime.**

---

## 7. Openpilot-side headroom at 16×

**[EVIDENCE, fresh disasm, §2 row 2]** The intake clamp (`FUN_00052676`) is **entirely independent of
the firmware LKAS gain** — it reads only the raw CAN torque request, scales `×−4`, and clamps to
±16384. This instruction sequence is **byte-identical at every gain**, so it neither helps nor hurts at
16×.

**Distinct-level accounting:** the arb-stage output at full scale is `gain÷2` (§4: exactly 7128 at 16×).
Since openpilot's raw signal carries 8193 distinct levels (±4096, DBC-integer) and the output span at
16× is 14257 slots (±7128), **the mapping from input to output does NOT hit every possible output
integer** (8193 < 14257) — but it remains **monotonic and spans the full range end-to-end**; the
"gap" is a coarser-than-1-count granularity in the upper part of the range, which is functionally
irrelevant for a physical torque signal. **⇒ [EVIDENCE] openpilot's ±4096 still addresses the complete
firmware output range at 16×**, exactly as it does at every other gain — this is not where a problem
would arise.

The real ceiling on what that ±4096 can ultimately deliver is §4/§6's governor and stability picture,
not anything on the openpilot side.

---

## 8. What I could not resolve — and the exact next step for each

1. **The 7th float mirror cell (`0xC65C8`)** — inferred from the array pattern (base+offset from a
   `movea` at `0x44384`/`0x43f98`-style addressing) but not independently hit by displacement-text
   search this session. *Next step:* `disassemble_function` on `FUN_00043e44`'s full body (not just the
   `0x44600-0x44680`/`tp`-filtered slices read here) to trace the register-indexed reads explicitly.
2. **SM2's recovery/ramp path** — the golden model itself flags this as unreconstructed. If a 16×-class
   build routinely trips `authority>=16384`, what actually happens next is not characterized. *Next
   step:* decompile the `sm2_state` transition logic inside `FUN_00042af8` beyond the entry condition
   already traced (this session read only the entry block, not the full state machine).
3. **The `|κG|` extrapolation bracket (0.97–2.0 at 16×) is wide, from 2 measured points.** *Next step,
   already recommended in the kit's own record*: a THIRD measured gain point, ideally with
   command-amplitude held constant across the comparison (to separate cal-gain from the openpilot-
   command confound flagged same-day in `HANDOFF-2026-08-20-v103…`). Under the kit's current 9×
   ceiling, that third point would have to be 9× itself — never flown.
4. **Motor current / thermal hardware limit downstream of the governor and FOC chain** — flagged
   **[OPEN]** in `FEASIBILITY-8X-LKAS.md` and not investigated further this session (out of scope
   against the task's clamp-chain focus). *Next step:* trace `FUN_00071272` (Park/Clarke + PI regulator)
   and the ADC/current-sense scaling.
5. **Whether the governor-saturation crossover (≈10.7×, derived this session) has ever been
   *felt* by the operator** — no build has been flown in the 9×-11× band specifically to listen for a
   "torque stops growing" plateau distinct from the vibration symptom. *Next step:* if a 9× build is
   ever flown (the kit's own current legal max), ask the operator specifically whether peak effort
   *feels* like more than 8× or not — that is a free, no-new-build data point available from the
   existing 9× ceiling.

---

## Sources

`analysis-2020accord/build_v101_tva.py`, `build_v102_tva.py`, `build_v103_tva.py` (headers, EME audit,
gain/clamp arithmetic); `docs/FEASIBILITY-8X-LKAS.md` (Parts 1-2, prior clamp-chain trace at 4×/8×);
`docs/SPEC-2026-08-20-v104.md` §§0.1-0.3, 2.1, 2.3, 3 (5-image ladder validation, cross-build cell
matrix, operator's V103 verbatim report, V101 re-run risk); `docs/GATE2-2026-08-20-boost-direction.md`
§§0, 3 (`|κG|` identification); `docs/STATE.md` (V101-V103 headline results, corrections list,
f0/gain-confound finding); `analysis-2020accord/eps_chain_core.py`, `eps_chain_delivery.py` (golden
model field definitions and `soft_eme_windup_shaper`/`hard_dtc_lockstep_monitor` docstrings). GhidraMCP
(`decompile_function`, `disassemble_bytes`, `search_instructions`, `get_xrefs_to`, `read_memory`)
against `code.bin` (stock) this session, functions `FUN_00042af8`, `FUN_00028ea6`, `FUN_0002b422`,
`FUN_0002b57a`, `FUN_00043e44`, `FUN_0004503c`, `FUN_00052676`; raw Python byte reads of
`_v103_V102BASE-BIQUAD.ENGAGED-…_plain_image.bin` for current-build cal confirmation.
