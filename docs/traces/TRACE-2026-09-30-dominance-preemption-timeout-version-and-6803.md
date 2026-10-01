# TRACE 2026-09-30: B2 dominance, 0xE4 preemption, 0xE4 timeout, the version string, and `gp-0x6803 == 2`

Agent: firmware-codepath-tracer (subagent). Programs: Ghidra `code.bin` (stock) and the V294 program (code-identical to
V295 except cal `0xC63EA` + CRC). Python LE byte scans on stock and the V295 image.
`gp = 0xFEDF8000`, `tp = 0xBF000`.

Scratch: `_scratch/angle_loop/dpt/`. It holds:
- `DptCfg.java`: the read-only Ghidra CFG/def-use script used for §1.
- `jarlscan.py`: a raw Format-V scanner, controlled by finding `0x22522 → FUN_00028ea6`.
- `e4_timeout_mirror.py`: the byte-faithful timeout mirror for §3.
- `dpt_common.py`.

Reused: `_scratch/angle_loop/sentinel_gates/sg_scan.py` (the gp/tp scanner with 4-byte and 6-byte forms) and
`dec_28ea6_v294.c`.

This trace feeds the C0 design (`docs/specs/design/DESIGN-ANGLE-LOOP-C0-2026-09-30.md`) and its three refuter reports.

## Verdicts

| # | question | verdict | grade |
|---|---|---|---|
| 1 | Does r27 hold bVar2 (from `0x2913A`) at `0x29A50` on every path? | **YES.** `0x2913A` dominates `0x29A50`. It is the only r27 def that reaches `0x29A50`; the incoming value does not. Both callees in between preserve r27. No external branch enters the region. | EVIDENCE |
| 1b | Is r8 dead after the guard? | **YES, on both paths.** From `0x2A164` (skip) and from `0x29A60` (run), r8's first touch is always a write. r27 is also dead after `0x29A5C`/`0x29A60`, so B2 consumes bVar2's last live use. | EVIDENCE |
| 2 | Can the 0xE4 RX callback preempt `FUN_00028ea6` between the request latch and the sp load at `0x29D6A`? | **NO. The window is 0 ticks.** The callback runs in RTOS slot 3 (prio 3, 200 Hz); the PID runs in slot 0 (prio 6, the highest). The kernel switches tasks only at explicit checkpoints, and none lies inside the RX dispatch. Every writer of `gp-0x69ae`/`-0x6805`/`-0x6803` is in `FUN_00052676`. | EVIDENCE |
| 3 | What happens when 0xE4 stops arriving? | **Timeout sentinel at 510–514 ms** after the last frame (500 ms cal `0xC626C`, 1 ms timestamp). It writes `gp-0x6805 = 0xFF`, `gp-0x69ae = 0x7FFF` and re-asserts both every 5 ms. **Until then the last request and setpoint are HELD.** Under C0 that means the wheel tracks the last θ_sp for about 0.5 s. | EVIDENCE |
| 4 | Version string: who reads it, and is editing it safe? | **The application reads `0x13100` only in the UDS F181 handler** (14 bytes + 2 NULs). F180 reads `0x1310E`. No bootloader-region code references `0x13100..0x13127`. The second copy (`0x14117`) sits inside a 40-byte NVM ROM-default block with no field-wise reader. Editing `0x1310D` is safe for the ECU (main-block CRC recompute only). **The kit flasher's part-number gate and the revert path both need the new string in the `.rwd` `/` header.** The fork must also fingerprint it. | EVIDENCE (ECU side); BELIEF (fork fingerprint) |
| 5 | What changes when the fork sends `gp-0x6803 == 2`? | **Two things.** (a) The engage SM takes the direction-2 path: ramp-in 0.10 s (`0xC63FC` = 328) instead of 0.99 s (`0xC63F8` = 33); ramp-out 0.50 s (`0xC63FA` = 66) instead of 2.05 s (`0xC63F6` = 16). (b) `r25` flips both driver-torque arms: setpoint taper `0xCB8B4`/`0xCB924` → cliff `0xCBA04`/`0xCBA74` (inert in C0, bypassed by E4); post-PID fade `0xCBBC4` → `0xCBAE4` (live in C0). Everything else is unchanged or identical-valued. | EVIDENCE |

---

## 1. Dominance of `0x2913A` over `0x29A50` and register liveness

