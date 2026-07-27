# HANDOFF 2026-07-27 (session 2) — V53: FOURFRAME2 + minimum steer speed 0

**Nothing was flashed. No CAN was sent.** One build was produced, unflashed. This was a short, focused
build session, not an investigation — the operator asked for a specific artifact and got it.

**Predecessor:** `HANDOFF-2026-07-27-fourframe-strb-defect-and-vibration-reframe.md` (same date, earlier
session). Read that first for the STRB defect and the vibration reframe; this handoff assumes it.

---

## 1. The request, and what was delivered

> *Make a V53 RWD: V38 base / Four frame V2 (FOURFRAME2) / Adjust minimum steer speed to 0*

Delivered exactly that, no more:

```
_v53_plain_image.bin  SHA 6be6055357506b87afe21ea622d46bda35ececfe5bb9038834e643d0f0292e1f
39990-TVA,A160-V53-LKAS-4x-V38base-FOURFRAME2-telem-STRB01FIX-authority-refmodel
  -newid0x6a0-0x6a3-mbx16-19-100hz-minsteerspeed0-lockout0xC62EA-320to0-0x13000-0x100000.rwd
                      SHA 29e444ca4a68e4dc1408d62e090cc6372927cb0ae7ca918465e3903125f9e114
```

**V53 = FOURFRAME2 plus exactly six bytes:** `0xC62EA`/`0xC62EB` (320 → 0) and the CAL-block CRC trailer
at `0xC6FFC`. 855 bytes vs stock (FOURFRAME2 is 853); 737 vs V38.

Builder: `analysis-2020accord/build_v53_tva.py`.

---

## 2. ★ The build technique worth reusing: import the cave, don't re-type it

`build_v53_tva.py` **imports the 774-byte telemetry cave from `build_vfourframe_tva.py`** — the file that
produced `_vfourframe2_plain_image.bin` — rather than copying the assembler and the mailbox tables into a
new file. Consequence: **there is no transcription surface at all.** Every encoder self-check, both
mailbox gates, the STRB=0x01 fix and all 16 signal displacements come along unmodified and unre-typed.

It then closes the loop with an assertion that is stronger than any re-disassembly:

```python
ff2_diffs = [i for i in range(START, END) if ff2[i] != code[i]]
assert ff2_diffs == [0xC62EA, 0xC62EB, 0xC6FFC, 0xC6FFD, 0xC6FFE, 0xC6FFF]
assert MAIN_CRC(ff2) == MAIN_CRC(code)     # cave + hook provably untouched
```

Because FOURFRAME2's cave was already Ghidra-verified in the previous session, proving byte-equality with
that image inherits the verification instead of redoing it. **Use this pattern for any future "existing
cave + one cal" build.**

---

## 3. The lever: `0xC62EA` 320 → 0

`0xC62EA` (`tp+0x72EA`) is the LO half of a two-sided speed window at the top of `FUN_00028ea6`, the live
~1 kHz arbitration:

```
0x28EB6  ld.hu 0x72e8[tp],r2    ; r2 = cal 0xC62E8 = 12800 = 199.8 km/h    HI  -- UNTOUCHED
0x28EBC  ld.hu 0x72ea[tp],lp    ; lp = cal 0xC62EA =   320 =   4.995 km/h  LO  <== THE LEVER
0x290C8  cmp r2,r10 / setfnh r9   ; r9 = (voted speed <= 12800)
0x290D2  cmp lp,r10 / setfnc r7   ; r7 = (voted speed >=   320)   [unsigned]
```

Failing the window is the only writer of `STEER_STATUS = 3`, and the intra-function `cmp 0x2` at
`0x29382` gates **both** the `STEER_CONTROL_ACTIVE = 1` write and the authority ramp. So this is real
authority, not a reported label.

### Why 0 and not the previously-recorded suggestion of 64

`docs/STATE.md` carried "suggested value **64** (1 km/h), not 0". The operator asked for 0, and 0 is the
better choice on the firmware's own logic — this is worth recording because the old note is the kind of
thing that gets cited later:

**Stock already unlocks true standstill.** `gp-0x68b3` (the window bypass) is written in `FUN_0004d0d0`
**only when `gp-0x6a62 == 0`**, i.e. exactly zero. So stock **permits 0 km/h and forbids 1–319 counts**.
The discontinuity is by design. Setting the LO bound to 64 would have *moved* that discontinuity to
1 km/h; setting it to 0 **removes** it. `STATE.md` has been corrected.

### Safety, re-verified in Python at build time, independently of Ghidra

