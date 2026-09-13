# TRACE 2026-09-13 — the LKAS lane to the aggregator, and the Ghidra analysis gap

Agent `ghidrafill` (subagent). Program **`code.bin`** (STOCK dump,
`C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/stock_fw_dump/code.bin`),
confirmed current via `list_open_programs` (three programs open; every call passed
`program:"code.bin"` explicitly). GhidraMCP only. `gp=0xFEDF8000`, `tp=0xBF000`, V850E2 LE.
Python = `bin_decompile` env. Ghidra database **written and saved** (authorised by the brief).

Every claim below is marked **[E]** EVIDENCE (address + method given) or **[B]** BELIEF.

---

## 0. HEADLINE — three results, in order of consequence

1. **[E] `gp-0x6b4c` is the aggregator term that carries the LKAS lane.** I re-derived the whole
   path myself, instruction by instruction. The 2026-08-01 memory is RIGHT on this point; the
   2026-09-13 tracer's "my evidence favours `gp-0x6ad4`" is **WRONG**, and section 4 gives the
   exact reason it looked that way (an `ep`-relative false zero).
2. **[E] `gp-0x6ad4` is NOT the LKAS rate-PID output.** `FUN_0003a382` is a *driver-torque
   tracking* PID: its error is `clamp(gp-0x4f60 − clamp(gp-0x6ad6, ±8192), ±10240)`. It never
   reads `gp-0x6b38`, `gp-0x6b3c`, `gp-0x6b3a` or the rate PID's `y`. LKAS reaches it only
   second-hand, as a perturbation of its *reference*.
3. **[E] `0x2A30E–0x2B421` is a 4,372-byte UNCALLED ISLAND — six functions, zero callers.**
   It is a near-duplicate of the live LKAS output path. **The brief's premise that the PID's `T`
   is "forwarded to `gp-0x6b3c` @`0x2B41C`" names the DEAD copy.** The live forward is
   **`0x2A2EA`**, inside `FUN_00028ea6`. Anyone patching `0x2B41C` would patch dead code.

---

## 1. TASK 1 — the analysis gap, closed

### 1.1 The gap was narrower than briefed [E]
`get_function_by_address` before any edit:

| probe | result |
|---|---|
| `0x2A30E` | `FUN_0002a30e`, body `0x2a30e–0x2a507` (already defined) |
| `0x2A504` | inside `FUN_0002a30e`; it is `dispose 0x0,{r20,r22,r24,r26,r28,lp},[lp]` — a RETURN |
| `0x2A8C0`, `0x2B124` | **no function** |
| `0x2B422` | `FUN_0002b422`, body `0x2b422–0x2b579` (already defined) |
| `0x2B57A` | `FUN_0002b57a`, body `0x2b57a–0x2b62b` (already defined) |

The true hole was **`0x2A508 … 0x2B421`** (0xF1A = 3,866 bytes), not `0x2A30E…0x2B421`.
`0x2B422` / `0x2B57A` were **already defined** — the kit memory
`reference_accord_undefined_live_code_2b422_and_gp6b2c_orphan_writers` is **stale on that point**
(it predates whoever created them). Since `0x2A504` is a `dispose`, `0x2A508` is a genuine entry,
not a fall-through.

### 1.2 Entry points [E, positive-controlled]
Ghidra cannot xref into undefined code, so entries were hunted in Python with a raw Format-V
(`jr`/`jarl` disp22, opcode field **0x1E**) scan over the whole image.
**Positive control 3/3 PASS**: `0x22522 -> 0x28EA6`, `0x23276 -> 0x34350`, `0x2291E -> 0x3AA2C`.

- **EXTERNAL `jr`/`jarl` into the region: 3 raw hits, ALL REJECTED.** `0x1b36a -> 0x2b3e9`,
  `0x20462 -> 0x2ac83`, `0x22ca0 -> 0x2ac41` — every target is **ODD**. V850 instructions are
  halfword-aligned, so an odd target cannot be a branch destination. These are the documented
  `prepare` alias (`prepare` shares opcode 0x1E with `jr`, reg2=0). **Net external entries: ZERO.**
- **INTERNAL: 54 `jr` sites**, all even targets, forming the region's own switch/dispatch webs.

Functions were therefore created at the block boundaries Ghidra's flow analysis reached.

### 1.3 Functions created, and the remaining-undefined answer [E]

