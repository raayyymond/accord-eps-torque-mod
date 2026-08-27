---
name: accord-v81-built-c407e511-friction-stock
description: V81 = the FLOWN V75, with 0xC407E returned to Honda's 511 interlock and the x1.5 friction table reverted to stock. CAL-ONLY, no cave change, 126 bytes. BUILT, VERIFIED, UNFLASHED.
metadata:
  type: project
---

# ★★★ V81 BUILT — the flown V75 with the friction lane returned to Honda's configuration

**V81 = the FLOWN V75 + two cal edits. CAL-ONLY. NO CAVE CHANGE. BUILT, VERIFIED, UNFLASHED.**

| | value |
|---|---|
| builder | `analysis-2020accord/builds/v80_v107/build_v81_tva.py` |
| base | `_v75_CY0.566-EX1.200_magprobe_plain_image.bin` sha `e16ba4093205772e3a1bfb48f8790ade5c12f0e042b6608e51a48faaf1edf61c` — **the cut that FLEW route 5e** |
| image | `_v81_C407E.511-FRICTION.STOCK_plain_image.bin` sha **`4ddbd0e2fca5c37873f4c1b633e88a81d4d62a3b45743ce2c13e1c7403bfd65b`** |
| rwd | `39990-TVA,A160-V81-V75BASE-C407E.511-FRICTION.STOCK-magprobe-6bd0-thermo-6ac2-0x13000-0x100000.rwd` sha **`fc4d4f74956c76dbda340e17ecf4c3ecbe3f86bbc47418cbc3b3185c52aea109`** (986,042 B) |

**EDIT 1** `0xC407E` 850 → 511 (bytes `5203` → `ff01`) — restores Honda's hard-fault interlock
([[accord-friction-lane-ceiling-is-the-hard-fault]]).
**EDIT 2** the ×1.5 friction table → **stock** at all 14 sites (`0xCF6E0 0xCF6F0 0xD0A5C 0xD2A4C
0xD2A5C 0xD3A5C 0xD3A6C 0xD4A5C 0xD6A5C 0xD7A5C 0xD7A6C 0xD8A5C 0xD9A5C 0xD9A6C`),
`67c667de7bf4` → `9ad99ae952f8`.

🛑 **CORRECTION TO THE RECORD: the ×1.5 friction was introduced by V73, NOT V74.** Verified across the
lineage — stock/V70/V71c/V72 carry Honda's row; **V73/V74/V75 carry ×1.5** (and V73 also raised
`0xC407E`). Every prior statement attributing the ×1.5 to V74 is wrong by one build.
🛑 **`0xD2A4C` is mode 10 — a DISENGAGED-column record.** V74's derivation only ever wrote the 13 engaged
modes, so it never saw m10. V81's edit there is a **revert to stock**, so that column can only become
*more* stock; asserted as *"all 34 friction records byte-identical to STOCK"*.

## Orchestrator's own from-disk verification — ALL PASS
- **25 differing runs / 126 bytes** vs the flown V75: 15 functional (86 B) + 10 CRC words (40 B).
  **0 unexpected functional runs. 14/14 friction sites.**
- **Value-anchored**: restoring exactly those 126 bytes reproduces the flown V75 **bit-for-bit**
  (sha back to `e16ba409…`) — a total statement over all `0x100000`, not a span check.
- **Exactly 1 flashable V81 `.rwd` and 1 V81 plain image on disk.**
- **All 34 friction records byte-stock**; mode 24 (manual) identical to V75 across all six record types,
  each resolved through its pointer array.
- **Unchanged from V75**: m26 FactorC `[566,234,429,908]` · FactorE X `[12,200,2500,4000]` Y
  `[0,539,539,927]` ⇒ **`k` = 1.5798 identical** · `0xC63A0` = 2048 · `0xC62EA` = 0 · `0x454FE` = `0xB5`
  · `0x2A1F0` disp = `0x7CD0` · `0xC6CD0` = 3564 · `0xC646C` = 891 stock · `0xC4004` = f32 0.5 frozen ·
  the 68-byte cave @`0xC4B34` and hook @`0x55C0E` byte-identical (also re-derived from scratch by V75's
  own `build_cave()` and re-disassembled out of the built image).
- CRC: exactly 10 blocks moved (asserted, not observed), full chain **50/50 PASS**; no edited byte in
  `[0xC5000, 0xC5FFC)`. Full `.rwd` encode → decode → re-verify-from-readback, plus a separate from-disk
  decode of the shipped `.rwd`.

