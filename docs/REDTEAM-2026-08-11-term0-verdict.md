# Red-team verdict: `FUN_00037fe6` term-0 claim (A1–A5)

**Role:** adversarial verifier, independent from the agent that produced the original claim.
**Target:** the term-0 structure in `FUN_00037fe6` (produces `gp-0x6ad6`) and its input `gp-0x6b4a`.
**Program:** `code.bin` (stock dump, `../accord-firmwares/analysis-2020accord/stock_fw_dump/code.bin`).
Every address below is stock; `FUN_00037fe6`, `FUN_00026c80`, `FUN_00025c32`, `FUN_0003405a`,
`FUN_00033d10`, `FUN_0003bd7c`, `FUN_00065eda`, `FUN_0007f3f8` are all pre-cave application code —
none of it sits in a region any build to date has touched, so the stock read applies to the flown
V90 image as well. `gp = 0xFEDF8000`, `tp = 0xBF000`.

## Verdicts at a glance

| # | Claim | Verdict | Confidence |
|---|---|---|---|
| A1 | Term 0 unconditional, negated | **CONFIRMED** | EVIDENCE (decompile + disasm + byte-level opcode decode) |
| A2 | Term 0 has no calibration weight | **CONFIRMED** | EVIDENCE (full instruction trace, no `mulh` on the term-0 path) |
| A3 | Term 0's window ±25600 = the final clamp | **CONFIRMED** | EVIDENCE (byte-level immediate decode) |
| A4 | `gp-0x6b4a` sources are all LKAS-internal | **REFUTED** — with a nuance neither the claim nor its own "why it matters" anticipated | EVIDENCE for the structural chain; BELIEF on completeness (see Open questions) |
| A5 | `gp-0x67ab != 1` gates terms 1–7 as a block | **CONFIRMED** | EVIDENCE (decompile + disasm + byte-level condition-code decode) |

---

## A1 — term 0 is unconditional and negated

`decompile_function(0x37fe6)`:

```c
iVar4 = 0;
if (&DAT_00006400 + *(short *)(unaff_gp + -0x6b4a) < &DAT_0000c801) {
    iVar4 = (int)-*(short *)(unaff_gp + -0x6b4a);
}
if ((byte)(*(byte *)(gp-0x67ab) * (*(byte *)(gp-0x67ab) < 2)) != '\x01') {
    iVar4 = iVar4 + <seven-term sum>;
}
```

Disassembly (`disassemble_function(0x37fe6)`), the term-0 block runs **before and independent of**
the `gp-0x67ab` gate:

```
00037fe6: ld.bu -0x67ab[gp],r13      ; r13 = gp-0x67ab
00037fea: ld.h  -0x6b4a[gp],r15      ; r15 = gp-0x6b4a
00037fee: cmp   0x1,r13
00037ff0: cmovh 0x0,r13,r14          ; r14 = (r13>1) ? 0 : r13   (used later for the !=1 gate)
00037ff4: addi  0x6400,r15,r9        ; r9 = r15 + 0x6400
00037ff8: ori   0xc801,r0,r7
00037ffc: cmp   r7,r9                ; r9 - r7, sets CY
00037ffe: mov   0x0,r10
00038000: bnc   0x38006              ; skip negation if r9 >= 0xc801 (unsigned)
00038002: sub   r15,r10              ; r10 = 0 - r15 = -r15   <-- the negation
00038004: sxh   r10
00038006: ld.h  -0x6b70[gp],r13      ; start of the 7-term block (unconditional so far)
   ...
000380b0: cmp   0x1,r14
000380b2: be    0x380b6              ; if gp-0x67ab==1 (via r14): SKIP the add
000380b4: add   r13,r10              ; else: r10 += (7-term sum)
```

**Byte-level confirmation of the two branches** (per the operator's standing instruction to decode
the condition nibble explicitly, given this exact class of site — `be`/`bne` — has inverted a probe
before):

