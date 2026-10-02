# JUDGE — minimality-and-verifiability (V299 design round, 2026-10-02)

**Role.** Panel JUDGE, lens = **minimality and verifiability**. Author: a SUBAGENT of the orchestrator.
**Status:** ANALYSIS ONLY. No image built, nothing flashed/sent, no fork/firmware/golden-model/STATE/lineage/git edit.
**Labels:** EVIDENCE = I re-ran the harness on the V298 image (sha `177abf04…`) this session, method named; BELIEF = inherited model/inference.
One automated safety-classifier interruption hit a file-reading turn; I noted it and continued (defensive engineering, nothing sent to a car).

**The lens, stated as a test applied identically to every candidate:**
1. **Minimality** — fewest firmware bytes, fewest/smallest code caves, fewest new RAM words, *for the loop structure the goal needs*. In-place immediate/branch edits rank above a relink; a relink above a new state word; one state word above two (operator doctrine 2026-09-30). Cal-only is a preference between designs giving the SAME loop, never a constraint.
2. **Observability** — every new term readable from ONE short symptomatic drive, by an instrument already on the wire or added in the same build; the inert tap preferred to the blind dose.
3. **Verifiability** — every decision-bearing number reproducible from the image + the harness: a byte-exact V298 reproduction control, an H1 interpreter run against an integer mirror, negative controls that fail, GATE-1 census, CRC.

## 0. What I re-ran this session (EVIDENCE — all < 30 s)

| check | result | wall |
|---|---|---|
| `s3_bytes.py` | every cited cell holds the claimed bytes; CRC trailers reproduce (`zlib.crc32`); D1c 152 B diff / sha `80dd2052`; D3a sha `83b9799b`; D4b 312 B / sha `59b90cbd`; pattern `206e2c01` unique @0xC4C6A, `206e0002` @{0x6271E Honda, 0xC4C62}; free run 0xC4D04–0xC4FF0 = 748 B 0xFF | 0.7 s |
| `s3_gate1.py` | gp-0x6a32 (D4b): 0 absolute literals, movhi pairs adjudicated bit-ops; gp-0x6c44 (D5a): 0 direct accessors, 0 movhi pairs, **14 nearby bases NOT decode-adjudicated** | 0.1 s |
| `s3_bar_sign.py` | D1 +8·s10 agrees 0.942 with today's bar; D2/D5 −8·s10 = 0.058 (**inverted**); co_tq/ang_output/cs_tqeps all 0 on r79 (free); ld_lat = 0.35 | 0.1 s |
| `d1_cave.py` | **C1: V298 re-derived byte-for-byte** (sha `ef1861e10421`); D1c flight 252 B fits; **H1 0/8000**; neg controls 29/1500 and 159/1500 (fail as they must) | 11.7 s |
| `d3_h1.py` | V298 control 0/712; **D3a 0/5748 valid, 0/5516 op-skip, 0/736 camera**; neg controls 244/712 | 7.5 s |
| `d4_cave.py` | **control reassembles V298 byte-for-byte** (sha `ef1861e10421` == image); D4b 312 B ends 0xC4D38 (fits); **H1 0/20000 incl. the state word** | 5.9 s |