**Entry point.** `FUN_00028ea6` body `[0x28EA6, 0x2A30E)`, V294 program. Stock differs inside this body only at
`0x28FA4`, `0x29D76` and `0x2A1F0/1`; a Python diff confirms this. None of those is on a path before `0x29A50`.

**Method.** `DptCfg.java` builds an instruction-level graph from Ghidra's own flow types (calls fall through) and
takes register def/use from p-code; pair registers like `r26r27` are split into halves. It then runs BFS reachability.

**Coverage.** 1,874 instructions, **0 undefined halfwords**, **0 computed non-terminal flows**. The single terminal is
`dispose` at `0x2A30A`.

```
r27 writers: 2913a[mov r8,r27] 29e7e[cmovnc r16,r8,r27] 29f2e[mov r8,r27] 2a0e4[mov 0x0,r27]
             2a168[mov 0x0,r27] 2a30a[dispose …r27…]
entry->0x29A50 reachable avoiding 0x2913A = false              <- 0x2913A DOMINATES 0x29A50
r27 @29a50 <- defs: 2913a[mov r8,r27]   incoming-value-reaches=false
r8  from 29a60 reads-before-write: (none)  first-writes: 29a78 2a0ca 2a1c2 2a236  epilogue_reached=false
r8  from 2a164 reads-before-write: (none)  first-writes: 2a1c2[mov r9,r8] 2a236[setfe r8]
r27 from 29a5c reads-before-write: (none)  first-writes: 2a168[mov 0x0,r27]
r27 from 29a60 reads-before-write: (none)  first-writes: 2a168 2a0e4 29e7e
```

**What r27 holds** (dry-run disassembly, V294):

```
0x29132 setfc r8 ; 0x29136 br 0x2913a ; 0x29138 mov 0x0,r8 ; 0x2913a mov r8,r27
```

So r27 ∈ {0, 1}.

**Calls on a `0x2913A → 0x29A50` path.** There are two.
- `0x2913E jarl FUN_00046ea6`: its full listing touches only r6/r8/r10/r13/r15 and never r27.
- `0x291CA jarl FUN_00016de6`: it does write r27, but it saves r27 in `prepare {r20..r24,r26..r29,lp}` at `0x16DE6`. Its
  single exit is `dispose` at `0x16F5A`; the early exit `jr 0x16f5a` lands on the same dispose. So r27 is restored.

**External entries.** A raw Format-V and Format-III scan of the whole image, stock and V295, looked for branches into
`[0x2913C, 0x29A50]` from outside the body.
- Control: the scanner finds `0x22522 → 0x28EA6`.
- It returns 3 hits: `0xD86C6`, `0xD86F2`, `0xD871E`. **All three are excluded.** They sit inside a calibration LERP
  table: monotone X `0x2d, 0x86, 0x101, 0x1de, 0x30c, 0x507, 0x7d8, 0xfb5, 0x1036`, repeating at stride `0x2C`. Ghidra
  has no function there.

**C0 edits.** No C0 edit changes this. E1 and E2 sit before `0x29A50` but are a load and an add, with no flow change and
no r27 write. A2 retargets `0x29A56` to `0x29A5C`, which is inside the guard. H, E4 and E5 lie after the guard.

⇒ **B2 `cmovne r0,r27,r8` at `0x29A50` yields r8 = (request == 1) ? bVar2 : 0 on every path. [EVIDENCE]**

On the run path under A2+B2, r8 = 1 exactly, a subset of stock's {0, 1}. That would make it harmless even if read; it
is not read.

⚠ **A new constraint the design must carry.** `r25 = (gp-0x6803 == 2)` is set at `0x29A82` (`setfe r25`). It is read
at `0x29B72`, `0x29C4E`, `0x29FDE` and `0x2A0AC`, and `0x29A82` is its only reaching def at each. **r25 is therefore
live across the hook H (`0x29D76`), so the cave must not touch r25.** It is callee-saved by ABI. The hook trace's live
list at `0x29D76` already includes r25.

---

## 2. Preemption: where the 0xE4 callback runs and at what priority

### 2.1 The call chain (EVIDENCE: raw jarl scan, controlled; Ghidra disassembly)

