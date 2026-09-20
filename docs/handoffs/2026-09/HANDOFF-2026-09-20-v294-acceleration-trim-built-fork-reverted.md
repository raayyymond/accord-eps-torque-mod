# HANDOFF 2026-09-20 — V294 built: an acceleration trim on the V293 torque map; the fork reverted

**Nothing flashed, no CAN sent.** V293 stays on the car. V294 is built, adversarially passed, and waiting for
the operator's decision. The fork is reverted on `Dom 54ff1ea39`. Two subagents were used in the whole
session (the operator's cap), both for the adversarial pass; Ghidra failed to connect, so every byte claim
came from Python reads and independent decoders.

## The operator's call, and what was built to it

> *"the delay kills the idea of a torque mode only control … a PID + feedforward which track acceleration,
> not rate/velocity … revert all torque mode changes in this next StarPilot update … anticipate grinding and
> stuttering (relying on feedforward/torque mode as much as possible)."*

**V294** keeps V293's torque map byte for byte and adds ONE term at 1 kHz through the stock PID's own P gain:

    r26 = clamp(s_new − s_old, ±1024)     0x28FA4 add→subr: the per-tick change of the lag-filtered wheel
                                           rate = the wheel's acceleration through a 2.0 Hz low-pass
    E   = 4·sp − r26                       0x29D76 shl 5→2
    P   = (E·960)>>8 = 15·sp − 3.75·r26   Kp 120→960 on all 28 records: (sp<<2)·960 ≡ (sp<<5)·120

| cell | V293 | V294 |
|---|---|---|
| `0x28FA4` code | `add r9,r26` c9d1 | `subr r9,r26` 89d1 |
| `0x29D76` code | `shl 0x5,r16` c582 | `shl 0x2,r16` c282 |
| `0xC62E6` fb clamp | 0 | 1024 (trim ≤ 25 % of the rail) |
| `0xC63E8` pole a | 923 (16.5 Hz) | 1011 (2.03 Hz) |
| `0xC63EA` gain b | 1560 | 567 (K_α/J = 1.0 at the BELIEF scale) |
| `0xCB994` Kp ×28 | 120 | 960 |

Kd 0, D clamp 0, Ki 0, r24 2048, map, 427 tap, 0x14A cave: unchanged. 314 diff bytes over 7 CRC blocks,
two code bytes differ in value. Image `3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85`,
rwd `a2b418f061160f66ffaa8ac541a478d43771fcbd004a92dc3d7a071cfd9f706a`, exactly one of each on disk in
`accord-firmwares`. Script `analysis-2020accord/builds/v108_plus/build_v294_tva.py` — 159 assertions,
zero-edit control reproduces V293 bit for bit, 20/20 mutations caught. Design
`analysis-2020accord/studies/v294/v294_design.py`.

## Why acceleration, and why a 2 Hz pole

With T = −K·H(s)·α and H a LAG, the equation of motion gives J_eff = J + K·Re H and b_eff = b − K·ω·Im H. A
lag has Im H < 0, so every degree of loop lag turns the trim into DAMPING. Delayed RATE feedback does the
opposite past 90° of lag — the 20 Hz crossover resonance V282 ground on. The operand `s_new − s_old` is
exactly α/(s + ω_p)·(b/1024): acceleration through a first-order low-pass at the lag pole.

The pole is the design's one free parameter (one cal cell). Sweep at K_α/J = 1, ζ of the wheel mode by
speed, light-damping world (fork plant, BELIEF):

| pole | ζ× @5 · 8 · 12.5 · 19 · 26 m/s | 20 Hz gain vs the loop V282 was marginal on |
|---|---|---|
| 16.5 Hz (stock) | 0.81 · 0.86 · 0.98 · 1.13 · 1.28 | −10 dB — inertia dominates below 5 Hz, worse at low speed |
| 8 Hz | 0.84 · 0.91 · 1.06 · 1.25 · 1.45 | −15 dB |
| **2.0 Hz (shipped)** | **1.02 · 1.16 · 1.49 · 1.82 · 2.05** | **−27 dB** |
| 1.4 Hz | 1.13 · 1.30 · 1.62 · 1.84 · 1.93 | −30 dB |

Adversary A's correction, adopted: at 2–3 Hz the trim is ~97 % damping / 26 % inertia (the pole's 40° lead
plus the output lag's 25° leave it 15° from pure rate feedback); pure inertia only below ~1 Hz. Through the
whole chain it delivers **1.85 T counts per deg/s of 2 Hz-band wheel rate** (0.0007 torque/(deg/s), a damper
comparable to the wheel's own light-world 0.0006). The 25 % cap binds only above ~230 deg/s of wheel rate
(measured peak 42–56; r71's limit cycle 88) — a backstop, not the operating authority.

## Adversarial pass — two Opus agents, disjoint surfaces, FAIL criteria written first: BOTH PASS

- **A — arithmetic, sign, scale.** Both opcodes decode as claimed, lengths 2 → 2, following instructions
  identical. Sign negative by four legs (the polarity flag cancels; register assignment; integer mirror;
  delivered torque at idx 10: 213 / −165 on V282 at fb 0 / +2434, 102 / −513 / 718 on V294 at 0 / +C / −C).
  The FF product identity holds for EVERY 32-bit sp (mod 2³²). Surface at r26 = 0 equals V293's at all 241
  indices under every taper / polarity / ramp. int32 margin 4.06×. The 20 Hz ratio re-derived −26.7 dB. All
  three cal cells are FLASH (tp-relative) so no register-indirect write reaches them. `gp-0x6a34` (|fb>>5|)
  becomes 0..32 (V293 0, V282 0..1440); its readers are the unreachable damper mode and the dead twin.
- **B — build audit, interlocks.** Independent rebuild reproduces the hash; the .rwd decodes to the image;
  every changed cell private (3/1/1 accessors, zero writers, base and built sets identical); the 0x14A cave
  reads the delivered torque and four non-PID cells, NOT the published P/I/D cells (zero readers image-wide;
  S read once in the orphan island — verified by the orchestrator); the fb state has one load and one store,
  both in the filter, no reset block touches it; no governor/EME function reads any changed or rescaled cell;
  V293's D1 conclusion (lane cap 3072 cannot drive soft-EME wind-up) survives. The difference operand is
  zero at every steady rate across a disengage/re-engage; the sum operand at this clamp would have railed
  permanently above 1.47 deg/s — the operand change is what makes C = 1024 safe.
- **The one new behaviour, stated for the page:** up to 616 counts of lane torque at ZERO command while
  engaged, opposing wheel acceleration (V293: 0; V282 flew 2463). If the base assist were within 616 counts
  of the 5120 EME floor and the wheel ramped hard for 75 ms, V294 enters the 5120–5325 band V293 could not.
  Bounded, 0.25× V282's flown exposure. After a filter BAIL the first tick's operand equals the fresh state
  (22–1023 counts, one tick, then the 5 Hz lag).
- **Defects (reports, none flash-blocking), and what was done:** (1) 961 on a non-live Kp knot passed with
  zero assertions → a full 28-record Y census after `mutate()` added; (2) substantive count 41 by B's
  entailment census vs the script's 66 → recorded, labels not churned; (3) the shl's destination register
  was never read back → both instructions' register fields now asserted from the built image; (4)
  `decode_one` mis-decodes the 6-byte `mov imm32` as a 4-byte `movea` → neither V294 decode window contains
  one; recorded for the next build; (5) the trace's 30th `gp-0x6a56` access at `0x14B1E` is `jarl
  0x5E0C8,lp` (the `ld.bu`/`jarl` collision) → erratum added, count is 29; (6) b was bounded, not pinned →
  (a, b) must now be a documented ladder rung. The four missed mutations are in the test: 20/20 caught,
  same image hash.

## The instrument, and the sentence a null licenses

The CAN-427 tap and the 0x18F wheel rate, both untouched. Because the FF is byte-exact V293's,
`residual = T_tap − FF_V293(idx)·taper` IS the trim on every engaged ramped frame. Regress it over the drive
on −(0x18F rate through a 2 Hz low-pass, differenced) — a regression, not a per-frame read (~18 counts at
10 deg/s against a 22-count residual; the slope over 10⁴+ frames is hundreds of sigma):
- slope ≈ +1.85 T counts per deg/s and the FF identity R² ≥ 0.98 on low-acceleration frames → **live, right sign**;
- flat → **not live** (the subr did not take, or r26 is clamped to zero); nothing else is licensed;
- **positive correlation → SIGN INVERTED: stop, revert to V293**; the clamp bounds the damage, it does not make it acceptable;
- identity broken → trust nothing else from the drive;
- outcome, the operator's to score: hard-turn jerk and the 1.6–3 Hz wheel-rate energy vs r75/r76, predicted
  down; any new line in 5–30 Hz is the revert signature.

## The fork: reverted, nothing deleted (`Dom 54ff1ea39`)

Every V293 torque-mode term now defaults to its stock value in `params_keys.h`, `starpilot_variables.py`
and the controller's `getattr` fallbacks (HoldMap, FrictionHyst, RateLoopGain, ErrorNotchQ, RefFilter,
TorqueKiHigh, DobHz, HoldLevel, FrictionHystBand); `AccordRatePlantFF` defaults off (its model is a rate
servo or a bare torque map; V294 is neither, so the generic torque-controller FF runs); one new toggle
`AccordJerkLpHz` (default 1.2 = the generic path; 4.0 = rev 6's measured value) gates the one
torque-mode-era edit that had no switch. Layout entry, safe-mode key and the layout test's pinned defaults
updated. **Tests:** py_compile and the JSON parse pass locally; the pytest suite needs the device
environment (`openpilot.common` is not importable here) — run it on the comma before deploying, as the
previous revs did. Configs in `analysis-2020accord/reference/`: `toggle-config_V294_accel-trim_r1.json`
(SteerKP 0.9, AccordTorqueKi 0.3, SteerLatAccel 14.0, SteerFriction 0.011, AccordRatePlantFF false, every
torque-mode term at stock, lane centering on) and `…_REVERT_to_V293_r64.json` (rev 6.4 as flown +
AccordJerkLpHz 4.0). Codec positive control 20/20 pairs; adversary B confirmed every key exists in the fork.

**Honest note on the fork values.** SteerKP 0.9 / Ki 0.3 are what the three "good" V282 routes flew; LAF
14 and friction 0.011 are the torque map's own measured values (rev 2), not V282's 6.0 / 0.01 which were
fitted THROUGH the rate servo. This is a starting point for a torque-map plant with EPS damping, the same
class as any stock torque-EPS car in openpilot; it has not flown.

## What this session did NOT do
- Did not resolve the 8 x-counts-per-deg/s scale (BELIEF; K_α/J is 0.5 / 1.0 / 2.0 at 4 / 8 / 16). The
  producer chain is `x = pol·((raw·48·[0xC613A = 1159]) >> 15)`; the raw sensor's unit needs Ghidra.
- Did not simulate the reverted fork's closed loop on the V294 plant. The EPS edit is attributable from the
  wire regardless; the feel is the operator's.
- Did not run the fork's pytest suite (environment).
- Did not model the plant's 20 Hz mode explicitly; the 20 Hz margin is stated relative to V282's flown,
  marginal loop in firmware units (scale-free).

## Non-stock delta on the CANDIDATE (V294), cumulative, read from the image
V282's cumulative delta (`docs/review/V282-CUMULATIVE-NONSTOCK-DELTA-2026-09-09.md`) + V293's five cells
(fb clamp, Kd bank, D clamp, Kp bank, r24 arm) + V294's six above. On V294 the fb clamp is 1024 (stock 7680,
V282 46080, V293 0); the Kp bank is 960 flat (stock 248/512/645/696/696 on slot 7, V293 120); the fb-lag
pole/gain 1011/567 (stock 923/1560); and two code halfwords at 0x28FA4 / 0x29D76 differ from every image
before it.

## Files
`build_v294_tva.py` · `studies/v294/{v294_design.py, make_v294_config.py, fork_revert_patch.py, out/}` ·
golden model `eps_chain_core.py` (fb_op, e_shift), `eps_chain_control.py` (lkas_fb_lag, lkas_rate_pid_tick,
`_self_check_v294`), `eps_chain_delivery.py` (94 symbols, hash `740f4bcd…` unchanged) · memory
`memory/accord/builds/accord-v294-acceleration-trim-on-the-v293-torque-map-built.md` · lineage PART6 entry +
stub · trace erratum in `TRACE-2026-09-13-fb-lag-filter-bytes.md` · the artifact page https://claude.ai/artifact/BcuAb3dgHP84oasqeadVBs.
