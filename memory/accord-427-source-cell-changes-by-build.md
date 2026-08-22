---
name: accord-427-source-cell-changes-by-build
description: "CAN 427 (0x1AB) MOTOR_TORQUE carries a DIFFERENT firmware cell on almost every build since V87 - eight sources and four sar shifts. Any cross-route analysis assuming one meaning is wrong. Read the map from the images at 0x55DF2/0x55E10, never from the docs. Includes the rectification and aliasing limits."
metadata:
  type: reference
---

# ★★★★★ 427'S SOURCE CELL MOVES BUILD TO BUILD — read it from the IMAGES

Read from every `_v*_plain_image.bin`: `int16 LE` at `0x55DF2` (the packer's source displacement) and
the `sar` imm5 at `0x55E10`. Cross-checked against `probe_build`/`wire_source` in each cache's
`_1ab.json`. 2026-08-21. **EVIDENCE.**

| build | `0x55DF2` | source | shift |
|---|---|---|---|
| ≤V86B | `e893` | `gp-0x6C18` | sar 3 |
| **V87, V88, V89** | **`6894`** | **`gp-0x6B98`** (delivered motor command) | sar 3 |
| V90, V91, V93 | `da94` | `gp-0x6B26` | sar 3 |
| V92 | `4294` | `gp-0x6BBE` | sar 4 |
| V94 | `da94` | `gp-0x6B26` | sar 1 |
| V96–V99 | `9094` | `gp-0x6B70` | sar 6 |
| V100, V101 | `6c94` | `gp-0x6B94` | sar 6 |
| V102, V103 | `b494` | `gp-0x6B4C` | sar 6 |
| V104 | `7a94` | `gp-0x6B86` | sar 4 |

**ROUTE → SOURCE:** r71=V87 · r73=V88 · r75/r76=V89 ⇒ **`gp-0x6B98`** · r77=V90, r78=V91, r7d=V94 ⇒
`gp-0x6B26` · r79=V92 ⇒ `gp-0x6BBE` · r7e/r7f=V96, r80=V97, r81=V98, r82=V99 ⇒ `gp-0x6B70` ·
r85=V100, r95=V101 ⇒ `gp-0x6B94` · r96=V102, r9e=V103 ⇒ `gp-0x6B4C` ·
**r97 = STOCK, no repoint** (427 is Honda's own MOTOR_TORQUE, approx 0).

## 🛑 427 IS RECTIFIED — and that decides which routes are usable
The packer ships `abs(cell) >> shift`, 10-bit unsigned. A magnitude is a **NONLINEAR** function of the
signal, so a directed cross-spectrum against any other channel is destroyed by sign flips unless the
sign is recovered. **Only V88 / route 73 has a cave reading the SAME cell** (`0x14A` byte4 b7 = sign of
`gp-0x6b98` at 100 Hz). V89 repointed the cave to `gp-0x6ae2` (`build_v89_tva.py:122`).

Measured `gamma^2(e4, 427)` at 0.5–3 Hz: **0.0018–0.0119 on the rectified routes vs 0.53 on route 73.**
The signed reconstruction is validated: a ±2-row skew sweep moves H1 <3 % at 0.5–3 Hz, and
`(raw14_t, raw14_b4)` reproduces `(t, probe)` **bit-identically**. Sign-flip rate 4.4/s, well below the
6–9 Hz band, which is why the rectification is recoverable at all.

## 🛑 ALIASING IS BAND-DEPENDENT — 20–24 Hz IS NOT A MAGNITUDE
`fs = 49.835 Hz` (not 50). The band folding onto **6–9 Hz** is 40.8–43.8 Hz: fold ratio
**0.0031 / 0.0200 / 0.0204** (r73/75/76) ⇒ negligible, ~1 % on any derived amplitude.
The band folding onto **20–24 Hz** is 25.8–29.8 Hz: fold ratio **0.23 / 2.57 / 0.28** —
**on route 75 the folded energy is 2.6× the true in-band energy.**
⇒ **20–24 Hz on 427 is a valid NULL** (folded energy is incoherent with a driven tone, which is why
gamma^2 there measures 0.0001–0.0011) **but must NEVER be quoted as a measurement of true 20–24 Hz
content.** Same error class as the retracted 30–49 Hz control band, pointed the other way.

Related: [[accord-band-envelope-is-rectified-not-analytic]] · [[accord-raw14-offbyone-in-every-cache]] ·
[[accord-lkas-lane-passes-8hz-nearly-unattenuated]]
