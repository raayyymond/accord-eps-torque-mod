# TRACE 2026-10-02: the V298 fresh-rate D term, its sign, and `pol` (gp-0x6752)

Subagent `firmware-codepath-tracer`, for the orchestrator's V298 route-79 panel. Read-only. Nothing was built,
flashed or sent. Ghidra was used through `mcp__ghidra__*` only, with `disassemble_bytes dry_run:true`. Nothing
was renamed or saved. Programs: `ADVIG_V298_177abf04.bin` (Ghidra bytes at `0x29ED0` and `0xC4C00` match a Python
read of the V298 image, sha256 `177abf04…2066`) and stock `code.bin`, which is used only for functions that are
byte-identical in V298 (§6). Python is the `bin_decompile` env. Scripts are in `_scratch/dsign-trace/`
(`ds01` diff and identity, `ds02` raw census, `ds03` mirror). `gp = 0xFEDF8000`, `tp = 0xBF000`.

## 0. Answers

1. **`gp-0x6abe` is a MOTOR-frame rate.** Its only writer is `FUN_00041464`, called once per tick from
   `0x22200` in slot 0 at 1 kHz, before the PID call at `0x22522`. It is an EMA (α = 37/128, cal `0xC643C`) of
   the resolver differentiator `gp-0x4f50` (`FUN_00068f52`). It carries **no pol factor**. The angle `gp-0x6a00`
   and the wire rate `gp-0x6a56` each carry **one** pol factor. So
   **sign(gp-0x6abe) = pol · sign(dθ/dt)**. pol is the only sign-bearing cell between them. **EVIDENCE** (§2, §3).
2. **D enters the driver-frame sum S with a + sign** (`0x29F24 add r8,r2`). D = clamp((48·gp-0x6abe)>>3, ±10240)
   = 6·abe. There is no pol on the D operand, and the whole S is multiplied by pol at the output (`0x2A1F6`/`0x2A1FE`).
   On this car (pol = −1), a wheel moving toward its setpoint gets **D < 0 while P > 0, so D opposes the motion**.
   In the aggregator frame the D term has the **same sign as Honda's own viscous damper** `gp-0x6bd0 = −sgn(abe)·m`
   (`0x3469E`–`0x346A2`). **EVIDENCE** (mirror in §3; `ds03` prints `D=-564 OPPOSES` for pol −1).
