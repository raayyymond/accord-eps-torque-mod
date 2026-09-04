# r24 derivative `dt`, Q-format, and gain-arm census — traced on the flown V283 image

Subagent `r24trace`, 2026-09-03, reporting to `team-lead`/`main`. Entry point: `gp-0x4f62` (the torque-rate
input to r24/r26) and `FUN_0003aa2c` (the aggregator computing r24). Goal: decide between the three
candidate explanations for r24's measured 0.30–0.52× (best estimate 0.37–0.43×) magnitude gap
(`V282-R24-TAP-READ-r36-r38-2026-09-03.md` §3.2) — derivative `dt`, Q-format, or gain-arm selection.

## Image traced [EVIDENCE]

`C:\Users\dudei\Desktop\Projects\accord-firmwares\analysis-2020accord\_v283_V283-V282BASE-KI50.KP.FLAT.Y0-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin`,
sha256 `fd0c321a…`, 1,048,576 bytes — confirmed by direct Python hash of the file on disk. No Ghidra
project existed for V283 specifically; the V282 project (`_v282_V282-V281R3BASE-…_plain_image.bin`,
already imported, 1682 functions after `reanalyze`) was used as the Ghidra vehicle, justified because
`V282-R24-TAP-READ-r36-r38-2026-09-03.md` §1 already full-image-diffed V282→V283 to **exactly 5 bytes**
(`0xC63E6` Ki 0→50, plus its CRC at `0xC6FFC`), nowhere near any address this trace touches. Every claim
below that depends on exact bytes was **additionally corroborated by a raw Python read of the actual
V283 file** (cal values, the `0x3AA94` repoint byte, and the gp-0x671d/gp-0x683c/gp-0x6806 census) — not
relayed from V282 alone. `gp = 0xFEDF8000`, `tp = 0xBF000`.

---

## Verdict, in priority order

1. **The derivative `dt` hypothesis is the one that survives, and it is now STRUCTURALLY supported, not
   just arithmetically plausible** — `gp-0x4e7e` (the "elapsed ticks" accumulator inside `gp-0x4f62`'s
   producer) is fed by a **DMA-received rolling counter out of the torque-sensor's own serial link**, not
   a CPU-tick counter. Its increment rate is set by the **sensor's own message cadence**, decoupled from
   the CPU's 1 kHz task rate. This is exactly the class of mechanism that reproduces both the magnitude
   gap and the small phase residual the tap measured. **I could not pin the exact ratio** (needs a DMA
   trigger-source register value or the physical sensor's datasheet rate, both outside this kit's SVD) —
   flagged as the explicit remaining gap, not asserted.
2. **The Q-format hypothesis is REFUTED, at instruction level.** The whole chain from the multiply through
   the deadband to the ±0x2000 clamp is bit-for-bit what the closed form already assumed — no missing or
   extra shift anywhere.
3. **The gain-arm hypothesis is REFUTED as census, on this exact image.** `gp-0x671d` has the same 16
   access sites, same 2 writers, as every prior build. `gp-0x683c` is confirmed to have **zero** readers
   or writers on V283 — the `0x3AA94` instruction was repointed to `gp-0x6806` (STEER_CONTROL_ACTIVE) at
   V104 and stays repointed. No LERP substitution, no alternate arm path, exists.

---

## Part 1 — the derivative `dt`, traced address-exact

### 1.1 `gp-0x4f62`'s producer, `FUN_0007e74a`, full disasm [EVIDENCE, fresh `disassemble_bytes` on V282, cal values cross-read on the real V283 file]

