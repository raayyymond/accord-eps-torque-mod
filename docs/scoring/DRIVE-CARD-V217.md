# DRIVE CARD — V217

**Flash target:** `39990-TVA,A160-V217-V216BASE-INERTIA.LANE.WEIGHT.TO.FLOWN.V108-0x13000-0x100000.rwd`
**.rwd SHA256** `941d82bf2dc556551dc9615bdd01d5e5e2d4fca7d8064578b5afb4bc969dcd54`
**image SHA256** `f89ea01f405d513985ce51c47f6796e1ea77f600fab3d9f7817cd79907a1967b`

> 🛑 **Nothing here authorises a flash.** Name the file and the bus yourself and they will be read
> back to you first. Kill openpilot/pandad (`tmux kill-server`) before any flash operation.

---

## What is on it — 19 payload bytes from YOUR CAR, every one a lever

```
  0xC60A8/AC/B0/B4   notch 20.50 Hz            GRINDING       (18-22 Hz)
  0xC63AE            1024 -> 512               RATCHET        (~7.8 Hz)
  0xC6CD0 + clamps   6x -> 8x                  LKAS AUTHORITY (+28.9 %)
  0x55DF2            427 probe -> gp-0x6b4e    the instrument
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

## What each outcome means — and which arm flies next

| what you report | what it means | next build |
|---|---|---|
| **Grinding gone, ratchet gone** | all three levers landed | nothing — hold V217 and drive it |
| **Grinding better, ratchet unchanged** | notch works, ratchet dose too shallow | **V218** (`0xC63AE` → 256) |
| **Grinding better but still there** | notch centred right, skirt too narrow | **V220** (poles 13.50, residual 4.7 %→2.8 %) |
| **Both better, steering still too heavy/slow** | levers landed, authority short | **V219** (10×, +56 % authority) |
| **Anything feels worse** | stop; the arms are single-variable | report it — V212/V215/V216 isolate which |

**The scorer's 30–49 Hz band is the one to watch for damage.** Read it as a large-excursion detector:
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

- **508 close-out assertions**, 13/13 shelf builders reproduce bit-for-bit.
- Gate `[17]` pins the **complete** non-stock delta — negative-tested by reverting all 320 payload
  bytes one at a time: **0 missed**.
- Gates `[8]`, `[13]`, `[14]`, `[15]`, `[16]` were all added or hardened this session after being
  found to check the wrong thing or nothing at all.
