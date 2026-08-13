---
name: accord-observer-residual-two-arms-v89-v97
description: "iVar6 = gp-0x6bfe (MODEL) + gp-0x6bfa (REQUEST) - (gp-0x374c>>4) (ACTUAL), coefficients EXACTLY +-1, both arms scaled by the same cal 0xC6468=2639. V89's K1 and V97's pole act on OPPOSITE ARMS of one observer residual and NEITHER arm's share has ever been measured — one unmeasured quantity explains both nulls. A '<=9% share' bound was computed and is RETRACTED: bounding one arm against the other's admitted range is invalid for a difference of correlated estimates."
metadata:
  type: reference
---

# ★★★★★ ONE OBSERVER RESIDUAL, TWO ARMS — AND WE HAVE ONLY EVER MOVED ONE AT A TIME

`FUN_00038148` @`0x38236-0x3823A`. Coefficients **exactly ±1**, verified from raw bytes:
`0x38238 subr r15,r6` (opcode `0x0C`) · `0x3823A add r9,r6` (opcode `0x0E`) · `0x38236 sar 0x4,r6`.

```
FUN_0003b8f6 — the 1 kHz PLANT MODEL / disturbance observer
   K0 0xC4080=0 (NEVER RAISE) · K1 0xC40D2=204 (V89, ON THE CAR) · relay 0xC40BC=600
   0xC40D0=408 · 0xC40D4=573 · 0xC40D6=246 · 0xC40D8=3686  ← four VIRGIN poles, SAME CLASS as 0xC63AC
      │ gp-0x6bfc → FUN_0003bc20 (plausibility ±20000, else force 0x7FFF)
      │ gp-0x6bfe ──── MODEL   ────┐  UNFILTERED   ◄── V89's K1 acts HERE
LKAS 11-slot aggregator FUN_00026c80 │
      │ gp-0x6bfa ──── REQUEST ────┤  UNFILTERED   (its ±20000 gate is DEAD — the writer pre-clamps)
six lanes → ×sign(gp-0x6752) → ×2639 (0xC6468) → <<4
      │ IIR pole 0xC63AC 102→150 = ALL OF V97
      │ (gp-0x374c>>4) ─ ACTUAL ───┘  MEASURED < 2048 on 100 % of route 80
                     iVar6 → gp-0x6b70 = sign × LERP(|iVar6|), clamp ±8192 = the PID REFERENCE
```

🛑 **BOTH ARMS ARE ESTIMATES OF THE SAME QUANTITY** — same units, same cal `0xC6468`=2639, entering a
**difference**. Branch A is built from the final motor command `gp-0x6b98` through a float two-stage
IIR; branch B from the six assist lanes through the `0xC63AC` pole.

⇒ **V89's K1 measured FLAT (0.947, inside placebo). V97's pole: the operator felt nothing. ONE
unmeasured quantity explains both — the arms may be wildly unequal, so whichever you move, the residual
barely notices.** [BELIEF, but the first account explaining two nulls with one mechanism.]

## 🛑🛑 THE "≤ 9 % SHARE" BOUND IS RETRACTED — DO NOT REUSE IT
Bounding the ACTUAL arm's measured ceiling (2048) against the MODEL arm's **admitted range** (±20000)
is **invalid**: a difference of two *correlated* estimates is smaller than either, so **the denominator
is the residual, not the range.** This is **NOT** the `0xC63A4` shape (a lane summed *alongside* others,
genuinely diluted) — here the coefficient is **exactly −1 into a difference**, so **one count of
Path-2 movement is one count of residual movement.**
⇒ **Path-2's share is UNRESOLVED, not small.**

## The measured bound on the residual itself [EVIDENCE]
Stage-2 LERP inverted (mode 26, creep; `0xC63AE`=1024 ⇒ index is `|iVar6|` **raw**):
`|gp-0x6b70|` p50 320 → `|iVar6|` **126–136** · p90 2,534 → **2,965–3,675** · max 3,187 → **5,681–6,891**.
⇒ **`|iVar6| ≤ ~6,900` at creep and ~130 half the time** — 2.9× tighter than the ±20,000 clamp.
⊕ **Median 130 against a six-lane term admitted to 2048 hints at strong CANCELLATION between the three
terms** — exactly what an observer residual should do. [live hypothesis, testable by the same instrument]

⚠ **Does not travel above 50 km/h** — `0xC669A`/`0xC66A8` truncate the LERP's X axis to 7,000 there.
⚠ **`mode 24 ≠ mode 26` in THIS family** — `[[accord-stock-mode24-equals-mode26-damper-is-ours]]` is
scoped to the **damper** families and does **not** generalise here.

## The rescale is the IDENTITY [EVIDENCE — and it kills a standing blocker]
🛑 *"`f′` swings ≥10× and cannot be pinned statically"* is **WRONG — the swing is 1.000×.**
`gp-0x6982`/`gp-0x6984` have **ZERO writers image-wide** (Ghidra + raw disp16 + raw disp23 + exhaustive
32-bit-literal search, **with a working positive control**: neighbours `gp-0x6980/86/88/8A` all DO have
`st.h` writers and the scan found them) and both boot to **1024** from `.data` (flash `0x8672E`/`0x8672C`).
The `[204,2048]` rails guard a value that never moves. **The original claim came from reading cal bounds
as a live range without checking whether the inputs move.**
🛑 And `STATE.md` §A6b's *"the transfer cannot be read from the image"* is **FALSE**.

Related: `[[accord-v97-flew-lever-live-null-was-ours]]` ·
`[[accord-probe-design-law-compare-dont-quantise]]` · `[[accord-friction-polarity-more-assist]]`
