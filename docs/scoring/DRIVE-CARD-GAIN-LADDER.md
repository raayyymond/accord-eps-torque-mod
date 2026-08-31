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

## ⭐ V246 — THE ONE BUILD THAT ATTACKS THE RATCHET WITHOUT TAKING TORQUE AWAY

Everything above says the ratchet is priced in gain: more torque, more ratchet. **V246 is the one
exception found**, and it is why the ladder now has a fifth rung.

The ratchet's anti-damping tracks the **forward gain** — but I checked three ways round that and closed
all three by arithmetic, needing no drive from you:

```
  the tracking CLAMP      follows the gain automatically  ->  a clamp-only build does NOTHING
  the 0xC646C feedback    contributes 0.7% at 7.8 Hz      ->  zeroing it moves ~0.1 of 65
  a low-pass on command   command has ~0.3% of its        ->  there is nothing there to filter
                          energy in the ratchet band
```

**Lever B is the one cell that is not tied to your torque and still moves the ratchet.** Holding the
gain fixed at 6×, the builds carrying the higher dose are measurably less anti-damped:

```
  at 6x gain    Lever B  512  ->  Re(Z) -73.59
                Lever B 5244  ->  Re(Z) -67.78      +5.81 better, p = 0.056
```

Your car already runs 5244. **V246 goes to 7866 (1.5×)** — and the headroom is computed, not guessed:
the lane saturates, and its knee sits at 58624 at typical steering effort, so 5244 is nowhere near it.
Raising it still buys real damping.

⚠ **The honest risk:** 5244 is the value **V88 measured as best for grinding**. V246 deliberately moves
off it. Whether that costs grinding is **not established** — the only comparison I have is uncontrolled
and its groups overlap, so I am not claiming it either way. That is exactly what your drive settles.

**Fly V241 first, then V246 on the same roads.** They differ by two bytes and nothing else, so if the
ratchet improves, Lever B did it — and if grinding comes back, the answer is 5244 and we have priced
the lever in one drive.

---

## 🛑 NEW, AND IT PRICES THE LADDER: THE GAIN *IS* THE RATCHET

Measured after the card was first written, on instruments independent of the EPS. **The 6–9 Hz
anti-damping — the thing that makes the wheel ratchet — tracks the LKAS gain across every build you
have ever flown.**

```
  4x  (7 builds)   Re(Z)  -46.6 .. -66.8      less negative = less ratchet
  6x  (9 builds)   Re(Z)  -62.3 .. -74.9
  8x  (1 build)    Re(Z)  -84.1
```

Gain went up over time, so a trend alone would prove nothing. **A reversal is the era-free test —
and one of its two legs is clean while the other is not**, because V101 also removed Lever B in
the same step:

```
  V100   4x  LeverB 5244  ->  -66.83
  V101   8x  LeverB  512  ->  -84.06    both changed -- CONFOUNDED
  V102   6x  LeverB  512  ->  -74.91    LeverB held  -- CLEAN, ratchet better by 9.15
```

So the era-free evidence is **one clean pair**, not two. The overall association is strong (rho −0.819, and −0.762 within builds sharing one Lever B value), but **build era cannot be fully separated from gain in this corpus.**

**Status: gain is the best-supported explanation for the ratchet, not a proven one.** In your terms:

| build | gain | expected ratchet vs your car today |
|---|---|---|
| **V241** | 6× | **the same** — this is your car's present gain |
| V242 | 8× | **likely worse** — supported, not proven |
| V243 | 10× | **likely worse still** |

**This does not withdraw V242 or V243.** You asked for the ladder, it is built and verified, and the
authority is real. What changed is that the trade is no longer unknown: **more torque buys more
ratchet, and now there is a number on it.** If the ratchet is the symptom you care most about,
**V241 is not just the safe first step — it is the best rung on the ladder.**

