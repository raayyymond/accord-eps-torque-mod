# ADV UNIT / SCALE on V298 -- FAIL criteria, written FIRST

Written 2026-10-01 by the unit/scale-chain adversary **before** reading the image bytes, the build
script, or the design page's numbers. Target: the BUILT image
`_v298_V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16A_plain_image.bin`
(sha256 `177abf04...2066`). Every factor is assumed WRONG until re-proven from the image bytes
(Python LE read + Ghidra decode/disassembly of the image, not of the build script's constants).

(Supersedes the truncated `FAIL-CRITERIA-unit-scale-V298.md` left by an earlier adversary run.)

## DO_NOT_FLASH -- any ONE of these, demonstrated from the image

- **U1 SIGN.** E = (sp<<2) - r26 is not a NEGATIVE-feedback angle error: sp and x = gp-0x6a00 have
  opposite sign conventions, or the delivered torque sign under P/I is such that a positive angle
  error (theta_sp > theta) drives the wheel AWAY from theta_sp. (Positive feedback on angle.)
- **U2 FRAME MISMATCH >= 1.25x.** sp<<2 and r26 are not in the same unit: e.g. r26 DC weight is not
  16 x gp-0x6a00 (a != 0, b != 8192, C != 65535, or the filter is not a 2-sample sum), or sp is not
  in 0.1 deg/LSB of the same angle as gp-0x6a00 (factor 4 from clamp(-4*raw) wrong, extra shift, wrong
  operand cell). A >= 1.25x factor between the two operands = a standing DC angle error / gain error
  under the integrator's absence -> FAIL; an integer-factor mismatch (2x, 4x) is DO_NOT_FLASH.
- **U3 SPEED KEY.** The G(v) table is keyed on a cell that is not vehicle speed, or not 64 counts per
  km/h, or the knots decode to speeds that put the HIGH-gain band at low speed (or the reverse) relative
  to the design page -- i.e. the schedule is applied in the wrong speed band by >= 1.5x in speed AND
  that moves Kp_eff by >= 1.5x at some speed. If it inverts the schedule (high gain where design wants
  low) at highway speed: DO_NOT_FLASH.
- **U4 Q-FORMAT.** G's Q-format in E' = (E*G)>>8 is not Q8 (so 256 = 1.0) -- e.g. the shift is 7 or 9,
  or G is read as a byte where a halfword is stored -- making Kp_eff/Ki_eff off by >= 2x from the page
  in any band.
- **U5 WRAP / SATURATION REACHABLE.** Any intermediate in the chain (sp<<2, r26, E, E*G, P = E'*Kp,
  I accumulate, D = (-Kd*x)>>3, x5346 lane product) overflows its storage width or sign-extends wrongly
  at a reachable input (|steer| <= 540 deg wheel, |theta_sp - theta| <= 1080 deg, |rate| <= 1000 deg/s,
  0..200 km/h) such that the DELIVERED torque sign flips. (Wrap that only saturates in the safe
  direction is a DEFECT, not a stop.)
- **U6 D-TERM SIGN / OPERAND.** The D term on gp-0x6abe is not a damping term in the angle frame --
  i.e. sign(D) = +sign(d theta/dt) relative to the P term's restoring direction (anti-damping), or the
  operand is not a rate of the same physical wheel angle.
- **U7 FREEZE THRESHOLD UNIT.** The opposing-hand freeze compares gp-0x4f68 against 300 in a unit
  where 300 is either (a) below the driver-torque noise floor so the integrator is ALWAYS frozen (goal
  failure, a DEFECT) or (b) so large (> ~5 Nm at the bar) that the integral never freezes while a driver
  fights it (DO_NOT_FLASH: integral windup against the driver).
- **U8 INTEGRAL BOUND UNIT.** The A3 integral bound's slopes/offset/knee/low-speed cap, re-derived from
  the bytes, permit the I term to reach a lane torque above the stock LKAS rail in a band the design
  page says is capped below it, or the low-speed cap is NOT applied below 6 m/s (bound unit/compare
  wrong). A bound that is LOOSER than the page by >= 2x at any speed = DO_NOT_FLASH.
- **U9 RAIL / CLAMP.** The delivered lane torque can exceed the stock rail 2461 (x5346/32768 chain,
  lane clamp 3072) -- i.e. any path bypasses the stock clamp chain -- or the fade record at 0xE54FC is
  not in the same units as the stock arm it replaces (so the override fade happens at the wrong driver
  torque by >= 2x).

## PASS_WITH_DEFECTS -- any of these, none of the above

- A design-page number (DC stiffness per deg per band, rail angle error per band, G table, Kp_eff/
  Ki_eff, knee speeds) disagrees with the image by > 10% but < the U-thresholds, or the page states a
  unit that is wrong while the image's behaviour is still safe.
- A rounding/quantisation bias (e.g. sar 5 floor on negative values) that produces an asymmetric DC
  offset > 0.1 deg in the angle frame.
- An inherited factor (1.155 rate/angle ratio, 125/128 torsion-bar, 64 counts/km/h) that the page uses
  but that the bytes do not support, without changing a safety conclusion.
- The version string not matching the build tag.

## PASS

Every link of the chain re-derived from the image bytes and agreeing with the design page within 10%,
with sign, Q-format, speed key, freeze unit, integral bound and rail all proven.

## Structural reachability of DO_NOT_FLASH

Each U-criterion is decided by a byte read plus a named instruction decode in the BUILT image; none of
them depends on a quantity the build script supplies. If the decode returns a different shift, cal,
cell or sign than claimed, the criterion fires. The verdict is therefore not structurally pinned to PASS.
