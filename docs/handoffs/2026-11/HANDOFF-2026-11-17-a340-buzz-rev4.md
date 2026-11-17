# HANDOFF 2026-11-17 — A340: why V300-A340 REV 3 buzzed on a user's car, and REV 4

**Ask (operator):** a user's report on the "A340 version of PTM" — "fantastic", plus "a slight buzz on return to center movements between 11
and 1, even without starpilot engaged" — with a route on the modded firmware and, later, a route on stock; then "act autonomously to solve
the issue".

**Result.** The buzz is measured, is caused by the build, and its cause is traced to one porting error. **V300-A340 REV 4** is BUILT, NOT
FLOWN: image `e73278a1…f2c6`, rwd `4bc63270…bcdc`, F181 `39990-TVA,A34D` = REV 3 with the 13 DampAxis bytes at STOCK and the letter C → D.
Nothing was flashed or sent. Page https://claude.ai/artifact/RKPUALFvKXPthPGbmuj2a6.

**Measured (EVIDENCE).** Routes `27da1a2b0cde4a09|00000055--a39019e01a` (REV 3, `,A34C`, 23 segs) and `…|0000005d--ff985a4e01` (stock, same
car, 7 segs); control = 10 A160 V300 routes. Metric BZ = 0x14A wheel rate, 10 Hz high-pass, 0.32 s rms, deg/s; buzz = BZ > 4; cell: v > 8
m/s, wheel still, |ang| < 10°, |tq| < 800. Engaged 8.91 / 88.9 % (REV 3) vs 0.81 / 0.6 % (stock) vs ≤ 0.63 / ≤ 0.4 % (A160). Manual 48.1 % vs
0.1 % vs ≤ 0.2 %. Manual return to centre within 30°: 94 % vs 2.8 % vs 1.0 %. Manual buzz: request 0 and cmd 0 throughout, 7 runs before the
first engagement. Kick-started, constant amplitude, firm grip suppresses it. 12–22 Hz as sampled; true frequency unresolved (BELIEF 70–130 Hz).

**Cause.** The port wrote the tripled DampAxis rows "at the same addresses" as A160. The lane's consumer picks its record by a mode byte that
comes from the car's coded chassis key (table `0xCD000`, columns [manual, manual, engaged, engaged]). On A160 records 26/27 are the operator
car's (TVCA4) engaged modes. On A340 they are keys TWAA0/TWAA1's manual AND engaged modes. The user's car is a 2.0T (all ECUs TWA) — BELIEF it
is coded TWAA0/1. So it ran ×3/×3/×8.1 acceleration feedback in manual, hands on, which no car had flown; the lane's own loop (two lags, 2–3 ms
delay, ±511 clamp) limit-cycles. With the request off no other REV 3 edit acts dynamically (audit of 842 B).

**Decision and why not a dose.** REV 4 returns the lane to stock for every key. Intermediate doses were scored and rejected: the stock margin
of the lane's own loop is only bounded to (0, 7.5 dB], and on this key the rows act in manual. Engaged-only ×3 (the A160 intent) is known to
buzz on this car (engaged duty 89 %).

**Gates.** GATE 1 n/a (no new RAM, no code byte vs REV 3). GATE 2 PASS-WITH-DEFECTS (`studies/a340_buzz/GATE2-A340-STOCK-LANE.md`): one
failing member (J_lo, 3–8 m/s, +5.4 dB at 11 Hz), central A340 estimate GM ≥ 18.3 dB. Adversarial lenses A/B/C all PASS_WITH_DEFECTS
(`studies/a340_buzz/adv{A,B,C}/LENS-*-REPORT.md`). Roll-call done, all six agents stopped.

**Risk the operator should relay.** Authority unchanged (rail 2472 = 5.49× stock peak). No car has flown the angle loop on the stock lane. If
the weak-damping corner is real: engaged only, ≤ ~18 km/h, hands light, a 7–11 Hz wheel shudder after a correction. First engaged test at
5–20 km/h, hands ready; revert if it sustains 2 s.

**Readouts for the next route.** Check `,A34D` in carParams. BZ cell: clean = median < 1.0 and < 2 % above 4. Low-speed corner: 8–20 Hz band,
1 s rms, engaged, not pressed, 1–8 m/s: clean p50 ≤ 1.5 / p90 ≤ 3.0; REV 3 was 5.83 / 8.61. Scripts: `rlog-tools/studies/a340_buzz/`
(`a340_buzz_extract_par.py` → cache, `a340_buzz_score.py`).

**Files changed.** `builds/a340/build_v300_a340.py` (REV 4; asserts the key table and that all 34 records are stock), `build_stock_a340.py`
(accept list + `,A34D`; revert rwd sha `51be7dd8…`, was `0965a24c…`). `accord-firmwares`: + REV 4 image and rwd, revert rwd updated, REV 3 rwd
removed (image kept). STATE A340 box, lineage PART6, memory.

**Open.** The car's coded key (ask the user for the trim, or read `gp+0x63fd` if a probe ever flies). `FUN_0002C0FC` untraced. The fork has
no `,A34D` test case (predicate accepts it). 🛑 A160 V300 on any A160 key other than TVCA4 runs stock rows + α2 14, never scored — matters if
A160 V300 is handed to other owners. The 2× A340 rwd accepts neither `,A34C` nor `,A34D` (go via the stock revert).
