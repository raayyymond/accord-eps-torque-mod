# ADVERSARIAL PASS — INTERLOCKS / DOWNSTREAM / GATE 1 / GATE 2 on the BUILT V299 rev 2 image

**Adjudicated by the orchestrator (2026-10-02)** from the lens's own scratch scripts after two subagent attempts were
stopped by an automated safety classifier while writing this report (both had run the scripts; neither delivered a
verdict). Scripts: `_scratch/adv_ilk_v299/{diff,cells,census,crcwalk,g1g2,dominance,carry_sim,f181ref}.py`, each
< 30 s, re-run by the orchestrator; outputs quoted below. FAIL criteria were written first
(`FAIL-CRITERIA-interlocks-gates-V299.md`, nine do-not-flash clauses). Decode-first evidence: the orchestrator's own
Ghidra dry-run decode of the V298 span 0xC4C50–0xC4CB0, and two independent Ghidra decodes of the V299 span (the mirror
agent on the built bytes, the bytes re-refuter on its rebuilt image) — the lens's own agent found GhidraMCP timing out
and used its own V850 decoder (`dec.py`) instead.

**Image:** `_v299_V299-ANGLELOOP…A3-2LVL.4096.6144.V2880.FRZ1229…A16B_plain_image.bin`, sha256
`30ff05fa464e87ab7eecfcbab9cbf6dfb3afcb57ceb5c89e4a29c1f748c38f08`; base V298 `177abf04…`.

## VERDICT: PASS_WITH_DEFECTS — no do-not-flash clause fires; three nonlinear costs are declared with stop bands.

