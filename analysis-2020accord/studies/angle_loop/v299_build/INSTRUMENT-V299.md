# INSTRUMENT-V299: the drive read, extended for drive 2 (V299, config A)

**Status:** analysis only. Nothing was built, flashed, sent or committed. The fork, the firmware and the golden model are untouched, and so are STATE, the lineage and git.
**Authors:** the INSTRUMENT subagent of the V299 round (first version), the ALIGN subagent (second), then the FIXER subagent (this revision: the re-verifier's rejection, §FIX), 2026-10-02.
**Criteria (binding):** the drive card `docs/scoring/DRIVE-CARD-V299-drive2-2026-10-02.md` and `docs/specs/design/v299/DESIGN-V299-SYNTHESIS-rev3-2026-10-02.md` §6–§7. The first version was written against rev 2; a verifier rejected it. This revision resolves every rejected item by name (§ALIGN below). Classifier interruptions in this revision: 0.

**EVIDENCE** means measured on a route's wire or caches, read from source, or run in this session (the wall time is given). **BELIEF** means a model or the spec's sims.

---

## FIX: the re-verifier's rejection and the orchestrator's rulings, item by item (FIXER, 2026-10-02)

The re-verifier rejected the ALIGN revision on two defects and six minor items. The orchestrator ruled on the snap clause and on the order of the fit floor.

- Every item below is fixed in `rlog-tools/studies/angle_loop/drive_read_v299.py`.
- Every fix has a selftest control. The selftest now runs **28 controls, ALL PASS, in 17.4 s wall**. The log is `_scratch/angle_loop/drive-read/v299_selftest.txt`.
- Classifier interruptions in this revision: 0.

| # | item | fix | where | control (selftest) |
|---|---|---|---|---|
| D1 | **Any wire carrying route 79's PREFIX could overwrite the positive-control cache.** The verifier's `vc_synth_wire.py` did it. | The cache is keyed on a sha256 of the canonical r79 wire cache's raw 0x1AB bytes, plus the F1 / hands-off thresholds. The file is `analysis-2020accord/_scratch/cache/v280/r79_a1f5d2_al.npz` (`t1ab`, `b0`, `b1`; sha `11ef31ebf63e…`). The cache is written **only** when the scored tap hashes to that file's tap, decoded the reader's way (dejittered `t1ab`, 8·s10). A match on the prefix alone prints the cached control with a note and writes nothing. With no cache, the control is recomputed from the canonical file by its fixed path, with the FR/C20 caches forced to it, and the loaded tap is re-checked against the hash first. The reference tap hash is memoised as `refs/r79_tapsha_<wire sha16>.json`, because the dejitter costs 0.78 s. | `r79_identity`, `tap_is_r79`, `_posctrl_path`, `positive_control` | **PC1:** a synthetic r79-prefixed wire, not flagged as a selftest, with tap := the V299 replay + noise (6B on it: V299). It leaves the cache byte-identical and prints V298 18/18. With the cache deleted, the control is recomputed from the canonical wire (V298 18/18). The real tap hashes to the wire; the synthetic does not. **EVIDENCE, the verifier's own script re-run:** `vc_synth_wire.py` (4 reads, 23.0 s) left the cache's sha256 `94a96622…` unchanged. Each synthetic read prints "carries route 79's prefix but NOT its tap (hash mismatch): not cached, not used". |
| D2 | **verdict() checked the fit floor before "V299 does not beat V298".** A card-literal F1 FAIL could therefore read NOT TESTABLE. | The ruled order, in one function. (a) V299 does not beat V298 (pooled dR² < +0.05, or < 2/3 of the windows): **FAIL**. (b) Otherwise, the winning replay's pooled R² < 0.5 (the fit floor, RATIFIED): the replay clause is **NOT TESTABLE**, with a "!!! LOUD" note. (c) Otherwise the clause passes. 6B prints it as "F1 REPLAY CLAUSE", and the verdict uses it. | `f1_decide`, `f1_replay_clause`, `verdict` | **F1R** (5 synthetic cases): dR² +0.02 at 15/18 → FAIL; +0.30 at 10/18 → FAIL; −1.0 with a poor fit → FAIL (the defect's case); +0.20 at 18/18 with R² 0.30 → NOT TESTABLE (loud); +0.20 at 18/18 with R² 0.80 → PASS. **F1Rr** (real replays): unrelated noise → FAIL (it read NOT TESTABLE before); tap := V299 replay → PASS; real r79 → FAIL. |
| R1 | **The snap ruling.** Clip-bound setpoint steps are not override snaps. The allowance is the literal 1.2°/frame on every config. Print both counts. | Only non-clip-bound snaps > 1.2°/frame toward the wheel fail F1. `cap` is fixed at 1.2; it was max(1.2, MaxRate/100). 6A and the F1 row print both counts and the AccordAngleMaxRate in force. | `o1_snaps`, `f1_snap_clause` | **A2:** one clip-bound snap and one not → the clause FAILS on the non-clip one. **A3:** a wire whose only snap is clip-bound → PASS (printed "1 clip-bound, not counted"). With MaxRate 250 the allowance is still 1.2, and a 2° non-clip step counts. |
| m1 | cap_read filtered the top-20 overshoot cut. D3 means 60–90° turn-ins at 8–10 m/s. | `turnins()` returns the full list (`_all`), which is popped from the JSON after use. The D3 gate takes 60 ≤ size ≤ 90 and 8 ≤ v ≤ 10 from it. 6G prints the "D3 gate input". | `turnins`, `cap_read`, `THR2.cap_d3_min/max` | **G2:** 24 turn-ins. The one D3 (70°, 9 m/s, overshoot 2.0) sits outside the top-20 cut → gate n 1, MET. A 40° turn at 9 m/s and a 70° at 7 m/s are not D3. The top-20 list alone sees none. |
| m2 | F6b's enrichment counted both edges of \|w\| > 1229. | The 1229 level counts ONSETS (rising edges) only. 300 / 512 stay crossings (both edges, F6). The reference caches (r6c / r39) are upgraded once (`enrich_1229: onsets`). | `enrichment(onset_levels=(1229,))`, `ref_stutter` | **C4:** surges planted at the falling edges → onsets ×0.00 (the both-edge count reads ×inf); at the rising edges → ×inf. |
| m3 | The F4 overshoot window was cut where the setpoint moved again. | The window is the full 3 s after θ first reaches 90 %. A setpoint move inside it is FLAGGED (`sp_moved`, "SP-MOVED"). Only a disengage truncates it, and that is flagged too. | `turnins` | **E2:** a 50° turn-in whose setpoint moves 2° inside the window, with a 10° bump at +2.0 s → overshoot 8.00, SP-MOVED, F4a fires. The pre-edit code, run on the same wire, reads 0.00 and does not fire. **E1** is unchanged. |
| m4 | F8's canValid drop was counted only on latActive frames. | It is now counted on every angle-mode frame: carParams.steerControlType == angle AND an A16x angle firmware (both hold per route), from the first valid frame. Every route starts with 2–4 boot rows before the first CAN parse (r79 2, r71 4), and counting those would fire F8 on every route. **That exclusion is my interpretation; see open item F2.** A drop now fails F8 on its own, even when the bar-equality clauses are NOT TESTABLE. | `angle_mode`, `_canvalid`, `bar_check`, `verdict` | Route reads: r79, 0 drops on 121 381 angle-mode frames (2 boot rows); r71b, not angle mode (torque, A160). |
| m5 | Print the release-instant gap per release in 6D. | θ − θsp at the release frame, on every scored release. The 25-row cap is removed, and 6D prints them all. | `releases`, `report` | **D4** (gap 3.00) |
| m6 | The hand side = the mean of −bar over the episode's LAST 0.3 s (before the first \|wire\| < 150 crossing), not the 0.3 s before the release frame. | The window ends at the episode's last \|wire\| > 300 frame before the release, so the 300 → 150 decay is not in it. | `releases` | **D4:** −1500 for 1 s, +400 for 0.1 s, then a +200 decay for 0.5 s → side +1. The 0.3 s before the release frame would say −1. |
| doc | Card §4 F1, spec §7.2 F1 and §6.1: the positive-control figures. Spec §2.2 and the F8 row: the stale bit. | Card F1 row: "V298 wins 18/18 hands-off windows, pooled dR² −1.013", plus one sentence for the clip-bound ruling and one for the order of the fit floor. Spec §6.1 item 1 and §7.2 F1: the same figures. Spec §2.2 F8 row: **256** · EPS-torque stale-or-bad (as `c6452361e` emits it; 8 reserved). Spec §7.2 F8 row and card F8 row: "bit 8 = value 256". Line endings preserved (spec CRLF, card LF). | the two documents | — |

