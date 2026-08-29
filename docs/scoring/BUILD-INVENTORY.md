# BUILD INVENTORY — what is cut, and how to choose

**Six builds are cut and unflashed. You can only fly one at a time, so this is the decision table
rather than a list.** All are on the same V158 base, so all carry V158's damper shape (the grind
lever) and all are scored from the same single 15-second engaged creep pass.

> 🛑 Nothing here authorises a flash. Name the file and the bus yourself; kill openpilot/pandad
> (`tmux kill-server`) first.


> 🚩 **V173 SUPERSEDES V172 AS FLY-FIRST.** V173 is V172's poles with **Honda's 55.23 Hz notch
> kept bit-for-bit** (`C_B0` untouched). Same +30.1 ms group delay, same ratchet effect (0.476 vs
> 0.444 at 8.64 Hz), three cells instead of four, and it never amplifies (max |H| 0.9946). It gives
> up half the grind attenuation (4.6x vs 9.6x) to preserve a notch whose purpose is unknown — the
> right side to err on, since the grind already has V158's damper on the same base.
>
> ```
> V173  image a9877aeecfbbbf2436c63fbc81041e1dfbfde787f5a1bf8ea58404b8f86ab1f7
>       .rwd  5d213cf8604df90f2df2eaa2a8e40ccedde89f1d66055cb2a22c81edb7245396
> ```
> Fly V172 only if the grind is the priority and losing Honda's notch is acceptable.

---

## THE CHOICE

| | edit | ratchet | grind | what it costs | when to fly it |
|---|---|---|---|---|---|
| **V172** | `0xC60A8..B4` section retune | **6.1×** | **9.6×** | +30 ms group delay; 3–5 Hz down 15–32 % | **FIRST** |
| V168 | `0xC6384` 2048→1536 | 3.4× | — | heavier near centre, always | if V172's lag is the problem |
| V169 | `0xC6384` 2048→1792 | 2.2× | — | as V168, less of it | if V168 is close but too heavy |
| V170 | `0xC6384` 2048→1280 | 4.5× | — | as V168, more of it | if V168 helps but not enough |
| V171 | `0xC6384` 2048→1024 | 5.7× | — | as V168, most of it | the largest sane cap dose |
| V158 | damper shape only | — | (grind) | engaged-only damping | to isolate the grind lever on feel |

```
V172  image ff8d07e6ba3e80484b8ef67eeb4d9fd13804ee999d35953038355ab2cd0ab830
      .rwd  c0ed77b773a7e7f300ab438450817e17f49269c67d096edefa56dea140e958a5
V168  image 058dd64ac442ef43c790965c9a5fc011f147f7ff0a5e7cd0c0d1bb8889c7b0ff
      .rwd  0f0ace3b5bc0a8541227e06c831c555797566374b298ba606614f5a09a1356f1
V169  image ed9e5fec84378f201644d38be671824c2a3b29009ce672993652a9cc9d8e3566
V170  image 0c923c363a92045929d5cde74810c34af8ecda84737da8bf80c05b7b53d3c80c
V171  image e3cbc92de7a07bf2cef813ae7f5c139ecaf419737cfab22c00b1dd923ee46fb1
V158  image 42078806f55829039b0891b0f32c465b7caa26f8c5079cfe9c60ab2ea7b0ccaf
```

---

## ✅ DO NOT STACK V172 AND THE CAP

They attack the same lane by different means, so they multiply — but the marginal return is poor:

```
   V172 alone          6.1x more damped than stock
   V172 + cap 1536     7.2x   => marginal 1.17x, for the FULL static weight cost
   V172 + cap 1024     8.3x   => marginal 1.35x
```

⇒ **carrying both feel costs buys 17–35 %.** Not worth it. V172's own build asserts the cap is still
stock, so the two cannot be stacked by accident.

---

## ✅ V172 ALREADY REACHES THE TARGET, AND WHAT WOULD COME NEXT

```
   to reach a Q ratio of 3.0 (a 4.8x improvement) needs |L| <= 2.025
   V172 leaves |L| = 1.732   => already past it
```

After V172 the loop splits **52 % assist map / 48 % everything else**, and "everything else" is the
census's engagement-conditional terms — PID 0.2565, r24 0.049–0.293, r26 0.098–1.17 (live only while
`gp-0x6b5e == 0`), `FUN_00036682` 0.0032.

⇒ **a third lever would have to come from those, not from the map.** That is a separate
investigation and it is **not** worth starting before a drive result: two independent levers already
exceed the target on paper, and which of them the car actually responds to is the thing no amount of
further analysis can settle.

---

## WHAT THE DRIVE SETTLES, WHICHEVER YOU FLY

Both levers rest on the **same** real-positive `P·L` assumption. So:

- **ratchet falls** → the loop-gain account is confirmed and the remaining question is only dose.
- **ratchet unchanged** → the assumption is falsified for **both** levers at once, the assist map is
  exonerated the way the Coulomb relay already is, and the search moves outside this loop.
- **ratchet rises** → `P·L` is not real-positive; revert and re-derive the phase.

V172 adds a discriminator the cap does not have: **the grind should fall further than the ratchet**
(9.6× vs 2.2× filter attenuation). If the ratchet moves and the grind does not, the shared-loop
account is wrong somewhere and that gap names where.

**One continuous 15-second engaged creep pass, with real curvature, answers all of it.**
Score with `python rlog-tools/score/score_band_excess.py <route-tag>`.