| # | FAIL clause | Result | Method (EVIDENCE) |
|---|---|---|---|
| 1 | Stray diff / a gain, table or clamp cell changed | **clean** — 67 bytes in 9 runs: 0x1310D (41→42), 0xC4C64–65, 0xC4C6A–0xC4CAB (5 runs), 0xC4FFC–FF; nothing else in 1 MiB. GB-P table 0xC4CDA–0xC4D04 identical; fb a/b/C, I deadband, Ki, ICL, DCL, PCL, OCL, Kp row 0xE5384, Kd row 0xE5126, T gain, dir-2 fade 0xE54FC, rate-fade 0xE55A4, post-PID fade 0xCBBC4, the whole cal 0xC5000–0xC7000 and 0xC7000–0xE6000: V298 == V299. ⇒ **GATE 2 is V298's by construction.** | `diff.py`, `cells.py`, `g1g2.py` (byte compares) |
| 2 | Write set non-empty (GATE 1) | **clean** — gp read set shrinks (gp-0x4f60 dropped; -0x4f68, -0x6a00, -0x6a5e, -0x6abe, -0x6dd0 kept); every reader's writer identical and none inside the cave; the raw store-pattern scan's 4 even-offset hits (0xC4C1E, 0xC4C64, 0xC4C8A, 0xC4CAA) are all MID-INSTRUCTION (inside `mov imm32` @C4C1C, `movea` @C4C62, `addi` @C4C88, `addi` @C4CA8 per the decoded listing); the positive control flags the real `st.*` at 0x29D72; the interpreter traps stores: **0 RAM writes in 7,300 cases**. | `g1g2.py`, `dominance.py`, decoded listing |
| 3 | Control-flow break | **clean** — every bcond in the cave lands on an instruction start (V299 targets C4C74, C4C7A, C4CA6, C4C9A, C4C9E, C4CAC… all starts of the decoded listing); the only entry is `jarl 0xC4C00` at 0x29D76; no disp17 branch and no `movhi` pair elsewhere targets 0xC4C00–0xC4D10; the table pointer `mov 0xC4CDA,r9` at 0xC4C1C is the only raw LE word in the span and is unchanged. | `census.py` |
| 4 | Exit-semantics regression | **clean** — 7,300 random cases through both caves (hands-off ×4, 300–512, 512–1229, pressed): skip/cam exits identical (0 mismatches); pressed band identical 600/600; the only exit differences are the intended ones (hands-off: V299 runs where V298 froze in 72–95/1500, never the reverse; 300–512: the removed opposing clause (101) and the tighter centre-ward bound (30); 512–1229: the raised threshold (193)). | `dominance.py` |
| 5 | Register clobber | **clean** — r16 (E′) / r26 mismatches 0; caller registers clobbered 0; sp/lp/gp/tp/ep untouched. | `dominance.py` |
| 6 | Downstream consumer change | **clean** — image identical outside the four diff ranges; sha-equal: the PID lane 0x28E00–0x2A400 (hook, I/P/D, sum, clamp, output lag, T), the engage SM + A2/B2 0x29A00–0x29A90, the 0x1AB/0x18F/0x14A builders 0x55800–0x56000, the hand |raw| writer FUN_0007f3f8, the v-word writer 0x41EEC–0x42400. EME, governor, lockstep and DTC code is therefore byte-identical to V298 (V298's lens enumerated them). | `g1g2.py` |
| 7 | Unbounded output | **clean** — bound ∈ [1250, 4096] at v ≤ 1382, [1250, 6144] at 1383–2880, V298's 16·\|θ\|+1250 above; max(bound_V299 − bound_V298) = 0 at every θ, sign and v (arithmetic lens, 30,000 cases) ⇒ V299 never allows more wind-up than V298; ICL 8192 and the output clamp unchanged. | `ADV-arithmetic-V299.md`, `cells.py` |
| 8 | Nonlinear hazard UNSAFE | **not unsafe; three declared costs** (below) | `carry_sim.py`, the re-refuters |
| 9 | CRC | **clean** — walk_all_blocks 0 bad (50/50) and bootloader walk 0 bad (49/49) on V299; negative control (one byte flipped at 0xC4C80) → 1 bad on each walk. | `crcwalk.py` |

**Freeze ⇔ hands-on, from the image:** raw ±1230 → wire ∓1201 → pressed AND frozen; raw −1229 → wire +1201 → pressed, NOT frozen (the one-count asymmetry the arithmetic lens found); raw ±1228 → not pressed, not frozen. The freeze set is a strict subset of Honda's pressed set (`cells.py`).

**F181 readers:** the two code references to the version string (32-bit LE words at 0x4F6E8 / 0x4F70E) are unchanged, so the car reports `39990-TVA,A16B` through the same path; an un-updated fork (exact A16A match) refuses to engage — the fail-safe direction (`f181ref.py`).

## Declared costs (clause 8), each with its stop band on the drive-2 card
- **Integral carried into a slow turn.** The cap limits wind-up at the current v-word but never lowers an integral already above it. `carry_sim.py`: a 60° turn at 3 m/s entered with I already at 8192 S (a same-sign hold above 12.5 m/s, then braking) overshoots 10.5–11.8° under V299 vs 13.3–28.1° under V298; entered at 6144 S, 6.1–6.7° under both. **Inherited, and V299 is the smaller of the two**; stop band F4a (> 6° at ≤ 10 m/s) and the F6 readouts. (BELIEF on the plant members.)
- **Moderate-hand band 500–1200 wire, no fork override (operator ruling).** The lane holds 37–60 % of the rail against a drag at 5–8 m/s (sim); the firmware's fade and the 1229 freeze remain the yield path, and the setpoint re-clips to the wheel every frame, so there is no un-overridable state. Declared; F7b observation, R9 the criterion. (BELIEF.)
- **6144 cap curve-hold shortfall at 6–12.5 m/s** (3–7° on ≥ 2.5 m/s² holds on the ms_free members) and the **outward light co-steer release** (8–10° on the heavy member): declared on the card with the cap null sentence and F3's speed-band bars. Above 12.5 m/s the cap is removed and the behaviour is V298's. (BELIEF.)

## Method defect (process, not the image)
GhidraMCP timed out for the lens's own agent; the decode-first step rests on the orchestrator's and two other agents' Ghidra decodes of the same bytes. The lens's interpreter (`dec.py` + `dominance.py`) is the agent's own, independent of the golden model and the build script.
