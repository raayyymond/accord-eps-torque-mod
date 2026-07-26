# HANDOFF — 2026-06-29 — 2020 Accord "GENTLE EME" (LKAS-only cut) root-caused → V32 prep

**Platform:** 2020 Honda Accord, `39990-TVA-A160`, Renesas V850E2. **Currently flashed: V31** (2× LKAS).
**openpilot:** sunnypilot, **PID already halved** (`kp 0.6→0.3, ki 0.18→0.09`) in the drives analyzed here.
**STOCK Ghidra program** = `code.bin` (`/master.bin`, 2113 fns). ⚠ NEVER analyze `../accord-firmware/analysis-2020accord/_v27_plain_image.bin`.
**Bases:** `gp = 0xFEDF8000`, `tp = 0xBF000`.

Read alongside: `docs/HANDOFF-2026-06-03-v31.md` (soft-EME lineage), and the three agent-memory files written
this session under `analysis-2020accord/.claude/agent-memory/firmware-codepath-tracer/` and
`.claude/agent-memory/firmware-codepath-tracer/`:
`reference_accord_lkas_column_torque_cut_trigger.md`, `reference_accord_lkas_engage_sm_disengage_trigger.md`,
`reference_accord_can399_torque_vs_voter_scale.md`.

---

## 0. What this is (and what it is NOT)

The **"gentle EME"** is a **DISTINCT** failure from the soft EME (V25–V31 work):

| | soft EME (prior work) | **gentle EME (this handoff)** |
|---|---|---|
| where | rate-shaper `FUN_00042af8`, SM2/SM3 | arbitration `FUN_00028ea6` + engage SM `FUN_000413ae` |
| what cuts | the MERGED command `gp-0x6b98` (assist + LKAS) | **LKAS-only** `gp-0x6b3c`; base assist `gp-0x6bf0` retained |
| driver steering | can be affected | **always available** (driver power steering stays on) |
| CAN signature | DTC 0xF00049 (hard) / internal | **`STEER_STATUS = no_torque_alert_2` (4) + `STEER_CONTROL_ACTIVE = 0`**, no DTC |
| fixed by V31? | yes (boost floor) | **NO — still occurs on V31** |

**Symptom:** on a hard turn (and/or a bump), the EPS momentarily stops delivering LKAS torque, the wheel
falls toward center, the driver grabs to continue. openpilot keeps commanding (latActive stays True) and is
blind to it — `no_torque_alert_2` is openpilot-IGNORED, which is precisely why we know the cut is EPS-side.
The PID halve does **not** fix it: on these hard turns openpilot saturates anyway (cmd = ±1.0), and at the
rail the command is pinned regardless of kp/ki, so the 2× firmware delivers 2× torque and the EME is a
property of the firmware at saturation. **The fix must be firmware.**

---

## 1. THE VERIFIED CODE PATH (root cause)

```
column torque sensor (5 coil ADC channels)
  → voter FUN_00041eec → gp-0x6a62 (0xFEDF159E) = voted + rate-limited column-torque MAGNITUDE (clamp 32000)
  → LKAS engage/disengage SM:  dispatcher FUN_000413ae (state byte gp-0x679c, 0..8)
        engaged handler = state 7 = FUN_00041222  →  calls FUN_00040d58(2):
            if  gp-0x6a62  >=  cal 0xC6312 (= 320)   →   DISENGAGE   (NO debounce)
  → disengage clears deliver flag gp-0x6809 (≠ 1)  + sets STEER_CONTROL_ACTIVE=0 (gp-0x6806),
        STEER_STATUS=no_torque_alert_2 (gp-0x6807)
  → arbitration FUN_00028ea6:  reads gp-0x6809 (ld.bu -0x6809[gp]); when ≠ 1 it ZEROES the LKAS term iVar28
        → request flag gp-0x67a7 = 0
  → delivery SM  m_steer_torque_limit_and_pack FUN_0x2b422:  drops ENABLE byte gp-0x67a4 out of {2,3}
  → gp-0x6b3c (0xFEDF14C4, LKAS-only final torque) = command × (gp-0x67a4 ∈ {2,3})  →  0
        (base assist gp-0x6bf0 is a SEPARATE summed term → driver steering retained)
  → re-engage ramp cal 0xC64DE (=17) brings LKAS back in ~0.1–1 s
```

