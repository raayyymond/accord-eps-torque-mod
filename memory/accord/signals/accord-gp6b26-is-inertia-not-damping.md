---
name: accord-gp6b26-is-inertia-not-damping
description: "gp-0x6c2c is a FIRST DIFFERENCE of the filtered motor rate = ACCELERATION, traced line by line in FUN_00041464. So gp-0x6b26 = -K x accel is an APPARENT-INERTIA term, not a damper. builds/v80_v107/build_v91_tva.py's 'genuinely DISSIPATIVE, it opposes motor rate' is WRONG, and the whole V74/V75/V91/V92 dose direction was aimed at the wrong physics."
metadata:
  type: reference
---

# 🛑🛑★★★★★ `gp-0x6b26` IS AN INERTIA TERM, NOT A DAMPER — the dose family's premise is wrong

Traced 2026-08-11 in `FUN_00041464` (GhidraMCP, `code.bin`), decompile-first. **This overturns the
core physics claim in `builds/v80_v107/build_v91_tva.py` and therefore the rationale of every build in the family.**

## THE TRACE [EVIDENCE] — confirmed in ASSEMBLY, because the decompile could not settle it

🛑 **THE DECOMPILE ALONE IS NOT SUFFICIENT HERE, and an earlier draft of this memory was rightly
challenged on exactly that.** Ghidra renders the reset path as `uVar8 = uVar16; uVar16 = uVar8;`,
which makes `iVar11 = uVar16 - uVar8` look **identically zero**, and it prints the EMA input as a
bare `iVar14` whose assignment from `iVar11` is easy to omit when quoting. Both are variable reuse
across paths. **The claim was re-framed from the decompile and then PINNED in assembly**
(`disassemble_bytes 0x415B8..0x41650`) — the order CLAUDE.md mandates.

```
415d4: shl  0xa, r28        ; r28 = rate << 10                       rate = gp-0x4f50 (resolver)
415da: ld.hu 0x743c,tp,r10  ; alpha = cal 0xC643C
415de: sub  r7, r28         ; r7 = OLD filtered rate, from gp-0x359c
415e0: mul  r10, r28, r0
415e6: sar  0x7, r28
415e8: add  r28, r24        ; r24 = NEW filtered = OLD + ((rate<<10 − OLD)*alpha >> 7)
415fa: cmp  r8, r7          ; r8 = 0xcb2000
415fc: ble  0x41600         ; 🛑 the NORMAL path SKIPS the next instruction
415fe: mov  r24, r7         ; RESET path ONLY (invalid state / first tick): OLD := NEW ⇒ diff = 0
41600: mov  r24, r9
41602: sub  r7, r9          ; 🛑 r9 = NEW − OLD   ==  THE FIRST DIFFERENCE
41612: shl  0x5, r9         ; ×32 …
4161a: cmovle r8, r9, r22   ; … clamped to ±0xfa0000  → r22   (this is Ghidra's `iVar14`)
4162e: mov  r22, r26        ; ⇒ THE EMA INPUT IS THE CLAMPED DIFFERENCE — the omitted link
41632: mul  r11, r26, r0    ; alpha_A = cal 0xC40DC
4163a: sar  0x6, r26
41644: st.w r26, -0x35a0,gp ; EMA-A state  → later >>9 → gp-0x6c2c   [FAST]
4164c: st.w r22, -0x35a4,gp ; EMA-B state  → later >>9 → gp-0x6c2e   [SLOW, alpha_B = cal 0xC40DA]
```

⇒ **`gp-0x6c2c` = EMA( 32 × ( filtered_rate[n] − filtered_rate[n−1] ) ) = angular ACCELERATION.**
The `gp-0x359c` round-trip is the tell: written at the end of the function, read at the top of the
next tick. `mov r24,r7` @`0x415FE` forces the difference to zero **only** on the reset path
(`r7 > 0xcb2000`, or the first tick where the state is the `0x7fffffff` sentinel) — a deliberate
guard so the first sample cannot spike. **On the live path `r7` is genuinely the previous tick's
value.**

### The one inherited link, and why it holds

