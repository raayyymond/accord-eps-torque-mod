# HANDOFF 2026-09-13 — V291 and V292, the first LOOP-OPENING builds: V291 cut and NOT CLEARED by its own pass, V292 (byte-exact) cut and CLEARED over one dissent

**Read `docs/STATE.md`'s decision box first.** This is the narrative of the session that set the goal
*"V282's authority with no grinding"*, measured that the grinding object does not exist with the loop
open, designed and cut the first build that opens the LKAS rate loop above ~8 Hz, and then — by a rule
written before the image existed — declined to clear it for flashing. Nothing was flashed or sent on
any bus.

## 0. One paragraph

The operator set the goal at the start: *a new EPS firmware, with StarPilot changes if necessary, that
keeps V282's authority (×6 torque, ×6 rate setpoint, no EME faults) and has no grinding.* Grounding in
the whole post-V38 record showed every in-loop lever at the mode had returned a null under the
authority gates, so the session tested the one direction never scored: **open the rate loop at high
frequency by lowering its feedback pole with DC held.** A 35-route measurement then showed **with the
loop open there is no 18–22 Hz object at all** (ζ_open ≥ 0.05 or non-modal) — V289's notch had been an
in-situ loop-opening and had removed the 20 Hz mode outright. The design did everything predicted
(sensitivity at 20 Hz ×0.34, margins up, transient authority up, nothing unstable) and failed exactly
one thing: the record's 7.3 Hz gate, because a roll-off is phase lag at 7.3 Hz and that lag is priced
against the r24 lane's pump. The r24 lane was traced and measured for the first time (a lag-4
torsion-bar-torque difference, a unit-weight sibling of the LKAS lane at the motor, a 7 Hz pump and a
20 Hz damper); a 10 % cut of its arm buys the gate. **V291 (C10)** — feedback pole 16.5 → 9.94 Hz,
r24 5244 → 4725, one telemetry rung — was cut, 15 bytes over V282. Four independent adversaries then
attacked the image: A, C and D pass; **B returns DO-NOT-FLASH** — at first on two pre-registered criteria, and after `biv` settled
the r24 arm and identified the 10–14 Hz band, on ONE (byte-exact steady state at tiny demand ×1.34–1.80,
intrinsic to any cal-only pole change; B3 re-scored PASS at ×3.3–4.2) plus one ungated cost (worst-fit sensitivity worse than V282 on 121/121 fits over
3–18 Hz, peak ×1.99 at 12.85 Hz — the band that killed V289). The orchestrator's verdict is **not
cleared**; flying it is the operator's decision against that verdict. The fork-side comb fix was built
too (uncommitted, OFF by default) and is worth −2.4/−4.2 dB, not a cure.

## 0b. The second half of the session — V292

The stop condition held the session open, and the only pre-registered failure on V291 was an integer
artefact, so the session continued into **V292: the same dose with the feedback filter's two floored terms
carrying error-feedback remainders in a 52-byte cave** (hook at the filter's own first multiply, 0x28F8E;
halfword remainders at gp-0x6D74/6D72; +10 instructions per tick). The cave designer proved from the built
bytes that the filter's mean is exact at every amplitude and that V291's own floors had been leaking a
constant −32 count feedback bias (one permanent phantom setpoint count). Four fresh adversaries: **A, C, D
PASS; B FAIL on one clause only** — the steady state at 3 setpoint counts against the LINEAR V282 chain,
which B2 showed is a surface no integer build can sit on (five floors in the loop, the cave repairs one;
V282 itself reads ×0.96/×0.72 there). Against byte-exact V282, V292 reads ×1.000 at +3 with the smallest
sign asymmetry of the three builds. **The orchestrator cleared V292 by the kit's own broken-check rule,
recorded B2's dissent verbatim, and put the sp = 3 numbers, the gp-0x6806 premise and the 9–18 Hz shoulder
on the page. V291 is SUPERSEDED-DO-NOT-FLASH on disk.** Two corrections from the pass propagate: the b3
read is the DUTY (0.47–0.50), not the transition rate; the record's r24 fold omitted the motor gain and
over-weighted r24 ×6.13 (pessimistic — corrected folded f0 18.4 Hz).

## 1. How the session ran

