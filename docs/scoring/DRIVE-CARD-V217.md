# DRIVE CARD — V217   ·   ⚠ **superseded as primary by V221 — see `DRIVE-CARD-V221.md`**

V221 is this build plus two bytes (Lever B `0xC6446` 5244 → 13107). **V217 remains the fallback** and everything below still applies to it verbatim; fly it if V221 reads worse on grinding, which would mean 5244 was already at that lever’s optimum.

**Flash target:** `39990-TVA,A160-V217-V216BASE-INERTIA.LANE.WEIGHT.TO.FLOWN.V108-0x13000-0x100000.rwd`

> ⚠ The filename says **V108**; it means **V122**, your car. The tag was fixed before the reference-build error was found, and renaming a published artifact would orphan the hashes above. The bytes are correct — only the name is wrong.
**.rwd SHA256** `941d82bf2dc556551dc9615bdd01d5e5e2d4fca7d8064578b5afb4bc969dcd54`
**image SHA256** `f89ea01f405d513985ce51c47f6796e1ea77f600fab3d9f7817cd79907a1967b`

> 🛑 **Nothing here authorises a flash.** Name the file and the bus yourself and they will be read
> back to you first. Kill openpilot/pandad (`tmux kill-server`) before any flash operation.

---

## What is on it — 25 payload bytes from YOUR CAR (V122)

```
  0xC60A8/AC/B0/B4   notch 20.50 Hz            GRINDING       (18-22 Hz)
  0xC63AE            1024 -> 512               RATCHET        (~7.8 Hz)
  0xC6CD0 + clamps   6x -> 8x                  LKAS AUTHORITY (+28.9 %)
  0x55DF2            427 probe -> gp-0x6b4e    the instrument
```

🛑 **CORRECTION — the car is V122, not V108.** I used V108 as the reference for most of this session. `preflight.py` says `FLYING = "v122"` and V122 flew as route `r24`. **The damper finding is unaffected** — V108 and V122 carry an identical inertia row — but two deltas were hidden by the wrong reference:

```
  0xC40DC  accel alpha             car 8 -> V217 22   (reverted to Honda)
  0xC40BC  friction ramp knee      car saturates at 250 deg/s, V217 at 50 deg/s
           -- the MULTIPLIER matches (2.000x Honda both), so 1-13 deg/s is identical.
           -- they differ ONLY above 50 deg/s, where V217 has LESS friction => heavier
              at high steering rate. That is a feel change you may notice on fast inputs.
```

**Everything else is identical to what you already drive.** Inertia (row *and* lane weight, both
modes) and the friction lane were all found adrift and pinned back to V108 across V214–V217 — that
was the session's real finding, not the notch.

⚠ **This is the first build in this arc that does NOT cut the 6–9 Hz damper.** Every notch build from
V196 to V213 carried it at 0.500× Honda = **0.140× your car** — a larger cut, in the same direction,
than the one you aborted V94 on.

---

## The drive — ~15–30 s engaged is enough

The whole shelf is designed so one short symptomatic pass is interpretable. **If you feel
micro-ratcheting or grinding, stop.** That is a result, not a failed drive.

1. **Creep, hands-off**, ~0.5–1.5 m/s, engaged. This is where the ratchet lives (1–13 °/s).
2. **Hands-on**, same speeds — the observer lane desensitises ~6.3× when you push, so the two
   conditions read differently by design.
3. If nothing is objectionable, **one highway stretch** for the 18–22 Hz grind band.

Then:

```
python rlog-tools/score/score_drive.py <tag> V217        # NAME THE BUILD -- it is not optional
python rlog-tools/probe/decode_v204_observer_lane.py <tag> --v209
```

---

📌 **The analysis is PRE-REGISTERED**: `docs/scoring/SCORING-V217-preregistered.md`. Every threshold is fixed before the drive, including the b5 prediction of **0.168 [0.113, 0.255]** — note this is LOWER than earlier shelf builds would have predicted, because restoring the damper raises the inertia dose to 2.384×.

---

## What each outcome means — and which arm flies next

| what you report | what it means | next build |
|---|---|---|
| **Grinding gone, ratchet gone** | all three levers landed | nothing — hold V217 and drive it |
| **Grinding better, ratchet unchanged** | **the EXPECTED outcome** — see below | V218 only if you want the dose ladder closed |
| **Grinding better but still there** | notch centred right, skirt too narrow | **V220** (poles 13.50, residual 4.7 %→2.8 %) |
| **Both better, steering still too heavy/slow** | levers landed, authority short | **V219** (10×, +56 % authority) |
| **Anything feels worse** | stop; the arms are single-variable | report it — V212/V215/V216 isolate which |

🛑 **SET YOUR EXPECTATIONS ON THE RATCHET — it is a long shot, not a likely fix.**

The kit's own measurements say the ratchet is a **lightly-damped mechanical resonance** (Q 14–29) on the **motor/rack side, which no channel on this bus observes**:

```
  limit cycle        EXCLUDED    calibrated Welch ladder
  stick-slip         KILLED      d log f / d log A = -0.034
  rate-limit         KILLED      backlash KILLED
  frequency tracks   LOAD        not amplitude, not the command
  engagement         SUPPLIES the resonance, does not amplify an existing tone
```

And the currency `0xC63AE` trades in **has already been tested on-car and came back null**: V104 raised assist-lane gain **×1.85 with its peak at 7.94 Hz** — dead centre of the ratchet band — its dose provably arrived, and it produced **no felt change**. Every alternative lever is closed on its own terms.

⇒ **A ratchet null on this drive is the expected outcome and is NOT evidence the dose failed to arrive** — `b5` settles arrival independently. **Fly V217 for the notch and the gain step**; the ratchet lever rides along because it costs nothing extra, not because it is likely.

**The scorer's 30–49 Hz band is the one to watch for damage.** 🛑 **But it is not purely 30–49 Hz** —
caches run at fs ≈ 101 Hz, so anything real in **52–71 Hz folds into it** and cannot be separated
afterwards. Read it as *"30–49 Hz **or its alias**"*. Read it as a large-excursion detector:
`< ~2` nothing broke · `> ~5` fall back · in between is unresolved. It **cannot** resolve the 1.65×
gain effect — the corpus spread is wider than that — so don't read a small move either way.

---

## What I cannot predict, stated up front

- **Whether any of this fixes the ratchet.** `0xC63AE` is the only lever that exists for it; every
  alternative is closed on its own terms (biquad re-centring by a 29,348-candidate sweep, the
  base-assist damper by sizing, the rate lane by four flown builds). It is untested.
- **Whether the 8× gain costs anything at 30–40 Hz.** One drive cannot settle it; that needs a
  matched V216/V217 pair.
- **What the ~31 Hz line on your aborted V94 drive actually was.** The obvious mechanism
  (apparent inertia ⇒ `f ∝ 1/√J`) is refuted by its own arithmetic. Still open.

---

## Verification behind this build

- **835 close-out assertions**, 13/13 shelf builders reproduce bit-for-bit.
- Gate `[17]` pins the **complete** non-stock delta — negative-tested by reverting all 320 payload
  bytes one at a time: **0 missed**.
- Gates `[8]`, `[13]`, `[14]`, `[15]`, `[16]` were all added or hardened this session after being
  found to check the wrong thing or nothing at all.
