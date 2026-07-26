---
name: reference-accord-voter-0xffff-sentinel
description: Accord TVA-A160 voter FUN_00041eec — byte-verified mechanism for gp-0x6a62/gp-0x4cae = 0xFFFF invalid-sensor sentinel. Real function is ~1158 bytes (0x41eec-0x42372), NOT the 358 bytes r2's af/pdf auto-detects (auto-analysis silently truncates around 0x42052 — must hand-walk with pD past that point). Store at 0x4231c/0x42320. Trigger = insufficient valid-channel count this cycle (instantaneous, no debounce), NOT a torque-magnitude spike.
metadata:
  type: reference
---

# Accord 39990-TVA-A160 voter FUN_00041eec — the gp-0x6a62==0xFFFF sentinel mechanism

Stock code.bin. gp=0xFEDF8000, tp=0xBF000. r2 5.5.0 `-a v850.gnu`. Session 2026-07-03. All addresses/bytes below are byte-read/disasm-verified this session unless marked [I]nferred.

## ⚠ TOOLING GOTCHA (new, important for anyone re-touching this function)
`r2`'s `af`/`aa`-based function analysis on `FUN_00041eec` badly under-detects: `af` reports `size:358, realsz:262, num-bbs:20`, ending at **0x42052** — but the REAL function continues to a `dispose 9,{r20-r29,lp},lp` at **0x42372** (total ~1158 bytes). `agf`/`pdf` silently stop at 0x4203c and never show the back half (including the entire 0xFFFF-sentinel logic). Root cause: v850.gnu hits a handful of **undecoded V850E2 opcodes** inside the function (`f0 fc` @0x41f8c, `ee fc` @0x41fec, `fa fe` @0x42148 — likely 32-bit V850E2-only ops the .gnu plugin's table doesn't cover) which breaks r2's forward CFG walk. **Always hand-walk this function with linear `pD <n> @ <addr>` across the full 0x41eec-0x42372 range and cross-check branch targets by grepping mnemonics+targets, don't trust `af`'s reported size or `agf`'s graph for this function.**

## The store [V — exact bytes]
```
0x0004231c   64 c7 9e 95   st.h r24, -27234[gp]   ; gp-0x6a62  = r24
0x00042320   64 c7 52 b3   st.h r24, -19630[gp]   ; gp-0x4cae  = r24   (shadow twin, same cycle)
```
(sibling branch, NOT the sentinel path: `0x42312 st.h r28,-27234[gp]` / `0x42316 st.h r28,-19630[gp]` — taken only when r25==1, see "sticky-rail" below.)

`r24` is initialized to **0xFFFF** at function entry to the channel-processing block:
```
0x000420ae   80 c6 ff ff   ori 65535, r0, r24      ; r24 = 0xFFFF (min-search / sentinel seed)
```
and is the ONLY register written to `-27234[gp]`/`-19630[gp]` in the r25==0 path. It is written EXACTLY ONCE elsewhere, at `0x421cc: cmov nh,r20,r25,r24` (`r24 = MAX(ch5_deviation, ch1-4_max_deviation)`), which computes the **real** voter output. **If that one write is skipped, r24 reaches the store still equal to 0xFFFF.** This is the entire mechanism.

## The guard — byte-verified [V]

Each of the 5 coil channels gets an independent RANGE-VALIDITY check against the SAME envelope, computed early in the function (~0x42052-0x420aa):
```
0x0004205a   80 6e 01 96   ori 38401, r0, r13       ; ceiling constant 0x9601 = 38401
0x00042054   0d 7e 00 19   addi 6400, r13, r15       ; ch1: r15 = ch1_raw + 6400
0x0004205e   cmp r13, r15                            ; validity = (ch1_raw+6400) < 38401 (unsigned)
0x00042062   setf c/l, r10                           ; r10 = ch1 validity flag (1=valid)
```
(repeated per-channel for ch2 @gp-0x6a40→r16, ch3 @gp-0x6a3c→r14, ch4 @gp-0x6a38→r12, ch5 @gp-0x6a46→r27, each stored into a 5-slot stack array `{value,...,flag@+20}` via `sst.w`.)

