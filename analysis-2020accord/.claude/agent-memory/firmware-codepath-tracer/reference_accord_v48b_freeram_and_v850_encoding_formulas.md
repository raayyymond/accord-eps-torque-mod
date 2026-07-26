---
name: reference-accord-v48b-freeram-and-v850-encoding-formulas
description: V48B notch-cave free-RAM audit (CORRECTS a prior gp-0x14E0 claim) + fully bit-derived, multi-example-verified V850E2 instruction encoding formulas for hand-assembling code caves in code.bin.
metadata:
  type: reference
---

## Free RAM audit (2026-07-21, code.bin/stock, gp=0xFEDF8000)

**Cell A — gp-0x1500 (abs 0xFEDF6B00/6B01), 1 halfword.** RECONFIRMED clean this session: exhaustive
`search_instructions` prefix sweep of `-0x150`/`-0x14f` (both `truncated:false`) shows zero literal
touches at disp `0x1500` or `0x14FF`. Matches prior finding exactly; this is also the cell V31P's
telemetry cave (`FUN_00055a98`-adjacent) used successfully — good precedent. Do NOT extend to a word:
disp `0x1502`/`0x1503` (abs `0xFEDF6AFE`/`6AFD`) are live (`ld.bu -0x1502,gp,r10` etc).

**⚠ CORRECTION — the previously-recorded "gp-0x14E0, 4 free bytes 0xFEDF6B1D–0x6B20" is WRONG.**
Fresh byte-level re-verification found **3 of those 4 bytes are LIVE**: disp `0x14E1`/`0x14E2`/`0x14E3`
(abs `0xFEDF6B1F`/`6B1E`/`6B1D`) are written by `FUN_000558a6` (`0x558a6-0x55a96`), a CAN/status byte
packer that stores 6 consecutive payload bytes at disp `0x14E6..0x14E1` and then packs 4 status bits
into the `0x14E1` byte via **two independent, cross-confirming addressing forms**: gp-relative
(`ld.bu/st.b -0x14e1,gp,rX`) AND absolute (`movhi -0x121,r0,r18` → `set1/clr1 N,0x6b1f,r18`, i.e.
`r18=0xFEDF0000` then `0x6b1f[r18]` = the exact same byte `0xFEDF6B1F`). Disassembly at
`0x55a06-0x55a82` shows the pattern explicitly. **Only disp `0x14E0` (abs `0xFEDF6B20`) itself is free.**

**Corrected free run in that neighborhood: disp `0x14DD`–`0x14E0` = abs `0xFEDF6B20`–`0xFEDF6B23`, 4
contiguous bytes** (bounded below by touched `0x14DC` — `st.h r28,-0x14dc,gp` @`0x21798` — and above by
the live `0x14E1`). Verified clean by: (1) exhaustive gp-relative prefix scan of `-0x14d`/`-0x14e`
(`truncated:false`, no hits at DD/DE/DF/E0); (2) targeted absolute-form checks for literal `0x6b20`,
`0x6b21`, `0x6b22`, `0x6b23` program-wide (the few hits found were `-0x6bXX,gp` — i.e. disp `0x6B2X`,
address `0xFEDF14xx`, a coincidental hex collision at an unrelated cell, correctly excluded); (3)
`read_memory` at `0xFEDF6B20` → "Unable to read bytes" (unbacked RAM, consistent). **Cell A (2B) +
corrected Cell B (4B) = 6 bytes across 2 non-contiguous spots — short of the preferred 8-byte run.**

**★ Cell C (NEW, RECOMMENDED PRIMARY) — gp-0x7F00 through gp-0x7FFF, abs `0xFEDF0000`–`0xFEDF00FF`, a
clean 256-byte contiguous region.** This is the extreme end of gp's negative disp16 reach (gp-0x8000 is
the max). Evidence:
- Exhaustive `search_instructions(operand_pattern="-0x7f")` program-wide (`truncated:false`, 161 total
  hits) — every hit with `gp` as base has a **3-digit** disp (`0x7f7`/`0x7f8` = 2039/2040, an unrelated
  cell near `0xFEDF7808`); **zero** hits with a 4-digit `0x7fXX` disp (32512-32767, our target range) on
  a `gp` base. All 4-digit `-0x7fXX` hits use `tp`/`ep`/`r0`/`r13`/`r14`/`r17`/`r26`/`r28` as base — either
  flash/cal space (`tp`) or SFR space (`r0`, since `r0` is architecturally 0 → address wraps to
  `0xFFFFxxxx`), not our RAM cell.
