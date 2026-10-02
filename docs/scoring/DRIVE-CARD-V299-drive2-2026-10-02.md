# DRIVE CARD: V299, drive 2 of the angle loop, config A (2026-10-02)

**Pre-registered from** `docs/specs/design/v299/DESIGN-V299-SYNTHESIS-rev3-2026-10-02.md` (§7 = the criteria; §3.5 = the
hand predictions). Nothing here licenses "fixed". **The flash is the operator's:** he names the file and the bus, and
openpilot is killed first. Every number below is a simulation prediction (BELIEF; two engines, two plant members) unless
it is marked r79.

**What this drive can decide:**
- whether V299's integral policy is live (F1);
- whether the ratchet/stutter of route 79 came from the freeze relay (F6, the stutter readouts);
- whether the hands-off big-turn authority (note 2) arrived without overshoot (F4);
- what the no-override hand layer feels like (F3, F5, F7, R9);
- what the cap costs in curve holds (readout 6).

**What it cannot decide:** the small-correction stick (M1, a later class) and the cap-250 dose (§6, a separate drive).

**Stop rule (operator, binding):** at the first ratchet or grind, stop. ~15–30 s of symptomatic frames per item is
enough. You do not need to finish the list.

---

## 1. Before the key turns

| # | check | how | if not |
|---|---|---|---|
| B1 | **Fork = Dom at the V299 commit** (the hash in the build record, with F12 passing), pulled **before** flashing, then **Rebuild Params** | `git -C …/StarPilot rev-parse HEAD` on the device = the recorded hash | do not drive |
| B2 | **Flash V299** (`39990-TVA,A160-V299-…-0x13000-0x100000.rwd`, image sha `30ff05fa…`). The operator names the file and the bus; openpilot is killed (`tmux kill-server`); reboot | the operator's flash log | — |
| B3 | **carFw: the EPS reports `39990-TVA,A16B`** | the device's fwVersions (initData / carParams), or the Galaxy device page | A16A means the flash did not take: stop. With A16B and a fault, the fork is not the V299 commit: stop |
| B4 | **Config A restored:** `toggle-config_V299-A_bar.json`, then reboot. Confirm: `AccordEpsAngleLoop` on; `AccordAngleBarFromEps` on; `AccordAngleMaxRate` 120; `AccordAngleClipScale` 1.0; `SteerRatio` 16.84; no fork angle integral; `UseAutoSteerDelay` on | the Galaxy toggles page | restore again |
| B5 | **The car's own LKAS is OFF** (the LKAS button; route 79 had it on for 3906 frames) | the dash LKAS icon is off | turn it off |
| B6 | **The revert kit is on hand**: (1) the V298 rwd re-headered for A16B (`…V298-REHEADERED-FOR-REVERT-FROM-V299-A16B-…`); (2) the V295 rwd re-headered for A16B; (3) `toggle-config_V298_angle_loop.json` (V298's config); (4) `toggle-config_V298_angle_loop_REVERT_to_V295_r2.json`; (5) how to check out Dom `2712e1336` | files on the device / laptop | do not drive |
| B7 | Stationary, ignition on, openpilot up, not engaged: no steering warning; the wheel is free; **the on-screen bar moves when you push the wheel lightly** (it now shows lane torque from the EPS's 0x1AB, not a lateral-accel request) | look | stop (F8) |

**Revert recipe.** A revert is NOT a toggle config, because the override removal is code. The order:
1. pull and check out Dom `2712e1336`, then Rebuild Params;
2. flash the V298 re-headered rwd (openpilot killed; the operator names the file and the bus);
3. reboot;
4. restore `toggle-config_V298_angle_loop.json`;
5. reboot.

**The second-level revert:** the V295 re-headered rwd + `…REVERT_to_V295_r2.json` (angle switch off).
**V294 is retired as a revert target:** its rwd lists A16A only.

---

## 2. The manoeuvres, in order (lowest risk first)

**"Hands verifiably off":**
- Fingers hover 2–3 cm clear of the rim: not resting and not touching.
- Hands-on frames are dropped by the read (\|wire\| ≥ 300 or pressed). A resting hand spoils the item, but it is harmless.
- Say nothing; just drive.

| # | manoeuvre | reads | predicted (sim, BELIEF) | stop if |
|---|---|---|---|---|
| D1 | 2–4 m/s on a straight; engage; 10 s hands off | engage sanity, F2 | a quiet hold; no pull or buzz | buzz, grind, pull |
| D2 | **A 30° turn at ≤ 4 m/s, hands off** (a gentle lot curve or a shallow corner), and its return | **F4b** (20–45° at ≤ 4.5 m/s, bar 8.5°); note 4 | overshoot ≤ 4.2° on the nominal member, **up to 7.0° if the car is the heavy member** (V298 ≤ 3.0°) | it swings well past the curve and comes back |
| D3 | **Two 60–90° turn-ins at 3–8 m/s, hands off** (a junction turn at ~3–5 m/s, one at ~6–8 m/s), and their returns | **note 2** (t90, tap peak), **note 4** (stutter readouts), **F4a** (bar 6°), F6, F9 | t90 0.67–0.72 s (V298 sim 1.4–1.9 s); overshoot ≤ 5.2° (≤ 3.3° at 7–8 m/s); 0 stall-surges per turn (V298 1.75–6.1); tap ≤ 193 LSB; unwind past centre ≤ 4.6° | **ratcheting, stutter, grinding**; an overshoot you would call a swing |
| D4 | **A request drop mid-turn**: during a hands-off 30–60° turn at ~5 m/s, disengage lateral (your usual cancel) | A2 (lane quiet), R7 (no push to centre) | the wheel is free within ≈ 0.1–0.5 s; no steer toward straight over 2 s | the wheel keeps steering, or pulls to centre |
| D5 | **Light-hand holds at 8 m/s** in a gentle curve: hold the wheel lightly **2–4 s inward** (toward straight) and then let go fully. Then the same **outward** (tighter than the path). Hands fully clear after each release for ≥ 2 s | **F3** (the swing past the path, away from where your hand was, within 1.5 s), **F5** (residual at +1.5 s), F7b (observation) | inward: swing ≤ 1.7° (nominal) / 3.0° (heavy). **Outward: 5.6° (nominal) / 9.9° (heavy)**, felt as a lurch toward straight after letting go. F5 ≤ 0.6° | a lurch you would call a snap (R9); F3 bar 12° |
| D6 | **A firm-hand override and release** at ~5–10 m/s: turn against it firmly (past your normal override) for ~2 s, then let go | **F7** (pressed and ≥ 50 % opposing > 0.5 s), F3 after release | the resistance fades within a tick of pressed; the ≥ 50 % run lasts ≤ 0.13 s; after release the wheel returns to the path, swing ≤ 5° (drag) / ≤ 10° (firm outward, heavy member) | **"fights my hands"**; a snap on release |
| D7 | **Curve holds at 8–12 m/s on ~2.5 m/s² curves**, hands off ≥ 3 s each (a ramp or a roundabout: one near 8 m/s, one near 10–12 m/s) | **readout 6** (the cap's hold shortfall; §3 below), **F10** (0.4–0.8 Hz ring at 10–13 m/s) | shortfall ≤ 3.2° at 8 m/s and ≤ 0.9° from 9 m/s on the nominal member; **3–7° at 8–10 m/s if the car is ms_free-like**; no ring ≤ 12.4 m/s | a slow 0.4–0.8 Hz weave (F10) |
| D8 | **Light-hand holds at 10 m/s and 15 m/s** (as D5, 2–4 s each, inward and outward) | F3 (bar 12° at 10 m/s, 8° at 15 m/s), F5 (bar 4°) | 10 m/s outward: 6.1° (nominal) / 9.8° (heavy); inward ≤ 1.6 / 3.0; F5 ≤ 2.0°. 15 m/s outward: 3.3–4.8° (nominal) / 5.3–6.5° (heavy); inward 2.4 / 4.1; F5 ≤ 2.6° | a lurch (R9) |
| D9 | **Highway, hands off: ≥ 60 s in each of 18–25 m/s and 25–30 m/s**, lane keeping including gentle curves | tracking 0.95–1.05, turn-hold ≥ 0.90, the hands-off straight error, F2, F10 at 10–13 m/s on the ramps | r79: tracking 0.976 (15–22 m/s), 0.989 (≥ 25 m/s); ring 0 % | buzz, weave, wander |

**The bar, throughout.** Glance at it. It now shows lane torque as a fraction of the rail, + = right, as in torque mode. A bar
pinned at full while the wheel is quiet is F8. Note it and finish.

**Moderate hand (expect it).** A light-to-moderate drag toward straight at 5–8 m/s (not enough to disengage) will be resisted
**harder than on V298**:
- the lane holds 53–63 % of the rail against you;
- your hand needs about 2–3.6× V298's force.

This is the declared price of having no fork override (ruling i). It is recorded (F7b), not a revert. **Your report decides
(R9).**

---

## 3. Abort: disengage, stop, and revert if you feel any of these (your words)

- **grinding**, **vibrating** or a buzz in the rim;
- **ratcheting** or **micro-ratcheting**; **stuttery** or **ratchety** turning;
- **"fights my hands"**: it keeps pulling against a firm hand;
- **a lurch or a snap when you let go**;
- **a jerk**;
- the wheel **hunting / oscillating / weaving** without being asked;
- a **pull** toward straight or away from the path;
- an **overshoot** past the turn that comes back;
- any steering warning or fault;
- `STEER_STATUS` 7 (key cycle clears it).

After an abort, use the revert recipe in §1. The route goes to the read either way.

---

## 4. Pre-registered criteria (rev 3 §7, final)

"Revert" = do not fly this firmware + fork pair again. **R9 outranks every band.**

| # | fires if | predicted |
|---|---|---|
| **F1** not live / mis-built (interpret nothing else) | the V299-rule replay does not beat V298's: pooled dR² < +0.05, or V299 wins < 2/3 of the 30-s hands-off windows (≥ 200 tap frames); carFw ≠ A16B; `accordAngleStatus` absent on > 1 % of frames; an O1-like setpoint snap (\|Δθsp\| > 1.2° in one frame toward the wheel, outside the first frame and the latActive rising edge) | V299 wins. Positive control: on r79 the same instrument picks V298, 23/25 windows, dR² p50 +0.45 |
| **F2** revert | ring presence > 0.5 %; F7(ring) > 0 per 100 s; a new 5–30 Hz line; 18–22 Hz eng/dis > 2.5; 13–17 Hz > 3.5 | none (r79: 0 %, 0, none, 1.83) |
| **F3** revert | the swing past θsp away from the hand side within 1.5 s of a release > **12° at 5–11 m/s**, **> 9° at 11–15 m/s**, **> 8° at ≥ 15 m/s**, **> 5° on a straight**; or a lurch you report | outward light holds: heavy 9.7–10.4° (5–10 m/s), 7.9° (12.5), 6.5° (15); nominal 4.4–6.1 / 5.4 / 4.8; straight ≤ 4.1 |
| **F4a** revert | a hands-off turn-in ≥ 45° at ≤ 10 m/s overshoots by > 6° | ≤ 5.2° |
| **F4b** revert | a hands-off 20–45° turn at ≤ 4.5 m/s overshoots by > 8.5° | ≤ 7.0° (heavy), ≤ 4.2° (nominal) |
| **F4c** revert | a hands-off 20–45° turn at 4.5–10 m/s overshoots by > 6° | ≤ 4.6° |
| **F5** revert | (θsp − θ) toward centre at release + 1.5 s > 4° at ≥ 5 m/s | ≤ 2.0° (≤ 10 m/s), 3.2° (12.5 m/s), 2.6° (15) |
| **F6** stop this class | ratchet trains ≥ 4.7 /min of turning at 5–10 m/s, or in-turn 4–8 Hz rms ≥ 7.09 deg/s there (both = V298 on r79), or surges enriched ≥ 2× at \|bar\| 300/512 crossings | far below V298 (sim 0 stall-surges/turn) |
| **F6b** relay one level up | surges enriched ≥ 2× within ±0.25 s of **\|w\| > 1229** freeze onsets, or hands-off \|w\| > 1229 onsets > 20 per minute of turning. A3-bound freezes are not counted | rare |
| **F7** revert | `steeringPressed` with the tap ≥ 50 % of rail opposing for > 0.5 s | no (≤ 0.13 s) |
| **F8** revert the bar/parser only | `cs_tqeps ≠ −8·tap` on > 0.1 % of bit-8-clear frames; bit 8 on > 0.1 % of latActive frames; a canValid drop in angle mode; the bar's sign against the tap | none |
| **F9** revert | tap > 250 LSB hands-off, or ≥ 230 for > 0.3 s | peak ≤ 207 |
| **F10** revert | in a hands-off curve hold at 10–13 m/s, the 0.4–0.8 Hz part of θ − θsp has a half-peak > 1°, or > 2 consecutive half-cycles ≥ 0.5° | none ≤ 12.4 m/s; possible above 12.5 m/s only if ms_free-like |
| **F7b** **OBSERVATION** | \|wire\| > 600 for > 0.3 s with the tap ≥ 40 % opposing, not pressed. Reported with the hand word, speed and duration | **expected** on moderate drags at 5–8 m/s (0.55–1.56 s at 800 words) |
| **R9** his call | you report grinding, vibrating, ratcheting, stutter, a lurch, "fights my hands", or anything new | — |

**Goal readouts** (scored per band against V282 r6c/r39; these are not revert criteria):
- stall-surges per minute;
- ratchet trains per minute of turning;
- in-turn 4–8 Hz wheel-rate;
- dwells per minute;
- tracking and turn-hold at ≥ 8 m/s;
- the 1.6–3 Hz hard-turn rate (information only, ruling ii).

### The sentences a null licenses (written now)

- **Stutter.** F1 passes and surges are not enriched at 300/512 crossings, but you still report ratcheting or stutter. Then the freeze relay was not the mechanism. Stop iterating the integral policy; next is the small-correction stick.
- **The cap (D7).** This applies to hands-off holds at 8–12.5 m/s with \|a_lat\| ≥ 2 m/s² for ≥ 3 s.
  - In ≥ 50 % of them the replayed I sits at the 6144 bound and the 0.5 Hz error is > 3°. Then the car is ms_free-like, and 7168 is **licensed for re-scoring, not for flight** (7168 trips F4 at 10 m/s in sim). It flies only if D3's 8–10 m/s turn-ins showed < 3° overshoot.
  - The bound is active but the error is ≤ 3°. Then 6144 suffices.
  - The bound is active in < 50 % of the holds. Then the cap is not the binder.
- **The lurch (D5/D8).** Outward releases ≤ 6.1° mean the car is nominal-like. 6.5–12° is the heavy member, as predicted; it is an observation, and your report decides. Above 12°, F3 fires.

---

## 5. After the drive

**Hand over the route.** Take it from the device's realdata, never by counter. Then run the read:

```
python rlog-tools/studies/angle_loop/angle_loop_drive_read.py <route>
```

The read takes ~11 s cold and ~5 s warm. Before F1 is scored:
1. Pin the fork extractor to the V299 commit, with `accordAngleStatus` added.
2. Assert the field is present on ≥ 99 % of frames.

The read then reports, per band:
- the V299-vs-V298 rule identity (`components(W, ref="V299")` vs `ref="C3B-P"`, arm-2 ramp);
- the stutter readouts against V282;
- each turn-in's overshoot (F4a/b/c);
- each release's F3/F5 and its hand side, word and age;
- every F7/F7b run;
- the D7 hold shortfall with the bound duty;
- F10 and R4.

---

## 6. OPTIONAL LATER DOSE: config B = cap 250, a separate drive on the same firmware (pre-registered now)

**Precondition.** Drive 2 passes F1–F10 and you report nothing under R9.

**What changes.** `AccordAngleMaxRate` 120 → 250 only. The clip stays ×1.0; the clip dose is its own later drive.

**Before it flies:**
1. `toggle-config_V299-B_cap250.json` is written.
2. It is scored (S2 + RSN) on the member drive 2 measured.

**Its card:** D3 (60–90° turn-ins at 3–8 m/s, hands off) ×3, D2, D7, D5 at 8 m/s.

**The readout:**
- t90 at 3–8 m/s, expected to fall by ≥ 20 % against drive 2;
- hands-off **\|w\| > 1229** freeze onsets per turn-in at ≤ 8 m/s;
- stall-surges per turn;
- the release table.

**X3, stop the dose, if any of these holds:**
- 1229-freeze onsets on ≥ 50 % of hands-off turn-ins at ≤ 8 m/s (the faster slew's reaction twist, p99 1100–1240 in sim, straddles 1229);
- stall-surges per turn ≥ 2× drive 2's;
- any of F1–F10 fires;
- R9.

**The null sentence.** If t90 does not fall by ≥ 20 %, the 120 deg/s cap was not the note-2 binder on this firmware. The next lever is the error clip.