Effective per-channel validity: **`-6400 ≤ raw_channel < 32001`** (unsigned compare of `raw+6400` against 38401 catches both the negative underflow and the positive overflow cases via 32-bit wraparound). This operates on `gp-0x6a44/-0x6a40/-0x6a3c/-0x6a38/-0x6a46` — the SAME ×41/64-scaled raw coil values documented in [[reference-accord-dual-torque-sensor-architecture]]. Real driving torque in these units "tops out ~3400" per that memory — so this envelope has ~9x headroom above and ~1.9x below normal peak driver torque. **This is a hardware-fault-level range check, not a torque-magnitude/plausibility check.**

`FUN_00041eec` then loops ch1-4 (`0x420b6-0x42108`), counting valid channels into `r26` (0-4) and tracking max/min |deviation-from-feedback| into `r28`/`r11`/`r16`/`r25(loop-local)`. ch5 folds into `r28`/`r11` if valid but does **NOT** increment `r26`.

**The two live gate branches (both land at `0x42200: mov 0,r25`, skipping the `0x421cc` real-candidate write, leaving r24=0xFFFF):**
```
0x000421b8   cmp 1, r27                 ; r27 = ch5 validity flag
0x000421ba   ba 25   bne 0x00042200     ; ch5 INVALID -> shortcut, r24 stays 0xFFFF

0x000421bc   cmp r23, r26                ; r23 = cal[0xC6501] (ld.bu 29953[r5]) = 3 [V, byte-read]
0x000421be   91 25   bl 0x00042200      ; r26 < r23 (fewer than 3-of-4 primary channels valid)
                                          ; -> shortcut, r24 stays 0xFFFF
```
Plus a third "total-loss" door (`0x4215e-0x42160-0x42194-0x421aa`) that fires when **ch5 invalid AND r26==0** (zero of ch1-4 valid): it additionally force-clears the plausibility latch `gp-0x67f4`(-26612[gp]) and shadow `gp-0x4c38`(-19512[gp]) to 0, then also lands at `0x42200`. This is a subset of the two conditions above, not a separate trigger.

**Unified trigger condition for `gp-0x6a62 = gp-0x4cae = 0xFFFF`:**
> `NOT( ch5 valid AND (count of valid ch1-4) ≥ 3 )`
> i.e. ch5 out of its ±32000ish range envelope this cycle, **OR** 2-or-more of the 4 primary channels out of range this cycle.

`r23` (min-valid-count=3) is a **calibration byte** at `tp+29953 = 0xC6501` (verified = `0x03`), so it is itself edit-checkable if ever relevant, though not recommended to touch (weakens fault detection, same caution as the ruled-out `bVar1`/32000 gate in `m_steer_torque_arbitration`).

## Q3 — instantaneous vs latched [V]

**INSTANTANEOUS, no debounce, on the way IN.** The per-channel range checks, `r26` count, and `r27` (ch5) flag are all recomputed FRESH every voter cycle from that cycle's raw ADC-derived values. The gate at `0x421b8-0x421be` reads `r26`/`r27` as computed THIS cycle only — no counter/hysteresis feeds this specific branch. **A single bad cycle is sufficient to write 0xFFFF.**

Also **instantaneous on the way OUT**: the moment validity is restored (ch5 valid AND ≥3-of-4), `r24` gets freshly computed via `0x421cc` as a real magnitude again — the store at `0x4231c` uses whatever `r24` is THIS cycle, with no memory of the prior 0xFFFF.

The SEPARATE plausibility latch `gp-0x67f4` (existing memory: [[reference-accord-arb-input-cluster]], [[reference-accord-lkas-column-torque-cut-trigger]]) DOES have hysteresis (a `|r28-gp-0x6a5e| < 65` recovery check with a shadow-twin double-confirm before flipping back to "OK"), and IS byte-confirmed here: `0x42222: cmp r0,r12(=gp-0x67f4); bne 0x42230; st.b 0xFF,-26613[gp]` (gp-0x67f5=0xFF "not-yet-converged" exactly when gp-0x67f4==0) — this matches [[reference-accord-arb-input-cluster]]'s claim precisely. **But `gp-0x67f4`'s value does NOT feed `r24`/`r25` at the store decision** (`0x4230e: cmp r0,r25`) — it's bookkeeping for a DIFFERENT downstream consumer (gp-0x67f5 convergence flag, and the arb curve bypass described in that memory), not a gate on the sentinel write itself. So gp-0x67f4's latch does not retroactively debounce or delay the gp-0x6a62=0xFFFF event.

