---
name: reference-accord-lkas-only-rate-limiter-c6194
description: 0xC6194 is a fully-implemented LKAS rate limiter that is ARCHITECTURALLY INERT — its output is multiplied by cal 0xC63CC which is exactly 0. There is NO live LKAS-specific slew limit; the LKAS lane reaches the aggregator unfiltered.
metadata: 
  node_type: memory
  type: reference
  originSessionId: 2a888703-82cf-4378-8b23-ce6677f440d5
  modified: 2026-07-20T00:25:58.220Z
---

## ⚠⚠ `0xC6194` IS DEAD CALIBRATION. Do not build on it.

`FUN_00026c80` contains a complete, correct-looking per-cycle rate limiter on the LKAS lane: it steps a
persisted 32-bit state `gp-0x3d6c` toward a clamped target by at most cal **`0xC6194` = 3** per call
(`0x27622 ld.hu 0x7194,tp,r7` → `cmovgt`/`cmovlt` at `0x2762e`/`0x27638` → `st.w r8,-0x3d6c,gp` at
`0x27654`). Bounds `0xC6192`=2048 / `0xC6198`=3072.

**It does nothing.** Verified at instruction level:

```text
0x276c2:  ld.hu 0x73CC[tp], r8      -> cal 0xC63CC
0xC63CC:  bytes 00 00 00 04         -> ld.hu takes the first halfword = 0x0000
```

That zero multiplies the entire term carrying the rate-limited state:

```c
gp-0x6b4c = gp-0x3d88 + (short)(gp-0x6752) * ((iVar13 * cal[0xC63CC]) >> 10)
```

`(anything * 0) >> 10 == 0`, so **`gp-0x6b4c` reduces to `gp-0x3d88` alone**, which is an *unlimited
per-mode passthrough* — `Σ over i=0..10 of (tp+0x5118[i] ? *(short*)(gp-0x62b0 + 2i) : 0)`, computed
fresh every call with no persisted state, no step, no IIR.

Blast radius checked: `gp-0x3d6c`, `gp-0x3d84`, `gp-0x3d88` have **2 sites each, all inside
`FUN_00026c80`** (image-wide sweep). No other consumer. So changing `0xC6194` is inert, not merely
redundant — it cannot affect anything.

## ⇒ THERE IS NO LIVE LKAS-SPECIFIC SLEW LIMIT

The LKAS command already reaches the aggregator **unfiltered**. Stock firmware already satisfies "LKAS
command slew should not be limited." The only slew limiting that touches LKAS is the **merged-command**
governor `FUN_0004503c` (`0xC6206`/`0xC6208`), whose target is `gp-0x6b94` — the aggregator output,
LKAS **+ base assist** (verified at `0x453E0`). Freeing that also frees base assist, which openpilot
neither commands nor observes, and is the prime suspect for V40's ignition fault. See
[[v40-governor-slew-root-cause]].

## Consequences

- **A "rate-limit-induced limit cycle on the LKAS lane" cannot explain the tens-of-Hz vibration** —
  there is no live rate limiter there. That hypothesis is dead.
- If a rate limit shapes the LKAS lane at all, it must be **upstream of the `gp-0x62b0` mode-value
  array** (accessed via a computed base, so a gp-relative displacement sweep will not find it) or
  further up in whatever sets the `tp+0x5118` mode flags. **Untraced.**
- `gp-0x6752` is a **runtime variable, not a cal** — 2 writers, both in `FUN_00048a40` (`0x48e68`,
  `0x48e88`), against dozens of readers across the torque pipeline including M1 `FUN_00042af8`, M2
  `FUN_00043e44` and the aggregator. Ubiquitous shared scalar, likely a polarity/enable byte.

## Process note

An earlier version of this memory asserted `0xC6194` was "the correct place to loosen LKAS slew."
**That was wrong and is retracted.** The zero gain was visible as a u16 read of `0xC63CC` early on and
was dismissed as a probable reporting error rather than chased — a build was written on top of it
before it was checked. Chase the anomaly first.
