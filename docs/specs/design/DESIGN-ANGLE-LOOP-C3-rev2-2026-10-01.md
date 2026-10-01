# DESIGN C3 rev2 — the REVISION JUDGE's merged angle loop (2026-10-01): PRIMARY C3-rev2-P, FALLBACK C3-rev2-F

**Status: DESIGN ONLY.** Nothing built, flashed or sent; the fork was not touched; no `.rwd` or image was written.
Ghidra read-only this session (`disassemble_bytes dry_run:true`, `list_open_programs`) on stock `code.bin` and the
open V294 program (code-identical to V295 except cal `0xC63EA` + CRC); nothing was saved. Python is the `bin_decompile`
env. Every byte-level number is read from the V295 image (sha `5c044d65…`) or executed by the panel-2 common scorers'
own interpreters; the judge-only re-runs are in `_scratch/angle_loop/c3-rev2-judge/`.

**Author:** the REVISION JUDGE, a SUBAGENT of the orchestrator `main`.

**What this page is.** Two independent revisions of the refuted design C3 were submitted:
- **rev2-A** (`DESIGN-ANGLE-LOOP-C3-rev2-A-2026-10-01.md`): PRIMARY **R1-P** = C3-P + Ki 56→40, a **setpoint-referenced**
  integral bound (byte-neutral), a raised dip knot (min G 520), and a `cmovh r0,r16,r16` that zeroes E on an invalid
  rate (+4 B open-loop fail-safe). Cave 226 B. It also **built** a firmware camera interlock **R1-P-cam** (+20 B) and a
  pol-free fallback **R1-F** that keeps the fresh-rate read purely as a validity flag for the same E:=0 fail-safe.
- **rev2-B** (`DESIGN-ANGLE-LOOP-C3-rev2-B-2026-10-01.md`): PRIMARY **C3B-P** = C3-P + Ki 40, a full **GB** table re-fit
  (min G 559), the A3 **θ-referenced** bound KEPT + an **opposing-hand freeze** (sgn 300, +16 B), and an **op-skip**
  `jr 0x2a164` on an invalid rate (+2 B, Honda's own epilogue). Cave 240 B. Fallback **C3B-F** (held D, pol-free) which
  **declares** a rate-invalid PI-only ring rather than skipping. It **escalates** the camera to the orchestrator.

**The verdict of this judge: MERGE.** The merged design is **anchored on rev2-B's C3B-P** (the only submission
re-scored on the COMMON scorers run unchanged, and the one whose N1 fix the judge's own re-runs confirm is the effective
one), **adopts rev2-A's F3-safe-fallback insight** (close C3B-F's one declared unstable fault state, pol-free), and
**offers rev2-A's built camera interlock as a non-default variant** while escalating the camera ruling. The merged
primary **is C3B-P byte-for-byte**, so it is re-scored by construction; the two adopted pieces are fault/safety-path
edits that the scorers do not exercise, stated as such.

Every decision-bearing claim is **EVIDENCE** (method given) or **BELIEF**. Code is cited by address or grep string.

---

## 0. The answer in one page

### 0.1 The merged implementations

