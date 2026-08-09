---
name: accord-fun3b8f6-coulomb-relay-proportional-to-command
description: "★★★★★ FUN_0003b8f6 (1 kHz, undocumented until 2026-08-09) contains a Coulomb RELAY whose magnitude is proportional to the DELIVERED MOTOR COMMAND. Relay index 7.87 — 2.4× V80's, the worst-grinding build ever. Lever = 0xC40BC, virgin on all 84 builds, 1 reader / 0 writers."
metadata:
  node_type: memory
  type: reference
---

**Orchestrator-verified at the decompile level, 2026-08-09.** `FUN_0003b8f6` @`0x3b8f6`, task 1 =
**1 kHz** (sole caller `FUN_0002214a` @`0x2240e`, immediately before `FUN_0003bc20` @`0x22416`). It was
absent from the golden model and from every handoff until this session.

```
gate: |gp-0x6b98| <= 0x2000 && |gp-0x4f60| <= 0x6400 && |gp-0x6abc| <= 13000 && gp-0x6752 in {-1,0,1}
      -- else the function writes the 0x7FFF INVALID SENTINEL and the whole lane drops out.
model    = EMA2(gp-0x6b98 * polarity / 1024, a=0xC40D4=573/4096)          # the DELIVERED MOTOR COMMAND
         + clamp(FIR(EMA2(gp-0x4f60/1024, a=0xC40D8=3686/4096) * 0xC613A/32768), +-15)
           * LERP(gp-0x6a10, X 0xC6B66 / Y 0xC6B80)/1024
iVar20   = polarity * gp-0x6abc * 12                              @0x3bab0
ratio    = clamp(iVar20 / cal(0xC40BC), +-1.0)                    @0x3bab4   <-- THE RELAY
FRICTION = clamp(EMA(|model|*ratio*0xC40D2/1024 + 0xC4080/1024*ratio, a=0xC40D0=408/4096), +-10)
INERTIA  = clamp(EMA2(d/dt(iVar20)*0.5*17.453293, a=0xC40D6=246/4096) * 0xC646E * 2^-24, +-10)
gp-0x6bfc = clamp(0xC6468(=2639) * (model - FRICTION - INERTIA), +-20000)
          -> FUN_0003bc20 -> gp-0x6bfe -> FUN_00038148 -> gp-0x6b70 -> FUN_00037fe6 -> gp-0x6ad6
          -> PID FUN_0003a382 -> gp-0x6ad4 -> aggregator -> gp-0x6b94 -> [[accord-aggregator-reaches-motor-via-gp6acc-bridge]] -> motor
```

## 🛑 The finding: `ratio` is `sign(motor rate)`, not a gain
It saturates at `cal(0xC40BC)/12` = **600/12 = 50 counts**, against this function's **own enable gate of
13000** ⇒ pinned at ±1 across **99.62%** of its valid input range. **This argument is scale-free** — it
does not depend on `gp-0x6abc`'s unconfirmed counts-per-°/s, which is the one number nobody has pinned.

Describing-function relay index `N(50)/N(500)`, reproduce with
`analysis-2020accord/fun3b8f6_friction_relay.py`:

| `0xC40BC` | saturates at | relay index |
|---|---|---|
| **600 (shipped, ALL 84 builds)** | 50 ct | **7.87** |
| 3000 | 250 ct | 1.64 |
| 6000 | 500 ct | **1.00 (viscous)** |

Reference scale: **Honda's viscous damper 1.00 · V75 1.45 · V80's bang-bang damper 3.27** — and V80
produced the worst grinding in this kit's history. **This term is 2.4× worse than V80's.**

**And `FRICTION` is proportional to `|model|`, i.e. to the DELIVERED COMMAND** ⇒ engagement-scaled with
no engagement flag anywhere. Sized: `|model|` is bounded to ~8 by the `|gp-0x6b98| <= 0x2000` gate, so
`FRICTION <= ~0.8` (never reaches its ±10 clamp) and the discontinuous swing across a velocity
zero-crossing is **~1,000–2,100 counts p-p in `gp-0x6bfc`** at a typical engaged command.

## The lever
**`0xC40BC` = 600.** Exactly **1 reader** (`ld.hu 0x50BC[tp],r16` @`0x3BAB4`) and **0 writers**
image-wide — confirmed two ways (GhidraMCP + a raw LE byte scan of both encodings).
🛑 **Encoding trap: the instruction halfword is `0x50BD` (the `disp|1` form). A scan for `0x50BC`
finds NOTHING.** See [[accord-v850-scan-traps-formatv-and-storezero]].
Flat `tp` scalar ⇒ **RULE 7 is moot, it is mode-independent.** Byte-identical on STOCK/V38/V67/V81/V84
and named in **zero** of the 84 build scripts, along with `0xC40D0` `0xC40D2` `0xC4080` `0xC40D4`
`0xC40D6` `0xC40D8` `0xC646E`. **The entire plant-model cal block is virgin.**

## 🛑 What bounds its expected efficacy — state this before any flight
**V56 muted this whole lane's terminus (`0xC6AF0` → 0) and got a NULL on the 18–22 Hz grinding**, while
the operator reported it **cost damping/feel**. ⇒ **Do NOT expect a `0xC40BC` change to move 18–22 Hz
(S1).** Its targets are S2 (6–9 Hz micro-ratchet), S3 (macro ratchet) and S4 (excess friction) — none of
which existed as a scored taxonomy when V56 flew, so none was ever tested.
⚠ Counter-argument to carry: the term is **dissipative**, so linearising it **removes dissipation at low
rate**. The case for doing it anyway is that a relay's harmonic injection is not clean damping — that is
an argument, not a measurement.

## Related
`gp-0x6bf6` / `gp-0x6c00` / `gp-0x6ae0` (INERTIA×1024) / `gp-0x6ae2` (FRICTION×1024) are **1 writer /
0 readers** ⇒ free, blast-radius-zero telemetry taps; `gp-0x6ae0`/`gp-0x6ae2` are written on the success
path only and hold **stale** values when the gate fails, so they need a companion gate rung.
⚠ `INERTIA` is **not** inertia compensation as delivered — its real part stays positive vs *rate* across
7.79–28.5 Hz ⇒ a lagged velocity damper, running at ~1–6% of its clamp.
See also [[accord-fun3b8f6-sensor-branch-is-live-not-dead-code]] and [[accord-v80-damper-relay-and-grind1-inert]].
