---
name: reference-accord-can-init-mid-pinmux-topology
description: 2020 Accord TVA-A160 CAN-TX swarm SEGMENT 3 — CAN controller (FCN0/FCN1) boot init, per-buffer MID/CTL/STRB assignment (corrects a prior session's wrong ASCII-block guess), FCN0 global-enable write, and an exhaustive (but ultimately inconclusive) pin-mux/PORT_CFG search. Verdict: exactly ONE CAN controller (FCN0) is ever initialized or enabled; FCN1 receives zero config beyond a boot bulk-zero. Disasm-verified against code.bin + SVD.
metadata:
  type: reference
---

# Accord TVA-A160 CAN-TX swarm — Segment 3: controller init, per-buffer MID map, pin-mux (2026-07-07)

Platform: 2020 Honda Accord 39990-TVA-A160, Renesas uPD70F3508/V850E2. `code.bin` (flat, file offset==address).
`r2 -a v850.gnu -b 32 -m 0 -s <addr> -c 'pd N' code.bin`. gp=0xFEDF8000, tp=0xBF000.
SVD: `analysis-2020accord/reference/svd_for_ghidra/UPD70F3508_V850E2Px4.svd`.
Read-only study. No CAN sent, no flashing.

Mission: re-trace the boot per-buffer MID init loop (0x9ba-0xa46) that a prior session mis-attributed to an
ASCII version-string block at 0xFB0; find the REAL MID source table; find FCN0/FCN1 global
enable/clock/bit-timing init; find CAN pin-mux (PORT peripheral); render a one-bus-vs-two-bus verdict.

## CONFIRMED

### 1. Function boundaries and call chain for the per-buffer init routine
`jarl 0x0000093a, lp` at **file offset 0x5ee** is the ONLY call site found for the function spanning
**0x93a–0xa5c** (ends `0x0000a5c: 7f00 jmp [lp]`), searched across the full sequential boot-dispatch region
(0x0–~0x2400, linear `pd 3000` disasm, which covers the entire early boot init-subroutine-call sequence).
The caller is a tiny 3-instruction wrapper at 0x5e6-0x5f2:
```
0x5e6: prepare {lp}, 0
0x5ea: jarl 0x00000c76, lp     ; peripheral bulk-zero (reaches the previously-documented 0xcf6-0xd08
                                  zero-loop that clears 0xFF480000..0xFF4A2000, i.e. FCN0 + FCN1's buffer space)
0x5ee: jarl 0x0000093a, lp     ; <-- our function: FCN0 module/clock/per-buffer init
0x5f2: dispose 0, {lp}, lp
```
**Sequencing confirmed: bulk zero-clear runs BEFORE per-buffer MID/CTL/STRB configuration.**

Note: file offset 0x900-0x936 (immediately preceding 0x93a) is a DIFFERENT, unrelated subroutine — six calls
to a watchdog/oscillator-wait helper at 0x8c4 with different magic constants (0xBB55/0xE7FB/0xBDAA/0xAF00/
0xB720/0xA902), ending in its own `dispose 0,{lp},lp` at 0x936. It is NOT part of the CAN init sequence
despite being adjacent in the file — a prior read that assumed straight-line fall-through from 0x900 into
0x93a would be wrong; 0x93a is reached only via the `jarl` at 0x5ee.

### 2. FCN0 module-level init (byte-exact against SVD offsets, r2=0xFF480000 held throughout)
```
0x93a: movhi -184, r0, r2        ; r2 = 0xFF480000  (FCN0 base)
0x93e: st.b  r0, 584[r2]          ; FCN0CMLCSTR (offset 0x248, "module last error information") := 0  (clear)
0x94c: mov 4, r1
0x94e: st.b  r1, 8[r2]            ; FCN0GMCSPRE (offset 0x008, clock prescaler [3:0]) := 4
0x962: ld.hu 40[r13], r1          ; r13=0xFB0 at this point (see §3) -> reads ROM cal halfword at file 0xFD8 = 0x0001
0x966: st.b  r1, 616[r2]          ; FCN0CMBRPRS (offset 0x268, "module bit-rate prescaler register") := 0x01
```
`FCN0CMLCSTR`(0x248)/`FCN0CMBRPRS`(0x268) offsets independently confirmed via a full sorted dump of every
named FCN0 register + addressOffset from the SVD (script-extracted, 60+ registers, cross-checked by hand).

### 3. Per-buffer loop 0x9ba–0xa46 — CONFIRMED structure, corrects prior session's r13 error
Loop bound is a **fixed 64** (all HW message buffers; confirmed via `addi -64,r1,r0` (flags-only, ADD not SUB
— CY=1 iff r1>=64 for this immediate's sign) + `bnl 0x9ba` continuing while r1<64), NOT the runtime `r12`
byte (that governs a DIFFERENT, inner two-way branch — see §4). Per iteration (idx = r1 = 0..63):
```
0x9ba: mov r1,r15 ; shl 6,r15                  ; r15 = idx*64
0x9be: mov 0xff489028,ep ; add r15,ep          ; ep = 0xFF489028 + idx*64  = FCN0M{idx}MID0H base
0x9c6: mov 1,r16 ; sst.h r16,16[ep]            ; CTL(ep+16=0x09038) := 1        (halt/config request)
0x9ca: sld.hu 16[ep],r16 ; shr 1,r16 ; bl 0x9ba ; spin-wait: loop (same idx) while CTL bit0 == 1
0x9d0: movea 30,r0,r16                          ; r16 = 30 (0x1E)
0x9d4: mov 0xff481000,r14 ; add r14,r15         ; r15 = 0xFF481000 + idx*64  (DATA-block base, SAME formula
                                                    Segment C's FUN_0001d68e uses for its mailbox writes)
0x9dc: cmp r12,r1                                ; flags: CY=1 iff idx < r12
0x9de: sst.h r16,16[ep]                          ; CTL := 30  (transitional value, later overwritten, see below)
0x9e0: bnl 0xa34                                 ; if idx >= r12: jump to the OUT-OF-RANGE path (§4b)
        ; --- IN-RANGE path (idx < r12) ---
0x9e2: addi 2,r1,r16 ; shl 3,r16 ; ori 129,r16,r16 ; r16 = ((idx+2)<<3)|0x81
0x9ec: st.b r16,36[r15]                          ; FCN0M{idx}STRB (r15+0x24) := ((idx+2)<<3)|0x81
                                                    -> SSOW(bit7)=1 (TX direction), SSAM(bit0)=1,
                                                       SSMT(bits6:3)=idx+2
0x9f0-0xa04: loop r14=0..7: st.b 0,{r15+0,4,8,...,28}  ; clears FCN0M{idx}DAT0B..DAT7B (8x, 4-byte stride —
                                                          matches SVD's byte-addr-at-word-offset layout exactly)
0xa06: mov r1,r16 ; shl 2,r16 ; add r13,r16      ; r16 = r13 + idx*4     (r13 STILL = 0xFB0, unchanged since
                                                    0x95c — see §5, this is the corrected finding)
0xa0c: ld.w 36[r16],r15                          ; r15 = *(u32*)(r13 + idx*4 + 36) = *(u32*)(0xFD4 + idx*4)
0xa14: shl 1,r15                                 ; tests bit31 of the loaded value (CY = old bit31), result
                                                    discarded — flags-only probe
0xa1a: bnl 0xa26                                 ; if bit31==0 (CY=0): "standard-ID" path
        ; extended-ID path (bit31==1):
0xa1c: shr 16,r15 ; sst.h r15,8[ep]              ; MID1H(ep+8=0x09030) := table_val >> 16
0xa20: ld.w 0[r16],r16 ; br 0xa2c                ; r16 = full table_val (reloaded)
        ; standard-ID path (bit31==0):
0xa26: shl 2,r15 ; sst.h r15,8[ep]               ; MID1H := table_val << 2   (r15 here = the FRESH unshifted
                                                    reload from 0xa16 `ld.w 0[r16],r15`, not the throwaway
                                                    shl-1 result — the two branches use different final shifts)
0xa2a: mov 0,r16                                 ; r16 := 0
0xa2c: sst.h r16,0[ep]                           ; MID0H(ep+0=0x09028) := (full table_val for ext, 0 for std)
0xa2e: movea 2310,r0,r16                         ; r16 = 0x906  (final CTL value for in-range buffers)
0xa32: br 0xa3e
        ; --- OUT-OF-RANGE path (idx >= r12), entered from 0x9e0 ---
0xa34: mov 1,r16 ; st.b r16,36[r15]              ; FCN0M{idx}STRB := 1  (SSAM=1 only, SSOW=0 -> RX direction,
                                                    minimal/disabled config; MID0H/MID1H are NEVER written for
                                                    this idx -> they retain HW reset value 0x0000)
0xa3a: movea 286,r0,r16                          ; r16 = 0x11E  (final CTL value for out-of-range buffers)
        ; --- common tail ---
0xa3e: add 1,r1                                  ; idx++
0xa40: addi -64,r1,r0                            ; flags-only: CY=1 iff idx>=64
0xa44: sst.h r16,16[ep]                          ; CTL := 0x906 (in-range) or 0x11E (out-of-range) — FINAL value,
                                                    overwrites the transitional CTL=30 written at 0x9de
0xa46: bnl 0x9ba                                 ; loop while idx<64
```
Register-offset -> SVD name mapping used above, all independently confirmed via a full sorted SVD register
dump: `ep+0`=**FCN0M{n}MID0H**(0x09028, "ID bits[15:0]"), `ep+8`=**FCN0M{n}MID1H**(0x09030, "ID bits[28:16]+IDE
bit13"), `ep+16`=**FCN0M{n}CTL**(0x09038, CSETR=bit2/SEIE=bit3/RDYF=bit8/IENF=bit11 etc.), `r15+36`=
**FCN0M{n}STRB**(0x01024, SSOW=bit7 direction/SSMT=bits6:3 type/SSAM=bit0), `r15+32`=**FCN0M{n}DTLGB**(0x01020,
DLC), `r15+{0,4,...,28}`=**FCN0M{n}DAT0B..DAT7B**(0x01000-0x0101C). Every one of these matches the SVD
`addressOffset` exactly — high confidence in the write-side of this trace.

### 4. The MID source table — CORRECTS prior session's wrong guess, WITH a caveat
Prior session's mistake: they stopped at `mov 0xfb0,r13` (file offset 0x95c, 6-byte imm32 form,
`2d 06 b0 0f 00 00`) and, on dumping raw bytes at 0xFB0 directly, found ASCII text ("0978005.079.988",
"SBK_E13B0100", part numbers) and concluded the MID source couldn't be there — correctly diagnosing that
0xFB0 itself isn't a CAN-ID table, but incorrectly inferring r13 was reassigned somewhere in 0x970-0xa06.

**I walked every instruction in 0x95c-0xa0a explicitly this session: r13 is NEVER reassigned in that range.**
r13 = 0xFB0 is used DIRECTLY at 0xa0a (`add r13,r16`) to build the table pointer. The prior session's error
was stopping the address computation one step early — the real table isn't at r13 itself, it's at
**r13 + idx*4 + 36 = 0xFD4 + idx*4** (32-bit stride, one entry per buffer index), per the `ld.w 36[r16],r15`
at 0xa0c (§3). This is a genuine, disassembly-confirmed correction of the prior finding's stopping point, not
just a restatement of it.

**Caveat (see OPEN #1): dumping this table's actual ROM content produces implausible values almost
immediately.** idx=0 -> `0x9bfc9223` (decodes, via the bit31/extended-ID path, to a constructed 29-bit ID
`0x1CFC9223` — not a recognizable OEM CAN-ID pattern). idx=2-4 literally overlap the ASCII string
"SBK_E13B0100" (i.e. by idx=2 the "table" has already walked into plain text). This means either (a) `r12`
(the in-range/out-of-range threshold, see §5) is very small (1-2), too small to cover the 7 known IDs this
way, or (b) this boot-time write is not the final/only place these buffers' MIDs get set (nothing prevents a
LATER runtime rewrite of MID0H/MID1H, which are documented read-write), or (c) a residual error remains in
this address derivation despite matching the SVD on every other field in this same function. **Flagging
explicitly rather than asserting — this is real tension with `reference_accord_can_tx_fcn0_forward_verify.md`'s
inference that r12>=7 (from Segment C's independently-found "0-6 status-polling loop"); that inference and this
session's table dump cannot both be comfortably true unless the table's early garbage-looking entries are
somehow still functionally correct (e.g. buffer 0 being a deliberately weird/reserved-ID system buffer).**

### 5. `r12` (in-range/out-of-range threshold) — confirmed source, value NOT statically resolvable
```
0x9ac: movhi -288,r0,r12          ; r12 = 0xFEE00000
0x9b0: ld.bu -476[r12],r12        ; r12 = *(u8*)(0xFEE00000-476) = *(u8*)(0xFEDFFE24) = *(u8*)(gp+0x7E24)
```
Matches prior session's identical finding for this address exactly. **I searched for the WRITE side (this
byte's initializer) via the same movhi(-288)+disp(-476) construction pattern used to read it — zero hits
anywhere in the image.** Consistent with this codebase's repeated pattern (documented in
`reference_accord_can_tx_segmentA_channel_topology.md` §4/§5d) of RAM tables/counters whose ROM initializer
isn't found via direct-literal or indexed-store scans — likely a blob-copy or pointer-parameter path invisible
to static literal search. **r12's actual runtime value remains unknown from this static analysis.**

### 6. FCN0 global enable (FCN0GMCLCTL) — a SEPARATE, later function, file offset ~0xdf5e
```
0xdf5e: mov 0xff488000, ep         ; ep = FCN0GMCLCTL (SVD offset 0x8000, "write uses SE/CL upper/lower byte")
0xdf64: sld.hu 0[ep], r1           ; r1 = current GMCLCTL value
0xdf66: movhi -184, r0, r2         ; r2 = 0xFF480000  (rebuild FCN0 base)
0xdf6a: shr 1, r1                  ; test bit0 (PWOM) via carry
0xdf6c: mov 0xfedf208c, r10        ; r10 = a RAM cal-table pointer (below gp, gp-0x5F74)
0xdf72: bl 0xdf82                  ; if PWOM already 1: skip the calibration rewrite below
0xdf74: ld.bu 4[r10], r1 ; st.b r1, 8[r2]   ; (else) FCN0GMCSPRE(+8) := *(u8*)(0xfedf208c+4)  [conditional cal rewrite]
0xdf7c: movea 256, r0, r2
0xdf80: sst.h r2, 0[ep]            ; GMCLCTL := 0x0100   <-- UNCONDITIONAL, both branches converge here
0xdf82: mov 0xff488240, ep         ; (continues into FCN0CMCLCTL, module-level control, offset 0x240 — a
                                       separate register from the global one, not traced further this session)
```
Per the SVD's own documented semantics for this register ("bit-set/clear mechanism... write uses SE/CL upper/
lower byte"), writing `0x0100` (upper-byte bit0) is the documented mechanism to **SET bit0 of the live
register = FCN0GMCLPWOM ("global operating mode: 0=disabled, 1=enabled") = 1**. This write always executes
(the preceding branch only gates a calibration-byte rewrite, not this write) — **FCN0 is explicitly, always
enabled by this code.**

### 7. FCN1 is NEVER enabled or configured — three independent confirmations this session
1. **The 0x93a per-buffer-init function (§2-§4) hardcodes 0xFF480000/0xFF481000/0xFF489028 as compile-time
   literals** (`movhi -184,r0,r2`; `mov 0xff481000,r14`; `mov 0xff489028,ep`) with exactly ONE call site
   (0x5ee) found across the entire linear boot-dispatch region. No parameterization by a channel-base
   argument; no second call site.
2. **The 0xdf5e GMCLCTL-enable function (§6) likewise hardcodes 0xFF488000** via the 6-byte imm32 form.
3. **Direct verification that the only 3 raw-byte matches for `0xFF4A8000` (FCN1's GMCLCTL) anywhere in the
   1MB image are NOT real code.** All three (file offsets 0xc5785, 0xfa385, 0xfaf85) sit at the exact same
   structural position: the tail of an unrelated small routine (`nop; shr 0,r9`) immediately followed by a
   long run of erased/blank flash (`0xFF` repeating, r2 renders it as `breakpoint` = 0xFFFFFFFF). The 4-byte
   pattern `00 80 4a ff` is a coincidental byte-boundary artifact (nop's trailing 0x00 + shr's `80 4a` +
   the first byte of padding), not an instruction referencing FCN1. I disassembled all three sites directly
   to confirm this (see session transcript) — this DIRECTLY RULES OUT what initially looked like a promising
   lead, strengthening rather than weakening the "FCN1 unreferenced" conclusion.

This corroborates and extends `reference_accord_can_tx_segmentA_channel_topology.md` §5b's driver-side
"FCN0-only" finding (which was based on `movhi 0xFF4A`=0 hits and `FUN_0001d68e`'s hardcoded 0xFF481000) with
an INIT-side confirmation via 3 additional, independent methods.

### 8. Pin-mux / PORT_CFG (0xFF404000) — exhaustive search, NO code found (see Inferred + Open)
SVD: `PORT_CFG` peripheral, base `0xFF404000`, block size `0xC19`. Contains `PIPC0-7` (offsets `0x200-0x21C`,
"Port N IP control register... I/O control: 0=software(PM), 1=peripheral(direct)" — THIS is the pin-mux/
alternate-function selector for this chip) plus `PIBC`/`PBDC`/`PU`/`PODC`/`PDSC`/`PIS`/`PPROTS`/`PPCMD`.
**All 42 possible 4-byte-aligned PORT_CFG addresses were searched as raw imm32 literals across the whole
image: all 42 hits cluster inside file offset ~0xbc7c0-0xbc990** (plus 6 more offset-clustered hits for
PORT_DATA, base 0xFFFF8000, in the same region). **I disassembled this region directly — it decodes as
nonsensical nop-padded garbage** (`mov rX,r8 ; st.b lp,N[r0] ; nop nop nop`, rigid 12-byte stride, no
plausible control flow) inconsistent with any compiled function. This is almost certainly a DATA TABLE (a
peripheral-register descriptor blob — plausibly the very source data an earlier session used to build this
SVD) rather than executable pin-mux code. **A second, independent scan for `movhi -192,r0,rX` (0xFF40, the
PORT_CFG base via the movhi+disp idiom) found ZERO hits anywhere in the image.** Between these two
addressing idioms (which are the only two structurally possible ways to build an absolute pointer this far
from `gp`=0xFEDF8000 — the offset is >0x600000, far outside any 16-bit gp-relative disp), **I could not find
ANY genuine code that writes PORT_CFG/PIPC registers anywhere in this firmware image.**

## INFERRED

- Given §7, FCN1 cannot be the mechanism carrying the internal-only IDs (0x660/0x19F/0x32E/0x64D) — no code
  clocks it, configures its buffers, or enables it. Confirmed now from BOTH the controller-init side (this
  segment) and the driver/dispatch side (prior segments A / fcn0_forward_verify / B / C / D), via entirely
  independent search methods each time.
- Given §8 + the SVD's documented PIPC reset default (`0x0000` = software/GPIO mode, i.e. NO peripheral
  routing without an explicit `PIPC=1` write), the total absence of PIPC-writing code is a genuine puzzle
  given CAN0 demonstrably transmits on the real vehicle bus (399/427/0x14A are observed). Three
  non-exclusive explanations, none confirmed: (a) pin-mux is set by an earlier boot-ROM/option-byte stage
  not present in `code.bin`; (b) this specific package/pin assignment routes CAN0 TXD/RXD outside the
  general PORT0-8 GPIO/PIPC matrix as dedicated fixed-function pins; (c) an addressing idiom not checked
  this session is used (a gp-relative form is ruled out by distance, but an indirect/computed-pointer form
  is not fully ruled out).

## OPEN — flagged rather than guessed

1. **MID-table content plausibility (§4).** Table values past idx≈1 look like ROM text/garbage, not CAN IDs.
   Tension with `reference_accord_can_tx_fcn0_forward_verify.md`'s r12>=7 inference. Next step: Ghidra
   decompile of 0x93a-0xa5c with proper struct typing over the 0xFB0-region header, and/or find r12's true
   runtime value (would need a live read, out of this session's static/read-only scope, OR a further static
   search for the missing initializer using an addressing idiom not yet tried).
2. **r12's ROM initializer (§5)** — not found via the one addressing idiom checked (movhi(-288)+disp(-476)
   store form). Other idioms (indexed store via a computed pointer, blob-copy) not yet searched.
3. **The "a2 07" 2-byte sequence** appears 6 times inside function 0x93a-0xa5c (4x preamble 0x942-0x97a, 2x
   tail 0xa48-0xa5c), always in the identical idiom `[imm-load into r1] -> [a2 07] -> [sld.h 26[ep],r1
   overwrites r1] -> [or gp,r0]`. `v850.gnu` cannot decode it (splits as 1-byte invalid + 1-byte unaligned,
   same symptom `reference_accord_can_tx_segmentA_channel_topology.md` §5 flagged at an unrelated address
   0x5221c — now confirmed recurring at a second, structurally different location, suggesting it's a real,
   not-uncommon V850E2 instruction missing from the plugin's opcode table, not a one-off misalignment).
   Attempted a manual Format-I bit decode (opcode=0x01, reg2=r29, reg1=r2) but could not confirm semantics —
   no v850 target in this environment's `objdump`, no V850 support in capstone. **Does not appear to affect
   any of the confirmed findings above** (r1 is clobbered immediately after in every occurrence by the
   following `sld.h`), but is a real, reproducible decoder gap worth fixing via Ghidra's V850E2 module or an
   authoritative ISA manual, since it recurs and may matter elsewhere in the image.
4. **Pin-mux/transceiver count (§8) is UNRESOLVED, not "one confirmed."** I could not find PORT_CFG-writing
   code at all via 2 exhaustive addressing-idiom scans. This means the mission's "how many CAN transceivers
   are wired" question cannot be positively answered from this angle. It does NOT change the one-controller
   verdict below (an unclocked, unconfigured, un-enabled FCN1 cannot transmit/receive regardless of how many
   physical pins/transceivers exist), but it does mean I cannot rule out an unusual pin-wiring scenario purely
   from absence of PIPC-writing code, since I also could not find the code that DOES make CAN0 work at the
   pin level (a real gap — CAN0 clearly functions, so SOME pin configuration happens, I just couldn't locate
   it statically).

## VERDICT

**CONFIRMED, high confidence:** exactly **ONE** CAN controller (FCN0, base `0xFF480000`) is initialized,
clocked, per-buffer-configured, and globally enabled anywhere in this firmware image. FCN1 (base
`0xFF4A0000`) receives no clock/bit-timing config, no per-buffer MID/CTL/STRB/DAT setup, and no global-enable
write anywhere in the image — its only appearance in any traced code path is as the upper bound of the
boot-time bulk register-zeroing loop (`0xcf6-0xd08`, previously documented) that sweeps `0xFF480000` through
`0xFF4A2000` without distinguishing FCN0's own space from FCN1's. This is now confirmed via **six independent
lines of evidence across two swarm sessions**: (1) Segment A's exhaustive `movhi 0xFF4A`/imm32 literal scans
(0 hits beyond the zero-loop bound), (2) `fcn0_forward_verify`'s direct trace of `FUN_0001d68e`'s hardcoded
`0xFF481000` base, (3) this segment's single-call-site trace of the FCN0 per-buffer init function, (4) this
segment's trace of the FCN0 global-enable write, (5) this segment's direct disassembly-level refutation of
the only 3 raw-byte `0xFF4A8000` matches (confirmed padding artifacts, not code), (6) this segment's pin-mux
search ruling out a gp-relative or other short-form escape hatch for reaching FCN1's address range unnoticed.

**Implication for the swarm's core question:** the car-facing (399/427/0x14A) vs internal-only
(0x660/0x19F/0x32E/0x64D) split **cannot be a dual-physical-CAN-channel (FCN0-vs-FCN1) phenomenon** — that
hypothesis is now closed from both the driver/dispatch side (prior segments) and the controller-init side
(this segment). Per the mission brief's own framing: **if there is only one controller, the split must be
explained elsewhere** — vehicle harness/gateway topology (outside what firmware alone can show), a different
on-chip mechanism not yet examined, or a purely logical/software distinction on the single shared bus. The
pin-mux search (§8/OPEN #4) could not positively confirm "exactly one transceiver" — it could only confirm
"no software-driven PIPC pin-mux was found for either controller," which is a weaker, still-open claim.

## Cross-references
- `reference_accord_can_tx_segmentA_channel_topology.md` — original FCN0/FCN1 base discovery, boot zero-loop,
  §5b's driver-side FCN0-only correction (this document's §7 independently corroborates from the init side).
- `reference_accord_can_tx_fcn0_forward_verify.md` — original (wrong-guess) MID-table attempt this session
  corrects (§4), and the r12>=7 inference this session's table dump is in tension with (OPEN #1).
- `reference_accord_can_tx_segmentB_scheduler_descriptor_table.md` / `_segmentC_driver_hw_mailbox.md` /
  `_segmentD_known_frame_provenance.md` / `_synthesis_2026-07-07.md` — driver/dispatch-side documentation of
  the outbound TX path (Table B -> `FUN_0001d68e` -> `0xFF481000+idx*64`), unaffected by this segment's
  findings but consistent with them (both point to FCN0-only).
