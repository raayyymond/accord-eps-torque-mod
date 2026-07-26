# Session 2026-05-30 — Accord EME mechanism resolved + V20A/V20B built

Consolidated findings from the V19-drive EME investigation. This is the SINGLE source for
this session; the canonical memories (`reference_accord_override_snap_state_machines.md`,
`project_accord_torque_mod_v0.md`, `reference_accord_pointer_base_audit.md`,
`EME_OVERRIDE_SM_NONVERIFIED.md`) should POINT here, not duplicate it. Pending: fold the
one-liners into each canonical home + MEMORY.md/constellation (not yet done — compaction hit).

## What was driven / asked
Operator drove V19. Sustained turns no longer reliably trigger EME, but EMEs still occur —
now on SHORTER turns too (90° stoplight, gentle merge), and when countering/maxed LKAS.
Log: `analysis-2020accord/v19_eme_log_steering_extract.jsonl` (qlog ~10 Hz). Goal: high-end
2×→3× LKAS torque without EMEs via minimal firmware mods, safety understood not defeated.

## THE LOGGED EME — characterized (the discriminator the project lacked)
RIGHT turn (this log: negative angle = right; metadata "positive=right" is inverted for this
signal). Data caveats: `steeringTorqueEps` (CAN 0x427 motor torque)=0 ALL samples (not
captured); `cmd_torque_norm` sign-flipped vs `actual_torqueOutputCan`. Reliable: angle,
driver torque, latActive, actual_torqueOutputCan magnitude (rails ±4096).
Timeline: opposing command railed +4096 at t=24.94s → wheel decelerated to STATIONARY (~0°/s)
by 25.74s → CUT/snap at 26.14s (~1.2 s sustained-opposing, column ~stationary at the cut).
latActive stayed TRUE through the cut → firmware-side cut, not an openpilot disengage.

## ROOT CAUSE — shaper authority-monitor WIND-UP (SM2/SM3), [STRONG] by elimination + fit
All instant/off-shaper candidates RULED OUT for the hands-off cut (see below). The monitor
integrator `gp-0x3570` is an **ACCUMULATOR of command-excess-over-envelope**, not a tracker:
per cycle `integ += (command − envelope)<<15`, clamped to ±(cal[0x71dc]<<15). uVar53=|integ>>15|
winds up under sustained excess. At 1× command rides under the envelope → bleeds off, never
trips. At 2×+ it exceeds the envelope → winds to saturation → SM cut. This UNIFIES long and
short EMEs: trip speed = command-excess-over-envelope (turn SHARPNESS), NOT turn length —
matches the operator's "length no longer predictive" observation.
- SM1 RULED OUT for this event: arming requires LIVE column velocity > cal 0xC61E0=7168;
  column was stationary at the cut and SM1 arm→trip is only ~12 cyc. (SM1 is the
  fight-on-motion monitor; left STOCK in all builds.)
- SM3 genuinely CUTS to 0 (cal tp+0x7420=0xC6420=0 is the node value on trip) — a prior
  tracer's "SM3 only reduces authority" was WRONG; verified 0xC6420=0x0000.

## VERIFIED NUMBERS (this session)
- **Shaper cycle rate = 1000 Hz (1 ms/cycle)** [STRONG] — via +0.001 s/call dt accumulator in
  co-called FUN_00043e44 + TAUA1 timer-ISR→scheduler→w_steer_control_task chain. NOT 100 Hz
  (prior assumption was 10× too slow). Dwell windows are therefore TINY: SM2≈5–6 ms, SM3≈20 ms,
  SM1≈12 ms → raising dwell is a near-useless lever vs a ~1200-cycle (1.2 s) event. (Earlier
  dwell-raise recommendation RETRACTED once rate was corrected.)
- **SM dwell cals**: SM2 = `tp+0x74ff`=0xC64FF=**5** (counter gp-0x6710); SM3 = `tp+0x7298`=
  0xC6298=**20** (accum gp-0x3568). SM2 cuts ~3× faster than SM3 once armed; both zero node gp-0x6962.
- **SM3 max = 0xFFFF**: cal 0xC61DC is BOTH integrator clamp AND SM3 trip. 16-bit field (ld.hu)
  → max 0xFFFF; clamp = cal<<15, 0xFFFF<<15=0x7FFF8000 (positive int32, safe); 0x10000 would be
  negative. SM3 compares uVar53 directly → 0xFFFF coherent.