3. **E is pol-free** in the lane (E = 4·gp-0x69ae − r26; neither operand is multiplied by pol). P therefore meets
   pol twice (θ's frame and the output). D meets it once (the output only). **A pol of +1 would invert D alone**,
   through the byte `gp-0x6752` read at `0x2A1F2` and applied at `0x2A1F6`/`0x2A1FE`. **EVIDENCE.**
4. **Minimal flip** (§5.1): `0x29EE2` `00 00` (nop) → `80 41` (`subr r0,r8`). 2 B, flag-safe, exact. No cal-only
   flip exists, because Kd is zero-extended (`0x29EDE zxh r7`). **Pol-invariant form** (§5.2): +8 B in the cave
   (`ld.b -0x6752[gp],r8 ; mulh r8,r26 ; subr r0,r26`), relinked. **On this car it computes exactly what V298
   computes.**
5. **pol = −1 on V298 at run time.** The V98 `b3` rung was a run-time RAM read of the same cell. Its duty was
   0.0000 over 17,983 frames, and V99 reproduced it on 12,005. That measurement **still applies to V298**:
   the parser, the pre-seed and the re-assert functions are byte-identical in stock, V98 and V298; the writer
   census is identical; and the config records sit below `0x13000`, which no `.rwd` writes (§4).
   🛑 **Record correction:** `FUN_000497e6` is **live**. It is called from the slot-3 task at `0x22C46` (mask
   `0x830`) and re-asserts pol from the saved record on every pass. The "zero callers" in
   `reference_accord_gp6752_resolved_negative_one_…` was a **tool zero**: Ghidra defines no function at slot 3.
6. ⭐ **For the panel:** at the **tap** (`gp-0x6b38` against the wire rate `x = gp-0x6a56`), the D component is
   **pol²-invariant**: T_D/x > 0 for both pol values (`ds03`). **A pol error cannot show up as a negative c_D.**
   It would show up as a sign flip of the absolute P coefficient (the structural `a`). It would leave the ratio
   c_meas/c_raw unchanged, because both of its terms flip together. A mixed-sign c_D therefore **cannot be a clean
   inversion of this D.** **EVIDENCE** for the algebra; the panel decides what the data says.

---

## 1. Entry point and goal

Entry: the cave load `0xC4C04 ld.h -0x6abe[gp],r26` and the in-place operand `0x29EE0 mov r26,r8` (OPH). The trace
goes backward to the sensor and to pol, and forward through S and the output pol multiply into the aggregator,
where it is compared with Honda's own damper. Goal: under what condition does D oppose a wheel moving toward
θ_sp, and which bytes decide it.

## 2. The path (every hop read from the V298 bytes, Ghidra dry-run)

| hop | addr | instruction | effect on the traced value |
|---|---|---|---|
| sensor | `FUN_00068f52` (from `0x65E5A` in `FUN_00065afe`) | wrap(θe−θe′)·120000>>14, 2-tap mean, clamp ±13000 | `gp-0x4f50`, motor electrical rate (kit record `reference_accord_common_mode_rate_…`) |
| producer | `0x22200` → `FUN_00041464` | state += ((raw·1024−state)·37)>>7; abe = state>>10 | `gp-0x6abe`; 4 `st.h` at `0x41790/0x417A0/0x419F8/0x41A18`, census §6 |
| wire rate | `0x22DE2` → `FUN_0003f776` (100 Hz) | `0x3F794 mulhi 0x30` · `0x3F7A0 mul` (1159) · `0x3F7A4 sar 15` · `0x3F79C ld.b -0x6752` · `0x3F7A6 mul` | `gp-0x6a56 = pol·((abe·48·1159)>>15)`, clamp ±12000; valid only when abe+13000 <u 26001 (`0x3F78A`) |
| angle | `FUN_0003e6d8` (decompile) | θ = gp-0x3608 + **pol**·C(d) + (gp-0x69ca·128)>>7, with gp-0x69ca = base + **pol**·lin(d) | `gp-0x6a00`, d = gp-0x6cc4 − gp-0x69d0 (motor counts) |
| setpoint | `0x29D6A` | `ld.h -0x69ae[gp],r16` | sp = clamp(−4·raw) = 4·θ_sp (no pol) |
| E | `0xC4C00` / `0xC4C02` | `shl 2,r16` ; `sub r26,r16` | E = 16(θ_sp − θ), with r26 = 8θ[n]+8θ[n−1] on entry |
| operand | `0xC4C04` | `ld.h -0x6abe[gp],r26` | r26 := abe (fresh, same 1 kHz pass) |
| guard | `0xC4C08`–`0xC4C14` | `addi 0x32c8,r26,r8` ; `movea 0x6590,r0,r13` ; `cmp r13,r8` ; `bnh` ; `jr 0x2A164` | \|abe\| > 13000 skips the whole PID into Honda's epilogue, so D never forms |
| camera gate | `0xC4C5A`/`0xC4C5C` → `0xC4CC8`/`0xC4CCA` | `cmp r0,r25 ; be` → `mov 0,r16 ; mov 0,r26` | the camera arm gives D = 0 |
| exits | `0xC4CD8 jmp [r6]` → `0x29D7A`; freeze `0xC4CC4 jr 0x29D7E` | — | **r26 = abe on both exits** |
| hold | `0x29D7A`–`0x29EDE` | (113 + 30 instructions listed, dry-run) | **no instruction writes r26** |
| Kd | `0x29E9A`/`0x29EB0`/`0x29EC0`…`0x29EDC`, `0x29EDE` | `ld.hu` knots, interpolation, `zxh r7` | r7 = 48, **unsigned** |
| D | `0x29EE0` `0x29EE2` `0x29EE4` `0x29EEC` `0x29EEE`–`0x29F06` | `mov r26,r8` · `nop` · `mul r7,r8,r0` · `sar 3,r8` · ±DCL clamp | D = clamp(6·abe, ±10240) |
| S | `0x29F18` `0x29F1E` `0x29F24` | `sar 7,r2` · `add r9,r2` · `add r8,r2` | **S = (I>>7) + P + D** |
| out | `0x2A1E6`…`0x2A23C` | `mul r14,r9` ; `sar 15` ; `sxh` · `ld.h 0x7cd0[tp],r7` (5346) · **`ld.b -0x6752[gp],r13`** · **`mulh r7,r13`** · `add r9,r11` · **`mul r13,r11,r0`** · `sar 15` · ±OCL · `st.h r1,-0x6b38[gp]` | T = clamp(((y·ramp>>15)+0)·**pol**·5346>>15, ±3072) |
| forward | `0x2A2C2` / `0x2A2EA` → `FUN_0002b422` → `gp-0x6b4c` | gated copy, clamp, struct sum (TRACE-2026-09-13 §3.2) | same sign |
| aggregator | `FUN_0003aa2c` (decompile) | gp-0x6b94 = … + gp-0x6b4c + … + **gp-0x6bd0** + … | the LKAS lane and **Honda's damper are both plain + addends** |
| Honda damper | `0x3469E cmp r0,r11 ; 0x346A0 ble ; 0x346A2 subr r0,r8` | r11 = gp-0x6abe | **gp-0x6bd0 = −sgn(abe)·m**: the firmware's own damping sign in this frame |

## 3. Integer-exact mirror (`_scratch/dsign-trace/ds03_mirror.py`; cals read LE from the V298 image)

```python
def x_6a56(abe, pol):                                   # FUN_0003f776, slot 4
    if ((abe + 13000) & 0xFFFFFFFF) >= 26001: return 0  # 0x3F786 addi 0x32c8 ; 0x3F78A addi -0x6591 ; bc
    r15 = abe * 48                                      # 0x3F794 mulhi 0x30,r8,r15
    r15 = (r15 * 1159) >> 15                            # 0x3F798 ld.hu 0x713a[tp] (0xC613A=1159) ; 0x3F7A0 mul ; 0x3F7A4 sar 15
    return clamp(pol * r15, -12000, 12000)              # 0x3F79C ld.b -0x6752 ; 0x3F7A6 mul r15,r6 ; clamp -> st.h -0x6a56

def cave_front(sp69ae, r26_fb, abe, r25):               # V298 cave 0xC4C00
    E = (sp69ae << 2) - r26_fb                          # 0xC4C00 shl 2,r16 ; 0xC4C02 sub r26,r16  (no pol)
    r26 = abe                                           # 0xC4C04 ld.h -0x6abe[gp],r26             (no pol)
    if ((r26 + 13000) & 0xFFFFFFFF) > 26000: return SKIP  # 0xC4C08..0xC4C14 -> jr 0x2A164
    if r25 == 0: return 0, 0                            # 0xC4C5A/5C -> 0xC4CC8/CA (camera arm: E'=0, op=0)
    return E, r26                                       # 0xC4CD8 jmp [r6] (freeze exit keeps r26 too)

def D_term(r26):
    r7 = 48 & 0xFFFF                                    # Kd knots 0xE5126 (48 x4) ; 0x29EDE zxh r7 (UNSIGNED)
    r8 = r26                                            # 0x29EE0 mov r26,r8
    #                                                   # 0x29EE2 nop     <- the flip site (5.1)
    r8 = (r8 * r7) >> 3                                 # 0x29EE4 mul r7,r8,r0 ; 0x29EEC sar 3   (= 6*abe, exact)
    return clamp(r8, -10240, 10240)                     # 0x29EE8 ld.hu 0x71b6[tp] ; 0x29EEE..0x29F06

S = (I >> 7) + P + D                                    # 0x29F18 sar 7,r2 ; 0x29F1E add r9,r2 ; 0x29F24 add r8,r2
T = clamp((((y * ramp) >> 15) + 0) * (pol * 5346) >> 15, -3072, 3072)   # 0x2A1E6..0x2A202 ; st.h -0x6b38 @0x2A23C
```

The scenario is the one `ds03` runs: θ = +5.0°, θ_sp = +10.0°, the wheel moving toward the setpoint at +20°/s
(x = +160). Wire fact: sign(x) = sign(dθ/dt). Inverting `0x3F794..0x3F7A6` gives abe = pol·94.

| pol | abe | E | P | D | D vs the approach | T_D (`gp-0x6b38`) | Honda damper sign | T_D / x |
|---|---|---|---|---|---|---|---|---|
| **−1** (this car) | −94 | +800 | + | **−564** | **OPPOSES** | +92 | +1 | **AGREES**, + |
| +1 | +94 | +800 | + | +564 | AIDS | +92 | −1 | DISAGREES, **+** |

The last column is the panel point in §0.6: **T_D/x has the same sign for either pol.**

**Sign rule, from the bytes.** S_D ∝ +abe = pol·k·(dθ/dt). In the driver frame, +S pushes θ up: that is P's
working direction, and P is pol²-invariant. So **D damps iff pol = −1.** In the motor/aggregator frame,
T_D ∝ pol·abe, and Honda damps with −sgn(abe). Same conclusion.

**Why "pol is the only cell".** On the angle side, θ's linear and VGR terms use unsigned cals (`0xC6432` = 900,
`0xC613A` = 1159, `0xC64F2` = 128, byte) and the LERP C. The total slope dθ/d(gp-0x69ca) is +0.962…+1.155
(TRACE-2026-09-30 §2.1). That slope sets the 1.155 frame ratio as a magnitude, not a sign. On the operand side,
nothing touches r26 between `0xC4C04` and `0x29EE4`. One non-sign caveat: while `gp-0x69d0` bleeds after a
re-reference, θ drifts about ±6.2°/s with abe = 0. That is an offset in dθ/dt, not a sign change.
**Wire anchor:** 0x14A packs −gp-0x6a00 and 0x18F packs −gp-0x6a56 (`FUN_00040a50` and `FUN_00055c42`, both
byte-identical in V298). Route 71 shows the two fields co-signed (ADV-unit-scale `us03`, r = +0.997). θ and x each
carry one pol, so the resolver-to-position relation inside the firmware is +1.