**THE TRIGGER = one constant: cal `0xC6312` = 320** (`gp-0x6a62 ≥ 320` → disengage). Verified:
- Read the cal bytes directly: `0xC6312 = 40 01` (LE) = `0x0140` = **320**.
- Disengage decider `FUN_00040d58` (`0x40d58`–`0x40e6a`): engaged paths (param 2/3) do
  `if (gp-0x6a62 < tp+0x7312) stay; else disengage(return 2)`. **No debounce counter on this gate.**
- Engaged handler `FUN_00041222` calls `FUN_00040d58(2)` and disengages (`FUN_00040e74`) on a non-zero return.
- The 3 readers of `0xC6312` are at `0x40db8 / 0x40dd0 / 0x40df4` (`ld.hu`, base r5 = tp), ALL inside
  `FUN_00040d58`.

Secondary gate (engage-attempt / re-arm, param 1/4): `gp-0x6a60 ≥ cal 0xC6310 (= 1600)` → refuse engage.
`gp-0x6a60`'s identity needs re-check (see §6 — `gp-0x6a56` turned out to be angle-rate, so `gp-0x6a60 =
|gp-0x6a56|` may be a rate quantity, not torque). The LIVE engaged-disengage gate is the **320** one.

**Cal block `0xC6300`–`0xC631e` (u16 LE), for context** (320 appears exactly once):
```
0xC6300=3200  0xC6302=24   0xC6304=16320 0xC6306=800  0xC6308=160  0xC630A=3200 0xC630C=800  0xC630E=64
0xC6310=1600  0xC6312=320  0xC6314=5120  0xC6316=640  0xC6318=640  0xC631A=640  0xC631C=5120 0xC631E=640
```

---

## 2. RULED OUT (do not re-chase — these cost time this session)

- **bVar1 / the 32000 channel ceiling** (a tracer's first answer): that is a **railed-sensor FAULT** level.
  Real torque tops out ~3400 (driver grab), so the 5 ADC channels never approach 32000. Raising it fixes
  nothing and weakens fault detection. **Wrong lever.**
- **Plausibility flag `gp-0x67f4`** (voter): a LATCH — set when `|fused − voted| < 65`, cleared ONLY in the
  no-valid-coil branch (total coil loss). It does **not** drop on a fast torque transient. (Walked
  `FUN_00041eec` to confirm.)
- **Motor distribute/current clamp** (CAN 427 `MOTOR_TORQUE`): tiny (0–3) and never railed at any cut.
- **Soft-EME SM2/SM3** (rate-shaper): that cuts the merged command — different mechanism, fixed by V31.

---

## 3. LOCKSTEP CHECK ON 0xC6312 — CLEAN (cal-only edit is safe)

- `0xC6312` is read at **exactly 3 sites, all in `FUN_00040d58`** — no consistency monitor, no
  `FUN_00042af8`/`FUN_00043e44`/`FUN_0006b9xx` reads it.
- **No int/float twin** (the engage SM is integer-only; not the corridor/wall dual-path that hard-faulted
  V25–V27). The value 320 appears once in the cal block.
- The runtime value `gp-0x6a62` has its own RAM shadow `gp-0x4cae` (restored by the voter) — that is the
  *value's* redundancy and is unaffected by changing the *threshold* constant.

**Verdict: editing `0xC6312` is a clean cal-only change** — recompute the block-48 / `0xC6000` CRC,
byte-verify, done. NOT the lockstep-fault class.

---

## 4. ROAD DATA (2 rlogs, already decoded this session)

Files: `analysis-2020accord/rlogs/75604b0a432fdc89_00000037--…--9--rlog.zst` (ROUTE37) and
`…_00000036--…--5--rlog.zst` (ROUTE36). Decoders: `analysis-2020accord/analyze_gentle_eme.py` +
`analyze_torque_thresholds.py`. **msg 399 is on CAN src/bus == 1.** Motorola hand-decode:
```
column_torque  = -s16(be_bits(d,7,16))     # STEER_TORQUE_SENSOR, scale -1   (THE signal)
steer_status   =  be_bits(d,39,4)          # 4 = no_torque_alert_2
control_active =  be_bits(d,35,1)          # 0 during the cut
angle_rate     = -0.1 * s16(be_bits(d,23,16))
```

**5 distinct gentle-EME events** (clustered; >2s gap = new event). The two the operator felt:
**Event A** = ROUTE37 @ ~543.469 (RIGHT turn + bump); **Event B** = ROUTE36 @ ~325.537 (LEFT turn + bump).
Others: ROUTE37 @ 554.469, ROUTE36 @ 317.017 & 334.109.

**Typical column torque, NORMAL op-engaged driving (clean baseline, n=6881):**
median **128**, p90 **402**, p95 **584**, p99 **1808**, max **2506**.
Exceedance: `>320` 14.9% · `>640` 4.5% · `>960` 3.0% · `>1600` 1.7% (the high tail is driver-grab/maneuver, not steady LKAS).

**Per-EME column torque (before → during-150ms-peak → @onset → after-grab):**
| event | before | during peak | @onset | after |
|---|---|---|---|---|
| A (R37 543.5) | 101 | 1633 | +1239 | 3403 |
| R37 554.5 | 482 | 2233 | +2233 | 3346 |
| R36 317.0 | 202 | 2169 | +2169 | 2516 |
| B (R36 325.5) | 210 | 1378 | −1378 | 1724 |
| R36 334.1 | 273 | 2290 | −2290 | 3475 |

**Key facts from the data:** torque LEADS velocity (operator-confirmed; this is a TORQUE trigger).
Every EME: quiet baseline (~100–280) → fast spike to **1378–2290** within 150 ms → grab/unwind to 1724–3475.
**No clean per-frame separation:** the 2× reaction band (1378–2290) overlaps the normal hard-maneuver tail
(p99 1808, max 2506). The clean discriminator is rate-of-rise, but a real grab rises just as fast.

---

## 5. THE SCALE (the immediately-preceding question, partially answered)

CAN-side packer **verified** (`FUN_00055c42`):
```
STEER_TORQUE_SENSOR (bytes[0:1]) = -(gp-0x4f60 * 125 >> 7) = -(gp-0x4f60 × 125/128)   ≈ -gp-0x4f60 (×1.024)
STEER_ANGLE_RATE    (bytes[2:3]) = -(gp-0x6a56)
STEER_CONTROL_ACTIVE = gp-0x6806 ;  STEER_STATUS = gp-0x6807 ;  commit FUN_00057b24(gp-0x1420, 7, 399)
```
So **the torque openpilot reads ≈ `gp-0x4f60`** (`0xFEDF30A0`), from pipeline `FUN_0007f3f8` (learned gain `gp-0x698c`).

**The gate variable `gp-0x6a62` is a SEPARATE acquisition** (voter `FUN_00041eec`, ADC channels ×41/64 via
`FUN_000534da`←`FUN_00053216` @ `0x53474 mul 0x29` / `0x53480 sar 0x6`). Two independent measurements of the
same torsion bar, each with a learned gain → **no literal static constant** links them.

**Best estimate: `gp-0x6a62 ≈ |CAN torque|`, ~1:1.** Evidence: both clamp at 32000 ≈ CAN ±31000; the
arbitration uses `gp-0x4f60` (torque, fault guard 25600) and `gp-0x6a5e/gp-0x6a62` (torque, override
breakpoints 3200–8320, gate 320) on ONE scale where 320=nudge / 3200–8320=grip / 25600=rail all make sense.

**Why the gate is 320 but the cut reports at CAN ~1239–2290:** `gp-0x6a62` is voted + rate-limited → it
**LAGS** the faster `gp-0x4f60`/CAN signal on a transient. On a bump, `gp-0x4f60`/CAN rockets to ~1633 while
the slower `gp-0x6a62` is still climbing through 320 — gate fires, CAN reports higher a beat later. In steady
state they converge ~1:1.

**This is exactly what STEP 1 below must nail down.**

---

## 6. ⚠ FLAG — `gp-0x4f60` identity (affects soft-EME memories, NOT the V32 edit)

The packer proves `gp-0x4f60` is the **column-TORQUE** signal (it feeds `STEER_TORQUE_SENSOR`, ranges ±100
hands-off to ±3400 grab). This **contradicts the long-standing project label** of `gp-0x4f60` as "column
angular velocity" used throughout the soft-EME memories (SM1 "velocity arm," the `25600 = 25 deg/s` gate, the
LERP-envelope X-axis). If `gp-0x4f60` is torque, those were torque gates — which aligns with the
torque-trigger finding here. **Park or reconcile separately**; it does not change the V32 gentle-EME edit, but
someone should re-examine whether the soft-EME "velocity" gates are actually on this torque signal.
(`gp-0x6a56`, formerly "polarity-scaled internal reference," packs as `STEER_ANGLE_RATE` → it is angle-rate ×10.)

---

## 7. NEXT STEPS (this is where the new opus session resumes)

### STEP 1 — Map raw torque sensor → the `gp-0x6a62` value compared against 320
Trace the exact arithmetic so the threshold edit is grounded in real units:
- **ADC → channels:** `FUN_00053216` / `FUN_000534da` write `gp-0x6a44/-0x6a40/-0x6a3c/-0x6a38/-0x6a46`
  (5 signed coils), scaling `× 41/64` (`0x53474 mul 0x29`, `0x53480 sar 0x6`). Confirm the raw ADC source +
  any offset, and the per-coil units.
- **Voter `FUN_00041eec`:** the channels → magnitudes → vote/average → **rate-limit** → clamp `0x7d00` →
  `gp-0x6a62` (and `gp-0x6a5e`, `gp-0x6a64`). Pin: (a) the exact vote/average (it tracks the closest-to-fused
  channel, or averages valid coils when spread `< adaptive cal 0xC6318/2`), (b) **the rate limit** (the
  `puVar26` down-rate using `FUN_000074e8[tp+5]`) — this is the LAG that makes the gate fire at 320 while CAN
  shows ~1633. Quantify the rate limit so we can predict `gp-0x6a62`'s peak for a given torque transient.
- **Tie to CAN:** establish the `gp-0x6a62 : |CAN STEER_TORQUE_SENSOR|` ratio. Static analysis bounds it to
  ~1:1; the clean confirmation is **one live RAM read** of `gp-0x6a62` (`0xFEDF159E`) next to CAN
  `STEER_TORQUE_SENSOR` (or `gp-0x4f60` = `0xFEDF30A0`) at a held torque. Decide whether to request that read
  from the operator or proceed on the ~1:1 static bound + headroom.

### STEP 2 — Choose the minimal firmware edit (with a little headroom) for V32
The edit is **raise cal `0xC6312`** (the disengage threshold, currently 320). From §4 + §5:
- At ~1:1, the threshold must clear the `gp-0x6a62` peak during legitimate hard turns. Held/slow hard turns
  reach ~2200 (CAN); fast bumps lag lower. **~2400 robustly stops all 5 logged EMEs.** A smaller value may
  suffice for the bump-only cases — Step 1's rate-limit math should refine this.
- **NOT 640** (an earlier mistaken "2× match"). The 2× reaction reaches 1378–2290, so 640 still trips.
- **Headroom vs nuisance:** normal hard maneuvers reach max 2506 (p99 1808); a genuine driver grab reaches
  1724–3475. Pick a value above the legitimate-reaction peak + a little headroom, while a real grab still
  overrides. Candidate: **~2400–2560** (`0x0960`–`0x0A00`). Name the safety trade plainly: raising 320→~2400
  means the driver must push harder to take authority from LKAS (the grab at 3475 still works).
- Confirm (already done this session, restate in the build): lockstep-clean, cal-only, no twin.

### STEP 2-build — Generate the V32 .rwd
- **Copy `analysis-2020accord/build_v31_tva.py` → `build_v32_tva.py`.** V31's structure: `HERE` =
  `analysis-2020accord`, `REPO` = repo root, `FLASHING` = `flashing-2020accord`. V31 already edits cals in
  block `0xC6000` and recomputes the block CRC.
- **V32 = V31 (ALL edits unchanged: GAIN 1782, clamps 1024, ramp 0x1B, corridor ×4 int+float, boost floor
  4096 int `0xC6768/6A/6C` + float `0xC65C4/C8/CC`, PN) PLUS one new cal edit:**
  `0xC6312`  `320 (0x0140)` → **chosen value (e.g. 2400 = 0x0960)**, 2-byte LE.
- Keep the same rigor as V31: 49/49 CRC, ECU-decode == patched, independent file-level byte-diff classifying
  every changed byte (expect: V31's diff + 2 bytes at `0xC6312` + the recomputed block-48 CRC), **UNFLASHED
  study artifact.** Output naming parallel to V31's `../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V32-…rwd` +
  `../accord-firmware/analysis-2020accord/_v32_plain_image.bin`.

---

## 8. KEY ADDRESSES / FILES (quick reference)

| thing | address / file |
|---|---|
| **Trigger threshold (THE edit)** | cal `0xC6312` = 320 (`tp+0x7312`) — disengage when `gp-0x6a62 ≥` it |
| engage-refuse gate | cal `0xC6310` = 1600 (`gp-0x6a60 ≥`; re-check identity) |
| re-engage ramp | cal `0xC64DE` = 17 |
| disengage decider | `FUN_00040d58` (`0x40d58`–`0x40e6a`); reads of 0xC6312 @ `0x40db8/dd0/df4` |
| engage SM dispatcher | `FUN_000413ae`, state byte `gp-0x679c` |
| engaged handler (state 7) | `FUN_00041222` → `FUN_00040d58(2)` → disengage via `FUN_00040e74` |
| torque voter | `FUN_00041eec` → `gp-0x6a62` (`0xFEDF159E`), `gp-0x6a5e` (`0xFEDF15A2`), `gp-0x6a64` |
| ADC channel readers (×41/64) | `FUN_00053216` / `FUN_000534da`; coils `gp-0x6a44/-0x6a40/-0x6a3c/-0x6a38/-0x6a46` |
| deliver flag (gate in arb) | `gp-0x6809` (`0xFEDF17F7`); siblings `gp-0x6806`=ctrl-active, `gp-0x6807`=status |
| arbitration (zeroes LKAS) | `FUN_00028ea6`; LKAS term `iVar28→0` when `gp-0x6809≠1` |
| delivery SM (ENABLE byte) | `m_steer_torque_limit_and_pack` `FUN_0x2b422`; ENABLE `gp-0x67a4 ∈ {2,3}` |
| LKAS-only output | `gp-0x6b3c` (`0xFEDF14C4`) = command × (ENABLE∈{2,3}) |
| CAN 399 packer | `FUN_00055c42`; torque field `FUN_000218be` = `-(gp-0x4f60 ×125/128)` |
| CAN-torque source | `gp-0x4f60` (`0xFEDF30A0`), pipeline `FUN_0007f3f8`, learned gain `gp-0x698c` |
| rlogs | `analysis-2020accord/rlogs/…--9--rlog.zst` (R37), `…--5--rlog.zst` (R36); msg 399 on src 1 |
| decoders | `analysis-2020accord/analyze_gentle_eme.py`, `analyze_torque_thresholds.py` |
| V31 build script (copy this) | `analysis-2020accord/build_v31_tva.py` |
| agent memories (this session) | `…/.claude/agent-memory/firmware-codepath-tracer/reference_accord_lkas_column_torque_cut_trigger.md`, `…_lkas_engage_sm_disengage_trigger.md`, `…_can399_torque_vs_voter_scale.md` |

---

## 9. IRON RULES (unchanged)

- **No flash without the operator naming file + bus; repeat it back first.** V32 is a STUDY ARTIFACT.
- V32 changes **only calibration data** — zero executable bytes (byte-verify, like V31).
- Before any flash on a comma device, openpilot/pandad must be killed (`tmux kill-server`).
- Analyze STOCK `code.bin` only — never `../accord-firmware/analysis-2020accord/_v27_plain_image.bin`.
- When a tracer's load-bearing claim conflicts with road data or prior work, **walk the disasm yourself**
  (this session: corrected a tracer's "raise 32000" answer, and verified the CAN packer by hand).
