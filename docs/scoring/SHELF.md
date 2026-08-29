# THE SHELF — what to fly, 2026-08-29

🛑 **Nothing is flashed until you name the file and the bus and it is read back to you.**
🛑 **Kill openpilot/pandad first** (`tmux kill-server` on the comma device).

Three builds are flashable. Everything else from this chain (V185–V193) has been renamed
`SUPERSEDED-DO-NOT-FLASH-…` so it cannot be picked by mistake. The `_plain_image.bin` files were
**not** renamed — later builders read them as bases.

---

## ⭐ V196 — both symptoms. **Start here.**
```
39990-TVA,A160-V196-V195BASE-ENGAGED-INERTIA-HALF-DOSE-0x13000-0x100000.rwd
image f904e43a1f4ccb94e81204dbecd93982049a024b95e48bd1c2c43852a7edec8e
```
The grind notch **plus** the ratchet lever. Card: `DRIVE-CARD-V196.md`.
Carries one recoverable sign bet (the inertia half-dose). If ratcheting gets **worse**, that bet was
wrong — go to V195, three int16 back.

## V195 — the grind only, no sign bets
```
39990-TVA,A160-V195-V189BASE-NOTCH.REFIT.ON.RATE-0x13000-0x100000.rwd
image a3ea8683df48c6b3f40e8ba8ac879047da6aec62fedc8d56cf9f1dc83f7b610b
```
Everything in V196 except the inertia half-dose. Card: `DRIVE-CARD-V195.md`.
Choose this if you would rather not carry an unproven sign.

## V194 — the detector probe
```
39990-TVA,A160-V194-V193BASE-PROBE-THE-DETECTOR-INPUT-0x13000-0x100000.rwd
image 2adde4ec37be9150b3d501bcd61b7d11a33e49e839c944622474c1d368db0f10
```
A different branch: the detector-conditional levers plus a CAN probe on `gp-0x6c2c`.
⚠ **The only build here that can change normal driving** (the dwell widening makes the detector
state reachable). Its notch is the older, weaker fit (15.0× vs 21.5×). Fly it only if the detector
question is worth a drive on its own. Card: `DRIVE-CARD-V194.md`.

---

## What each build changes relative to the car you drive today
| | V195 | V196 | V194 |
|---|---|---|---|
| grind notch | **19.75 Hz, 21.5×** | **19.75 Hz, 21.5×** | 19.40 Hz, 15.0× |
| engaged inertia | Honda | **half Honda** | Honda |
| K1 friction, accel alpha | → Honda | → Honda | → Honda |
| detector levers | — | — | ✔ (3 cells) |
| CAN probe | — | — | `gp-0x6c2c` |
| can change **manual** driving | no | no | **yes** |

## The drive, for any of them
1. **1a** — 15 s engaged creep, 1–24 km/h, driven **how you normally do**. Scoreable today.
   **1b** — the same again **hands on**. Baseline-building; thresholds unknown.
   Don't break either pass up — the analysis window is 5.12 s.
2. `python rlog-tools/score/score_band_excess.py <route-tag>`
3. `python rlog-tools/score/cross_channel_band_excess.py`
4. V194 only: `python rlog-tools/probe/decode_v194_detector_input.py <route-tag> --v194`

🛑 **Read the ABSOLUTE column, not the control-band ratio** — the ratio divides by 30–40 Hz, which
the notch also attenuates, and it will read a large fix as a regression.

## What the symptoms map to
| symptom | what it is | lever |
|---|---|---|
| grinding | a real motion oscillation, strongest in steering rate | the notch |
| ratcheting | torque-dominant, ω²-weighted lane | inertia half-dose + K1 revert |
| command oscillation | cannot be commanded (1–5 Hz low-pass); it tracks the grind | fixed by fixing the grind |
| LKAS authority | the knob is `0xC6CD0`, also the grind's carrier | **after** the grind is confirmed fixed, 6× → 8× |

## Stop conditions
- **Ratcheting noticeably worse** → the inertia sign was inverted. Reflash V195.
- **Wheel heavy or dead to fast inputs** → the half-dose is too much; quarter it.
- **A new high note or whine while engaged** → Honda's 55 Hz null, which the notch gives up.
  Manual driving is bit-for-bit stock, so this can only appear when LKAS is on.
