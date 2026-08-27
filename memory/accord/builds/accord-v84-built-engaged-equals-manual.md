---
name: accord-v84-built-engaged-equals-manual
description: V84 BUILT, VERIFIED, UNFLASHED on a V83a base — after it, every damper factor family is engaged-equals-manual exhaustively over speed counts 0..14000 on BOTH mode pairs, and the damper surface is byte-identical to V67/V68.
metadata:
  type: project
---

★★★★ **V84 BUILT, VERIFIED, UNFLASHED.** 2026-08-08. Base = **V83a**.

**7 control cells + a probe repoint**, all inside the **proven 68-byte cave**. CRC **50/50**.

| artefact | sha256 |
|---|---|
| `.rwd` | **`5e830b2588b22fd6238c4bd376e602d603b5d25871368d08df7986519cda1bca`** |
| plain image | **`344f22f7303f6b5b006b13d329192ce098d118c9ce149834cb3cc05899dc637a`** |

⚠ **V84 WAS RE-CUT.** An earlier **control-only** cut (`.rwd` `54985b45…` / image `bdd857c9…`) is retained
on disk as **`SUPERSEDED-DO-NOT-FLASH-…`**. This is the hazard in
[[accord-recut-overwrites-the-previous-plain-image]] — the flash risk is closed by the rename, the
**verifiability** of the superseded cut is not. **Flash only the `5e830b25…` `.rwd`.**

## The edits

| site | change | why |
|---|---|---|
| `0x3AA96` | `C5` → `FB` | restores **lever B** — repoints the r24 arm's gate onto the LKAS gate `gp-0x6806` |
| `0xC6446` | 512 → **5244** | lever B's arm value |
| FactorC **m26 and m27** `Y[0]` | 566 → **0** | removes the engaged-only dip on **both** engaged columns |
| FactorE **m27** | → **Honda** | disarms the relay plateau V83a left standing on mode 27 |

## ★ What V84 establishes

- **After V84, every factor family is `engaged ≡ manual`, verified EXHAUSTIVELY over speed counts
  0…14000, on BOTH mode pairs** (24↔26 and 25↔27). That closes the half-application hazard in
  [[accord-mode-27-is-a-second-engaged-column]] — V83a's mode-27 relay is gone.
- **V84's damper surface is byte-identical to V67/V68** — the pair that measured the kit's best grind-#1
  result (0.40 [0.27, 0.58]) **and** drove creep grind #2 to zero bursts. So V84 restores the measured
  configuration rather than proposing a new one.

⚠ Carry the standing caveat from [[accord-v81-carries-neither-grind1-fix]]: **lever B is not the highway
answer.** V67/V68 flew it and the highway grind was still present. V84 is the low-speed case plus a clean
damper baseline, not a highway fix.

Related: [[accord-v83a-flew-worst-modern-build]] · [[accord-v81-built-c407e511-friction-stock]] ·
[[accord-r24-is-the-grind1-actor-r26-nearly-blind]] · [[accord-v67-flew-both-grinds-fixed]] ·
[[accord-stock-mode24-equals-mode26-damper-is-ours]]
