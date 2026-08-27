---
name: reference_accord_c62ea_disabled_since_v53_does_not_explain_lowspeed_dropoff
description: 0xC62EA (the low-speed steer-lockout LO bound) = 0 on V106 AND V107, confirmed by a fresh byte read -- it has been zeroed (disabled) since V53 per BUILD-LINEAGE.md, ~50+ builds, NOT still 320 as an older memory describes. It therefore CANNOT explain the operator's V107 <=8-10km/h grinding drop-off (authority isn't gated there any more). Best-supported alternative: gp-0x6b26's own Y-table is LARGEST (most authority) at v=0, so the drop-off is not an authority/gain effect at all -- it is more likely an EXCITATION effect, matching the kit's separate wheel/steering-RATE-axis finding for the older ratchet.
metadata:
  type: reference
---

# `0xC62EA` re-checked for V107 — disabled since V53, refutes the low-speed-lockout explanation for the new drop-off

2026-08-26, `hfmech` task. The team-lead brief's own candidate for the operator's "<=5-6mph grinding
drops off completely" was `cal(0xC62EA)=320ct~5km/h` (the low-speed steer lockout documented in
[[accord-low-speed-lockout-window-c62ea]], project memory, dated 2026-07-24). Checked fresh rather than
assumed current.

## Fresh byte read [EVIDENCE]
`0xC62EA`: stock=320, **V106=0, V107=0**. Cross-checked against `docs/BUILD-LINEAGE.md:1284`:
**`v53 | FOURFRAME2 byte-for-byte + 0xC62EA 320→0`** — confirmed frozen at 0 on every build since,
~50+ builds through V107. `[[accord-low-speed-lockout-window-c62ea]]`'s "cal 0xC62EA=320" describes the
mechanism as understood BEFORE it was implemented as a lever (that memory's own "Fix surface" section
proposes lowering it as the clean next step) — it was current when written, not stale in what it
documents, but citing "320" as V106/V107's live value would be wrong; the memory itself doesn't claim
that, a reader has to know to re-check.

## 🛑 Consequence — refutes the brief's own hypothesis for the drop-off
With `0xC62EA=0`, the window compare `speed >= cal(0xC62EA)` becomes `speed >= 0`, always true ⇒ **the
low-speed steer lockout has been fully bypassed since V53.** It cannot be gating anything on V107 —
LKAS authority is NOT blocked below ~5km/h any more. `cal(0xC6316)=640≈10km/h` (also byte-confirmed
unchanged stock/V106/V107) does not fill the gap either: per
[[reference-accord-rate-limits-c6194-partition-and-c520c-ceiling-scale]] it only SKIPS a slew-rate
limiter below ~10km/h, making the governor MORE responsive there, not more restrictive.

## Best-supported alternative [BELIEF, synthesis]
`gp-0x6b26`'s own Y-table (modes 26/27) is **-29490 at v=0 — its LARGEST (most-authority) point**,
falling toward -16000 by 90km/h (V107). A pure authority/gain story therefore predicts the mechanism
should be STRONGEST at creep, not absent — the opposite of what's observed. This points away from any
gain/authority gate and toward the EXCITATION side: the kit's own separate finding that the ~7.8Hz
ratchet's real axis is STEERING/WHEEL RATE, not vehicle speed (engaged/manual contrast 1.16× at 2°/s →
3.94× [2.19,6.70] at 100°/s, per `MEMORY.md`'s own index line for the — currently unlocatable as a
standalone file, possibly merged/renamed in the 2026-08-26 repo reorg — "ratchet-axis-is-wheel-rate"
finding) generalizes cleanly: low-speed creep/parking maneuvering involves inherently slow, low-rate
steering corrections (both driver and LKAS), so there is little high-rate excitation to drive ANY of
the mechanisms in this family (7.8Hz ratchet, the 74.5-500Hz sector this session characterizes)
regardless of how much Y-table authority is technically available. Symmetrically explains "absent at
highway straight" (small LKAS corrections, low rate) and "returns in a hard turn at 50mph" (large fast
input restores the rate content) — the SAME axis explains all three of the operator's speed-conditional
observations without needing any new gate.

## Not ruled out — an independently-flagged, still-open second gate
[[accord-low-speed-lockout-window-c62ea]] itself flags a **second, separate** low-speed gate: `0xC62EE`
(=320, same 4.995km/h threshold) feeding `gp-0x680c`, role **NOT ESTABLISHED**, living in a Ghidra
**unanalyzed region** (`0x2d5xx-0x2dbxx`). Not independently re-examined this session (time-boxed out of
scope for this trace) — flagged here as a genuine open item rather than silently dropped. Next step:
`reanalyze` that region or `get_xrefs_to` its 5 known reader addresses to recover function boundaries.

## Related
[[accord-low-speed-lockout-window-c62ea]] (the memory this corrects for currency, not for correctness at
time of writing), [[reference_accord_gp6b26_hf_sector_crossing_74hz_and_v107_railing]] (the Y-table
values this reasons from).
