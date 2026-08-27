# FUN_00043e44 — Float Rate-Shaper Monitor

**Decompiled:** 2026-05-31 via Ghidra MCP.  
**Raw output:** `_decomp_43e44.txt`  
**Bases:** `tp = 0xBF000` (app), `gp = 0xFEDF8000`  
**Integer parallel:** `s_motor_torque_rate_shaper` (`FUN_00042af8`)

---

## Role and architecture

`FUN_00043e44` is the **float-domain parallel path** of the integer rate-shaper. It is called
co-temporally with `FUN_00042af8` at **1000 Hz** (proven: SM timer increments `+= 0.001f` per
call = 1 ms/call; see notes/SESSION-2026-05-30-EME-RESOLUTION.md §"VERIFIED NUMBERS"). It reads the
same runtime RAM signals as the integer shaper, recomputes the rate-shaper envelope in
single-precision float, then cross-checks the integer shaper's outputs.

**This function is REPORT-ONLY.** It writes a fault word to `gp-0x6906` (s16) and fires fault
code `0x3f1b` via `FUN_000462e6` → telemetry packer `FUN_00056518`. It does NOT write to
`gp-0x6b98`, `gp-0x6960`, `gp-0x6962`, `gp-0x6787`, or any other torque-path RAM.
Confirmed in `reference/firmware/reference_accord_override_snap_state_machines.md`.

---

## Key structural difference from the integer path

The integer shaper applies a **LERP1 additive Y-shift** to `gp-0x6444` before building the
LERP3 Y array (shift = `lerp1_out × lerp2_out >> 10`). This function reads `gp-0x6444`
**raw** and adds `lerp_a × lerp_b` directly in the loop. There is no LERP1 equivalent in the
float path — the float LERP_A table at `tp+0x75D4/0x75F0` is a distinct cal, not the same
table as integer LERP1 at `tp+0x7770`.

For linear LERP tables the two approaches are algebraically equivalent. The difference only
matters if the integer path's LERP1 shifts values past the u16 ceiling.

**Consequence for V21/V22 modding:** Patching the integer shaper's `shl 0x8 → 0x9` at
`0x42DAE`/`0x42DCA` (for `gp-0x3574`) or `0x42F16` (for `gp-0x3578`) does NOT affect this
function. The float path has no analogous shift instruction to patch. The float monitor will
continue to report the un-doubled envelope as the reference, which is the CORRECT behavior —
it is the watchdog; it should reflect the designed-in envelope, not the modded one.

---

## Signal table

