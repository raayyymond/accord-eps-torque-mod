#!/usr/bin/env bash
# Full re-run of the e4_chain decomposition on every route, one route at a time (RAM: ~2.5 GB shared).
# extract_chain.py must have been run first (MAXSEGS=20 for the 62-segment V282 route 0000006c--2bc842dbac).
cd "$(dirname "$0")"
V293="0000006c--68c6e94b17 0000006d--05e83bb04f 0000006e--6ca3e014fd 00000076--d0b7ea7e4d 00000075--6c8687d5bd"
V282="00000064--ce6b0b0ebb 0000006c--2bc842dbac"
for r in $V293 $V282; do
  python chain_software.py $r > out/log_chain_$r.txt 2>&1
  python chain_timing.py $r > out/log_timing_$r.txt 2>&1
  python sensor_lags.py $r > out/log_sensor_$r.txt 2>&1
done
for r in $V293; do
  python controls_tap_xcorr.py $r > out/log_controls_$r.txt 2>&1
done
echo ALLDONE
