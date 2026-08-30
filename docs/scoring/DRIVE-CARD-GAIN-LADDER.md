# DRIVE CARD — the gain ladder: V241 (6×) · V242 (8×) · V243 (10×)

## 🚗 THE ANSWER TO YOUR BRIEF

You asked for the **safest, highest-probability** firmware at **6× or higher**, with no grinding,
vibration or oscillation — "up to 16×" bounding what to explore, not demanding the maximum.

**Read that way, the answer is V241, not V242.** It is 6× — your car's current gain — carrying all the
grinding work and **no torque lever you have already rejected**. It satisfies "6× or higher" at the
floor and is the build most likely to simply work.

⚠ **I had been leading with V242 (8×) earlier in this session. That was answering "give me more
torque", not what you asked** — and it skips your own ruling, *"fix at 6× first, then raise to 8×"*,
where the fix is built but has never been verified on the car.

```
  V241   6x   <-- FLY THIS FIRST.  Your car's gain. All the grinding work. Nothing else changes.
  39990-TVA,A160-V241-V235BASE-NOTCH.IMU.29.75-22.50-0.940-0x13000-0x100000.rwd
              rwd  57d240d77f568aac...      image 2ef7eb8eb2417905...

  V242   8x   +4 bytes on V241. Fly ONLY if V241 is clean -- then the gain is the only variable.
  39990-TVA,A160-V242-V241BASE-GAIN8X.CLAMPS4096-0x13000-0x100000.rwd
              rwd  a94962b4240613c8...      image 424249b0c7d89fad...

  V243  10x   The ceiling. Only if V242 is also clean. 10x has NEVER flown at any point.
  39990-TVA,A160-V243-V242BASE-GAIN10X.CLAMPS4608.CEILING-0x13000-0x100000.rwd
              rwd  43a32ac352508557...      image 5fb9ad74f104de46...

  FALLBACK at any point:  V122  (what is on your car now)
  BEFORE anything:        kill openpilot/pandad  ->  tmux kill-server
```

**All three live in `../accord-firmwares/flashing-2020accord/rwd/`.** To flash, give me **the exact
filename and the bus** — I will repeat both back to you before anything is sent.

🛑 **The flash decision is yours. Name the file and the bus, and I will repeat both back before
anything happens.**

**Why this order beats flying V242 first.** If V242 grinds you learn nothing — it could be the gain or
the grinding work, and you are back where V101 left you. If **V241** grinds, the grinding work has
failed and 8× is pointless. If V241 is clean, V242 is a **4-byte** step with the grinding question
already answered. Two short drives, and each one is interpretable.

**If you only want one drive and will accept the risk**, fly V242 — it is the same build plus the gain.
The 8× level itself flew fault-free as V101; what you rejected was how it felt.

---

## 🛑 Why there is no 16×

The forward-path clamp must stay **below** the soft-EME floor `0xC674E`, and the clamp tracks the gain
exactly as `gain × 512 // 891`:

```
   6x -> clamp 3072   OK
   8x -> clamp 4096   OK
  10x -> clamp 5120   EQUALS the floor -- V219/V225 had to use 4608 instead
  12x -> clamp 6144   EME AUDIT FAILS
  16x -> clamp 8192   EME AUDIT FAILS
```

⚠ **One correction to be exact about this.** `0xC674E` is **not** at Honda's value on your car —
**Honda ships 1024, and your car carries 5120**, raised 5× by an earlier build. So the floor is already
a modification, not an untouchable factory value.

**What that changes:** reaching 16× would mean raising it *again*, to above 8192 — eight times Honda's
number — on an interlock whose job is to bound how much torque the EPS will hold against you. **I have
left it exactly where your car has it, in all three builds, and I am not going to raise it further on
my own initiative.** If you want that explored, say so and I will price it properly rather than just
doing it.

Even V243's 10× is nominal rather than delivered: its clamp is held at 4608 instead of the exact 5120,
so what actually rises is delivered authority **4096 → 4608, about 12%**.

---

## Safety vs comfort — they are different questions here

**The 8× gain level is proven safe to drive.** V101 flew it: **fault-free**, identity duty 1.000000
over 25,551 frames, 176.1 s engaged, **EME audit passed**, `0xC407E` = 511 unchanged. What you rejected
was how it *felt*, not a failure. V242 sits at that same proven gain.