**Sections 0–5 are byte-identical (EVIDENCE).**
- Pre-edit warm reads were made first (`_scratch/out/fix299/pre/`).
- Every post-edit read was diffed against them with `_scratch/out/fix299/diff05.py`, with RUNTIME excluded.
- The reads compared: route 79 and r71b_v294, warm (`post/`, `final/`) and cold (`cold/`).
- Sections 0–5 have **0 diff lines** (93/93 lines). The JSON outside `v299` has **0 differences**.
- With the replay cache aside, all 16 regenerated replay files are **bit-identical** to the pre-existing ones.

**What moved in section 6 on the controls (EVIDENCE):**
- **Route 79.** The verdict is unchanged: **FAIL F1, F6**.
  - F1 still FAILS, now on "does not beat" by branch (a).
  - All 448 snaps are non-clip-bound (0 clip-bound), so all 448 still count.
  - F6b's 1229 enrichment on onsets is ×1.31 (×1.18 on both edges).
  - canValid: 0 drops on 121 381 angle-mode frames.
- **r71b_v294.**
  - V299 "beats" V298 (dR² +1.285, 18 of 23 windows), but its pooled R² is −54.6. So the replay clause is **NOT TESTABLE**, loudly (branch b).
  - F1 still FAILS on carFw A160 and the absent status.