| Signal | Address (absolute) | Type | Role |
|---|---|---|---|
| `gp-0x6a28` | `0xFEDF15D8` | u16 | Assist magnitude (LERP_A input) |
| `gp-0x4f60` | `0xFEDF30A0` | s16 Q10 | Column angular velocity [STRONG] |
| `gp-0x6b4a` | `0xFEDF14B6` | s16 Q10 | Secondary velocity (gated by tp+0x74CB) |
| `gp-0x6bf0` | `0xFEDF1410` | s16 ÷128 | Driver assist magnitude |
| `gp-0x6752` | `0xFEDF18AE` | s8 | Polarity byte (±1) |
| `gp-0x6acc` | `0xFEDF1534` | s16 Q10 | FOC/motor output (±8 gate) |
| `gp-0x6af6` | `0xFEDF150A` | s16 Q10 | Shaper reference signal |
| `gp-0x6b00` | `0xFEDF1500` | s16 Q10 | Motor reference signal |
| `gp-0x6b0a` | `0xFEDF14F6` | u16 Q10 | Integrator reference |
| `gp-0x6b04` | `0xFEDF14FC` | s16 Q10 | Mode reference |
| `gp-0x6b98` | `0xFEDF1468` | s16 Q10 | Shaper output (FOC input) — READ ONLY here |
| `gp-0x6ac2` | `0xFEDF153E` | u16 | Motor/rotor speed (governor input) |
| `gp-0x4f64` | `0xFEDF309C` | u16 Q10 | Governor runtime cal (also cal tp+0x7202=0xC6202) |
| `gp-0x6430` | `0xFEDF1BD0` | u16 | LERP3 count/first-X field (runtime) |
| `gp-0x6444` | `0xFEDF1BBC` | u16×10 | LERP3 Y base values (runtime, from FUN_000352b4) |
| `gp-0x6966` | `0xFEDF169A` | u16 | Time/speed signal (Q15 scale) |
| `gp-0x354c` | `0xFEDF4AB4` | float | Time accumulator (read; written at end of fn) |
| `gp-0x3544` | `0xFEDF4ABC` | float | Timing state |
| `gp-0x3548` | `0xFEDF4AB8` | float | First-call reset flag (1.0f=reset, 0.0f=normal) |
| `gp-0x3554` | `0xFEDF4AAC` | float | IIR state: upper bound |
| `gp-0x3558` | `0xFEDF4AA8` | float | IIR state: lower bound |
| `gp-0x3540` | `0xFEDF4AC0` | byte | Fault SM state (0–3) |
| `gp-0x3550` | `0xFEDF4AB0` | float | Fault SM timer (s) |
| `gp-0x6dc8` | `0xFEDF1238` | float | Integrator accumulator state (persistent) |
| **`gp-0x6906`** | **`0xFEDF16FA`** | **s16** | **Fault word output (REPORT-ONLY)** |

### Float arrays built at runtime by this function

| Array | Base address | Size | Content |
|---|---|---|---|
| Forward X | `gp[-0x6574]` = `0xFEDF1A8C` | 12 floats | LERP3 X breakpoints (float, ÷1024) |
| Forward Y | `gp[-0x65a4]` = `0xFEDF1A5C` | 12 floats | LERP3 Y values + `lerp_a×lerp_b` offset |
| Negated X | `gp[-0x65a8]` = `0xFEDF1A58` | 12 floats | `-X[j]`, stored at `gp[-0x65a8 - j*4]` |
| Negated Y | `gp[-0x65d8]` = `0xFEDF1A28` | 12 floats | `-Y[j]`, stored at `gp[-0x65d8 - j*4]` |

### Cal table addresses

| Cal | Flash address | Value (stock) | Role |
|---|---|---|---|
| `tp+0x75D4` | `0xC65D4` | float table | LERP_A X breakpoints |
| `tp+0x75F0` | `0xC65F0` | float table | LERP_A Y values |
| `tp+0x7648` | `0xC6648` | float table | LERP_B X breakpoints |
| `tp+0x7664` | `0xC6664` | float table | LERP_B Y values |
| `tp+0x75B8` | `0xC65B8` | float table | Governor LERP X |
| `tp+0x75C4` | `0xC65C4` | float table | Governor LERP Y |
| `tp+0x75A4` | `0xC65A4` | float table | Driver-assist hi-side LERP X |
| `tp+0x75AC` | `0xC65AC` | float table | Driver-assist hi-side LERP Y |
| `tp+0x7590` | `0xC6590` | float table | Driver-assist lo-side LERP X |
| `tp+0x7598` | `0xC6598` | float table | Driver-assist lo-side LERP Y |
| `tp+0x74CA` | `0xC64CA` | byte | IIR enable (1=enabled) |
| `tp+0x74CB` | `0xC64CB` | byte | Combine-velocities flag (1=add gp-0x6b4a) |
| `tp+0x7418` | `0xC6418` | 10 | IIR alpha (÷1024 = ~0.00977) |
| `tp+0x741C` | `0xC641C` | 32440 | IIR startup delay threshold (Q15 ≈ 0.990 s) |
| `tp+0x741A` | `0xC641A` | ? | Driver-assist time-enable threshold (Q15) |
| `tp+0x741E` | `0xC641E` | 16384 | Second timing threshold (Q15 = 0.5 s) |
| `tp+0x74E3` | `0xC64E3` | byte | Timer cal (×0.001) |
| `tp+0x74C8` | `0xC64C8` | byte | Command mode selector (0/1/2) |
| `tp+0x74C9` | `0xC64C9` | byte | Command mux flag (1=use FOC only) |
| `tp+0x74A4` | `0xC64A4` | byte | Fault SM enable gate (0=enabled) |
| `tp+0x71E4` | `0xC61E4` | 3072 | LERP3 X spacing (÷1024 = 3.0) |
| `tp+0x71D4` | `0xC61D4` | s16 | Fixed command cal (mode 1/2) |
| `tp+0x71D8` | `0xC61D8` | s16 | Command offset cal |
| `tp+0x71DA` | `0xC61DA` | u16 | Decay multiplier for timer |
| `tp+0x71DC` | `0xC61DC` | **30720 (V18/V19) / 61440 (V20A/B)** | Integrator clamp = SM3 arming threshold (shared cal) |
| `tp+0x7156` | `0xC6156` | u16 | Driver-assist deadband threshold (×0.0078125) |