Each of these runs inside `build_v53_tva.py` on every build, so it cannot silently rot:

- **Exactly one reader image-wide.** Sweeping **both** V850E2 encodings over `[0x13000,0xC4FFC)`: the
  `disp|1` halfword `0x72EB` — the form `ld.hu` actually uses — occurs **once**, at `0x28EBE`, the
  displacement field of `0x28EBC`. The single bare-`0x72EA` hit is at **odd** address `0x21167`, so it
  cannot be an instruction operand. (This is the `hw2 = disp|1` trap from `CLAUDE.md`: a scan for the bare
  displacement finds *nothing at all* here and would have looked like a dead cal.)
- **LERP-masquerade check** (the §4e trap from the 07-24 handoff — a displacement scan structurally cannot
  see table-indexed reads): the nearest `movea …,tp,rX` base below the lever is `0x7010`, a 4-point record
  with X = 0/640/3200/6400, ending ≥ 0x2DA bytes short.
- **SNA detection intact.** The `0x7FFF` = 32767 sentinel still fails the untouched HI bound 12800, so an
  implausible speed keeps locking out exactly as at stock. Asserted in the model too (§4).
- **`0xC62EE` left stock** and asserted. It is a permissive on a CAN-commanded assist-shutdown task, not a
  lockout, and must never be raised.
- **Opposite risk class from V40.** V40 wrote `0xFFFF` into a governor slew guard so it *never fired* →
  snap-to-target → DTC 0x1d → motor off. Here nothing is removed from a limiter: a comparison threshold is
  widened at its low end, on a gate whose failing branch only reports a status and withholds assist.

Builder gates: 50/50 CRC blocks, both bootloader walks (`walk`, `walk_all_blocks`), and an RWD
decode-back with **every gate re-run on the readback**.

---

## 4. Golden-model corrections — three stale claims retired

Updating `analysis-2020accord/eps_lkas_chain_model.py` turned up that its low-speed section had never been
reconciled with the 2026-07-24 lockout result. Three claims were wrong in a decision-bearing way:

| stale claim | status |
|---|---|
| "the sub-3-mph cutoff is **NOT** a firmware speed gate — a dedicated trace found no discrete speed threshold anywhere in the command chain" | 🛑 **FALSE.** It is `0xC62EA`, in `FUN_00028ea6`, in the command chain |
| "the exact firmware low-speed threshold is **unquantified**" | 🛑 quantified: 320 = 4.995 km/h = 3.104 mph |
| "**NO VEHICLE-SPEED INPUT ANYWHERE**, confirmed broader" (2026-07-21 completeness pass) | 🛑 scope falsified **twice** — the window, and the G1 governor reading `gp-0x6a64` vs cal `0xC6316`=640 to skip the slew limiter below ~10 km/h |

**Why the original trace returned a false negative** (recorded in the model as a method rule): it required
a two-sided compare **followed by a boolean store**, and the window's boolean `bVar2` is never stored to
RAM — it lives in a register and is consumed immediately by the AND-chain. *Never require
"compare → boolean store"; search for the compare alone.*

What **survives** from that completeness pass, and is still true, is narrower: none of the **9 aggregator
lanes** reads road speed, and every rate-adaptive **table** is keyed on motor/resolver electrical-angle
rate (`gp-0x6ac0`), not road speed.

### What was added to the model

- `Calibration.speed_window_lo` / `speed_window_hi` with full address provenance.
- `steer_status_low_speed_lockout(sensors, cal)` — a runnable helper carrying the firmware map, with the
  `gp-0x68b3` standstill bypass **derived from speed** (`counts == 0`) rather than configured, because it
  is a runtime RAM flag and not a cal.
- `Calibration.for_build("V53")`, inheriting the V38 cal set and overriding only `speed_window_lo`.

Verified against the documented behaviour:

```
 mph      V38-ST3  V53-ST3
  0.000   False    False     <- the designed standstill bypass, both builds
  0.500   True     False
  3.000   True     False
  3.104   False    False     <- V38 releases exactly at the cal
 317.8    True     True      <- 0x7FFF SNA sentinel still locks out on V53
V53 vs V38 cal delta: ['speed_window_lo']
```

⚠ The helper models the **speed conjunct only**. `bVar2` is a 5-way AND, and `gp-0x69aa == 0x8000`
("no derate") shares the same `STEER_STATUS=3` write — so **an on-car ST=3 observation cannot distinguish
"speed window failed" from "a derate is active."** Documented in the docstring.

