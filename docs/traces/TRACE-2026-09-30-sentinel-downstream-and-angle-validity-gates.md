# TRACE 2026-09-30 — the 0xE4 fault sentinel downstream, and the angle-validity gates

Agent: firmware-codepath-tracer (subagent). Programs: Ghidra `code.bin` (stock) and the V294 program
(code-identical to V295 except cal `0xC63EA` + CRC); Python LE byte scans on stock and the V295 image.
`gp = 0xFEDF8000`, `tp = 0xBF000`. Every Python scan below was positive-controlled (see §5).
Scratch: `_scratch/angle_loop/sentinel_gates/` (`sg_scan.py`, `sg_bits.py`, `sg_indirect.py`, `fault_pulse.py`,
`lane_mirror_v295_andguard.py` = the study mirror plus one guard switch; the study file was not modified).

**Decision this trace feeds:** does the angle loop need a validity cave or a fault clamp?

| gate | verdict | minimal fix |
|---|---|---|
| A. 0xE4 RX fault sentinel `0x7FFF` | **NOT covered downstream — the lane's 2.048 s pulse is delivered** | 2 code bytes, in place, no cave: `0x29A56 da 05 → b2 05` (§3.3) |
| B1. angle wrap (~+32700) on the `−0x8000` baseline | **covered** by the ±12000 bail (fail-safe, but latches LKAS off for the ignition cycle) | none |
| B2. `gp-0x67fe ≠ 2` (angle forced to 0) | **NOT covered** — lane runs a 2.048 s PID fade with θ = 0; no downstream cut found | +4 code bytes in the same block: `0x29A50 e2 47 00 00 → e0 df 34 43` (§4.2) |
| B3. `gp-0x679c ≠ 3` with an in-range wrong angle (baseline `0x7FFF`) | **NOT covered** by any lane gate | zero firmware bytes: fork drops the request unless 0x14A byte 4 bit 1 = 1 (§4.3) |

---

## 1. What the fault writes (EVIDENCE: `decompile_function(0x52676)`, V294 program)

`FUN_00052676` (0xE4 RX callback, slot 7) has three sentinel branches:

| branch | condition | writes |
|---|---|---|
| `0x5268C` | `gp-0x3330 == 1 && param == 4` | `69ae=0x7FFF`; `6805/6804/6803/6802/6876/67f3 = 0xFF`; `gp-0x3330 = 0` |
| `0x52726` | `param ∈ {1,2,3,5,6,7}` | same cells; then `FUN_0005462c(7, param)` |
| `0x527C6` | `param == 0` but `gp+0x6400 & 8` | `69ae=0x7FFF`; `6805/6804/6803/6876 = 0xFF` (6802, 67f3 from the tail) |

