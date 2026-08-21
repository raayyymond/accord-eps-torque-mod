# TRACE 2026-08-21 (correction pass) — the governor's real limit chain, `gp-0x4f64`, and `0xC6202`

**Status: analysis only. Nothing built, flashed, or sent on CAN/UDS to produce this document.**
Subagent trace, GhidraMCP against `code.bin` (stock, analysed — confirmed via `list_open_programs`,
the only program open this session). This corrects `docs/TRACE-2026-08-21-lkas-gain-ceiling-to-16x.md`
§2 row 9/10, whose "governor flat ceiling = cal `0xC6202`" claim is **withdrawn** — its own cited
instruction (`ld.hu -0x4f64,gp,r8`) reads a **RAM cell**, not the cal.

**Evidence legend:** **[EVIDENCE]** = read or computed this session (Ghidra tool call, or exact
arithmetic on a value read this session). **[prior EVIDENCE]** = established in an earlier kit session,
cited not re-derived by me. **[BELIEF]** = inference, flagged as such.

---

## 0. HEADLINE

**The governor's bound on the merged (LKAS+base-assist) command is NOT a flat 4762. It is
`(gp-0x4f64 × channel5) >> 15`, where `gp-0x4f64` is a RAM cell continuously recomputed from a
motor-electrical-rate-scheduled ROM table that ranges from 512 (fast motor rate) to 5325 (slow/at
rest) — an ~10.4× swing — and `channel5` is a second, not-fully-resolved runtime factor internal to
the governor itself.** `0xC6202` (4762) is real, is read exactly once program-wide, but it is consumed
**upstream, inside the table's own producer function**, as an input to a float computation — not as a
parallel `MIN()` ceiling the governor applies directly. Treating "4762" as the governor's ceiling
significantly **understates** how much the ceiling can vary, and **at high motor electrical rate the
real ceiling (512) is already below where a 6× build's steady output (2673) sits today** — a materially
different, more urgent picture than "10.7× headroom before anything binds."