Firmware-minimality ranking (operator's priority), firmware-moving candidates only — reproduced from my `s3_bytes` run:
**D2 (0 B, no cave) < D5b (5 B, in-place) < D3a (9 B, in-place) < D4a (14 B, in-place) < D1c (152 B diff, cave 260→252 relink, 0 RAM) < D4b (218 B, cave 260→312 relink, +1 RAM) < D5a (~110 B, NOT assembled, cave→~330, +1 RAM).**
Caveat the raw count hides: D1a/D1-a2/D3a/D3b/D4a/D5b are in-place immediates (**no relink**); D1c/D4b/D5a relink the whole cave (every jr/bcond re-encoded, table pointer moved → must re-run H1 + Ghidra on the BUILT image). D1c's 152 is a relink-tail artifact; its *semantic* change is 3 instructions and the cave SHRINKS 8 B.

## 1. Ranking under the lens

### #1 — D1c (D1-firmware-minimal, recommended impl b)
**Why #1.** It is the minimal firmware change that *gives the structure the measured mechanism needs* AND is fully verified AND carries a zero-byte inert instrument. Semantic change = 3 instructions of integral policy (hard freeze 512→1229; remove the 16-B opposing clause; +8-B sign-referenced A3 bound); **cave SHRINKS 260→252, 0 RAM, 0 new state word**. Linear loop byte-identical to V298 ⇒ GATE 2 = V298's (S1 finding 1, hex table == image).
**Verifiability (the strongest of any firmware-mover, all reproduced by me):** C1 re-derives V298 byte-for-byte; H1 0/8000; both negative controls fail; and the new term is read by a **zero-byte inert tap** — the rule-identity replay vs the 0x1AB tap (V298 wins 18/18 r79 windows, dR² +0.605), run reversed next drive. This is the doctrine's gold standard ("prefer the inert tap to the blind dose"). Its bar formula is the only one with the correct sign (0.942).
**Why it beats the cheaper in-place edits:** its +8-B asymmetric bound is *structurally required* — the measured N1 hazard (an outward 511-word light hand) cannot be separated from the reaction twist by any threshold (D1a, = D5b's firmware, is MEASURED at 15.9°/18.6° lurch; D1c restores 5.05°). So 5 bytes do not "give the same loop more cheaply"; they give a loop with a measured hand-safety regression. D1c spends the fewest bytes that hold the structure.
**Honest minimality debts:** (a) it relinks the cave (larger re-verify surface than an in-place immediate); (b) it cannot touch the fork's O1 relay/re-slew/cap/clip (notes 2 authority), so a fork graft is needed; (c) version A16A left open (S3-7: bump to A16B, +1 B, for carFw attribution).

### #2 — D2a (D2-fork-first, impl a)
**Why #2.** The **absolute firmware minimum**: 0 bytes, 0 caves, 0 RAM, GATE 1 vacuous, **no bricking class at all** (the kit's only bricking class is code caves — D2 has none). Every term param-gated with a V298 default and a one-toggle restore; it is the only candidate that *adds* margin to a fork-coupled loop (O1 lead 0 → GM 6.0→9.4 dB at 60 ms, S1 finding 4). Instruments land in confirmed-free log fields (co_tq/ang_output/cs_tqeps = 0 on r79, I re-checked).
**Why it loses to D1c under this lens:** it leaves the **measured note-4 mechanism** (the firmware integrator freeze) entirely untouched — its own declared miss; S2 confirms the relay survives (I kept 0.46–0.53). Its central note-4 claim is "unchanged / may rise (BELIEF)". Plus two must-fix verifiability defects: **bar sign inverted** (S3-1, I re-measured 0.058 — use −eps/2461) and the "freq 0 never affects canValid" claim is false on the counter path (S3-2). So it is maximally minimal and zero-risk, but its edit is *not verifiably the fix for the symptom the goal names first*.

### #3 — D3a (D3-authority-first, recommended impl a)
**Why #3.** 9 in-place bytes (no relink), 0 RAM; the loop change (G row-0 ×1.2→1.0) is GATE-2-clean (worst +7.3°, independently reproduced in S1) and H1 reproduces here (0/5748 + 0/5516 + 0/736; neg 244/712). Strong firmware minimality and verifiability, and it is the only candidate that lifts low-speed stiffness without a relink/RAM.
**Why below D2a:** three verifiability/safety gaps. (a) Its own time sim shows the raised 1229 freeze **still fires on the faster slew's own twist** (hand-lost 0.41 at 3 m/s) — the claimed fix is partly self-defeating, and replay vs sim disagree on the number that must move. (b) S1 FLAG: the K3 lead is applied *after* the clip, so it is positive wheel-rate feedback while the clip binds (GM 9.6→6.4 dB at 60 ms) — fixable (take ṡ pre-clip, D5's placement). (c) weakest override (S3-5): a 600–1200 hand never yields the setpoint while P can reach 75 % of rail, and A16B is accepted without coupling to K2.

### #4 — D4b (D4-smoothness-first, recommended impl b)
**Why #4.** Thoroughly verified (control reassembles V298 byte-for-byte; H1 0/20000 incl. the state word; GATE-1 static-clean + V288 on-car flight precedent for gp-0x6a32), and it attacks note 4 directly with a motion-gated freeze, with a same-build wire instrument (0x14A b4.7 = sign(h)).
**Why this low despite good verification:** it is the **heaviest flyable firmware** (218 B, cave grows +52 B, **the only new RAM word** of the recommended set), and its fork terms are **code constants, not toggle-expressible** — against the operator's standing preference. On the minimise-firmware/minimise-RAM priority it ranks far below the in-place and zero-byte candidates. Its felt-result claim also rests on the r79 enrichment statistic (BELIEF; the sim does not reproduce the stall-surge trains). D1c reaches the same hand/twist-separation safety result with +8 B and 0 RAM instead of +52 B and 1 RAM.

### #5 — D4a (GB-S13, D4 impl a)
**Why #5.** 14 in-place bytes, verified slopes, but **FAILS the common frequency gate** (S1: 23 R2-box fails on the ms_free family, two engines agree; curve-hold ζ 0.040→0.010 at exactly the 15–17.5 m/s knots where S1 §2.9 shows the model under-reads real loop gain). And it does **not move the freeze relay** (its own declared miss). Minimal in bytes, fails verification on the stability gate under the panel definition — needs an orchestrator ruling on ms_free gating before it is even eligible.

### #6 — D5b (D5-architect, primary impl b, firmware part)
**Why #6 despite 5 bytes.** Its firmware is maximally minimal and verified (FZ2 dead-branch confirmed by Ghidra structure), **but it is byte-identical to D1a**, which D1 MEASURED failing N1 (15.9° outward 511-word lurch; S2 confirms D5b 18.6° worst), and S3 confirms D5's fork O1 (ON at 600) does not cover a ~500-raw 511-word hand. So the 5 cheap bytes **do not give a structure that holds hand safety** — the exact trap the 2026-09-30 doctrine warns against. Add the inverted bar sign (S3-1) and parser-freq-50 non-optional (S3-3, must-fix). **PENDING DISQUALIFIER** on hand safety until scored on D1's `rb_n1` out_2_511 lens; S2 already scores it 18.6°.

## 2. Disqualified / not eligible this round

| candidate | ground (lens) |
|---|---|
| **D3b** | DO-NOT-FLY: SCL/PCL 19072 opens the soft-EME band 5120–~5900 **unreplayed** (S3-8, designer concurs); rail reached on 0 ms ⇒ no measured benefit for the interlock cost. Fails verifiability (unenumerated consumer) + minimality (benefit nil). |
| **D5a** | NOT-RECOMMENDED: the cave was **never assembled** (bytes unverifiable — no H1 possible), GATE-1 **decode adjudication of 14 nearby bases owed** for gp-0x6c44 (I confirmed 0 direct accessors but the bases are not cleared), FAILS S1 (washout collapses the O1 loop to 1.5 dB; GATE 2 only +0.4°). Designer does not recommend it. |
| **D1a** | NOT-FOR-FLIGHT by its own designer: cal-only, measured N1 FAIL (15.9°/8.0°). It is the *proof* the cal space cannot hold the structure — valuable as evidence, not as a build. |
| **D4b+GBS13** | inherits D4a's GATE-2 FAIL plus D4b's weight (~231 B, not built). Disqualified via D4a. |

Not disqualified but dominated / not a standalone primary:
- **D2b** — dominated by D2a for this lens: largest fork diff (~100–120 lines + second-order limiter + plan-lead); its 20 Hz interpolation and 1500 deg/s² limiter are **outside the frequency scorer's scope** (S1 unverified) and its lead is unverified by S1. It is the authority follow-up, not the minimal first drive.
- **D1-a2 (G0-1400)** — a legitimate *optional later* stiffness dose (4 in-place bytes, GATE-2 clean), FLAG at the 5 Hz edge (S1). A graft, not a competing candidate.
- **D1 fork bar** — not a competing candidate; it is the correct-sign bar component every candidate needs (only D1 has the sign right).

## 3. Process notes the build round must carry (from this lens)

- **Every relinked cave (D1c, D4b, D5a) must re-run H1 + the Ghidra decode on the BUILT image + the adversarial pass** (S3-10). Patch by address, never pattern (`20 6e 00 02` also at Honda 0x6271E).
- **No golden-model `_self_check_v299` mirror exists yet** (S3-11): D1c's `d1c_cave`, D3's snippet, D4b's `d4b_ref`, D5b's `v299b_frozen` must be grafted into `eps_chain_control.py` and the 94-symbol / hash contract re-checked before any build.
- **The bar fix must use D1's sign** (+8·s10 → steeringTorqueEps, bar = eps/2461) OR, for a carState that stores −8·s10, draw −eps/2461. D2/D5 as written are inverted.
- A16B is fail-safe against an un-updated fork (S3); recommend bumping D1c to A16B (+1 B).

## 4. Verdict in one line
Under minimality-and-verifiability, **D1c wins**: it is the fewest-bytes firmware edit that holds the structure the measured note-4 mechanism needs, it is byte-exactly reproduced and H1-clean with failing negative controls, and its central new term is read by a zero-byte inert tap. **D2a** is the firmware minimum and the right zero-risk fork-graft donor but leaves the named symptom's mechanism unverified-as-fixed; the cheaper in-place firmware edits either change a loop that fails the gate (D4a), partly undo their own fix at the new authority (D3a), or re-use firmware measured to break hand safety (D5b).