If `gp-0x4f50` were motor POSITION, its difference would be a RATE and the whole conclusion inverts,
so this link is load-bearing. **Three independent corroborations, all outside this trace:**
1. `[[accord-friction-polarity-more-assist]]` (★★★★, confirmed five ways): `gp-0x6abc ← gp-0x4f50`
   **= motor rate**. This same function performs exactly that copy —
   `*(short *)(gp-0x6abc) = sVar15` on the normal path.
2. **Internal bracket:** the EMA runs on `rate << 10` and the function then writes
   `gp-0x6ac0 = |filtered| >> 10` — the `<<10 … >>10` pair recovers the ORIGINAL scale, and
   `[[reference-accord-c520c-cap-table-axis-provenance]]` independently calls `gp-0x6ac0`
   *"resolver/FOC electrical **rate**"*. A position would not survive that round trip as a rate.
3. **Range:** the validity window is `r15 ∈ [−13000, +13000]` (`addi 0x32c8` / `addi -0x6591`
   @`0x415BE`) — a bipolar bounded quantity, not a wrapping angle.

⇒ carried as **EVIDENCE**, with the caveat that it is corroborated rather than re-derived here.

## THE CONSEQUENCE — and it is the whole point

`FUN_00036c12` computes `gp-0x6b26 = −K · gp-0x6c2c` (GAIN negative on **every** path), and Path 1
adds it to the aggregator **unweighted, un-negated**. So the motor command carries `−K·α`:

```
J·α = T_driver + T_motor        with   T_motor ∋ −K·α
⇒ (J + K)·α = T_driver + …      ⇒  APPARENT INERTIA INCREASES BY K
```

🛑 **An inertia term is 90° out of phase with velocity. It stores energy; it dissipates NONE.**
⇒ **`0xCBE74` cannot add damping, and cannot fix an anti-damping problem** — see
`[[accord-rez-antidamping-replicated-three-drives]]`, where `Re(Z) < 0` from 2 to ~24 Hz.

**What raising K actually does:** heavier, more sluggish wheel; resonance `ω = √(k/(J+K))` pulled
**DOWN**, i.e. further into the 6–9 Hz band the driver's own input excites. That is the opposite of
what the operator asks for when he says *"turning angle rate still limited by this."*

## 🛑 WHAT THIS RETIRES

- **`builds/v80_v107/build_v91_tva.py`'s "The Y row is NEGATIVE … so the term is genuinely DISSIPATIVE (it opposes
  motor rate)" is WRONG.** It opposes *acceleration*. Every doc calling `0xCBE74`
  "friction/**damping**-comp" inherits the error.
- **13 builds have touched this LERP family** (V73–V77, V81, V83a, V84, V86, V90–V92) and **every one
  raised it or restored stock. Nobody has ever LOWERED it.** The untried direction is DOWN.
- ⚠ Reconciles with `[[accord-friction-polarity-more-assist]]` only in part: that memory is about the
  **observer** path into `gp-0x6ad6`; this is the **direct aggregator** path. **Two paths, two
  polarities — do not merge them.** [Path-1 sign is EVIDENCE from `build_v91`'s assertion; the net
  aggregator→motor sign is BELIEF, resting on
  `[[accord-aggregator-reaches-motor-via-gp6acc-bridge]]`.]

## ⊕ AND THE TELEMETRY COULD NOT SETTLE THIS — worth knowing why

`rlog-tools/studies/v91-v94-dose/v93_identify_6b26.py` reconstructed the signed lane from 427 magnitude + the `0x14A` b7
sign and returned **MIXED/UNRESOLVED**: gain rise 2.29× (viscous 1.0, inertial 4.7), mean phase
+137° (viscous 0°, inertial +90°), and the ±2-sample **skew sweep swings 5×** (6–9 Hz: 21 / 31 / 100
/ 76 / 68). **`gp-0x6b26` is too small (p50 4.8 ct) and sign-flips too fast for a two-message
reconstruction** — unlike `gp-0x6bbe` (p50 76.8 ct), where the same sweep moved < 1.5 %.
⇒ **A two-message signed reconstruction is only valid for a LARGE, sign-STABLE lane.** Ghidra
settled it; the telemetry could not.