```
TCB slot 3 (0xBB9B0: attr 0x00040307 -> prio byte +5 = 3, entry FUN_00022b24)
  0x22b7e jarl 0x521dc   (r6 = 1)           [only caller: raw scan]
    0x521dc..0x522fe: loop idx 0..18 over descriptor recs at tp-0x3abc = 0xBB544 + idx*0x20;
       calls FUN_000520d0(idx) iff rec+0x08 == 1 && (rec+0x18 & (1 << gp-0x334a)) != 0
       (idx 7 = 0xE4: +0x08 = 1, +0x18 = 0x0F -> every pass)   0x522c2 jarl 0x520d0
    FUN_000520d0(7): new frame?  -> FUN_00054520 (timers reset), checksum FUN_000541d8, counter FUN_0005413a,
                                    then 0x52176 jmp [r20] = handler(+0x1c) = FUN_00052676(status)
                     no frame    -> 0x5217c state = FUN_0005550a(7); 0x521ac FUN_000542a6(7) (timeout monitor);
                                    0x521ca jmp [r28] = FUN_00052676(OLD state) if old==4 || monitor==1
```

**Slot 3 rate.** The dispatcher `FUN_00014be4` calls `FUN_000861e0(3)` (syscall 8) when `gp-0x4304 % 5 == 2`. The
syscall-8 handler `0x837c0` computes the TCB as `idx*0x30 + [tp-0x3814]`, where `[0xBB7EC] = 0xBB920`; index 3 is
`0xBB9B0`. The tick is TAUJ1I2 at 1 kHz (kit record). **Slot 3 therefore runs at 200 Hz.**

### 2.2 Priority semantics (EVIDENCE: kernel disassembly and decompile)

**ActivateTask.** `FUN_00083854(TCB)` sets the ctx state to 2 and copies the TCB+5 byte (priority) into ctx+0xc. It
then calls `FUN_000838c6`, which walks the ready list `gp-0xe90` while `new.prio <= node.prio` and inserts after them.
The list is sorted **descending**, and the head is next to run. ⇒ **A larger number means a higher priority.**

**Schedule** (syscall 5 = `0x8412c`). At `0x841a2` it executes `cmp r15,r7 ; bnc skip`: a switch happens only if the
ready head's priority is strictly greater than the running TCB's base priority (`sld.bu 0x5[ep]`).

**Task priorities** (TCB+5): slot0 `FUN_0002214a` **6**, slot1 4, slot2 5 (stub), slot3 **3**, slot4 2, slot5 1,
idle 0. ⇒ **No task can displace slot 0. Slot 3 cannot preempt the PID.**

### 2.3 Switches happen only at checkpoints (EVIDENCE)

**The ISR does not dispatch.** The EI trampoline `FUN_0001492a` handles EIIC 0x340 (TAUJ1I2) by storing
`gp-0x42fc = 1` and then `eiret`s, with no kernel call. It dispatches only 0x970, 0x600, 0x340, 0x470, 0x110, 0x100
and 0xF0; any other EIIC goes to the fault path `0x14810`. **There is no CAN interrupt vector, so CAN RX is polled.**

**Where checkpoints are.** All 82 `jarl 0x14be4` sites (raw scan) lie in task bodies:
- `0x14d02..0x14d4a`: idle loop
- `0x221f4`, `0x22494`: slot 0
- `0x22a68..0x23844`: slots 1–5
- `0x86252`: kernel

The syscall-5 wrapper `0x861e6` has exactly 1 caller (`0x14c54`, inside `FUN_00014be4`). **There are zero checkpoints
in `0x50000..0x58000` or in any RX callee.** The `caxi` scan likewise finds none in that range.

**Writers of the PID's inputs.**
- `gp-0x69ae`: `0x5268c`, `0x526f2`, `0x52726`, `0x527c6`
- `gp-0x6805`: `0x5269c`, `0x52706`, `0x52736`, `0x527ac`
- `gp-0x6803`: `0x526ac`, `0x526f8`, `0x52732`, `0x527cc`

All are in `FUN_00052676`, found by `sg_scan.py` with both encodings. The sentinel trace's LE32/`movea` indirect scan
found no other writer.

**Result.** Each handler invocation is atomic with respect to slot 0, and slot 0 runs to completion against slot 3.
**The window between the request latch and `0x29D6A` is 0 ticks.** The design's "one-tick sentinel impulse"
preemption hazard does not exist. **[EVIDENCE]**