## 4. pol: the value, the V98 measurement, and whether it holds on V298

**Writers (raw census `ds02`, positive-controlled; stock = V98 = V298, set difference empty).**
- The 6-byte forms in `FUN_00048a40`: `0x48E68 st.b` (+1, record byte `','`) and `0x48E88 st.b` (−1, byte `0xFA`).
  Ghidra dry-run decodes `8407ed5231ff`. The loads at `0x48E56` and `0x48E76` are the shadow checks.
- `0x490C0 st.b`, the pre-seed in `FUN_000490ac` (caller `0x57EAA`).
- `0x49838` and `0x49844 st.b` in `FUN_000497e6`.
- 56 accesses in all: **51 R / 5 W**, the V98 GATE-1 figure exactly. V298 adds **no** access. V98 adds one,
  `0xC4B9C ld.b` (its rung).

**Value, boot.** The records are `0x1180: 6c 55 10 54 2c …` and `0x14C0: a6 71 10 54 fa …` (stock dump). The
parser walks them in ascending order and the last write wins, so pol = −1. This is the kit record, and the decodes
above re-confirm it.

🛑 **NEW: pol is re-asserted at run time.** Ghidra dry-run at `0x22C40`–`0x22C46` shows
`cmp r0,r26 ; be ; mov 5,r6 ; jarl 0x497e6,lp` (bytes `82 ff a0 6b`). This sits in the slot-3 body (slot table
`0xBB9B0`, entry `0x22B24`, priority 3), with r26 = (1<<state) & `0x830` at `0x22BD2`. The raw jarl scan finds the
same call; control `0x22522`→`0x28EA6` passed. `FUN_000497e6` (decompile): when pol equals its shadow
`gp-0x4c2d`, it sets pol = (`*(gp-0x34b8)+4` == `','`) ? +1 : **−1**. The pointer is the last type-0x54 record,
`0x14C0`, whose byte is `0xFA`. **So pol is re-written to −1 on every slot-3 pass in the normal state.** Any
non-comma byte also gives −1. Ghidra's "zero callers" came from the missing function at `0x22B24`, so it was
a tool zero, not a verified one. [BELIEF from kit memory: slot 3 is 200 Hz, and `gp-0x67fa` sits in {11}.]