Orchestrated; twenty-one agents (Opus for every substantive task, Sonnet for two trivial ones, none on
Fable — the operator's model policy). Nothing built by an agent except the one image, on an explicit
GO WRITE.

| agent | surface | outcome |
|---|---|---|
| `route6c` | attribute the newest route from the tap | **V282** (b7 → 0.000 after disengage, b5 0.156); 326 s engaged, p50 61 mph; the 20 Hz and 13–16 Hz lines both visible |
| `fbdown` | score the fb-pole-down class on the V290B machinery | reproduced the record's control rows to the digit; **the class does everything but fails gate73 at every dose (94 % phase)**; Addenda A–D: fb×Kd dominated, P-path split parked, extended gates G6–G8, the r24 k-ladder, readability floor ×2.43 (C12 unreadable), the r24 fold (C3(ii) fails in the 10–14 Hz band) |
| `openloop` | ζ with the loop open, from the wire | **no 18–22 Hz object with the loop open** (35 routes, 4,759 s); ζ_open ≥ 0.05; amplitude ratio 0.21; V289's 16 Hz ring also engagement-gated; **caught two record estimators** (free-decay ζ void; coherence-time saturates); corrected the ring's units (16 rate-LSB, not sub-LSB) |
| `tracer` | the feedback filter's bytes | 32-bit state, one reader per cal cell, runs every tick (never stale), the dead-zone table, the bail path, the r25 coupling, the correct DC-held integer pairs |
| `r24lane` (+ its tracer, + `bof`) | the r24 lane, bytes and wire | lag-4 difference, Q10 gain, ±3 deadband cal, unit-weight sibling of the LKAS lane; B(f) measured fresh on r39+r6c; **pump at 7 Hz, damper at 20 Hz (73–86 %)**; gate73 monotone in the arm; **HP on r24 is dead**; κ dispute 0.45 vs 1.45 vs 0.10–0.20; the gp-0x671d latch unarmed; 10–14 Hz unidentified |
| `ghidrafill` | the Ghidra gap + which term carries LKAS | 0x2A508–0x2B421 analysed and SAVED (an uncalled twin island); **gp-0x6b4c carries LKAS, gp-0x6ad4 is a driver-torque PID**; the live forward is 0x2A2EA |
| `combfix` (+ its FF sub-agent) | the fork-side comb fix | `ModelCurvatureLead` built, OFF by default; −2.4/−4.2 dB on the band; design B falsified; the rate-plant FF is bandwidth-blind |
| `builder` | the V291 script | three doses × three telemetry bits, dry-run hashes, **b3 not b7** (b3 was an aliased coin-flip), the ld.w proof by a second decoder; wrote one image on GO WRITE |
| `advA` / `advB` / `advC` / `advD` | the adversarial pass | **PASS / DO-NOT-FLASH / PASS / PASS**; C: the census is inflated 377 → 67; D: the b3 instrument's window; B: the three numbers above |
| `artifact` | the close-out page | https://claude.ai/code/artifact/19038e6d-729b-4a79-ba3b-a07aeefcc067 |
| `gmcheck` | the golden-model contract | 90 symbols, sha256 unchanged |
| `cavedesign` | the V292 error-feedback cave | hook 0x28F8E, 52 B at 0xC4C00, halfword remainders, five proofs from the bytes; the −32 count floor-bias mechanism; a free b3-at-rest control |
| `builder292` | the V292 script | 69 bytes vs V282; hashes reproduced across five runs; two write blockers found (Windows 260-char paths, unpinned mirror import) and fixed; 14/14 mutations; wrote on GO WRITE and superseded V291 |
| `advA2` / `advB2` / `advC2` / `advD2` | the V292 adversarial pass | **PASS / DO-NOT-FLASH (sp = 3 clause only) / PASS / PASS**; A2: the b3 read must be the duty; B2: the five-floor mechanism, the ×6.13 fold defect, the gp-0x6806 premise; D2: the hook liveness wording and the boot copy loop |
| `artifact2` | the page, V292 | same URL, version 4 |
| `biv` | the two flips B named | **the deadband does NOT explain the r24 arm gap (≤ 15 %); the residual is a constant pre-deadband scale; the effective arm (κ 0.449) is admissible; the 5244 rung IS selected; B(f) not biased at 20.3 Hz; 9.94–14 Hz identified at nperseg 512** → B3 re-scored PASS |

## 2. What changed our mind, and in what order

1. **The record's own 7 Hz gate is a PHASE gate.** Reading `gate73` before the design agent reported made
   the outcome predictable: the servo's +j component at 7.3 Hz cancels the r24 pump's, so any lag there
   fails. That turned a one-axis design into a two-axis one before the first result landed.
2. **The free-decay ζ anchors were never measurements.** `openloop` called the record's own function on
   synthetic modes of known ζ and it returned the same 0.036–0.040 for everything, including no mode.
   The family was not fitted to them (the design agent checked), so the ordering survived.
3. **The ring is 16 rate-LSB, not sub-LSB.** A unit trap the orchestrator propagated into two briefs;
   caught against the source document.
4. **r24 and the LKAS lane are unit-weight siblings.** The tracer first called the delivery path a monitor,
   then re-derived it against its own agent memory and found the governor. The LKAS-term adjudication
   then went the other way again under `ghidrafill`'s instruction-level trace — the false zero was an
   `ep`-relative store that no cell-name scan can see.
5. **The r24 fold does not certify itself.** Its C3(ii) control fails in exactly the band the wire cannot
   identify, and the two arm scalings give ×4.4 and ×1.5. Both agents that touched it said so.
6. **Adversary B found the cost the gates did not price.** The 9–18 Hz sensitivity waterbed was in the
   design agent's own table; nobody had gated it. And the byte-exact steady state at tiny demand is a
   consequence of the quantum that no cal-only fb-pole change can avoid.

## 3. Process lessons

- 🛑 **Write the FAIL criteria before the image exists, and then obey them.** The prereg said a B(1–4)
  FAIL is "do not flash"; when B failed, the verdict followed. The alternative — re-litigating the
  criteria with the FAIL in hand — is what makes a pass theatre.
- 🛑 **A band-maximum gate is blind to a waterbed.** "Max Ms over 12–26 Hz" read ×5 better while every
  fit was worse over two octaves below it. Gate sensitivity pointwise, over the whole band a lever can
  move, and against the worst fit.
- 🛑 **A linear "dc = 1.000" does not test the integer loop.** The steady state must be read from the
  byte-exact chain at the amplitudes the car actually spends its time at.
- **Independent decoders catch each other.** Adversary A's own branch decoder had a displacement bug
  that a control could not see until it exercised a long branch; adversary D found two opcode-field
  collisions (0x3C/0x3D jr vs 6-byte load; 0x3F ld.hu vs mul/setfcc) — hw2 bit 0 discriminates both.
- **Agents that re-derive their own load-bearing claim keep catching themselves** (the tracer's
  monitor-vs-governor correction; `openloop`'s estimator test; `combfix` killing its own design B). Keep
  briefing that way.
- **Read the agent-memory store before tracing.** The r24 tracer found six of its findings already
  recorded after it finished.

## 4. On disk

- **On the car:** V282 (rwd sha256 `618365154e3ffdbb073c00a60173508291f0a18340d6a4f7d39cdd4b2a5b7e22`).
- **Built, not flown, CLEARED over one dissent — THE FLIGHT CANDIDATE:** V292 rwd
  `$ACCORD_FIRMWARE_ROOT/flashing-2020accord/rwd/39990-TVA,A160-V292-V282BASE-EFCAVE.C4C00.6D74-FBPOLE.10HZ.962.958-R24.4725-B3.FBSTATE-KP.FLAT.Y0-CAVE.R24CMP.B5.B6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP-0x13000-0x100000.rwd`
  sha256 **`6d2784b5e27e2f21a909f552ac786f74fe28991dcbc275bf7ae03fb61f9fc20c`**; image `_v292_…_plain_image.bin`
  sha256 **`d1128232993d3a1dcfa4afecb279976f014e6c940f36d88b87db9f2aee3aef33`**; script `build_v292_tva.py`
  (sha256 9bf135ab…, frozen). Design `DESIGN-V292-FBLP-CAVE-2026-09-13.md` (+ errata), mirror `v292_cave_mirror.py`,
  prereg + verdicts `ADVERSARIAL-V292-PREREG-2026-09-13.md`, reports `ADV-V292-{A,B,C,D}-2026-09-13.md`.
- **Built, not flown, SUPERSEDED-DO-NOT-FLASH by V292:** V291 (C10) rwd
  `$ACCORD_FIRMWARE_ROOT/flashing-2020accord/rwd/39990-TVA,A160-V291-V282BASE-FBPOLE.10HZ.962.958-R24.4725-B3.FBSTATE-KP.FLAT.Y0-CAVE.R24CMP.B5.B6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP-0x13000-0x100000.rwd`
  sha256 **`8ce8d5b7c7cda973a04fbe9a061090c76121b6a136d1bba18d1b67fd24530533`**; plain image
  `_v291c10_…_plain_image.bin` sha256 **`a66f9c54b21031d3948cf1f60fbcadc6ac44d422c01d5a357b19aa0d23144657`**.
  Exactly one V291 rwd on disk (verified by listing and by re-hash at close-out). Script
  `analysis-2020accord/builds/v108_plus/build_v291_tva.py` (frozen).
- **Design / review / traces / wire:** `docs/specs/design/DESIGN-V291-FBLP-2026-09-13.md`;
  `docs/review/ADVERSARIAL-V291-PREREG-2026-09-13.md` + `ADV-V291-{A,B,C,D}-2026-09-13.md`;
  `docs/traces/TRACE-2026-09-13-{fb-lag-filter-bytes,r24-lane-transfer,lkas-lane-to-aggregator-and-ghidra-gap}.md`;
  `rlog-tools/studies/grind/{OPENLOOP-RING-DAMPING,B-OF-F-V282,ROUTE-6C-ATTRIBUTION}-2026-09-13.md` and the
  `openloop_*.py`, `bof_v282.py`, `b_of_f_v282.py`, `r24_lane*.py`, `r24_plant_refit.py`,
  `fork_comb_*.py`, `v291_b7_state_sign_sizing.py` scripts; `docs/research/FORK-COMB-RECONSTRUCTION-2026-09-13.md`.
- **Fork (`../openpilots/raayyymond-StarPilot/StarPilot` @ Dom):** the `ModelCurvatureLead` patch applied,
  UNCOMMITTED, toggle OFF; the operator's own uncommitted SR-map refit untouched. Not pushed.
- **Ghidra:** `code.bin` analysed over 0x2A508–0x2B421 and SAVED (2086 → 2090 functions).
- **Golden model:** untouched; contract re-verified — 90 symbols, `_self_check()` + `_demo()` stdout
  2,512 B sha256 `740f4bcd0534212a0c200a9359b0b4318e1419bea33823d66e2e89c12961102d`.
- **Memories:** seven new kit notes under `memory/accord/{mechanism,firmware,builds}/` and
  `memory/feedback/measurement/`, pointers at the top of `memory/MEMORY.md`; two harness auto-memory
  notes. The tracer store gained four files (`.claude/agent-memory/firmware-codepath-tracer/`); two
  existing tracer memories need the corrections in STATE §CORRECTIONS 6 — **not edited, ask first.**
- **STATE.md** is 20 KB: the 09-09/09-10 decision boxes and the 84 finding blocks are archived under
  `docs/archive/STATE-ARCHIVE-2026-09-13-*.md`. `BUILD-LINEAGE.md` (229 KB) and the lever index (193 KB)
  are over the 150 KB soft target — split next.

## 5. The operator's instructions this session
- The goal (verbatim in substance): V282's authority AND no grinding, with StarPilot changes if necessary.
- Subagent model policy: never Fable; Opus for hard tasks, Sonnet for trivial — saved as a feedback memory.
- "newest route is on V282" — confirmed from the tap.
- The 2026-09-10 fork rule still governs: fork changes for grinding only, no LPF, no added lag, no
  authority cut. The comb patch passes the authority test (|H| ≥ 1) but is a lag above ~3.5 Hz relative to
  today's hold — flagged on the page; the toggle is OFF.

## 6. Open items
1. **The operator's decision on V292** (V291 is superseded). `B-IV-AND-KAPPA-2026-09-13.md`
   closed B3; the residual ×1.95 scale on the r24 lane's product is characterised but not physically named
   (a frequency-resolved κ would).
2. **Two premises to close before spending on the sp = 3 point again:** gp-0x6806's state while engaged (the
   ±102 deadband on y, B2 §7.2) and the r24 fold's motor-gain factor (B2 §7.1 — re-run the V291 §4.2/§11 folds
   with K included; expected: every folded number improves, f0 18.4 Hz). Whether the 9–18 Hz shoulder is an
   acceptable price is the operator's call; a V293 with error feedback through the output lag would close the
   sp = 3 clause as written for ~0.1 deg/s.
3. **The IMU** — still the top missing instrument.
4. **The transient test** — now the ζ_eff measurement, not the mechanism test.
5. **`0xC61C0/C2/C4`** still has no lineage entry; the two tracer memories in STATE §CORRECTIONS 6.
6. **Kit trap** (adversary C): `encode_eps.crack_cipher` returns `(None, None)` on failure and
   `bytes.translate(None)` is a silent no-op; `roundtrip`'s default part-number regex cannot match
   `39990-TVA,A160`.
