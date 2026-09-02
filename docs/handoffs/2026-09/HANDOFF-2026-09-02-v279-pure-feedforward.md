# HANDOFF — 2026-09-02 — V279: pure feedforward, and the StarPilot multipliers derived from the car

**Predecessor:** `HANDOFF-2026-09-02-v278-the-damping-fraction.md`.
**Artifact:** https://claude.ai/code/artifact/4696407c-e0ef-4c44-b1ee-698be51df141
**Status: V279 BUILT, written to `../accord-firmwares`, NOT flashed. V278 remains built as the fallback. V277 withdrawn.**

---

## The operator's design, verbatim

> "Seems like openpilot is driving a steering angular velocity setpoint instead of a torque… how can we turn the
> PID loop mechanism in the firmware into a pure feedforward… zero out the angular velocity feedback term… zero out
> Kd so the D term is 0… linearize the entire feedforward path… keep the effective peak torque at 6x stock."

## What shipped — three cal edits and one code window, base V268

```
image  dca2acbc9f805272eafea9a8cda2a57e1ca0de0dbf37ae0d19173ddb5f7871b5
rwd    6c104b5519a5a5f463842616535bedc3afc72385dcd1abb1daba1a3817c38b25
703/703 · CRC 50/50 · bootloader replay 49/49 · cipher fail-closed · independent rebuild reproduces
```

| cell | V268 | V279 | consequence |
|---|---|---|---|
| `0xC62E6` | 7680 | **0** | the feedback filter's output is clamped to ±0 at `0x28fa6`–`0x28fbc` → operand r26 = 0 on every path → `E = 32·setpoint` |
| Kd `0xCB7D4` → 28 records | 128/64 | **0** | D = (dE×0)>>3 = 0 |
| map `0xC9A88` → 28 records | Honda Y | **Y = 2X** | ceiling 172 → 480 |
| Kp `0xCB994` → 28 records | 248…717 | **256 flat** | `P = 32·2idx·256>>8 = 64·idx` exactly |
| `0x55DF0`–`0x55E11` | stock | V278-rev-1 window | `sel \| demand>>5 \| sign(E)` |

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

## The StarPilot side — EVIDENCE from the fork's source and the V276 log

- StarPilot (`openpilots/raayyymond-StarPilot`, e631b24) runs **`LatControlPID`**, the angle PID, for the Accord —
  not the torque controller. `honda/interface.py:98–104`: `b"," in fw.fwVersion` → `EPS_MODIFIED`; `:139–142`
  halves the tune, kpV 0.6→0.3, kiV 0.18→0.09 (the "0.5 auto factor"). `starpilot_variables.py:690–691` the user
  multipliers, PID path only; `latcontrol_pid.py:116–117` scale kpV/kiV only. **kf = 0.00006 is never scaled.
  There is no friction term** — the earlier "openpilot friction relay" attribution is withdrawn.
- From route r2e (3–5 Hz band, coherence 0.97): column response **0.00056 deg per torque count at −104°** at
  3.9 Hz (hands-on windows — the conservative case); openpilot's flown cmd/angle 332–354 counts/deg (confirms 0.33);
  cmd-vs-angle phase −79° → **openpilot delay ≈ 56 ms**. Plant −104° + delay −79° = **−183°: 3.9 Hz is V279's
  phase crossover.** |L| = 1229·mult × 0.645 × 0.00056 = **0.444 × Kp-multiplier**.

| Kp multiplier | \|L\| at 3.9 Hz | gain margin |
|---|---|---|
| **0.33** | 0.147 | **16.7 dB** — recommended |
| 0.50 | 0.222 | 13.1 dB |
| 1.00 | 0.444 | 7.0 dB — ceiling |
| 2.25 | 1.0 | 0 dB — oscillates |

**⇒ Enter Kp 0.33, Ki 0.33 (0.5 acceptable). Leave kf. Do not switch to the torque controller.** The same number as
today, now derived. BELIEF on the low-frequency side: column stiffness k ≈ 85–170 counts/deg, not identifiable from
31 s of a railed limit cycle. Authority is not lost: on V112 the 0.33 throttled the *rate* asked for; on V279 it
scales torque — 5° of error gives ~1300 counts from P alone.

---

## The adversarial pass

| agent | surface | verdict |
|---|---|---|
| `ff279` | mechanism, from bytes | zero clamp → 0 on all three branches; `0xC62E6` has exactly 3 readers image-wide (2 raw-scan false positives adjudicated); D is a pure multiply; LERPs flat beyond domain; `gp-0x6a32` has ZERO readers; a 4th clamp `0xC61BA` (I anti-windup, moot) |
| `adv279a` | arithmetic / interlocks / packer | no blocker; P clamp is `ble` (exact at 15360); dead twin re-verified unreachable; caught its own `hw2=disp\|1` scan trap by positive control; docstring's "V278 rev 1" needed disambiguating from the final V278 image |
| `adv279b` | build script | rebuild reproduces; 85/99 mutations caught; **no end-state assertion on the primary edit**, Kd only read back in-loop, last-record blindness, last-knot overdose masked by the clamp; docstring's 406 vs 417 explained (P-only vs the sum clamp stock reaches via D) |

All script holes closed after the audits: end-state re-reads of all 84 records and the clamp from the **final
image and the decoded `.rwd`**, against the constants; `Kd(idx) == 0` on every slot. Image unchanged, 703/703.

**Study finding, reported not fixed:** `rlog-tools/studies/osc-2to4/dose_e_sign_by_k.py` hard-codes the command
LIMIT as 15360 "slot 7 flat"; slot 7's record (`0xCB844 → 0xE51A8`) is **16384**. Affects only near-full-command
indices (max idx 237 vs 240). The V278 damping-fraction table is unaffected in its conclusions.

---

## The instrument and the drive

CAN 427: selector bits 3:0 (**must read 7**), demand/32 bits 7:5, `sign(E)` bit 9. With feedback zeroed
`sign(E) == −sign(0xE4 cmd)` on every frame: **agreement 1.00 proves the feedback is dead**; ~0.5 means it is not
and nothing else can be trusted. 0x18F rate vs 0xE4 command then gives openpilot's plant model for free.

**Watch, in order:** a NEW slow wallow at 1–2.5 Hz (Kp → 0.2) · a return of 3.9 Hz with the tap at 1.00
(column response off by >5×: Kp → 0.15) · sluggish centering / steady offset (Ki → 0.5 first). Hands-light first
minute. V276 rang at damping fraction 0.57; V279 is 0 by construction — stability now rests on the tune.

## Open
- The comma-side lever is now primary if V279 rings; the firmware fallback is V278 (K=2, 0.86).
- `0xC61BE` (the real 2505 ceiling, virgin) remains a second-stage authority lever.
- The golden model still lacks the rate loop, the taper, the two-sample sum, the selector, and now the pure-FF build.

## Safety
**Nothing was flashed. No CAN message and no UDS read was sent at any point.**