```
0007e74a  ld.bu -0x4e3d[gp],r14      ; r14 = current torque-sensor CHANNEL select (0 or 1)
0007e74e  ld.bu -0x281d[gp],r7       ; r7  = channel value cached from the LAST call
0007e752  cmp   r14,r7
0007e754  be    0007e762             ; channel UNCHANGED since last call -> take the "opposite-channel" branch
   [channel CHANGED:]
0007e756  mov   r14,r7               ; update cached channel
0007e758  st.b  r7,-0x281d[gp]
0007e75c  ld.bu -0x281e[gp],r11      ; r11 = cached "next" value from the LAST time it was computed
0007e760  br    0007e776
   [channel UNCHANGED, @0007e762:]
0007e762  cmp   r0,r7
0007e764  setfe ep                   ; ep = (r7==0) ? 1 : 0
0007e768  add   gp,ep
0007e76a  ld.bu -0x4e9e[ep],r14      ; r14 = table[gp-0x4e9e + (r7==0?1:0)]  -- the OPPOSITE channel's counter
0007e76e  ld.bu -0x281f[gp],r11      ; r11 = cached prior value of THIS SAME lookup
0007e772  st.b  r14,-0x281e[gp]      ; cache it for the "changed" branch to use later
   [merge, @0007e776:]
0007e776..0007e78e   ring-buffer index management (gp-0x2820, 0..7, wraps)
0007e78e  ld.h  -0x4f60[gp],r8       ; r8 = current torque sample gp-0x4f60
0007e792..0007e79c   push r8 into an 8-slot ring buffer at gp-0x2814 + idx*2
0007e79e  movea -0x4e9e,gp,ep
0007e7a2  add   r7,ep
0007e7a4  sld.bu 0x0[ep],r16         ; r16 = table[gp-0x4e9e + r7] = CURRENT channel's rolling counter
0007e7a8  sub   r11,r12              ; r12 = r16 - r11  (delta since last read)
0007e7ac  cmp   r0,r12
0007e7ae  st.b  r16,-0x281f[gp]      ; cache current value for next call
0007e7b2  bge   ...                  ; if delta >= 0, skip
0007e7b4  add   0x4,r12              ; mod-4 wrap correction (table values cycle 0..3)
0007e7b8  ld.h  -0x4e7e[gp],r11      ; r11 = accumulated "ticks" so far
0007e7bc  add   r11,r12              ; accumulate delta
0007e7c0..0007e7ce   wrap at 30000, store back to gp-0x4e7e
0007e7d4  st.h  r12,-0x27f4[r9]      ; push the accumulator value into a PARALLEL "time" ring buffer, same slot
0007e7d8  ld.hu 0x7c42[tp],r16       ; D = cal(0xC6C42) = 4, byte-confirmed on V283
0007e7dc..            gate D<8, else zero
0007e7f6..0007e832    look back D slots into BOTH ring buffers -> torque[n-D], time[n-D]
0007e832  sub   r15,r8               ; Δtorque = torque[n] - torque[n-D]
0007e836  sub   r7,r12               ; Δt(raw) = time[n] - time[n-D]
0007e83a..0007e844    wrap-correct Δt at +30000 if negative
0007e846..0007e852    if Δt<=0, rate=0
0007e84a  shl   0x1,r10              ; Δtorque <<= 1
0007e84c  divq  r12,r10,r0           ; r10 = 2·Δtorque / Δt(raw)     <-- gp-0x4f62, RAW INTEGER DIVIDE
0007e854..0007e872    store to gp-0x4f62 (+ shadow-pair lockstep check, FUN_0006b9ee)
```

**No hidden scale factor anywhere in this arithmetic.** `gp-0x4f62 = 2·Δtorque / Δt(raw)`, where `Δt(raw)`
is measured **entirely in units of the rolling-counter table `gp-0x4e9e[channel]`**, not in CPU
milliseconds. The closed form's `dt = D·(1 ms) = 4 ms` is an assumption about what those units ARE, not
something read off this code — this function itself carries no unit annotation.

### 1.2 `gp-0x4e9e[0]`/`gp-0x4e9e[1]` — NOT a software phase counter, a DMA-fed rolling counter from the torque sensor [EVIDENCE, fresh decompile chain]