**Side effect (BELIEF, not measured).** Because switching is cooperative at checkpoints, a slot-0 activation that fires
while slot 3 is inside `0x521dc` is delayed until slot 3's next checkpoint (`0x22b8a`). That is PID-tick jitter, not a
torn read.

**Not traced** (non-blocking): the context that writes the RX buffer `0xFEDF6BD8` and the flags at `gp-0x16a4`. The flag
setter `FUN_0002141c` is reached only via the pointer table `0xB74A0`. Since no CAN EI vector exists, that context is a
task, and it cannot run inside `FUN_00052676`.

---

## 3. 0xE4 timeout

### 3.1 The monitor (EVIDENCE: decompiles of `FUN_000520d0`, `FUN_000542a6`, `FUN_00054520`, `FUN_0005550a`; disassembly of `0x520d0`)

**Per-message record.** It lives at `gp-0x32cc + 7*0x2c = 0xFEDF4E68`. Its `.data` boot image is at flash `0x89F18`,
under the copy-loop mapping flash `0x86260..0x8AB18` ↔ RAM `0xFEDF11B0..0xFEDF5A68`:

```
6e 62 0c 00 11 00 53 00 65 00 00 00 00 00 00 00 00 00 ff 00 04 00 00 00 01 00 00 00 00 00 00 00 01 00 00 00 00 00 00 00 6c 62 0c 00
```

| field | value | meaning |
|---|---|---|
| +0x00 | ptr `0xC626E` = **60000** | confirmed-timeout accumulator threshold |
| +0x08 | DTC id `0x0065` | |
| +0x14 | boot state **4** | never received |
| +0x18 | **1** | debounce divisor class, `tp-0x3835+1` = **10** |
| +0x28 | ptr `0xC626C` = **500** | pending-timeout threshold |

**The clock.** `gp-0x3e54` is incremented by `0x2217a add 0x1,r7` / `0x22182 st.h` at the start of slot 0, so its unit is
**1 ms**. It is 16-bit and wraps safely.

**Byte-faithful mirror** (`e4_timeout_mirror.py`; condensed):

```python
def monitor(r, now, mon_en=1, g6a98=0):          # FUN_000542a6(7)
    if r.start == 0: r.start = r.last = now      # timer starts at the first SILENT poll
    el = (now - r.start) & 0xFFFF
    if mon_en == 1 and r.state in (1, 5): r.acc += (now - r.last) & 0xFFFF
    r.last = now
    if 60000 <= r.acc or r.state == 1 or (g6a98 != 0 and 200 <= el):
        r.state = 1; return 1                    # confirmed
    if el < 500: return 0
    r.state = 5; return 1                        # pending  -> handler gets called
# FUN_000520d0: old = state (0x5217c, read BEFORE the monitor); fire = monitor(...)  (0x521ac)
#               if old == 4 or fire: FUN_00052676(old)                          (0x521ca)
```

**Timeline.**
1. The poll that crosses 500 ms sets state 5 but calls the handler with the **old** state 0. That re-decodes the stale
   buffer, so the request stays 1.
2. The next poll calls `handler(5)`. That is the `param ∈ {1,2,3,5,6,7}` branch: `gp-0x6805 := 0xFF`,
   `gp-0x69ae := 0x7FFF`, `gp-0x6803/6804/6802/6876/67f3 := 0xFF`, plus `FUN_0005462c(7,5)` (DTC `0x65`; the sentinel
   trace showed its reaction dword is 0).
3. The handler re-asserts the sentinel every 5 ms while frames stay absent.

**Measured on the mirror.** Over all 10 frame phases, **`gp-0x6805 = 0xFF` arrives 510–514 ms after the last frame**. The
PID sees it at the next slot-0 tick, ≤ 1 ms later. A2 then skips the PID; the output lag decays in about 0.1 s.

**The `gp-0x6a98 ≠ 0` variant.** If `gp-0x6a98` is non-zero, the timeout confirms at **200 ms** (`0xC6262`). That cell is
written `0xA5A5` by `FUN_0001b02e` and copied from `gp+0x63e8` by `FUN_00021b98`. Its role and its on-car value are
**BELIEF / not measured**; it looks like a special mode.

**Recovery.** The next frame resets the record (`FUN_00054520`) and decodes immediately. The sentinel's ST = 3 is not
sticky (sentinel trace §2).

### 3.2 Consequence for C0 (EVIDENCE for the hold; BELIEF for the fork and panda behaviour)