**What V98 measured.** The V98 cave in the 100 Hz 0x14A builder (hook `0x55C0E`) hand-decodes at
`0xC4B9C`–`0xC4BA8` as `ld.b -0x6752[gp],r6 ; addi -0x80,r6,r0 ; bnh +4 ; add 8,r7`. That sets b3 = (pol ≥ 0).
The hand decode confirms the framed claim; the encodings were cross-checked against Ghidra decodes of `b305`,
`07066f9a` and `4242` in this session. The **duty was 0.0000 on 17,983 frames** (route `0x81`), and V99
reproduced it on 12,005 frames. Only −1 is negative among the values any writer stores, so **pol = −1 in RAM at
run time.** [EVIDENCE: kit record for the duty figures, hand decode for the rung.]

**Still valid on V298? Yes.** EVIDENCE:
- The cell is the same, and so are the instructions that address it.
- `FUN_00048a40`, `FUN_000490ac`, `FUN_000497e6` and the slot-3 body `0x22B24..0x22CA0` are byte-identical in
  stock, V98 and V298 (`ds01`).
- The writer census is unchanged (`ds02`).
- The records are below `0x13000`. The V298 `.rwd` covers `0x13000`–`0x100000` (build script `START`/`END`), and
  no kit build writes lower. The plain snapshots read `0xFF` there; that is a snapshot artifact.