- Exhaustive `clr1` (212/212, `truncated:false`) and `tst1` (220/220, `truncated:false`) mnemonic scans,
  plus a near-exhaustive `set1` scan (250/~291, 88% of instructions covered) — checked every absolute
  bit-op reachable via the ubiquitous `movhi -0x121,r0,rX` idiom (which sets `rX=0xFEDF0000`, used with
  dozens of destination registers program-wide as the compiler's absolute-addressing base for
  set1/clr1/tst1, since those opcodes have no gp+disp16 form). **Every single r18-style absolute bit-op
  offset found is ≥0x156C — none below 0x100.** Confirms this compiler/linker convention never places
  bit-flag structs at the very start of the gp-reachable window.
- `read_memory` at `0xFEDF0000` and `0xFEDF00F8` both fail "Unable to read bytes" (unbacked RAM).
- Residual/unclosed risk: regular `ld/st` (non-bit-op) absolute forms via the same `-0x121` register
  family were **not** individually audited (100s of instances, impractical to fully enumerate this
  session) — only the bit-manipulation subclass was exhaustively checked. Architecturally this residual
  risk is low: gp-relative disp16 already reaches this address in one instruction, so there is no
  compiler incentive to burn a movhi+reg pair on a regular load/store here. Treat as **strong, not
  ironclad** evidence; a full audit would need to grep every `-0x121`-established register's subsequent
  small-offset ld/st, which the search tool cannot filter for in one pass.

**Recommendation:** use Cell C, e.g. `gp-0x7F00`/`gp-0x7F02`/`gp-0x7F04`/`gp-0x7F06` for x1/x2/y1/y2 (all
one contiguous 8-byte block, far from the busy CAN-buffer struct at gp-0x1400..0x1600). Cell A/B remain
valid as a documented fallback (6 bytes, 2 locations) if the operator prefers to stay adjacent to the
already-flown V31P precedent.

## V850E2 instruction encoding formulas (verified 2026-07-21 against real code.bin bytes)

