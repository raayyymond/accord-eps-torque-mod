# HANDOFF — 2026-09-02 — V279: pure feedforward, and the StarPilot multipliers derived from the car

**Predecessor:** `HANDOFF-2026-09-02-v278-the-damping-fraction.md`.
**Artifact:** https://claude.ai/code/artifact/4696407c-e0ef-4c44-b1ee-698be51df141
**Status: V279 rev 2 BUILT (`a165b1a5…`), written to `../accord-firmwares`, NOT flashed; rev 1 renamed SUPERSEDED-DO-NOT-FLASH. V278 remains built as the fallback. V277 withdrawn.**

---

## The operator's design, verbatim

> "Seems like openpilot is driving a steering angular velocity setpoint instead of a torque… how can we turn the
> PID loop mechanism in the firmware into a pure feedforward… zero out the angular velocity feedback term… zero out
> Kd so the D term is 0… linearize the entire feedforward path… keep the effective peak torque at 6x stock."

## What shipped — three cal edits and one code window, base V268

```
image  a165b1a59307ab67867fd5488c287a2271d51e322ff601d527853712ea423485   (rev 2; rev 1 dca2acbc… = sel/demand/sign(E) tap)
rwd    ea0d7dfdbbc3277141aaff0666aea9f2ebc82cafe8bdd5b64fefd19d3532985b
710/710 · CRC 50/50 · bootloader replay 49/49 · cipher fail-closed · independent rebuild reproduces
```

| cell | V268 | V279 | consequence |
|---|---|---|---|
| `0xC62E6` | 7680 | **0** | the feedback filter's output is clamped to ±0 at `0x28fa6`–`0x28fbc` → operand r26 = 0 on every path → `E = 32·setpoint` |
| Kd `0xCB7D4` → 28 records | 128/64 | **0** | D = (dE×0)>>3 = 0 |
| map `0xC9A88` → 28 records | Honda Y | **Y = 2X** | ceiling 172 → 480 |
| Kp `0xCB994` → 28 records | 248…717 | **256 flat** | `P = 32·2idx·256>>8 = 64·idx` exactly |
| `0x55DF0`–`0x55E11` | stock | signed delivered torque | `(sign(T)<<9) \| (\|T\|>>3)`, T = `gp-0x6b38` |

`P(240) = 15360` lands **exactly** on the P clamp and the sum clamp (`ble`, no off-by-one); delivered
`= 15360 × 5346 >> 15 = 2505` — 6× stock, unchanged. Linear to cmd ≈ 3886 (`idx = |cmd|/16.2`, cap 240).
`FUN_00028ea6` is byte-identical: cal-only, outside the bricking class. 759 bytes differ, all attributed.

---

## The fact that reshaped the tune

**Honda's rate loop is a bang-bang rate servo, not a torque interface with a slope.** Stock's P term rails at
|E| = 440 operand counts — ±1.8 deg/s of rate error. With the wheel still, stock delivers its full 417 at a command
of **~113 counts** (<3% of scale); at the operator's median command with the wheel moving at its p50 rate it is
railed *negative*. To openpilot's angle PID the plant has looked like an **integrator** (cmd → rate → angle).
V279 gives it torque into a spring-inertia column — a different loop *shape*, so "stock gain ÷ V279 gain" has no
finite value and the multipliers could not be scaled; they had to be derived from the cmd→angle loop.

## The StarPilot side — torque controller, verified on the operator's tree at HEAD