Residual [BELIEF]: a checksum abort between `0x1180` and `0x14C0` would leave the +1 pre-seed. The V98 run-time
read excludes that on this car's flash, and the re-assert writes −1 regardless.

⭐ **On-V298 confirmation without a new probe.** T_P = pol·k·P (§3), and the drive read's replay hard-codes
pol = −1 (`components()`: `Tz = -(…)`). So **a POSITIVE absolute structural `a`** (c_P / c_P,pred > 0 per band)
**on route 79 is a direct measurement of pol = −1 on the V298 image.** The ratio c_meas/c_raw is pol-blind and
cannot do this.

## 5. Edits (design inputs only — nothing built)

### 5.1 Minimal D flip: one instruction, 2 B, in place
| addr | V298 bytes | new | before | after |
|---|---|---|---|---|
| `0x29EE2` | `00 00` | `80 41` | `nop` | `subr r0,r8` (r8 := −r8 = −abe) |

- **Encoding:** Ghidra decodes `8041` as `subr r0,r8` at `0x29F06` in this same image.
- **Flags:** `subr` sets PSW, but `mul` (`0x29EE4`) and `ld.hu` (`0x29EE8`) do not consume flags, and
  `sar`/`cmp` (`0x29EEC`/`0x29EEE`) rewrite them before `ble` (`0x29EF0`). Stock had a flag-setting
  `sub r27,r8` in this slot.
- **Arithmetic:** exact. |abe| ≤ 13000 after the guard, and 48·a/8 = 6a has no floor asymmetry.
- **CRC:** main block, so recompute the `0xC4FFC` trailer.
- 🛑 **On this car it makes D AIDING** (pol = −1). Fly it only if the panel shows pol = +1 at run time, which
  every line in §4 contradicts.
- **No cal-only flip exists.** Kd is `ld.hu` plus `zxh r7` (`0x29EDE`), so a cal value of −48 reads as 65488 and
  rails D. The output cell `0xC6CD0` would flip P as well.
- The alternative `0x29EDE c7 00 → 80 39` (`subr r0,r7`) drops Honda's `zxh` guard. Not preferred.

### 5.2 Pol-invariant D: multiply the operand by pol once, so D meets pol twice
Insert at the guard's pass target `0xC4C18`, before `ld.hu -0x6a5e[gp],r8`. r8 is dead there; the next
instruction overwrites it.

```
04 47 ae 98   ld.b  -0x6752[gp], r8   ; pol (control: 0x2A1F2 04 6f ae 98 = r13 form)
e8 d0         mulh  r8, r26           ; r26 = pol*abe (16x16 exact: |abe| <= 13000, pol in {-1,+1})
80 d1         subr  r0, r26           ; r26 = -pol*abe = the driver-frame rate (sign of -x, fresh 1 kHz)
```

**8 B, cave 260 → 268 B** (ends about `0xC4D0C`, well short of `0xC4FF0`). The result is
D = 6·(−pol)·abe and T_D ∝ pol·(−pol)·abe = −abe for **any** pol, which is Honda's damper sign. On this car
(pol = −1) −pol·abe = abe, so the D values are **identical to V298's, sample for sample**.