⚠ One route per build and 75–170 windows each, so treat this as a **priced trade-off, not a
controlled experiment**. The reversal is what carries it, not the regression line.

⭐ **Why this is the most useful thing found in the whole arc:** it explains why sixty builds of
cals, filters, dampers, caves and notches all measured null on the ratchet — **none of them changed
the thing that sets it.** Reader: `rlog-tools/score/gain_vs_antidamping.py`.

---

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

  V246   6x   <-- FLY THIS SECOND, right after V241, on the same roads.
              The ONLY build that targets the RATCHET without costing you torque.
              2 bytes on V241: Lever B 5244 -> 7866. Identical notch, identical gain.
  39990-TVA,A160-V246-V241BASE-LEVERB.5244.TO.7866-0x13000-0x100000.rwd
              rwd  f336b0d53d335fde...      image c97e535f3177c564...

  FALLBACK at any point:  V122  (what is on your car now)
  BEFORE anything:        kill openpilot/pandad  ->  tmux kill-server
```

**🛑 A FOURTH BUILD, AIMED AT THE RATCHET — and it is additive, not a trade:**

```
  V245        V241 + the resonance-PID ceiling knee.  TWO bytes on V241, ONE payload byte.
  39990-TVA,A160-V245-V241BASE-RESPID.KNEE.1280.TO.512-0x13000-0x100000.rwd
              rwd  00bc8ddbb0135cd3...      image 10494d5fe6a948ef...
```

The record calls `gp-0x6ad4` **"the most reachable authority of any gated lane"**, and V56's mute of it
was scored at ~21 Hz **only** — **it has never been scored at 6–9 Hz**. The return-to-centre analysis
narrows the ratchet's entry to five sensor-fed lanes; four are spoken for. **This is the fifth**, and
it is virgin in 216 of 218 images.

The lever moves the ceiling knee from **20 km/h to 8 km/h**, so the lane reaches full authority through
the **creep band** where the ratchet lives — and is **identical above 20 km/h**. It does not touch the
biquad, so **V241's whole grinding treatment is carried**.

⚠ **This is an OPEN lever, not a predicted fix.** More ceiling means more authority, and if the lane's
phase at 6–9 Hz is wrong, that means more **pumping** — a *worse* ratchet. Nobody has scored this lane
in that band, which is exactly why it is worth a drive and exactly why I cannot tell you which way it
will go. Two bytes, cal-only, no cave, nothing changes above 20 km/h, instantly revertible.

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

## The third symptom you named: "peak command oscillation"

**It has been tested, and as literally stated it does not exist in the data.** Both readings this bus
can observe were checked with controls, and both were refuted. The roughness runs the *other* way:

```
  command p90 quartile     n     roughness ratio  P(6-30Hz)/P(0.5-3Hz)
        76 -   276        928        2.4877
       276 -   473        928        2.8547
       473 -  1161        928        2.4342
      1161 -  4096        928        0.6637   <- 3.7x SMOOTHER
  log roughness vs log command   corr -0.358, p<0.0001, all five routes agree
```

**The car gets smoother as the command grows.** High-frequency power does rise with command
(corr +0.491) — but low-frequency power rises *faster* (+0.793), so the ratio falls.

⇒ **The roughness you feel is a SMALL-command phenomenon**: gentle steering, holding a straight line —
not peak demand. That matches the ratchet living at creep, 1–13 °/s.

⚠ **Do not read that as "so more gain will be smoother."** It is a within-build correlation across
operating points, not a between-build prediction — and V101 at 8× ground badly, which is direct
evidence against that inference. Raising the gain moves the loop, not just where you sit on the command
axis.

**None of these three builds targets peak-command oscillation, and none of them claims to.** The
useful consequence is the opposite of intuition: levers have to be sized for the **micro** regime, and
that is what this lineage does — Lever B sits at 5244, its saturation onset at 640 counts against an
engaged torque-rate p90 of 146, deliberately keeping the small-signal region linear.

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