| function | body | bytes | status |
|---|---|---|---|
| `FUN_0002a508` | `0x2a508–0x2a891` | 906 | **NEW** (created this session) |
| `FUN_0002a892` | `0x2a892–0x2a939` | 168 | **NEW** |
| `FUN_0002a93a` | `0x2a93a–0x2b06f` | 1,846 | pre-existing |
| `FUN_0002b070` | `0x2b070–0x2b359` | 746 | **NEW** |
| `FUN_0002b35a` | `0x2b35a–0x2b421` | 200 | **NEW** |

906+168+1846+746+200 = **3,866 = exactly `0x2B422 − 0x2A508`.**
**[E] ZERO bytes remain undefined in the range.** No data, no padding, no unreached remainder —
the five bodies tile it exactly, ending flush against `FUN_0002b422`.

**Function count: 2086 -> 2090 (+4).** Instructions scanned: **183,576 -> 184,512 (+936).**
`run_analysis` reported `new_functions:0` (the four were already created by hand). **`save_program`
succeeded.**

### 1.4 The whole island is UNCALLED [E, three independent methods]

| method | result | control |
|---|---|---|
| Python Format-V scan over `0x2A30E–0x2B421` | **0 external callers** | 3/3 PASS |
| Ghidra `get_function_callers` | 0 for `FUN_0002a30e`, `…a508`, `…a892`, `…a93a` | **PASS** — `FUN_00028ea6` -> `FUN_0002214a`; `FUN_0002b422` -> `FUN_0002214a` |
| Ghidra `get_xrefs_to` | 0 refs to `0x2a30e`, `0x2a508`, `0x2a892`, `0x2a93a` | — |
| Python: any 32-bit word == an entry point | **0** for all six entries | control FAILED (see §5) |

**[E] No direct call and no address constant reaches this island.**
**[B] It is a second, separately-compiled copy of the LKAS output path that was never wired in** —
see §3.3 for the register-level twinning that motivates this.

---

## 2. TASK 1b — pre/post xref census

Method: `search_instructions` operand-text, whole program. "Real" = an actual `gp`/`tp` memory
operand; branch-target text collisions (e.g. `bne 0x00066b38`) and the `set1/clr1 0x…,r18`
bit-ops on absolute `0x6ad4` are excluded.

| cell | pre | post | delta | new sites | decision-bearing? |
|---|---|---|---|---|---|
| `gp-0x6b38` | 3 | **5** | **+2** | `0x2a934` **st.h** (`FUN_0002a892`), `0x2b418` **ld.h** (`FUN_0002b35a`) | **YES** |
| `gp-0x6b3c` | 2 | **3** | **+1** | `0x2b41c` **st.h** (`FUN_0002b35a`) | **YES** |
| `gp-0x6b3a` | 2 | 2 | 0 | — | no |
| `gp-0x6b94` | 7 | 7 | 0 | — | no |
| `gp-0x6ad4` | 2 | 2 | 0 | — | no |
| `gp-0x6b4c` | 9 | 9 | 0 | — | no |
| `gp-0x6ada` | 1 | 1 | 0 | — | no |
| `tp+0x73E8` | 1 | 1 | 0 | — | no |
| `tp+0x73EA` | 1 | 1 | 0 | — | no |
| `tp+0x7446` (0xC6446) | 1 | 1 | 0 | — | no |
| `tp+0x746C` (0xC646C) | 5 | **6** | **+1** | `0x2a904` `ld.h` (`FUN_0002a892`) | **YES** |
| `tp+0x7CD0` (0xC6CD0) | 0 | 0 | 0 | — | see note |
| `tp+0x71B4` (0xC61B4) | 4 | **8** | **+4** | `0x2a910`, `0x2a91e`, `0x2a924`, `0x2a92e` (all `FUN_0002a892`) | **YES** |

**Four cells moved. What each delta means:**

- **`gp-0x6b38` gains a SECOND WRITER (`0x2a934`) and its only non-CAN READER (`0x2b418`)** — both
  in the dead island. Live writer remains `0x2a23c`. The delta is real but **inert**.
- **`gp-0x6b3c` gains a second writer `0x2b41c` — dead.** **This is the site the brief called
  the forward.** The live one is `0x2a2ea` (§3.2).