| check | result |
|---|---|
| encodings | the rules are checked against Ghidra decodes of `046fae98` (`ld.b -0x6752,gp,r13`) and `e768` (`mulh r7,r13`) |
| pol range | the lane's entry test requires pol ∈ {−1,+1} (decompile `(char)pol+1U < 3 && pol != 0`) |
| other r26 uses | the cave uses r26 nowhere else after `0xC4C08` |
| flags | `subr` sets flags; the next flag consumer `bh` (`0xC4C28`) follows its own `cmp` |
| GATE 1 | no new RAM write; pol is already read by this function at `0x2A1F2` |

🛑 **This needs the two-pass relink, not a byte splice.** The table pointer `mov 0xC4CDA,r9` (`0xC4C1C`) moves
by +8, and the PC-relative `jr 0x29D7E` at `0xC4CC4` and `0xC4CD4` need new displacements. That is the
stale-pointer trap the V298 build docstring describes.

The held, pol-free alternative is C3-rev2-F: `0x29EDE subr r0,r7` + `0x29EE0 ld.h -0x6a56[gp],r8`. It costs the
100 Hz hold.

## 6. Verification record

| item | method | result |
|---|---|---|
| Ghidra DB = V298 image | `read_memory` vs Python at `0x29ED0`/`0xC4C00` | identical |
| code diff V298 vs stock | `ds01`, [0x13000, 0xC0000) | the 8 V298 sites plus inherited edits; **no run inside any sign-chain function** |
| byte identity, stock = V98 = V298 | `ds01` | `FUN_00048a40/490ac/497e6`, `FUN_00041464`, `FUN_0003f776`, `FUN_0003bd7c`, `FUN_00068f52/68fbe`, `FUN_0003e6d8/3e600`, `FUN_00055c42`, `FUN_00040a50`, `FUN_00034350`, slot 3, the `0x2A2BC..` forward. The output tail differs only at `0x2A1F0` (5346 repoint, also present in V98) |
| gp-0x6abe census | `ds02` | 28 stock accesses, 4 stores (all `FUN_00041464`). The 6-byte candidates `0x59A30`… are `ld.h` (hw2 nibble 7; Ghidra decodes `0x59A30`). V298 adds only `0xC4C04 ld.h` |
| callers | raw jarl scan (opcode 0x1E, even target, control `0x22522`) | `0x41464`←`0x22200` · `0x3F776`←`0x22DE2` · `0x48A40`←`0x4911C` · `0x490AC`←`0x57EAA` · **`0x497E6`←`0x22C46`** |
| aggregator signs | `decompile_function 0x3aa2c` | `+gp-0x6b4c`, `+gp-0x6bd0` |

**Ghidra:** `decompile_function` `0x28ea6` (V298), `0x3f776`/`0x3e6d8`/`0x497e6`/`0x3aa2c` (stock); dry-run
disassembly of `0x29d6a–0x29f40`, `0x2a1e6–0x2a240`, `0xc4c00–0xc4cda` (V298) and `0x3f776`, `0x34690`,
`0x48e50`, `0x59a2c`, `0x22b24–0x22c60` (stock).

## 7. Open — what remains unverified, and the next step

1. **pol on V298, on V298's own wire.** Read the **absolute sign** of the structural `a` per band on route 79
   (not the ratio). Positive means pol = −1 is measured, closing H-pol for this image.
2. A mixed-sign c_D is **not explained by pol** (§0.6). Candidates the panel owns: e/ω collinearity in closed
   loop, frozen-I misspecification (the drive read's own docstring already flags the ratio-form c_D as biased on
   the correct build), the ~5 Hz output lag `0xC63EC`, and the 100 Hz hold of x standing in for 1 kHz abe in the
   replay.
3. Slot-3 rate and the `gp-0x67fa` ∈ {11} state for the re-assert: taken from kit memory, not re-derived here.
4. Kit-memory errata found and **not edited** (the operator decides):
   - `reference_accord_gp6752_resolved_negative_one_and_pid_polarity_reversal.md` (agent memory) says
     `FUN_000497e6` has "zero callers". It is called from `0x22C46`.
   - The same file and the DESIGN H-pol rows call pol "boot-static". It is re-asserted on every slot-3 pass.
   - DESIGN C3-rev2 §7 calls "c_D aiding" "the pol check". At the tap it is pol-blind.

**Proposed memory** (`reference_*`, not written, per the brief): the content of §0 items 2, 4, 5 and 6.