**Is there a raisable limit? Yes, one with an already-flown-safe precedent: flattening the bank-A ROM
table that produces `gp-0x4f64` (V41's CHANGE 2, cal-only, flew clean on V41) removes the motor-rate
throttling and holds the ceiling at a uniform 5325 regardless of how fast the motor is turning.** This
does not reach 16×'s full-scale 7128, but it is the single highest-confidence, lowest-risk lever on this
chain — see §4.

---

## 1. `FUN_0004503c` — the full limit chain, address by address

Confirmed function body `0004503c`–`00045607` (`get_function_by_address`). Called with the aggregator
sum as its effective input (per `docs/BUILD-LINEAGE.md`'s golden chain: `gp-0x6b94 → FUN_0004503c
(governor) → gp-0x6ace`).

**Stage A — bound computation + primary clamp**
```
0x453d6  ld.bu -0x1388[gp],r15      ; one-shot init flag
0x453de  cmp   r0,r15
0x453e0  ld.h  -0x6b94[gp],r6       ; r6 = aggregator sum (raw, signed)
0x453e4  bne   0x453f0              ; skip one-shot init if already done
0x453e6  st.h  r6,-0x138a[gp]       ; init: persisted STATE = aggregator sum
0x453ea  mov   0x1,r13
0x453ec  st.b  r13,-0x1388[gp]
0x453f0  ld.hu -0x4f64[gp],r8       ; r8 = gp-0x4f64  <-- RAM, NOT cal 0xC6202
0x453f4  mul   r26,r8,r0            ; r8 = r26(channel5) * r8, 32x32->32
0x453f8  sar   0xf,r8               ; r8 >>= 15 (Q15)  => BOUND magnitude
0x453fa  mov   r8,r7
0x453fc  subr  r0,r7                ; r7 = -r8
0x453fe  jarl  0x00049a90,lp        ; r10 = clamp(x=r6, lo=r7=-BOUND, hi=r8=+BOUND)
```
`FUN_00049a90` decompiled this session — confirmed 3-argument signed clamp (overflow-safe
comparisons, `clamp(param_1, param_2, param_3)`). **[EVIDENCE]**

**Stage B — target and step**
```
0x45402  mul   r28,r10,r0           ; r10 = clamped_value * r28(channel1)
0x4540a  sar   0xf,r10              ; TARGET = r10 >> 15
0x45406  ld.bu -0x67f5[gp],r11      ; direction/hard-turn flag
0x45410  ld.hu 0x7206[tp],r16       ; cal 0xC6206 = 512  (if gp-0x67f5==0)
0x45416  ld.hu 0x7208[tp],r16       ; cal 0xC6208 = 205  (else)
0x4541a  mul   r23,r16,r0           ; r16 = r16 * r23(channel-F, last schedule)
0x4541e  sar   0xf,r16              ; STEP = r16 >> 15
```
`0xC6206`/`0xC6208` confirmed **[EVIDENCE, read_memory this session]** = 512 / 205 exactly, matching
every build script since V38. **[prior EVIDENCE]** never touched by any flown build; V40's attempt to
set both to `0xFFFF` is implicated in that build's ignition-disable brick (`memory/v40-governor-slew-
root-cause.md`).

**Stage C — rate-limited slew of persisted STATE toward TARGET**
```
0x45420–0x45436  sign-mismatch snap-to-zero: if sign(STATE) != sign(TARGET), STATE := 0
0x4543a–0x4545a  STATE moves toward TARGET by STEP, never overshooting;
                 snaps to TARGET outright if already within one STEP
```
Output written to persisted `gp-0x138a` **and** lockstep-published to `gp-0x6ace`/`gp-0x4cca` (matches
the golden chain's `gp-0x6ace` governor-output node exactly).

**Stage D — state-4 governor lockout** (`0x454f8`–`0x455c4`): `gp-0x67fa==4` forbids a magnitude
*increase* over the previous cycle's output. **[prior EVIDENCE]** = V42's fix, `docs/BUILD-LINEAGE.md`
now records state 4 as **measured 0/123,277 occurrences while driving** — structurally present, not
observed to bind. Not re-derived this session; cited only.

**Stage E** (`0x455c4`–end): STATE persisted; `channel1` (r28) and `channel5` (r26) lockstep-published to
`gp-0x6934`/`gp-0x4c54` and `gp-0x6946`/`gp-0x4c56` for the next cycle.

**`channel1` (r28) and `channel5` (r26) — NOT `0xC520C`.** Both are runtime-tracked schedule values
**internal to `FUN_0004503c`** (sourced from `gp-0x652c..gp-0x6544`, a 7-point array, and
`gp-0x6938`/`gp-0x694c`, a tracked/target pair respectively), each independently rate-limited and
optionally corrected against a wraparound constant `tp+0x7492` (`0xC6492`) when `gp-0x6a64 ≥
tp+0x7316` (`0xC6316`, the ~10 km/h threshold from `memory/accord-fun45608-authority-slots-not-
motoroff.md`). **[EVIDENCE, this session's register-level trace]** `FUN_00049a78` — the helper both
channels are built from — decompiles cleanly to `min(a,b)` (confirmed this session), so in the
**non-wraparound** branch both channels are provably bounded to ≤32768 (i.e., ≤1.0 as a Q15 fraction).
**[BELIEF]** In the wraparound-correction branch the result is only masked to 16 bits (`& 0xffff`), so a
value >32768 is not structurally excluded there — **not resolved this session.**

**🛑 Correction to the withdrawn trace's own table:** its row 10 ("governor adaptive rate cap … table
`0xC520C`") attaches the bank-A table citation to **this** `channel1` multiply (`0x453fa`-area) — but
`channel1`'s actual ROM source (`gp-0x652c`/`gp-0x6544`, 7 points) has a different point-count and a
different address family than bank A's 5-point `0xC520C` record. **The two are very likely different
tables; row 10's attribution is [BELIEF, likely wrong], not re-confirmed.** Bank A's real, single
consumer is `gp-0x4f64` (§2) — a RAM cell loaded at `0x453f0`, not recomputed in this function at all.

---

## 2. `gp-0x4f64` — identity, provenance, and the 17-candidate adjudication

**Writer: `FUN_0007b022` (`0007b022`–`0007c4f1`, ~5.3 KB), exactly 3 sites**, one per internal mode
branch, all following the identical pattern:
```
ld.hu -0x4f64,gp,rX      ; read current
ld.hu -0x448a,gp,rY      ; read shadow
cmp   rY,rX
bne   +6                 ; mismatch -> skip both writes, fall to FUN_0006b9ee(fault 0x17)
st.h  rZ,-0x4f64,gp      ; write fresh value to BOTH cells
st.h  rZ,-0x448a,gp
```
Confirmed at **`0x7C2D2`(read)/`0x7C2E2`(write)**, **`0x7C3A8`(read)/`0x7C3B4`+`0x7C3B8`(write pair)**,
**`0x7C470`(read)/`0x7C47C`+`0x7C480`(write pair)** — `disassemble_bytes`, all 3 branches. **[EVIDENCE]**

**Shadow mechanism, personally re-verified this session (not just cited):**
```
FUN_0006b9ee(x) -> gp-0x4d6c = x; FUN_0006ce7c(0x17)     [decompiled this session]
FUN_0006ce7c(p) -> gp-0x444f = gp-0x4e53 = (p==0 ? -1 : p)   [decompiled this session]
```
This confirms **[EVIDENCE]**: a mismatch between `gp-0x4f64` and `gp-0x448a` sets fault-code cells to
`0x17`. It is a **stored-duplicate consistency check** — both cells receive the *same freshly computed*
value every cycle (from the *same* table read), so it trips on **RAM divergence between cycles**
(bit-flip / corruption), **never on the calibration value itself.** A cal-only edit to bank A that keeps
`0xC520C` and its mirror `0xC5224` byte-identical to each other **cannot trip this check** — confirmed
structurally (both writes derive from one shared computation) and consistent with V41's on-car result
(flew clean with bank A fully flattened). I did **not** trace `FUN_0006ce7c`'s fault-code-to-action
dispatcher (what "0x17" does downstream, e.g. which DTC, whether it's debounced) — that remains
**[prior EVIDENCE only]**, cited from `memory/v40-governor-slew-root-cause.md`("HARD-FAULT-ELIGIBLE,
motor off + power cycle"), not re-derived.

**The other 5 real readers**, function-identified this session:

| addr | function | role (from decompile/disasm) |
|---|---|---|
| `0x453F0` | `FUN_0004503c` (governor) | **primary** — the bound on the merged command (§1) |
| `0x43AE4` | `FUN_00042af8` (`0x42af8`–`0x43e43`) | inside a signed-saturate block alongside `gp-0x6afe`; role not fully resolved — see §5 open items |
| `0x4486E` | `FUN_00043e44` (`0x43e44`–`0x44a8b`) | converts to float, scales, clamps to ±10.0 against another float (`gp-0x6dac`); reads a byte at `tp+0x74c9`; looks like a **plausibility/consistency check**, not the delivery path |
| `0x6E0F2` | `FUN_0006e09a` (small, `0x6e09a`–`0x6e13f`) | **self-test/startup sequencer** — `gp-0x6b98 = gp-0x4f64 × cal(tp+0x7c3c)` inside a timed state-machine step (`param_1` dispatch), gated by an elapsed-tick check against `cal(tp+0x7c22)` |
| `0x6E1CA` | `FUN_0006e140` (`0x6e140`–`0x6e225`) | twin of the above, next sequencer step |

Both decompiled in full this session. `FUN_0006e09a`/`FUN_0006e140` write **`gp-0x6b98` directly** (the
FOC motor command) using `gp-0x4f64` as a multiplicative scale during what reads as a power-up/mode-
entry self-test kick (state counters `gp-0x2902`/`gp-0x2904`/`gp-0x2908`, calls to small enable/disable
helpers) — **[BELIEF]** this is not the live-driving LKAS path; it plausibly reuses the same "how much
authority is currently considered safe" cell to size a startup actuator check. Not fully confirmed.

**6 of the original 17 candidates are FALSE POSITIVES**, adjudicated with `disassemble_bytes` this
session — recorded here because they are exactly the traps the kit's skill file warns about:
- `0x4A3D4`: `mov 0xbb09c,r7` — a **32-bit literal** that happens to contain byte pattern `9c b0` (the
  LE encoding of displacement `-0x4f64`) as a coincidental substring. Base register: none — not a
  memory access at all.
- `0x80492`: `jarl 0x0005b52e,lp` — same coincidental-substring trap, inside the branch-target encoding.
- `0xBCDFE`, `0xBE13E`: `st.b r7,-0x4f64,r18` — **base register is r18, not gp.** Real instructions,
  wrong cell; part of a 4-offset write loop (`-0x6a8d,-0x4f64,-0x345b,-0x1972` from r18) unrelated to
  the governor. Exactly the base-register-aliasing trap this kit's memory already documents.
- `0xC7346`: no matching instruction in the vicinity at all (saturate-arithmetic opcodes, no memory op).
- `0xC782E`: `disassemble_bytes` returned **zero instructions** — not code / not executable memory.

**Net count: 3 writers (one function, 3 mode branches), 5 real readers (one primary + 4 diagnostic/
self-test), 6 false positives out of 17 raw candidates (35%).** This is worth keeping as a standing
example of why every raw-scan hit must be individually adjudicated before it is used to bound a count.

---

## 3. `0xC6202`'s real role — corrected

**[EVIDENCE, `search_instructions` program-wide, 183,569 instructions scanned, `truncated:false`]**
`0xC6202` (tp+0x7202) has **exactly one reader anywhere in the program**: `0x7b06a`, `ld.hu
0x7202,tp,r15`, **inside `FUN_0007b022`** — the `gp-0x4f64` writer itself, not `FUN_0004503c`.
Confirmed a second way: raw LE byte scan of `code.bin` for both the `disp|1` and exact-displacement
encodings (98 raw candidate offsets across the image), narrowed by Ghidra's own instruction parse to
the single real hit — the two methods agree.

**Register-level trace, `0x7b060`–`0x7b0c8`, this session:**
```
0x7b06a  ld.hu 0x7202,tp,r15         ; r15 = cal(0xC6202) = 4762 (confirmed by read_memory this session)
0x7b08e  movhi 0x3a80,r0,r15         ; r15 := 0x3A800000 = float 0.0009765625 (= 1/1024) — OVERWRITES r15
0x7b092  mulf.s r15,r6,r15           ; r15(float) = (1/1024) * (float)4762 = 4.650390625
0x7b0c2  sst.w r15,0x20,ep           ; stored into a stack parameter-block field
0x7b0c8  st.w  r15,0xcc,gp           ; also stored to a persistent scratch slot
```
The stack field sits **between pointers to bank A's own tables** (`0x7b0a2 movea 0x620c,tp,r11` = X
array of `0xC520C`; `0x7b0ea movea 0x6038,tp,r13` = slope array `0xC5038`) being assembled in the same
struct. **`0xC6202` is consumed as a Q10 SCALE FACTOR (÷1024 → 4.65) feeding into the same float
computation that eventually produces `gp-0x4f64`, not as a parallel `MIN()` ceiling.** I traced ~230
bytes forward from the load without reaching the point where this scale is actually multiplied against
anything else, or a `jarl` that would consume the assembled struct — **the exact arithmetic role (does
it scale the X-axis lookup key? the Y output? a blend weight between the two mirror tables?) is NOT
resolved this session.** `FUN_0007b022` is ~5.3 KB; I examined the first ~300 bytes closely (its
preamble) plus the 3 write sites at the far end. The middle is unexamined.

**So: is `0xC6202` "involved at all"? Yes — but not as the row-9 claim described it, and its effect of
*raising* it is genuinely unknown, not merely risky.** I cannot respons­ibly recommend touching it either
direction without resolving what the scale actually does.

**`0xC6204`, `0xC6206`, `0xC6208` — the ledger's "cluster at `0x045410`–`0x0457de`" claim, checked:**
`search_instructions` for "7204" found exactly 2 raw hits: the real one at **`0x457de`, inside
`FUN_000456a4`** (not `FUN_0004503c`), and a false positive (`0x7202a`, a branch-target address that
textually contains "7204"). `0xC6206`/`0xC6208` ARE genuinely inside `FUN_0004503c` (`0x45410`/
`0x45416`, confirmed). **So the range `0x045410`–`0x0457de` is real but spans TWO functions
(`FUN_0004503c` then `FUN_000456a4`), and `0xC6202` is not in it at all** — it is far away, in
`FUN_0007b022` (§3 above). This is the precise error behind the withdrawn claim.

**`FUN_000456a4` ("comp-add", `0x456a4`–`0x45959`) — decompiled in full this session.** It reads
`gp-0x6a10` (absolute steering angle — matches `docs/BUILD-LINEAGE.md`'s established identity) as a
lookup key into a small 3-point LERP over `tp+0x7834..0x783c`, producing an angle-scheduled threshold.
**If `gp-0x6ac0` (motor electrical rate) exceeds that threshold**, it computes:
```
compensation_magnitude = MIN( (gp-0x6ac0 − angle_threshold) × cal(0xC6204) >> 10,
                               angle_scheduled_ceiling_table )
```
`cal(0xC6204)` **[EVIDENCE, `read_memory` this session]** = **3072** stock (3072/1024 = 3.0 exactly — a
clean Q10 gain of 3.0×). The ceiling table (`0xC67D2`–`0xC67DC`, **[EVIDENCE, read_memory this
session]**: count 3, angle-X = [3200,3800,4150], ceiling-Y = [512,1024,2560]) exactly matches the
"compensation ceiling 2560" figure the withdrawn trace's §2 row 12 already cited from V40's era —
**cross-confirms the general mechanism, corrects its exact gain-cal identity (`0xC6204`, not
previously named).**
The result is **negated** (sign of `gp-0x6abe`, which `docs/BUILD-LINEAGE.md`/V39's own trace
established sits at a fixed +32767 in all normal driving) and **added** to the governor's own output:
`gp-0x6acc = gp-0x6ace + compensation` (compensation ≤0 in normal driving). **This is a subtractive,
angle-and-rate-gated anti-windup/consistency term, not a ceiling on the governor itself.** Lowering
`0xC6204` would weaken it (let more of the governor's raw output through when motor rate exceeds the
angle-implied expectation); I did not determine what this term is protecting against, so I am not
recommending it — flagged only as an identified, uncharacterized lever.

---

## 4. Ranked headroom list

| rank | lever | cal or runtime | stock (LE) | raisable? | other readers | fault cost if pushed too far |
|---|---|---|---|---|---|---|
| 1 | **Flatten bank A** (`0xC520C`+mirror `0xC5224`: Y→5325 flat, slopes `0xC5030`/`0xC5038` and mirror `0xC5030`/`0xC5038`→0) | cal, 2×24B records + 2×8B slopes | X=(1050,1700,2500,3700,4100), Y=(5325,3584,2406,1587,512), slopes=(−21940,−12059,−5593,−22021) — **[EVIDENCE, read_memory this session, exact match to V38–41's cited values]** | **YES — already flown safe as V41's CHANGE 2** [prior EVIDENCE: V41 booted and drove cleanly] | `gp-0x4f64` has 4 other readers (§2) — 2 look like a startup self-test that would receive a larger kick amplitude; role of the other 2 unresolved | none observed on V41; shadow check (§2) structurally cannot trip on a bank-A-only edit since both mirror copies stay identical |
| 2 | `0xC6206`/`0xC6208` (governor slew step) | cal | 512/205 | **NO — do not.** V40 raised both to `0xFFFF` and the car came up with EPS lamp, no power steering | single reader each, confirmed | ignition-disable class fault, `memory/v40-governor-slew-root-cause.md` |
| 3 | `0xC6204` (comp-add subtractive gain) | cal | 3072 (=3.0×) | **untested, not recommended** — role as a safety/consistency term not characterized | single reader (`FUN_000456a4`) | unknown — this term's purpose (what it's protecting against) is not established |
| 4 | `0xC6202` (feeds `gp-0x4f64`'s producer) | cal | 4762 | **do not — effect unknown**, not merely risky | single reader (`FUN_0007b022`), consumed mid-function, arithmetic role unresolved | unknown |
| 5 | `channel1`/`channel5` (internal governor schedules) | RAM, no direct cal identified | n/a | **not a lever** — no calibration address found; sourced from an unidentified 7-point table | n/a | n/a |

**Stability wall, restated per the brief's framing:** none of the above changes the measured
`|κG| = 0.63–0.75` loop-margin picture or the `Re(Z) = −3761` finding — those apply upstream of and
independently of the governor. Rank-1 (flatten bank A) removes a **clamp-style** restriction; it says
nothing about whether the loop is stable at whatever gain reaches that clamp. **Do not read this ranked
list as clearance to raise gain — it only answers "which clamp can move," not "should the loop take the
result."**

---

## 5. The `gain÷2` full-scale relation — re-confirmed

**[EVIDENCE, re-derived from the withdrawn trace's own §2 row 4/§7, arithmetic checked this session]**
This is a *different, earlier* stage than the governor — `FUN_00028ea6`'s Q15 gain multiply:
`fs_output = (setpoint_fullscale × gain_cal) >> 15`. Setpoint full-scale for this car's record is 16384
(`0xE51A8`, prior evidence, not re-read this session). `16384/32768 = 0.5` **exactly**, so
`fs_output = gain_cal × 0.5 = gain_cal ÷ 2`, with no rounding error for any integer `gain_cal` (16384 is
a power of two). This is **full-scale of the arb-stage output** — i.e., the value handed toward the
aggregator/mixer, **before** the governor (§1) or comp-add (§3) touch it. It is not "post-governor" and
was never claimed to be; the withdrawn trace's error was in what it compared this number *against*
(a flat 4762 instead of the true 512–5325 range), not in this arithmetic itself.

---

## 6. What a 16× command actually receives — corrected

At `gain_cal = 14256` (16×), arb-stage full-scale = 7128 (§5, unchanged by this correction).

**This value is NEVER delivered unclipped**, because `gp-0x4f64`'s own ceiling never exceeds 5325 at any
motor rate (§1/§2) — even in the best case (motor at rest, `gp-0x4f64 = 5325`), 7128 exceeds it by
33.8%. **How much of it clips depends on motor electrical rate at that instant, not on command
magnitude**:
- **motor rate ≤1050** (slow/controlled steering): ceiling ≈5325 → a 7128 command clips **33.8%**.
- **motor rate ≥4100** (fast steering — exactly the maneuvers more torque is wanted for): ceiling ≈512
  → the SAME 7128 command clips **92.8%**, to essentially the table's floor.
- Between those, the ceiling interpolates linearly per the table's own negative Q13 slopes.

**This is qualitatively different from the withdrawn claim's "flat 4762, top 33% of range clipped."**
There is no single clip fraction — it is motor-rate-dependent and, at high rate, far more severe than
33%. **[BELIEF, not measured]**: if real driving routinely produces high motor electrical rate during
exactly the fast corrections the operator cares about, **the governor may already be the dominant
limiter at rates well below 16×, possibly below the car's current 6×** — this is a natural, high-value
target for the next build's live telemetry (a raw tap on `gp-0x6ac0` and/or `gp-0x4f64` alongside the
existing angle/torque/LKAS-demand instruments), not something resolvable by further static tracing.

After the ceiling, the (possibly heavily clipped) value is further scaled by `channel1` (§1, ≤1.0 in the
common case) to form TARGET, then the persisted STATE **slews toward TARGET at a bounded per-cycle
STEP** (§1 Stage C) — so even a command that WOULD fit under the ceiling does not arrive instantly; it
ramps in at the `0xC6206`/`0xC6208` rate. Then comp-add (§3) can subtract further when motor rate
exceeds an angle-implied expectation.

---

## 7. What I could not resolve, and the exact next step

1. **`channel1`/`channel5`'s ROM source and exact range.** Both are runtime-tracked inside
   `FUN_0004503c` from `gp-0x652c/gp-0x6544` (7 points) and `gp-0x6938/gp-0x694c` respectively; neither
   traced to a cal table this session. *Next step:* `get_xrefs_to` on `gp-0x652c`/`gp-0x6938`
   (correcting for the gp-relative absolute-address arithmetic — I made and caught one such error this
   session) to find their writer function(s), then decompile.
2. **`0xC6202`'s exact arithmetic role inside `FUN_0007b022`.** Confirmed as a Q10 scale (÷1024→4.65)
   feeding a float computation; not traced to its consuming operation. *Next step:* disassemble
   `0x7b0c8`–`0x7b658` (the middle ~1.4 KB of the function, up to the clamp-at-table-ends logic V41's
   own notes cite at `0x7b658`) to find where `gp+0xcc` (the stored scale) is next read.
3. **`gp-0x4f64`'s two unresolved extra readers**, `0x43AE4` (`FUN_00042af8`) and `0x4486E`
   (`FUN_00043e44`) — both look diagnostic/plausibility-check in nature but not confirmed. *Next step:*
   full decompile of both functions (both are large; targeted disassembly windows only were used this
   session).
4. **`FUN_0006ce7c`'s fault-code dispatcher** — confirmed it writes fault-code cells `gp-0x444f`/
   `gp-0x4e53`, did not trace what reads them or what action follows. *Next step:* `get_xrefs_to` on
   `gp-0x444f`.
5. **Whether real driving reaches high motor electrical rate (`gp-0x6ac0`) during the maneuvers the
   operator cares about** — this is the load-bearing empirical question raised by §6 and is not
   resolvable statically. *Next step:* live telemetry tap on `gp-0x6ac0` and `gp-0x4f64` on the next
   build.

---

## Sources

This session: `FUN_0004503c`, `FUN_0007b022`, `FUN_000456a4`, `FUN_0006e09a`, `FUN_0006e140`,
`FUN_00049a78`, `FUN_00049a90`, `FUN_0006b9ee`, `FUN_0006b9fa`, `FUN_0006ce7c` (all decompiled in full
or in targeted disassembly windows this session); `read_memory` on `0xC6200`–`0xC620F`, `0xC520C`–
`0xC5223`, `0xC5030`–`0xC5037`, `0xC67D0`–`0xC67DF`; `search_instructions` program-wide for "7202" and
"7204" (183,569 instructions scanned, `truncated:false`); raw Python LE byte scans of `code.bin` for
both encodings of `0xC6202`/`0xC6204`. Prior: `analysis-2020accord/build_v39_tva.py`,
`build_v40_tva.py`, `build_v41_tva.py`, `build_v42_tva.py` (headers); `memory/v40-governor-slew-root-
cause.md`; `docs/BUILD-LINEAGE.md` (the `0xC6200`/governor-cluster note this trace corrects, and the
`gp-0x6acc` bridge / state-4 sections); `docs/TRACE-2026-08-21-lkas-gain-ceiling-to-16x.md` (the trace
this document corrects).