---

## Pseudocode

```
// Called at 1000 Hz alongside s_motor_torque_rate_shaper (FUN_00042af8)
// REPORT-ONLY: writes gp-0x6906 (fault word s16), fires fault 0x3f1b. No torque gating.

void FUN_00043e44(char sched_tick_expected) {

    // ── 1. LERP_A: assist_magnitude → float envelope scale factor ──────────
    // gp-0x6a28 = raw assist magnitude (u16), scaled ×(1/64) in float path
    // (integer shaper uses this as the raw u16 LERP1 index; scale differs)
    float assist_mag = (float)(u16)(gp[-0x6a28]) * 0.015625f;   // ÷64
    gp[-0x6cf4] = assist_mag;                                    // debug store

    // Float LERP table: X@tp+0x75D4, Y@tp+0x75F0 (NOT the same as int LERP1 @tp+0x7770)
    float lerp_a = float_lerp(X@tp+0x75D4, Y@tp+0x75F0, assist_mag);


    // ── 2. VELOCITY PROCESSING ─────────────────────────────────────────────
    // gp-0x4f60: column angular velocity (s16 Q10 = ÷1024), gate |v| ≥ 25 → 0
    float v_col = (|gp[-0x4f60]/1024.0| >= 25.0) ? 0.0f
                  : (float)(s16)(gp[-0x4f60]) / 1024.0f;
    gp[-0x6da8] = v_col;

    // gp-0x6b4a: secondary velocity (s16 Q10), same gate
    float v2 = (|gp[-0x6b4a]/1024.0| >= 25.0) ? 0.0f
               : (float)(s16)(gp[-0x6b4a]) / 1024.0f;

    // Combine if tp+0x74CB == 1; clamp result to ±25.0
    float vel_combined = (tp[0x74CB] == 1) ? v_col + v2 : v_col;
    float vel = clamp(vel_combined, -25.0f, 25.0f);
    gp[-0x6db4] = vel;


    // ── 3. LERP_B: clamped_vel → velocity-indexed envelope modifier ────────
    // Float LERP table: X@tp+0x7648, Y@tp+0x7664
    float lerp_b = float_lerp(X@tp+0x7648, Y@tp+0x7664, vel);


    // ── 4. LERP3 FLOAT ARRAY BUILD ─────────────────────────────────────────
    // Reads gp-0x6430 (count/first-X, runtime u16) and gp-0x6444 (Y base, 10×u16, runtime).
    // ⚠ LERP1 additive Y-shift NOT applied (integer shaper does apply it).
    // Builds 12-element forward X[] at gp[-0x6574+i*4] and Y[] at gp[-0x65a4+i*4].
    // Y values include lerp_a*lerp_b offset (equivalent to the integer path's combined shift).

    float x_step = (float)(s16)(tp[0x71E4]) / 1024.0f;  // 3072/1024 = 3.0
    float cnt_f  = (float)(u16)(gp[-0x6430]) / 1024.0f;  // count field, scaled

    // Elements 0 and 1 are prologues bracketing the actual breakpoints:
    X[0] = (cnt_f - 0.5f) - x_step;    // gp[-0x6574]
    Y[0] = 0.0f;                        // gp[-0x65a4]
    X[1] = cnt_f - x_step;             // gp[-0x6570]
    Y[1] = (float)(u16)(gp[-0x6444]) / 1024.0f + lerp_b * lerp_a;  // gp[-0x65a0]

    for (int i = 0; i < 10; i++) {
        X[i+2] = (float)(u16)(gp[-0x6430 + i*2]) / 1024.0f;           // gp[-0x6574+(i+2)*4]
        Y[i+2] = (float)(u16)(gp[-0x6444 + i*2]) / 1024.0f + lerp_b * lerp_a;  // gp[-0x65a4+(i+2)*4]
    }

    // Build negated mirror arrays (for lower-bound lookups):
    //   neg_X[j] = -X[j] stored at gp[-0x65a8 - j*4]   → gp[-0x65a8..gp[-0x65d4]
    //   neg_Y[j] = -Y[j] stored at gp[-0x65d8 - j*4]   → gp[-0x65d8..gp[-0x6604]
    // Unrolled 4-elements per iteration (iVar13 loop: 3 iters × 4 = 12 total)
    for (int j = 0; j < 12; j++) {
        gp[-0x65a8 - j*4] = -X[j];
        gp[-0x65d8 - j*4] = -Y[j];
    }


    // ── 5. LERP INTERPOLATION: forward (upper) and negated (lower) ─────────
    // Forward lookup on vel → upper bound (raw, before IIR)
    float upper_raw = float_lerp(X[]@gp[-0x6574], Y[]@gp[-0x65a4], vel);

    // Negated lookup on vel → lower bound (raw, before IIR)
    // Note: negated arrays are stored in descending address order, so the lookup
    // effectively sees the array as an increasing-X table when traversed from
    // gp[-0x65d4] upward, matching the standard LERP traversal logic.
    float lower_raw = float_lerp(negX[]@gp[-0x65a8..0x65d4], negY[]@gp[-0x65d8..0x6604], vel);


    // ── 6. IIR SMOOTHING ────────────────────────────────────────────────────
    // tp+0x74CA: IIR enable byte (0=bypass)
    // tp+0x741C: startup delay threshold (Q15; 32440/32768 ≈ 0.990 s)
    // tp+0x7418: alpha = 10/1024 ≈ 0.00977  (τ = 1024/10 = 102.4 ms @ 1000 Hz)
    // gp-0x354c: time accumulator (read before update)
    // gp-0x3554 / gp-0x3558: IIR state upper / lower

    float t_accum = gp[-0x354c];
    float alpha   = (float)(u16)(tp[0x7418]) / 1024.0f;  // = 10/1024

    bool bypass_iir = (tp[0x74CA] == 0)
                   || ((float)(u16)(tp[0x741C]) / 32768.0f < t_accum);
    // Bypass during startup (t_accum < ~0.990 s) or if disabled.
    // When bypassed, both bounds collapse to lower_raw (fVar8 = fVar26 path).

    float upper_smooth, lower_smooth;
    if (bypass_iir) {
        upper_smooth = lower_raw;
        lower_smooth = lower_raw;
    } else {
        // IIR update (exponential moving average):
        upper_smooth = (upper_raw - gp[-0x3554]) * alpha + gp[-0x3554];
        // Direction guard: snap to raw if vel ≤ -x_step (-3.0) or if IIR overshot target
        if (vel <= -x_step || upper_smooth < upper_raw)
            upper_smooth = upper_raw;

        lower_smooth = alpha * (lower_raw - gp[-0x3558]) + gp[-0x3558];
        // Direction guard: snap to raw if vel ≥ +x_step (+3.0) or if IIR undershot target
        if (x_step <= vel || lower_raw < lower_smooth)
            lower_smooth = lower_raw;
    }
    gp[-0x3554] = upper_smooth;
    gp[-0x3558] = lower_smooth;


    // ── 7. GOVERNOR LOOKUP (speed-indexed ceiling) ──────────────────────────
    // gp-0x6ac2: motor/rotor speed (u16); gate to 0 if > 13000
    // Float LERP: X@tp+0x75B8, Y@tp+0x75C4
    // gp-0x3548: first-call flag (1.0f = reset/first-valid-call; 0.0f = normal)
    // gp-0x4f64: runtime governor cal (same as integer shaper's governor; branch-1 taper is
    //   motor-electrical-rate-adaptive, NOT road-speed — corrected 2026-07-17)

    float speed = (float)(u16)(gp[-0x6ac2]);
    float gov_in = (speed > 13000.0f) ? 0.0f : speed;
    gp[-0x6d94] = gov_in;
    float governor = float_lerp(X@tp+0x75B8, Y@tp+0x75C4, gov_in);

    // Reset governor on first-call or specific timing condition:
    bool reset_gov = (gp[-0x3548] == 1.0f) || (t_accum > ~1e-5f);
    if (reset_gov) {
        governor    = 0.0f;
        gp[-0x3548] = 1.0f;   // mark reset state
    } else {
        gp[-0x3548] = 0.0f;
    }
    // Apply governor as lower floor: upper_smooth = max(upper_smooth, governor)
    upper_smooth = (upper_smooth < governor) ? governor : upper_smooth;


    // ── 8. DRIVER ASSIST DIRECTIONAL BOUNDS ─────────────────────────────────
    // gp-0x6bf0 (s16 ÷128): driver_assist.  Active only when |da| ≤ 200.0.
    // Two float LERPs on assist_mag:
    //   hi-side: X@tp+0x75A4, Y@tp+0x75AC
    //   lo-side: X@tp+0x7590, Y@tp+0x7598
    // tp+0x741A: time-enable threshold (Q15); assist bounds zero until t_accum >= threshold
    // tp+0x7156: driver-assist deadband threshold (u16 × 0.0078125 = ÷128)

    float da = (float)(s16)(gp[-0x6bf0]) * 0.0078125f;  // ÷128
    float assist_hi = float_lerp(X@tp+0x75A4, Y@tp+0x75AC, assist_mag);
    float assist_lo = float_lerp(X@tp+0x7590, Y@tp+0x7598, assist_mag);

    // Gate: zero both if |da| > 200 OR not yet enabled by timing
    bool assist_gate = (|da| <= 200.0f)
                    && (!bypass_from_timing_flag)  // involves gp-0x3548 state
                    && ((float)(u16)(tp[0x741A]) / 32768.0f >= t_accum);
    if (!assist_gate) {
        assist_hi = 0.0f;
        assist_lo = 0.0f;
    } else {
        float da_thresh = (float)(u16)(tp[0x7156]) * 0.0078125f;
        // lo-side active only when da ≤ +threshold AND da < -threshold
        assist_lo = (da <= da_thresh) ? assist_lo : 0.0f;
        if (da <= da_thresh) {
            assist_hi = 0.0f;
            assist_lo = (da < -da_thresh) ? assist_lo : 0.0f;
        }
    }


    // ── 9. POLARITY-GATED BOUND SELECTION ────────────────────────────────────
    // gp-0x6752 (s8): polarity byte (±1). Out-of-range → zero output.
    // Also: gp-0x354c is updated here with fVar35 (time accumulator write).

    float polarity = (float)(s8)(gp[-0x6752]);
    gp[-0x354c] = v_signal_current;  // update time accumulator for next call

    float bound_final;
    if (polarity == 1.0f) {
        // Positive polarity: select max(upper_smooth, assist_lo)
        bound_final = polarity * max(upper_smooth, assist_lo);
    } else if (polarity == -1.0f) {
        // Negative polarity: negate governor, select max(min_of(-gov, lower_smooth), assist_hi)
        float neg_gov = -governor;
        float lo_floor = max(neg_gov, lower_smooth);
        bound_final = polarity * max(lo_floor, assist_hi);
    } else {
        // Polarity out of range (neither +1 nor -1) → zero
        bound_final = 0.0f;
    }


    // ── 10. FAULT FLAG ACCUMULATION ──────────────────────────────────────────
    // Seven binary flags, each a power-of-2 weight, summed into fault_word.
    // Threshold pattern for most flags: |x| > 0.0048828125 = 5/1024 (1 LSB tolerance).
    // Flags test whether the integer shaper's outputs agree with what the float path computes.

    float shaper_ref = (float)(s16)(gp[-0x6af6]) / 1024.0f;  // reference for bound comparison
    float motor_ref  = (float)(s16)(gp[-0x6b00]) / 1024.0f;  // motor reference
    float foc_out    = (float)(s16)(gp[-0x6acc]) / 1024.0f;  // FOC output; gate |v|>8 → 0
    foc_out = (|foc_out| > 8.0f) ? 0.0f : foc_out;

    // Mode-gated command:
    //   tp+0x74C8 == 1 → fixed_cmd = tp+0x71D4/1024
    //   tp+0x74C8 == 2 → fixed_cmd + foc_out
    //   else           → foc_out
    float cmd_base = [mode-gated selection as above];
    float cmd = clamp(cmd_base, -12.0f, 12.0f);

    // Integrator gp[-0x6dc8]: accumulates (cmd - shaper_ref) with deadband.
    // Clamp: ±(tp+0x71DC / 1024) = ±(SM3_threshold / 1024).
    // ⚠ SHARED CAL: tp+0x71DC (0xC61DC) is the SM3 arming threshold in FUN_00042af8.
    //   Raising 0xC61DC (V20A/B) proportionally raises this integrator clamp too.
    float integ_clamp = (float)(u16)(tp[0x71DC]) / 1024.0f;
    float integ = clamp(gp[-0x6dc8] + deadband_add(cmd - shaper_ref), -integ_clamp, integ_clamp);

    // Final mux: tp+0x74C9 == 1 → use foc_out only; else use cmd path
    // Clamp final command to ±8.0 (same as integer shaper's output ceiling)
    float cmd_final = clamp((tp[0x74C9] != 1) ? cmd_from_path : foc_out, -8.0f, 8.0f);

    // Flag definitions:
    float f1 = (bound_final - shaper_ref > 0.0048828125f) ? 1.0f : 0.0f;
        // Bound vs shaper reference mismatch
    float f2 = (gov_in * polarity - motor_ref > 0.0048828125f) ? 2.0f : 0.0f;
        // Governor×polarity vs motor reference mismatch
    float f3 = (|integ - (float)(u16)(gp[-0x6b0a])/1024.0f| > 0.0048828125f) ? 4.0f : 0.0f;
        // Integrator vs reference mismatch
    float f4 = [8.0f or 0.0f based on gp[-0x6b04] range check]
        // Reference in-range check (flag 4 = 8)
    float f5 = [16.0f or 0.0f based on tp+0x71D8 + cmd threshold]
        // Command vs secondary threshold (flag 5 = 16)
    float f6 = (|cmd_final - gp[-0x6b98]/1024.0f| > 0.0048828125f) ? 32.0f : 0.0f;
        // Shaper output vs expected command mismatch
    float f7 = ((v_signal - decay_ref) > 0.00015258789f) ? 64.0f : 0.0f;
        // Time-signal decay check (threshold = 5/32768)
        // decay_ref = gp[-0x6b0a]/1024 × tp+0x71DA/32768

    float fault_word = f1 + f2 + f3 + f4 + f5 + f6 + f7;


    // ── 11. FAULT STATE MACHINE ───────────────────────────────────────────────
    // gp-0x3540: state byte (0=init, 1=idle, 2=accumulating, 3=persistent)
    // gp-0x3550: timer float (seconds; increments at +0.001/call = 1 ms → proves 1000 Hz)
    // tp+0x74A4: enable gate byte (0=SM enabled; 1=hold in state 1)

    byte sm_state = gp[-0x3540];
    float sm_timer = gp[-0x3550];

    switch (sm_state) {
        case 0:     // Init/reset (also: invalid state default)
        default:
            gp[-0x3550] = 0.0f;
            gp[-0x3540] = 1;
            fault_word  = 0.0f;
            break;

        case 1:     // Idle — waiting for persistent fault + enable
            if (tp[0x74A4] == 0 && fault_word > 0.0f) {
                gp[-0x3540] = 2;                        // transition to accumulating
                gp[-0x3550] = sm_timer + 0.001f;        // ← 1 ms increment (1000 Hz proof)
            } else {
                fault_word = (sm_timer > 0.0f) ? fault_word : 0.0f;
                if (sm_timer < 1.0f) {
                    gp[-0x3540] = 1;
                    fault_word  = 0.0f;
                    gp[-0x3550] = sm_timer - 0.0005f;   // decay timer
                }
            }
            break;

        case 2:     // Accumulating — dwell timer counts up
            if (fault_word > 0.0f) {
                if (sm_timer >= 0.01f) {                // ~10 ms dwell → persistent
                    gp[-0x3540] = 3;
                    fault_word += 1024.0f;              // persistent-fault marker
                } else {
                    gp[-0x3550] = sm_timer + 0.001f;
                }
            } else {
                gp[-0x3540] = 1;                        // fault cleared — back to idle
                fault_word  = 0.0f;
                gp[-0x3550] = sm_timer - 0.0005f;
            }
            break;

        case 3:     // Persistent — hold + mark indefinitely
            fault_word += 1024.0f;
            break;
    }


    // ── 12. OUTPUTS ──────────────────────────────────────────────────────────
    *(s16*)(gp[-0x6906]) = (s16)(int)fault_word;   // PRIMARY OUTPUT (fault word, report-only)

    // Debug buffer stores:
    gp[-0x6db4] = vel;                   // clamped velocity (overwritten here)
    gp[-0x6c84] = decay_ref;             // float(gp[-0x6b0a]) × tp[0x71DA]/32768
    gp[-0x6db0] = lower_smooth;          // IIR lower bound
    gp[-0x6dbc] = cmd_final;             // final clamped command
    gp[-0x6dc0] = integ;                 // integrator value
    gp[-0x6db8] = gov_in * polarity;     // signed governor input

    // Fault reporter: if fault_word ≥ 128.0 → log fault code 0x3f1b
    if (fault_word >= 128.0f)
        FUN_000462e6(0x3f1b, fault_word, 0, upper_32_bits_of_cmd, 0);

    // Timer state update (bVar2 path, tp+0x741E threshold):
    if ((float)(u16)(tp[0x741E]) / 32768.0f + 1e-5f < t_accum) {
        gp[-0x3544] = (t_accum < lower_raw) ? t_accum : (lower_raw + 0.001001f);
    } else {
        gp[-0x3544] = 0.0f;
    }

    // ── 13. TIME ACCUMULATOR UPDATE ──────────────────────────────────────────
    // v_signal = (float)(u16)(gp[-0x6966]) / 32768.0  (read earlier)
    // decay_ref = v_signal × ... (computed in fault accumulation above)
    // Written to gp[-0x354c] BEFORE the above; the value from this call becomes
    // t_accum in the NEXT call.
    // (Note: gp[-0x354c] is actually written earlier in the polarity section —
    //  see raw decompile.  The timer accumulates v_signal - decay_ref.)


    // ── 14. TASK SCHEDULER TICK CHECK ────────────────────────────────────────
    // Validates this function's execution tick against the scheduler's expected tick.
    // Calls watchdog handler FUN_0001cba6() on mismatch (if slot enable byte == 1).
    int task_ptr = *(int*)(gp[-0x257c]);
    u32 idx = min((byte)(task_ptr[0x14]), 7);   // slot index, cap at 7
    char actual_tick = (*(char*)(gp[-16000 + idx]))++;
    if ((actual_tick + 1 != sched_tick_expected) && (gp[-0x3e78 + idx] == 1))
        FUN_0001cba6();

    // Persist integrator for next cycle
    gp[-0x6dc8] = integ;
    return;
}
```