## Q4 — bump plausibility [I — reasoned from V structure, not a live measurement]

The per-channel envelope (±32000ish, ~9x headroom over real driving torque ~3400) argues AGAINST a pure torque-magnitude transient (hard grab + bump) tripping this on its own — it would need an actual signal-level excursion, not just "high torque." **However**, all 5 channels are unpacked from the SAME 8-byte DMA'd serial frame ([[reference-accord-dual-torque-sensor-architecture]]: "an 8-byte serial frame is DMA'd... 5 readers bit-unpack 5 fields"). A single frame-level glitch (a corrupted DMA transfer, an IRQ-lock race, connector/ground-bounce noise coincident with a mechanical shock) could plausibly corrupt MULTIPLE channel fields in the SAME 8-byte frame simultaneously — and the gate only requires losing ch5 alone, or losing 2-of-4 primary channels together, to trip. That is a much lower bar than "all 5 independently glitch." **Net verdict: MEDIUM confidence that a bump-induced electrical/DMA-frame transient (not a torque magnitude event) could plausibly satisfy this gate for one cycle; LOW confidence that torque magnitude alone (however hard the grab) does, given the ~9x headroom.** This is a genuinely different failure class than "big steering torque" — it is closer to "sensor frame glitch coincident with mechanical shock."

## Corrections to prior memory [flagged, not yet resolved with operator]

- [[reference-accord-assist-mode-eme-dropout]] states the plausibility trip in `FUN_00041eec` is "dual-coil... exceed inter-channel delta threshold... threshold ~0x7D00=32000." **This session found NO inter-channel-delta check tied to the 0xFFFF sentinel.** The only appearance of 32000/32001 in this function is as a VALUE CLAMP CEILING (`0x42150-58` clamps r28 to ≤32000; `0x421c4/0x421ee` test candidates against 32001 for the clamp, not for validity). The actual sentinel trigger is the per-channel absolute-range check (≈±32000 envelope, described above) + the ≥3-of-4 valid-count gate — a channel-count/range mechanism, not a spread/delta mechanism. There IS a separate spread(max-min)-vs-threshold check (`0x4213a-0x42150`) but it only decides whether `r28` gets replaced by an averaged value — it does not feed the 0xFFFF path. **Recommend re-verifying or retiring the "~0x7D00 inter-channel delta" characterization** — ask the operator before editing that memory file directly.
- [[reference-accord-lkas-column-torque-cut-trigger]]'s "ruled out" note on `gp-0x67f4` ("cleared only on total coil loss") is CONFIRMED at the byte level, with "total loss" now precisely defined as ch5-invalid-AND-zero-of-ch1-4-valid (the `0x42194` door), consistent with — not contradicting — that memory.

## Open questions / next verification steps
1. The undecoded opcodes at `0x41f8c` (`f0 fc`), `0x41fec` (`ee fc`), `0x42148` (`fa fe`) are outside the sentinel path traced here (they affect an unrelated preamble diagnostic-call block and the spread/average blend of `r28`) but remain unresolved V850E2 instructions — would need Ghidra's V850E2 processor module or a manual opcode-table lookup to decode if ever load-bearing.
2. `gp-0x6a64` (a related but distinct output, `-27236[gp]`, written at `0x42360/0x42364` from `r22`) was NOT traced for its own 0xFFFF-equivalent — flagged in the mission as a bonus question, not resolved this session. `gp-0x6a60` is confirmed NOT written by this function (matches existing memory: it's angle-rate-derived, a separate signal) — so it cannot rail via this mechanism.
3. No live RAM read performed this session (per the study/analysis-only constraint) — this is a pure static-disassembly trace. A live read of `gp-0x6a62`/`r26` validity flags during an actual bump event would be the strongest confirmation of the Q4 verdict.

[[reference-accord-lkas-engage-sm-disengage-trigger]] [[reference-accord-dual-torque-sensor-architecture]] [[reference-accord-arb-input-cluster]] [[reference-accord-assist-mode-eme-dropout]]
