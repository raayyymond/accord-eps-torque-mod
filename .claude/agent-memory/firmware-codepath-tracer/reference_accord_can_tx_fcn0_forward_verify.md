---
name: accord-can-tx-fcn0-forward-verify
description: 2020 Accord TVA-A160 V850E2 — forward-traces the 399 (car-facing) and 0x660 (internal) CAN TX builders through FUN_0001d68e to the actual FCN0 hardware message-buffer stores, SVD-grounded register by register. Confirms the "new frame -> same wire as 399/427/0x14A" hypothesis at the FCN0-vs-FCN1 level; finds a NEW boot-time per-buffer TX-config loop (STRB.SSOW + MID0H/MID1H) that complicates (but does not refute) the prior swarm's "single shared mailbox 6" reading.
metadata:
  type: reference
---

# Accord TVA-A160 CAN TX forward-verify: does 399 provably write an FCN0 message buffer? (2026-07-07)

Platform: 2020 Honda Accord 39990-TVA-A160, Renesas uPD70F3508/V850E2. All addresses verified on
`../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin` (flat, file offset == address) with
`r2 -a v850.gnu -b 32 -m 0 -s <addr> -c 'pd N' code.bin`. gp=0xFEDF8000, tp=0xBF000.
SVD: `analysis-2020accord/svd_for_ghidra/UPD70F3508_V850E2Px4.svd` (chip 0DB40h).

**Mission:** the 2026-07-07 CAN-TX swarm (see `reference_accord_can_tx_synthesis_2026-07-07.md`) proved the
dispatch *structure* (Table B: fn-ptr `0xB72AC` / CAN-ID `0xB721C` / DLC `0xB71B8`, 17 entries → HW writer
`FUN_0001d68e` → `0xFF481000+idx*64`) but left one open item: trace a KNOWN car-facing frame all the way to a
concrete FCN0 store, and check whether an internal-only frame (0x660) shares the same physical controller. This
document is that verification, done with fresh byte-level r2 disassembly (not just re-reading prior memory) and
SVD register names cited throughout, per operator standing preference.

## CONFIRMED

### 1. `FUN_0001d68e`'s hardware base is an immutable literal — architecturally FCN0-only
At `0x1d6d4`: `mov 0xff481000,r6 ; add r6,r28` and again at `0x1d784`/`0x1d7e6`: `mov 0xff481000,r8/r9`. This
literal is baked into the function body at **compile time** — it is never `0xFF4A0000` (FCN1) anywhere in this
function, and Segment A's exhaustive whole-image literal scan (both `mov IMM32` and `movhi` idioms) found **zero**
references to `0xFF4Axxxx` outside the one boot zero-fill loop bound. Per SVD, `FCN0.baseAddress = 0xFF480000`
with an `addressBlock` at `offset 0x1000, size 0x25` — i.e. `0xFF481000` is literally FCN0's message-buffer bank
(SVD line ~2520). **Any message dispatched through `FUN_0001d68e` structurally cannot land anywhere but FCN0.**