**The 10× level has never flown at all.** V219 and V225 were built and gated but never driven, so V243
carries an additional unknown that V242 does not. That is why it is third on the ladder and not second.

---

## 🛑 The risk on V242, stated plainly

**8× has flown before, and you rejected it.** V101, route 0x95:

> *"GRINDING/VIBRATION AT ALL SPEEDS, ONLY WHILE LKAS COMMANDS, killed by applying driver torque,
> returning and growing when he lets go."*

You reverted to 6× yourself. The measurement agreed: the peak **moved 20.3 → 23.0 Hz** (a pole moved),
and the de-confounded gain was **2.7–3.9× over 22–26 Hz**.

**Why V242 is not a repeat of V101.** That 22–26 Hz band is exactly what this lineage's notch attacks —
and the notch is now aimed by the comma **IMU**, an instrument physically independent of the EPS, which
independently names 22–30 Hz as the largest engagement-created band on the car. **V101 raised the gain
with no grinding treatment at all. V242 raises it with the best treatment the kit has.**

**It may still grind.** Every part of this lineage is unflown. That is the honest position.

---

## What V242 changes, relative to YOUR CAR — read from the built image

**27 bytes. Nineteen of payload, eight of recomputed CRC.**

```
  0xC60A8..B6   the NOTCH, 4 float32, re-aimed on the IMU        12 B   grinding
  0xC6CD0       THE FORWARD LKAS GAIN   5346 -> 7128 (6x -> 8x)   2 B   torque
  0xC61B3..B5   the two forward clamps  3072 -> 4096              2 B   tracks the gain
  0xC40DC       alpha2  8 -> 22, back to Honda's own value        1 B   restores a damper
  0x55DF2       CAN 427 probe repoint                             2 B   telemetry only
  0xC4FFC / 0xC6FFC   CRC trailers, recomputed                    8 B
```

**V241 is the same list minus the gain and clamps** (23 bytes). **V243 is V242 with only those four
bytes different again** (gain 8910, clamps 4608).

Unchanged from your car, and asserted so in every build: **`0xC674E` = 5120** (the soft-EME floor) and
**`0xC407E` = 511** (the hard-fault interlock).

---

## One limitation of the notch, stated up front

**The notch is aimed using data from 4× builds.** Every route in the profile it was optimised against
is pre-V100, and V242 runs at 8×. The record's one relevant data point says the band *does* move with
gain — V101 put its peak at 23.0 Hz against 20.3 Hz at 4×.

I tried to measure that directly and **the corpus cannot support it**: the 6×/8× era has almost no
speed-matched engaged-*and*-manual exposure (the only 8× route yields 15 s against a 30 s gate). I did
not lower the gate to manufacture an answer.

**What can be said:** the 4× profile peaks at **27.0 Hz**, and V241's trough spans **22.5 → 29.75 Hz**.
If the band moves up with gain, it moves *further into* the trough, not out of it, until about 30 Hz.
That is reassuring — it is not a measurement.

---

## How to drive it

**One episode is enough, and your verdict is final.** If it feels wrong, stop — that is a complete
result.

**Stop and say so if:** grinding or vibration appears at any speed while LKAS is commanding (the V101
signature) · the ratchet is clearly worse · the wheel feels heavier near centre · anything faults.

**Walk the ladder upward, not downward.** V241 first: it is the single most valuable drive on the
shelf, because nothing in this lineage has ever flown and V241 tests the grinding work at the gain you
already run. Only once that is clean does V242's four-byte gain step mean anything.

**If a rung is bad, drop to the one below it:** V243 → V242 → **V241** → **V122** (your car).

---

## What I could not deliver, and why

**No lever for LKAS authority beyond the gain.** The only EPS-side route to more authority is
`0xC6CD0`, which is what this ladder raises. Everything else in the assist path was measured this
session and is either inert or broadband gain reduction — the same trade, arriving through other cells.

**The ratchet is not fixed, and I could not fix it by calibration.** Measured this session: every cal in
the assist path, the one frequency-selective device, and the loop-delay hypothesis — all closed. The
band worth filtering in the torque domain is 6–10 Hz, and the record forbids notching there because the
lane damps. **That rule is now itself in doubt** (it may rest on a rectified channel), which is the
single most promising open thread, but it is not resolved and I have not built on it.

**Grinding and ratcheting are different problems.** Two independent instruments now agree on that.
V242 attacks the grinding; it is not expected to move the ratchet.
