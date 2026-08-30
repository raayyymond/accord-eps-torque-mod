# HANDOFF 2026-08-30 — the calibration search closes in every direction, and five of my own claims were withdrawn

**Flight candidate unchanged: V222.** Nothing this session moved a byte of it. What changed is that
the search space around it is now closed, the build is audited against all three of the operator's
asks, and several things the record asserted — including several *I* asserted earlier the same day —
are corrected.

> 🛑 **Read this section first if you read nothing else.** The single most useful output of this
> session is not a new lever. It is that **there are no more cal-level levers to find**, and the
> binding constraint is a drive. Every attempt to find one is documented below *with the reason it
> failed*, so nobody spends another session re-finding the same dead ends.

---

## 1. The flight candidate

| | |
|---|---|
| **file** | `39990-TVA,A160-V222-V221BASE-FRICTION.LANE.SATURATION.TO.CAR-0x13000-0x100000.rwd` |
| **rwd sha256** | `0766d45cbad4bde1…` |
| **image sha256** | `0e83c7074699d6ab…` |
| **delta from the car (V122)** | 23 payload bytes |
| **card** | `docs/scoring/DRIVE-CARD-V222.md` |
| **ladder** | V223 (Lever B rung 2) · V224 (ratchet) · V225 (authority) · V226 (grind) · V227 ⚠ see §4 |

🛑 **The flash decision is the operator's.** He must name the file and the bus, and it must be repeated
back before anything happens. Nothing in this session changes that.

**Verified this session from disk, not from the record:** 32/32 builders reproduce bit-for-bit;
exactly one flashable `.rwd` per build number (all 9 multi-file build numbers carry a correct
`SUPERSEDED-`/`DO-NOT-FLASH-` prefix; V31P and V31P-V2 are genuinely different builds); 1107 close-out
assertions pass.

---

## 2. The pre-flight audit — all three asks

| ask | finding | verdict |
|---|---|---|
| **Grinding** | notch cuts 15–22 Hz **3.6×**; reaches the 9–12 Hz `Re(Z)` peak by only 4.5 %, but Lever B covers that band **1.35× more strongly** than the ratchet | aimed acceptably |
| **LKAS authority** | the 8× step scales its clamp **exactly** — margin **1.2260×** against the car's **1.2263×** | passes |
| **Peak command oscillation** | dose is **fully linear in the micro regime**; V222 delivers **100.0 %**, V223 **98.6 %** | passes |

⭐ **The third one closed better than expected: Lever B can never clip the micro regime at ANY value in
its uint16 range.** At cal max the saturation onset (128 ct) still sits **7.8× above the pooled median
`|dT|` of 16.5 ct** (n = 455,183 engaged frames, 6 routes). Delivery degrades only to **82.6 %** at the
extreme, so the **whole ladder is usable** — what clips is large excursions, not roughness.

🛑 **Authority has a near ceiling.** The clamp is a byte<<8 that must sit strictly between `lane_max`
and the EME wall, so at **11×** only bytes 18–19 fit and at **12× no valid clamp exists at all**. One
~10 % step remains beyond V225, not an open runway.

---

## 3. What is now CLOSED, and why

Each of these is a lever someone will otherwise re-propose.

| region | closure |
|---|---|
| **aggregator lanes** | census complete at 7.79 Hz; **only r24 has ever been shown to help** |
| **the governor** | ramp is **3.5–8.7 ms** at the confirmed 1 kHz against a **128 ms** ratchet cycle ⇒ cannot build it. And `0xC6206`/`0xC6208` caused **EPS lamp + no power steering at ignition** at `0xFFFF`; leave them |
| **the notch** | V222 is the **constrained optimum of its only second-order section** (109,446 configs searched) |
| **a second notch** | **there is exactly one biquad** in the whole cal region ⇒ the 55 Hz vs 20.5 Hz trade is structural |
| **the span cal `0xC6C42`** | 91 % magnitude / 9 % phase — Lever B's job, and its optimum sits **one step from a double kill-switch** (N=8 silently zeroes r24 **and** r26) |
| **r24's phase** | structurally capped at **+149.3°**; shipped N=4 already achieves **94 %** of that ceiling |
| **delivery lag** | bounded at **3.25 ms** against a **77 ms** inversion threshold — 24× of margin, and the sign is favourable |
| **the FOC current loop** | transparent at 7.79 Hz for every plausible tuning; would need **BW = 7.8 Hz**, slower than the task feeding it |
| **creep damping** | search space already exhausted (prior session) |