Method: `disassemble_bytes` has **no bytes-input parameter** — it disassembles bytes already present at
an address, it cannot decode caller-supplied candidate bytes on undefined memory. So verification here
was done by finding **multiple independent real instances** of each mnemonic via `search_instructions`
(which returns the raw `bytes` field alongside Ghidra's decoded operands), bit-extracting the bytes by
hand, solving for the constant "opcode" field across ≥2 examples with different registers/immediates,
then computing the requested target encoding by the same formula and cross-checking a 3rd/4th real
example. Every formula below reproduced ≥2 independently-pulled real instruction bytes exactly.

All values little-endian; "byte0,byte1" = low byte, high byte of each 16-bit half.

**Format I (2-byte, reg1 op reg2, reg2 is dest):** `value = (reg2<<11)|(opcode<<5)|reg1`
- MOV reg1,reg2: opcode=0x00. (`mov r8,r14`=`08 70` confirmed)
- ADD reg1,reg2: opcode=0x0E. (`add r11,r10`=`cb 51` confirmed — reg2+=reg1)
- CMP reg1,reg2: opcode=0x0F. (`cmp r0,r8`=`e0 41`, `cmp r11,r10`=`eb 51`, both confirmed)

**Format II (2-byte, imm5 op reg2):** `value = (reg2<<11)|(opcode<<5)|imm5`
- SAR imm5,reg2 (arithmetic shift right): opcode=0x15. `sar 12,r10` → value=0x52AC → bytes `ac 52`.

**Format V/VI (4-byte, imm16):** `halfword1=(reg2<<11)|(opcode<<5)|reg1; halfword2=imm16` (raw 16-bit
two's-complement pattern, NOT scaled — confirmed by exact byte match against real `-0x7c28` etc examples).
- ADDI imm16,reg1,reg2: opcode=0x30. `addi -16,sp,sp`→`03 1e f0 ff`; `addi 16,sp,sp`→`03 1e 10 00`.
  ADDI sets PSW flags (Z/S/OV/CY) identically to ADD — standard documented V850 ISA behavior, not
  independently pcode-reverified this session; confirm via `get_function_pcode` if bit-exact certainty
  on flag timing is safety-load-bearing.
- MOVEA imm16,reg1,reg2 (reg2=reg1+sign_ext(imm16), no flags): opcode=0x31.
  `movea 0x6400,r0,r11`→`20 5e 00 64`; `movea 0x9c00,r0,r11` (=-25600)→`20 5e 00 9c`.
- MULHI imm16,reg1,reg2 (reg2 = sign_ext(reg1[15:0]) × sign_ext(imm16), 32-bit result, signed 16×16→32):
  opcode=0x37. `mulhi 4045,r12,r11`→`ec 5e cd 0f`; `mulhi -7949,r12,r11` (imm=0xE0F3)→`ec 5e f3 e0`.

**Load/Store disp16 (4-byte):** `halfword1=(reg2<<11)|(opcode<<5)|reg1` [reg2=dest for load / src value
for store; reg1=base register]. `halfword2` encodes the displacement — **and this is where V850E2's real
quirk lives**: LD.H and LD.W (and separately ST.H and ST.W) **share the same 6-bit opcode field**;
byte/halfword-vs-word is selected by **bit0 of the encoded disp16 field**, not by the opcode:
- LD.H/LD.W opcode=0x39. ST.H/ST.W opcode=0x3B. (LD.BU opcode=0x3C, distinct — not requested but checked
  in passing.)
- For **.h** (byte/halfword) access: `halfword2 = disp16` raw, two's-complement, **must itself be even**
  (bit0=0 naturally, since halfword access requires 2-byte alignment).
- For **.w** (word) access: `halfword2 = disp16 | 1` — bit0 is **forced to 1** as the format flag. disp16
  itself must still be even (word-aligned in practice). Confirmed by decoding real `ld.w 0x18,sp,r7` →
  raw second halfword `0x0019`, and `0x0019 & ~1 = 0x0018` = the *displayed* disp exactly; reconfirmed
  on 4 more examples (`0x24`→`0x25`, disp=0/4/0x30 on st.w, etc). **This directly resolves the operator's
  "does bit0 encode format" question: yes, for the WORD form only, not the halfword form.**
- `ld.h -0x1500[gp],r12` → `24 67 00 eb`. `st.h r10,-0x1500[gp]` → `64 57 00 eb`.
- `st.w r10,0[sp]` → `63 57 01 00` (raw imm=0|1=1). `ld.w 8[sp],r12` → `23 67 09 00` (raw imm=8|1=9).

**Format III (2-byte Bcond, PC-relative):** `value = ((d8>>3)<<11)|(0xB<<7)|((d8&7)<<4)|cond`, where
`d8 = (disp>>1) & 0xFF` (8-bit signed; disp must be even; effective range ≈ -256..+254 bytes from the
branch instruction's own address). `0xB` (`1011`) at bits[10:7] is the fixed Bcond format identifier.
Condition nibble (bits[3:0]), reconfirmed against real bytes: **BGE=0xE, BLT=0x6, BLE=0x7, BGT=0xF**
(standard V850 table). Formula reproduced 3 independent real examples exactly, including a negative-disp
one (disp=-28 → `f5 ae`) proving the sign-extension path. Small forward branches:
- disp=+4: BGE→`ae 05`, BLT→`a6 05`, BLE→`a7 05`, BGT→`af 05`.
- disp=+6: BGE→`be 05`, BLT→`b6 05`, BLE→`b7 05`, BGT→`bf 05`.
- disp=+8: BGE→`ce 05`, BLT→`c6 05`, BLE→`c7 05`, BGT→`cf 05` (the BLE/+8 case, `c7 05`, exactly matches
  a real confirmed instance at `0x15124`, disp=8 — independent validation).

**JR disp22 / JARL disp22,lp (4-byte):** the operator's existing Python encoders are **CONFIRMED CORRECT**
against 4 real examples (2 positive-disp, 2 negative-disp, the negative ones exercising the `disp>>16`
carry path):
- `jr`: `halfword1 = 0x0780 | ((disp>>16)&0x3F)`, `halfword2 = disp&0xFFFF`.
- `jarl disp,lp`: `halfword1 = 0xFF80 | ((disp>>16)&0x3F)`, `halfword2 = disp&0xFFFF`.
Not tested at exactly `disp≈0x44000` this session, but the linear bit-packing structure is doubly
cross-validated (positive-small and negative-large-disp>>16 cases both reproduced exactly), so it is
expected to generalize with high confidence.

## Cross-reference
See [[reference-accord-lkas-only-rate-limiter-c6194]] and the V48B notch design context in
`docs/HANDOFF-2026-07-21-v48-vibration-loopgain-notch.md` / `eps_v48b_notch_design.py` for why this cave
exists (filtered copy of `gp-0x4f60`, DF-I biquad, 21.4 Hz notch).