- **`tp+0x746C` (`0xC646C`) reaches SIX read sites** — `0x2a1ee`, **`0x2a904`**, `0x2b656`,
  `0x2c488`, `0x36686`, `0x3684a`. `0x2a904` is precisely the occurrence the `firmware-decompile`
  skill records as missed by `search_instructions`. **It is now visible — and it is in dead code**,
  so the *live* reader count is five. Anyone reasoning about `0xC646C`'s blast radius (the V57
  fork precedent) should use **five live**, not six.
- **`tp+0x71B4` (`0xC61B4`) doubles, 4 -> 8 readers**, the four new ones all in dead
  `FUN_0002a892`. Live count stays 4 (all in `FUN_00028ea6`). `0xC61B4` is 512 stock / 3072 on
  V280+ — **the raise is consumed only by the four live sites.**
- **`tp+0x7CD0` (`0xC6CD0`) is 0 both before and after, and that is CORRECT for this program.**
  On stock, `0x2a1ee` reads `0x746c`. The `0xC6CD0` repoint exists only on V57+/V282 images.
  **This is a stock-image fact, not a null result** — do not read it as "the cell is dead".

---

## 3. TASK 2 — which term carries LKAS, traced end to end

### 3.1 What `gp-0x6ad4` actually is [E — full `decompile_function(0x3a382)`]

```
ref  = clamp(gp-0x6ad6, ±LE16(tp+0x7200 = 0xC6200) = 8192)
err  = clamp(gp-0x4f60 − ref, ±0x2800)              # gp-0x4f60 = TORSION-BAR TORQUE SENSOR
P    = EMA(err·LERP(gp-0x6ac0)>>10 ·32, cal 0xC6450)      -> gp-0x367c
I    = accumulate(err·LERP(gp-0x6ac0)>>10)               -> gp-0x3688   (no x32)
D    = EMA(clamp((err−err[n-1])·LERP>>10, ±0x2800)·32, cal 0xC644A) -> gp-0x3680
out  = ((P+I+D)>>5) · LERP(gp-0x671a)>>10 · POL(gp-0x6752)
       then min-magnitude against the AUTH ceiling
0x3a8a0  st.h r10,-0x6ad4[gp]
```

**Inputs, exhaustively, from the decompile text:** `gp-0x6ac0`, `gp-0x671a`, `gp-0x6a5e`,
`gp-0x6bda`, `gp-0x6966`, `gp-0x6a98`, `gp-0x2588/-0x2584`, **`gp-0x6ad6`**, **`gp-0x4f60`**,
`gp-0x6765`, `gp-0x67f4`, `gp-0x67fe`, `gp-0x3678/367c/3680/3684/3688`, `gp-0x6752`.
**`gp-0x6b38`, `gp-0x6b3c`, `gp-0x6b3a` do NOT appear. Neither does the rate PID's `y`.** [E]

So **`gp-0x6ad4` is the output of a driver-torque tracking servo, not of the LKAS rate PID.**
Its read of `gp-0x67fe` at `0x3a704` proves *gating*, not identity — and per the kit's own
`reference_accord_gp6ad4_engagement_gate_and_36682_closed_loop_math`, `gp-0x67fe` is the EPS's own
FOC/assist substate, **not an openpilot-engagement flag**.

### 3.2 The live path from the rate PID's `T` to `gp-0x6b94` [E, instruction-anchored]