⇒ **the cal-level search is complete in every direction from the aggregator.**

---

## 4. 🛑 V227 IS MEASURED INERT AT THE RATCHET — do not fly it as a ratchet rung

V227's only edit is the ceiling knee `0xC67C4`. **The ceiling does not bind there.** The lane's 6–9 Hz
output measures **47.2 counts** against a recorded ceiling of **164–341** at ratchet speeds — 3.5–7× of
headroom. The record itself listed *"a third outcome is INERT"* for V227; that outcome is now measured
rather than speculated.

⊕ The same number killed a build I was about to cut — a mirror-image lever on the same knee, inert for
the identical reason. ⊕ And the lane is only **0.25× r24** in this band, so even a lever that *did* act
there is worth about **23 %** of r24's contribution. The lever that acts regardless of the ceiling is
the lane **gain `0xC6AF0`**, not the knee.

V227 may still act at DC/low frequency through the integrator's anti-windup window. That is a
different experiment with a different readout, and it must be described that way.

---

## 5. 🛑 A SCORING TRAP FOR THE NEXT DRIVE

**Do not score 30–49 Hz across the V222/V122 boundary.**

V222 removes Honda's 55 Hz notch to place one at 20.50 Hz. Caches run at **fs ≈ 101 Hz ⇒ Nyquist
50.5**, and **52–71 Hz folds into the scored 30–49 Hz band** from above Nyquist, where it can be
neither seen nor filtered.

```
  mean |H| over 52-71 Hz    car 0.1700    V222 0.6392   ->  V222 passes 3.76x more
```

Any 30–49 Hz difference is therefore confounded by genuine content the build no longer notches, and it
**cannot be separated post hoc**. This applies to **every notch build**, not just V222. Score 6–9, 9–12
and 15–22 as planned. (A 911× ratio appears at 55.2 Hz but is an **artefact** of dividing by the car's
notch null — the honest figure is the band mean, 3.76×.)

---

## 6. ⭐ New measurement: the anti-damping is BROADBAND and peaks at 9–10 Hz

`Re(Z) = Re(S_TR/S_RR)`, 6 routes engaged, magnitude-weighted:

| band | mean Re(Z) | coherence |
|---|---|---|
| ratchet 6–9 | −23.5 | 0.532 |
| **mid 9–12** | **−67.9** | **0.618** |
| gap 12–15 | −51.3 | 0.511 |
| grind 15–22 | −14.2 | 0.631 |

Single-signed across the whole gated 7–23 Hz range ⇒ **broadband, not a narrow mode**. The extremum is
**~3× the ratchet band and ~5× the grind band**, in a band the kit **scores but has never targeted**.
⇒ **size and aim levers at 9–12 Hz, not only 6–9.** Instrument: `rlog-tools/score/rez_spectrum.py`.

⚠ Two things it had to get right, both of which changed the answer: **magnitude-weighting** (the phase
extremum is at 13 Hz, the impedance extremum at 10 — phase alone mis-aims by 3 Hz) and **coherence
gating** (torque–rate is 0.44–0.76 in band but collapses outside; command–rate never exceeds 0.23
anywhere, which is why no command-referenced delay could be fitted).

---

## 7. 🛑 FIVE THINGS WITHDRAWN — three of them mine, from earlier the same day

**Read this section before citing anything from this session.**

1. **"r24 DAMPS at 6–9 Hz" — WITHDRAWN.** Published as EVIDENCE, then failed its first external check:
   across the three bands V88 measured on-car, `corr(work, V88 ratio) = −0.803` where the prediction
   required **positive**. My controls pinned the **pipeline**, not the **physical frame**. Weak
   evidence (n=3, and V88 moved 5 bytes), so it withdraws the claim without asserting the opposite.
   **Both directions are open.** ✅ The **magnitude** correction is frame-independent and **stands**:
   **187 ct measured against 431–1294 claimed** in the record.