- `sub r15,r10` at `0x38002`: raw bytes `AF 51` → halfword `0x51AF` = `0101 0001 1010 1111`. Format-I
  decode: reg2 (bits15-11) = `01010`=r10 ✓, opcode (bits10-5) = `001101`=`0x0D` (standard V850 `SUB
  reg1,reg2` → `reg2 = reg2 - reg1`), reg1 (bits4-0) = `01111`=r15 ✓. With r10=0 from the preceding
  `mov 0x0,r10`, this is a genuine two's-complement negation, not a `subr`/`satsubr`-class opcode.
- `bnc 0x38006` at `0x38000`: raw bytes `B9 05` → low nibble of byte0 (`0xB9`) = `0x9` = **BNC** (branch
  no-carry) in the V850 condition-code table. Matches Ghidra's mnemonic independently.
- `be 0x380b6` at `0x380b2`: raw bytes `A2 05` → low nibble of byte0 (`0xA2`) = `0x2` = **BE** (branch
  equal), distinct from `0xA` (BNE). Confirms the `gp-0x67ab==1` gate really takes the branch (skips the
  add) on EQUAL, not not-equal — the specific inversion class this kit has hit before did NOT occur here.

**A1: CONFIRMED.** Term 0's own computation (`r10 = -gp-0x6b4a` when `|gp-0x6b4a| <= 0x6400`, else 0) runs
unconditionally relative to `gp-0x67ab`; only the ADDITION of the 7-term sum is gated.

## A2 — term 0 carries no calibration weight

Traced every instruction from `gp-0x6b4a`'s load (`0x37fea`) to its use in the final `add r13,r10`
(`0x380b4`): `ld.h → addi → cmp → mov → bnc → sub → sxh → (falls straight into the 7-term block,
which does not touch r10) → add`. **No `mulh` (or any multiply) ever executes on r10 or its precursor
r15.** Contrast with each of terms 1–7, which is individually loaded, gated by its own `addi`/`cmovc`
window check, AND multiplied by a distinct per-term calibration byte via `mulh` before being summed
(`ld.bu 0x74aX[tp],rN; ...; mulh rN,rM`, for `tp+0x74ac..0x74b3` — 7 distinct cal bytes for 7 terms).

Checked for the two things the brief specifically asked about: an implicit shift (none — term0's
only shift is `sxh`, sign-extension, not a scale) and a multiply folded into an upstream store
(none in *this* function's path; see the A4 write-up for what happens further upstream in
`gp-0x6b4a`'s own producer, which is a separate question from A2's literal scope).

**A2: CONFIRMED.**

## A3 — term 0's gate window is ±25600, matching the final clamp

`0x37ff4: addi 0x6400,r15,r9` / `0x37ff8: ori 0xc801,r0,r7` / `0x37ffc: cmp r7,r9` / `0x38000: bnc`.
This is the standard V850 idiom for `|x| <= K`: unsigned `(x + K) < (2K+1)`. Here `K = 0x6400 = 25600`
and `2K+1 = 0xc801`, confirming the window is exactly `[-25600, +25600]`.

The function's own final clamp (`0x38126-0x3813e`): `iVar4 < 0x6401` / `< -0x6400` → clamps the
COMBINED reference to `[-25600, +25600]` before storing to `gp-0x6ad6`. Term 0's own gate window is
therefore identical to the cell's own output rail — term 0 alone, unweighted, can drive the reference
to its rail. (Terms 1–7's *local* gate windows are smaller, e.g. `±0x2800=10240` for most — but per
the brief's own framing this is a separate question from whatever upstream clamp bounds term 7's
actual range at write time; I did not re-verify the `0xC6200`/±8192 figure independently, see Open
questions.)