🛑 **THE STARPILOT RETUNE IS PART OF THIS BUILD — TORQUE CONTROLLER, verified on `openpilots/StarPilot` @ 3d4c625de by
the orchestrator (an agent had traced an older fork and reported the angle PID; retracted the same day).**
The car runs `LatControlTorque` on 60/60 logged routes. On HEAD: `latcontrol_torque.py:152-153` sets the Accord's torque
PID to kp 0.8 (last knot) / ki 0.15 flat, but `controlsd.py:443-444` overwrites `_k_p` with the `SteerKP` toggle every
frame (default KP 0.6, range 0.3–0.9) → **effective kp = SteerKP, ki = 0.15**; measured `p/error = 0.600` on the V276 log.
**`HondaLateralPidKpScale/KiScale = 0.33` is read by exactly one file, `latcontrol_pid.py` — INERT on the torque path.**
The `,` → `EPS_MODIFIED` halving is on the Accord's PID branch, discarded by `configure_torque_tune`; the torque path has no
Accord `EPS_MODIFIED` effect (only the Civic Bosch scales LAF). **What compensated the 6x was `torqued`'s live LAF**
(raw 4.5–5.2 on V276, capped at 1.3 × 1.689 = 2.196; friction cap 1.5 × 0.212 = 0.318).
V279 loop at the 3.9 Hz crossover: |L| = [kp_eff + fricSlope] × (4096/LAF) × 0.645 × |G(3.9)| × latAccel/deg(v); **friction
(a saturating linear, slope friction/0.3, LAF-independent) is 60–80% of the gain.** GM with port values: 5.4x @13 m/s,
3.6x @20, 2.8x @25, **2.1x @30** (rows ≥ 30 extrapolated from 13–15 m/s column data — a floor, not a budget).
**⇒ FIRST DRIVE: SteerFriction 0.212 → 0.08 (GM @30 → 3.6x); SteerLatAccel → 2.53 (toggle max); SteerKP stay 0.6 (ceiling
0.9, only with friction ≤ 0.08); ForceAutoTuneOff ON. No Ki lever exists. Then read `liveTorqueParameters.latAccelFactorRaw`;
if > 2.5, edit `params.toml:14`.** The feedforward is now real torque: 1 m/s² at port LAF = 1563 EPS counts = 62% of peak.
Watch for a 3–4 Hz shimmy ABOVE ~25 m/s that grows with speed and vanishes under a little steady torque: friction down
first, then LAF up. Gentle curves, hands on, below 25 m/s first.

**Process record:** the first derivation (`tune279`) traced `openpilots/raayyymond-StarPilot/StarPilot` @ e631b24 (July), reported
`LatControlPID`, and was retracted the same day on the operator's correction; the second (`tune279b`) traced the same old fork
but on the torque path (ki 0.35 there; 0.15 on HEAD); the orchestrator re-verified every gating line on `openpilots/StarPilot`
@ 3d4c625de. Memories: `accord-starpilot-torque-controller-the-033-multiplier-was-inert`,
`feedback-the-operator-runs-force-torque-controller-check-toggles-not-defaults`.

---

## The adversarial pass

| agent | surface | verdict |
|---|---|---|
| `ff279` | mechanism, from bytes | zero clamp → 0 on all three branches; `0xC62E6` has exactly 3 readers image-wide (2 raw-scan false positives adjudicated); D is a pure multiply; LERPs flat beyond domain; `gp-0x6a32` has ZERO readers; a 4th clamp `0xC61BA` (I anti-windup, moot) |
| `adv279a` | arithmetic / interlocks / packer | no blocker; P clamp is `ble` (exact at 15360); dead twin re-verified unreachable; caught its own `hw2=disp\|1` scan trap by positive control; docstring's "V278 rev 1" needed disambiguating from the final V278 image |
| `adv279c` | rev-2 window + the tapped cell | decompile matches; r9 survives abs; no branch into the window; **`gp-0x6b2c` provably zero** (zero table + dead gate); found the `gp-0x6b3c` forwarding copy |
| `adv279d` | rev-2 build script | rebuild reproduces `a165b1a5…`; 148/157 caught; **`jarl_target` ignored the link register** (a `jr` to abs would never return) — closed; base window is V112's `gp-0x6abc`, not stock's |
| `adv279b` | build script, rev 1 | rebuild reproduces; 85/99 mutations caught; **no end-state assertion on the primary edit**, Kd only read back in-loop, last-record blindness, last-knot overdose masked by the clamp; docstring's 406 vs 417 explained (P-only vs the sum clamp stock reaches via D) |