**Runtime (EVIDENCE, this machine, today, final code):**

| run | wall | the read's RUNTIME line |
|---|---|---|
| route 79 cold (replay cache aside) ×3 | **15.2 / 14.3 / 14.2 s** | 14.9 / 14.0 / 13.9 s (8 replays 7.3 / 6.6 / 6.6 s) |
| route 79 cold, PRE-EDIT code, same session (A/B) | 14.7 s | 14.4 s (replays 6.8 s) |
| route 79 warm | **7.9 s** | 7.6 s (pre-edit warm today 8.5 s) |
| r71b_v294 cold ×3 | **15.9 / 16.2 / 15.8 s** | 15.6 / 15.9 / 15.5 s (replays 8.3 / 8.5 / 8.1 s) |
| r71b_v294 cold, PRE-EDIT code (A/B) | 15.3 s | 15.0 s |
| r71b_v294 warm | **7.6 s** | 7.4 s |
| `--selftest` (28 controls) | **17.4 s** | — |

The cold reads are about 2 s slower than the ALIGN session's 12.1 / 13.3 s. This is the machine today, not this revision:
- The pre-edit code, run cold in the same session, is just as slow (14.7 / 15.3 s).
- The extra time is in the lane replays, which this revision did not touch: 6.6–8.5 s now against 5.8–7.1 s then.
- The V299 blocks cost 1.1–1.2 s cold and 0.27–0.34 s warm.

### FIX: open items for the orchestrator

- **F1.** Spec §0 (line "It discriminates … 23/25") and §4 (the `r3_fastlane_v299.py` counterfactual row, "V298 wins 23/25, dR² p50 +0.450") still carry the earlier script's figures. They are records of a different frame set, and they are left as written: the brief named only §6.1 and §7.2. The spec's §7.2 F1 row does not carry the two rulings either; only the card's row does, as briefed.
- **F2.** The canValid "angle-mode frame" set starts at the first valid frame, so the 2–4 boot rows every route begins with are excluded. Ratify this or overrule it. Counted literally, F8 fires on every route.
- **F3.** The hand-side change (m6) differs from the old window only when the 300 → 150 decay carries the opposite sign to the hand's last 0.3 s. That case is constructible (D4) but rare. No scored release on r79 or r71b changed side.

---

## ALIGN: the verifier's rejection, item by item