For **about 0.5 s after a fork or controls crash, the firmware still sees request = 1 and the last θ_sp**. Under C0 the
angle PID keeps holding the wheel at the last commanded angle for that half second, then releases. Stock already does the
same with the last rate demand.

If the panda falls back to relay pass-through, the camera's 0xE4 (request 0 with stock LKAS off) arrives instead. A2 then
skips on the first such frame, within ≤ 10 ms, and no timeout occurs. The panda's silent-mode timing is **BELIEF** and is
fork/panda-version dependent.

### 3.3 Bonus finding (EVIDENCE, decompile only): corrupt frames are accepted for up to 49 frames

`FUN_000541d8` (checksum, nibble `byte4 & 0xF` vs `FUN_00057b24`) and `FUN_0005413a` (counter, `(byte4 & 0x3F) >> 4`)
debounce with `FUN_000540d0` / `FUN_00054066`.

While the consecutive-error count is below `500/10 = 50`, they return 0. **`FUN_00052676(0)` then decodes the failing
frame as valid.** State 7 (checksum) or 6 (counter), and with it the sentinel, comes only at count ≥ 50. Confirmation
comes at 6000. Each count resets on a good frame.

**For the safety refuter.** The ECU does not reject single bad-checksum or bad-counter 0xE4 frames. Not disassembly-
confirmed; next step: `disassemble_function 0x540d0`.

---

## 4. The part-number / version string

### 4.1 Bytes

| addr | stock | every modded image (V15B on, V295 included) |
|---|---|---|
| `0x13100..0x1310D` | `39990-TVA-A160` | `39990-TVA,A160` (`0x13109`: `2d → 2c`) |
| `0x1310E..0x1311B` | `39990-TVA-A110` | unchanged |
| `0x14117..0x14124` | `39990-TVA-A160` | `39990-TVA,A160` (`0x14120`: `2d → 2c`) |

The stock vs V295 diff confirms this; the two changed bytes are `0x13109` and `0x14120`.

### 4.2 Readers

Three methods scanned the whole 1 MB image, bootloader region included: LE32 literals, `mov imm32` (6-byte), and
`movhi`/`movea|addi` pairs. Targets were `0x13100..0x13127` and `0x14100..0x1412F`. Control: the scan finds the known
`0x4F70C`.

**The `0x13100` region.**
- `0x4F70C mov 0x13100,r6` in `FUN_0004f6fa`: the **DID 0xF181 handler**. Its DID table record is at `0xB7A0C` (`81 f1 10 00`).
  It copies 14 bytes, then explicitly zeroes bytes +0xE/+0xF, giving a 16-byte payload.
- `0x4F6E6 mov 0x1310E,r6` in `FUN_0004f6d6`: **DID 0xF180** (`39990-TVA-A110`).
- **No other reader.** In particular **no bootloader-region code references `0x13100..0x13127`**; the bootloader carries
  its own strings at `0x9011`.

**The `0x14100` region.**
- `0x5BC4` and `0x5C9E` (`FUN_00005baa` / `FUN_00005c86`) read `0x14102 + 6i` and `0x14104 + 6i`. The index i comes from
  `FUN_00005ed0`, a binary search over keys at `0x14100`, stride 6, bounded by `[key0 = 0, u16(0x141CC) = 0]`. **Only
  i = 0 is ever valid**, so only `0x14100..0x14105` is read, never the PN bytes from `0x14107`.
- `0x8AF68`/`0x8AF64` is an NVM block descriptor: len `0x28`, RAM `0xFEDFE000`, ROM default `0x14100`. The PN copy is
  part of that 40-byte default image.
- gp-relative readers of its RAM image (`gp+0x6000..0x6027`) exist only at `+0x6000..+0x6008` (`0x4F0B0..0x4F1DE`).
- Literal references to `0xFEDFE000` all address the block base, at `0x1BE4C/8A/EA`, `0x88D4C` and `0x8AD58`.
- ⇒ **The PN copy at `0x14117` is never read field-wise.** It is BELIEF that it is ever copied out at all; that would
  happen only on an NVM-invalid default load.

**Wire evidence.** `flashing-2020accord/flashing-dry-run-20260710.txt` records the response
`62 f1 81 39 39 39 39 30 2d 54 56 41 2c 41 31 36 30 00 00`. Kit record `analysis-2020accord/lib/route_build_registry.py`:
every modded route reports `fw='39990-TVA,A160'`. ⇒ **openpilot's EPS fwVersion is the 14 bytes at `0x13100` plus
2 NULs.**