---

## Key observations for modding

### 1. Shared cal `tp+0x71DC` (0xC61DC)
This cal is **used by both `FUN_00042af8` (integer shaper)** as the SM3 arming threshold
**and by `FUN_00043e44`** as the integrator clamp ceiling. Raising it (V20A/B) proportionally
scales both. This is expected — the float monitor's integrator tracks the same quantity the
integer SM3 guards, so they should share the ceiling.

### 2. No torque-path write
The function reads `gp-0x6b98` (shaper output) but only reads it — it never writes it.
The only write that could be confused for a torque path is `gp-0x6906` (fault word), which
is the monitor output.

### 3. Float LERP tables are distinct from integer tables
The integer path uses cal tables at:
- LERP1: `tp+0x7770` (0xC6770)
- LERP2: `tp+0x79E8` (0xC69E8)
- LERP3 X/Y: runtime RAM (`gp-0x642e`, `gp-0x6444`)

The float path uses cal tables at:
- LERP_A: `tp+0x75D4`/`tp+0x75F0` (0xC65D4/0xC65F0)
- LERP_B: `tp+0x7648`/`tp+0x7664` (0xC6648/0xC6664)
- Governor: `tp+0x75B8`/`tp+0x75C4` (0xC65B8/0xC65C4)
- Driver-assist hi/lo: `tp+0x75A4`/`tp+0x75AC` / `tp+0x7590`/`tp+0x7598`