2. **"the record's 'net PID DAMPS' is a convention flip" — WITHDRAWN**, as a consequence of (1). The
   record may simply be right.
3. **My published V222 notch response — CORRECTED.** I reported 0.970 / 0.924 / 0.366; those came from
   a **parametric reconstruction**, not the image floats. V222's biquad is **not symmetric** (zeros
   20.50 Hz, poles 15.50 Hz; Honda's own are 12.88 Hz apart). Actual: **0.998 / 0.955 / 0.281** —
   **better than I said** on both counts.
4. **"task 5 = 100 Hz" — retracted 2026-08-12, but still live in `BUILD-LINEAGE.md`** as a ★★
   structural finding until this session. The ZOH veto it supports is **unsupported** (not refuted).
   V44/V47's nulls now rest on the FactorC speed-axis argument alone, which is independent and solid.
5. **1 kHz stands on ONE route, not two.** The OSTM0 derivation is refuted — **PCLK is 40 MHz, not
   80**, and OSTM0 is not the RTOS tick. The conclusion is unaffected (the on-car `0xC64DF` dwell never
   used that chain) but do not cite the OSTM0 route.

⊕ Also corrected mid-session: `r95` is **V101** (8×/7128, Lever B removed), **not V102** — the
correction existed in 2 of 4 files and has been propagated to all, including a cal-association scan
that was attaching gain 5346 to a 7128 route.

---

## 8. Traps recorded so they are not re-paid

- **A `*_plain_image.bin` file offset IS the address.** Rebasing by `0x13000` returns `0xFFFF` for
  every cal and an arm byte of `0x63` — data-shaped, not an error.
- **A bare `*v104*` glob matches `SUPERSEDED-DO-NOT-FLASH-…` first**, because `S` sorts before `_`.
- **`scipy.csd(x, y)` returns `arg(Y) − arg(X)`.** Pin it with a constructed +90° lead; assuming it is
  how this kit has been inverted before.
- **A span of `round(4 ms × 100 Hz) = 0`** silently becomes a 1-sample, 10 ms difference — 2.5× the
  gain and 8.4° of phase error. Compute the transfer analytically instead.
- **Band means hide pointwise peaks.** A notch candidate with a 6–9 Hz *mean* of 1.019 concealed a
  **1.265× peak at 6.0 Hz** and a Q≈33 pole on the ratchet.
- **An optimiser exploits every omitted constraint.** Three passes were needed: band-mean → +360 %
  (GATE 2 failure); pointwise ceiling → +394 % (by *cutting* the 6–9 damper to 0.528, because I removed
  the floor); ceiling *and* floor *and* no global lift → nothing beats V222.

---

## 9. OPEN ITEMS

1. **The drive.** V222 is the candidate. Everything else here is subordinate to it.
2. **The frame** (which decides absolute damping/pumping) is **not resolvable from bus data**. It needs
   a probe putting delivered assist on the wire with a known sign — a cave, i.e. this kit's only
   bricking class. It blocks nothing, because every actionable conclusion is anchored on V88 instead.
3. **The 30–49 Hz band** needs a 1 kHz cave zero-crossing counter to be interpretable at all; the fold
   source is above Nyquist. Unchanged from the prior record.
4. **`0xC6AF0`** (the resonance-PID lane gain) is the untried lever that would act regardless of the
   ceiling — worth ~23 % of r24's contribution. **Not built**; V56 went this way at ~21 Hz and was
   scored on the wrong band.
5. **Notch widening to r = 0.92** is pre-computed (`a1 −1.82475755, a2 +0.84640000, b1 −1.983432120,
   c4 +1.30628962`) if the drive shows residual 9–12 Hz. It costs 8.7 % of the 6–9 damper — **do not
   take that trade before V222 has flown.**
6. **`docs/STATE.md` was split at 138.6 KB → 66 KB**; the V204–V208 era is archived with its closures
   summarised back. ⚠ 40 of 51 archives are 1–20 KB one-topic fragments totalling 226 KB — **prefer one
   archive per era.**

---

## 10. What did NOT change

No byte of any firmware image. No CAN or UDS message was sent. No flash was performed or proposed.
The car is still on **V122**.