```
FUN_00028ea6  (jarl from 0x22522, task-1 1 kHz)
 0x2a1ee  ld.h  0x746c[tp],r7          gain = LE16(0xC646C)=891  (V282 repoints this operand @0x2a1f0)
 0x2a1f8  ld.hu 0x71b4[tp],r16         ceiling = LE16(0xC61B4)   512 stock / 3072 V280+
 0x2a23c  st.h  r1,-0x6b38[gp]         T = clamp((y·gain)>>15, ±ceiling)   [r1 <- r11 @0x2a226]
 0x2a2bc  cmp   r0,r13                 gate flag
 0x2a2c2  cmove 0x0,r1,r16             r16 = (r13==0) ? 0 : T        <<< THE GATE
 0x2a2ea  st.h  r16,-0x6b3c[gp]        gp-0x6b3c = gated T           <<< THE LIVE FORWARD
       |
FUN_0002b422  (jarl from 0x22530, SAME tick, immediately after)
 0x2b42e  ld.h  -0x6b3c[gp],r12
          clamp r12 to ±LE16(tp+0x71b2 = 0xC61B2)   [512 stock / 2048 on 4x builds]
 0x2b45c  st.h  r12,-0x6b3a[gp]        telemetry mirror only
 0x2b52a  sst.h r0, 0x2[ep]   = 8104   struct+2 = 0    -> gp-0x62e0[1] -> TERM 0 (gp-0x6b4a) KILLED
 0x2b52c  sst.h r12,0x4[ep]   = 8264   struct+4 = LKAS -> gp-0x62f8[1]
 0x2b53e  jarl  0x25c32,lp             (bytes bf ff f4 a6, decoded -> 0x25C32)
       |
FUN_00025c32  0x26490 movea -0x62f8,gp,ep ; 0x26496 sst.h  -> gp-0x62f8[1]
       |   slot index = 1; cal 0xC4124 = [0,0,5,0,5,5,0,0,0,5,0] -> slot 1 is MODE 0
FUN_00026c80  (jarl from 0x225f6)    mode 0: gp-0x62b0[1] = gp-0x62f8[1]
 0x2730c  st.w  r1,-0x3d88[gp]         gp-0x3d88 = SUM over gp-0x62b0[]
 0x276d4  ld.w  -0x3d88[gp],r10
 0x276f0  st.h  r8,-0x6b4c[gp]         gp-0x6b4c = clamp(sum, ±0x2800)
       |
       +--(a) 0x3aa3e  ld.h -0x6b4c[gp],r6   FUN_0003aa2c   DIRECT summand, UNIT weight
       |
       +--(b) 0x3816c  ld.h -0x6b4c[gp],r14  FUN_00038148
              0x382d2  st.h r11,-0x6b70[gp]  (sole gp-0x6b70 writer in that function)
              -> FUN_00037fe6 -> gp-0x6ad6 (PID REFERENCE, term 3)
              -> FUN_0003a382 -> 0x3a8a0 st.h -0x6ad4
              -> 0x3aca8 ld.h -0x6ad4[gp],r6   FUN_0003aa2c   second summand
       |
FUN_0003aa2c  0x3acfa / 0x3ad12 / 0x3ad20  st.h -> gp-0x6b94  (clamp ±0x2800, shadow gp-0x4ce0)
 -> 0x453e0 FUN_0004503c governor -> gp-0x6ace -> FUN_000456a4 -> gp-0x6acc
 -> FUN_00042af8 shaper -> gp-0x6b08 (+ gp-0x6afe) -> gp-0x6b98  (FOC motor command)
```

**[E] The LKAS lane enters the aggregator by TWO routes: `gp-0x6b4c` DIRECTLY (unit weight), and
`gp-0x6ad4` INDIRECTLY (as a reference perturbation of the torque-tracking PID).**
Route (b) is conditional on term 3's weight byte `0xC64B0` and on `gp-0x6b4c`'s gain in
`FUN_00038148` — not re-verified here (§5).

### 3.3 Why the island is a twin, not a third route [E for the bytes, B for the reading]

Dead `FUN_0002b35a` ends:

```
0x2b40e cmp r0,r16 / 0x2b414 mov 0x0,r15 / 0x2b416 be 0x2b41c
0x2b418 ld.h -0x6b38[gp],r15            <- else r15 = T
0x2b41c st.h r15,-0x6b3c[gp]            <- same gated copy
0x2b420 jmp lp
```

That is **the same gated `gp-0x6b38 -> gp-0x6b3c` copy as `0x2a2bc/0x2a2c2/0x2a2ea`, with a
different register allocation** [E]. Likewise dead `FUN_0002a892` at `0x2a8c0–0x2a938` re-reads
`gp-0x6806`, `gp-0x69b0`, `gp-0x6b2c`, `gp-0x6b30`, `0xC646C`, `0xC61B4`, `gp-0x6752` and stores
`gp-0x6b38` — the same shape as live `0x2a1ee–0x2a23c`.
**[B] Two compilations of one source unit; only one was linked into the task.**

---

## 4. ADJUDICATION — which memory is wrong

