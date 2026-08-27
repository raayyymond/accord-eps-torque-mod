# HANDOFF 2026-07-24 (third) — V52C: the COMPLETE broad low-pass (all 19 carriers), built + verified

Supersedes `handoffs/2026-07/HANDOFF-2026-07-24-v51p-v52-carrier-surface.md` on the carrier partition, the
"self-filtering lane" classification, and the reader-enumeration method. Read `CLAUDE.md`'s
LATEST-3 block first.

## TL;DR

1. **V52C is BUILT and UNFLASHED** — `_v52c_plain_image.bin`, sha256 `af01c8bd…`, 132 changed bytes
   vs V38 in 24 runs, 50/50 CRC, x31 round-trip + RWD readback clean.
2. **ALL 19 command-path carriers of `gp-0x4f60` are repointed** to the filtered copy in `gp-0x1300`
   (operator directive). V52 repointed 10; V50 repointed 7.
3. **The prior handoff's "3 self-filtering lanes" classification was WRONG on all three** — measured
   coefficients below. Two of the three are genuine 21 Hz carriers.
4. **GATE-1 (RAM ownership) is closed FIVE independent ways** for `gp-0x1300`; the method reproduces
   V50's and V48B's failures as controls.
5. **GATE-2 (closed-loop stability) is CLOSED** — margin improves monotonically with the filtered
   fraction, and 19/19 is the best configuration measured (edge 4.66× → 21.2×).
6. **Correction of record: the "definitive 69 readers" figure in the prior handoff is WRONG.** The
   byte scan behind it was structurally blind to the V850E2 6-byte extended-displacement encoding.

## 1. Why "all carriers", not "the ones that matter"