### 4.3 Is editing the last character safe?

**ECU side: yes.** Example: `0x1310D` `30 → 31`, giving `39990-TVA,A161`.
- It changes only the F181 payload.
- It sits inside the main CRC block `[0x13000, 0xC4FFC)`, which every build already recomputes.
- No bootloader or runtime plausibility reader exists.

`0x14124` (the NVM-default copy) can be left alone or kept consistent; nothing reads it field-wise. **[EVIDENCE]**

**Flash path: two traps** (EVIDENCE: `flashing-2020accord/eps-update-tva.py`). `app_id_matches_part` compares the
**running** ECU's F181 against the `.rwd`'s `/` header list by exact or prefix match. NULs are stripped first.
- (a) The **new** build's `.rwd` header must list the string **currently** on the car (`39990-TVA,A160`).
- (b) **Every revert `.rwd` (V295, V294, …) must list the new string.** Today they list `['39990-TVA-A110','39990-TVA,A160']`.
  After flashing `,A161`, a V295 revert is **refused by the gate** unless re-headered, or unless
  `--force-part-mismatch` is passed, which the drive card forbids.

Both strings are 14 characters, so neither is a prefix of the other. A header entry `39990-TVA,A16` would match both.

**Fork side: BELIEF, not traced here.** The fork must accept the new fwVersion, or the car may fail to fingerprint
(no engage). Check how it currently accepts the non-upstream `,A160` before choosing the character.

---

## 5. What `gp-0x6803 == 2` changes

`gp-0x6803` is 0xE4 byte 2, bits 3:2 (`0x526ac`). A fork sending `SET_ME_X00 = 0x08` alongside the request bit sets it
to 2.

**Live readers.**
- In the engage SM: `0x29376`, `0x29436`, `0x294BC`, `0x29514`, `0x295B4`, `0x29632`, `0x29666`, `0x296A2`.
- The arm flag: `0x29A74 → 0x29A80 cmp 2 ; 0x29A82 setfe r25`.
- `0x4E87E`: the diagnostic record.

**Dead readers.** `0x2A552..0x2A822` (`FUN_0002a508`) and `0x2A976` (the uncalled twin island).

### 5.1 Engage / ramp state machine `gp-0x3d38` (EVIDENCE: decompile, `dec_28ea6_v294.c` lines on `gp-0x3d38`)

| | openpilot today (`6803 = 0`) | fork sends 2 |
|---|---|---|
| idle → engage (req 1, ST < 3) | state 3, `gp-0x679f = 1`, ramp += **`0xC63F8` = 33**/tick → **0.99 s** to `0x8000` → state 2 | state 6, `gp-0x679f = 2`, **`gp-0x679e = 1`**, ramp += **`0xC63FC` = 328**/tick → **0.10 s** → state 7 (`679f = 4`) |
| request drop (req 0, field held) | state 4, ramp −= **`0xC63F6` = 16** → **2.05 s** | state 8 (`679f = 6`), ramp −= **`0xC63FA` = 66** → **0.50 s** |
| ST = 3 (sentinel, `67fe ≠ 2`, speed window …) | state 4, 2.05 s | state 8, 0.50 s |
| ST = 7/4, or `6803 == 1 ∧ req 0` | state 5, −`0xC63F4` = 328 → 0.1 s | same |

⚠ **The fork must keep sending 2 when it drops the request.** With req 0 and field 0, state 7 falls to state 4, the
2.05 s path.

`gp-0x679e = 1` selects `0xC63DA`/`0xC63DE` instead of `0xC63DC`/`0xC63E0` for `gp-0x697e`/`gp-0x697c`. All four cals
are 1024 (stock and V295), so **this has no effect**.

`gp-0x679f` has 8 live writers and **no gp-relative reader** (scan). It looks report-only.

Under A2 the ramp-out rate only paces the ramp multiplier on an output that is already decaying. **The ramp-in matters.**
At 0.10 s instead of 0.99 s, it shrinks the window behind the friction refuter's item (5), engage droop and I wind-up
during ramp-in. That is a candidate zero-byte mitigation; its effect is BELIEF (needs the harness).