These are entirely separate float-native calibration tables. They cannot be cross-referenced
with the integer path tables (different addresses, different scale).

### 4. V21 patch scope
V21's `shl 0x8 → 0x9` patches in `FUN_00042af8` affect only the integer shaper's IIR
outputs (`gp-0x3574`, `gp-0x3578`). This function is unaffected. It continues to compute
the unmodified envelope as the reference. That is correct — the monitor should reflect
stock design intent.

### 5. gp-0x6b4a identity
The secondary velocity signal at `gp-0x6b4a` is gated by `tp+0x74CB` and combined with
`gp-0x4f60` when enabled. The identity of `gp-0x6b4a` is not yet verified (OPEN).
It is possible this is a second velocity channel (e.g., motor electrical velocity) or
a filtered version of `gp-0x4f60`.

---

## Open questions

1. **gp-0x6b4a identity** — secondary velocity input combined when `tp+0x74CB == 1`. Trace
   the writer.
2. **Exact flag 4 and flag 5 semantics** — the `gp-0x6b04` range check and `tp+0x71D8`
   offset comparison need disassembly-level verification.
3. **gp-0x6906 consumers** — the fault word is written; who reads it? The integer shaper
   has the `gp-0x3564` leaky integrator that feeds fault 0x3f1b. Does `gp-0x6906` feed
   into `gp-0x3564` directly, or is it read by a separate logging path?

---

## Cross-references

- `notes/SESSION-2026-05-30-EME-RESOLUTION.md` — §"2026-05-31" has the initial unconfirmed findings
  that this decompile confirms
- `reference/firmware/reference_accord_override_snap_state_machines.md` — confirms REPORT-ONLY status
- `reference/firmware/reference_accord_lerp3_gp3574_chain.md` — integer path LERP1/2/3 chain for comparison
- `reference/fw_inventory/cluster3_shaper_foc.md` — inventory context for this function
- `_decomp_43e44.txt` — raw Ghidra decompile output