## GATE 1 — RAM OWNERSHIP: **PASS, vacuous by construction**
Cal-only: no new RAM, no code, no instruction, no cave byte. Measured anyway: `gp-0x6b26` 1w/4r (no
literal, no `movhi` pair) · shadow `gp-0x4cd0` 1w/1r · `0xC407E` 0w/3r signed, all in one function ·
`0xC4004` 0w byte-frozen · `gp-0x6c2c` 2w unmoved. Friction records are pure data behind pointer array
`0xCBE74`; V81 writes 6 bytes inside 14 of them and **never** the count word, X axis or slack bytes.

## GATE 2 — CLOSED-LOOP STABILITY (magnitude AND phase): **PASS, empirically**
**V81 does not change any loop.** Damper surface, rate lanes, gate, both `sar` sites, `0xC63A0`, every
filter coefficient — byte-identical to the build that flew route 5e. The only dynamic element it touches
is a **saturation bound, moved DOWN**.
- **MAGNITUDE**: `k = ((C_Y0·E_Y1)>>10)/(E_X1−E_X0) = 297/188 = 1.5798`, a **frequency-independent
  scalar on the whole damper path** ⇒ loop gain equals V75's at every frequency, **no plant model
  needed**. The friction revert lowers an open-loop feed-forward coefficient; the clamp revert lowers a
  bound. Neither can raise gain anywhere. [EVIDENCE]
- **PHASE**: no new filter, delay, state or sample point ⇒ every pole, zero and task-order relationship
  is bit-identical to V75, so the phase response of every loop is *literally* unchanged. [EVIDENCE]
- **The one nonlinearity that moves, stated plainly**: `|gp-0x6c2c|` needed to REACH the clamp at creep —
  stock **3189** · flown V75 **3539** · **V81-A 3189** · V81-B 2126. So **V81-A clamps ~10% MORE often
  than V75 did (0.90×)** — harmless, and that is the point: at 511 the clamp sits *below* the 512 trip,
  so clamping **cannot fault**. V81-A's threshold is byte-for-byte stock's ⇒ its duty cycle is Honda's
  exactly. 511 also sits far inside the aggregator's ±1024 zero-reject window ⇒ no contribution cliff.
- ★ **The decisive empirical bound**: on **V76** — Honda's friction row with `0xC407E` = 511, i.e.
  exactly V81's configuration in this lane — the probe bit `|gp-0x6b26| > 448` fired **0 / 63,477
  frames** over route 65, positive control (`gp-0x67fa == 5`) **99.926%**, bit4 70.0%. **The lane doesn't
  reach 448, let alone 511 — the Coulomb-relay hazard here is not merely bounded, it is measured to be
  unexercised.** [EVIDENCE]
- ★ **The strongest GATE 2 case this kit has made**: V75's damper surface FLEW and eliminated the
  grinding, with `|gp-0x6bd0| ≥ 448` at **0.000%** of 28,317 engaged frames.

⚠ **V81 removes drag the operator may be used to.** Creep effort will differ from V75's — that is
intended (the V75 handoff attributes the creep-heaviness complaint to V73/V74's friction ×1.5 plus
`0xC407E` 511→850, and `0xC407E` is a bare `tp` scalar so it raised the drag ceiling in **manual** too) —
but it is a **feel change as well as a safety change and the operator should be told.**
⚠ `gp-0x6c2c`'s physical scale is still underived ⇒ *"3189 counts is a rare excursion"* rests on V76's
measured zero, not a unit conversion.

## Variant B — implemented, NOT cut
`ACCORD_V81_FRICTION=V75` keeps the ×1.5. Both variants' tokens appear in **both** output filenames so
they can never collide. Rationale for choosing **A**: a measured zero backs it; the ×1.5 contributed
nothing to the grinding fix (V74 already carried it and still measured grind #1 at 2.72×); it is
implicated in the creep-heaviness complaint; and it removes the second leg of the fault mechanism.
🛑 **The probe could not discriminate**: ×1.5 pins at 511 when the stock-equivalent raw ≥ **340.7**, and
the rung sits at **448** — 340.7 is 76% of 448, so the entire decision lives inside the comparator's
first cell. A calibrated model puts ×1.5's pinning at **rare tail events (~one per 285 s of mixed
driving), not a duty cycle** [BELIEF]. Settling it properly needs rungs at **320/352/416** (V75's
`shr 0x5` + `cmp imm5` idiom, ~30 B inside the proven 68 B extent).

⇒ **RECOMMENDED NEXT FLIGHT**: a **126-byte revert from the only build that has ever eliminated the
grinding**, with both legs of the recorded fault mechanism removed. **Flash decision is the operator's;
the file and the bus must be named back.**

Related: [[accord-v80-flew-the-damper-is-a-relay]] · [[accord-friction-lane-ceiling-is-the-hard-fault]] ·
[[accord-c63a0-exonerated-of-the-hard-faults]] · [[accord-grind1-is-inert-to-the-damper-dose]]