| | **C3-rev2-P (PRIMARY) = C3B-P** | **C3-rev2-F (FALLBACK)** | **C3-rev2-P-cam (variant)** |
|---|---|---|---|
| base | rev2-B C3B-P, byte-for-byte | rev2-B C3B-F + an F3-safe hardening | C3-rev2-P + rev2-A's `gp-0x6803==2` gate |
| D operand | fresh 1 kHz `gp-0x6abe`, Honda-guarded, Kd 48 | held `gp-0x6a56` via E5, Kd 24 (**pol-free**) | = primary |
| Ki (F1) | **40** (cal `0xC63E6`, was 56) | 40 | 40 |
| table (N2) | **GB-P**, 6 knots, min **G 559** | GB-F, min G 560 | GB-P |
| integral bound (N1) | A3 θ-referenced + **opposing-hand freeze sgn 300** | same | same |
| rate-invalid (F3) | **op-skip `jr 0x2a164`** (Honda epilogue, no torque path) | **recommended:** validity-read op-skip (pol-free); **default C3B-F:** declared PI-only ring | op-skip |
| cave | `0xC4C00`, **240 B** flight (238 B score), sha `9a10cdc4ec75` | `0xC4C00`, **220 B** (default) / **≈240 B** (hardened), sha `9de9365fa952` (default) | **246 B**, sha `1159ee1cd0fc` (rev2-A's R1-P-cam bytes) |
| in-place set | E1 E2 B2 A2 E4 HOOK **OPH** V1 (20 B) | E1 E2 B2 A2 E4 HOOK **E5a E5b** V1 (23 B) | primary's + none (r25 already live) |
| cals changed vs V295 | 24 B (Ki 40) | 24 B (Kd Y = 24) | + fade record `0xE54FC` ← `0xE564C` (24 B) |
| bytes written | 20 + 24 + 240 = **284**, RAM 0 | 23 + 24 + 220 = **267** (default) / ≈287 (hardened), RAM 0 | 20 + 48 + 246 = **314**, RAM 0 |
| GATE 2 R2-box (θ=0), common scorer | **0 / 0** | **0 / 0** | = primary |
| GATE 2 curve-hold op-points (F1) | **0 ρ≥1; every credible member passes** | **0 ρ≥1; every credible member passes** | = primary |
| goal time fails ≥ 8 m/s, common scorer | **0** | **0** | = primary |
| pol = −1 dependence | yes (R1 INVERTED drive 1) | **none** | yes |
| 13 Hz anti-damping vs V295 | 0.79× (κ 1) / 0.93× (phys, ages 1-10) | 1.9× — creep-grind band (M-13, R4) | = primary |

**The primary C3-rev2-P is C3B-P unchanged. It passes, on the COMMON scorers run unchanged, the brief's θ=0 GATE 2
(0 R2-box), the curve-hold operating-point GATE 2 that refuted C3 (0 ρ≥1, every credible member), and every goal time
criterion in every band ≥ 8 m/s.** (EVIDENCE: rev2-B `rb_final freq`/`rb_final time`, controls reproduce the round-1
anchors; the judge re-verified the N1 crux, the N5 claim, the F3 op-skip target and the dip tables independently — §2.)

### 0.2 Why this merge, finding by finding — the judge's own checks

| finding | merged resolution | why this over the alternative (EVIDENCE) |
|---|---|---|
| **F1** op-point instability (refuting) | **Ki 40** (both revisers agree) | `opbreak_ki40` / `gate2_ki40`: 0 exact ρ≥1; every member through J1.3 clears both bars; only the J≈2 ms_free family misses (ρ<1), report-only. Identical in both submissions. |
| **N1** outward / nudge release lurch (refuting) | A3 θ-bound **+ opposing-hand freeze sgn 300** (rev2-B) | **Judge re-run at Ki 40** (`n1_ki40.py`): with the freeze present the bound reference (θ vs setpoint) is **identical on every N1 scenario**; the setpoint-bound (rev2-A's fix) only differs WITHOUT the freeze, where it **worsens** the inward partial drag (12.5-22: 9.6° vs θ's 5.3°). The freeze is the effective fix: nudge 2.0°, partial drag 7.2°, outward ≥12.5 = 5.6° — all < 8°. |
| **N5** reversal / windup overshoot | Ki 40 (reduces it); residual declared | **Judge re-run** (`rev_n5.py`): at Ki 40 the worst reversal overshoot is ≈0.16·A (θ-bound) vs 0.19·A at Ki 56; the setpoint-bound gives 0.18·A — **no improvement**. rev2-A's "reversal overshoot 0.00" is the MIN over members, not the max; the worst case is ≈0.18. Declared under R9. |
| **N2** G < 512 one-sided quantum (refuting) | **GB-P table, min G 559** (rev2-B) | Judge computed both tables (`tables.py`): rev2-A's raise-one-knot gives min 520; rev2-B's full re-fit gives min 559 **and** a higher dip region (11.5 m/s: 588 vs 544), so more margin over the 512 floor AND better small-signal in the dip. Same 0 code bytes. |
| **F3** rate-invalid PI-only instability | **op-skip `jr 0x2a164`** on the primary (rev2-B); **harden the fallback the same way** (rev2-A's insight) | **Judge verified in Ghidra** (dry-run, stock `code.bin`): `0x2A164` writes `gp-0x6cf8 := 0x7FFFFFFF` (sentinel) and `gp-0x6dd0 := 0` (I state), and `0x29A5C`/`0x29A64` are the A2/B2 `jr 0x2a164` skips — so the op-skip reuses Honda's own epilogue and leaves **no torque path** on an invalid rate. Fewer bytes (+2) than rev2-A's E:=0 (+4). The fallback's declared PI-only ring (C3B-F) is closable the same way, pol-free — **recommended**. |
| **F2** τ_o<1 s outer-loop ring below R3* | **R3\* widened to 0.25 Hz** + τ_o ≥ 1 s a CHECKED fork prerequisite | Both revisers agree; refuter F2 shows τ_o ≥ 1 s has PM ≥ 56°, GM ≥ 8 dB. |
| **F4** Re(T/ω) frame/phase fragile | restated at **physical κ 0.866 / ages 0-9** | Both revisers restate; 13 Hz = 0.93× (ages 1-10) / 1.33× (ages 0-9); 20 Hz 0.55× (goal met). M-F4, R4 watch. |
| **F5/F6/F7** | declared / cosmetic | F5 two-mass modal ζ below V295 on a fraction, no peak > +3 dB, 0 unstable (R4). F6 sub-LSB cycle (< R3* band). F7 hex typos fixed in the listings. |
| **N3/N4/N6/N7/N8** | declared, each with a stop band | §5. |
| **bytes F1** stock camera on a relay close | **ESCALATED** to the orchestrator (both agree) + rev2-A's built interlock offered as C3-rev2-P-cam | §6 H-cam. The firmware interlock's discriminator premise (camera 0xE4 byte-2 field 3:2 = 0) needs re-measure (trace open item 4) and arms the ×1.8-2.1 fade; default first flight = camera-LKAS-off, the standing practice on every flown build V282→V295. |
| **bytes F2/F3/F4/F5** | declared / stock-parity / pol-handled / build-time | §6. |

### 0.3 The rulings this judge makes (and the one it escalates)

1. **MERGE, primary = C3B-P.** It is the submission re-scored on the common scorers themselves (rev2-A used validated
   refuter mirrors), its N1 fix is the one the judge's re-runs confirm, and it carries the most N2 margin and the
   cheapest, Ghidra-verified F3 fail-safe. **The primary needs no re-score — it is C3B-P byte-for-byte.**
2. **N1 = the opposing-hand freeze, NOT the setpoint-referenced bound.** The judge's Ki-40 re-run shows the setpoint
   reference gains nothing once the freeze is present and loses on partial drag without it, and does not fix N5. The
   A3 θ-bound is kept (byte-neutral vs C3); the freeze (+16 B) is the N1 edit.
3. **Harden the FALLBACK's F3.** rev2-B's C3B-F declares a rate-invalid PI-only ring (ρ 1.0017 on 19/2888 ms_free
   points). rev2-A showed a held, pol-free cave can still be made F3-safe by a validity read. Under *verify thoroughly,
   nothing waived*, the recommended fallback adds the same `jr 0x2a164` op-skip (≈+20 B, pol-free — `gp-0x6abe` is a
   branch condition only, not in the D sign). The 220 B C3B-F stands as the byte-minimal alternative if the orchestrator
   accepts the declared rare fault.
4. ⚠ **ESCALATED — bytes-lens F1 (the stock camera on a relay close) is a HAZARD-CLASS RULING the judge cannot make.**
   Either camera-LKAS-off is ruled acceptable for this hazard class (program precedent, every flown build), or the
   firmware interlock C3-rev2-P-cam is built — **and before it is relied on, the camera 0xE4 byte-2 field 3:2 = 0
   premise must be re-measured on bus 2** (trace open item 4). This is the one finding the merge leaves open.

---

## 1. The merged primary C3-rev2-P — every byte (= C3B-P)

### 1.1 In-place code edits (C3-P's set, re-asserted against V295; Ghidra dry-run this session)

| id | addr | V295 → bytes | instruction (Ghidra dry-run) | loop term |
|---|---|---|---|---|
| E1 | `0x28F4C` | `24 3f aa 95`→`24 3f 00 96` | `ld.h -0x6a56[gp],r7` → `ld.h -0x6a00[gp],r7` | x := θ (0.1° counts) |
| E2 | `0x28FA4` | `89 d1`→`c9 d1` | `subr r9,r26` → `add r9,r26` | r26 = 8θ[n] + 8θ[n−1] |
| B2 | `0x29A50` | `e2 47 00 00`→`e0 df 34 43` | `setfe r8` → `cmovne r0,r27,r8` | r8 := (request==1) ? bVar2 : 0 |
| A2 | `0x29A56` | `da 05`→`b2 05` | `bne 0x29A60` → `be 0x29A5C` | PID runs iff ramp ≠ 0 ∧ r8 ≠ 0 |
| E4 | `0x29D6A` | `08 80 ed 80`→`24 87 52 96` | → `ld.h -0x69ae[gp],r16` | sp := gp-0x69ae |
| HOOK | `0x29D76` | `c2 82 ba 81`→`89 37 8a ae` | → `jarl 0xC4C00,r6` | the hook (r6 = 0x29D7A on entry) |
| OPH | `0x29EE0` | `10 40 bb 41`→`1a 40 00 00` | → `mov r26,r8 ; nop` | D operand = r26 (the cave's fresh op) |
| V1 | `0x1310D` | `30`→`41` | F181 `…A160` → `…A16A` | the fork interlock string |

(EVIDENCE: the current V294 bytes at every site match the "V295" column; the new encodings decode as stated —
re-asserted from rev2-A/rev2-B's dry-run decodes and the judge's own `0x29A48..0x29A6E` disassembly this session, which
also confirms r25's single writer `setfe r25 @0x29A82` is untouched.)

### 1.2 The cave (`0xC4C00`, 240 B flight = 198 code + 42 table; 238 B score cave)

The cave is C3-P's **E2-A3 cave** (`shl 2 ; sub r26 ; fresh-op guard ; G walk ; E·G ; A3 policy ; FRZ/DONE`) with three
additions over C3-P, each decoded by Ghidra dry-run (rev2-B §1.2, re-checked) and executed by the common time scorer's
own V850E2 interpreter against `CandLane.cave_stage` (H1: **0 / 8000**; `e2_asm` H1 on the fresh score cave: **0 / 30000**):

1. **opposing-hand freeze** (after the hard-freeze test): `movea 300,r0,r13 ; cmp r13,r8 ; bnh N ; ld.h -0x4f60[gp],r9 ;
   xor r16,r9 ; blt FRZ ; N:` — r8 = |driver torque| (`gp-0x4f68`), r16 = E′, r9 = signed hand torque (`gp-0x4f60`). A
   hand pushing **away** from the setpoint with |tq| > 300 (`xor r16,r9 < 0` ⇔ sign(hand) ≠ sign(E′)) freezes the I, so
   it cannot unwind into a release lurch (N1). **+16 B.**
2. **GB-P table** (6 knots, §1.3) substituted for G-P48's rows — the N2 fix, **0 code bytes**.
3. **op-skip** (flight cave): the op-validity `cmovh r0,r26,r26` is replaced by `cmp r13,r8 ; bnh CONT ; jr 0x2A164` —
   on an invalid rate the whole PID is skipped to Honda's own A2/B2 epilogue. **+2 B.**

**EVIDENCE (judge, Ghidra dry-run on stock `code.bin` this session):** `0x2A164` is the shared skip epilogue — it stores
`0x7FFFFFFF` to `gp-0x6cf8` (the first-tick sentinel, `st.w r16,-0x6cf8 @0x2a18c`), `0` to `gp-0x6dd0` (Honda's I state,
`st.w r24,-0x6dd0 @0x2a190`) and zeroes the lane's `gp-0x6b2e..-0x6b36` state, then runs the decaying output path. And
`0x29A5C` / `0x29A64` are the A2/B2 `jr 0x0002a164` skips (bytes `80070807` / `80070007`). So the op-skip routes an
invalid rate into Honda's proven skip path: **no new torque path exists on an invalid rate**, GATE-1-clean (0 RAM written
by the cave; the epilogue is Honda's own). The exits are C3-P's: `jr 0x29D7E` (freeze) and `jmp [r6]` → `0x29D7A` (normal).

### 1.3 Calibration cells (24 bytes; Ki is the only one differing from C3-P)

| cell | addr | V295 | **C3-rev2** | what it is |
|---|---|---|---|---|
| a | `0xC63E8` | 1011 | 0 | fb pole → pure 2-sample sum |
| b | `0xC63EA` | 1050 | 8192 | s_new = 8θ |
| C | `0xC62E6` | 1024 | 65535 | r26 clamp |
| DB | `0xC62E4` | 4 | 0 | I deadband |
| **Ki** | `0xC63E6` | 0 | **40** | **F1: PI corner 0.62 → 0.44 Hz, below the curve-hold crossover** |
| ICL | `0xC61BA` | 10240 | 8192 | I clamp, below V295's own 10240 |
| DCL | `0xC61B6` | 0 | 10240 | D clamp |
| Kp Y | `0xE5384` | 960 | 112 | Kp flat (selector 7) |
| Kd Y | `0xE5126` | 0 | 48 | D = (48·op) >> 3 |

**GB-P table** (in the cave; EVIDENCE `rb_table`, judge-recomputed `tables.py`): `(714,1178,1041) (1843,1465,−6264)
(2304,760,−2033) (2707,560,1570) (4032,1068,2118) (6198,2188,0) (0xFFFF,2188,0)`. Walk **min G = 559 @ 11.75 m/s**
(G-P48 was 462; rev2-A's raise-one-knot was 520).

### 1.4 The loop, integer-exact Python (= the function the common grid runs)

```python
def c3rev2p_tick(st, theta, sp69ae, abe, v6a5e, tq4f68, tq4f60, ramp, req, bvar2):
    if not (ramp != 0 and req == 1 and bvar2):                 # A2 + B2
        st.I8 = 0; st.Eprev = 0x7FFFFFFF; return lag_gate(st, 0)
    r26 = clamp(st.s_old + ((8192*theta)>>10), -65535, 65535); st.s_old = (8192*theta)>>10
    E  = s32((sp69ae << 2) - r26)                              # 16(theta_sp - theta)
    if ((abe + 13000) & 0xFFFFFFFF) > 26000:                   # [F3] invalid rate
        return skip_lane(st)                                   #   -> jr 0x2a164: I8=0, sentinel, output decays
    op = abe
    G  = walk(GB_P, v6a5e)                                     # [N2: min G 559]
    Ep = s32(E * G) >> 8
    frozen = (tq4f68 > 512)                                    # hard freeze
    if not frozen and tq4f68 > 300 and (s16(tq4f60) ^ Ep) < 0: # [N1] opposing-hand freeze
        frozen = True
    if not frozen:
        sh = 4 if (v6a5e <= 2880) else 6
        bound = (abs(s16(theta)) << sh) + 1250                 # A3 theta-referenced bound
        if v6a5e <= 1382: bound = min(bound, 4096)             # low-speed cap
        t = (st.I8 >> 10) if Ep >= 0 else -(st.I8 >> 10)
        if t >= bound or (ramp & 0x8000) == 0: frozen = True
    e5 = 0 if frozen else (Ep >> 5)
    I  = clamp((st.I8 >> 3) + ((e5 * 40) >> 3), -(8192<<7), 8192<<7)   # Ki 40, ICL 8192
    P  = clamp((Ep * 112) >> 8, -15360, 15360)
    D  = clamp((48 * op) >> 3, -10240, 10240)
    S  = (I >> 7) + P + D ; st.I8 = I << 3
    return lag_gate(st, fade_and_clamp(S))                     # fade (floor 0.297), SCL, output lag, x ramp, x pol x 5346 >> 15, OCL
```

---

## 2. Method — the merge is re-scored, and the judge verified the deciding cruxes himself

**The primary is C3B-P byte-for-byte, so it carries rev2-B's COMMON-scorer runs unchanged** (`rb_final.py` imports
`panel2/score_freq.py` and `panel2/score_time.py` at module level and registers C3B-P/C3B-F; its controls P2 / E2-A3
reproduce the published SCORE-TIME / SCORE-FREQ cells, and the freq VALIDATE block's six controls reproduce the round-1
anchors — EVIDENCE, cached `score_freq_tables.md`, `rbf_score_time_tables.md`). The two pieces the merge adopts beyond
C3B-P — the fallback's F3 hardening and the camera variant — are **fault/safety-path edits the scorers do not exercise**
(they fire only on an invalid rate or a camera relay close), so they do not change any scored valid-rate metric; that is
stated, not assumed.

**The judge re-derived the four decision-bearing cruxes independently** (`_scratch/angle_loop/c3-rev2-judge/`):

| crux | script | result | bearing |
|---|---|---|---|
| N1 bound-reference vs freeze, at Ki 40 | `n1_ki40.py` (on rev2-B's `rb_n1.Lane2`, a c3nl_sim mirror; CONTROL `theta,56` == `c3nl_sim.Lane` 0/0) | with the freeze, θ and setpoint bounds are IDENTICAL on every N1 scenario; without it, setpoint worsens partial drag (9.6 vs 5.3) | ruling 0.3.2: freeze, not setpoint-bound |
| N5 reversal overshoot at Ki 40 | `rev_n5.py` | θ-bound 0.16·A, setpoint-bound 0.18·A, Ki 56 was 0.19·A | rev2-A's "0.00" is min-not-max; no setpoint-bound advantage |
| N2 dip tables | `tables.py` | rev2-A min G 520, rev2-B min G 559, GB higher through the dip | ruling 0.3 (N2): GB table |
| F3 op-skip target | Ghidra dry-run `0x2A164`, `0x29A48..0x29A6E` | `0x2A164` zeroes I8 + sets sentinel; `0x29A5C/64` are the A2/B2 skips | F3 fail-safe on the primary, CONFIRMED |

The **builder** still runs the actual common scorers on the BUILT table/cals (H2/H3), Ghidra on the BUILT image
(H5–H10) and the mandatory adversarial pass — none waived.

---

## 3. GATE 2 and GATE 1 (EVIDENCE, the common scorers; op-points on the independent refuter model)

**θ = 0 (the brief's GATE 2), common frequency scorer run unchanged** (`rb_final freq`; the integral policy acts only
through FREEZE states = the scorer's I-frozen loop, so the linear PID row is GB-P's / GB-F's):

| | C3-rev2-P (C3B-P) | C3-rev2-F (C3B-F) | bar |
|---|---|---|---|
| R2-box / strict fails | **0 / 0** | **0 / 0** (G-strict = 1 on a reported ×tau6 product, not a gated member) | 0 |
| tier-A box / aged-strict min PM | 58.8° / 56.0° | 60.2° / 50.1° | 45° |
| tier-B box (excl. ms_free) min PM | 39.8° | 40.3° | 30° |
| ms_free×{b_lo,b_q} min PM (ring ζ) | 38.5° (ζ 0.148) / 40.8° | 31.1° (ζ 0.123) / 36.8° | 30° |
| min GM↑ / peak 5–30 Hz / max L20 ÷ V295 | 13.8 dB / −0.2 dB / 0.96 | 6.6 dB / +2.2 dB / 0.83 | ≥ 6 / ≤ +3 / ≤ 1 |
| M20 (κ 1 / physical κ 0.866) | 0.96 / 0.96 | 0.82 / 0.83 | ≤ 1.00 |

**Operating-point GATE 2 (refuter F1, k·sech²(θ_op/sat), Ki 40)** — the test that refuted C3 (EVIDENCE `opbreak_ki40`,
`gate2_ki40`): **0 exact ρ ≥ 1** for both. **Every credible member (through J1.3) clears both bars** (worst non-ms_free:
b_lo×J_hi 32.8°, J1.0 34.7°). The only shortfall is the **J≈2 ms_free family** (ms_free 21.2°, b_lo×ms_free 4.6°,
b_q×ms_free 8.2° — all ρ < 1, no divergence), which the held-out r71b ident disfavours (prefers J ≤ 0.5 at 10–15 m/s)
and which friction masks to ±0.1–0.6° in the refuter's own integer lane. **Report-only, covered by R3\* 0.25–0.9 Hz.**

**Re(T/ω) at the physical κ 0.866 / ages 0–9 (refuter F4, EVIDENCE):** C3-rev2-P 13 Hz **0.93× (ages 1-10) / 1.33×
(ages 0-9)**, 20 Hz **0.55×** (goal's "20 Hz ≤ V295" met); C3-rev2-F 13 Hz **1.9–2.05×** (M-13, R4 10–17 Hz watch).

**GATE 1:** 0 RAM words written. New reads vs Honda: `gp-0x4f60` (signed hand, opposing freeze — a read, same tick as
Honda's `gp-0x4f68`), `gp-0x4f68`, `gp-0x6a00`, `gp-0x6dd0` (read before Honda's own read at `0x29DA4`), a second
`gp-0x6a5e`, and the fresh `gp-0x6abe` (sole writer `FUN_00041464` runs earlier in the same 1 kHz pass — EVIDENCE
rev2-A/rev2-B decompile). The op-skip adds no RAM write (Honda's epilogue owns those cells). No new state word.

---

## 4. Time gates — the goal's own criteria, common time scorer run unchanged (EVIDENCE)

`rb_final time` (Ki 40) on `panel2/score_time.py`; P2 / E2-A3 reproduce the published SCORE-TIME cells.

| goal criterion | C3-rev2-P | C3-rev2-F | bar |
|---|---|---|---|
| tracking (clean) 8–15 / 15–22 / >22 | 0.987 / 0.981 / 0.997 | 0.989 / 0.976 / 0.996 | 0.95–1.05 |
| tracking (replay) 8–15 / 15–22 / >22 | 0.979 / 0.964 / 0.989 | 0.981 / 0.957 / 0.987 | 0.95–1.05 |
| turn-hold a ≤ 2.0 / a 2.5, min ≥ 8 | 0.98 / 0.98 | 0.98 / 0.98 | ≥ 0.90 |
| real-curve hold (r71b), min | **0.94** | 0.92 | ≥ 0.90 |
| inward light / firm lurch, b_lo×J_hi, max ≥ 8 | 3.9 / 2.9° | 3.9 / 2.9° | ≤ 8° |
| co-steer droop, max ≥ 8 (opposing freeze) | 0.9° | 0.9° | (C3: 2.3°) |
| **goal time fails per band ≥ 8 m/s** | **0** | **0** | 0 |

**N1 release lurch, judge re-run at Ki 40** (`n1_ki40.py`, worst over members): straight nudge 5° **2.0°**; inward
partial drag 0.5·Aₕ **7.2°**; outward 1.5·Aₕ 3 s **7.2°** (8-12.5) / 2.8° (≥12.5); outward **2·Aₕ** 3 s **14.3°**
(8-12.5) / 5.6° (≥12.5). Every realistic case is < 8°; the only > 8° residual is the aggressive 2·Aₕ-outward drag at
8–12.5 m/s (where θ_op at a2+ already approaches lock, so 2× is arguably unphysical) — **declared M-N1, R9.**

**Ki trade (EVIDENCE `rb_time`):** real-curve hold 0.75 (Ki 20) → 0.92 (Ki 36) → **0.94 (Ki 40)** → 0.98 (Ki 56);
15–22 tracking 0.918 (Ki 20) → **0.975 (Ki 40)**. The op-point instability is 0 up to Ki ≈ 44 and appears (ρ > 1) only
by Ki 56. Ki 40 clears the goal with 0 instability and the broadest curve-hold margin.

---

## 5. Pre-declared misses (each quantified, each with a covering stop band)

**Stop bands:** **R3\*** — a **0.25**–5.5 Hz oscillation that grows, or ≥ 4 cycles ζ < 0.25 → REVERT (lower edge dropped
to 0.25 for the outer-loop and curve-hold rings, F1/F2). **R4** — a narrowband 5–30 Hz line absent on V282/V295 → REVERT.
**R5** — ring > 0.5 %, F7 > 0. **R9** — the operator's words. **τ_o ≥ 1 s is a CHECKED fork-config prerequisite** (F2).

| # | finding | band | predicted (EVIDENCE) | stop band |
|---|---|---|---|---|
| M-F1 | ms_free-family curve-hold ring | J≈2, a2.0–2.5, 9.5–16.5 m/s | PM 1–21°, 0.45–0.9 Hz ζ 0.02–0.12, **ρ < 1**; disfavoured by the ident; friction-masked ±0.1–0.6° | **R3\* 0.25–0.9 Hz** |
| M-N1 | aggressive outward-drag lurch | 2·Aₕ, ≤ 12.5 m/s, b_lo×J_hi | 14.3° (realistic nudge/drag < 8°; 2× is arguably past lock at a2+) | R9; release overshoot > P2 + 2° |
| M-N2 | small-signal in the dip | ±0.2–0.5 Hz, 11–12.5 m/s | in-phase gain ≈ 0.51 (±1°) / ≈ 0 (±0.3°); 0.1 Hz improved by GB | R9 (micro-ratcheting on small corrections) |
| M-N4 | S-bend tracking, gated time members | 0.1 Hz, bc / b_lo×J_hi, 16–17.5 m/s | ≈ 0.94 (GATE-2-clean table cost); real r71b paths pass 0.981 | on-car tracking < 0.95 in-band = FAILED |
| M-N5 | reversal / windup overshoot | 9.5–14 m/s | ≈ 0.16·A at Ki 40 (0.19 at Ki 56); setpoint-bound does not reduce it | R9 ("a jerk") |
| M-N3 | dwell-then-jump, small corrections | 8–10 m/s and > 22 m/s | counted, not simulable vs V282; P2-class at 8-10, reduced > 22 by G ≥ 512 | R9; dwell rate vs r6c |
| M-N6 | road load at θ ≈ 0 | 8–12.5 m/s | P carries the bound-capped excess; 300/500 T → 1.2–3.9° | **hands-off error > 1° on a straight ≥ 8 m/s → REVERT** |
| M-N7 | turn-hold while accelerating out of a curve | 13–15 m/s | transient (~2 s) PI lag, min 1 s hold ≈ 0.86; not the 60 s FAILED definition | R9 ("runs wide out of a curve") |
| M-N8 | aged-sensor lurch | ≥ 8 m/s | +h10 light / firm ≈ 4.9 / 3.8°, under 8° | — |
| M-F4 | Re(T/ω) at physical κ / ages 0–9 | 13 Hz | 0.93× (ages 1-10) / 1.33× (ages 0-9); C3-rev2-F 1.9× | R4 |
| M-F5 | two-mass modal ζ vs V295 | 13–17 Hz | below V295 on 10 % (P) / 43 % (F) of stress points, max Δζ 0.034/0.041; 0 unstable, no peak > +3 dB | R4 |
| **M-13 (C3-rev2-F)** | no new 5–30 Hz line | ≥ 13 Hz | 13/15 Hz anti-damping 1.9–2.05× V295 (held D) | **R4, 10–17 Hz watch** |
| inherited | F5 camera, pol = −1 (P), the FB frame, 510 ms timeout | — | §6 | procedure + fork gate; R1 INVERTED drive 1 |

---

## 6. Hazards and fail-safe paths

| # | path | behaviour | fails safe? |
|---|---|---|---|
| **H-rate** | motor rate invalid (`gp-0x6abe` = 0x7FFF or out of ±13000) | **C3-rev2-P: `jr 0x2a164` → the whole PID is skipped, I8 := 0, sentinel set, output decays (Ghidra-verified §1.2).** C3-rev2-F recommended: same op-skip (pol-free); default C3B-F: D := 0, PI-only ring declared (M-13-class). | **Primary & hardened fallback: fully.** Default fallback: declared |
| H-ovr | override / outward light hand (N1) | hard freeze > 512, **opposing-hand freeze > 300**, A3 θ-bound, ICL 8192, fade; outward release lurch ≤ 5.6° ≥ 12.5 m/s, realistic cases < 8° | bounded; M-N1 |
| **H-cam** | **the stock camera's 0xE4 on a relay close** (comma off, Honda LKAS on) | the firmware cannot tell the camera's command from an angle setpoint; the F3 op-skip does NOT help (the camera sends a valid rate). | **NO — not fail-safe in firmware. ESCALATED (§0.3.4).** Default: **camera LKAS OFF (FLIGHT PREREQUISITE)** + the fork B3 gate + A2-skip on request 0 (program precedent). **Option: C3-rev2-P-cam** — rev2-A's built `gp-0x6803==2` gate (+20 B cave, + a fade-record cal to neutralize the ×1.8–2.1 fade). ⚠ Its discriminator (camera byte-2 field 3:2 = 0) is kit record and **must be re-measured on bus 2 before flight** (trace open item 4). |
| H-pol | the sign of C3-rev2-P's fresh D | on this car pol = `gp-0x6752` = −1 (boot-static, V98). **C3-rev2-F is pol-invariant.** | yes on this car; FLIGHT PREREQUISITE: image stays on this car; re-prove pol; R1 INVERTED catches it drive 1 |
| H-tmo | the fork stops sending | last θ_sp held 510 ms → sentinel → A2 → ≈ 0.1 s decay; mid-motion wheel ≈ 2.4° | holds the last VALID command 0.51 s (= stock); declared |
| H-fork-tq | a torque-mode / zero-emitting fork on this image | reads torques (or 0) as angle setpoints; a 0 drives toward centre (bounded by the clamps, caught by R6) | bounded IFF V1 `…A16A` + the fork's angle-loop key ship and the revert `.rwd`s are re-headered; **declare the zero-emitting sub-case** |

**FLIGHT PREREQUISITES:** camera LKAS off (or the H-cam ruling) · the fork sends θ_sp on 0xE4 in the EPS 0.1°/count
frame, inactive output = θ_meas, **any fork angle integral at τ_o ≥ 1 s (CHECKED) and none below 8 m/s** · V1 `…A16A` in
carFw + the fork key · the revert `.rwd`s re-headered to list A16A · **image car-specific (pol = −1, C3-rev2-P only)**.

---

## 7. The instrument — one short drive (no new telemetry bit)

Identified within an episode from signals already on the wire: 0xE4 (θ_sp = −raw/10 and request), 0x14A (θ 100 Hz),
0x18F (rate, driver torque = raw × 1.024, STEER_STATUS), the CAN 427 tap (T = gp-0x6b38, +sign(cmd)), F181 in carFw.
Decode with the patched cereal (slot-137 collision); take routes from the device's realdata.

Regression (hands-off, |0x18F| < 500, request 1, ≥ 1.2 s after engage): `tap = c_P·(raw − 10θ) + c_I·Σ(…) + c_D·ω + c0`.
- **LIVE image:** carFw EPS = `39990-TVA,A16A`. **LIVE angle loop:** c_meas/c_raw ∈ [−1.25, −0.80].
- **LIVE Ki-40 fix (F1):** c_I/c_P ∈ [1.9, 3.6] s⁻¹ (≈ 2.8, down from C3's 3.9). **LIVE re-sized D:** c_D ∈ [0.45, 0.70]
  tap/(deg/s) (C3-rev2-P), [0.38, 0.58] (C3-rev2-F).
- **LIVE opposing-hand freeze (N1):** the light-hold episode is **bidirectional** — one inward, one **outward** (rest a
  hand ≈ 2–4° FURTHER into a curve, |0x18F| ≤ 500, then release). The I component (tap − c_P·e − c_D·ω, 1 Hz LP) must
  stay flat within ≈ 200 T and the release must not overshoot toward centre by more than the §4 value + 2°.
- **INVERTED → abort (R1):** c_meas/c_raw > 0, or c_D aiding ω (for C3-rev2-P, the pol check).

**REVERT (any one):** R1 INVERTED · R2 |tap| ≥ 300 hands-off > 0.3 s · **R3\*** a 0.25–5.5 Hz ring that grows or ≥ 4
cycles ζ < 0.25 · R4 a 5–30 Hz line absent on V282/V295 (C3-rev2-F: 10–17 Hz watch) · R5 ring > 0.5 % or F7 > 0 ·
R6 |θ − θ_sp| > 10° hands-off > 0.5 s at > 8 m/s · R7 tap pushing toward 0° > 0.2 s after a request drop · R8
STEER_STATUS ≠ 0 or 0x14A b4 bits 0–2 ≠ 7 engaged · R9 the operator's words.

**The sentence a null licenses:** *"If c_I/c_P ≈ 3.9 (not ≈ 2.8), the Ki-40 fix did not ship. If an outward 3 s light
hold still ramps the I or lurches on release, the opposing-hand freeze is not live. If a curve hold at a2+ rings at
0.45–0.9 Hz, that is the declared ms_free margin (M-F1) — revert either way."*

---

## 8. What a FAIL looks like (any one → do not flash)

H1 bytes ≠ the §1.4 arithmetic on any of 60 000 inputs, or any register outside {r6,r8,r9,r13,r16,r26} (P) /
{r6,r8,r9,r13,r16} (F) changes, or r25/r14 written, or any RAM written · any R2-box OR curve-hold-op-point GATE-2 fail
outside the declared ms_free report set · any goal time criterion failing on any member ≥ 8 m/s on the BUILT table · a
new 5–30 Hz line · **H-skip:** the invalid-rate branch does not reach `0x2A164`, or reaches it with any RAM written in
between · **H-N1:** the BUILT image's outward 3 s light-hold release lurch > 8° at any speed ≥ 12.5 m/s · the BUILT-image
H5–H10 (hook/exit decode, A2/B2 dominance, CRC walk, F181, pol) · the mandatory close-out adversarial pass (≥ 3
independent agents, "do not flash" reachable) finds any decision-bearing defect.

---

## 9. How this merge differs from the two revisions, and from the arc

- **vs rev2-A:** takes rev2-A's F3-safe-FALLBACK insight (a held, pol-free cave made rate-invalid-safe) and offers its
  built camera interlock, but **does not** take its setpoint-referenced bound (the judge's Ki-40 re-run shows it is
  dominated by the opposing-hand freeze and worsens partial drag) or its raise-one-knot table (less N2 margin, 520 vs
  559). It uses rev2-A's F3 idea via the cheaper op-skip, not the +4 B E:=0.
- **vs rev2-B:** adopts C3B-P as the primary unchanged, but **hardens the fallback's F3** (rev2-B declared a rate-invalid
  PI-only ring on C3B-F; the merge closes it with the same Honda-epilogue op-skip, pol-free) rather than leaving it
  declared. The camera is escalated as in rev2-B, with rev2-A's interlock offered.
- **vs the arc:** still the first firmware angle loop (not V294/V295 cal-space, not torque mode, not an unfiltered rate
  tail, not a fork rewrite). A gated cave — GATE 1 0 RAM, GATE 2 clean at θ=0 **and** at the curve-hold operating points
  the refuter added, a byte-exact mirror the H1 executes, the wire instrument on every term (including the new freeze),
  an adversarial pass reachable. The one open item — the stock-camera relay close — is a hazard-class ruling flagged for
  the orchestrator, not papered over.

## 10. What this page did not do

No image built → nothing decoded from a BUILT image (H5 is build-time). The common scorers' runs behind the primary are
rev2-B's (`rb_final`), re-used because the primary is C3B-P byte-for-byte; the judge re-verified the N1/N5/N2/F3 cruxes
himself but did not re-run the full 12-process common grids (the builder's H2/H3 on the BUILT table does). The merged
fallback's F3 hardening is specified, not assembled — the builder assembles + H1s it; its scored metrics are C3B-F's
(fault-path edit). κ is unmeasured (BELIEF); the A3 bound and the opposing freeze are κ-independent / sign-only.
Dwell-then-jump vs V282 and hard-turn energy vs V282 are not simulable without V282. Low-speed stick-slip "gone" is met
by no candidate (the friction frontier). The camera byte-2 discriminator and pol = −1 are kit record, not re-measured.
The mandatory close-out adversarial pass on the BUILT image and the Artifact (signal-flow + LERPs, before/after) are
build-time steps.