**A3: CONFIRMED** for the stated comparison (gate window identity, term0 vs. the cell's own final rail).

## A4 — is `gp-0x6b4a` "all LKAS-internal"? **REFUTED**, with a real nuance

### The chain, hop by hop

1. **`gp-0x6b4a`'s only writer is `FUN_00026c80`** (confirmed two ways: `search_instructions`
   operand-pattern `"6b4a"` → 11 hits; independent raw Python LE byte scan over `code.bin` for the
   disp16 gp-relative encoding (`hw1==0x94b6`, `reg1==4`) → same 11 hits, same addresses, same opcode
   fields (`0x39`=ld.h, `0x3b`=st.h, `0x31`=movea). Full agreement between two independent methods.
2. Inside `FUN_00026c80`: an 11-lane loop (i=0..10) reads a per-lane MODE byte from **`tp+0x5124[i]`**
   (calibration; read from the image: `[0,0,5,0,5,5,0,0,0,5,0]`) and, depending on the mode, either
   passes through `gp-0x62e0[i]`→`gp-0x6298[i]` and `gp-0x6274[i]`→`gp-0x625c[i]`, or zeroes them.
   A second loop sums: `S_flag1 = Σ gp-0x6298[i]` where **`tp+0x5118[i]`** (image: all eleven bytes =
   `1`) is nonzero — i.e. the mask is open for every lane — plus a rate-limited `Σ gp-0x625c[i]`, plus a
   `gp-0x6a62`-indexed LERP term. This sum becomes **`gp-0x6b4a = clamp(iVar13, ±0x6400)`** directly
   (confirmed in disassembly at `0x277be`, not just decompile) and separately scales into `gp-0x6b4c`.
3. `gp-0x6298[i]`/`gp-0x625c[i]` are populated (via `gp-0x62e0[i]`/`gp-0x6274[i]`) by **`FUN_00025c32`**,
   called once per lane. **Corroborated the caller count two ways**: `get_function_callers(0x25c32)` →
   10 functions; `search_instructions(mnemonic=jarl, operand="25c32")` → the same 10 call sites, same
   addresses. jarl targets are absolute (not subject to the gp-relative encoding trap), so this count is
   solid — **lane 10 is genuinely never invoked** (the defensive `clamp(idx,0,10)` inside `FUN_00025c32`
   is dead code for idx==10, not a missed caller).
4. For each of the 10 callers, extracted the value written to the caller's local struct at offset+2
   (→ `gp-0x62e0` → `gp-0x6298`, the arm that survives lane2's mode=5 into `gp-0x6b4a`) and offset+6
   (→ `gp-0x6274` → `gp-0x625c`). In **9 of 10** lanes, both are a literal constant `0` on the code path
   reaching the call. **Lane 2 (caller `FUN_0003405a`, `local_2c = 2`) is the only lane with a live,
   computed value at offset+2: `iVar7`.**
5. `iVar7` traces to **`gp-0x6b76`** (`FUN_0003405a`'s only non-gate source for it), whose only writer is
   **`FUN_00033d10`** — a genuine 4-stage PID/filter (P: gain `tp+0x70c0`; I: integrator `tp+0x70b8`;
   D-ish term: `tp+0x70bc`/`tp+0x70c8`; output clamp/rate stage: `tp+0x70d0`/`tp+0x70d4`/`tp+0x70d8`/
   `tp+0x70cc`).
6. **The nuance.** I expected this PID to track `gp-0x4f60` (driver torque — independently confirmed:
   `gp-0x4f60`'s only real writer is `FUN_0007f3f8`, which does dual-channel ADC differencing plus an
   inverted-value redundancy check plus DTC fault-confirmation state machines with codes 9, 0xb, 0xc,
   0xd — textbook dual-channel torque-sensor input processing, not a CAN/LKAS parse). That's correct as
   far as it goes, but `gp-0x4f60`/`gp-0x4f68` (its magnitude companion) appear in `FUN_00033d10` **only
   as an enable gate** (`bVar1 = gp-0x4f68 < cal`, gates whether the integrator runs) — driver torque
   does **not** enter as an additive or multiplicative term in the tracked value.
7. The actual process variable is `fVar13 = gp-0x6be0 - gp-0x6bf0`. `gp-0x6bf0` (`FUN_0003bd7c`) is
   built from `gp-0x4ee8` via a ±0x800/±0x1000 wraparound-unwrap (the classic idiom for a 12-bit rotary
   sensor), scaled by `gp-0x6abe` (independently on file in this kit's memory as column deg/s) and the
   steering-direction sign `gp-0x6752`. `gp-0x4ee8`'s writer, **`FUN_00065eda`, is unambiguously the
   motor resolver decode routine**: masks a raw ADC to 11 bits (`&0x7ff`), computes
   `SQRT(sin²+cos²)` (resolver-magnitude check), extracts sin/cos channels with a `-0x1ff` ADC offset,
   and drives resolver-excitation outputs. This is a hardware position sensor. `gp-0x6be0`
   (`FUN_0002cc2a`) is a large boost/assist state machine gated by vehicle speed (`gp-0x69aa`) and
   engagement state (`gp-0x67fa`, `gp-0x67e8`) that shows the same rotary-unwrap idiom on a related seed
   (`gp-0x6a0e`); I did not close its ultimate seed as cleanly as `gp-0x4ee8`'s (see Open questions), but
   found no CAN read and no LKAS-command cell anywhere in either producer.

### Verdict

**A4 is REFUTED as literally stated** — "all 11 lanes are LKAS-internal" is false; lane 2 is not.
But the refutation does **not** land on the alternative the brief's own "why it matters" section
offered ("driver-torque-descended, or a MIX ⇒ ordinary torque feedback"). What's actually there is a
**third category**: lane 2 carries a **column/motor angle-RATE signal (resolver-descended)**, heavily
**gated** by driver-torque presence/magnitude but not carrying torque as a value. This still breaks
the "memoryless feed-forward of the LKAS command" framing (`gp-0x6b4a` is demonstrably not purely
LKAS-internal), but the replacement mechanism is a rate/kinematic feedback term, not ordinary torque
feedback, and needs its own characterization before it can support a Q-derivation of the resonance
argument.

## A5 — `gp-0x67ab != 1` gates terms 1–7 as a block

Already covered in A1: `cmp 0x1,r14` / `be +6` skips `add r13,r10` (the 7-term sum) precisely when
`r14==1`, and `r14` was computed as `(gp-0x67ab < 2) ? gp-0x67ab : 0` — so `r14==1` iff
`gp-0x67ab==1` exactly. Byte-level condition-code decode (`0xA2` low nibble `0x2`=BE, not `0xA`=BNE)
independently confirms the branch fires on equality. At `gp-0x67ab==1`, `gp-0x6ad6`'s pre-clamp value
is purely `-gp-0x6b4a` (before the speed-LERP scale and final ±25600 clamp, both of which apply
identically whether or not the 7-term block contributed).

**A5: CONFIRMED.**

---

## Open questions / what I'd need to fully close this

1. **9 non-lane-2 callers were checked only in their tail block** (the join point after their internal
   if/else, immediately before the `FUN_00025c32` call) — not their full bodies. That block is reached
   on every path I traced, but I have not exhaustively ruled out an earlier `goto` bypassing it, or a
   live value at offset+2/+6 that gets overwritten to 0 by the time execution reaches that tail on some
   path I didn't walk. Lane 8 (`FUN_0002caa2`) in particular showed an ALL-constant tail with no visible
   computed value anywhere in the captured window — worth a dedicated full-function read if this needs
   to be airtight.
2. **`gp-0x6be0`'s ultimate seed** (inside `FUN_0002cc2a`, via `gp-0x6a0e`, written by `FUN_00052a14`)
   was not traced to a hardware register the way `gp-0x4ee8`→`FUN_00065eda` was. It shows the same
   rotary-unwrap idiom and speed/engagement gating, consistent with a column-kinematic classification,
   but I'd want `FUN_00052a14` decompiled and `gp-0x6a0e`'s writer chain closed before calling it
   fully EVIDENCE rather than a strong pattern-match.
3. **A3's comparison to term 7's ±8192 figure** (from the original claim, attributed to `0xC6200`) was
   not independently re-derived here — I confirmed term 0's own window and the cell's own final clamp,
   but did not re-verify the `0xC6200` cap on term 7's actual range. Next step: trace `gp-0x6b70`'s
   writer chain and find where `0xC6200` (or its true address, not assumed) applies to it.
4. **The `gp-0x6a62`-indexed LERP term** that also feeds `gp-0x6b4a` (alongside `S_flag1` and the
   `gp-0x625c` slew sum) was not classified in this pass — `gp-0x6a62` is read by dozens of functions
   including the FOC/torque-model bridge (`FUN_000757a2`), consistent with a speed-like or rate-like
   broadcast signal, but I did not find its producer or confirm its physical identity. This is a third,
   unexamined contributor to `gp-0x6b4a` and could itself be LKAS- or sensor-descended.

All four items are tractable with the tools already used here (`decompile_function` +
`search_instructions` cross-checked against a raw byte scan); none required anything beyond GhidraMCP.

**Status at session close: items 2 and 3 remain OPEN, not closed by assertion.**
- **Item 2 (lane 8's full body, `FUN_0002caa2`)**: only its tail block (post-branch-merge, immediately
  before the `FUN_00025c32` call) was read; it showed all-constant values at both offset+2 and offset+6.
  Closing this properly means reading the function's full body the way `FUN_0003405a` (lane 2) was read,
  to rule out a live value on a path the tail-only read can't see. Cost: one `decompile_function` call
  plus the same trace depth already applied to lane 2 — moderate, not large.
- **Item 3 (`gp-0x6be0`'s lineage, `FUN_0002cc2a` → `gp-0x6a0e` → `FUN_00052a14`)**: shows the same
  rotary-unwrap idiom and speed/engagement gating as the confirmed-resolver `gp-0x6bf0` path, but its
  ultimate hardware source was not pinned down as cleanly. Cost: one more `decompile_function` call on
  `FUN_00052a14` plus tracing `gp-0x6a0e`'s further upstream writers. Given lane 2 is now known to be
  inert regardless of its own input dynamics, this item has dropped in priority but is left open rather
  than asserted either way.
- **Item 4 (lane 10, no caller)**: CLOSED this session — see the lane-2 addendum below; two independent
  methods (`get_function_callers` and a `jarl`-operand search) agree on exactly 10 callers, all indexing
  0-9. Lane 10 is genuinely unused, not a missed caller.

---

## Addendum (same session, later): lane 2 is structurally DEAD — corrects the dynamics framing above

Follow-up tasking asked for a frequency-response/phase characterization of lane 2 at 7.79 Hz (does the
resolver-rate PID found above act as anti-damping or damping). Building that model required pinning
down `FUN_00033d10`'s exact output path, and the decompile of its tail is genuinely ambiguous —
classic compiler branchless/`cmov` codegen with heavy variable reuse across a collapsed 3-way branch.
Dropped to disassembly (`disassemble_function(0x33d10)`) and re-derived it register-by-register.

**Finding: `FUN_00033d10`'s live filter result (register `r9`, the output of the whole P/I/deadband/
second-stage cascade) is stored to `gp-0x6b78`** (`0x33ffa: st.h r15,-0x6b78[gp]`, where
`r15 = (gate open) ? r9 : 0x7fff`) — **not to `gp-0x6b76`**, which is what `FUN_0003405a` (lane 2's
caller) actually reads for `iVar7`, the numeric value that reaches `gp-0x62e0[2]`/`gp-0x6298[2]`/
`gp-0x6b4a`.

`gp-0x6b76` is computed by a SEPARATE tail block (`0x33fec`-`0x3402c`) implementing "clamp `gp-0x4f60`'s
sign to a magnitude of `tp+0x716c`". Traced all three branches to their final register value:

```
0x34006: r14 = tp+0x716c                    (gp-0x4f60 > 0 branch)
0x34018: r14 = gp-0x4f60  (== 0 in this sub-case, since the outer branch already required gp-0x4f60<=0)
0x34014: r14 = -tp+0x716c                   (gp-0x4f60 < 0 branch)
```

`tp+0x716c = 0xBF000+0x716C = 0xC616C`. Read directly from the image: bytes `00 00` = **0**, confirmed
identically on stock `code.bin` and the flown V90 image, and confirmed untouched by any build
(`grep 716c\|C616C analysis-2020accord/build_v*_tva.py` → 0 hits). With that constant at 0, **`r14 = 0`
in all three branches, unconditionally.** The store that follows (`0x3402c: st.h r8,-0x6b76[gp]`)
therefore always writes either `0` (gate open, r8 computed from r14=0 either directly or via
`0-r14`) or `0x7fff` (gate closed — a fault sentinel).

**`gp-0x6b76` cannot carry a nonzero live value in the current calibration, full stop.** The elaborate
resolver-derived PID cascade computes correctly every cycle and lands in `gp-0x6b78` — a cell
`FUN_0003405a` only reads to help set a qualitative state byte (verified: `gp-0x6b78` has exactly 1
writer + 2 readers, both readers inside `FUN_0003405a`, both feeding its internal state machine, never
`uStack_2a`, the struct slot that becomes `gp-0x62e0[2]`). Even the sentinel value (`0x7fff`) is caught
and zeroed by `FUN_0003405a`'s own first gate condition (`iVar7 > 0x5000`).

**Net effect: lane 2's contribution to `gp-0x6b4a` is unconditionally zero, on every path, regardless
of the resolver dynamics traced in the main A4 write-up above.** The structural claim in A4 — that this
lane's wiring is non-LKAS-internal (resolver-descended, torque-gated) — still stands as written; what's
new is that the wiring is calibrated off by a single zero constant (`0xC616C`) sitting between a fully
live computation and the cell its only consumer reads. Whether that's a deliberate Honda reserve/disable
or an artifact can't be determined from statics alone. A frequency-response/phase characterization
(originally requested) is therefore moot — there is no signal to have a phase relationship with column
velocity, since its amplitude is identically zero at every operating point.

**Calibration values read from the image while building the (now-moot) filter model, for the record**
(all confirmed virgin — 0 hits in `build_v*_tva.py` for the whole `0x70b8`-`0x70d8` range):

| tp offset | address | role in `FUN_00033d10` | value |
|---|---|---|---|
| `0x70c4` | `0xC60C4` | stage-1 gain on rate-diff (K_D1) | **0.0** |
| `0x70bc` | `0xC60BC` | stage-1 derivative gain (K_D3) | **0.0** |
| `0x70c0` | `0xC60C0` | stage-1 P+D clamp | 1.0 |
| `0x70c8` | `0xC60C8` | stage-1 proportional gain (K_D2) | 14.0 |
| `0x70b8` | `0xC60B8` | I-term gain (on `gp-0x6be0` alone) | ≈0.01 |
| `0x70cc` | `0xC60CC` | stage-2 derivative gain (K_4) | **0.0** |
| `0x70d0` | `0xC60D0` | stage-2 output clamp | 5.0 |
| `0x70d4` | `0xC60D4` | stage-2 gain on the `gp-0x6a58`-corrected term | ≈0.002 |
| `0x70d8` | `0xC60D8` | stage-2 rate-term gain | not fully decoded |
| `0x716c` | `0xC616C` | **the output magnitude clamp that kills `gp-0x6b76`** | **0** |
| `0x749d` | `0xC749D` | I-term enable flag (byte, `!=0` enables) | `0xB0` (enabled) |

Three of the filter's own internal gains (`K_D1`, `K_D3`, `K_4`) are independently zero — the cascade
that does execute is simpler than a full PID (mostly a proportional term ×14 on the rate difference,
plus a slow leaky-integrator term on `gp-0x6be0` alone, plus a `gp-0x6a58`-based correction stage) —
but this is now academic given the output is severed downstream.

### 🛑🛑 `0xC616C` (`tp+0x716c`) = 0 — NEVER RAISE

**Not a dormant feature to enable.** A future session finding this cal at 0, virgin across every build,
will be tempted to read it as "a free, never-tried, unclipped lever." It is not. The idiom it feeds is:

```
r14 = (gp-0x4f60 > 0) ?  tp+0x716c
    : (gp-0x4f60 < 0) ? -tp+0x716c
    :                    0
```

i.e. `r14 = sign(driver torque) × constant`. **Raising `0xC616C` off zero turns this into a Coulomb
relay on driver-torque sign, injected straight into the driver-feel reference `gp-0x6ad6` via `gp-0x6b76`
→ lane 2 → `gp-0x6b4a` → term 0.** That is exactly the class of lever this kit has spent fifteen builds
removing (`V80`: "the worst grinding the car has ever produced," from a relay in this same class). It is
arguably worse than the standing `0xC4080` (K0) NEVER-RAISE cell, because this one relays on driver
torque SIGN specifically, which reverses on every micro-correction at the wheel — the exact input this
kit's ratchet/grind investigations have shown is richest in sign reversals.

**Zero is the safe, shipped value.** Verified 0 on stock `code.bin` and on the flown V90 image
(`_v90_V89BASE-PROBE.6B26.6BF6.6AE2.6C00-427.6B26_plain_image.bin`), and confirmed untouched by every
build script (`grep 716c\|C616C analysis-2020accord/build_v*_tva.py` → 0 hits).

Supporting the "deliberately disabled" reading (BELIEF — statics cannot distinguish deliberate from
accidental): a SECOND, independent part of the same cascade is also dead in this calibration —
`tp+0x70c4` (stage-1 gain on the rate difference, K_D1) and `tp+0x70bc` (stage-1 derivative gain, K_D3)
are both exactly `0.0`, read directly from the image. Two unrelated zeroed gains inside one elaborate,
fully-built filter is more consistent with an intentionally-shipped-disabled feature than with an
accident, but this is a plausibility argument, not a traced fact.

### The would-be sign (lane 2, if reconnected) — CANNOT ESTABLISH the absolute physical sign

Downstream of the (dead) `gp-0x6b76`, the known chain is unambiguous and was re-verified this session:
mode-5 pass-through in `FUN_00026c80` has no negation (`gp-0x6298[2] = +gp-0x62e0[2]`), `gp-0x6b4a`'s
S_flag1 sum is a straight unweighted add, term 0 in `FUN_00037fe6` negates it
(`iVar4 ∋ -gp-0x6b4a`), and `error = gp-0x4f60 - gp-0x6ad6` re-negates (`gp-0x6ad6 ∝ +iVar4·speedLERP`,
so `-gp-0x6ad6 ∝ -iVar4 ∝ +gp-0x6b4a`), then PID (Kp/Ki/Kd all positive) and the aggregator (`mov`,
`add`×8, no negation) preserve sign. **Net: assist_command ∝ +[lane 2's value]**, i.e. whatever sign
lane 2's own filter output carries reaches the motor unchanged — the two negations (term 0, then
`error`'s subtraction) cancel exactly, matching the general "term 0 is reinforcing" finding.

Lane 2's own dominant term (K_D2=14, a **memoryless multiply — zero phase shift at any frequency**,
since `K_D1=K_D3=0` kill the only two terms in stage 1 that would have introduced delay) is
`+14 × (gp-0x6be0 - gp-0x6bf0) × 0.0078125`. `gp-0x6bf0` traces to the motor resolver
(`FUN_00065eda` → `FUN_0003bd7c`) scaled by `gp-0x6abe` and `sign(gp-0x6752)`.

**What I can and can't establish:**
- EVIDENCE: the relative/structural sign chain above (every hop traced this session, several at
  byte level).
- EVIDENCE: the dominant path has ~0° phase shift at 7.79 Hz (a pure gain, no filter state in the live
  gains).
- **CANNOT ESTABLISH the absolute sign (damping vs. anti-damping) from statics alone.** That requires
  knowing whether the resolver's ADC-channel/sin-cos assignment convention (ungained "positive" reading
  direction, set in `FUN_00065eda`) agrees or disagrees with the motor/FOC output's own phase-to-torque
  sign convention (set deep in the FOC chain, not traced this session) — a cross-domain sign comparison
  I have not made and consider out of reasonable scope without either a full FOC-phase trace or an
  on-car correlation.
- BELIEF only: `FUN_00033d10` has the complete architecture of a purpose-built rate-feedback damper
  (P/I gains, symmetric clamps, enable gating on driver-torque presence) — the same shape as this kit's
  other confirmed dissipative lanes (e.g. the friction lane at `gp-0x6b26`). Typical engineering intent
  for this class of structure is damping, not anti-damping, but this is pattern-matching to intent, not
  a traced sign.
- **Moot regardless**: the lane is dead as wired (see above), so this sign has no bearing on current
  on-car behavior either way.

### Testing "the LKAS overlay enters at unity, unlike driver torque" — PARTIALLY CONFIRMED, PARTIALLY REFUTED

Checked the specific claim `gp-0x6b4e ≡ gp-0x6afe`, `0xC63A8 = 1024`. **`FUN_00042ac6`, called from the
tail of `FUN_00026c80` with the same value stored to `gp-0x6b4e`, does `gp-0x6afe = param_1` with only a
sentinel/fault check in between — no scaling. `gp-0x6b4e ≡ gp-0x6afe` CONFIRMED (EVIDENCE).**

But `gp-0x6afe` (i.e. `gp-0x6b4e`) is consumed inside **`FUN_00038148`** — which turns out to be the
producer of **`gp-0x6b70`, term 7 of the ORIGINAL claim under test at the top of this document** — as
lane 1 of a **six-lane weighted sum**. Read all six weights from the image (`tp+0x73a0`..`0x73aa` =
`0xC63A0`..`0xC63AA`):

| lane | source | gate window | weight cal | weight value |
|---|---|---|---|---|
| 1 | `gp-0x6bd0` | ±2048 | `0xC63A0` | 1024 (unity) |
| 2 | `gp-0x6bbe` | ±2048 | `0xC63A2` | 1024 (unity) |
| 3 | `gp-0x6b46` | ±1024 | `0xC63A4` | 1024 (unity) |
| 4 | `gp-0x6b26` (friction) | ±1024 | `0xC63A6` | **1024 (unity)** |
| 5 | `gp-0x6b4e`/`gp-0x6afe` (LKAS overlay) | ±10240 | `0xC63A8` | **1024 (unity)** |
| 6 | `gp-0x6b4c` | ±10240 | `0xC63AA` | 1024 (unity) |

**`0xC63A8 = 1024` CONFIRMED (EVIDENCE) — but so is every other lane's weight.** All six lanes enter
this particular sum at identical unity weight; there is no differential weighting that singles out the
LKAS-mirror lane versus the friction/driver-adjacent lanes **at this stage**. The asymmetry that does
exist is in **gate window width**: the LKAS-mirror lane (and `gp-0x6b4c`) get a ±10240 window, 10× wider
than the friction lane's ±1024 — so the LKAS-descended lane can swing proportionally further before
being clipped, even though its per-unit weight is the same. Whether that constitutes "entering more
directly" is a matter of interpretation, not a clean weight asymmetry as originally framed. The whole
six-lane sum is then passed through a shared EMA (`0xC63AC` ≈ 0.0996, matching this kit's prior
`c63ac_second_phase_lag_lever` finding) and a final clamp to **`±cal[tp+0x7200]` = `±cal[0xC6200]`
= ±8192** — which independently confirms, at the exact cal address, the original claim's supporting
detail from the top of this document ("term 7 is capped at ±8192 by `0xC6200`") that I had flagged as
not independently re-verified. It is now CONFIRMED (EVIDENCE).

### OPEN — with lane 2 inert, what actually makes `gp-0x6b4a` non-zero?

Recorded here as an open question, not answered by assertion. Nine of the ten active lanes into
`gp-0x6298[i]`/`gp-0x6274[i]` were found writing literal constant `0` in the code path examined (see
item 2 above for the one lane, #8, not yet fully closed), and lane 2 is now known to be structurally
inert (`gp-0x6b76` always 0/sentinel). `gp-0x6b4a`'s two other named contributors —
**the rate-limited `Σ gp-0x625c[i]`** (same nine-of-ten-dead pattern applies, since `gp-0x625c[i]`
draws from the same per-lane `gp-0x6274[i]` array as the S_flag1 sum's `gp-0x6298[i]`) and **the
`gp-0x6a62`-indexed LERP term** (identity and dynamics not characterized this session) — have not been
traced to confirm which, if either, is what actually drives `gp-0x6b4a` off zero in practice. Whether
`gp-0x6b4a` is itself live, and via which path, is unresolved. This does not block anything currently in
flight — per the operator's team, the live mechanism under active investigation is the D-term in
`FUN_0003a382`'s PID, a different function independent of everything traced in this document.
