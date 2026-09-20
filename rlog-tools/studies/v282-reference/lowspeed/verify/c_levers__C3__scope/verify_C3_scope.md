# Adversarial verification -- C3 (AccordDither gate cannot reach large low-speed snaps)

Lens: SCOPE (false-negative hunt) -- retest below 3 m/s, dwell episodes, large angle, other
speed bins for a case where the gate IS open during a large low-speed jump that C3 missed.

## What was re-run (independently, from the already-built outputs; no new reconstruction needed
since the recon step is itself the contested method -- instead I re-derived every quoted number
from the JSON the scripts already wrote, plus re-checked the gate formula and the ring number
against the fork source directly)

1. `lowspeed/c_levers/out/bigjumps.json` (38 rows, v 0.3-15 m/s, `us` mask) -- recomputed the
   17/18 and 21/38 counts, the median |out| at jump>=7, the |angle| and v ranges, directly in
   Python from the raw rows (not from the finding's prose).
2. `lowspeed/c_levers/out/reach.json` (hands-off mask, v>=2.5) -- independent dwell-jump list
   (261 dwells), filtered to jump>=7 (13 rows) as a second, differently-masked dataset.
3. `lowspeed/c_levers/out/reach_us.json` (extended mask, v 0.3-2.5-5-8-15, 4 bins) -- specifically
   pulled bin 0 (0.3-2.5 m/s, the SCOPE target below-3-m/s regime), and `gate_med_turn` /
   `gate_med_trans` (large-angle / transient frame-level gate) across all 4 bins for all 5 routes.
4. Fork source `selfdrive/controls/lib/latcontrol_vehicle_tunes.py` and `latcontrol_torque.py` at
   commit 91e902a86 -- confirmed the gate formula, `HONDA_ACCORD_DITHER_CMD_REF`, where dither is
   summed in, and the quoted hold-and-kick ring numbers, from the actual diff.

## Results

**Core counts reproduce exactly.**
- jump>=7 deg (`us` mask, n=38 total >=3deg rows): 18 rows, gate==0 in 17/18. The one exception is
  T4/route 75, v=5.38, jump=10.0 deg, gate=0.268 -- matches the finding's own caveat.
- jump>=3 deg: gate==0 in 21/38.
- Median |out| at jump>=7: 0.276 (finding says "0.28" -- matches).
- |ang| range at jump>=7: 9.78-151.6 deg (finding says "10-152" -- matches).

**Speed-range statement is imprecise but not load-bearing.** The finding states the 18 large
snaps sit at "3.6-11.6 m/s." The actual range in the data is 0.35-11.60 m/s: one row (T64/r6c,
v=0.35 m/s, jump=14.35 deg, ang=-34.5, dist from steeringPressed 1.18 s) sits well below the
stated floor. This is a real write-up inaccuracy -- but note it goes the WRONG way to be a
false negative: that row's gate is *also* 0.000, so including it only widens the range over
which the claim holds, it does not create a counter-example.

**gate_gt05 "54-74% at 2.5-8 m/s" is close but one route runs below the stated floor.**
Sec-weighting `reach.json`'s bin0 (2.5-5) and bin1 (5-8) `gate_gt05` per route: T64/6c 0.595,
T64/6d 0.676, T64B/6e 0.604, T5/76 0.485, T4/75 0.649. T5 comes in at 48.5%, below the claimed
54% floor (my weighting is an approximation -- sec-weighting two already-averaged fractions
rather than recombining at the frame level -- so this may just be a rounding/route-selection
difference in how the finding computed its range). Not disqualifying, but the range as stated
is optimistic by a few points on the low end.

**False-negative hunt found no counter-example.** Specifically:
- Below 2.5 m/s (`reach_us.json` bin 0, all 5 routes): only 11 dwell events total. The ONE large
  one (v=0.35, jump=14.35 deg) has gate_end=0.000, gate_med=0.000 -- consistent with, not
  against, C3. Every other sub-2.5-m/s dwell has a small jump (<=5.89 deg) and an open gate
  (0.49-0.97) -- exactly the "small jumps near centre, gate open" pattern C3 describes, now
  confirmed to extend down to 0.3 m/s.
- Second, independently-built dwell list (`reach.json`, hands-off mask v>=2.5): 13 dwells with
  jump>=7 deg, 12/13 gate_end=0.0 -- same exception row (T4, v=5.38) recurs. No new counter-example
  from a differently-masked pipeline.
- `gate_med_turn` (frames inside |angle_des|>=15 deg turns) across all 4 speed bins x 5 routes:
  0.0 in 17 of 20 bin/route cells, and 0.08-0.33 in the other 3 (all in bin 0, 0.3-2.5 m/s, on
  small turn_sec samples for T5 and T4) -- still far from an "open" gate, and still low speed,
  not a new regime where the effect disappears.
- `gate_med_trans` (|rate_des|>=40 deg/s) shows two outliers above 0.5 (T64/6c bin1 0.20 -- not
  high -- and bin3 0.84 on trans_sec=1.4 s, i.e. ~1 s of data; T5 bin3 0.69 on trans_sec=2.4 s)
  but these sit at 8-15 m/s, not the low-speed regime C3 is about, and are single-route,
  small-sample. They do not contradict the low-speed claim.

**The risk-quote is verified exactly.** Fork commit 91e902a86 (`common/params_keys.h` and
`selfdrive/controls/lib/latcontrol_vehicle_tunes.py`) states: "Ungated it puts a 0.15-0.41 deg
ring on the T3 hold-and-kick test" and the test file spells it out as 0.41 / 0.29 / 0.15 deg at
8 / 19 / 26 m/s. C3's "0.41 deg at 8 m/s" is exact, correctly marked BELIEF (a bench simulation,
never flown), and correctly attributed. The gate formula in C3's method
(`clip(1 - |out|/0.15, 0, 1)`) matches `get_honda_accord_dither_gate` byte-for-byte
(`HONDA_ACCORD_DITHER_CMD_REF` = 0.15, same clip). Confirmed AccordDither is 0.0 (off) by
default and never flown, and the dither is summed in strictly after the PID/hysteresis/rate
loop/observer, applied to `output_torque` (same quantity as the reconstructed `D['out']`, up to
sign, and the gate takes abs()). One thing C3's method does NOT model: the dither is also fully
suppressed whenever the Honda rate limiter is active (`steer_limited_by_safety`), a second,
separate gate not folded into the reconstructed `gate` column. This can only make the true dither
reach at big jumps SMALLER than what C3 reports (rate-limiter activity clusters exactly at the
release/jump instants), so it reinforces the "gate is closed at large jumps" conclusion rather
than weakening it.

## Verdict

Not refuted. The false-negative hunt (below 3 m/s down to 0.3 m/s, a second independently-masked
dwell dataset, frame-level turn/transient gate stats across all 4 speed bins, and the fork source
itself) found no case where the dither gate is open during a large low-speed snap. The core counts
(17/18, 21/38, magnitude, angle range) reproduce exactly from the underlying JSON, and the risk
quote is verified byte-exact against the source commit. Two small write-up imprecisions were found
(the stated 3.6-11.6 m/s range should be ~0.3-11.6 m/s, and the 54-74% gate>0.5 range runs a few
points low on one route by my recombination) -- neither changes the substance and the first, if
corrected, only strengthens the claim.
