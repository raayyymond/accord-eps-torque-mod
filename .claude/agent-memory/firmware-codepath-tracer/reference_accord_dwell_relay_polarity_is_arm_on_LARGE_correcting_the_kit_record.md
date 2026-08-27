---
name: reference_accord_dwell_relay_polarity_is_arm_on_LARGE_correcting_the_kit_record
description: "CORRECTION: FUN_00036388's dwell counter arms when |gp-0x6b64| > cal(0xC618A)=1024, NOT when it is less. Pinned in assembly at 0x36448 (cmp r16,r7 + setfgt) with the operand order validated in-block by an abs() idiom, and confirmed by the decompile AND by V92's on-car duties. This inverts my own prior memory and three earlier sessions, and it EXONERATES the byte7 b6 rung that accord/firmware/accord-return-centre-and-detent-dead-engaged.md indicted -- the 855s sustained (gate=0,snap=0) run is the PREDICTED steady state, not a null on the gate."
metadata:
  type: reference
---

# 🛑 The dwell-relay polarity is ARM-ON-LARGE — correcting the kit's record, 2026-08-12 (`fw-return`)

## The correction [EVIDENCE, assembly + decompile + on-car, three independent lines]

The kit records `window_open = |gp-0x6b64| < cal(0xC618A)=1024` (arm on **SMALL**) in both
`memory/accord/firmware/accord-return-centre-and-detent-dead-engaged.md` and
[[reference_accord_dwell_relay_polarity_settled_and_detent_likely_dead_at_handsoff]] — the latter
claiming it "settled" a cross-agent dispute with three prior independent re-derivations. **It is
backwards.**

`FUN_00036388`, assembly at the site:
```
00036432: ld.h -0x6b64[gp],r8
00036436: cmp r0,r8        \   abs() idiom -- VALIDATES the operand order below,
00036438: mov r8,r7         |  since cmp r0,r8 + bge can only mean r8 >= 0
0003643a: bge 0x00036440    |
0003643c: subr r0,r7        |
0003643e: sxh r7           /   r7 = |gp-0x6b64|
00036440: ld.h  0x718a[tp],r16   r16 = cal(0xC618A) = 1024
00036444: ld.hu 0x727e[tp],r6    r6  = cal(0xC627E) = 20
00036448: cmp r16,r7             V850 `cmp reg1,reg2` computes reg2 - reg1  => r7 - r16
0003644a: setfgt r16             r16 = 1  <=>  |gp-0x6b64| > 1024
00036458: cmp r0,r16
0003645a: be 0x00036464          if NOT greater -> DECREMENT path
00036460: add 0x1,r14            else counter++ (subject to counter <= 20)
```
Decompile agrees: `iVar11 - iVar17 < 0 == OV && iVar11 != iVar17` is signed **`>`**.
(Ghidra's overflow-safe idiom: `(a−b<0) != OV` ⟺ `a < b`; `== OV && a != b` ⟺ `a > b`.)

## Why the earlier readings went wrong, and how to avoid repeating it

The prior memory quoted a *simplified* `if (iVar11 < iVar17)` as though it were a literal decompile
line. The real decompile emits the full overflow idiom, and **the `==` vs `!=` on the OV term is the
entire meaning** — it is easy to normalise away when paraphrasing. **Never paraphrase a Ghidra signed
compare; quote the `== OV` / `!= OV` verbatim, and validate operand order against a known-semantics
idiom in the same basic block** (here, the `cmp r0,rX` + `bge` + `subr` abs pattern).

## 🛑 Consequence: the `byte7 b6` rung was WRONGLY INDICTED

Gate shut ⇒ `Y1(gp-0x6bda)=0` ⇒ `gp-0x6b64 ≡ 0` ⇒ `|0| > 1024` is FALSE ⇒ counter decays to 0 and
holds ⇒ no snap ⇒ `sVar8 = |gp-0x6b64| = 0` ⇒ **the lane contributes exactly ZERO.**

| | inverted polarity (kit's record) predicts | correct polarity predicts | V92 MEASURED |
|---|---|---|---|
| `byte7 b6` snap duty | 1.0 (default-armed) | **0.0** | **0.0000** |
| `byte4 b5` (`gp-0x6b62 ≠ 0`) | 1.0 (flat −1024 bias) | **0.0** | **0.0000** |

`memory/accord/firmware/accord-return-centre-and-detent-dead-engaged.md` indicts `byte7 b6` as a dead rung because an
855 s sustained `(gate=0, snap=0)` run contradicted `STATE.md` §E's pre-registration. **That
pre-registration was built on the inverted polarity.** Under the correct polarity the sustained run is
the *predicted steady state* — a **clean confirmation, not a null on the gate**. The rung is sound and
does not need re-flying.

Likewise the **"flat −1024 CONSTANT bias at hands-off"** conclusion in
[[reference_accord_dwell_relay_polarity_settled_and_detent_likely_dead_at_handsoff]] **does not
occur** — it was the direct consequence of the inverted polarity. The lane contributes 0, which is
exactly what `b5 = 0.0000` measured.

## The inverted polarity is in THREE places, not two

1. `memory/accord/firmware/accord-return-centre-and-detent-dead-engaged.md`
2. `docs/STATE.md` §E (the V92 pre-registration built on it)
3. **`docs/BUILD-LINEAGE.md`** — the "RECORDED, VIRGIN, UNTESTED AND NOT PROPOSED" note just after the
   "Struck LEVERS, 2026-08-09 (late)" table, which states *"+1/tick while `|gp-0x6b64| < 0xC618A`"*.
   Surfaced by team-lead 2026-08-12; **every other element of that note verified correct** (counter
   `gp-0x6a82` `ld.h`@`0x3642e`/`st.h`@`0x36472`; ceiling `0xC627E`=20 @`0x36444`; threshold
   `0xC618A`=1024 @`0x36440`; snap value = **the same cal `0xC618A`**, dual-purpose, @`0x3649e`;
   3 stores to `gp-0x6b62` @`0x36514`/`0x3652c`/`0x36544`; cals virgin).

⊕ The counter test uses the **pre-update** counter (latched before the ±1 at `0x36460`/`0x3646a`), so
the snap trails by one tick.

✅ **RESOLVED 2026-08-12 — team-lead authorised and I applied the fix to (1) and (3):**
- `memory/accord/firmware/accord-return-centre-and-detent-dead-engaged.md` — polarity corrected, the "byte7 b6 is a
  DEAD rung / null on the gate" section **replaced** with the exoneration + predicted-vs-measured
  table. Its MEASUREMENT section (duty table, `b4≡b5` on 87,317 frames) was left untouched — only the
  *interpretation* changed.
- `docs/BUILD-LINEAGE.md` — the quoted note corrected in place (`<` → `>`, plus the end-stop
  re-identification), preserving its "never edited by any build" and "no-comb" sentences verbatim.
- 🛑 `docs/STATE.md` §E was **deliberately NOT edited** — team-lead owns that file at close-out.
  Verbatim replacement text lives in `analysis-2020accord/sessions/v97/fw_return.md` §8c.

**Lesson for next time:** when a correction touches the kit's record, grep for the claim across
`docs/` AND `memory/` before reporting "two places" — this one was in three, and the third
(`BUILD-LINEAGE.md`) was the one a future session was most likely to act on.

## Related
[[reference_accord_return_centre_is_an_end_stop_cushion_not_centring]] — the re-identification from
the same pass; explains *why* the gate is shut and therefore why `gp-0x6b64 ≡ 0`.