`gp-0x4e3d` (the channel selector `FUN_0007e74a` indexes by) has **exactly 2 writer values, 0 and 1**,
both inside `FUN_0007ff08` (a torque-sensor-pair init/DTC state machine gated on `FUN_0005b2be` config
reads) — confirmed by `search_instructions operand_pattern=4e3d`, 12 hits, 3 writers, all `st.b r0/r12`.
So `gp-0x4e3d` is a **redundant-channel A/B select flag**, not a rotating phase index — corrects my own
first-pass reading of the mod-4 arithmetic as a "4-phase counter."

The 2-entry table `gp-0x4e9e[0..1]` (byte array, confirmed via the `setfe ep; add gp,ep; ld.bu -0x4e9e[ep]`
idiom decoding to `gp-0x4e9e + (0 or 1)`) has **zero writers found by any `st.b`/`sst.b` text scan** —
until the array-base blindspot this kit's own memory already flags
([[reference-accord-gate1-movea-gp-array-blindspot-and-scalar-bound]]) is applied: a `movea -0x4e9e,gp,r9`
at `0x8260a` inside `FUN_000825f0` is the base of a REGISTER-INDEXED write invisible to any displacement
text search. Decompiled:

```c
void FUN_000825f0(uint param_1)          // param_1 = channel, 0 or 1
{
  uVar1 = *(byte*)(gp-0x548 + param_1*4);              // per-channel decoded frame-status byte
  if (*(int*)(gp-0x2828 + param_1*4) == 10) {          // per-channel state == "synced"
    if (*(byte*)(gp-0x4e9e + param_1) != (uVar1 & 3))
      *(char*)(gp-0x4e9e + param_1) = (char)(uVar1 & 3);   // <-- THE WRITE: table[channel] = frame's low 2 bits
    ...
  }
  ...
}
```
Sole caller: `FUN_0007df80` (calls `FUN_000825f0(0)` and `FUN_000825f0(1)`, once each), sole caller of
THAT: `FUN_0006bb08` — **the same function that calls `FUN_0007f3f8` (`gp-0x4f62`'s gated call site)**,
both under the confirmed 1 kHz task-1 dispatcher `FUN_0002214a`
([[reference_accord_gp4f62_torque_rate_producer_and_c6c42_window]]).

`uVar1` (`gp-0x548 + channel*4`) is written by `FUN_0007007c` (also called only from `FUN_0006bb08`),
which decodes a **24-byte frame** out of a staging buffer fed by `FUN_0006c23c`/`FUN_0006c14c`. Those
functions compute `available = 0x30 - DAT_ffff7362` — and **`0xFFFF7362` is `DTC1`, the DMA Transfer Count
register for DMAC channel 1**, per the kit's own SVD (`DMAC` peripheral base `0xFFFF7300`, `DTC1` at
offset `0x62`; `0xFFFF736A` = `DTS1`, the channel-1 transfer STATUS register, at offset `0x6A`).

**So the chain is: physical torque sensor → serial link → DMA channel 1 → a 48-byte software mirror →
decoded once per 1 kHz CPU tick into `gp-0x548`, whose low 2 bits are a ROLLING COUNTER embedded in the
sensor's own frame protocol** — and `gp-0x4e9e[channel]` mirrors that counter's CURRENT value each CPU
tick. `FUN_0007e74a`'s `Δt(raw)` is therefore counting **how many of the sensor's OWN frames arrived
since the last time the ring buffer was pushed**, in units of the sensor's native message period — **not
CPU milliseconds**, unless the sensor's message rate happens to equal exactly 1 kHz.

### 1.3 What this means for the dt hypothesis [BELIEF, with the mechanism as EVIDENCE]

