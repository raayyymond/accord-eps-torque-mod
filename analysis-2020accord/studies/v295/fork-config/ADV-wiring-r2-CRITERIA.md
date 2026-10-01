# ADV "wiring+observability" on the V295 fork config r2 / r2alt: FAIL criteria (written BEFORE any computation)

Adversary subagent, 2026-09-30. Written after reading the design report and its CRITERIA file, before running any
script or reading the fork source. Nothing is sent, flashed, deployed or committed; the fork is read-only.

Target files (analysis-2020accord/reference/):
- toggle-config_V295_r2.json (+ .decoded)                                   gated r2 (claimed == r1 byte-identical)
- toggle-config_V295_r2_REVERT_to_V294_r1.json (+ .decoded)                 r1
- toggle-config_V295_r2alt_KiHigh0.8_GATE-FAIL-G4-G8.json (+ .decoded)       r1 + AccordTorqueKiHigh 0.8
- toggle-config_V295_r2alt_..._REVERT_to_V294_r1.json (+ .decoded)          r1

## A config FAILS this pass ("do not hand to the operator as written") if ANY of these holds

W1  WIRING. Any key in the file is not read by the fork at Dom 20d24ab79 on the path the car runs (Accord, generic
    torque controller, ForceTorqueController on), OR it is read only under a gate the file does not open
    (ForceAutoTuneOff / AdvancedLateralTune / torqued useParams / a "car is Accord" test / a toggle-mode gate), such
    that the value the designer quotes is NOT the value the controller uses at 100 Hz.
W2  KiHigh SEMANTICS. AccordTorqueKiHigh 0.8 does not produce Ki = interp(v, [8,18], [0.3, 0.8]) on the live path
    (wrong breakpoints, wrong base Ki, applied before/after the LSF inflation differently than the design assumes,
    clamped/rounded to another value, or ignored when 0 vs non-0 is a mode switch that changes something else).
W3  BACK-FILL / PERSISTENCE. A mechanism (stock-param sync, the route-73 class back-fill of explicit 0.0 with
    stock, torqued overwrite, a "Rebuild Params" or reset path, onroad-boot re-derivation) can replace any value in
    the file (in particular SteerFriction 0.011, SteerLatAccel 14.0, SteerKP 0.9, AccordTorqueKiHigh 0.8 or 0.0) with
    something else, and the design does not say so.
W4  RANGE. Any value in the file lies outside the fork's params-schema / toggle clamp range, or is quantised by the
    UI / schema step to a different value.
W5  CODEC. The encoded file does not decode, with the fork's own decode_parameters (source from git show
    20d24ab79:), to exactly the decoded companion; or format / version / settingsCount do not match the fork's
    importer's expectations; or any key is not a known fork param (a typo Galaxy would silently drop); or a value's
    TYPE differs from what the fork's importer writes for that key (e.g. bool vs "1", float vs str) such that the
    import writes a different value or skips it.
W6  REVERT. Either REVERT file does not restore r1 exactly (every key, every value, same key set as the flown r1),
    or r2 is not byte-identical to the flown r1 file as claimed. Also FAIL if the delta format means keys NOT in the
    file keep the r2alt value after the revert (i.e., the revert must name every key r2alt set).
W7  OBSERVABILITY OF THE ONE DISCRIMINATOR. On r71b's own logged 100 Hz data with the r2alt values substituted,
    the pre-registered Ki = di/(0.01*error) read, binned by vEgo, cannot separate the 0.3 flat schedule from the
    0.3 -> 0.8 schedule at the bins given (i.e., the unfrozen-frame count or the error magnitude at >= 15 m/s is too
    small, or di is dominated by something other than Ki*error*dt: freeze, clip, reset, a different formula),
    OR the pre-registered formula is not the fork's actual integrator update at 20d24ab79 (e.g. the (1+lsf/Kp)
    factor or a speed-dependent factor enters di, making the read Ki*(1+lsf/Kp) rather than Ki).
W8  OTHER PRE-REGISTERED READS. Kp = p/error, LAF = (p+i+d+f)/-output, and the friction plateau do not reproduce
    their stated values on r71b by the stated formula (so the read cannot confirm the config landed), or the
    initData key list stated (26 keys) does not match what initData actually carries.
W9  FIRMWARE/FORK SEPARATION. The c1/c2 OLS of the 427 tap is shown to depend on the fork command statistics
    strongly enough that a fork change (r2alt) could move c2 across the stated decision thresholds (1.45 / 0.99),
    i.e. the "identical on drive (1) and drive (2)" claim is false.
W10 ONE-DRIVE CLAIMS. Any outcome sentence in the pre-registration (null sentence, contradiction sentence, revert
    signature) that one ~120 s-per-band drive CANNOT decide given r71b's measured scatter, and the design presents
    it as decidable. (Reported, graded; a mis-stated sentence is a required change, not an automatic REFUTE.)

## Verdict mapping (pre-registered)
- REFUTED: W1, W2, W3 (unstated and live), W5 or W6 fires on the file the operator will import. The config is not
  what the report says it is.
- SURVIVES_WITH_CHANGES: only W4 (cosmetic), W7/W8 (instrument) or W9/W10 (claim wording) fire, or a W3 hazard
  exists but is already handled by the procedure, or findings in part (d).
- SURVIVES: none fires.

## Methods (two per load-bearing claim)
- Fork source: git show / git grep at 20d24ab79 only (read-only), each claim cited by file + grep string.
- Codec: fork decode_parameters (AST-extracted from git show) AND the kit codec; round-trip and cross-decode.
- Observability: r71b rlog torqueState / carState / initData, recomputed with pure Python; second method =
  closed-form expectation of the Ki-read SNR from the error distribution.
