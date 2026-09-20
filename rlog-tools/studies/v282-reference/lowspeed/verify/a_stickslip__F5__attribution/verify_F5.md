# Adversarial verification of F5 (stick-slip jump size, matched vs headline 12.6°)

## What I checked independently

Re-derived every checkable number in F5 directly from `lowspeed/a_stickslip/out/ss_analyze.json`,
`out_dw12/ss_analyze.json`, and the raw episode arrays via `ss_load.load_all()` (not from F5's own
prose) — did not just re-read the JSON F5 cites, re-ran the arithmetic myself against the raw `EP`
records.

1. **Matched slip ratios (dw=20, primary).** `R['matched']['TORQUE_ALL|2-8']['slip_ratio_geo']` =
   `0.9467 [0.838, 1.059]`; `TORQUE_ALL|8-15` = `1.1067 [1.000, 1.208]`. Matches F5's "0.95 [0.84,1.06]"
   and "1.11 [1.00,1.21]" to the stated precision. **CONFIRMED.**
2. **j30 (300 ms jump) p90.** `TORQUE_ALL|2-8`: 1.772 vs 1.393 deg → F5's "1.8 vs 1.4". `8-15`: 1.613 vs
   1.37 → F5's "1.6 vs 1.4". **CONFIRMED.**
3. **dw=12 sensitivity.** `out_dw12/ss_analyze.json['matched']['TORQUE_ALL|2-8']['j30_p90']` = torque
   2.804, V282 1.514 → F5's "2.8 vs 1.5 deg below 8 m/s" at the 0.12 s threshold. **CONFIRMED exactly.**
4. **Episode counts.** `len(EP)==978`, torque subset `TQ.sum()==511` (matches per-band n: 145 at 2-8 +
   366 at 8-15 = 511). **CONFIRMED exactly** (F5: "Of 978 episodes, 511 are on the torque routes").
5. **Large-angle rarity.** Recomputed directly from `EP`: torque episodes at v<8, 15≤|angle|<45 → **n=7**,
   slip p50 = **14.23 deg**. Matches F5 exactly ("only 7 torque episodes below 8 m/s are at 15-45 deg
   (slip p50 14 deg)").
6. **Near-centre median.** Torque episodes <8 m/s: median |angle| = 1.94 deg. Matches "|angle| p50 about
   2 deg" exactly.
7. **Origin of the "12.6 vs 1.5" headline.** Traced independently (F5 itself marks this as unverified
   BELIEF — "I did not re-run the s4 extractor"). Found it: `s4_texture/s4_events.json`,
   `T64['dj_per100deg_0_8']['jump_p90'] = 12.557` (**n=26**, T64 route-group only, unmatched to any V282
   condition) vs `V282['dj_per100deg_0_8']['jump_p90'] = 1.460` (n=98). This is an EXACT match to the
   REPORT.md line 51 numbers, and it is: (a) T64 only — not T64B (3.03), T5 (3.65), T4 (2.94), all far
   below 12.6 — i.e. not representative of the torque-mode class as a whole; (b) an unmatched p90 off
   only 26 raw episodes (a handful of points set the p90); (c) not controlled for speed/angle/demand-rate
   mix between the torque and V282 populations. **F5's BELIEF is correct and now has EVIDENCE behind
   it** — I am upgrading this from BELIEF to EVIDENCE in my verification (small-n, single-route,
   unmatched artifact, not a reproducible class-level effect).

## Where I tried to break it — and what I found

**The matched comparison silently drops the torque-only large-angle population.** Re-ran the
nearest-neighbour matcher myself (2-8 m/s band): 133/145 torque episodes matched, **12 unmatched**
(distance > 1.5, i.e. no V282 episode exists at comparable speed/angle/demand-rate). The unmatched set
is exactly the large-slip tail: angles up to 39.6°, slip up to 29.0° (unmatched slip values: 14.2, 1.2,
5.0, 1.8, 19.0, 1.3, 4.2, **29.0**, 23.8, 2.5, 15.9, 0.3). The matched set's angle p90 is only 7.1°
(max 20.3°). **V282 has essentially no comparable low-speed, large-angle episodes to match against — so
the "about equal" verdict is a statement about the typical/near-centre population, not about the rare
but large torque-only excess-jump population**, which is exactly the population most likely to register
to the operator as a "snap."

F5's own text does disclose this ("only 7 torque episodes below 8 m/s are at 15-45 deg, slip p50 14
deg") with correct numbers, so it is not hidden — but the finding's framing ("matched jump sizes are
about equal... the 12.6 deg figure is not reproduced") risks being read as debunking the earlier
headline outright. A more accurate reading: **both are true and describe different populations** — the
bulk of low-speed dwell-then-jump episodes (near centre, small angle) jump about the same size as V282's;
a small excess population of large, torque-mode-only jumps (up to 29-40°) exists with no V282 analogue,
consistent with the already-flagged "self-centring has no V282 reference" gap (STATE.md / REPORT.md
note 3) and with route-70/75's spring+Coulomb-friction plant model (bigger stored error → bigger snap on
release). This nuance does not contradict any of F5's numbers — it is a caveat on how the "12.6 deg not
reproduced" framing should be read, not a refutation of the arithmetic.

## Consistency with route-70/75 findings

F5's mechanism (pause ends when accumulated command crosses a friction band, then a jump) is the same
dwell/stick-slip class already established for route 70 (spring + Coulomb friction, F≈0.011-0.024) and
the rev-4 hard-turn-jerk note (lightly damped 2-2.7 Hz wheel mode) — F5 does not contradict either; it
refines the SIZE claim for the matched/typical case while leaving the large-angle tail (which is closer
in spirit to the original 12.6° number) as a distinct, separately-quantified population. Consistent, not
competing, with prior notes.

## Independently re-derived numbers (not in F5's JSON, cross-checked as spot audit)

`ss_ratios.json` p50 ratios (torque/V282, cluster bootstrap): dwell_s 2-8|all = 1.315 [1.055,1.71];
gap_model_deg 2-8|all = 2.305 (stream summary's "2.3x further behind" — exact match); catch30_deg
2-8|all = 1.822, 8-15|all = 1.861 (stream summary's "1.8-2.0x" — matches); peak_rate_dps 2-8|all = 1.498,
8-15|all = 1.787 (stream summary's "1.5-2.1x" band — matches, aa>=5|8-15 = 1.988 near the top of range).
These numbers, quoted in the broader stream summary around F5, check out too.

## Verdict

F5's stated numeric claims (the matched slip/j30 ratios, the dw12 sensitivity re-run, the episode
counts, the near-centre median, the 7-episode large-angle subset) are **all independently reproduced
exactly** from the raw episode data and the cited JSON outputs. The origin of the 12.6° headline is
correctly diagnosed and now confirmed (small-n, single-route, unmatched artifact). **Not refuted** on
the object level. One nuance for the ATTRIBUTION lens: the "about equal" verdict applies to the matched
(typical, near-centre) population only; a genuinely torque-mode-only excess-jump population (up to
29-40°, no V282 analogue) exists and is separately, correctly quantified inside F5's own text — future
framing should carry both halves together rather than reading the second as debunking the first.