### 5.2 Driver-torque arms switched by r25 (EVIDENCE: reaching-defs §1; slot-7 records byte-read, stock == V295)

The key is `x = gp-0x682f = |tq|>>5`.

| stage | `6803 ≠ 2` (live today) | `6803 == 2` |
|---|---|---|
| setpoint taper, same sign | `0xCB924[7]→0xE52FC` X 32,42,80,112 / Y 255,255,255,0 | `0xCBA74[7]→0xE547C` X 70,72,78,80 / Y 254,234,12,0 |
| setpoint taper, opposite sign | `0xCB8B4[7]→0xE5284` X 32,38,80,112 / Y 255,255,255,0 | `0xCBA04[7]→0xE5404` X 70,72,78,80 / Y 254,234,12,0 |
| post-PID grab factor (key `gp-0x6830`) | `0xCBC34[7]→0xE56F4` X 0,3,6,8,10,20 / Y 255×5,205 | `0xCBB54[7]→0xE55A4`: **identical values** |
| post-PID torque fade | `0xCBBC4[7]→0xE564C` X 16,26,38,48,64,96 / Y 255,243,218,179,77,77 | `0xCBAE4[7]→0xE54FC` X 24,45,64,80,96,112 / Y 255,205,164,125,90,51 |

The setpoint taper is selected at `0x29B72`/`0x29C4E`; the post-PID fade at `0x29FDE`/`0x2A0AC`.

**Integer LERP, as in the decompile:**

| raw \|tq\| | 512 | 1024 | 1536 | 2048 | 2560 | 3072 | ≥3584 |
|---|---|---|---|---|---|---|---|
| post fade, 6803 = 0 | 255 | 231 | 179 | **77** | 77 | 77 | 77 |
| post fade, 6803 = 2 | 255 | 236 | 199 | **164** | 125 | 90 | 51 |
| setpoint taper, 6803 = 0 (same sign) | 255 | 255 | 255 | 255 | 255 | 128 | 0 |
| setpoint taper, 6803 = 2 | 254 | 254 | 254 | 254 | **0** (cliff from 2240) | 0 | 0 |

**For C0.** E4 bypasses the setpoint-stage taper (hook trace: "Removed by the setpoint edit"). Its only remaining
consumer is the Kp/Kd schedule axis, which is flat in C0, so **that arm is inert**. That the consumer is the axis only
is the hook trace's EVIDENCE, not re-derived here.

**The post-PID fade arm is live in C0.** With 2, the mid-band hand fade is **weaker**: 0.64 vs 0.30 of full at
2048 raw. It is stronger only above about 3240 raw (floor 0.20 vs 0.30). **So 2 raises lane authority against a
hand everywhere from about 600 to 3240 raw**, by up to ×2.1 at 2048 raw. It must enter the friction refuter's
light- and heavy-hand override sims before 2 is adopted.

**Not changed by 2:** `gp-0x6802` (bits 1:0), `gp-0x6804` (bit 6), `gp-0x6805`, the sign-hold gate, the PID gains and
clamps, and the output lag.

**Camera interlock arithmetic** (kit record, not re-measured): the stock camera sends `byte2 & 0x7F == 1`, so field 3:2
is 0 and `gp-0x6802` is 1. **A "6803 == 2" condition would therefore exclude camera frames.** But r25 is computed at
`0x29A82`, *after* the guard at `0x29A48..0x29A5C`. A 6803 gate in the guard needs a new `ld.bu` (+4 bytes), so it is
not an in-place edit.

---

## 6. Open / exact next steps

1. **Fork fingerprint** (fork owner, not this kit). Check how `39990-TVA,A160` is accepted today, then choose the F4
   character. **Re-header every revert `.rwd` before flashing a new string.**
2. **`FUN_000540d0`/`FUN_00054066` debounce**: disassemble to confirm the "up to 49 bad frames decoded" reading (§3.3).
3. **`gp-0x6a98`**: its on-car value and meaning. It decides 500 ms vs 200 ms (confirmed). Either way the sentinel comes
   at ≤ 515 ms.
4. **Camera field values**: re-measure byte 2 of the camera's own 0xE4 on bus 2 before relying on "camera sends 0 in
   bits 3:2".
5. **The direction-2 option** (§5) has to go through GATE 2 and the friction harness as a design change: post-fade arm
   `0xCBAE4` plus the 0.10 s ramp-in.