- **`reference_accord_gp671d_arm_inverts_r24_on_v280plus_and_6ad4_vs_6b4c_conflict` §3 is WRONG**
  where it concludes "my evidence this session favours `gp-0x6ad4`". **Cause, precisely [E]:** it
  scanned `FUN_00026c80`'s body across "49 distinct gp cells" for LKAS-domain *cell names* and
  found none. But the LKAS command does not enter `FUN_00026c80` by a named `gp` cell — it enters
  through the **`ep`-relative request arrays**. `FUN_00025c32` sets the base with
  `movea -0x62f8,gp,ep` (6 sites: `0x25eaa`, `0x25f0c`, `0x26490`, `0x26792`, `0x26a74`, `0x26ae2`)
  and the actual stores are `sst.h 0x0[ep]`, **which carry no `-0x62f8` in operand text at all.**
  This is the exact false-zero class the store's own
  `reference_accord_two_lkas_routes_gp6b4c_bypasses_auth` documents under "Method trap".
- **`reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain` is RIGHT** on its load-bearing
  claim ("`gp-0x6b4c` is the only LKAS-sourced summand"). Its parenthetical label for `gp-0x6ad4`,
  *"resonance, eliminated V56"*, is a stale mislabel — the lane is live and is a torque-tracking
  PID — but that does not touch the LKAS attribution.
- **`reference_accord_aggregator_11term_loop_census_units_and_fork` is NOT wrong in its math.**
  Its §7 derives `err = clamp(gp-0x4f60 − ref, ±10240)` correctly, i.e. it already has the
  torque-tracking form. Only the shorthand label "PID P+I+D" invites the LKAS reading. **If the
  orchestrator's summary of it as "the LKAS rate-PID P+I+D output" came from that file, the file
  should gain the word "driver-torque", not a retraction.**

**I edited no memory file** (kit convention: ask first).

---

## 5. WHAT I DID NOT VERIFY

1. **Register-indirect reachability of the island was NOT excluded.** My `jmp [rN]` census returned
   **1,475 hits** image-wide against 756 plain `jmp lp` — the bit pattern `0x0060|reg` clearly
   collides with other encodings, so the scan is **not adjudicable** and I did not lean on it.
   A dispatch through a RAM-resident pointer written at boot would defeat all four of my methods.
   So "uncalled" is **[E] for direct calls and address constants**; "dead" remains **[B]**.
2. **The 32-bit-word pointer scan had a FAILING positive control** — 0 words equal `0x28EA6`,
   `0x3AA2C` or `0x2B422` either, so this firmware simply does not store function entries as
   absolute words. Its null for the island is therefore **weak corroboration, not proof**.
3. **The `movhi`/`movea` address-construction scan was run WITHOUT a positive control.** 0 hits;
   treat as weak.
4. **I did not verify that `r1` is unmodified between `0x2a23c` and `0x2a2c2`.** The `cmove` reads
   `r1` and `0x2a226` is the last write I observed, but I did not disassemble every instruction in
   that 134-byte span. If something rewrites `r1`, `gp-0x6b3c` carries a different value than `T`.
   **Next step: `disassemble_function(0x28ea6)` and scan `0x2a23c–0x2a2c2` for `r1` as destination.**
5. **Route (b)'s live magnitude is unquantified.** I confirmed the wiring
   (`gp-0x6b4c -> 0x3816c -> 0x382d2 -> gp-0x6b70 -> gp-0x6ad6`) but did NOT read `FUN_00038148`'s
   gain for `gp-0x6b4c` (`tp+0x73aa`) nor term 3's enable byte `0xC64B0`. Prior kit memory says the
   weight bytes are all 1, **not re-verified here.**
6. **`gp-0x6b4a` = 0 is RELAYED, not re-derived.** I confirmed `0x2b52a` writes a literal zero into
   field +2 for slot 1 [E], but slot 2's `gp-0x6b76` producer and `0xC616C`=0 are from memory.
7. **I did not decompile `FUN_0002b57a`** (the `gp-0x6b3a` reader) — the census shows its single
   read at `0x2b5b2`, and prior memory calls it a float monitor; unverified this session.
8. **The new function boundaries are Ghidra's flow-following result**, not hand-proven. They tile
   the range exactly, which is strong, but a mid-function entry could still be mis-attributed.

---

## 6. Ghidra database changes made (all authorised, saved)

`create_function` x 4: `0x2a508`, `0x2a892`, `0x2b070`, `0x2b35a` (each `disassemble_first:true`).
`run_analysis`. `save_program` -> success. **No renames, no retypes, no labels, no comments.**
Every exploratory `disassemble_bytes` used `dry_run:true`.