All script holes closed after the audits: end-state re-reads of all 84 records and the clamp from the **final
image and the decoded `.rwd`**, against the constants; `Kd(idx) == 0` on every slot. Image unchanged, 703/703.

**Study finding, reported not fixed:** `rlog-tools/studies/osc-2to4/dose_e_sign_by_k.py` hard-codes the command
LIMIT as 15360 "slot 7 flat"; slot 7's record (`0xCB844 → 0xE51A8`) is **16384**. Affects only near-full-command
indices (max idx 237 vs 240). The V278 damping-fraction table is unaffected in its conclusions.

---

## The instrument and the drive

The operator rejected carrying the selector (measured: 7) and the demand index (computable offline from 0xE4 and 0x18F).
CAN 427 now carries **the delivered lane torque itself**: `(sign(T)<<9) | (|T|>>3)`, T = `gp-0x6b38` — the lane's ramped,
gain-multiplied, `±0xC61B4`-clamped output, `st.h r1,-0x6b38,gp` at `0x2A23C`, stored unconditionally every tick; its only
other readers are two UDS diagnostic loads in `FUN_0004e82e`; it has never been on a broadcast frame. 8-count resolution;
2505 reads 313. The window reuses the STOCK packer's skeleton (`ld.h` / `jarl abs` / `sar 3` / clamp bounds), retargets the
load, deletes the dead `ori`/`min`/`andi`/`mul 5`, and packs the sign from a copy in r9 taken before the abs call (the abs
helper touches only r6, r10, lp).

**Reads:** `sign(T) == -sign(cmd)` on every engaged, in-taper, ramped frame proves the feedback is dead (~0.5 if not);
T vs cmd is the delivered surface (slope 2505/3886 × taper); 0x18F rate vs T is openpilot's plant model for free.
✅ **Closed (`adv279c`):** The second term added before the gain (`gp-0x6b2c`) is PROVABLY ZERO on every path: its LERP table at `tp+0x7736..0x7744` is all-zero (byte-identical to stock) AND its gate `gp-0x6809 == 1` can never be true (`gp-0x6809` has no writer in the image, kit memory 2026-07-14). So `T = -lane x 5346 >> 15`, clamped +-3072, always. The sign is one negation (`gp-0x6752` = -1).

**Census of `gp-0x6b38`, by subop-validated raw scan (Ghidra's `search_instructions` found 3 of 5):** writers `st.h r1` @`0x2A23C`
(live) and `st.h r12` @`0x2A934` (in the unreachable tail-duplicate before `FUN_0002a93a`, gain 891 = stock's cell); readers
`0x4E8D2`/`0x4E8E2` (UDS record) and **`0x2B418` → `st.h -0x6b3c` @`0x2B41C`**, a gated forwarding copy (`gp-0x6b3c = r16 ? gp-0x6b38 : 0`)
followed by clamp logic against `tp+0x71b2` — **the first byte-level link from the lane's output toward the motor path.** What
sets `r16` and where `gp-0x6b3c` goes next are the next hops. `FUN_00028ea6` is `void`: the value leaves only through this cell.
⚠ **V279 REPLACES V112's `gp-0x6abc` tap on 427** — every offline 427 decoder for the V268 family must switch to the T decode.

**Watch, in order:** a 3–4 Hz shimmy ABOVE ~25 m/s that grows with speed and vanishes under a little steady torque (friction
slope at the margin: SteerFriction down, then SteerLatAccel up) · turning in too hard on the first curves (feedforward is now
real torque; the I term unwinds it) · T == 0 with cmd ≠ 0 outside taper/ramp-closed frames (the cell is not the lane
output). Gentle curves, hands on, below 25 m/s first.

## Open
- The comma-side lever is now primary if V279 rings; the firmware fallback is V278 (K=2, 0.86).
- `0xC61BE` (the real 2505 ceiling, virgin) remains a second-stage authority lever.
- The golden model still lacks the rate loop, the taper, the two-sample sum, the selector, and now the pure-FF build.

## Safety
**Nothing was flashed. No CAN message and no UDS read was sent at any point.**