### 2. Byte-exact SVD-grounded stores inside `FUN_0001d68e`, freshly re-verified
```
0x1d6cc: mov r23,r22 ; shl 2,r22      ; r22 = logical_idx * 4   (r23 = arg2, masked)
0x1d6d0: mov r27,r28 ; shl 6,r28      ; r28 = mailbox_idx * 64  (r27 = arg1, masked)
0x1d6d4: mov 0xff481000,r6 ; add r6,r28   ; r28 = 0xFF481000 + mailbox_idx*64
...
0x1d6fe: mov 0xb71b8,ep ; ... ; add r23,ep ; sld.bu 0[ep],r13   ; r13 = DLC_table[logical_idx]  (0xB71B8, DLC array)
0x1d70e: st.b r13,32[r28]                                        ; -> FCN0M{N}DTLGB  (SVD addressOffset 0x01020+N*0x40)
...
0x1d77c-0x1d7b8 (ep = r27<<6 + 0xFF481000, computed fresh at 0x1d780-0x1d78a):
  sst.b r6, 0[ep]   -> FCN0M{N}DAT0B  (SVD 0x01000+N*0x40)
  sst.b r15,4[ep]   -> FCN0M{N}DAT1B  (0x01004+N*0x40)
  sst.b r13,8[ep]   -> FCN0M{N}DAT2B  (0x01008+N*0x40)
  sst.b r11,12[ep]  -> FCN0M{N}DAT3B  (0x0100C+N*0x40)
  sst.b r8,16[ep]   -> FCN0M{N}DAT4B  (0x01010+N*0x40)
  sst.b r6,20[ep]   -> FCN0M{N}DAT5B  (0x01014+N*0x40)
  sst.b r15,24[ep]  -> FCN0M{N}DAT6B  (0x01018+N*0x40)
  sst.b r13,28[ep]  -> FCN0M{N}DAT7B  (0x0101C+N*0x40)
```
For N=6 this is `0xFF4811A0` (DTLGB) and `0xFF481180-0xFF48119C` (DAT0B-DAT7B) — matches the SVD's stated
"array step 0x40 for buffers 1-63" formula exactly. Source data for the 8 bytes is `r26[0..7]`, `r26` being the
non-null-checked return value of the just-invoked content-builder (`jmp [r25]` at `0x1d744`, `r25` = the
fn-ptr-table entry `table-A[logical_idx]` = e.g. `FUN_00055c42` for 399 at idx9, `FUN_000561b0` for 0x660 at
idx4 — table itself re-confirmed byte-identical to Segment C/D's dump). This is a **direct, fresh, byte-level
re-verification** of Segment C's original finding, not a re-quote.

### 3. `FUN_0001f98e` = generic critical-section PSW-read helper, NOT an ID/CTL setter
`0x1f98e: stsr psw/vmtid,r10 ; jmp[lp]` (4 bytes total). Confirmed this is the `di`/`ei`-wrapped critical-section
idiom seen throughout the driver cluster (called immediately before every `di`), not a hidden hardware-register
writer. Rules out one hypothesis for where MID/STRB might be set per-message.

### 4. One of `FUN_0001d68e`'s 3 call sites is a confirmed DEAD branch for the entire current 17-entry table
Call site 1 (`FUN_0001d82e`, call at `0x1d904`): `0x1d866: mov 0xb7208,ep; add r24,ep; sld.bu 0[ep],r26` loads
the per-message "channel byte" (Segment D's table), then `0x1d88c: cmp 6,r26 ; bne 0x1d8b8`. **When r26==6 (true
for all 17 currently-populated table-A entries, Segment C/D's exhaustive dump), execution falls through
`0x1d890-0x1d8b6` to an EARLY RETURN (`mov 1,r10 ; br 0x1d90e/dispose`) that never reaches the `FUN_0001d68e`
call at `0x1d900-0x1d904`.** Freshly re-verified byte-for-byte — this independently confirms Segment D's original
finding via direct disassembly (not by re-reading their memory file).

### 5. The real, live call site (0x1dc8e) hardcodes mailbox_idx=6 as a literal
`FUN_0001d82e`'s sibling dispatcher (the one containing `0x1dc8e`) ends its selection logic with:
```
0x1dc40: andi 0xffff,r28,r26      ; r26 = logical index found by a bitmask-scan dispatcher (see below)
0x1dc8a: mov r26,r7
0x1dc8c: mov 6,r6                  ; <-- LITERAL, mailbox_idx = 6, unconditional
0x1dc8e: jarl 0x0001d68e,lp
```
Bytes at `0x1dc8c`: `06 32` = `mov 6,r6` — a **compile-time literal**, not computed. This is the call site that
actually reaches `FUN_0001d68e` for the populated table (call site 1 is dead per #4). Call site 2 (`0x1db32`)
structurally mirrors this exact shape (`0x1dae6: andi 0xffff,r28,r26` — byte-identical pattern to `0x1dc40`) —
same bitmask-scan-into-`r26` convergence, `r7=r26` at the call — but I did **not** locate the instruction that
sets `r6` for call site 2's specific `jarl` in the disassembly window inspected this session (see Open Questions).

### 6. A genuine boot-time per-buffer TX-init loop exists and DOES set STRB.SSOW=1
Located via a literal-address scan (searching for `0xFF489000+n*0x40+0x38`, the CTL-register alias address, which
hit at file offset `0x1D036` — inside the driver cluster, corroborating Segment C's "unrolled 0-6 status polling
loop" — and separately at file offset `0x9C0`, in early boot code). The boot loop at `0x9ba-0xa46`:
```
0x9ba: mov r1,r15 ; shl 6,r15            ; r15 = idx*64  (r1 = loop counter, buffer index)
0x9be: mov 0xff489028,ep ; add r15,ep    ; ep = FCN0M{idx}MID0H base (SVD 0x09028+idx*0x40)
0x9c8: sst.h r16,16[ep]                   ; write to ep+0x10 = CTL (SVD MID0H+0x10 = 0x09038 = FCN0M{idx}CTL)
...  [spin-wait on CTL bit1, then data-byte + DLC zero-clear loop]
0x9d4: mov 0xff481000,r14 ; add r14,r15  ; r15 = 0xFF481000 + idx*64  (the DATA-block base, SAME formula as
                                            FUN_0001d68e uses)
0x9e2: addi 2,r1,r16 ; shl 3,r16 ; ori 0x81,r16,r16 ; st.b r16,36[r15]
```
`36 decimal = 0x24 = FCN0M{idx}STRB` (SVD `addressOffset 0x01024+idx*0x40`, field `SSOW` bit7 = TX direction).
The value written is `((idx+2)<<3) | 0x81` — **bit7 (0x80) is unconditionally set by the `|0x81`, regardless of
idx.** This loop runs for `idx = 0 .. r12-1`, where `r12` is a **runtime RAM byte** read at `0x9ac-0x9b2`
(`movhi -288,r0,r12 ; ld.bu -476[r12],r12`, resolving to address `0xFEDFFE24`, i.e. `gp+0x7E24`) — **not a static
literal**, so its exact numeric value could not be pinned from `code.bin` alone this session. Given Segment C
independently found an **unrolled 7-entry (indices 0-6) status-polling loop** elsewhere in this same driver
cluster, it is a reasonable (not 100%-statically-proven) inference that `r12 >= 7`, i.e. **buffer 6 falls within
the TX-configured range.**

## INFERRED (structurally well-supported, not byte-exhaustively proven)

- **399 and 0x660 both structurally MUST write FCN0 whenever their content reaches hardware**, because (a) both
  builders (`FUN_00055c42`/`FUN_000561b0`) have **zero direct JARL callers** anywhere in the image (Segment D,
  re-confirmed by the same fn-ptr-table-only-read-inside-`FUN_0001d68e` structure I independently re-verified at
  `0x1d728-0x1d744`), and (b) the only reader of that fn-ptr table is `FUN_0001d68e`, whose HW base is the
  immutable `0xFF481000` literal (finding #1). There is no code path by which either builder's content reaches
  hardware except through this one function. **This is the core of the mission hypothesis and it is CONFIRMED at
  the FCN0-vs-FCN1 level**, independent of exactly which mailbox index (N) is used.
- The bitmask-scan dispatcher feeding call sites 2/3 (large nibble-decode structures at `0x1d9a0-0x1dae6` and
  `0x1db90-0x1dc40`, shr-28/24/20/16/12/8/4/0 walks over a status word with small per-nibble sub-table lookups at
  `0xb71cc`/`0xb71e0`/`0xb71f4`/`0xb72f4`) shows **no car-facing-vs-internal differentiation anywhere** in the
  branches actually walked — consistent with Segment D's "no field splits car-facing from internal" conclusion,
  now independently re-derived from the control-flow side rather than just the per-message table-value side.

## OPEN — genuinely unresolved, flagged rather than guessed

1. **Whether mailbox index 6 is truly a single SHARED staging buffer for all ~11 TX-capable logical messages, or
   whether each logical message has its own dedicated buffer (with 6 being merely the one this session's traced
   branch happened to hardcode).** This is the central remaining uncertainty. The NEW finding in #6 above (a
   per-buffer boot-time loop that ALSO writes `MID0H`/`MID1H`, i.e. the buffer's CAN **arbitration ID**, seemingly
   per buffer index) is in real tension with "one shared mailbox handles 11 different CAN IDs" — a single hardware
   mailbox cannot simultaneously hold 11 different fixed arbitration IDs. I attempted to identify the source table
   feeding the `MID1H` write (traced a register `r13` that appeared, at one point, to hold `0xFB0`) but on
   dumping `0xFB0` directly this is a **firmware version/part-number ASCII string block**
   (`"0978005.079.988"`, `"SBK_E13B0100"`, `"0369981116001"`, etc.) — **not a CAN-ID table** — meaning my
   attempted identification of the `MID1H` source was wrong (`r13` must have been reassigned to a different base
   between `0x970` and `0xa06`, in a code region I did not fully disassemble this session). **I am explicitly
   NOT asserting what feeds `MID0H`/`MID1H`.** The most structurally plausible resolution — that the large
   nibble-decode "bitmask scan" dispatcher has MULTIPLE branches, each hardcoding a DIFFERENT `(mailbox_idx,
   logical_idx)` pair for a different pending-bit, of which `0x1dc8e`'s `mov 6,r6` is only the ONE branch this
   session happened to trace to completion — is a reasoned inference, not a proven fact. **What would close this:**
   fully decode the sibling nibble-branches in `0x1db90-0x1dc40` (and its `0x1d9a0-0x1dae6` twin) to see if any of
   them hardcode a mailbox literal other than 6, and separately re-trace `r13`'s reassignment between `0x970` and
   `0xa06` to find the real `MID0H`/`MID1H` source table.
2. **The exact mailbox index N used specifically for 399 (table-A idx9) and specifically for 0x660 (idx4) was NOT
   statically pinned this session.** I confirmed the literal `6` is used at the one live call site, but did not
   exhaustively prove that idx9/idx4 are among the values `r26` can take when reaching that specific call site
   (as opposed to reaching call site 2, whose `r6`-provenance is also unresolved — Open Item below). **Per the
   task's own instruction: this is a runtime/structurally-computed value I could not pin statically, so I am
   flagging it rather than guessing.** What would close this: either exhaustively decode the whole bitmask-scan
   dispatcher's per-nibble sub-tables (`0xb71cc`/`0xb71e0`/`0xb71f4`/`0xb72f4`, values not yet dumped/decoded) to
   derive the idx→(mailbox,call-site) mapping statically, or take a live RAM/register trace while the ECU
   transmits 399 and 0x660 (out of scope for this read-only static session).
3. **Call site 2's (`0x1db32`) `r6` (mailbox_idx) provenance is unresolved.** The function containing it has the
   same bitmask-scan shape as call site 3, but I did not locate where `r6` is set for its `jarl 0x1d68e` — it may
   be set once at function prologue (unexamined region) or be a different literal than 6.
4. **`r12` (the boot-loop's TX-buffer-count bound) is a runtime RAM value (`gp+0x7E24`), not statically known.**
   Buffer index 6 falling within `[0, r12)` is inferred from Segment C's independent "0-6 polling loop" finding,
   not proven by finding `r12`'s literal initializer this session.

## VERDICT

**CONFIRMED:** 399 (car-facing) and 0x660 (internal) both structurally write an **FCN0** message buffer's DATA
(`DATxB`) and length (`DTLGB`) registers when their content reaches hardware — this is architecturally guaranteed
by `FUN_0001d68e`'s immutable `0xFF481000` base literal and by both builders being reachable ONLY through that
function. **FCN1 (0xFF4A0000) is definitively not involved** — re-confirmed by the same absence-of-literal
evidence Segment A found, now cross-checked from the call-site side too. **A new TX frame added by extending
Table B (the fn-ptr/ID/DLC array triplet) and dispatched through the same `FUN_0001d68e` mechanism will,
likewise, structurally land on FCN0 — the same physical wire as 399/427/0x14A. The core hypothesis under test
is CONFIRMED.**

**STILL-INCONCLUSIVE (narrower, does not block the build feasibility conclusion above):** whether the new frame
would share the *exact same* hardware mailbox index (6) as existing traffic, or land on a distinct dedicated
index, is open per the Open Questions above — and per Segment C's "hardware mailbox headroom plentiful, ~64/FCN0,
only a fraction wired" finding, either outcome is buildable; this narrower question affects *which* mailbox index
a new frame's dispatch code should target, not *whether* FCN0 is reachable.

**TX-direction config:** STRB.SSOW=1 is CONFIRMED written (via an unconditional `|0x81` OR) for a boot-time-loop
range of buffer indices `[0, r12)`; buffer 6 falling inside that range is a well-supported inference (not a
pinned-literal proof, since `r12` is runtime RAM).

## Cross-references
- `reference_accord_can_tx_synthesis_2026-07-07.md` — the swarm rollup this document verifies against.
- `reference_accord_can_tx_segmentC_driver_hw_mailbox.md` — original `FUN_0001d68e` trace + 17-entry table +
  "unrolled 0-6 status-polling loop" (corroborates buffer-6 liveness here).
- `reference_accord_can_tx_segmentD_known_frame_provenance.md` — original b7208=6 / call-site-3 finding, now
  independently re-derived from the control-flow (branch-condition) side in this document.
