# DRIVE CARD — the gain ladder: V241 (6×) · V242 (8×) · V243 (10×)

## 🚗 THE ANSWER TO YOUR BRIEF, IN ONE PLACE

You asked for the safest, highest-probability firmware at **6× or higher, up to 16×**, with no
grinding, vibration or oscillation.

**16× is not available, and neither is 12×.** Not a judgement call — a structural interlock. See below.
**~10× is the ceiling.** Here is the whole ladder, all three on the identical grinding work:

```
  V241   6x   39990-TVA,A160-V241-V235BASE-NOTCH.IMU.29.75-22.50-0.940-...rwd
              rwd 57d240d77f568aac...   image 2ef7eb8eb2417905...
              SAME gain as your car. Safest. Isolates the grinding work.

  V242   8x   39990-TVA,A160-V242-V241BASE-GAIN8X.CLAMPS4096-...rwd          <-- RECOMMENDED
              rwd a94962b4240613c8...   image 424249b0c7d89fad...
              Your own sequence: "fix at 6x first, then raise to 8x."

  V243  10x   39990-TVA,A160-V243-V242BASE-GAIN10X.CLAMPS4608.CEILING-...rwd
              rwd 43a32ac352508557...   image 5fb9ad74f104de46...
              The structural ceiling. Only if V242 is clean.

  BEFORE anything: kill openpilot/pandad   ->  tmux kill-server
```

🛑 **The flash decision is yours. Name the file and the bus, and I will repeat both back before
anything happens.**

---

## 🛑 Why there is no 16×

The forward-path clamp must stay **below** the soft-EME floor `0xC674E` = 5120, and the clamp tracks
the gain exactly as `gain × 512 // 891`:

```
   6x -> clamp 3072   OK
   8x -> clamp 4096   OK
  10x -> clamp 5120   EQUALS the floor -- V219/V225 had to use 4608 instead
  12x -> clamp 6144   EME AUDIT FAILS
  16x -> clamp 8192   EME AUDIT FAILS
```

Above ~10× **the command cannot be delivered** — it would be clipped long before the nominal gain was
reached, and getting there means raising a safety interlock. **I have not touched `0xC674E`, and I
would not without you telling me to explicitly.** Every build here asserts it frozen at 5120.

Even V243's 10× is nominal, not delivered: its clamp is held at 4608 rather than the exact 5120, so
what actually rises is delivered authority **4096 → 4608**, about 12%.

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

## What all three carry

**V241 against your car: 23 payload bytes.** V242 and V243 add exactly **4 more** (gain + two clamps).

```
  0xC60A8/AC/B0/B4   the notch, aimed on the IMU (29.75 / 22.50 / 0.940)   12 B   grinding
  0xC40DC            alpha2 8 -> 22, Honda's own value                      1 B   restores a damper
  0x55DF2 / 0x55E10  the biquad-state probe on CAN 427                      3 B   telemetry only
  0xC63AE            back to Honda's 1024                                   2 B   (in V235)
  0xC6446            Lever B at V88's measured optimum, 5244                2 B   (in V234)
  ---- V242/V243 only ----
  0xC6CD0            the forward LKAS gain                                  2 B
  0xC61B2 / 0xC61B4  the two tracking clamps                                2 B
```

The notch geometry beats V235's by **28%** on the measured objective, survives **leave-one-route-out on
all ten routes**, and wins under **five of six** objective weightings. It also cuts *less* of the band
the lane damps in than V235 did — V235 was slightly below Honda's own floor there.

---

## How to drive it

**One episode is enough, and your verdict is final.** If it feels wrong, stop — that is a complete
result.

**Stop and say so if:** grinding or vibration appears at any speed while LKAS is commanding (the V101
signature) · the ratchet is clearly worse · the wheel feels heavier near centre · anything faults.

**The ladder is meant to be walked in order.** If V242 grinds, V241 tells you whether the grinding work
itself is sound at your current gain — that is the single most valuable drive on the shelf, because
nothing in this lineage has ever flown.

**Fallbacks:** V242 → **V241** → **V122** (your car).

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
