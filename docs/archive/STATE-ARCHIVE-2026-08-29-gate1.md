# STATE archive

A RECORD, NOT AN INSTRUCTION.

## ✅✅✅ **WHICH LANES ACTUALLY DAMP AT 7.8 Hz — AND V158 SIZED IN PHYSICAL UNITS**
The `gp-0x6ad4` result generalises into a method: **compute each lane's phase at the symptom's own
frequency before touching it.** Applied to every sensor-fed survivor:
```
   lane          structure                              phase @7.8 Hz     verdict
   gp-0x6ad4     P 99.88 % @0.0 deg (IIR pole = 1024    -1.7 deg          STIFFNESS -- ELIMINATED
                 => PASS-THROUGH), D 0.02 %                                (structural, u16-bound)
   gp-0x6b26     -K x ACCELERATION (gp-0x6c2c is a      +180 deg vs pos   ADDED INERTIA -- lowers f0,
                 first difference of filtered rate)                        does NOT damp
   gp-0x6bbe     MEASURED on-car: 90 ct/(rad/s),        ~0 deg vs RATE    TRUE VISCOUS DAMPING
                 phase ~0 vs rate, DC pedestal 73.6 ct
   gp-0x6bd0     -sign(gp-0x6abe) x f(|rate|, speed)    ~0 deg vs RATE    VISCOUS *if* f is linear
                 = odd-symmetric in rate                                   in |rate| -- V158's target
   r24           K x d(torque)/dt                       +90 deg vs torque DERIVATIVE -- damping,
                 (Lever B 0xC6446)                                         MEASURED by V88
```
⭐ **THE TWO LEVERS THIS KIT HAS ARE THE TWO THAT ACTUALLY DAMP** — V158 on `gp-0x6bd0` and Lever B on
r24. That is not luck; it is why they are the two that measured well.

### ✅ V158 IS GENUINELY VISCOUS, NOT A RELAY — MEASURED FROM ITS OWN BYTES
```
   rate_ct   deg/s    dose    dose/rate        a RELAY would fall 6.5x across this span
      40      8.5      15      0.3750
      99     21.0      50      0.5051          <- the ratchet's operating point
     260     55.2     144      0.5538
```
=> `dose/rate` is **near-CONSTANT (0.375 -> 0.554) across a 6.5x rate span.** ✅ **[EVIDENCE] GATE 2's
rate-proportionality requirement is satisfied empirically, not just by the monotone shape.**

### ⭐ V158 SIZED AGAINST AN INDEPENDENTLY MEASURED ON-CAR QUANTITY
```
   stock / V122 at creep        0.000 ct/(deg/s)     FactorC Y[0] = 0 kills the product
   gp-0x6bbe   (measured)       1.571 ct/(deg/s)     = 90 ct/(rad/s), on-car, independent
   V158 damper (from bytes)     2.733 ct/(deg/s)     local slope at the operating point
   ------------------------------------------------
   TOTAL creep viscous          1.571 -> 4.304       = x2.74
```
✅ **[EVIDENCE] V158 adds 1.74x the viscous damping the car already had at creep**, expressed in the
SAME aggregator counts as a quantity measured on the car. This turns "dose 50" from an abstract
number into a physical damping increment.
⚠ **[BELIEF] what that buys in ζ.** If the firmware's viscous term were the DOMINANT damping source,
ζ would scale with it: **0.017–0.036 -> 0.047–0.099**. If mechanical damping dominates, less. The
split cannot be resolved without a drive, so **treat 2.74x as the firmware-side increment, not a ζ
prediction.**

### ⚠ ONE OPEN DETAIL — SUB-LINEARITY AT THE VERY BOTTOM
`dose ∝ (rate − 12)` inside FactorE's first segment, so `dose/rate = k(1 − 12/rate)` → 0 as rate → 12:
the damping fades in the DEEPEST micro regime. Setting `X[0] = 0` would make it exactly linear through
the origin — **but the golden model argues X[0] = 12 deliberately** (*"a firmware review flagged X0 < 30
with Y1 > 300 as the zone it would not fly without telemetry; 12 is the TOP of its own 6–12 band"*).
**NOT changed.** Recorded as a known, deliberate limitation.
⊕ Headroom exists but is NOT taken: the build-time rule `(FactorC x FactorE[3])>>10 ≤ 512` reads **388**,
and FactorE `Y=[0,700,700,927]` would give dose 65. **The model's own requirement is ~43 [30,60] and
V158's 50 sits inside it** — exceeding a stated requirement without cause is what produced six
superseded builds this session. **Left at 50.**

