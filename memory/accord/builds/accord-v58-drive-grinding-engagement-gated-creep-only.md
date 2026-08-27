# V58 drive (route `2b`, 2026-07-30) — the grinding is engagement-gated and creep-only

**Type:** reference / project · **Build:** V58, FLASHED, flight-clean · **Route:** `75604b0a432fdc89_0000002b--7926e8f7e5`, 14 segments, 83,959 frames

## V58 is flight-clean
`steerUnavailable` / `steerTempUnavailable` / `canError` / `controlsMismatch` / `immediateDisable`:
**0 across all 14 segments.** Only flags are `commIssue`×2 + `selfdrivedLagging`×1, all at seg 0 t≈8.5 s
**in `wrongGear` before the drive started** — a boot transient, not route 28's real mid-drive soft-disable.
`STEER_STATUS == 0` in **83,959/83,959**; **`ST==4` = 0**, extending V57's 0/37,922 to 121,881 combined.

## ★★ The collinearity confound is BROKEN
Seg 13 is **60 s of moving-but-disengaged at 0.5–4.8 m/s**, against engaged creep at overlapping speeds —
the first route where a speed bin has windows in both arms.

| | value |
|---|---|
| amplitude ratio, speed-matched | **13.4×** [boot 95% 3.9–19.8], MWU p = 6.1e-6 |
| speed **+ effort** matched | **16.9×** median, 17/18 pairs > 1 |
| time-occupancy, envelope > 300, matched creep | engaged 27.8% of 53.4 s vs disengaged 0.15% of 65.8 s ⇒ **184×** |
| share of all grinding time that is LKAS-applying | **99.3%** |

**Confounds run AGAINST the engaged arm** (disengaged has |ang| 167° vs 9°, effort 1638 vs 205) ⇒ floors.

🛑 **Better than any ratio — the resonance is ABSENT disengaged:** prominence median **122.7× vs 3.6×**,
and the disengaged "peak" wanders 15–29.9 Hz (sd 2.49 Hz) — the argmax of a floor, not a mode.
Sharpest single case, seg 12 t≈49.3, same road, 1 s apart, speed constant at 5.0 m/s:
`env 750.4 → 36.5` (**20.6×**) while driver effort *rises* 101 → 2193.

## Three record corrections
1. **Frequency law does NOT reproduce.** Strict 18–26 Hz: `a = −0.005…+0.031` at every prominence cut;
   **`a = 0` fits within 0.12–1.48σ, `a = 0.177` rejected at 3.2–7.1σ.** It is a **fixed ~20.9 Hz** line.
   ⚠ Don't rewrite the law off one route — the recorded value is a *pooled cross-route* fit and here
   `spearman(v,|ang|) = −0.728`. Re-run strict-band over V55/V56/V57 first.
2. **CREEP-ONLY**, not road speed: prominence 141×/138×/518× at 1–4 m/s → 29×/11×/8×/7× at 4–18 m/s.
   `STATE.md` had it backwards. The operator's "look only at the few-mph moments" was correct.
3. **~21 Hz IS in openpilot's command** — verified on the **native 0xE4 grid** (not a resampling
   artifact): prominence 34.0×, `coherence(cmd,bar) = 0.917`, K=4, null 0.632. Bar is 6–7× sharper ⇒
   reads as an echo, but **direction unresolved**: carrier phase can't settle it (75° skew) and the
   skew-robust envelope cross-correlation was inconclusive (2/4 each way, corr 0.33–0.44).

## Limits
🛑 **Zero fully-hands-off windows in either arm, any speed bin** — a normal commute. All numbers are
"any hands", matched on effort. 🛑 **Cannot speak to the ratchet**: hands-off + engaged + `|e4tq|≥3500`
+ v≤3 m/s gives **9 runs / 139 frames**, all inside one 8 s hands-on manoeuvre. Zero clean episodes.

See [[accord-gp6ba6-is-the-boost-amplitude-index]], [[accord-sign-probe-needs-zero-crossings]],
[[accord-ratchet-and-grinding-are-two-symptoms]], [[accord-telemetry-conventions-that-produced-wrong-answers]].
Handoff: `docs/handoffs/2026-07/HANDOFF-2026-07-30-v58-drive-and-the-boost-index-mechanism.md`.