- **SM2 uVar34 wrap**: SM2 compares uVar34=(uVar53*1092)>>10 truncated 16-bit (zxh); wraps when
  uVar53 > ~61454. V19's SM3=61440 sat just under it on purpose. With SM3=0xFFFF the integrator
  can enter the wrap zone, but it only affects SM2 — and SM2 arms far below (V20A 32768→uVar53
  ~30728; V20B 49152→~46091), so SM2 binds first and the wrap zone never decides. 49152 is the
  practical SM2 ceiling for "3×"; higher risks wrap incoherence.
- **Envelope** = two velocity-indexed LERP tables, plateau ±1024 LSB:
  T1 upper `tp+0x7748`=0xC6748 (count=2, X={-8192,-1024}, Y={1024,1024,0});
  T2 lower `tp+0x7754`=0xC6754 (count=2, X={1024,8192}, Y={-1024,-1024,0});
  X = gated column angular velocity gp-0x4f60 (Q10, raw/1024; HW gate |v|≥25600→0).
  Multiplied by POLARITY byte gp-0x6752 (±1, NEVER 0) → **envelope is LIVE during turns** (the
  earlier "inert in mode 0" claim conflated gp-0x6752 with the command-mode byte tp+0x74c8=0).
  Envelope DECLINED as a lever this session: high-velocity tail (Y2=0 collapse) unresolved.
  Plot: `analysis-2020accord/_envelope_lerp_plot2.png` (script `_envelope_lerp_plot2.py`).
  **⊕ 2026-05-30 GATING FINDING (verified 0x43116–0x43134):** T1/T2 output is selected by
  **DRIVER ASSIST** `gp-0x6bf0` (NOT the LKAS command `gp-0x6acc`). Threshold ±9216 (`0xC6156`):
  `driver_assist < -9216` → T1 only; `driver_assist > +9216` → T2 only; `|driver_assist| < 9216`
  → **BOTH outputs = 0**. During hands-off LKAS (`gp-0x6bf0 ≈ 0`), the LERP envelope is ENTIRELY
  INACTIVE; integrator bounds come from velocity-based rate-shaper only. This is why stock 1×
  (cmd ~418) never trips SM2/SM3 — the rate-shaper bound is never crossed at stock command.
  2× EMEs are a rate-shaper-bound collapse at stalled column, not a LERP plateau crossing.
  T1/T2 are mutually exclusive alternatives (not simultaneous upper/lower bounds); prior plot
  overlaid both without showing this, creating a misleading "dead zone" annotation. Plot corrected.
  **OPEN:** velocity-breakpoint asymmetry (T1 releases at -1 deg/s, T2 at +8 deg/s) — operator
  is skeptical this reflects real left/right behavioral asymmetry; investigate future session.

## OFF-SHAPER INSTANT CUTS — all ruled out for hands-off 2× short-turn EME
- Observer-edge gate (FUN_00041d56→counter gp-0x671d≥3→zeroes LKAS-enable gp-0x67fe): the
  signal gp-0x4fd8 is **accumulated motor rotor electrical angle** (π/2048 scale); the observer
  is a JERK detector (decays to 0 at steady velocity), NOT 2×/velocity-scaled. Entry gate
  cal 0xC61FA=5530, inner 0xC61F8=1024 (NOT 41060 — that was a +0x1000 address slip). UNLIKELY.
- Fault-bit-8 (FUN_00046ea6(8) reads bit8 of gp-0x18d4): both reachable channels dwell-based,
  not 2×-driven. UNLIKELY. (bit→channel map lives in RAM descriptor, [OPEN].)
- Plausibility voter gp-0x67f4 (FUN_00041eec): sets 0 only on all-5-ADC-channel sensor LOSS
  (alive window ±~14544); downstream only CHANGES A RATE (governor 512→205), NOT a cut. Needs
  real sensor fault, not hands-off. UNLIKELY.
- Mode-byte gate gp-0x67a4/gp-0x3d28 (m_steer_torque_limit_and_pack; arb zeroes gp-0x6b3c when
  gp-0x67a4∉{2,3}): TORQUE-BLIND — every drop-out tests a mode handshake (gp-0x67a1 from
  m_motor_cmd_distribute_clamp, or gp-0x67a7), never a torque magnitude. UNLIKELY for 2× EME.