- **DTC side effect [EVIDENCE].** `FUN_0005462c(7, code)` returns without a DTC for codes 1–4, and for codes
  5/6/7 calls `FUN_00016de6(id, 4|2|1, …)`. The id is the halfword at `gp-0x32cc + 7·0x2c + 8`, `.data`
  boot value (flash `0x89F20`) **= `0x0065`**. DTC 0x65's descriptor (`tp−0x72c4 + 0x65·0x1c` = `0xB8848`,
  `03 14 00 00 00 00 00 00 00 00 00 00 ff …`) has **reaction dword (+8) = 0**. The fault-class masks
  `gp-0x18d4` (`FUN_000160c8`, `FUN_0001712a`, `FUN_00046810`) and `gp-0x18d0` (`FUN_0001601e`,
  `FUN_00047c4a`) are each the OR of that +8 dword over active DTCs. **⇒ the 0xE4 DTC sets no fault-class
  bit; it does not trip `FUN_00046ea6(n)` (the lane's ST=7 trigger uses n = 9, FOC substate uses n = 8).**
- **`gp+0x6400` bit 3 is a CODING bit, not a runtime fault [EVIDENCE].** Writers: `0x50ABE`/`0x50B52`
  (`FUN_000508e8`, from variant record byte `0xCD01B + 0x24·row`, bit 3 set iff record bit 0x04 = 0),
  `0x50C40` (another coding-write routine), `0x4A882` (`FUN_0004a798`, PasCom debug command, German strings).
  Live row 11 (selector 7, measured on the wire) has option byte `0x75` ⇒ bit 0x04 = 1 ⇒ **`gp+0x6400` bit 3
  = 0 on this car.** Only row 0 (`0x80`) sets it. Consequence: the lane's `ST = 6` branch (`0x29172 ld.w
  0x6400[gp]; shr 4; bnc`) is unreachable at runtime. This matters because state 2 **HOLDS** full ramp on
  `ST = 6` (§2) — a latent full-authority hold that coding prevents.

## 2. Inside the lane (EVIDENCE: decompile of `0x28EA6` in V294 + dry-run disassembly)

```
0x2912C..0x2913A  r27 = bVar2 = (69aa in [C73F2,0x8000]) && bVar1 && speed-window && gp-0x67fe==2
                                && (unsigned)(gp-0x69ae + 0x4000) < 0x8001        # 0x7FFF fails this
0x29142 cmp r0,r25 ; be 0x2915E      inputs invalid (bail)          -> ST := 7
0x2914A cmp 1,r10  ; be 0x2915E      FUN_00046ea6(9) == 1           -> ST := 7
0x29152 cmp 8,r14  ; be 0x2915E      gp-0x67fa == 8                 -> ST := 7
0x29156 ld.bu -0x6807 ; cmp 7 ; bne 0x29172   ST already 7         -> ST := 7   (STICKY)
0x29172 ld.w 0x6400[gp] ; shr 4 ; bnc        coding bit 3           -> ST := 6
0x2918E cmp r0,r27 ; bne 0x291A6             !bVar2                 -> ST := 3   (0x29194)
```

**The fault path is ST = 3, not 4/7.** In state 2 (saturated, 0x295B4..0x2961A, bytes read):
`6803==1 && 6805==0 → 0x296C6`; `ST==7 → 0x296C6`; `ST==4 → 0x296C6`; `6805==0 && 6803==0 → 0x296F8`;
**`ST==3 → 0x296F8`**; otherwise (`6805 ≠ 0`, ST ∉ {3,4,7}) **→ 0x29734 = hold**.
`0x296F8` = `ramp −= [0xC63F6]` (16), `gp-0x6806 := 0`, state 4; state 4 keeps subtracting 16 while
`ramp > 16`, then `LAB_2971A` (ramp 0, state 1). **2.048 s.** The PID runs on every one of those ticks:
`0x29A48..0x29A5C` runs iff `ramp ≠ 0 || gp-0x6805 == 1` (and inputs valid, `0x29A60`).

## 3. Gate A — the sentinel pulse IS delivered

### 3.1 Every consumer of the fault-written cells (two methods, set difference adjudicated)

Python LE scan (4-byte disp16 incl. `ld.bu` odd/even and `ld.hu`/`ld.w` hw2|1, store-r0, 6-byte disp23) over
`[0x13000,0xC0000) ∪ [0xC4000,0xC5000)` of V295; plus LE32-literal and `movea`/`addi` lo16 scans for
register-indirect access (zero hits for all nine cells; control `gp-0x6b98` finds its 2 known literals).
Ghidra `search_instructions` on the V294 program: `-0x6805` 16, `-0x6803` 15. Python: 26 and 23. **Every
extra Python hit is in `0x2A546..0x2A822` = `FUN_0002a508`, the uncalled twin island** (not analysed in the
V294 program; zero callers per kit record) ⇒ set difference adjudicated.

| cell (fault value) | readers outside the lane and the dead twin | effect of the fault value |
|---|---|---|
| `gp-0x69ae` (0x7FFF) | `0x4E840` `FUN_0004e82e` | 56-byte diagnostic record into a caller buffer; writes no gp cell |
| `gp-0x6805`, `-0x6803`, `-0x6802` (0xFF) | `FUN_0004e82e` only | same record |
| `gp-0x6804` (0xFF) | `0x428AC` `FUN_00042746`; `0x55CE6` `FUN_00055c42` | 42746: read only under `gp-0x6806 ≠ 0 && ramp == 0x8000`, which the fault leaves on its first tick. 55c42: 0x18F packer bit |
| `gp-0x6876` (0xFF) | `0x4D114` `FUN_0004d0d0` | tests `== 1` ⇒ 0xFF ≡ 0 |
| `gp-0x67f3` (0xFF) | `0x2F070`, `0x3039C`, `0x3313C..0x33182`, `0x4FA56`, `0x4FE26`, `0x514F6`, `0x5180C` | the first three test `== 1` (`x·(x<2)==1`, `bh`/`cmove`, `cmp 1`) ⇒ 0xFF ≡ 0. The rest are freeze-frame / UDS RID handlers per kit record [BELIEF, not re-read] |
| `gp-0x6807` (3) | `0x4E8EC` (diag record), `0x55C96` (0x18F STEER_STATUS field) | report only |
| `gp-0x6806` (0) | `0x2EF40`, `0x2FC88`, `0x3130C..54`, `0x35A06`, `0x3AA94`, `0x42842`, `0x4FA96`, `0x4FD44`, `0x55C76` | none gates `gp-0x6b4c` (aggregator below); others are other lanes, diag, or the packer |
| `gp-0x69b0` (falling) | `0x42846` (`FUN_00042746`), `0x2B38E/9E` (dead island) | table re-select on a settled transition — same as a normal disengage |

**No governor (`FUN_0004503c`, `FUN_0004595a`, `FUN_000456a4`), EME (`FUN_00042af8`), FOC
(`FUN_00041464`, `[0x60000,0x84000)`) or mixer (`FUN_00025c32`, `FUN_00026c80`) address appears in any row.**

### 3.2 The delivery chain, gate by gate (EVIDENCE: decompiles)

```
0x2A23C  st.h  gp-0x6b38 = T
0x2A2EA  st.h  gp-0x6b3c = T * (gp-0x67a4 in {2,3})          # decompile tail of 0x28EA6
         gp-0x67a7 = (ramp != 0 || gp-0x6809 == 1)            # 0x2A2A0 reads r20 = (ramp != 0)
FUN_0002b422: state gp-0x3d28 keyed only on gp-0x67a1 (FUN_00025c32's return), gp-0x67a7, and
         gp-0x67a2/67a3 (literal 1). In state 4 it stays at role 3 while 67a1 != 0 and 67a7 == 1
         => role 3 (delivering) for the whole fade; role 4 (stop) only once the ramp reaches 0.
         clamp +-[0xC61B2] -> FUN_00025c32(ch 1) -> FUN_00026c80 -> gp-0x6b4c
FUN_0003aa2c (aggregator): gp-0x6b4c enters BOTH branches of the gp-0x67ac test, masked only by
         |x| < 0x2800; gp-0x6806 (bVar4) selects r24/r26 lane gain cals 0x743E/0x7440/0x7444/0x7446 only.
         -> gp-0x6b94 -> governor -> EME shaper -> gp-0x6b98 -> FOC
```

**Verdict A [EVIDENCE for the chain and the census; BELIEF only for the 4 un-reread diag/UDS sites]:** no
consumer of the fault cells sits on the delivery path, and every gate on that path is fault-blind for the
duration of the ramp. **The 2.048 s pulse reaches the motor**, bounded only by fault-independent
structures: lane clamp/rail, `0xC61B2`, the aggregator ±0x2800, the governor ceiling, and the soft-EME
integrator `gp-0x3570` (an over-bound excess, not a fault response; whether the pulse arms SM2 depends on
the corridor bound at that moment — not evaluated).

### 3.3 Size of the pulse, and the fixes (MIRROR: `fault_pulse.py`, the byte-exact study mirror)

Sign-hold gate (`0xC64A3` = 1, dead zone `0xC61B8` = 102, armed by `gp-0x6806 = 0`) passes the pulse only if
the lane was already pushing in the sentinel's direction (+).

| path, ramp step | lane before the fault | T peak | at | last T ≠ 0 |
|---|---|---|---|---|
| V295 map, 16 (the car now) | pushing + (raw −1500, T 961) | **2286** | 113 ms | **2047 ms** |
| V295 map, 16 | pushing − | −918 (decay only) | 0 | 10 ms |
| V295 map, 328 | pushing + | 1329 | 22 ms | 99 ms |
| angle loop (edits 1–4), 16 | err +5° (T 480) | **2275** | 118 ms | **2047 ms** |
| angle loop, 328 | err +5° | 1178 | 29 ms | 99 ms |
| **angle loop + `0x29A56 → b2 05`, 16** | err +5° | **472 = decay only** | 0 | 105 ms |

**Fix A1 (cal, 2 bytes + CRC): `0xC63F6` 16 → 328.** Readers of `tp+0x73F6` — Ghidra 8 = Python 8 (incl.
6-byte form), no LE32 literal: live `0x2945E`, `0x294EE`, `0x29500`, `0x296F8`, all in the engage SM;
`0x2A624/6A8/6BA/85E` in the dead `FUN_0002a508`. **It governs only the direction-0 ramp-down** (openpilot's
`gp-0x6803 = 0`): request drop, every `ST = 3` cause (sentinel, `gp-0x67fe ≠ 2`, speed window, `gp-0x69aa`
range, `bVar1`), and the state-3 shortcut threshold. **Not** the override latch (`0xC63F4` = 328) nor
direction 2 (`0xC63FA` = 66). Side effect: every one of those fades becomes 0.1 s. It still acts on the
sentinel (1178–1329 peak for 0.1 s) and does not close the override-latch I wind-up.

**Fix A2 (recommended, 2 code bytes, in place): `0x29A56` `da 05` (bne 0x29A60) → `b2 05` (be 0x29A5C).**
Encoding: Format III `ddddd1011dddcccc`, disp 6, cond 2; the same form is `be 0x2915E` = `b2 0d` at `0x29148`
(disp 22). Result: **run iff `ramp ≠ 0 && gp-0x6805 == 1`** (stock: `ramp ≠ 0 || request`). `r20` is left
intact for its second reader at `0x2A2A0`. Effects: the sentinel never reaches P (`0xFF ≠ 1`); the output
lag (5.05 Hz) decays to 0 in ~105 ms; the override-latch wind-up closes (ramp 0 → skip → I := 0), so this
**supersedes edit (6) `0x29A5A`**; a normal disengage releases in ~100 ms instead of a 2 s PID-held fade,
which also removes the fork-side "steer to centre while inactive" hazard. Int32 headroom against the
sentinel (`Kp ≤ 10922`) stops mattering.

## 4. Gate B — angle validity

### 4.1 The ±12000 bail (`0x28F50..0x28F5A` → `0x290B0`) — EVIDENCE

Valid iff `(unsigned)(gp-0x4f60 + 0x6400) < 0xC801` (|τ| ≤ 25600) **and** `gp-0x6752 ∈ {−1, +1}` **and**
`(unsigned)(x + 0x2EE0) < 0x5DC1` (|x| ≤ 12000). On a bail tick: `gp-0x3d2c := 2`, r26 := 0, `gp-0x682f := 0`,
`r25 = 0`. Then:
1. `0x29A60 cmp r0,r25 → jr 0x2A164`: **PID skipped** — I := 0, `E_prev` := 0x7FFFFFFF, S = 0 into the
   output lag (which decays, not resets).
2. `0x29142 → 0x2915E`: **STEER_STATUS := 7, STICKY.** Every non-7 write of `gp-0x6807` sits behind
   `0x29156 ld.bu -0x6807; cmp 7; bne`. Census: 10 live writers `0x29160..0x2931A`, all in that block, plus
   10 in the dead `FUN_0002a30e`. No literal/indirect reference. `.data` boot value 0 (flash `0x868A9`), so
   only an ECU reset clears it.
3. State 2 with ST = 7 → `0x296C6` → state 5, ramp −328/tick (0.1 s) → state 1. Re-engage needs `ST < 3`
   ⇒ **LKAS is off until the next key cycle**, reported as STEER_STATUS 7 on 0x18F (`FUN_00055c42`,
   `gp-0x141c` high nibble). No DTC from this path (the DTC 0x49 call at `0x291C0` is the `gp-0x6758`
   counter branch).

**Verdict B1:** with edit (1) the wrap (~+32700) bails ⇒ fail-safe, **NO CAVE NEEDED**. The cost is a
latched loss of LKAS for the drive; a legitimate |θ| > 1200° cannot occur.

### 4.2 `gp-0x67fe ≠ 2` — EVIDENCE for the lane, BELIEF for the motor

`FUN_0003bd7c` (decompiled): FOC mode `gp-0x6772` < 4 or 6–8 → 0; mode 4/5 with `FUN_00046ea6(8) == 0`,
`gp-0x671d < [0xC6500]` (= 3), `gp-0x6851 == 0` and latch `gp-0x6845` clear → 2 (mode 5) or 1 (mode 4);
otherwise 0 + latch (+ flags into `gp-0x6a94`). `FUN_0003e760` is the fifth writer (record).

- **Lane:** `bVar2` requires `gp-0x67fe == 2` ⇒ ST := 3 on the same tick ⇒ the same 2.048 s state-4 fade
  as the sentinel, PID running, request still 1. θ is forced to 0 at the next 100 Hz pass, so P acts on
  `E = 16·θ_sp` for up to 2 s, signed toward the setpoint — held turn ⇒ pulled further in. The sign-hold
  gate passes it whenever the lane was already pushing that way (the normal hold-a-turn case).
- **Downstream:** no 67fe reader sits in the mixer, aggregator or governor. The EME shaper reads it at
  `0x43016`: when ∉ {1,2} it zeroes the angle-based boost bound terms (`iVar43`, `iVar27`) — a narrower
  corridor, i.e. faster soft-EME charging, **not a cut**. `FUN_00043e44` (`0x44406`) is the float twin
  (record: not on the assist chain). Whether the motor delivers in FOC mode < 4 or 6–8 was **not traced**
  [BELIEF: off]. In mode 4/5 with a gate failure the motor is running and nothing found cuts the lane.

**Verdict B2: NOT covered ⇒ gate needed.** Minimal, in place, same block as A2, **+4 bytes**:
`0x29A50` `e2 47 00 00` (setfe r8) → **`e0 df 34 43` = `cmovne r0, r27, r8`**. After `0x29A4E cmp 0x1,r8`,
r8 := request==1 ? r27 : 0, where r27 = bVar2 (`0x2913A mov r8,r27`). With A2 the guard becomes **run iff
`ramp ≠ 0 && request == 1 && bVar2`**, so the sentinel, `67fe ≠ 2`, the speed window, the `gp-0x69aa` range
and `bVar1` each skip the PID on their first tick.
- Encoding control: `0x23954 e0 37 34 33` = `cmovne r0, r6, r6` (Ghidra dry-run decode); 50 such instances.
- r27 census in the function (Ghidra operand search): written `0x2913A`, next at `0x29E7E`/`0x29F2E`
  (run path), `0x2A0E4` (`gp-0x680a` lane), `0x2A168` (skip) ⇒ unchanged at `0x29A50` [EVIDENCE within the
  analysed body; dominance of `0x2913A` over `0x29A48` is BELIEF from the decompile's linear structure].
- r8 is overwritten at `0x29A78` on the run path. Its deadness on the `0x2A164` skip path is **not proven**:
  next step below.

### 4.3 `gp-0x679c ≠ 3` with an in-range angle

The lane tests neither `gp-0x679c` nor `gp+0x6470`. Baseline `0x7FFF` ⇒ θ relative to power-on, in range,
no bail, and 0x14A then carries a different signal (`gp-0x6ce0`, angle trace §2.3). **Zero firmware bytes:**
the fork should send `STEER_TORQUE_REQUEST = 0` unless 0x14A byte 4 bit 1 (`gp-0x679b` = mode 3 ∧
`gp-0x67fe == 2` ∧ |θ| ≤ 1000°) is 1. With A2 the request drop skips the PID at once. Measured 1 in
2,316,807 healthy frames (angle trace §3.2), so this gate costs nothing in normal driving. Latency is 10 ms
plus the fork's round trip. A firmware-side mode-3 gate would need a cave.

## 5. Methods and controls

- `sg_scan.py`: control `gp-0x4f60` finds the 7 known 6-byte sites (`0x4C784`, `0x59BFA`, …); `gp-0x6806`
  finds the 8 `st.b r0` sites; `tp+0x73F6` Python 8 = Ghidra 8.
- `sg_indirect.py` (LE32 literal + `movea`/`addi` lo16): control `gp-0x6b98` → `0x89C90`, `0xBBC68` ✓.
- `.data` mapping flash `[0x86260,…)` ↔ RAM `0xFEDF11B0` (kit record, copy loop `0x1476C`).
- Not covered by any method: a base pointer into the `gp-0x68xx` block with `sld`/`sst` (ep-relative).
  The fault cells' readers all use gp-relative forms where seen.

## 6. Open / exact next steps

1. **r8 liveness on the skip path** after `0x2A164` up to the next r8 write, before cutting the 6-byte guard
   (`disassemble_function` of the tail, or `analyze_dataflow` on r8 from `0x29A50`).
2. **GATE 2 / feel of the faster release.** A2 makes every disengage and every ST = 3 event a ~100 ms
   output-lag decay instead of a 2 s fade. Operator-facing; a design decision, not a trace fact.
3. **Motor state in FOC mode < 4 / 6–8** (`gp-0x6772`) — would turn "BELIEF: off" into evidence.
   Not needed if the 6-byte guard ships.
4. **The 4 un-reread `gp-0x67f3` readers** (`0x4FA56`, `0x4FE26`, `0x514F6`, `0x5180C`) — confirm `== 1`
   tests.
5. **Preemption:** if the RX callback can preempt the lane between the SM's `gp-0x6805` read and
   `0x29D6A`, one tick could compute on the sentinel with request seen as 1 (~1 ms impulse into a 5 Hz lag).
   Task priority not traced.
6. **Instrument already on the wire:** STEER_STATUS (0x18F, `gp-0x6807`) shows 3/7, and 0x14A b4 bit 1
   shows mode 3 ∧ `gp-0x67fe == 2`. A build carrying A2/B2 is observable through them plus the existing
   torque tap.
