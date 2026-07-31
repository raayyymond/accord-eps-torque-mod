# ★★★ `gp-0x671a` is a HARD-REVERSAL COUNTER — the firmware has a built-in oscillation detector

**Found 2026-07-31 while answering the operator's objection to V62** (*"we're affecting manual steering
feel even though the symptom is LKAS-specific"*). It is the decoupling point that lets a rate-lane
damping increase apply **only once an oscillation has occurred** rather than always. ⚠ Not "only while
oscillating" — see the LATCH section below; the first version of this note claimed the stronger thing.

## The state machine — `FUN_000428d4`, 1 kHz
States `{neutral, +latched, −latched}` at `gp-0x67df`; dwell at `gp-0x6759`; reversal count at
`gp-0x357c`, clamped into `gp-0x671a`:

```python
T, HYST, CEIL = 12800, 50, 5      # 0xC620A (ld.h) / 0xC64DD (ld.bu) / 0xC64FA (ld.bu) -- byte-read LE
if state == neutral:
    dwell = 0; revcount = 0                     # 0x428FE / 0x42906 -- RESET EVERY TICK
    if   cur >  T: state = +latched             # 0x4290A cmovlt/blt -- only exit from neutral
    elif cur < -T: state = -latched             # 0x42918
else:
    if   dwell >= HYST:  state = neutral        # 50 ticks with no reversal -> clears the counter
    elif crossed_opposite_threshold:            # a HARD reversal, not a sign flip
        dwell = 0; state = flip(state); revcount += 1
    else: dwell += 1                            # small excursions do NOT reset anything
gp_0x671a = min(revcount, CEIL)                 # 0x42A12 -- the ONLY st.b writer image-wide
```

⇒ **It reads 0 during smooth or neutral steering and RISES with reversals.** `state >= 5` means
"5+ hard reversals recently" = **an oscillation is happening**. At 18–21 Hz the half-period is 24–28 ms,
comfortably inside the 50 ms dwell timeout, so it arms in ~125–150 ms.

## 🛑🛑 IT IS A ONE-WAY LATCH WITH A 5 s HOLD — the output stage, traced 2026-07-31
The value the arms test is **not** the raw per-tick count. `FUN_000428d4`'s output stage (`0x429A0`–
`0x42A12`, orchestrator-verified, cals byte-read) holds it:
```
0x429A8  cmp r15,r12 / bh   ; cal 0xC62DE = 640 > voted DRIVER TORQUE gp-0x6a5e -> RELOAD hold timer
0x429AC  cmp r0,r14  / bne  ; revcount != 0                                     -> RELOAD hold timer
0x429CA  reload = cal 0xC6270 = 5000 ticks = 5.0 s @ 1 kHz
0x429DE  cmp r8,r6 / bh     ; CEIL > held -> output = revcount
0x429EA                     ; else        -> output RE-PINNED TO CEIL every tick
```
Once the held value reaches CEIL it stays there. The only way down is **5000 consecutive ticks with
driver torque >= 640 AND no reversals** — and driver torque dips below 640 on every direction change, so
the timer reloads constantly. ⇒ **once tripped, the arm is sticky**, and it carries into subsequent
manual steering.
✅ **The latch is PROTECTIVE.** A gain that switched per-tick with the reversals would modulate **at the
mode frequency** — a parametric pump, the exact failure mode V58/V59/V60 chased for three builds. Honda's
hold prevents that. A per-tick-gated damper would be actively dangerous; this one cannot be.
⚠ **Cell correction:** the per-tick zeroing at `0x42906` is on **`gp-0x357c`** (raw count), NOT on
`gp-0x671a`, which is the latched output written once at `0x42A12`.
🛑 It is a **hard AMPLITUDE gate**: if the driving signal never crosses ±12800, the counter never leaves 0.