If the sensor's own message rate is **faster** than 1 kHz (very plausible for an automotive torque
sensor's raw serial output — DMA-driven receive into a ring buffer is architecturally overkill for an
exactly-1kHz-synchronous link), each CPU tick would typically see the rolling counter having advanced by
**more than 1**, so the SAME nominal "D=4 samples" window (4 pushes into the ring buffer, each push one
CPU tick if `FUN_0007f3f8`'s gate is usually true) would accumulate **more than 4 raw ticks** in
`gp-0x4e7e`, i.e. a **larger denominator than the closed form assumes** — which computes a **smaller**
rate for the same real `Δtorque` and time span. That is exactly the direction and rough shape of the
2.5–2.7× the wire demands (§3.2 of the tap-read study): `dt_effective = dt_nominal / (sensor_rate / 1 kHz)`.

**I could not pin the sensor's actual message rate.** The DMA trigger source for channel 1 (`DTRS1`,
`0xFFFF7340`, a 4-bit trigger-select field) is configured somewhere in boot init, but this kit's SVD does
not enumerate the V850E2Px4's trigger-source table, and a `0x7340` operand search collides with an
unrelated `tp`-relative cal read at `0xC6340` (a fresh instance of the coincidental-text-collision trap
the decompile skill warns about — confirmed and excluded, not chased further). **What would close this**:
either the UPD70F3508 hardware manual's DMA trigger-source enumeration (to identify which UART/CSIH
channel drives DTRS1's configured value), or that peripheral's baud-rate divisor register, read from the
boot init block. Both are outside what I resolved this session.

**What is NOT open**: that this is a real, hardware-driven mechanism decoupling `gp-0x4f62`'s effective
`dt` from the CPU's 1 kHz scheduling period. That is confirmed at the instruction and SFR level, not
inferred.

---

## Part 2 — Q-format of the whole r24 chain, address-exact, mirrored in Python [EVIDENCE]