- **gp-0x4e65 is NOT on the LKAS torque path** — real accesses are in the resolver/rotor cluster
  (FUN_00065af8/65eda/6651e/6964c), NOT arb/shaper. The EME doc's "assist-mode dropout
  gp-0x4e65 3→1" suspect is MISLOCATED — do not trust that line.

## V20 BUILDS (UNFLASHED)
Builder: `analysis-2020accord/build_v20_tva.py`. Method: decode validated V19 .rwd (cipher v9b
keys BF,10,9E / xor,xor,sub), patch cal halfword(s) in the 0x13000 window, recompute ONLY
block#48 CRC @0xC6FFC (both cals inside [0xC6000,0xC6FFC); main block @0xC4FFC untouched),
re-encode with V19 headers. (The stock image is
../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin and the header template is
../accord-firmware/iHDS_rwds/CalibFiles/39990-T2F-A210.rwd.gz; both are external to this checkout.)
- **V20A** = V19 + SM3 0xF000→0xFFFF (max @0xC61DC). SM2 stays 0x8000. byte-diff vs V19 = 6 B
  (0xC61DC-DD cal 2B + 0xC6FFC block#48 CRC 4B). Expected ~INERT vs V19 (SM2 still binds first)
  → controlled "isolate SM3" test.
- **V20B** = V19 + SM3 0xF000→0xFFFF AND SM2 0x8000→0xC000 (49152, 3× of stock 16384 @0xC6422).
  byte-diff vs V19 = 7 B (SM3 cal 2B + SM2 high-byte 1B at 0xC6423 + block#48 CRC 4B; SM2's low
  byte 0x00 was already 0x00 in V19 so only 1 byte changed). The actual "3× gate" set — real
  loosening of an anti-oscillation guard.
  Both: 986042 B, build self-verify OK (re-decode==patched, both block CRCs valid, GAIN=1782 +
  PN-fix lineage intact). **Real sha256 in `analysis-2020accord/_v20_hashes.txt`** (do NOT trust
  any inline hash — earlier drafts of this doc contained placeholder hashes that were removed).

## SAFETY / LEVER SUMMARY for 3×
SM3 is CAPPED at 0xFFFF (architectural) — a truly SUSTAINED 3× opposing command still winds to
it eventually; no finite firmware threshold defeats that. Real root-cause fix = COMMA-SIDE:
don't hold a maxed OPPOSING command for >~hundreds of ms (ramp/decay it — what your hands do
when you intervene, which is why the EME bites when you DON'T). Firmware levers
(SM2/SM3 thresholds) buy wind-up TIME; envelope would slow per-cycle wind-up but is unresolved.

## TOOLING PITFALLS TO PREVENT REPEATS (cost real time this session)
1. **+0x1000 address slip**: tp=0xBF000, so tp+0x7NNN = 0xC6NNN, NOT 0xC7NNN. Bit two tracers
   AND me (0xC7420 vs 0xC6420; 0xC71F8=41060 vs 0xC61F8=1024). ALWAYS read_memory to confirm.
2. **search_instructions**: param is `operand_pattern` (not `operand`); match is on the RENDERED
   string — use the hex offset substring like "4e65", NOT "-0x4e65[gp]". get_xrefs_to on an
   absolute RAM addr (0xFEDF…) returns NOTHING (code uses gp-relative displacement) — use
   search_instructions on the offset hex instead.
3. **Don't hand subagents unverified addresses** — I passed the gp-0x4e65 tracer 3 addresses
   that were actually OTHER variables because my pre-scoping searches silently errored. Verify
   anchors first.
4. **Decompile of FUN_00042af8 is ~55k chars** → exceeds tool cap; saved to
   `_decomp_42af8.txt` / `_disasm_42af8.txt` (note: an on-disk `_disasm_42af8.txt` got
   MISLABELED with FUN_000757a2 once — re-pull if greps return nothing).
5. Mode-0 integrator is an ACCUMULATOR not a tracker → SM2/SM3 ARE reachable, V19 edits ARE
   LIVE (initial "V19 inert" conclusion was WRONG; operator's V18-vs-V19 observation was the
   correct check that overturned it).

---

## 2026-05-31 — LERP3 Dual-Path Investigation + FUN_00043e44 Full Decompile

Initial findings below were [UNCONFIRMED] when first written. FUN_00043e44 was subsequently
fully decompiled via Ghidra MCP (2026-05-31). Key Finding 2 (integer/float dual path, LERP1
not applied in float path) is **CONFIRMED** by the full decompile. Finding 1 (gp-0x3578
second IIR state) remains unverified at the integer-shaper level.

**Full analysis:** `FUN_00043e44_FLOAT_MONITOR.md`  
**Raw decompile:** `_decomp_43e44.txt`

### What the full decompile resolved

- **FUN_00043e44 is REPORT-ONLY.** It is a float-domain watchdog that cross-checks the integer
  shaper's outputs. It writes `gp-0x6906` (s16 fault word) and fires fault `0x3f1b` via
  `FUN_000462e6`. It does NOT write to `gp-0x6b98` or any torque path. (Confirms
  `reference_accord_override_snap_state_machines.md` — the "dual-path int/float monitor" entry.)
- **gp-0x6574 / gp-0x65a0 / gp-0x65a4 / gp-0x65a8 / gp-0x65d8 are intermediate float LERP3
  arrays** built within this function each cycle. They feed the float LERP interpolation that
  produces upper/lower envelope bounds (fVar8 / fVar26), which then go through IIR smoothing
  (states gp-0x3554, gp-0x3558) and polarity-gated bound selection. They do NOT feed back
  into gp-0x3574/gp-0x3578 (the integer shaper's IIR states). The two paths are structurally
  independent — the float monitor observes, the integer shaper controls.
- **LERP1 not applied: CONFIRMED.** The float path reads `gp-0x6444` raw and adds
  `lerp_a × lerp_b` directly in the Y-build loop. The integer shaper applies LERP1 as an
  additive Y-shift before the loop. For linear tables these are algebraically equivalent;
  the float path uses a distinct set of float cal tables (tp+0x75D4..0x767C range) entirely
  separate from the integer LERP1/2/3 cals at tp+0x7770/0x79E8.
- **V21 patch scope confirmed correct.** Patching the integer shaper's shl instructions
  does not affect FUN_00043e44. The monitor will continue to report the stock envelope as
  its reference — which is the right behavior (watchdog should reflect design intent).
- **Shared cal tp+0x71DC (0xC61DC) confirmed.** This cal appears in FUN_00043e44 as the
  integrator clamp ceiling (via `DAT_000071dc + unaff_tp`). Raising it (V20A/B) proportionally
  scales both the SM3 arming threshold in FUN_00042af8 AND this float monitor's integrator.
- **SM timer proves 1000 Hz.** `gp-0x3550` increments by exactly 0.001f per call in state 2.
  Previously derived from the TAUA1 chain; now directly observed in this decompile too.

### Finding 1 — gp-0x3578 is a second rate-shaper IIR state (lower/negative bound) missed by V21  [UNVERIFIED at integer-shaper level]

The shaper contains **two** IIR outputs, not one:
- `gp-0x3574` — upper (positive) envelope bound. V21 patched its `shl` at `0x42DAE`/`0x42DCA`.
- `gp-0x3578` — lower (negative) envelope bound. **V21 did NOT patch this path.**

The gp-0x3578 path:
- IIR state loaded at `0x42F24: ld.w -0x3578[gp], r9`; stored at `0x42F4C: st.w r9, -0x3578[gp]`
- `shl 0x8, r10` at **`0x42F16`** (byte `0xC8`) — the unpatched scaling instruction
- The `shl 0x8` fires **before** the IIR-vs-bypass branch (`be 0x42F40`), so ONE patch covers
  both IIR and bypass cases (unlike gp-0x3574 which has two separate `shl` patches)
- Value stays in register r9, consumed at `0x43142: sar 0x8, r9` (same pipeline as gp-0x3574
  at `0x43136: sar 0x8, r11`)
- Only 2 refs in the entire firmware — both within the shaper; not independently read elsewhere
- gp-0x3578 absolute RAM: `0xFEDF8000 - 0x3578` = `0xFEDF4A88`

**Candidate V22 code-byte patch for symmetric 2×:**
```python
(0x42F16, 0xC8, 0xC9, "SHL imm  0x42F16  shl 0x8,r10 -> shl 0x9,r10  [lower-bound IIR+bypass]")
```

**Open questions (not yet verified):**
- Is gp-0x3578 actively driving SM3 wind-up behavior, or is it a passive mirror the integrator
  never actually hits in normal LKAS operation?
- Does the bypass path condition (check on r8 = setflt of column velocity sign) mean this path
  only updates under specific velocity directions?

### Finding 2 — Integer/float dual path on the LERP3 Y table  [CONFIRMED by full decompile 2026-05-31]

The LERP3 Y values (`gp-0x6444`, 10 halfwords, runtime RAM) are consumed by **two separate
computation paths** that read the same table:

**Integer path — inside `s_motor_torque_rate_shaper` (FUN_00042af8):**
- `movea -0x6444, gp, ep` at `0x42CAE`; loads all 10 Y values
- Applies LERP1 additive shift: `mul r8, r25, r0` / `sar 0xa, r25` / `add r25, Yval` at
  `0x42CBA–0x42CF0` (r25 = LERP1 output, r8 = LERP2 output = 1024 always)
- Integer LERP3 interpolation (mul/divq arithmetic)
- Scaled by `shl 0x8` → IIR → stored to `gp-0x3574` / `gp-0x3578`
- **LERP1 is part of this path only** — the additive Y-shift is woven in here

**Float path — inside `FUN_00043e44` (co-called with the shaper at 1000 Hz):**
- `ld.hu -0x6444[gp], r16` at `0x4402E`; `ld.hu -0x6444[ep], r10` at `0x4406C` (loop)
- Also reads `gp-0x6430` (LERP3 count) at `0x44002` and `0x44062`
- Converts to float: `cvtf.uws`, then computes float LERP: `mulf.s`, `subf.s`, `divf.s`,
  `maddf.s`, `addf.s`, `trncf.sw`
- Writes float LERP results to `gp-0x6574`, `gp-0x65a0`, `gp-0x65a4`
- Then negates via `negf.s` → stores into `gp-0x65a8` / `gp-0x65d8` arrays
- **LERP1 is NOT applied** — the float path reads `gp-0x6444` raw with no additive shift
- V21 did not touch FUN_00043e44

**FUN_000352b4** (called from `w_steer_control_task` at `0x2214a`; body `0x352b4–0x35b1f`):
- Contains float FPU instructions: `cvtf.uws`, `mulf.s`, `msubf.s`, `divf.s`, `cmpf.s`,
  `trncf.suw` — this is the float arithmetic that *produces* the LERP3 Y values in `gp-0x6444`
- At `0x35378: movea -0x6444, gp, ep` followed immediately by reads from ep — appears to be
  reading gp-0x6444 as input to further computation (not the primary writer)
- Also references `tp+0x7384` = `0xC6384` (a flash cal used in the float formula)
- Writer relationship to gp-0x6444 vs gp-0x37xx not fully resolved this session

**Implication for 2× mod:**
- Changing **LERP1 values** (flash cal at `tp+0x7770` = `0xC6770`) affects the integer path
  only (additive Y-shift) — the float path does NOT see LERP1
- Changing **LERP3 Y values** at the source (gp-0x6444) would affect both paths simultaneously,
  but gp-0x6444 is runtime-computed and not directly flash-patchable
- To scale the float path 2×: requires either a code-side multiplier change in FUN_00043e44,
  or a change to the flash cal that FUN_000352b4 reads (e.g. `tp+0x7384` = `0xC6384`)
- V21's `shl 0x8→0x9` approach is correct for the integer path; the float path needs its own
  equivalent intervention

**Open questions (status after 2026-05-31 decompile):**
- ~~What do gp-0x6574 / gp-0x65a4 / gp-0x65a8 / gp-0x65d8 ultimately feed into?~~
  **CLOSED:** These are intermediate float arrays built within FUN_00043e44 and consumed
  only within it. They feed the float LERP interpolation → IIR → polarity selection →
  fault accumulation → gp-0x6906. They do NOT merge into gp-0x3574/gp-0x3578 or any
  torque path. FUN_00043e44 is a reporting-only watchdog.
- ~~Does FUN_00043e44's float path need independent scaling for a 2× mod?~~
  **CLOSED:** No — the float monitor reflects the stock design envelope as reference.
  Patching only the integer shaper is correct; the monitor should stay at stock.
- **OPEN:** Is FUN_000352b4 a reader or writer (or both) of gp-0x6444? The float path
  reads gp-0x6444 raw. Identifying who writes it determines whether gp-0x6444 can be
  modulated via a cal change in FUN_000352b4 (e.g. tp+0x7384 = 0xC6384).
- **OPEN:** gp-0x6b4a identity (secondary velocity combined when tp+0x74CB == 1).