## Why it matters — both rate lanes already branch on it
```
r24: gate_671d!=0 -> 0xC6442=1024 | gate_683c!=0 -> 0xC6446=512 (DEAD) |
     state>=5 -> 0xC6440=2048  <-- OSCILLATION ARM | else -> mode-indexed LERP  (smooth steering)
r26: gate_683c!=0 -> 0xC6444=512 (DEAD) |
     state>=5 -> 0xC643E=1536  <-- OSCILLATION ARM | else -> gain_A LERP        (smooth steering)
```
⇒ **Raising only the `state>=5` arms adds damping only once an oscillation has been detected** (then it
holds — see the LATCH section). That is
[[accord-v63-oscillation-gated-rate-damping]]. `gate_683c` is dead (zero `st.b` writers image-wide) so
r26's chain is clean; `gate_671d` **is** live (2 writers) and outranks r24's arm, so r24's coverage is
not guaranteed.

## 🛑 THE POLARITY WAS DISPUTED AND THE ORCHESTRATOR RESOLVED IT IN GHIDRA PERSONALLY
One trace read `gp-0x671a` as a **sign-persistence ramp** that saturates during *smooth* steering and
falls during oscillation — the exact opposite. Acting on it would have raised the **smooth-steering**
gain: all of the manual-feel cost, none of the benefit. Verified directly, twice over:
```
0x3AA70 ld.bu -0x671a[gp],r12 ; 0x3AA78 ld.bu 0x74fa[tp],r14 ; 0x3AA7C cmp r14,r12 ; 0x3AA7E bc
0x3AA80 mov 0x1,r2   <- NOT taken => state >= 5 => r2 = 1
0x3AA88 mov 0x0,r2   <- taken     => state <  5 => r2 = 0
0x3AB64 cmp r0,r2 / 0x3AB66 be -> 0x3AB68 ld.hu 0x743e[tp],r8   => 0xC643E loaded IFF state >= 5
0x3AC0E cmp r0,r2 / 0x3AC10 be -> 0x3AC12 ld.hu 0x7440[tp],r10  => 0xC6440 loaded IFF state >= 5
```
★ **Lesson:** two subagents produced opposite polarities for the same branch, and the wrong one was
*plausible*. **A branch polarity that decides a build's direction must be read by the orchestrator.**
See [[feedback-delegate-firmware-tracing-to-subagents]].

## ⚠ Open, and load-bearing
- **`gp-0x6c2c`'s real amplitude during the vibration is UNMEASURED.** It is a 2-pole IIR-filtered rate
  of `gp-0x4f50` (evidence points to a motor/resolver angle, ISR-captured under `__disable_irq` in
  `FUN_00068fbe` — an inference from usage, not a labelled identity). **If it never crosses ±12800 the
  detector never fires and any edit to these arms is INERT.** ⇒ a null on V63 is ambiguous; resolve by
  then flying V62 (unconditional doubling, cannot miss) rather than by guessing.
- `gp-0x671a` is **not private** to r24/r26 — also read by `FUN_0003a382`, `FUN_000352b4`,
  `FUN_00035b20`, `FUN_00036c12`. Irrelevant to raising the two cals; **very** relevant if anyone ever
  changes `T`/`HYST`/`CEIL`, which would move the detector under all five consumers at once.
- `gp-0x6b5e` (r26's other gate) is a LERP output on axis `gp-0x6bda`, tested only as a boolean. **Not**
  a hands-off or LKAS flag.
- 🛑 **There is NO LKAS-active signal in this path.** `gp-0x6806` (`STEER_CONTROL_ACTIVE`) has exactly 7
  reader/writer functions image-wide and **neither `FUN_0003aa2c` nor `FUN_000428d4` is among them**.
  The reversal counter is the only conditioning available here — which is why it matters.

Related: [[accord-rate-lane-is-the-damper-not-the-amplifier]], [[accord-v62-doubles-the-rate-lane]],
[[accord-v850-scan-traps-formatv-and-storezero]].