Full fresh disassembly, `0x3AB90`–`0x3AC5F`, confirmed byte-identical in this region between V282 and
V283 (outside the study's 5-byte diff window).

```
0003ab98  ld.bu -0x671d[gp],r6        ; gate: r6 = gp-0x671d
0003ab9c..0003abf8   mode-indexed LERP over the motor-rate index (gp-0x6ac0) -> r10, "curve-A" default
                      (memoryless: rebuilt from tables gp-0x6e28..gp-0x6e40 every call, no state)
0003abfa  cmp r0,r6
0003abfc  be 0003ac04
0003abfe  ld.hu 0x7442[tp],r10        ; r6!=0  -> cal 0xC6442 = 1024  (tp+0x7442, FAULT arm)
0003ac04  cmp r0,lp                   ; lp carries bVar4 = (gp-0x6806==0) from earlier in the function
0003ac06  be 0003ac0e
0003ac08  ld.hu 0x7446[tp],r10        ; r6==0 && gp-0x6806!=0 -> cal 0xC6446 = 5244 (ENGAGED arm, the flown one)
0003ac0e  cmp r0,r2
0003ac10  be 0003ac16
0003ac12  ld.hu 0x7440[tp],r10        ; r6==0 && gp-0x6806==0 && r2!=0 -> cal 0xC6440 = 2048 (stock arm)
0003ac16  mov r1,r8                   ; r8 = r1 = clamp(gp-0x4f62, +-0x1400)   [clamp done earlier, 0x3aa9c-0x3aac0]
0003ac18  mul r10,r8,r0               ; r8 = r8 * r10   (clamped_dtorque * gain_arm_Q10), low 32 bits
0003ac1c  ld.hu 0x71f6[tp],r12        ; cal 0xC61F6 = 3, DEADBAND
0003ac20  sar 0xa,r8                  ; r8 >>= 10 (ARITHMETIC shift)         -> "scaled"
0003ac22..0003ac3c   soft deadband: y = 0 if |scaled|<=3 else scaled - sign(scaled)*3
0003ac3e  mul r14,r6,r0               ; r6 = y * gp-0x6752   (polarity, confirmed -1 elsewhere in this kit)
0003ac42..0003ac58   clamp r6 to [-0x2000, 0x2000]           -> r24 final
   (function tail) st.h r24,-0x6ada[gp]     ; the exact cell V282's cave taps as |r24|
```

Python mirror, integer arithmetic exactly as coded (no float anywhere in this chain):

```python
def r24(dtorque_raw, gain_arm_q10, polarity=-1, deadband=3):
    # dtorque_raw = gp-0x4f62 (int16)                              @ FUN_0007e74a -> gp-0x4f62
    x = max(-0x1400, min(0x1400, dtorque_raw))       # r1/r8       @ 0x3aa9c-0x3aac0
    scaled = (x * gain_arm_q10) >> 10                # ARITHMETIC shift, sar  @ 0x3ac18, 0x3ac20
    if abs(scaled) <= deadband:
        y = 0
    else:
        y = scaled - deadband if scaled > 0 else scaled + deadband   # @ 0x3ac22-0x3ac3c
    y = y * polarity                                  # gp-0x6752    @ 0x3ac3e
    return max(-0x2000, min(0x2000, y))               # r24          @ 0x3ac42-0x3ac58, stored gp-0x6ada
```

**This is bit-for-bit identical to the closed form the tap-read study already used** (`scaled =
(dtorque*gain_q10)>>10`). No missing shift, no double-application of Q10, no truncation-before-shift
ordering error — the `mul` writes the low 32 bits (product of two ≤13-bit magnitudes, no overflow risk),
then a single `sar 0xa`. **The Q-format hypothesis is refuted for this chain.** I also re-confirmed
`gp-0x4f62`'s own arithmetic (§1.1) is a raw integer divide with no Q-format shift at all — so there is no
second candidate site for a bit-format bug between the two functions either.

---

## Part 3 — `gp-0x671d` census on V283 [EVIDENCE, two independent methods]

**Method 1 — Ghidra `search_instructions`, already-analysed corpus (171,746 instructions), on V282 (byte-
identical here to V283):** 16 hits, `truncated:false`. Two writers — `st.b r0,-0x671d,gp` @`0x3bd2a`
(`FUN_0003bcb2`) and `st.b r28,-0x671d,gp` @`0x41ec6` (`FUN_00041d56`, the resolver/FOC-domain filter
this kit's memory already identifies as `gp-0x671d`'s producer:
[[reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain]]). Fourteen readers across 8 functions
(`FUN_00035ce6`, `FUN_0003aa2c`, `FUN_0003bcb2`, `FUN_0003bd7c`, `FUN_0003d4a2` ×4, `FUN_0003eb38` ×2,
`FUN_00040906`, `FUN_00041d56` ×2).

**Method 2 — raw Python LE-byte scan of the actual V283 file, `0x13000`–`0xFFFFC`, 2-byte aligned,
looking for the `ld.bu`/`st.b` hw2 pattern `e3 98`** (the encoding for displacement `-0x671d`, confirmed
against 14 of Ghidra's 16 hits). This raw scan alone over-counts (26 hits) because `hw2` is shared between
`-0x671d` (odd) and its even neighbour `-0x671e`; I disambiguated using `ld.bu`'s documented parity bit
(hw1 bit 5) and — for the 2 `st.b` writers, which encode parity differently and don't fit the same bit-5
rule — cross-confirmed against Ghidra's own instruction-level decode rather than trusting my own
heuristic. **After adjudication, the two methods agree exactly: 16 real `gp-0x671d` sites, the same 16
addresses.** The 10 extra raw hits are all genuine, unrelated `gp-0x671e` accesses (confirmed by direct
disassembly at `0x37b6a`, e.g. `ld.bu -0x671e,gp,r14`), not evidence of anything at `-0x671d`.

**Verdict: gp-0x671d is unchanged from stock and from every prior build census — 2 writers, 14 readers,
same functions, same addresses.** No new arm-selection path, no LERP substitute, and its producer
(`FUN_00041d56`) is confirmed resolver/FOC-domain, not LKAS or CAN-domain — matching the standing record.
The 5244 (`0xC6446`) arm is reached exactly when `gp-0x671d==0 && gp-0x6806!=0` (§4).

---

## Part 4 — `gp-0x683c` on V283: confirmed dead, repoint verified directly [EVIDENCE, two independent methods + direct byte read]

**Direct byte read, the real V283 file:** `0x3AA94` = `84 7f fb 97`. Fresh Ghidra decompile of
`FUN_0003aa2c` on this exact byte content (V282, confirmed identical here) resolves this instruction as
`bVar4 = *(char *)(unaff_gp + -0x6806) == '\0';` — **`gp-0x6806` (`STEER_CONTROL_ACTIVE`), not
`gp-0x683c`.** This matches this kit's own prior finding
([[reference_accord_r24_gate_repoint_reconciles_lever_b_dead_vs_v280_live]]) that the V104 lineage
repoints this single `ld.bu` displacement from `gp-0x683c` to `gp-0x6806`, and confirms that repoint is
**present, unchanged, on V283** — not merely inherited-and-assumed.

**Method 1 — `search_instructions operand_pattern=683c`:** 1 hit, and it is a `be 0x683c2` **branch-target**
text collision (the branch destination address happens to contain the substring "683c"), not a real
`gp-0x683c` operand — the same false-positive class this kit's decompile skill documents for `jarl`.
Excluded. **Real hit count: 0.**

**Method 2 — raw Python LE-byte scan of the real V283 file** for the `-0x683c` hw2 pattern (`c4 97`),
same 2-byte-aligned full-code-region scan as Part 3: **0 hits, anywhere in `0x13000`–`0xFFFFC`.** (For
comparison, the same scan for `gp-0x6806`'s pattern `fa 97` returns exactly 16 hits — matching this kit's
existing gp-0x6806 census — confirming the scan methodology itself is sound and not silently missing a
real cluster the way it would for a live cell.)

**Verdict: `gp-0x683c` has zero readers and zero writers anywhere in the V283 image, confirmed by direct
byte read of the repoint instruction plus two independent null-searches.** Part 4 of the brief is answered
completely — there is no residual risk that an independent telemetry cave reading `gp-0x683c` directly
would diverge from what the aggregator actually tests; the aggregator does not read that address at all
on this build.

---

## Summary table

| candidate | verdict | evidence |
|---|---|---|
| **(1) derivative `dt`** | **SURVIVES, and now structurally grounded** — `gp-0x4e7e`'s tick unit is a DMA-fed sensor rolling counter, not a CPU tick. Exact ratio **not resolved** (needs the DMA trigger-source config / sensor datasheet rate). | Fresh disasm of `FUN_0007e74a`, `FUN_000825f0`, `FUN_0007df80`, `FUN_0007007c`; SVD confirms `0xFFFF7362`/`0xFFFF736A` = DMAC CH1 `DTC1`/`DTS1`. |
| **(2) Q-format** | **REFUTED** — chain is bit-for-bit the closed form's assumption, no missing/extra shift anywhere from `gp-0x4f62`'s raw divide through r24's clamp. | Fresh disasm `0x3AB90`–`0x3AC5F` and `0x7E7D8`–`0x7E854`, address-exact. |
| **(3) gain arm** | **REFUTED as census** — `gp-0x671d` and the `gp-0x683c`→`gp-0x6806` repoint are byte-identical to the standing record; no alternate/LERP arm path exists. | Two-method census, real V283 file bytes, cross-adjudicated. |

## Addendum — set-difference against `team-lead`'s raw byte census, and the bounded DTRS1 attempt [EVIDENCE]

`team-lead` ran an independent raw byte census (hw2-pattern candidates, undecoded) over 6 cells and asked
me to adjudicate every candidate against Ghidra's real decode (decompile-first, per policy). Full
per-address results below; every candidate was individually disassembled (`disassemble_bytes`, `dry_run`),
not inferred.

### `gp-0x4F62` — the one that matters most for Part 1: confirms a SINGLE producer, no second task

| address | real decode | verdict |
|---|---|---|
| `0x2C4E8` | `ld.h -0x4f62,gp,r22` (`FUN_0002c478`) | REAL — a genuine reader I had not previously catalogued |
| `0x3AA9C` | clamp read, `FUN_0003aa2c` | REAL — already known (r24/r26's shared input) |
| `0x3B6A8` | `ld.h -0x4f62,gp,r11` (near `FUN_0003b66a`, the 8Hz bandpass boost-gain modulator) | REAL — another new reader |
| `0x7E7E0`,`0x7E7EC`,`0x7E854`,`0x7E860` | all inside `FUN_0007e74a` (the producer itself — clamp/shadow-check/store) | REAL — already fully traced in §1.1 |
| `0x7F436`,`0x7F442` | inside `FUN_0007f3f8`, a DIFFERENT branch from the real call: `ld.h -0x4f62,gp,r13; ld.h -0x4488,gp,r15; cmp; bne; st.h r0,-0x4f62,gp; st.h r0,-0x4488,gp` — **zeroes gp-0x4f62 (and its shadow) when the pair still agrees**, after calling `FUN_0007e8d8` | REAL, but a **defensive RESET branch, not a second differencer** — confirms rather than refutes a single producer (see below) |
| `0xBD44A`,`0xBE78A` | `st.b r7,-0x4f61,r19` — base register is **r19**, not gp | FALSE POSITIVE (coincidental hw2 collision with an unrelated base register) |
| `0xC734A` | `satsubr r28,r22` — not an `ld`/`st` instruction at all | FALSE POSITIVE |

**The "written by one task, differenced by another" hypothesis is REFUTED, not confirmed.** `search_instructions mnemonic=jarl operand_pattern=7e74a` returns **exactly 1 hit**, `0x7F9DA` inside
`FUN_0007f3f8` — the sole call site to the producer, program-wide. Immediately before it (`0x7F9A0-0x7F9D8`)
the SAME function writes a rate-limited/rounded value into `gp-0x4f60` (the torque sample `FUN_0007e74a`
differences) via its own shadow pair (`gp-0x4486`) — so the "two different tasks" `team-lead` hypothesized
turn out to be **two branches of the SAME function** (`FUN_0007f3f8`): one path updates `gp-0x4f60` and
calls the real differencer, a separate path (mode/fault-dependent) just zeroes `gp-0x4f62`. Both are on the
same 1kHz task-1 dispatch as everything else in this trace. **This does not change Part 1's verdict** — the
DMA-fed rolling-counter mechanism inside `FUN_0007e74a` itself remains the sole, correct site for the `dt`
question; there is no alternate producer with a different clock domain to reconcile it against.

### `gp-0x683C` — the highest-stakes classification: confirms Part 4 stands

**All 14 candidates decode, unambiguously and individually, to `-0x683b, gp`** (e.g. `0x52E54`:
`st.b r14,-0x683b,gp`; the full cluster is a shadow-pair consistency check — paired with `-0x4c3f`/
`-0x4c40`/`-0x4c41`/`-0x4c42`, calling `FUN_0006b9fa` on mismatch, the SAME redundancy-vote helper this
kit's memory already documents elsewhere). **None of the 14 is `gp-0x683c`.** This is the same
even/odd-neighbor hw2-collision class as `gp-0x671d`/`gp-0x671e` in the main trace, one byte lower.
**`gp-0x683c` itself is still confirmed to have zero real accessors on V283** — Part 4's verdict is
unchanged, now checked against a SECOND independent byte-pattern method (not just my own) and individually
adjudicated, not inferred from a null count.

### `gp-0x6ADA` (r24), `gp-0x6B38` (T), `gp-0x6B94` (aggregator) — quick census, not central to Part 1

- **gp-0x6ADA**: `0x3AD5A` = `st.h r24,-0x6ada,gp` — REAL, confirms this is the exact r24-final-value writer
  (the tail of `FUN_0003aa2c`, matches the cave's tap site). `0x75B7E`, `0x75C74`, `0x797BE` all decode to
  `sst.w r18,0x4c,ep` (an unrelated `ep`-relative struct store) — FALSE POSITIVES.
- **gp-0x6B38**: all 5 non-cave/non-427-tap candidates are REAL — two writers (`0x2A23C` inside the
  arbitration/LKAS-PID neighborhood, `0x2A934`) and three readers (`0x2B418` — the known
  gp-0x6b38→gp-0x6b3c forward hop; `0x4E8D2`/`0x4E8E2` — a packer building a multi-byte struct via `ep`,
  likely CAN-adjacent). No false positives on this cell.
- **gp-0x6B94**: 8 of 9 REAL (all genuine readers — `0x36BF0`; `0x3ACEC`/`0x3ACFA`/`0x3AD12` are the
  shadow-lockstep clamp/store I already saw in the full decompile of `FUN_0003aa2c`; `0x453E0`; `0x4595E`
  feeds a `cvtf.ws` float conversion; `0x80820` is inside `FUN_0007ff08`'s DTC/init state machine, matching
  the `*(short*)(gp-0x6b94)==0` line already visible in that function's decompile in §1.2). `0xC8216`
  (`mov r13,r0` / `sld.h 0xd8,ep,r18`) is a FALSE POSITIVE — not a `-0x6b94,gp` access.

### The bounded DTRS1 attempt — mechanism found, specific value NOT resolved [BELIEF for the mechanism's role, EVIDENCE for what exists]

Per `team-lead`'s explicit one-attempt authorization. `gp`/`tp` cannot reach `0xFFFF7340` (disp16 range is
`0xFEDF0000-0xFEDFFFFF` / `0xBEF00-0xC6FFF`); confirmed the image's actual idiom for this address range is
`movhi -0x1,r0,rX` (constructs `0xFFFF0000` in `rX`) followed by a displacement off `rX` — seen live at
`0x6C242`/`0x6C33C` (`clr1 0x0,0x736a[r18]`, clearing a bit in `DTS1`, DMAC CH1 status — confirms the idiom
and that this kit's own code already touches the DMAC CH1 status register, corroborating §1.2's mechanism
independently). A direct operand-text search for `movea`/`st` with `"7340"` finds **zero** non-tp-relative
hits (the one `"7300"` hit, `movea -0x7300,tp,ep` at `0x1E74E`, is `tp`-relative, resolving to `0xB7D00` — a
ROM cal-table address, unrelated).

Broadening to all 27 `movhi -0x1,r0,rX` sites in the image, one (`FUN_0006cc34`, called from
`0x6CC34`-area boot/init code) is a **generic table-driven bulk SFR initializer**: it walks a caller-
supplied descriptor array (12 bytes/entry — a 32-bit table-relative value, a 16-bit peripheral-offset that
gets OR'd with `0xFFFF0000` to form the absolute SFR address, plus flag bytes) and writes each entry's
value to its computed address in a loop. **This is exactly the class of construct that would make a DTRS1
write invisible to ANY instruction-operand text search** — the actual trigger-source value would be DATA
in a ROM table read by this walker, not an instruction operand anywhere in the code region. I did not
parse that table (locating its base pointer, confirming it is the right walker instance for the DMAC
block, and finding a DTRS1 entry within it is a further, non-trivial trace on its own), and **even a
located entry would still need this chip variant's DMA trigger-source enumeration — which is not in this
kit's SVD** — squarely the stop condition `team-lead` set.

**Reporting per the agreement: the mechanism is established (§1.2, and now independently corroborated by
this attempt's confirmation that the image's code already manipulates DTS1/DTC1 for DMAC channel 1); the
multiplier is NOT determinable from this image** without either parsing the boot-time descriptor table to
find a DTRS1 entry (a further, bounded trace in its own right) or external hardware documentation this kit
does not carry. No ratio, no `sin(π f dt)` gain table, and no predicted comparator duty are offered — they
would not be a measurement, they would be a guess dressed as one.

## What would still close Part 1 fully

Trace the boot-init write to `DTRS1` (`0xFFFF7340`) to identify DMA channel 1's trigger source (which
UART/CSIH peripheral), then that peripheral's baud-rate/prescaler configuration — this pins the sensor
frame rate and hence the exact `dt_effective`. This is genuinely Ghidra work (an absolute-address SFR
write, likely via `movhi`/`movea` to a non-gp base, not yet located) plus, possibly, information this
kit's SVD does not carry (the trigger-source enumeration is chip-specific and not present in the loaded
SVD). I am not confident this closes from the image alone — flagging it rather than guessing a number.