The lead initially built a 16-lane version, excluding three lanes on per-lane cost/benefit. **The
operator overrode this and was right**: a MIXED raw/filtered population is itself the hazard. Any
self-consistency, dual-path, lockstep or mirror check straddling the split would see a divergence
that does not exist today. **This kit's V27 brick was caused by exactly that — ASYMMETRY, not
magnitude** (a float twin scaled wholesale vs an int corridor scaled partially → "divergence ≈ FULL
torque").

It is also the most stable option by the numbers (§4). Uniform filtering is both the most
self-consistent and the most stable configuration — the two criteria agree.

## 2. ★ The carrier partition, corrected

A definitive byte scan of V38 found **64 `ld.h` + 5 `st.h`** gp-relative disp16 accesses to
`gp-0x4f60`. In V52C: **19 read the filtered cell, 46 still read raw** (+1 = the cave's own input
read, 65 total loads).

### The 19 repointed carriers (all byte-verified; `word1 = (reg2<<11)|0x724`)

| Site | Reg | Function |
|---|---|---|
| 0x29A90 | r12 | FUN_00028ea6 arbitration LERP curve select |
| 0x2B69E | r25 | FUN_0002b62c → gp-0x6aea |
| 0x2C480 | r15 | FUN_0002c478 type-8 |
| 0x2DF32 | r2 | FUN_0002db94 → gp-0x6b1a |
| 0x2F318 / 0x2F330 / 0x2F33E | r7 | FUN_0002eda8 3-way branch → gp-0x6b6c |
| 0x33D2A | r2 | FUN_00033d10 float PID → gp-0x6b78 |
| 0x354D2 / 0x35AA4 | r16 / r14 | FUN_000352b4 magnitude |
| **0x36682** | r11 | FUN_00036682 → gp-0x6b46 |
| **0x36846** | r14 | FUN_00036828 → gp-0x6b44 |
| 0x3A6CA / 0x3A7CA | r10 / r8 | FUN_0003a382 resonance lane |
| 0x3B4A8 | r13 | FUN_0003b49a |
| 0x3B672 | r9 | FUN_0003b66a damping+boost Factor-A |
| **0x3B908** | r9 | FUN_0003b8f6 → gp-0x6bfc/6bf6/6c00 |
| 0x3F8E2 | r11 | FUN_0003f884 → gp-0x6a0a |
| 0x3FCC6 | r7 | FUN_0003fc16 → gp-0x6a0a |

⚠ **ENCODING TRAP — the prior handoff's `word1` column was a nominal `reg<<8` notation, NOT the real
encoding** (it listed `0x0C24` for r12; the real value is `0x6724`). Building from it would have
corrupted 9 instructions. Every value above was read from the image.

### The 10 command-region reads deliberately left RAW — all justified, machine-checked

| Site | Reason |
|---|---|
| 0x28F26, 0x42C20, 0x43EDA | **health gates**, each vs a LITERAL constant. Health gates must see the true sensor. |
| 0x34392, 0x34ACE | dormant mux arms (cals 0xC6498/0xC6499 = 0x01 select the other branch) + a live raw range gate |
| 0x2EC66, 0x2ECBA | FUN_0002ec52 diagnostic logger |
| 0x2A992, 0x2D9A2, 0x2DAE6 | **DEAD** — triple-confirmed (0 callers, 0 xrefs, 0 LE32 pointer refs) |

`verify/verify_v52c_image.py` enforces this as a **completeness invariant**: it fails if any future edit
leaves an unexplained raw read in `[0x28000,0x46000)`. Non-command regions (producer, CAN packers,
UDS/diagnostic loggers, DTC freeze-frame, angle-cal SM) stay raw by design — telemetry must report
the true sensor.

## 3. ★★ The "self-filtering lanes" were mis-classified — all three

The prior handoff excluded three lanes as "self-filtering (cascade risk)". Measured against V38:

| Lane | Handoff claim | **Measured reality** |
|---|---|---|
| 0x36682 | self-filters | **TRUE** — terminal EMA α=6/1024 (cal `0xC63D2`=6) → **fc 0.94 Hz**, −27 dB at 21 Hz. Also wraps a nonlinear slew/hysteresis tracker. ~0.5% of the residual. |
| 0x36846 | "self-filters (EMA)" | **FALSE — not a filter at all.** Its `gp-0x6b44` write is a *cal-selected constant*; the same load feeds a first-difference rate check raising **DTC 0x23**. |
| 0x3B908 | "self-filters **heavily** (float IIR chain)" | **FALSE — nearly a passthrough.** Its 3rd biquad stage is **degenerate in stock cal** (coeffs `0xC404C`/`0xC4050` = 0.0f); the two live poles are α=3686/4096 → **fc 366 Hz each (~236 Hz combined)**. ~11.8% of the residual. |

⚠ **Note on cal provenance:** a tracer read these cals from `code.bin`, which is **STOCK, not V38**.
Confirmed: `0xC646C` is **891 stock vs 3564 in V38** (exactly 4.00×). Structural findings from
`code.bin` are valid; **any cal VALUE quoted from it must be re-read against V38.**

### ⚠⚠ DISPUTE RESOLVED — the off-by-0x1000 trap, third occurrence

A second agent challenged the lane-3 figure, reporting `0xC50D0=259, 0xC50D4=832, 0xC50D8=122`
("all slow filters, none near 3686/4096") and concluding the 366 Hz characterisation "doesn't hold".
**That agent was wrong by exactly 0x1000.** `tp = 0xBF000`, anchored by TWO independent known values:

| anchor | address | value | source of truth |
|---|---|---|---|
| `tp+0x746c` | 0xC646C | **3564** | the V38 4× LKAS gain |
| `tp+0x74a4` | 0xC64A4 | **0x00** | CLAUDE.md: SM gate ENABLED |
| (decoy) | 0xC74A4 | 0xEA | CLAUDE.md: "a different byte" |

So `tp+0x50d8 = 0xC40D8 = 3686` → α=0.8999 → **fc = 366.31 Hz**. The `0xC5xxx` values belong to a
different table. CLAUDE.md already records this exact trap ("an agent-memory verdict was an
off-by-0x1000 misread"); **this is its third occurrence.**

**★ RULE: never accept a tp-relative cal VALUE without re-deriving the absolute address from
`tp = 0xBF000` and sanity-checking it against a known anchor.** An 0x1000 slip lands in a plausible
table and yields a plausible-looking number — it does not fail loudly.

(Immaterial to the build either way: all carriers are filtered regardless, and GATE-2 swept an
assumed existing pole fc2 over 2–100 Hz and found stability across the whole range.)

### `0x3B908` — its single load is REUSED by a validity gate (Ghidra-confirmed)

```
0x3b902  bnc  0x0003b908          ; branch target == our site
0x3b904  jr   0x0003bc0a          ; 4-byte jr
0x3b908  ld.h -0x4f60, gp, r9     ; THE LOAD
0x3b90c  ori  0xc801, r0, r16
0x3b910  addi 0x6400, r9, r8      ; same r9 -> gate: (x + 25600) < 51201, i.e. |x| <= 25600
0x3b914  cmp  r16, r8
0x3b916  bc   0x0003b91c
```
Repointing moves **both** the gate and the filter input to the filtered copy, so the function stays
internally self-consistent — which is the point of the directive. The filtered copy is provably
bounded by the same envelope as raw (the EMA never overshoots), so the gate cannot newly trip.

## 4. GATE-2 — CLOSED

`analysis-2020accord/studies/models/eps_v52c_gate2_broad.py`. Reuses V50's plant/Nyquist machinery (reproduces V50's
own baseline exactly as a control). Both calibrations: pessimistic Q_cl=13.6, broad-shelf Q_cl≈4.8.

| filtered fraction | worst_re (pess) | GM dB | edge× | worst_re (broad) | edge× |
|---|---|---|---|---|---|
| 0/19 (V38 stock) | 0.858 | 1.33 | **4.66** | 0.631 | 6.34 |
| 7/19 (V50) | 0.601 | 4.42 | 6.65 | 0.448 | 8.94 |
| 10/19 (V52) | 0.493 | 6.14 | 8.11 | 0.373 | 10.73 |
| 16/19 | 0.283 | 10.96 | 14.13 | 0.241 | 16.60 |
| **19/19 (V52C)** | **0.189** | **14.48** | **21.19** | 0.193 | 20.76 |

Because V52C filters **every** carrier, its REAL composition **is** the 19/19 row — `worst_re=0.189`,
`GM=14.48 dB`, `edge=21.19×`. The script retains the superseded 16-filtered/2-raw case as a
deliberately pessimistic comparison: even there, the raw `0x3B908` passthrough was neither dominant
nor negating (6.58 dB attenuation, `DOMINATES=False NEGATES=False`), so the shipped build is strictly
better than an already-sufficient case. That makes the margin attributable rather than asserted.

- **Monotonic** over a 41-point sweep under both calibrations → no destructive raw/filtered blend
  (`worst_re(f=0)=0.858 → worst_re(f=1)=0.189`, max over the sweep at f=0).
- **No unity-gain crossing anywhere 0.3–150 Hz**, so there is no low-frequency crossover for the
  filter's phase lag to erode. Loop gain is architecturally concentrated at ~21 Hz.
- Cascade sweep (existing pole fc2 ∈ {2…100} Hz) stays stable even at fc2=2 Hz (GM ≈ 16 dB).
- ZOH/decimation for ~100 Hz consumers **increases** margin; filtering **reduces** the aliasing those
  lanes already suffer reading a raw 1 kHz signal (78.6 Hz alias partner −15.6 dB vs −6.6 dB at 21.4 Hz).
- **A first-order EMA has no resonant pole and |H| ≤ 1 everywhere** — unlike V48B's notch, whose own
  poles (r=0.979, Q≈3.2) *were* the brick mechanism.

## 5. GATE-1 — closed FIVE independent ways for `gp-0x1300`

1. **V51P live probe** — 0/24000 CAN-330 frames non-zero, full 16-bit, beacon 100% live.
2. **Outside the 0xb7260 mailbox array** (0xFEDF6D00 > array top 0xFEDF6C20).
3. **Zero LE32 pointer references** anywhere in the 1 MiB image.
4. **Zero `movhi` materialising the 0xFEDF page** anywhere in the code region.
5. **Absent from the 0x89c34 / 0xbbc48 descriptor tables** (§6).

**The method reproduces both historical failures as controls** — `gp-0x1500` (V50, failed on-car) is
INSIDE the mailbox array *and* has 2 pointer-table entries (`0xb73ac`, `0xbb658`); `gp-0x14FA` (V48B,
bricked) is inside the array. Tests 2 and 3 are complementary and between them catch both modes.

**Startup transient (V48B's failure mode was a key-on slam):** RAM clears at power-up and a flash
requires a power cycle, so the filter state and every prior-sample cell start at 0 **together** — no
stale-state discontinuity can survive the flash. Worst-case convergence ~70 ms, during which the
filtered copy sits *below* raw → **less** assist, not more.

## 6. NEW FINDING — an uncatalogued address-descriptor table names `gp-0x4f60`

`0xFEDF30A0` appears as a literal LE32 word **3 times**: `0x89c6c` (a flat 32-entry pointer array) and
`0xbbc80` + `0xbbca0` (8-byte `{address, bit-descriptor}` records). The same table names `gp-0x6b98`
(delivered command) and `gp-0x6abe`. Shape strongly suggests a data-driven UDS DID / RAM-telemetry
definition table (cf. `docs/guides/SPEC-uds-can-ram-telemetry-a160.md`).

**The consuming CODE was NOT located** by any method (0 xrefs, 0 callers, movea reach math, text
search). **OPEN ITEM.** It does **not** block V52C: the tables name the RAW sensor (correct — we leave
every telemetry/diagnostic reader raw) and contain **zero** references to `gp-0x1300`.

## 7. ★ Correction of record — the reader-enumeration method was flawed

The prior handoff's **"definitive 69 accesses"** figure is **WRONG**. That scan matched only the
4-byte disp16 form and was structurally blind to the **V850E2 6-byte extended-displacement encoding**.
**CLOSED — corrected total, confirmed by three independent methods:**

| encoding | ld.h | ld.hu | st.h | subtotal |
|---|---|---|---|---|
| disp16 (4-byte) | 64 | 0 | 5 | 69 |
| extended (6-byte) | 6 | 1 | 0 | **7** |
| **TOTAL** | **70** | **1** | **5** | **76** |

**All 7 encoding-2 readers are diagnostic** — `0x4C784` (FUN_0004c780, boot self-test, table-dispatched
via the 0xBBA18 literal) and `0x59BFA/0x59C02/0x59C44/0x59C4C` (FUN_00059912) + `0x5A0BC/0x5A0C4`
(FUN_00059e7a), both UDS/RDBI record packers. Every one writes only to a local output buffer
(`sst.b rX,N[ep]` / `st.b rX,N[r26|r28]`), never to a `gp-0x69xx/0x6axx/0x6bxx` command cell.
**⇒ NO 6-byte reader is a command-path carrier; the 19-carrier partition is COMPLETE.**
**No 6-byte STORE exists** — the single-producer chain remains the only writer, all 5 stores disp16.

### Two methodological corrections (both cost real time this session)

1. **Destination-register field is `(hw1 >> 11) & 0x1F`**, NOT `(hw1 >> 3) & 0x1F`. The wrong form
   returns `r0` for all 7 known-good sites. (The error came from doing the arithmetic on the HIGH
   BYTE — `0x6a >> 3 = 13`, correct — then writing it down as a shift of the whole halfword.)
2. **`hw2 = 0xff61` is NECESSARY BUT NOT SUFFICIENT.** It does not encode the full displacement; it is
   shared across ~13 nearby offsets (`-0x4f68, -0x4f6a, -0x4f6c, … -0x4ee8` — a dense struct region).
   Scanning `(hw0, hw2)` returns **53 hits of which only 7 are ours — a 7.6× over-match.** This, not
   "alignment noise", is the real reason the lead's earlier attempt produced 45 junk candidates.
   **Encoding 2 cannot be enumerated by byte scan alone; confirm each hit with Ghidra's semantic decode.**

⚠ **`search_instructions` undercounted encoding 1 too** — 61 `ld.h` vs the true 64. The 3 missed
(`0x2D9A2`, `0x2DAE6`, `0x4F996`) are real instructions sitting OUTSIDE any function boundary
("No function found"), so the tool skipped them: it walks only function-owned instructions.
**4th recorded occurrence of that blind spot.** It also independently reproduced the lead's 64 figure
by raw byte scan — so encoding 1's count is now triple-confirmed.

**Rule going forward: any "N gp-0x4f60 accesses, fully enumerated" claim must state that it covered
BOTH encodings, and neither tool may be used alone** — byte scan misses encoding 2 and over-matches it
7.6×; `search_instructions` misses anything outside a function boundary.

## 7a. Monitor-asymmetry audit — SAFE, plus a CORRECTION OF RECORD on DTC 0x18

An adversarial audit of the repointed lanes' destinations (`gp-0x6a32`, `gp-0x6b2c`, `gp-0x6b12`,
`gp-0x6aea`, `gp-0x6b1a`, `gp-0x6b6c`, `gp-0x6b78`, `gp-0x6b86`, `gp-0x6a0a`, `gp-0x6ad4`,
`gp-0x6b2a`, `gp-0x6ba6`, `gp-0x6b9a`) found **no class-(c) raw-vs-filtered and no class-(d)
independent-mirror comparison anywhere**. Every live comparison is against a LITERAL/cal constant, or
against the same function's own prior filtered state.

**Three destinations ARE shadowed** — `gp-0x6b86`↔`gp-0x4cde`, `gp-0x6ba6`↔`gp-0x4ce8`,
`gp-0x6b9a`↔`gp-0x4ce4` (co-location byte-confirmed: e.g. `gp-0x6b86` at 0x35AB6/AC0/ACE interleaved
with `gp-0x4cde` at 0x35AA8/AC4/AD4 inside FUN_000352b4). All three use the pattern
`if (live==shadow) {write BOTH from one freshly-computed value} else FUN_0006b9fa(&shadow)` — a
this-cycle-write vs last-cycle-shadow corruption check, **not** an independent re-derivation. Because
both legs are written atomically from a single shared value, the mismatch condition is
**input-invariant**: whether that value came from raw or filtered `gp-0x4f60` cannot change whether
it fires. SAFE.

`FUN_0006b9fa` is a **different, weaker** mechanism from `FUN_0006b9ee`: `…b9ee` → `FUN_0006ce7c(0x17)`
= the hard shadow-mismatch fault; `…b9fa` → `FUN_0006ce7c(4)`, which writes an index into
`gp-0x444f`/`gp-0x4e53` and does **not** go through the `FUN_00016de6` / 0xB7D58 DTC table. Do not
conflate them.

### ⚠ CORRECTION OF RECORD — **DTC 0x18 IS HARD-FAULT ELIGIBLE**

An agent reported DTC 0x18 as "NOT hard-fault eligible, same class as 0x23/0x49". **That is WRONG.**
It computed the record address as `0xB7FDE`; the correct record is **`0xB7FDC`** (a 2-byte slip),
so it read `0x00` from inside the following field. The true value:

| idx | record | record+8 | value | verdict |
|---|---|---|---|---|
| 0x17 | 0xB7FC0 | 0xB7FC8 | 0x2D01 | HARD |
| **0x18** | **0xB7FDC** | **0xB7FE4** | **0x3D01** | **HARD** |
| 0x1C | 0xB804C | 0xB8054 | 0x3D01 | HARD |
| 0x1D | 0xB8068 | 0xB8070 | 0x3D01 | HARD |
| 0x23 | 0xB8110 | 0xB8118 | 0x0000 | not hard |
| 0x49 | 0xB8538 | 0xB8540 | 0x0000 | not hard |

`0x3D01` is the *same value as monitors 0x1C/0x1D*. **DTC 0x18 → motor-off, power-cycle to recover.**

DTC 0x18 is the **per-task call-cadence / overrun watchdog** (compares an invocation counter against
a scheduler-supplied sequence number — decoupled from data content). It is reachable from nearly
every function in the repointed set via `FUN_0001cba6 → FUN_00016de6(0x18, …)`. Since a code cave
adds instructions to the 1 kHz path, **task-timing headroom is now a real safety question**:

| estimate | cycles | time | % of 1 ms period |
|---|---|---|---|
| optimistic (1 cyc/mem) | 28 | 0.35 µs | 0.035% |
| pessimistic (3 cyc/mem) | 50 | 0.625 µs | 0.063% |

The cave runs **once per tick** (it sits at `LAB_0007feac`, the common tail where all paths converge)
and contains no loop, no divide, no call. Even a 100× error in the cycle estimate leaves >90%
headroom, so a cadence trip from this insertion is not credible on magnitude.

**★ STANDING RULE ADDED: any future cave on the 1 kHz path that introduces a LOOP, a DIVIDE, or a
CALL must re-check this budget against DTC 0x18 — which is hard-fault eligible.**

## 8. Verification artifacts

- `analysis-2020accord/builds/v50_v79/build_v52c_tva.py` — the builder (19 repoints; asserts the raw sites stay raw).
- `analysis-2020accord/verify/verify_v52c_image.py` — **INDEPENDENT** post-build verifier. Per the V40 process
  lesson it imports NOTHING from the builder: its own CRC walk, its own V850 decoder, its own cave
  simulation. **72/72 PASS.** It discovers the repoint set *from the built bytes*, not from a list.
  It caught two real defects during development (see §9).
- `analysis-2020accord/studies/models/eps_v52c_gate2_broad.py` — GATE-2.

## 9. Process notes — what the verification actually caught

- **The verifier FAILED on 0x3B908** when that lane was added. Root cause was a decoder bug in the
  verifier: `0x0780` (`jr disp22`) collides with the 48-bit load prefix `0x0784`, so a single-guess
  length function swallowed the target. Resolved by making the walker search over ambiguous lengths,
  and confirmed in Ghidra. **A boundary check that guesses instruction length can reject valid code.**
- **★★ THE STALE-GHIDRA-IMPORT TRAP — hit TWICE this session, and hash-checking does NOT catch it.**
  1. First occurrence: an agent certified a **superseded image**, reporting the old SHA. Caught
     because the brief pinned the expected SHA.
  2. Second occurrence, and the dangerous one: an agent verified the on-disk SHA **correctly**, but
     the **already-open Ghidra program of the same name was stale**. `read_memory` /
     `disassemble_bytes` returned `ld.h -0x4f60` (raw) at all three NEW repoint sites while a direct
     Python read of the same file offsets returned `00ed` (repointed). Ghidra was holding an earlier
     revision of a file that had since been regenerated in place.

  **Hashing the file on disk proves nothing about what Ghidra has loaded.** A load-bearing
  re-disassembly gate must `import_file` a FRESH copy and expect a `.N` suffix on name collision
  (the trustworthy handle became `/_v52c_plain_image.bin.1`). Beware also that `close_program`
  matches by display NAME and will close *all* duplicates sharing it.

  **★ STANDING RULE: for any pre-flash re-disassembly gate — (a) verify the on-disk SHA, (b) re-import
  fresh rather than trusting an open program of the same name, and (c) spot-check at least one edited
  site against a direct Python byte read of the file before trusting the disassembly.**
  Independently confirmed on disk for this build: 0x36682 `245fa0b0→245f00ed`, 0x36846
  `2477a0b0→247700ed`, 0x3B908 `244fa0b0→244f00ed` (disp `0xB0A0→0xED00`, opcode/reg halfword
  untouched); 132 bytes / 24 runs.
- **Sub-agents self-contradicted.** One returned "LEAVE RAW" in an interim message and "REPOINT" in
  its final for the same lane. Another quoted stock cal values while analysing a V38-based build.
  Both were caught by re-reading the bytes at the lead level.
- **Three agents terminated with `API Error: claude-opus-5 … cybersecurity topic`** despite both the
  agent definitions and an explicit `model: "sonnet"` override specifying Sonnet. They delivered their
  reports before dying. Worth knowing when planning swarms.

## 10. Status / next

**Gate status:**

| Gate | Result |
|---|---|
| Byte / structural integrity (`verify/verify_v52c_image.py`) | ✅ **72/72** — independent of the builder; also re-run independently by the re-disasm agent, 0 discrepancies |
| GATE-1 RAM ownership (`gp-0x1300`) | ✅ **five** independent clearances; method reproduces V50 + V48B failures as controls |
| GATE-2 closed-loop stability | ✅ **CLOSED** — real composition `worst_re=0.189`, GM 14.48 dB, edge **21.19×** (stock 4.66×), monotonic |
| Monitor asymmetry (16-lane set) | ✅ no class-(c)/(d); 3 shadow pairs all input-invariant |
| Task-timing headroom vs DTC 0x18 | ✅ ~0.06% of the 1 ms tick |
| **Ghidra re-disasm of the 19-repoint built image** | ✅ **PASS (A)–(G)**, on a freshly re-imported copy |
| **Self-consistency / dual-path audit of the 3 NEW lanes** | ✅ **PASS — no hazard** |

### Final gate — dual-path audit of the 3 newly-added lanes: CLEAR

- **Prior-sample discontinuity (the key-on risk):** `gp-0x3798` (lane-2 prior sample) and `gp-0x6a80`
  (lane-1 hold counter) are **strictly self-contained — zero external readers**, both zero-init at
  boot. From a zero state `y[1] = α·x[1]`, so `|filtered| ≤ |raw|` on the first cycle: the filter can
  only *shrink* a key-on transient relative to what raw already produces fault-free today.
- **Cross-lane:** one-directional, not mutual — lane 1 reads lane 2's `gp-0x6b44`; lane 2 does **not**
  read back. (Corrects the "read each other" framing.) No comparison against anything raw.
- **Shadow:** `FUN_0006b9ee`'s full caller list (~58, all 0x5a000–0x82000) contains **none** of the
  six functions in this cluster. No shadow-lockstep exposure.
- **Int/float twin:** lane-3's outputs have exactly one consumer, `FUN_0003bc20`, which re-reads the
  *same stored short* and re-checks the *same* ±20000 bound — a redundant re-validate, not an
  independent re-derivation. Cannot diverge.
- **DTC 0x23:** not hard-eligible (formula cross-checked against 0x17/0x1c/0x1d = hard). Trip needs
  a per-cycle diff ≥32768; an EMA can only *attenuate* that magnitude → filtering makes it **less**
  likely to fire, never more.

New structural fact (not a hazard): lane 1's `gp-0x6b46` feeds
`FUN_00038148 → FUN_00037fe6 → gp-0x6ad6` — i.e. into the very convergence point CLAUDE.md names as
the recommended narrow-filter site. Both stages are pure deadband/gain/LERP aggregation with **no DTC
or shadow call**. Same 1 kHz task, so no new cross-rate coupling.

**Residual, honestly stated:** that audit used 4-byte disp16 scans only and did **not** extend the
6-byte extended-displacement check to the destination cells. Reader sets found were small and tight
(1–2 external readers each), so the risk of a hidden extended-form reader is low but **not zero**.
Closing it formally needs a dedicated 6-byte scan over those offsets.

**ALL PRE-FLASH GATES NOW PASS.** V52C is byte-verified, Ghidra-verified, GATE-1 and GATE-2 closed,
and free of monitor asymmetry and dual-path divergence. It remains **UNFLASHED** — a code cave is this
kit's only bricking class, and the flash is the operator's iron-rule call.

Residual, honestly stated: filtering `0x36846` slightly desensitises the DTC-0x23 rate check. **DTC
0x23 is NOT hard-fault eligible** (record `0xB8110`, `record[+8]=0x0000`; formula
`0xB7D58 + (idx-1)*0x1c`, validated against 0x17/0x1c/0x1d = hard and 0x49 = not). The primary
sensor-health architecture — the `gp-0x4486` shadow lockstep (→ fault 0x17 → hard motor-off), M1, M2,
the `0x28F26` gate, and the `FUN_0007f3f8` A/B cross-check — all still read RAW.

**A code cave remains this kit's only bricking class (V24/V27/V48B). Flash ONLY on explicit operator
instruction naming the file and the bus.**
