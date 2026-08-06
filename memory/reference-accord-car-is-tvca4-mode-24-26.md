# ★★★★★ THE CAR IS `TVCA4` — modes 24 (manual) / 26 (engaged), and the mode TOGGLES with engagement

**Settled 2026-08-05 by V73's probe, 104,061 frames.** Every "mode 10/11" statement this kit made before
this date is **wrong**, and the error was inherited from an *assumption* recorded in `BUILD-LINEAGE.md`
that `39990-TVA-A160` reads as row 2 `'TVAA1'`. It was never a measurement.

## The forcing argument — [EVIDENCE]

V73's probe reports `gp+0x63fd` in a **4-bit** field, so bit 4 is dropped: an observed *v* means the true
mode ∈ {*v*, *v*+16}.

1. The probe reads **8 when manual, 10 when engaged** — 18 transitions, all on engagement edges
   (1.02 s rise lag, 2.08 s fall lag, 99.09% lag-matched agreement).
2. Observed **8** ⇒ true ∈ {8, 24}. **Raw 8 appears in NO row** of the config table at `0xCD000`
   (present value set: `{0,1,2,3,4,5,10,11,12,13,14,15,16,17,22,23,24,25,26,27,28,29,30,31,32,33}`).
   ⇒ **manual = 24, forced.**
3. **Only row 11 `TVCA4` contains 24**, and all four mode columns come from one row ⇒
   **engaged = 26, forced.**

★ **It is the MANUAL arm that closes it.** The engaged reading of 10 alone never would have — rows
2/3/6/7 (`TVAA1`/`TVAC1`/`TVAA6`/`TVAC4`) all carry raw 10. Anyone reasoning from the engaged arm only
would have re-derived the old wrong answer.

## The row table, byte-read from `stock_fw_dump/code.bin` (`0xCD000`, stride `0x24`, modes at +0x12..+0x15)

| row | key | e012 | e013 | **e014** | **e015** |
|---|---|---|---|---|---|
| 0 | `00000` | 0 | 1 | 2 | 3 |
| 1 / 4 / 5 | `TVAA0` / `TVAA2` / `TVAA4` | 4 | 4 | 5 | 5 |
| 2 / 3 / 6 / 7 | `TVAA1` / `TVAC1` / `TVAA6` / `TVAC4` | 10 | 10 | 11 | 11 |
| 8 | `TVAA7` | 12 | 13 | 14 | 15 |
| 9 | `TVCA0` | 16 | 16 | 17 | 17 |
| 10 / 12 | `TVCA3` / `TVCA6` | 22 | 22 | 23 | 23 |
| **11** | **`TVCA4`** | **24** | 25 | **26** | 27 |
| 13 / 14 | `TWAA0` / `TWAA1` | 28 | 28 | 29 | 29 |
| 15 | `TWAA2` | 30 | 31 | 32 | 33 |

`gp-0x67f6` selects **e012 when settled-disengaged and e014 when settled-engaged**; `gp-0x67e2` picks the
A/B branch (e013/e015) and stayed at 1 all drive.

## ★ The engaged and disengaged column sets are DISJOINT — [EVIDENCE, all 16 rows]

- **ENGAGED** (e014, e015) = `{2, 3, 5, 11, 14, 15, 17, 23, 26, 27, 29, 32, 33}` — 13 modes
- **DISENGAGED** (e012, e013) = `{0, 1, 4, 10, 12, 13, 16, 22, 24, 25, 28, 30, 31}` — 13 modes
- **Collisions: NONE.**

⇒ Dosing the **engaged columns of every row** delivers whatever row is live **while leaving manual
driving byte-stock** on every mode-indexed lever. That is the V74 design, and it is robust to the row
inference being wrong. ⚠ The one edit that cannot be scoped this way is **`0xC407E`** (the friction
clamp) — a non-indexed `tp` scalar that applies in both arms.

## What this invalidates

**Every mode-indexed lever this kit ever flew was written at modes 10/11 or 0–5/12/14 and was therefore
inert:** V44, V47, V72's Levers B/C, both of V73's levers, and the **entire r24 dose** of
V69/V70/V72/V73. See [[feedback-rule7-mode-proof-or-a-bet]] for the rule this produced and
[[accord-r24-gain-b-four-pointer-arrays]] for the arrays.

🛑 **The recorded r24 "dose ladder" (0×/1×/2×/4×) never existed** — V69 and V70 delivered byte-stock
behaviour. Do not reason from it; the two memories carrying it
(`accord-v69-flew-dose-response-non-monotone`, `accord-grind1-ladder-monotone-at-peak-velocity`) were
**deleted** 2026-08-05 rather than hedged, because a hedged fictional ladder still gets re-derived from.

**The one fact worth keeping out of them:** on route `4f` (8 segs, 481.7 s) grind #1 was measured **back
at creep** — and since V69 was byte-stock, that is a **measurement of the STOCK condition**, not of a
4× dose. The same applies to V70 on route `50`. Two independent replications of stock, nothing more.

Related: [[accord-damper-is-mode-table-selected]] (the first half of this finding, which stopped one step
short), [[accord-two-lane-rule-grind2]], [[reference-accord-two-dead-zones-speed-and-rate]].
