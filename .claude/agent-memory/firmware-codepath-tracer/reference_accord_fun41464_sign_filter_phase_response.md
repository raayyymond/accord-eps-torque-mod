---
name: reference-accord-fun41464-sign-filter-phase-response
description: FUN_00041464 (producer of gp-0x6abe/gp-0x6ac0, the damping term's sign+magnitude source) is phase-gated to 5/16 of the host task's ticks (31.25% of master rate), NOT every tick -- this lowers the effective filter sample rate below what a naive 100Hz/1000Hz assumption gives. At the 1kHz-master hypothesis the filter still nets real damping (39.65 deg lag) but weaker than a naive estimate; at the 100Hz-master hypothesis 21Hz EXCEEDS the filter's own Nyquist (15.625Hz) -- not a simple lag, an aliasing regime where the sign relationship to true motion is not reliably damping OR anti-damping, it drifts. Also found gp-0x6ac0's producer already computes abs() before storage, contradicting a cited "half-wave gate" claim for that specific read.
metadata:
  type: reference
---

Traced 2026-07-21 for team-lead's question: can the damping term's SIGN source (`gp-0x6abe`, from
`FUN_00041464`) act in phase with a real 21Hz oscillation, given the magnitude-bandwidth finding
([[reference-accord-gp6a5e-voter-bandwidth-insufficient-for-21hz]]) already shows the GATE stays
locked at zero throughout the vibration under the current calibration.

## 1. Call rate / phase mask [VERIFIED]

Sole caller of `FUN_00041464` is `FUN_0002214a` (the arbitration/`w_steer_control_task`). Call site:
```
0x221f8: r23 = r25 & 0xD30
0x221fc: be [skip if r23==0]
0x22200: jarl FUN_00041464
```
`0xD30` = bits {4,5,8,10,11} → **runs on 5 of 16 phases (31.25%)**, not every tick — smaller fraction
than the voter's 6/16. `r25` is built at `0x2214e-0x2217c` from **the SAME shared phase counter
`gp-0x67fa`** the voter uses (`ld.bu -0x67fa,gp,r13` at `0x2214e`, then `andi 0xf`, then `1<<phase` —
byte-identical idiom to `FUN_00022ca0`'s). **Both tasks are co-scheduled off one master tick** — this
lets the two functions' relative timing be reasoned about on the same 16-phase cycle even without
knowing the master rate in Hz.

## 2. Filter structure [VERIFIED]

`0xC643C` (`tp+0x743c`) byte-read = **37**, confirming the cited α=37/128=0.2891 exactly. The update
(inside `FUN_00041464`, feeding a 32-bit persisted accumulator `gp-0x359c`):
```c
target = gp-0x4f50 * 1024                          // Q10 scale of raw motor resolver rate
new = old + ((target - old) * 37) >> 7              // plain single-pole EMA, alpha = 37/128
```
This is a **plain first-order EMA**, one stage, feeding BOTH outputs directly:
- `gp-0x6abe` (sign source) = `new >> 10` (sign-preserving)
- `gp-0x6ac0` (magnitude) = `|new| >> 10` (abs taken BEFORE storage — see §5)

No deadband, no second EMA stage, no rate limit on either output. **There IS a separate second-stage
filter cascade in the same function** (persisted states `gp-0x35a0`/`gp-0x35a4`, gains
`tp+0x50dc`/`tp+0x50da`) but it feeds a **different output pair**, `gp-0x6c2c`/`gp-0x6c2e` (consumed
elsewhere, e.g. the friction lane) — **not** `gp-0x6abe`/`gp-0x6ac0`. Confirmed this doesn't affect the
damping term's sign/magnitude source.

Gating: this whole live-compute path only runs when `gp-0x4f50 <= 12936` (asymmetric, positive-side-only
— see the corrected read of `bVar2` below); outside that, both outputs pin to `0x7fff`/`0xffff`. This
independently **resolves a standing contradiction in this kit's own memory** between
`reference_accord_fun34350_damping_term_live_and_gated.md` (claimed gp-0x6abe is LIVE in normal driving)
and the `model/eps_lkas_chain_model.py` docstring (claimed the opposite) — **the agent-memory file was right.**
`gp-0x4f50 > 12936` is a narrow, positive-only, near-the-clamp-ceiling condition; `gp-0x6abe` is live
across virtually the entire normal operating range. Flagging this resolution for whoever next edits the
model docstring.

## 3. Magnitude/phase at 21 Hz — exact z-domain computation [VERIFIED arithmetic; task rate INFERRED]

`H(z) = alpha / (1 - (1-alpha)*z^-1)`, evaluated at `z = e^{j*2*pi*21/fs}`:

| Scenario | fs (Hz) | Nyquist | \|H\| | dB | phase |
|---|---|---|---|---|---|
| master=1000Hz, phase-gated (5/16) | 312.5 | 156.25 | 0.633 | -3.97 | **-39.65 deg** |
| master=100Hz, phase-gated (5/16) | 31.25 | 15.625 | 0.196 | -14.15 | **+25.17 deg** (see caveat) |
| master=1000Hz, naive ungated | 1000 | 500 | 0.933 | -0.60 | -17.58 deg |
| master=100Hz, naive ungated | 100 | 50 | 0.269 | -11.39 | -39.91 deg |

Cycle-domain (rate-independent framing, as requested): **≈14.9 filter updates per 21Hz period** at the
1kHz/312.5Hz case, **≈1.5 updates per 21Hz period** at the 100Hz/31.25Hz case.

**Correction to your preliminary numbers**: the phase-gating I found (§1) was not in your original
estimate — it lowers the effective sample rate from a naive 1000Hz/100Hz to 312.5Hz/31.25Hz. This
worsens the 1kHz case (39.65° lag, not your ≈25°) and, more importantly, changes the CHARACTER of the
100Hz case entirely (see below) rather than just its number. My exact-z-domain values also differ
somewhat from your naive-ungated estimates (0.933/-17.6° vs your 0.91/-25° at 1000Hz; 0.269/-39.9° vs
your 0.21/-78° at 100Hz) — possibly a different filter-response approximation on your side; I'd trust
the exact z-transform numbers above over either of our earlier estimates.

**⚠ The 100Hz-master case is NOT "approaching 90° lag" — it's a fundamentally different, worse regime.**
At `fs=31.25Hz`, the filter's own Nyquist frequency is `15.625Hz`, and **21Hz exceeds it**. The `+25.17°`
figure above is the mathematically well-defined value of `H(e^{jωT})` at that `z`, but it does NOT mean
"the filter lags the true 21Hz motion by -25°." Above Nyquist, the discrete filter cannot distinguish a
true 21Hz input from its alias (`|21-31.25| = 10.25Hz`), and because 21Hz and 31.25Hz share no simple
integer ratio, **the phase relationship between the filter's zero-order-held output and the TRUE
continuous-time 21Hz motion will slowly precess through all possible values over time** — sometimes
near in-phase (damping), sometimes near quadrature (no net effect), sometimes near anti-phase (energy
injection) — rather than sitting at one fixed lag. **This is a materially more dangerous answer than "78°
lag, borderline" — it's "the phase relationship is not controlled at all."**

## 4. Coulomb vs viscous character + `gp-0x698a` [PARTIAL — one input unresolved]

The magnitude is `clamp(gp-0x698a, 0, 1024) x factor_0xC9CCC(=1024, flat/no-op, see
[[reference-accord-damping-friction-returncentre-torque-gates]]) x factor_0xC9E9C(keyed on gp-0x6a5e) x
factor_0xC9DB4(keyed on gp-0x6a10, tracking error) x factor_0xC9F84(keyed on gp-0x6ac0, same IIR chain
as the sign)`, all Q10, chained with `>>10` after each multiply.

`gp-0x698a`'s SOLE producer [VERIFIED, `search_instructions` exhaustive, 5 hits total] is `FUN_00026c80`
— the **LKAS mixer** (the same function that produces `gp-0x6b4c` and, per this session's earlier trace,
`gp-0x67ac`). It's written at `0x27384` from a lockstep-checked internal register (`gp-0x3d78`) inside
the mixer's dense per-channel weighted-sum loop. **This is a COMMAND-domain quantity, not a copy of any
established sensor signal** (not `gp-0x4f60`, not `gp-0x4f50`, not `gp-0x6a5e`) — but I did **not**
resolve exactly what `gp-0x3d78` represents or whether it carries 21Hz content; the mixer's channel-mode
dispatch logic is dense and I ran out of budget mapping it fully (same region flagged as unresolved in
`reference_accord_gp67ac_aggregator_lane_suppression_gate.md`, now confirmed by the team as a dead
branch for THAT variable — `gp-0x698a` is a different register from the same loop and its status is
separately unresolved).

What IS established: of the OTHER three magnitude factors, one (`0xC9E9C`, keyed on `gp-0x6a5e`) is
independently proven bandwidth-limited at 21Hz to single-digit-to-tens of counts
([[reference-accord-gp6a5e-voter-bandwidth-insufficient-for-21hz]]), and one (`0xC9F84`, keyed on
`gp-0x6ac0`) shares the exact same IIR chain as the sign itself (so its OWN dynamics at 21Hz mirror §3,
just in rectified/magnitude form rather than signed form). **Net read: the magnitude is a blended product
where at least half the known factors are slow relative to 21Hz; this reads structurally closer to
Coulomb (magnitude roughly steady over a cycle, sign flips with filtered direction) than to a clean
viscous term whose magnitude tracks instantaneous |velocity|** — but I cannot rule out `gp-0x698a`
dominating with fast content, since I did not close that thread. **[OPEN]**, flagged rather than guessed.

## 5. The "half-wave gate" — my evidence contradicts the claim as you summarized it [VERIFIED, high confidence]

`gp-0x6ac0`'s producer (`FUN_00041464`, this session's decompile) computes it as:
```c
uVar8 = uVar16;                    // uVar16 = the IIR-filtered rate (signed)
if ((int)uVar16 < 0) { uVar8 = -uVar16; }     // uVar8 = |uVar16|  -- ABS TAKEN HERE
...
*(short*)(gp-0x6ac0) = (short)(uVar8 >> 10);   // stored value is ALREADY non-negative
```
`gp-0x6ac0` is a **non-negative magnitude by construction at its own producer**, well under `0x8000`
given the ~13000 clamp ceiling. A value that's already guaranteed non-negative reads **identically**
whether loaded `ld.hu` or `ld.h` — there is no signed/unsigned distinction left to exploit. I re-checked
`FUN_00034350`'s gate at `0x345fa` (`ld.hu -0x6ac0[gp],r14; addi -0x32c9,r14,r0; bc ...`) against this:
it is a **pure speed-magnitude threshold** (`gp-0x6ac0 < 12999`), **symmetric in rotation direction** —
I cannot find the one-direction/half-wave effect the V43 handoff describes, for THIS specific read.

**Possible reconciliation, not confirmed**: `FUN_00041464` separately computes `gp-0x6ac2` (feeds the
damping term's CLAMP BOUND via table `0xC77A0`, not the gate) with genuinely sign-dependent logic:
`uVar19 = |filtered_rate|>>10` **only when** `sign(filtered_rate) != sign(gp-0x6b98, delivered torque)`,
**else 0**. That IS a real "half the time" zeroing — of the clamp bound, not the gate — and could be
what the V43 note was describing if it was looking at a different variable or an intermediate build. I
did not read table `0xC77A0`'s `Y[0]` this session to check whether a zero clamp-bound would itself
suppress the damping term during the "agreeing-sign" half of the cycle (a DIFFERENT path to a similar
practical effect) — flagging as the natural next check if this thread matters to the recommendation.

## Bottom line for V44

Unlike the magnitude-bandwidth finding (robust to the rate ambiguity), **this phase analysis is NOT
robust to it — the verdict flips with the unresolved host rate**:
- **If the master rate is ~1000Hz**: the sign filter's 39.65° lag is still net-damping (`cos(39.65°) ≈
  0.77` — real, moderately-attenuated damping, weaker than your initial estimate but not borderline).
  Raising `Y[0]` plausibly gives real damping when it fires.
- **If the master rate is ~100Hz**: 21Hz is past this filter's own Nyquist. The sign relationship to the
  true motion is not a fixed lag — it drifts through all phases over time. **I would not call this "the
  damper cannot act in phase" in the sense of a guaranteed 90°+/anti-damping outcome, but I also cannot
  call it safe** — it is phase-INCOHERENT, which means raising `Y[0]` would sometimes damp and sometimes
  inject energy, unpredictably, cycle to cycle. That is a genuinely different and arguably worse
  situation than a clean "always slightly anti-damping" verdict, because it can't be reasoned about or
  bounded the way a fixed-phase system can.

**Resolving the actual host task rate is now the single most decisive open question for V44's safety** —
more so than for the magnitude-bandwidth finding, which held regardless.

## Related
[[reference-accord-gp6a5e-voter-bandwidth-insufficient-for-21hz]] — the magnitude-side finding this extends
[[reference-accord-damping-friction-returncentre-torque-gates]] — the 0xC9CCC/0xC9E9C table dump this session builds on
[[reference-accord-fun34350-damping-term-live-and-gated]] — the memory this session's §2 finding VINDICATES over the golden model's docstring
