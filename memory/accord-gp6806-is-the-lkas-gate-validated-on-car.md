---
name: accord-gp6806-is-the-lkas-gate-validated-on-car
description: ★★★ gp-0x6806 != 0 agrees with carControl.latActive at 99.90-99.94% over 37,914 frames on two V57 routes, and toggles at 0.03-0.05/s. It IS "LKAS is applying", it does NOT drop out during steady engaged holding, and it is three orders of magnitude too slow to parametrically pump. V67's gate is validated on-car BEFORE the flash, from data that was already on disk.
metadata:
  type: reference
---

# ★★★ `gp-0x6806` IS the LKAS gate — validated on-car, from existing data

Decoded 2026-08-01 by the orchestrator from **V57's own probe**, which put `(gp-0x6806 == 0)` on
`0x14A` byte4 **bit6** and flew routes `28` and `29` back in July. Nobody had ever correlated it.

| | route `29` | route `28` |
|---|---|---|
| frames / span | 7,924 / 79.2 s | 29,990 / 299.9 s |
| **agreement with `carControl.latActive`** | **99.90%** (8 disagreeing frames) | **99.94%** (17 frames) |
| `gp-0x6806 != 0` duty | 21.73% | 49.88% |
| **transitions** | **4 in 79.2 s = 0.0505/s** | **9 in 299.9 s = 0.0300/s** |

## What this settles

1. ✅ **`gp-0x6806 != 0` ⟺ LKAS is applying.** Polarity confirmed, and confirmed at two very
   different duty cycles (21.7% and 49.9%) so it is not an artifact of one route's engagement pattern.
2. ✅ **It does NOT drop out during steady engaged holding.** A trace had flagged a real structural
   ambiguity — `gp-0x6806` is written by an arbitration ramp FSM, `= 1` for "ramp-active" phases 1–4
   and `= 0` for reset/settled phases 5/6/7, so *static analysis could not rule out* the cell going
   low while LKAS held steady. **It does not**: 99.9% agreement across 37,914 frames means the
   settled phases do not occur during ordinary engaged driving. Measurement closed what structure
   could not.
3. ✅ **THE PARAMETRIC-PUMP KILL CRITERION IS SATISFIED WITH ENORMOUS MARGIN.** 0.03–0.05 toggles/s
   against modes at 21 and 45 Hz — **three orders of magnitude**. A gain keyed on this cell cannot
   modulate at the mode frequency, which is the failure mode V58/V59/V60 spent three builds chasing.

⇒ **V67's gate is validated BEFORE the flash**, and V67 does not have to wait for V66's drive.

🛑 **The lesson is about where to look, not about the cell.** This measurement existed since July.
Every session since has treated the `gp-0x6806` polarity as an open static-analysis question while a
direct on-car answer sat in `_cache_r28` / `_cache_r29`. **Before opening Ghidra on a signal, check
whether a past probe already flew on it** — `docs/BUILD-LINEAGE.md` lists every probe payload, and
`analysis-2020accord/route_build_registry.py` maps every route to its build.

## What is still NOT closed for V67

- **`gp-0x671d` OUTRANKS the arm and is LIVE.** If it fires, r24's gain is pinned to `0xC6442` = 1024
  — *below* the stock default — so V67 would be **worse than V66**. V64's probe read it 0 across
  14,980 frames of creep; V67's own probe bit5 measures it directly.
- **`gp-0x683c`'s deadness** rests on two independent static methods, never on-car. Mitigation: if it
  were live, V65's r24 gain would already be taking the 512 arm today, and nothing in V65's behaviour
  suggests it.
- **Grind #2 survives under LKAS**, at 2.21× — see
  [[accord-grind2-is-a-45hz-mode-under-driver-load]]. LKAS separates grind #1 well (98.7% vs a 54.7%
  base rate) and grind #2 barely (84.3%).

See also [[accord-gp683c-dead-gate-is-a-free-lkas-arm]], [[feedback-probe-the-gate-not-just-the-output]].