The model's own scenario suite still runs clean (`python eps_lkas_chain_model.py`, exit 0).

---

## 5. Why the two changes belong in one build

They are not merely compatible — **the lockout edit creates the condition the telemetry needs to observe.**

On route 13, `STEER_CONTROL_ACTIVE` is a deterministic function of speed (ST=3 *is* the sub-5 km/h gate),
so cells B and C of the A/B/C split have **zero speed overlap** and the "engaged at low speed" cell is
structurally **empty**. The 14,750× result therefore establishes that *applied* torque is required, but
cannot exclude "needs v > 1.4 m/s *and* OP engaged, with applied torque incidental."

V53 fills that cell. **One parking-lot drive now:**
1. measures `gp-0x6966` (authority) — settling the `0xC6AF0` edit direction, which two analysis passes
   got opposite answers on from static data alone;
2. captures all three terms of the `FUN_0003a382` loop (`gp-0x4f60` sensor, `gp-0x6ad6` model,
   `gp-0x6ad4` output) so the lane's transfer function can be **identified**, not inferred;
3. breaks the speed/applied-torque collinearity.

⚠ **V53 still cannot settle 21.09 vs 78.91 Hz.** The cave transmits at 100 Hz and samples
instantaneously; 78.91 folds to exactly 21.09. That was left deliberately unstacked — the cave has never
once transmitted, so changing the TX rate in the same step would make a null uninterpretable. **Prove TX
first.**

---

## 6. Two things the operator must decide before this goes on the car

1. **V53 does not carry the V42 ratchet fix.** `0x454FE` stays stock `0x65BA` — asserted in the builder,
   not left implicit — because FOURFRAME2 doesn't carry it and a V38 base was specified. This **matches
   the image on the car today**, so V53 is not a regression. But `0x454FE` is a CONFIRMED root cause with
   a validated on-car fix, and it is one byte. Rebuilding with it is trivial if wanted.
2. **Expected behaviour change.** Below ~3 mph the EPS will now accept LKAS torque where it previously
   refused. `CP.minSteerSpeed = 0.0`, but the StarPilot fork runs `steerAtStandstill = False`, so at a
   dead stop openpilot still will not command — the real new window is roughly **0.1–3 mph**: creep,
   parking lots, stop-and-go. Static-friction steer effort at walking pace is high; expect the EPS to work
   harder there than it ever has on this car.

---

## 7. Testable prediction recorded for the drive

On V53, `STEER_STATUS = 3` should become **unreachable** except on an implausible-speed HI-bound failure.
Combined with the model's separate finding that ST=4 and ST=7 are unreachable on the V37/V38 cal set, the
ST=3 excursion that today fires **every time the car crosses ~3 mph** disappears — and with it that
trigger's ramp restart, which holds `gp-0x6806` at 0 through a full ~993-cycle mode-0 ramp-up.

Other disengage arms still zero `gp-0x6806`, so this removes **one route, not the mechanism**. If the
"transient vibration just after pulling away" reading is right, V53 should change it; if the "sustained"
reading is right, V53 should not. Either result is informative.

---

## 8. Recommended next steps

Unchanged from the predecessor handoff except that old steps 2 and 3 have merged into V53:

1. **openpilot-side 21 Hz notch.** Zero brick risk, known untested rather than null. Keep the ±4096 rail
   fraction matched between runs — 14% of frames are railed and railed windows show no 21 Hz.
2. **Flash V53.** One parking-lot drive answers both open questions (§5).
3. **The `0xC646C` decoupling** — a correctness fix, not the vibration fix.
4. Only then a `0xC6AF0` edit, in whichever direction the telemetry indicates.

🛑 **Flash only on explicit operator instruction naming the file and the bus.**

---

## 9. Collaterals updated this session

- `docs/STATE.md` — V53 added as the flash candidate; workstream B moved from "unbuilt" to "built";
  the "suggest 64" note corrected to 0 with the reasoning; next-steps renumbered.
- `docs/BUILD-LINEAGE.md` — `0xC62EA` row moved out of "untested levers"; v53 added to the per-build
  delta table and to the flash-status list.
- `analysis-2020accord/eps_lkas_chain_model.py` — §4 above.
- `analysis-2020accord/build_v53_tva.py` — new.
- `memory/project-v53-fourframe2-plus-minsteerspeed0.md` + `memory/MEMORY.md`, and the same fact in the
  session-memory store.
- `docs/INDEX.md` — handoff chain extended to this document (it had stopped at V44).
- Both repos committed and pushed to `main`; artifacts to `accord-firmwares`.
