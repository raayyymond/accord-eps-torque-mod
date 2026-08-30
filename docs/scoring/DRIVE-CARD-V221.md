# DRIVE CARD — V221 · **the new primary. V217 is now the fallback.**

**Flash target:** `39990-TVA,A160-V221-V217BASE-LEVERB.5244.TO.13107-0x13000-0x100000.rwd`
**.rwd SHA256** `f8c49be81ca685f123b3e8b2209655a8eb647e2059c7bc2912183cff1681ed1e`
**image SHA256** `7bb0ba58956ca21064a815d0298c6994cf124b941c72aa76c03f8628a598c51b`

> 🛑 **Nothing here authorises a flash.** Name the file and the bus yourself and they will be read
> back to you first. Kill openpilot/pandad (`tmux kill-server`) before any flash operation.

---

## What is on it — 27 payload bytes from YOUR CAR (V122)

```
  0xC60A8/AC/B0/B4   notch 20.50 Hz            GRINDING       (18-22 Hz)
  0xC63AE            1024 -> 512               RATCHET        (~7.8 Hz)
  0xC6CD0 + clamps   6x -> 8x                  LKAS AUTHORITY (+28.9 %)
  0xC6446            5244 -> 13107   <-- NEW   LEVER B: less HF EVERYWHERE, no LF cost
  0x55DF2            427 probe -> gp-0x6b4e    the instrument
```

**V221 is V217 plus two bytes.** Everything V217 carries — the damper restoration, the notch, the
gain step, the two known deltas from your car (`0xC40DC` accel alpha, and the friction ramp
saturating at 50 °/s instead of 250) — is byte-for-byte identical. See `DRIVE-CARD-V217.md` for
those; they are unchanged and unrepeated here.

---

## Why this build exists — the record understated its own best lever by 10×

**Lever B is the only thing this kit has ever changed that moved both symptom families at once with
the LKAS command measurably untouched.** V88 vs V87, single-variable, speed-matched, on your car:

```
   0.5-3 Hz   1.192 [0.780, 1.812]  NULL   <- peak effective LKAS command, UNTOUCHED
   3-6        1.165
   6-9        0.859                        <- the ratchet's band
   9-12       0.604 [0.465, 0.943]
   15-22 Hz   0.549 [0.407, 0.844]         <- the grinding band
   28-35 Hz   1.13x / 0.94x  FLAT          <- aliasing control, two independent channels
```

Your own report on that drive was **grinding fixed, command intact**. It has sat frozen at 5244 for
**130+ builds since V67**, because V160 declared 6553 a hard arithmetic ceiling:

> *"6553 is the EXACT int16 ceiling for this lane, not an arbitrary number:
> `(5120 × 6553) >> 10 = 32765 ≤ 32767` fits · `(5120 × 6554) >> 10 = 32770` OVERFLOWS"*

**That is false, and it is wrong by a factor of ten.** There is no int16 anywhere on the path —
decompiled first, then confirmed instruction by instruction:

```
  0003ac08  ld.hu  0x7446, tp, r10   ; the gain cal, ZERO-EXTENDED  -> its range is 0..65535
  0003ac18  mul    r10, r8, r0       ; 32-BIT multiply; the high word goes to r0 and is DISCARDED
  0003ac20  sar    0xa, r8           ; >>10, still a 32-bit register
  0003ac42  addi   -0x2000, r6, r0   ; and ONLY HERE is it bounded -- the +-8192 output clamp
```

No `st.h`, no sign-extend, no halfword store between the multiply and the clamp. Worst case
`5120 × 65535 = 3.4e8` sits an order of magnitude inside int32. ⇒ **the real headroom above your car
is 12.5×, not 1.25×.** V160's 6553 was built three times, never flown, and orphaned at a rebase.

---

## Why 13107 and not more

The gain sets **where the damper stops being a damper and becomes a rail** — nothing else. It cannot
raise the lane's peak output, which the ±8192 clamp fixes:

```
   gain    512   V87 stock          saturates at 16384  = 320% of the input clamp -- NEVER
   gain   5244   V88..V122 YOUR CAR                1600 =  31%
   gain  13107   THIS BUILD                         640 =  12.5%
   gain  65535   cal maximum                        128 =   2.5%
```

Measured `|d(column torque)/dt|` on engaged frames — **your car's own route `r24`: p50 27, p90 146,
p99 610, max 1669**; pooled over 412,204 frames on eight routes: p50 64, p90 483, p99 1222. The
golden model's independent figure for normal driving (123–839 counts) agrees. So at 13107 the whole
micro regime — where ratcheting and grinding live — stays **fully linear**, p50 sitting 10–24× below
the onset, and ~94 % of engaged frames never touch the rail.

🛑 **It cannot cost LKAS authority, structurally.** Raising the *rail* is the one change in this path
that could let a derivative lane eat the ±10240 aggregator headroom your steering command needs. All
22 bytes of that rail are asserted **byte-identical** to the base. We raise the gain and leave the
rail alone, so r24 cannot claim one more count of the aggregator than it already could.

---

## The drive — identical protocol to V217

~15–30 s engaged is enough. **If you feel micro-ratcheting or grinding, stop.** That is a result.

