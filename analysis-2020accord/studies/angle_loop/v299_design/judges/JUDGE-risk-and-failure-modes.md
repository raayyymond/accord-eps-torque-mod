# JUDGE — risk and failure modes (V299 design round, 2026-10-02)

**Role.** Judge, lens = *what can go wrong on the car*. A SUBAGENT of the judge-panel orchestrator. I read all five design
pages and all three scorer reports (S1-frequency, S2-time-nonlinear, S3-bytes-interlocks-fork) in full, then ranked every
implementation by on-car risk: stability under friction and the hand, release/override to the driver, the 0xE4
sentinel/timeout, the downstream interlocks, the fork safety path, and the cave bricking record (V24/V27/V48B bricked
pre-gate; V96/V112/V288/V289/V292 flew post-gate; V291/V292 loop-opening, V289 notch, V283 Ki each failed on-car).

**Status.** ANALYSIS ONLY. Nothing built, flashed, sent or committed; fork / firmware / golden model / STATE / lineage /
git untouched. I read bytes read-only from the V298 image (`analysis-2020accord/_v298_…A16A_plain_image.bin` in
`accord-firmwares`, sha256 `177abf04`, asserted).
**One safety-classifier interruption** occurred this session; per the brief I noted it and continued (defensive work on
the operator's own ECU; designs are documents).
**Labels.** EVIDENCE = read by me from the image, or computed by a named scorer; BELIEF = modelled/inferred. I score
risk bands; the operator scores symptoms.

**Crux I re-derived myself** (doctrine: verify every decision-bearing finding before relaying). Image reads, `python`
LE: hard-freeze imm **512** @0xC4C64, opposing **300** @0xC4C6C; **OCL 3072**, PCL/SCL **15360**, fwd **5346**; version
byte **0x41 'A'** @0x1310D; GB-P row0 X714/G1178/S1041. All override-critical and rail/EME-critical cells match the
designers and S3. D3b's SCL→19072 makes the naive sum (3111) exceed OCL 3072, so OCL becomes the ceiling (~3057 T) and
lane+base-assist can enter the unreplayed soft-EME 5120–5900 band — **D3b's DO-NOT-FLY is substantiated from bytes.**

---

## 0. Ranking (risk lens; 1 = lowest on-car risk among legitimate attempts)

| # | candidate | risk verdict | the governing risk fact | best graft to salvage |
|---|---|---|---|---|
| 1 | **D1c** | **FLYABLE, lowest new-hazard** | V298 linear loop (= V298 GATE 2, EVIDENCE S1); **0 RAM, no new state word**; fade + O1 unchanged; the asymmetric A3 bound is the ONLY firmware edit that removes the freeze ratchet **and holds N1** (worst 11.2° vs D1a 23.7°, S2). Residual: relinked cave must re-run H1+Ghidra on the BUILT image; I runs under a 600–1229 hand (benign DC droop ≤3°). | — (base of my synthesis) |
| 2 | **D2a** | **FLYABLE, zero bricking class** | **0 firmware bytes** → GATE 1 vacuous, no brick path, V298 stays as flown; the **only** candidate that ADDS O1-loop margin (lead 0: GM 6.0→9.4 dB @60 ms, S1); params clamped + toggle-revert; override best-formed (>1200 instant). Residual: X3 twist-O1 (2 trips @3 m/s, S2); leaves the ratchet (efficacy, not hazard); bar sign must flip. | the lead-0 O1 fork + clamped-param + toggle-revert pattern |
| 3 | **D2b** | FLYABLE, larger fork surface | As D2a (0 firmware, O1 margin, override preserved) but the 2nd-order limiter + plan-lead are the largest fork diff and BELIEF-heavy; 20 Hz interpolation not freq-assessable (S1); 1.6–3 Hz ×2.7 (S2). | the speed-scheduled plan lead (once de-risked against the 20 Hz staircase) |
| 4 | **D4b** | FLYABLE with the heaviest brick exposure of the recommended set | V298 linear loop (= V298 GATE 2); GATE 1 for gp-0x6a32 **passes static + V288 flight precedent at the SAME site 0x29D72** (S3). But +52 B relinked cave + **1 new RAM word** (most bricking-exposed "recommended"); fork terms are **code constants** (not toggle-expressible, harder to revert); **no instant >1200 override path** (debounces every level); N1 outward +1.7°, 4–8 Hz up. | the motion gate "don't freeze while the wheel moves toward the setpoint" (if the RAM word is ever justified) |
| 5 | **D1-a2 (G0-1400)** | LOW-RISK minor lever, separate dose | 4-byte cal, no relink (least brick); GATE 2 clean (+2.4°). But low-speed PM −9.1°, 5–30 Hz flag, deeper DC drift under O1 (\|S\|28); efficacy mixed (S2 no separable signal). Not to be carried inside a ratchet-fix build (one drive, one edit). | the ×1.2→×1.0 low-speed stiffness taper as a standalone later dose |
| 6 | **D1a** | **NOT FOR FLIGHT** (hand-release) | Bytes correct, 4-byte cal (least brick), but designer's own N1 lens FAILS: outward 2×511 hold **15.9°** lurch vs V298 4.7°, nudge 8.0° (EVIDENCE d1_n1; S2 worst 23.7°). A real on-road release lurch. Exists only to prove the cal space cannot hold the fix. | (none beyond D1c, which is this plus the asymmetric bound that fixes N1) |
| 7 | **D3a** | **DO NOT FLY AS SPECIFIED** (override + coupling) | **Weakest driver override in the panel**: O1 only after 1200 held 100 ms or >2500 instant; 600–1200 **never** yields the setpoint while P reaches **75 % of rail**; sim override latency **370–400 ms**, 75 % rail + **+21 % hand force** under the overriding hand (S2 F6). Its 1229 freeze STILL fires on its own faster-slew twist (hand-lost 0.41, S2 F3). **A16B accepted without requiring K2** → a mis-deploy runs D3 firmware on V298's fork, which relays O1 on the twist (designer's own sim). GATE-2 low-speed margin halved (+15.3→+7.3). | the rate-cap/clip authority schedule behind clamped params — NOT its override rule |
| 8 | **D5b** | **DO NOT FLY AS SPECIFIED** (N1 + self-twist-trip) | Firmware is **byte-identical to D1a** → inherits the 15.9° N1 outward-release failure (S3 §5 pending disqualifier; S2 worst 18.6°), and its fork O1 (600 ON) does not cover a ~500-raw hand, so nothing rescues it. **15 instant-1200 O1 twist trips** (setpoint snaps to the wheel on a hands-off slew) and the **highest 4–8 Hz wheel rate of any row (14.4)** — likely feels MORE ratchety, against note 4. Bar sign inverted. | its override FORM (>1200 instant / 600 held 60 ms) — the best-formed override in the panel — grafted onto D1c's firmware (= G:D1c+D5fork, N1 → 9.8°) |
| 9 | **D3b** | **DO NOT FLY** (uncleared interlock) | Opens the **soft-EME 5120–~5900 band**, unreplayed (I confirmed the SCL→19072 / OCL-3072 mechanics from bytes). Exactly the adversarial-pass failure class ("a cell is not private because you did not find another reader"). +24 % override effort on the raised rail; S2 shows it is DOMINATED by D3a (its 2500-instant O1 trips on its own twist). Designer + S3 concur. | nothing — the rail raise is unneeded (rail never binds, D3 finding 2) |
| 10 | **D4a (GB-S13)** | **FAILS GATE 2** as the panel defines it | 23 ms_free fails, worst **25.1°**, curve-hold ζ **0.040→0.010** (S1, two engines), at the **17.5 m/s knot where the model under-states the real loop gain ×1.5–2** (S1 §2.9) — a fail on margins already optimistic. Also does NOT move the freeze relay; fork terms are code constants. | the +1.3× highway (10–17.5 m/s) small-correction stiffness, ONLY if the ms_free ruling clears it |
| 11 | **D4b+GBS13** | **FAILS GATE 2 + most firmware** | Inherits D4a's GATE-2 fail AND D4b's +52 B cave + new RAM word. Worst of both axes. | — (see D4b and D4a) |
| 12 | **D5a** | **DO NOT FLY** (O1 collapse + GATE 1 owed) | Washout strips low-frequency D → the **O1 loop COLLAPSES to 17.4° / 1.5 dB @90 ms** (S1, far below the 6 dB bar); 17 R79 sub-bar points; **worst N1 (26.3°) and worst overshoot (9.9°) of all rows** (S2); and GATE 1 for its new RAM word gp-0x6c44 is **not cleared** (decode owed, S3) — unretired bricking exposure. Designer + S1 agree: not recommended. | (none that is not better taken from D1c/D2) |
| — | D1 fork bar | PASS (no loop term) | Parse 0x1AB → bar = +8·s10/2461; correct sign (0.942 agreement, S3). A UI-only change; `steeringTorqueEps` has no Honda consumer today. Low risk; the counter-coupling nit is watched by F8. | ship the bar with whatever wins (it is note 3's fix) |

**Scorer grafts (not designer builds, but on the table):** G:D1c+D2bfork, G:D1c+D5fork, G:D1c+D3fork all put D1c's
safe firmware under a higher-authority fork and **fix N1 to 9.1–9.8°** (S2). From the risk lens these dominate the
stand-alone high-authority designs. My synthesis (§5) is the leanest of them.

---

## 1. Risk by surface (every candidate on one axis at a time)

### 1a. Cave / bricking class (the only bricking class this kit has — V24/V27/V48B)

| candidate | firmware Δ bytes | new cave? | cave size | new RAM word | GATE 1 state | brick risk |
|---|---|---|---|---|---|---|
| D2a / D2b | **0** | no | 260 (V298) | 0 | vacuous | **none** |
| D5b | 5 / 9 CRC | no | 260 | 0 | n/a (immediates) | lowest firmware |
| D3a | 9 / 13 | no | 260 | 0 | n/a | low |
| D4a | 14 / 18 | no | 260 | 0 | n/a | low |
| D1-a2 | 4 / 8 | no | 260 | 0 | n/a | low |
| D1a | 4 / 8 | no | 260 | 0 | n/a | low |
| **D1c** | 152 / 157 | no (**relinked**) | 260→252 | **0** | n/a (no st.*) | moderate: relink correctness, mitigated by H1 0/8000 + reproduction control |
| **D4b** | 218 / 222 | no (relinked, grown) | 260→**312** | **1 (gp-0x6a32)** | PASS static + **V288 flight precedent, same site** | moderate-high: +RAM, largest cave |
| D5a | ~110 | no (relinked, grown) | 260→~330 | **1 (gp-0x6c44)** | **owed** (14 bases not decode-adjudicated) | **high: unretired** |

EVIDENCE (S3 byte census; I re-read the cited anchor cells). Doctrine (CLAUDE.md, 2026-09-30): minimise — in-place
edits before a cave, one new state word before two. D2 spends zero; D1c/D4b relink; D5a both grows the cave AND leaves
GATE 1 open.

### 1b. Driver override / release — the operator's iron rule (driver must ALWAYS override by hand)

The **firmware Honda fade (×0.30 at \|bar\| 2289) is unchanged in every candidate**, so *physical* override survives
everywhere (EVIDENCE: no candidate edits the fade record). The risk is in *when the setpoint follows the hand*.

| candidate | O1 onset rule | setpoint-follow latency (S2 OV) | worst override hazard |
|---|---|---|---|
| D1c / D1a / D1-a2 | 600 instant (V298) | 30 / 160 ms @5/15 | keeps V298's 345 twist trips (known, not new) |
| D2a / D2b | >1200 instant, 600–1200 held 80 ms | 40 / 240 ms | clip ×1.6 lets P reach 61 % rail (first fork near the rail) |
| **D5b** | >1200 instant, 600–1200 held 60 ms (**best-formed**) | 40 / 220 ms | but its firmware fails N1; a ~500-raw hand not covered by O1 |
| D4a / D4b | **debounce every level 5 fr, no instant hard path** | 70 / 210 ms | a firm >1200 hand waits ~50 ms; LP freeze ~17 ms backstops |
| **D3a / D3b** | **1200 held 100 ms OR >2500 instant; 600–1200 never yields** | **370 / 400 ms** | **75 % of rail under the overriding hand, +21 % hand force** (S2 F6); the sharpest conflict with the iron rule |

EVIDENCE: S2 F6 table; fork rules from each design page; firmware fade unchanged per S3. BELIEF: the hand-force
numbers use the panel's stiff positional hand model. **D3's override is the single worst risk in the round short of
D3b's interlock** — it is the only candidate where a light-to-moderate real hand (600–1200 raw) cannot make the system
yield its setpoint while the lane is at its highest authority.

### 1c. Stability under friction and the hand (GATE 2, magnitude AND phase)

| candidate | inner loop | R2 gate box (S1) | the stability risk |
|---|---|---|---|
| D1c, D1a, D2a, D2b, D4b, D5b | **= V298** (bytes verified) | 0 fails (= V298) | none new; switching PID↔PD between two stable loops (BELIEF: no hunt; S2 shows none) |
| D1-a2, D3a/b | own table | 0 fails, worst 37.3–37.8°; low-speed PM −9.1/−9.6°; 5–30 Hz ×1.03–1.06 (5 Hz edge) | eats ~2° low-speed margin; D3a halves ≤3 m/s margin (+15.3→+7.3) |
| **D4a, D4b+GBS13** | GB-S13 | **23 fails, worst 25.1°; ζ 0.040→0.010** | **GATE-2 fail at 17.5 m/s where the model is optimistic ×1.5–2** |
| **D5a** | washout + Kf 28 | 0 gate-box fails but **+0.4° only**; 17 R79 fails; **O1 loop 1.5 dB @90 ms** | washout removes low-freq D → O1-loop collapse; a genuine instability risk |

EVIDENCE: S1 §2.1/§2.6, both engines agree to 0.1°. GATE 2 is a mandatory gate (CLAUDE.md). A ζ cut to 0.010 at a speed
whose modelled margin is already optimistic is, on the risk lens, not clearable without new identification.

### 1d. The O1 override loop (fork safety path at the wheel's own 4.5–7.7 Hz)

S1 finding 4 is decision-bearing and I accept it: the O1 relay is a closed loop whose least margin (GM 6.0 dB @Trt 60 ms,
3.2 dB @90 ms with V298's 0.06 s lead) sits in the band route 79 showed a 4–8 Hz wheel-rate excess near O1 (BELIEF on
the coincidence).

- **D2 (lead 0) is the only candidate that raises this margin** (9.4 / 8.3 dB). From the risk lens this is a real
  safety improvement and D2's strongest point.
- D1c, D5b keep the 0.06 lead and run the I under O1 → benign DC drift (\|S\|17), = the declared co-steer droop.
- **D3's K3 lead is post-clip = positive wheel-rate feedback while the clip binds: GM 6.4 dB @60 ms, 4.5 dB @90 ms**,
  and D3 raises the clip so this state is more frequent (S1 finding 5). Fixable (zero K3 while clip-bound, or take the
  rate pre-clip = D5's placement), but a defect as written.
- D5a collapses this loop (above).

### 1e. 0xE4 sentinel / timeout, engage/disengage, camera interlock

Low differential risk. The firmware sentinel/timeout/request-drop path is V298's in every candidate (EVIDENCE S3: no
candidate edits the governor/EME/lockstep/DTC cells). D4b's gp-0x6a32 and D5a's gp-0x6c44 engage-init on Honda's
0x7FFFFFFF first-tick sentinel (D4b has V288 precedent; D5a's init is BELIEF until an H1 run). No candidate degrades the
510 ms hold → sentinel → A2 path. Version-byte interlock: bumping to A16B is **fail-safe** against an un-updated fork
(EVIDENCE S3: un-updated fork → `EPS_ANGLE_LOOP_FW_MISSING`, a permanent steer fault). **D1c leaves A16A; I recommend
A16B** so carFw attributes the build and a mismatched deploy fails safe.

### 1f. Self-induced twist feedback (authority relaxes a threshold, the faster slew re-crosses it)

The round's subtle shared hazard: more authority raises the hands-off reaction twist, which re-trips the very detectors
the design relaxed (S2 F3; D2 pre-registered it as X3).

| candidate | self-twist outcome (S2, sim; BELIEF on the α extrapolation) |
|---|---|
| D1c | none — stays fork-limited at 120 deg/s, twist low; keeps V298's trips |
| D2a | 2 instant-1200 trips @3 m/s (80 ms held gate mostly protects) |
| **D3a** | its 1229 freeze fires on its own twist (hand-lost 0.41 @3 m/s; word p99 1559) — authority partly self-defeating |
| **D5b** | **15 instant-1200 O1 twist trips** (word p99 1378) — the setpoint snaps to the wheel mid-hands-off-turn |

From the risk lens D5b's self-trip is the sharper event (a sudden authority-yield to a phantom hand), D3a's is a quieter
loss of integration (and a path back to the ratchet at the higher threshold — D3's own F6).

---

## 2. Disqualifiers (explicit, with the reason that makes it do-not-fly)

| candidate | disqualifier | class |
|---|---|---|
| **D3b** | opens the soft-EME 5120–~5900 band, unreplayed (I confirmed SCL→19072 pushes the sum past OCL 3072 from bytes) | **interlock — hard** |
| **D5a** | O1-loop collapse (1.5 dB @90 ms); worst N1 (26.3°); GATE 1 for gp-0x6c44 not cleared | **stability + bricking — hard** |
| **D4a, D4b+GBS13** | GB-S13 fails the panel GATE-2 box (25.1°, ζ→0.010) at the speed the model over-rates | **GATE 2 — pending the ms_free ruling; I would not clear it** |
| **D1a** | own N1 lens FAIL (15.9° outward release lurch) | **hand-release — designer-declared** |
| **D5b** | firmware ≡ D1a (same 15.9° N1 failure, not rescued by its fork) + 15 self-twist O1 trips | **hand-release + self-trip — as specified** |
| **D3a** | weakest override (75 % rail + 100 ms under a Honda-level hand, 600–1200 never yields); A16B accepted without K2 (mis-deploy relays O1 on twist) | **override + deploy-coupling — as specified** |

D3a and D5b are *conditional* disqualifiers: each has a clean, named fix (D3a — couple A16B to K2, add an instant hard
override path, clamp params, resolve the 1229-freeze-on-own-twist; D5b — swap its firmware for D1c's asymmetric-bound
firmware, i.e. G:D1c+D5fork). As **written** they are do-not-fly. D3b, D5a and D4a/D4b+GBS13 are unconditional for this
round.

---

## 3. Best graft to salvage from each losing candidate

- **From D2 → the lead-0 O1 fork + clamped-param + toggle-revert pattern.** It is the only change in the round that
  *adds* margin to a fork safety loop (O1 GM 6.0→9.4 dB), it preserves override best, every param is clamped and
  defaults to V298, and it ships 0 firmware with a REVERT config. This is the authority-adder I would put under D1c.
- **From D3 → the low-speed stiffness taper (G ×1.2 @3.1 → ×1.0 @8, GATE-2 clean, 0 fails)**, as a *separate later
  dose*, NOT its override rule and NOT the rail raise. (Equivalent to D1-a2's G0 edit.)
- **From D4 → the motion gate** ("do not freeze while the wheel already moves toward the setpoint"), the most principled
  statement of the ratchet fix — but only if a new RAM word is ever judged worth its GATE-1/brick cost; D1c achieves the
  same N1-safe ratchet relief with 0 RAM, so the graft is a fallback, not a need.
- **From D5 → its override FORM** (>1200 raw instant, 600–1200 held 60 ms) — the best-formed override in the panel —
  grafted onto a firmware that holds N1 (D1c's), i.e. exactly G:D1c+D5fork.
- **From D1a / D5a / D3b / GB-S13 → nothing better than what D1c + D2's fork already give.** D1a's value is fully
  superseded by D1c; D5a's friction channel is GATE-2-inert at the gain it can afford; D3b's rail raise is unneeded (the
  rail never binds); GB-S13's highway stiffness is the one scrap worth re-scoring IF the ms_free ruling ever clears it.
- **The 0x1AB torque bar (note 3's fix) ships with whatever wins**, drawn **bar = −eps/2461** with `steeringTorqueEps =
  −8·s10` and the message listed with `float('nan')` (S3 §4: D1's +8·s10/2461 keeps the sign; D2/D5 inverted it; D5's
  50 Hz entry makes 0x1AB non-optional — use nan).

---

## 4. Synthesis the risk lens points to (not a build order — a recommendation to the orchestrator)

**The lowest-risk legitimate build that attacks the goal is D1c's firmware under D2a's fork, plus the bar and A16B.**

- **Firmware = D1c** (relinked cave, 0 RAM, V298 linear loop = V298 GATE 2): removes the measured freeze ratchet
  (note 4) and **holds N1** — the only firmware in the round that does both. EVIDENCE: S2 N1 worst 11.2°; S1 GATE-2 = V298.
- **Fork = D2a's terms**, each param-gated to a V298 default with a toggle REVERT and **clamped ranges**: lead-0 O1 (adds
  the only fork-loop margin in the round), cap 300 / clip ×1.6 for the fork authority note 2 asks for, the >1200-instant
  override (iron rule), and the bar. Prefer D2a's leaner fork over D2b's plan-lead (less BELIEF, smaller surface, no
  20 Hz-staircase unknown).
- This is the leanest member of the S2 graft family: **G:D1c+D2bfork** scored N1 9.1°, best small-correction tracking,
  ratchet removed; a D2a (not D2b) fork trades a little tracking for a smaller, more-assessable fork surface.
- **A16B + CRC** so a mismatched deploy fails safe.

Residual risks even for this synthesis, to carry into the build round and pre-register on the drive:
1. **Relink correctness** — D1c's cave is relinked; re-run H1 and the Ghidra decode on the BUILT image, and the
   adversarial pass with "do not flash" reachable (S3-10; CLAUDE.md close-out doctrine).
2. **I runs under a 600–1229 hand during O1** → DC drift / co-steer droop ≤3°, recovers ~0.4 s (declared D1c M-D1-2;
   benign but real). Pre-register the release-lurch FAIL (D1c F5).
3. **D2a's X3** — faster slews can push the twist to ~1222 and trip the instant-1200 O1 (2 trips @3 m/s in sim); the
   80 ms held gate keeps the twist from the held path. Pre-register D2's X3 (via-hard bit 64) on the wire.
4. **Clip ×1.6 is the first fork to push P toward 61 % of rail** — still well under the 2461 T rail (peak ~59 % on r79),
   OCL 3072 unchanged, no interlock touched (EVIDENCE S3). Watch the tap p99 against 250 LSB.
5. **The bar parser counter-coupling** — a 0x1AB counter fault can drop `canValid` (optional or not); r79 was 99.997 %
   clean. Watch it (D1 F8 / D2 F4).
6. The goal's **1.6–3 Hz hard-turn criterion worsens** with any authority gain (every designer declared it). That is a
   goal-conflict for the operator to rule, not a safety stop.

**If the operator wants more authority than the 120 deg/s-capped fork gives**, the risk-ordered next step is to raise the
cap toward 250–300 behind D2's clamped params (D5's override form), NOT to raise firmware gains (D3a's override and
self-twist costs) and NOT to raise the rail (D3b's interlock).

---

## 5. Process notes

- Scripts I ran: one `python` LE read of the V298 image to verify the override/rail/version cells (<1 s). No sim, no
  build, no fork/firmware/golden/STATE/git edit.
- Writes: this file only, under `v299_design/judges/`.
- The golden-model mirror for whatever wins is NOT yet in `eps_chain_control.py` (designers were barred); S3-11 flags it
  as a build-round prerequisite. I concur: no build without a byte-exact `_self_check_v299` mirror.
- Classifier interruptions this session: **1** (noted, continued).