| # | item | resolution | where (`drive_read_v299.py`) | control |
|---|---|---|---|---|
| 1 | **F3 bars by speed band**; score 5–8 m/s too; release edge; re-grab excluded | bars 12° at 5–11 m/s, 9° at 11–15, 8° at ≥ 15, 5° on a straight (\|θsp\| < 3° across the window, any speed); nothing scored below 5 m/s off a straight. Release = the first \|wire\| < 150 after ≥ 0.5 s at \|wire\| > 300 (a dip to 150–300 is the same episode); a re-grab (\|wire\| > 300 within 1.5 s) is excluded and counted | `f3_bar`, `releases`, `THR2.f3_bands` | D1: a 10° swing at 8 m/s does not fire (bar 12), at 12 m/s fires (bar 9); 6° on a straight fires (bar 5); a re-grab is excluded and its own later release scored; a dip to 200 is one episode |
| 2 | **F4 split into F4a / F4b / F4c**, 15 % clause deleted, overshoot vs θsp_final in the 3 s after 90 % | the §7.1 turn-in: an excursion ≥ 20° between two settled runs (\|dθsp/dt\| < 5 deg/s for ≥ 1 s, rate = centred 0.2-s difference because 0xE4's 0.1° LSB makes a one-frame slope 10 deg/s per count). Overshoot = max (θ − θsp_final)·sign over the 3 s after θ first reaches 90 % of the excursion, cut where the setpoint moves again. F4a ≥ 45° at ≤ 10 m/s > 6°; F4b 20–45° at ≤ 4.5 m/s > 8.5°; F4c 20–45° at 4.5–10 m/s > 6°. Returns toward centre are printed, not scored | `turnins`, `f4_class` | E1: six turns read exactly as planted (F4a 8.0 fires, 1.0 not; F4b 7.5 not, 9.0 fires; F4c 7.0 fires; 30° at 12 m/s has no clause) |
| 3 | **F1** = pooled dR² ≥ +0.05 AND V299 wins ≥ 2/3 of the 30-s hands-off windows with ≥ 200 tap frames | pooled R² and the windows both on §7.1 hands-off settled frames (`score_replay_mask`); a window counts with ≥ 200 hands-off tap frames; the manoeuvre-window count is printed as information only | `rule_identity` | B2: tap := V299 replay + noise → V299 18/18; := V298 replay → V298 18/18; the real tap → V298 18/18 |
| 4 | **accordAngleStatus on ≥ 99 % of latActive frames, a fraction** | presence = the share of latActive carState rows with a starpilotCarState row within 5 ms; a schema without the field reads 0 % | `attribution` (`status_present`) | A1: rows on 98.5 % → 0.9875, fires; all → 1.0 |
| 5 | **O1-snap = \|Δθsp\| > 1.2° in one frame toward the wheel**, outside the first frame and the rising edge | on the fork's carOutput setpoint: both frames latActive (so the rising edge and the first frame never count), toward = sign(Δθsp) = sign(θ − θsp) at the step's start, the allowance scales with the 10-ms frames a step spans (a dropped log row is not a snap), allowance = max(1.2, MaxRate/100). Each snap is tagged clip-bound or not (see open item 1). The old limiter-reconstruction check is kept as information | `o1_snaps` | A2: a 3° step toward the wheel fires; away, a 1.2°/frame ramp, a 2.4° step over a dropped row, and a 5° step at the rising edge do not; a step behind a wheel past the clip is tagged clip-bound |
| 6 | **positive control prints what the read measures** | `positive_control`: live on route 79, else from `SCR/refs/r79_v299_posctrl_<hash>.json` (keyed on the F1 and hands-off thresholds; computed once when missing; a selftest tap is never cached) | `positive_control` | B2 checks that the printed control equals the read's own r79 result |
| 7 | **F5 after ANY release, at ≥ 5 m/s, with the spec's edge** | (θsp − θ)·sign(θsp) at release + 1.5 s > 4° (\|θ − θsp\| when \|θsp\| < 1°, where "toward centre" has no sign); needs the full 1.5-s window | `releases` | D2: a firm 1500-word release 5° short fires at 6 m/s; at 4 m/s it is not scored |
| 8 | **F6 second clause scored** | F6 fires on trains ≥ 4.7/min, OR in-turn 4–8 Hz rms ≥ 7.09 deg/s at 5–10 m/s, OR 300\|512 enrichment ≥ 2× | `score_f6` | F6: a 6 Hz wobble of 14 deg/s (rms 9.90) fires on that clause alone; 3 deg/s (2.12) passes |
| 9 | **the cap null sentence per the card / §6.2** | holds = hands-off, 8–12.5 m/s, \|a_lat\| ≥ 2, ≥ 3 s; per hold over the LAST second: the replayed V299 I at the 6144 bound (bound active AND the bound in force = 6144) on ≥ 80 %, and the 0.5 Hz-LP \|θsp − θ\| > 3°. Three-way sentence: ≥ 50 % both → ms_free-like, 7168 licensed for RE-SCORING only (with drive 2's 8–10 m/s turn-in overshoot printed against < 3°); ≥ 50 % bound → 6144 suffices; else the cap is not the binder | `cap_read`, `bound_active` | G1: all three sentences, and a 2.5-s hold is not a hold |
| 10 | **PRED strings → rev 3** | F3 heavy 9.7–10.4 / nominal 4.4–6.1 (5–10 m/s), 7.9/5.4 at 12.5, 6.5/4.8 at 15; F5 ≤ 2.0 / 3.2 at 12.5 / 2.6 at 15; F4a ≤ 5.2; F4b 7.0 heavy / 4.2 nominal; F4c ≤ 4.6; cap 3–7°; F7 97–130 ms; F9 ≤ 207; F7b 550–1560 ms | `PRED` | — |
| 11 | **the release-lurch null sentence** | light (peak \|bar\| < 1229, unpressed) OUTWARD releases at 5–10 m/s: max ≤ 6.1 nominal-like; 6.5–12 heavy member (observation); > 12 F3 fires; 6.1–6.5 "between the members" | `lurch_sentence` | D3: swings 5 / 9 / 13 → nominal / heavy / beyond |
| 12 | **the 1.6–3 Hz hard-turn readout as information** | `m6_goal_scoring.spectral`'s own definition mirrored (engaged runs ≥ 2 s, w18 band-passed 1.6–3 Hz, \|θ\| ≥ 20°, unpressed), per m6 band + pooled, V282 refs beside it. It reproduces the record exactly on r79: ALL **8.48** vs V282 **3.45 / 4.02**; <3 7.88, 3–8 9.59, 8–12 6.01 (M6: 7.9 / 9.6 / 6.0) | `hard_turn` | HT: a 2 Hz 10 deg/s rate reads 6.97 (expect 7.07) |
| 13 | **one hands-off definition everywhere, incl. F6b's onset** | `handsoff_v3`: latActive, \|wire\| < 300, unpressed, \|bar\| < 300 over frames k−50..k (wire = bar/1.024). Used by rule identity (pooled + windows), F4, F9, F10, the cap holds; F6b's onset test = the 0.5 s BEFORE the onset were hands-off (`handsoff_before`) | `handsoff_v3`, `handsoff_before`, `enrichment` | HO: \|bar\| 400 is not hands-off (the reader's < 500 rule says it is); hands-off returns 0.5 s after the hand. C3: onsets after a 400-word hand are 0 of 235 hands-off |
| 14 | **the fork-cache filename bug** | ONE naming function, `drive_read_v299.fork_cache_path(prefix)` = `<cache>/r<ctr>_<hash6>_al_fork.npz`, named from the route PREFIX (never the wire tag). The extractor's `default_out` calls it; the read passes it as `--out`; the extractor runs ONLY when no such file exists (a file for another route is reported, not overwritten). `--print-out` prints the path | `route_tag`, `fork_cache_path`, `fork_cache`; extractor `_naming`, `default_out` | K1: route 71's cache is found under the legacy tag r71b_v294 with no extractor run, and the extractor's `--print-out` names the same file |
| 15 | **report header cites rev 3** | section 6's header and the verdict header cite rev 3 §7 and the card | `report` | — |
| 16 | **spec §7.1 sign sentence** | corrected (one sentence): + = left for θsp, θ and carState.steeringTorque; the 0x18F word is + = RIGHT, bar = −1.024 × steeringTorque; the hand side is sign(−bar) | spec rev 3 §7.1 | EVIDENCE below |
| 17 | **the 0x1AB checksum identity, recomputed** | `chk_0x1ab_checksum.py`: opendbc's `honda_checksum`, compiled verbatim (ast) from the V299 fork commit `c6452361e`'s `hondacan.py` (source sha16 `58264d309ba35c31`), over every raw 0x1AB frame of route 79 | `rlog-tools/studies/angle_loop/chk_0x1ab_checksum.py` (2.7 s) | **61 113 / 61 113 frames pass (100.0000 %)**, all 3 bytes, src 1 only; counter steps mod 4 = 1 on 99.99 % |

**The sign, recomputed (EVIDENCE, `chk_0x1ab_checksum.py` on route 79).** Each carState row was paired with the latest 0x18F frame at or before it, which is the frame it was parsed from. On that pairing the 0x18F torque word equals −carState.steeringTorque **exactly on 100.00 % of 121 383 rows** (slope −1.0000, corr −0.99999). So bar = −1.024 × steeringTorque. The first version's −1.028 / −0.994 came from a looser pairing: carState ZOH'd onto the 100 Hz grid gives about −1.018 / −0.995 (also run here); its exact method is not recorded. The instrument's sign(−bar) is right.

### Found while aligning (not on the rejection list)

1. **The status bit values.** The V299 fork commit `c6452361e` (`values.py`) emits `ANGLE_STATUS_RATE = 4`, `ANGLE_STATUS_CLIP = 16` and **`ANGLE_STATUS_EPS_STALE = 256`**. All other bits are reserved. The first version decoded the stale bit as **8**, following the spec's §2.2 prose. On a V299 drive that would have:
   - counted every stale frame as an anomaly (> 127);
   - read F8's "bit 8 duty" as 0, blind;
   - scored the cs_tqeps equality on stale frames too.

   The instrument now decodes the fork's values and counts any frame with 8 set as reserved. **EVIDENCE** (fork source at the commit). The spec's §2.2 F8 row still says 8 (open item 2).
2. **The rule identity had no fit floor.** On r71b (V294, torque mode, A160), both replays' pooled R² are about −55, yet the first version printed "RULE THAT RAN: V299". So a V299 drive whose tap neither replay explains would have passed F1's replay clause on noise. Added as an **instrument guard beyond the card**: the identity is decided only when the winning replay's pooled R² ≥ 0.5. Route 79's V298 fit is 0.867. Otherwise the read prints "neither fits" and F1's replay clause is NOT TESTABLE.
   - B2 control: a tap of unrelated noise → "neither fits" (best R² −0.32).
   - Open item 3.
3. **The informational V298 limiter reconstruction crashed on route 71.** `m4_common.limiter_reconstruct` raised an IndexError on route 71's arrays. It never ran there before, because the cache was never found. It is now caught and printed as NOT TESTABLE. It is information only, and the F1 clause is `o1_snaps`.

---

## 0. What changed, and the identity guarantee

| file | change |
|---|---|
| `rlog-tools/studies/angle_loop/drive_read_v299.py` | the ALIGN rewrite (above); 20 synthetic controls in `--selftest` |
| `analysis-2020accord/studies/angle_loop/v298_flight/r79_extract_fork.py` | `route_tag` and `default_out` delegate to `drive_read_v299` (lazy import, parent process only); `--print-out`. Route 79 with no `--out` still writes the panel's `r79_fork.npz` |
| `rlog-tools/studies/angle_loop/chk_0x1ab_checksum.py` | **new**: the checksum and sign identities (2.7 s) |
| `docs/specs/design/v299/DESIGN-V299-SYNTHESIS-rev3-2026-10-02.md` | §7.1 sign sentence only (one line) |
| `angle_loop_drive_read.py`, `drive_read_fastlane.py` | **not edited** |

**Sections 0–5: byte-identical. EVIDENCE.** Each run below was diffed against a pre-edit run made first (`_scratch/out/align299/pre/`). Every diff of the section 0–5 text (RUNTIME excluded) has **0 lines**. The JSON is identical outside `v299` too, with one exception: r71b's `meta.fork_extract_s` = 11.6 s exists only in the pre-edit run, the footprint of the naming bug.
- route 79 warm ×2;
- route 79 cold;
- r71b_v294 cold.

**The replay cache, cold.** On route 79, all 8 regenerated replay files are **bit-identical** to the pre-existing ones.

**Runtime (EVIDENCE, this machine, final code):**

| run | wall | the read's RUNTIME line | V299 blocks |
|---|---|---|---|
| route 79 cold (replay cache aside) | **12.1 s** | 11.9 s (8 replays, 5.8 s) | 0.95 s |
| route 79 warm | **6.5 s** | 6.3 s | 0.29 s |
| r71b_v294 cold | **13.3 s** | 13.1 s (8 replays, 7.1 s) | 1.08 s |
| r71b_v294 pre-edit (the bug: extractor re-run, cache still not found) | 17.9 s | 17.7 s | 11.79 s |
| `--selftest` (20 controls) | 13.0 s | — | — |

The ~0.7 s of rule identity on a cold read is the V299 replay. On r71b it is now computed, because the fork-side block no longer crashes first.

---

## A. Attribution

- **carFw family:** `39990-TVA,A16<letter>`, where A16A = V298 and A16B = V299. `A160` (V294/V295) is excluded.
- **V299 fork params:** `AccordAngleBarFromEps`, `AccordAngleMaxRate` and `AccordAngleClipScale`.
- **The schema pin:** the fork commit the schema was pinned to, and whether that schema defines the status field.
- **`accordAngleStatus`:**
  - PRESENCE is measured as a fraction of latActive carState rows (F1 needs ≥ 99 %).
  - It is decoded with the fork's values: 4 rate/jerk, 16 clip, 256 EPS stale.
  - Reserved bits are counted, including the spec's literal 8.
- **The O1-like snap:** `o1_snaps`, item 5 above.

**The extractor (from the first version, still EVIDENCE).**
- It pins the schema with `git show <commit>:<path>`.
- `--commit auto` reads the route's own initData GitCommit and stops on a mismatch.
- Re-run on route 79, it reproduces all 151 arrays of `r79_fork.npz` bit for bit.

**Route 79.**
- `accordAngleStatus`: present on 0.00 % of 66 767 latActive frames. The schema at `2712e1336` lacks the field.
- **448 O1-like snaps** in 66 759 latActive steps, none clip-bound.
  - The largest toward-wheel step is 16.8°/frame.
  - The first ones: +9.5° toward a wheel 11.1° away at 1.2 m/s. That is V298's override snapping the setpoint to the wheel.
- The clip-bound reconstruction is live: 68 latActive frames sit at the error clip on route 79. None coincides with a snap.
- Information: the no-O1 limiter matches 84.37 %; the with-O1 control matches 99.98 %.

**r71b_v294.**
- Fork cache **`r71_a7b8ba_al_fork.npz` found**, 0.00 s, with no extractor run.
- Schema `20d24ab79`; status absent.
- 0 snaps. That is a torque fork; its co_ang is not an angle setpoint.

## B. Rule identity (F1's instrument)

The byte-exact fast lane is replayed under the V298 rule (C3B-P) and the V299 rule (`v299_cand`), with the read's structural inputs. Scoring is now on §7.1 hands-off settled frames: pooled, each replay at its own best lag in −2..8 frames, and per 30-s settled window with ≥ 200 hands-off tap frames.

**F1:** pooled dR² ≥ +0.05 AND V299 wins ≥ 2/3 of those windows, AND the fit guard.

**B0, the rule's validation every run (unchanged, EVIDENCE).** The V299 rule is compared with the spec mirror `cave_rev2`, compiled verbatim from `rev_h1.py`, sha16 `eaca5ea500f60030`:
- random: 0/4000 mismatches;
- targeted: 0/2000;
- 0 E′ mismatches;
- negatives: rev-1 caps 136, the V298 rule 1962.

**Route 79 (EVIDENCE) = the positive control the read now prints.** The pooled R² is **V298 0.867 (lag 0)** against **V299 −0.146 (lag −2)**, so dR² = **−1.013**.
- **V298 wins 18 / 18 windows.** dR² p10/p50/p90 = −7.454 / −1.552 / −0.215.
- The 10 manoeuvre windows (information) are V298 10 / 10.
- The card's and spec's "23/25, p50 +0.45" are not what this instrument measures (open item 4).

The first version scored on |bar| < 500 frames: −0.452 pooled, 18/18. The frame set changed, and so did the numbers. Why V299's fit falls further on the stricter set is not established here; the verdict (V298 wins every window) is the same under both masks.

**r71b_v294 (control):** "neither fits", best pooled R² −54.6 (found-while-aligning item 2).

## C. Stutter readouts, enrichment, F6 / F6b, the 1.6–3 Hz readout

The detectors are the panel's own, imported unchanged. They are unchanged from the first version; the enrichment cross-check (80.7 / 30.3 per min at 5–10 m/s) still reproduces the refuter.

**F6 (route 79):**
- trains 4.68 /min at 5–10 m/s;
- 4–8 Hz rms **7.089** deg/s;
- 300|512 enrichment **×3.58**.

F6 FAILS on the enrichment. Both of the other clauses sit just under the bars the card set equal to this route's values (4.7, 7.09).

**F6b (route 79):**
- hands-off |w| > 1229 onsets: 0, under the new pre-onset test;
- all onsets: 89 = 39.1 /min, each with a hand already on the rim.

**1.6–3 Hz readout (information):** ALL 8.48 [V282 3.45 / 4.02] (item 12).

## D. Releases: F3, F5, the lurch sentence

Definitions are items 1, 7 and 11 above.

**Route 79 (EVIDENCE):**
- 34 releases, **all excluded as re-grabs**.
- The median time from the release edge (the first |wire| < 150) to the next |wire| > 300 is **0.03 s**: the hand's torque reversing through zero, not a let-go.
- F3, F5 and the lurch sentence are therefore **NOT TESTABLE on route 79**. Card D5 / D6 / D8 feed them.

The first version scored 11 releases there under its own edge (|bar| < 300, window cut at the next hand onset).

## E. F4a / F4b / F4c

Definitions are item 2 above.

**Route 79:** no hands-off turn-in in any class (NOT TESTABLE).

The first version's one turn-in (58.8°, 5.3 m/s, t 60.3) is not a §7.1 turn-in:
- the setpoint runs 116° → −58° → +14° without settling for 1 s until t 64.3;
- |bar| runs 120–590 through it, so it is hands-on by the 300-word rule on most of its frames.

That was checked frame by frame (`_scratch/out/align299/probe_rel_ti.py`).

## F. F10 ring

The F10 definition is unchanged from the first version, except that the holds use the §7.1 hands-off mask.

**Route 79:** no qualifying hold (NOT TESTABLE).

## G. The cap read and its null sentence

Item 9 above.

**Route 79:** no hands-off hold at 8–12.5 m/s with |a_lat| ≥ 2 for ≥ 3 s (NOT TESTABLE).

The bound test is a frame-level reading of a 1 kHz condition. It is BELIEF at the tick and EVIDENCE at the frame.

## H. F7, F7b, F9

F7 and F7b are unchanged. F9 is scored on §7.1 hands-off tap instants.

**Route 79:**
- F7: 0 runs;
- F7b: 0 runs (longest 0.04 s);
- F9: hands-off tap max **74 LSB** (173 under the old |bar| < 500 mask).

## I. Bar check (F8)

The equality cs_tqeps == −8·tap is checked on stale-bit-clear frames. The stale bit is **256**, the value the fork emits.

**Synthetic (I1):**
- exact relation: 0.0000;
- sign-flipped: 0.999;
- stale on 5 % of frames with the bar zeroed: 0.0000 mismatch and 0.0500 stale duty;
- one frame carrying the spec's literal 8: counted as reserved.

**Route 79 and r71b:** NOT TESTABLE (no status field). 0 canValid drops while latActive.

## J. The verdict

Every criterion is printed as PASS, FAIL or NOT TESTABLE with the measured value, the bar and the rev-3 prediction:
- F1, F2, F3, F5, F4a, F4b, F4c, F6, F6b, F7, F8, F9, F10;
- F7b as OBSERVATION;
- X3 as N/A;
- R9 as OPERATOR.

The three null sentences are printed with their current inputs: stutter, cap and lurch.

**Route 79 (control):** FAIL F1, F6.
- F1 fails on carFw A16A, the V298 replay winning 18/18, status absent, and 448 O1 snaps.
- F6 fails on the 300|512 enrichment ×3.58.
- F2, F6b, F7 and F9 pass.
- F3, F5, F4a, F4b, F4c, F8 and F10 are NOT TESTABLE.

**r71b_v294 (control):** FAIL F1 (A160), F3, F5. The F3/F5 firings are artefacts: on a torque-mode route the reader's θsp = −raw/10 is a torque word, not an angle. The block is labelled a control read.

---

## Open items (for the orchestrator; not decided here)

**Status after FIX (2026-10-02):** item 1 is RULED (clip-bound steps do not count) and implemented. Item 2 is fixed in the spec (§2.2 and the F8 row now say 256). Item 3 is RATIFIED with the ruled order (§FIX D2). Item 4 is fixed in the card and in spec §6.1 / §7.2. Items 5 and 6 stand as written.

1. **F1's literal snap clause counts clip-bound steps.** The V299 fork keeps its error clip (`values.py`: "the only bound between the setpoint and the wheel"). The clip is applied after the rate limit, so a hand turning the wheel faster than 120 deg/s drags a clip-bound setpoint more than 1.2°/frame toward the wheel (EVIDENCE, `carcontroller.py _update_angle`). The card's D6 firm override is where this can happen.
   - The read implements the literal clause: any snap FAILS F1.
   - It prints the clip-bound / not split.
   - Should a clip-bound step count? This needs a ruling.
2. **The spec §2.2 F8 row says 8 for the stale bit; the fork emits 256.** The instrument follows the fork. The spec row (outside my write scope) should be corrected or the fork changed. One of them is wrong.
3. **The fit guard (F1 identity needs the winner's pooled R² ≥ 0.5) is beyond the card.** Ratify or remove it. Without it, a V299 drive whose tap neither replay explains passes F1's replay clause on noise.
4. **The positive-control figures in the card (§4 F1) and spec §7.2 F1 ("23/25, dR² p50 +0.45") do not match this instrument.** It measures V298 18/18, pooled −1.013, p50 −1.552 on route 79, and that is what the read now prints. The card and the spec are outside my write scope.
5. **Still not exercised on a real route** (unchanged): the status decode and F8's equality need a fork commit with the field. That is `c6452361e`, which has no route yet. The camera gate and op-skip are absent from every replay.
6. **F6 on route 79** sits 0.001 deg/s under its own rms bar (7.089 against 7.09) and 0.02 /min under its trains bar. The card set both bars equal to this route's values, so the control fires only on enrichment. That is information, not a defect.

**Run:**
```
python rlog-tools/studies/angle_loop/angle_loop_drive_read.py <route>          # the full read, section 6 included
python rlog-tools/studies/angle_loop/drive_read_v299.py --selftest             # 28 synthetic controls (~17 s)
python rlog-tools/studies/angle_loop/chk_0x1ab_checksum.py [<prefix>]          # 0x1AB checksum + 0x18F sign (~3 s)
python analysis-2020accord/studies/angle_loop/v298_flight/r79_extract_fork.py --route <prefix> --out <path>   # fork cache (~10 s; the read calls it only when the file is missing)
```

The ALIGN session's outputs are in `_scratch/out/align299/`:
- `pre/`: the pre-edit reads;
- `post/` and `final/`: the post-edit reads;
- `work/`: the LF working copies;
- `chk1ab_sign.py` and `probe_rel_ti.py`.

The selftest log is `_scratch/angle_loop/drive-read/v299_selftest.txt`.