1. **Creep, hands-off**, ~0.5–1.5 m/s, engaged.
2. **Hands-on**, same speeds.
3. If nothing is objectionable, **one highway stretch** for the 18–22 Hz grind band.

```
python rlog-tools/score/score_drive.py <tag> V221        # NAME THE BUILD -- it is not optional
python rlog-tools/score/score_authority.py <tag> V221    # NEW -- the authority readout below
python rlog-tools/probe/decode_v204_observer_lane.py <tag> --v209
```

⚠ **The authority readout needs some curvature at speed.** Creep in a straight line cannot exercise
the command; the bins will be empty and it will say so rather than guess.

---

## LKAS authority now has a direct measurement — and it changes what the 8× step means

**Your command rails.** `sc_tq` pins at ±4096 on **2.7 % of engaged frames on your own drive**, in
**sustained runs of 475–732 ms** (up to 6 s), same-signed between runs, with steering rate 6–21×
higher than off-rail. So these are honest saturations during real manoeuvres — **not** hunting, and
not a decode artifact. On r24 the command's p90 is 733 but its **p99 is the rail**: small nearly all
the time, then pinned.

**When the command is pinned, openpilot has no authority left.** That makes rail duty — at matched
lateral demand, `|curvature| × speed²` — a direct authority metric that needs no model of the plant.

```
   demand |curv|*v^2      0.00-0.15  0.15-0.40  0.40-0.80  0.80-1.60    1.60+
   4x  (Lever B present)      8.81%     20.27%     19.82%     31.48%   34.96%
   6x  (Lever B present)      1.06%      3.89%      4.81%     13.65%   23.04%
     -> improvement            8.3x       5.2x       4.1x       2.3x     1.5x
   r24 = YOUR CAR (6x)        1.16%      2.46%      3.99%     19.47%   22.63%
```

⇒ **more EPS forward gain buys authority back, and by a lot** — 4–8× fewer railed frames in the low
and mid bins, shrinking as demand rises, which is the shape you would expect.

🛑 **AND THE APPARENT COUNTER-EVIDENCE AT 8× IS A CONFOUND.** There is exactly **one** 8× route in the
whole corpus — r95, build V101 — and it appears to rail far worse (33 %, 48 %, 56 % in the upper
bins). **V101 removed Lever B in the same build.** Byte-checked: `0xC6446` = **512** (stock) and its
arm `0x3AA96` = **c5** (stock), against 5244/`fb` on every other build in the comparison. It raised
forward gain and deleted the loop-damping lever at once, and more gain with less damping needs more
command to hold a line — exactly what it shows.

⇒ **the corpus has no clean 8× data point**, and **V221 is the first build ever to pair 8× gain with
Lever B raised rather than removed** — the opposite of V101's combination.

⚠ Honest limit: a V221 drive moves gain *and* Lever B together against your car, so a good authority
result cannot be attributed to either alone. **V216 is the same build at 6×** if you want that split.

---

## What each outcome means

| what you report | what it means | next build |
|---|---|---|
| **Grinding gone, ratchet gone** | everything landed | nothing — hold V221 |
| **Grinding clearly better than you remember** | Lever B is still on the rising part of its curve | consider a further step; 12.5× of headroom remains |
| **Grinding better, ratchet unchanged** | the **expected** outcome | **V218** if you want the ratchet dose ladder closed |
| **Grinding WORSE than V217 would have been** | **5244 was already at or past the optimum** — a real possibility, see below | fall back to **V217**, which is built and published |
| **Steering feels notchy or noisy on fast inputs** | the rail is being hit more often than the estimate predicted | fall back to **V217** |
| **Both better, steering still too heavy/slow** | authority short | **V219** (10×, +56 %) |

🛑 **THE HONEST RISK: only two dose points for this lever exist.** 512 and 5244. V62's lesson is
explicit — *"2× is approximately the OPTIMUM, not a point on a ramp"* — so **5244 could already be at
or past the best value**, and this build would then be worse than V217. It is a **dose probe as much
as a fix**, and one drive settles it in the direction that matters: your report.

⚠ More derivative feedback also amplifies torque-sensor noise. V88 measured 28–35 Hz **flat** across
a 10.24× step, which is the reassuring direction, but this build adds a further 2.5× on top of that
and no one has measured there.

🛑 **The ratchet expectation is unchanged from the V217 card and is still a long shot** — a
lightly-damped mechanical resonance (Q 14–29) on the motor/rack side, with limit cycle, stick-slip,
rate-limit and backlash each separately excluded. Read that section on the V217 card; it applies here
verbatim.

---

## Verification behind this build

- **68/68 build assertions**, CRC 50/50, `.rwd` decodes byte-identical to the built image.
- **835 close-out assertions**, 13/13 shelf builders reproduce bit-for-bit.
- Blast radius: `0xC6446` has **exactly one reader** (`ld.hu 0x7446, tp, r10` @ `0x3AC08`, seen
  directly in the disassembly) and **zero writers**. No float mirror. CRC block #48. Cal-only, one
  halfword, outside the cave/bricking class and recoverable by reflashing.
- Pre-registration: `docs/scoring/SCORING-V217-preregistered.md` applies unchanged; the Lever B
  readout is the 15–22 Hz and 9–12 Hz bands, pre-registered to move **down** relative to V217.
