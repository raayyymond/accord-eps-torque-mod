# ADV-B (units / scale chain + the instrument) vs the BUILT V295 image — FAIL criteria

Written 2026-09-30 BEFORE any V295 number was computed by this agent. Only the image hash was re-read first
(`5c044d65…40452ed`, matches the brief). Nothing below may be edited after the computation starts; post-hoc changes
go in the report as declared amendments.

Verdict mapping: any **[DNF]** criterion firing => DO_NOT_FLASH. Any **[DEF]** firing => PASS_WITH_DEFECTS (the claim or
the protocol must be corrected before flight, the image need not change). Nothing firing => PASS.

## U — the unit / scale chain (every factor re-derived from the IMAGE bytes and the r71b wire)

- **U0 [DNF]** The built image's sha256 is not `5c044d65…`, or u16 LE at 0xC63EA != 1050, or any other PID-chain cell
  (a, C, Kp bank rec 7, Kd, D clamp, Ki, output lag, forward gain, map rec, shl imm, add/subr opcode, 0x55B48 shift)
  differs from V294's image.
- **U1 [DEF / DNF]** x scale. From the image, the 0x14A rate writer at 0x55B48 must be `(-x)>>3` with x = gp-0x6a56.
  On r71b: 0x18F raw rate vs carState.steeringRateDeg slope must be 8.00 +/- 2 %, and 0x14A rate x8 vs x_fw slope
  1.00 +/- 1 %. DEF if outside those; DNF if x were off by >= x1.5 in the direction that makes the delivered trim
  larger than every adversary bound (int32 margin < 2, restart > 288 is NOT affected by the scale — see U-note).
- **U2 [DEF]** kappa (wheel angle / rack). If my on-centre (|angle| < 20 deg) d(angle)/dt vs x/8 ratio lies outside
  [1.10, 1.22], or beyond-80-deg outside [0.93, 1.02], the inherited 1.16 / 0.965 is wrong. Either way, any page/brief
  number quoted "per deg/s (or deg/s^2) of STEERING WHEEL" that does not carry kappa is a DEF.
- **U3 [DEF]** r26 per deg/s^2 of x-rate at b 1050 must equal 8*b*Ts/(1024-a) on my own march within 2 %.
- **U4 [DEF]** T per wire count (sub-rail) must be 0.641 +/- 1 % on my own byte march of the built image; T per openpilot
  torque unit must be (T per wire) x (wire per torque unit measured on r71b) — DEF if the brief's 2605 differs from my
  value by > 1 %.
- **U5 [DEF]** K_alpha (T per deg/s^2 of x-rate, below the pole) must be 0.388-0.389 +/- 3 % on my own march.
- **U6 [DEF]** damping (in-phase opposing component, T per deg/s) at 2, 2.5 and 3 Hz: V295/V294 ratio must be
  1.852 +/- 1 %; the brief's "~3.4 T per deg/s at 2-3 Hz" must be within +/- 10 % of my value at 2.5 Hz.
- **U7 [DNF if ratio >= 3; DEF if the V282 anchor is off]** |P/x| at 20 Hz: V295 3.850 +/- 1 %, V295/V294 < 3.0.
  V282's 44.90 re-derived from the V282 IMAGE, +/- 2 %.

U-note (written first): the int32 margin and the restart-pulse cap depend on x in COUNTS (|x| <= 12000 bail) and on b,
a, C, Kp — not on the deg/s scale. A wrong x scale changes the physical claims (K_alpha, damping), not the
safety bounds. I will state which claims each factor moves.

## I — the instrument (the c1/c2 regression, implemented by me from the image cells)

- **I0 [DNF]** My byte-exact V294 LIVE march on r71b's own command/rate must reproduce the real 427 tap: rms(tap -
  quant(march)) on hands-off engaged frames <= 10 counts (attribution got 5.4). If > 10 the instrument is unreliable,
  and the flight read cannot be executed as specified.
- **I1 [DEF at > 5 %, DNF at > 20 %]** NULL (real r71b tap regressed on V294 FF + V294 TRIM): c2 median in [0.90, 1.10];
  false-"live" rate (c2 > 1.45) on 15 s and 30 s hands-off windows.
- **I2 [DEF at > 5 %, DNF at > 20 %]** POSITIVE CONTROL (real r71b residual + quant(V295 march)): c2 median in
  [1.70, 2.00]; miss rate (c2 <= 1.45) on 15 s and 30 s hands-off windows.
- **I3 [DEF at > 5 %; DNF if > 20 % on 30 s windows]** misfire rates (I1/I2) on 15 s and 30 s, hands-off AND
  all-engaged contiguous windows.
- **I4 [DEF]** Alignment: the tap sampling offset (-4 ms vs 0 ms) must not flip the c2 > 1.45 call on > 5 % of
  windows, and the c2 medians under the two alignments must differ by < 0.10.
- **I5 [DEF]** FF identity (`v293_flight_read.identity_block`, V293 cells, bar fade) on the synthetic V295 tap: state
  the expected R^2. DEF if it falls below the inherited F1 line (0.90) on the CORRECT image (the gate would misfire);
  then a new gate line is set with margin from V295's own window distribution.
- **I6 [DNF]** Sign leg: a synthetic tap with the operand INVERTED (r26 -> -r26 at b 1050) must read c2 < 0 on
  >= 95 % of 15 s windows. DNF if an inverted tap can read c2 > 1.45 on ANY 30 s window (inversion would pass as live).
- **I7 [DEF]** Secondary outcomes (1.6-3 Hz hard-turn wheel rate 5-15 m/s; 0.5-1 Hz lateral error 0-10 m/s; tracking
  gain / turn-hold): report the one-drive no-change 90 % interval from r71b block bootstraps. DEF if any page/brief
  sentence claims one drive can confirm or refute a predicted change that lies inside that interval.
- **I8 [DEF]** The quantiser: the tap is (fld & 511) x 8 with a sign bit — if my reconstruction of the tap from the
  march differs in its LSB/sign/saturation from the wire's field (e.g. |T| > 4088 unrepresentable, or a sign-bit
  mismatch), the synthetic positive control is mis-built. Check that max |T| of the V295 march on r71b stays inside the
  field's range.

## What a FAIL looks like (plain words, so the pass can say DO_NOT_FLASH)
- the image is not what the brief says (U0);
- the instrument cannot tell V295 from V294 in one short drive (I1/I2/I3 at > 20 % on 30 s windows) — the build would
  fly uninterpretable, which CLAUDE.md rule 2 calls NOT READY;
- an inverted operand can read as live (I6);
- the controller's 20 Hz gain rises by x3 or more (U7);
- my march cannot reproduce the V294 tap on r71b (I0), so no pre-registered read exists.
