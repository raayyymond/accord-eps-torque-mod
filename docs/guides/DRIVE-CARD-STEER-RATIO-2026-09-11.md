# Drive card — pin the steering-ratio curve past 45°

**~15 min, manual driving only, one large flat open area. 2026-09-11.**

Why: the rack's true ratio is measured and identified from 20° to ~165° of wheel, but every
large-angle sample in 14.2 h of logs is a *transit* — wound in, briefly dwelt, unwound — with the
longest continuous dwell at 0.92 s. These two manoeuvres produce real dwells and a direct
calibration of the transit bias.

🛑 **Manual throughout.** openpilot will not hold a lock or execute a ramp, and driving it manually
buys the firmware-independence check for free — the measurement is kinematic (wheel angle → yaw
rate) and does not care who turns the wheel.

---

## Before you start

- **Drive there on normal roads for ≥5 min** so `calStatus` reads `calibrated`.
- 🛑 **Do not power-cycle the device** between that drive and the manoeuvres — recalibrating
  discards the extrinsic and the whole run is wasted.
- Flat, dry, **≥60 m clear** for the 90°/135° rows. Industrial estate loop, empty retail car park,
  skidpan. A large roundabout serves 45–135° if the site is too small.
- Steady throttle. No mid-circle braking. **Do not sit on the steering hard stop.**

---

## M2 — matched slow ramps · ~4 min · **do this one first**

**This is the higher-value manoeuvre: it retroactively unlocks the 14.2 h of logs already on disk.**

Constant **5 m/s** (11 mph), in an open area, as a continuous in-and-out spiral:

1. Wind steadily **45° → 270°** over about **8 s**
2. Wind steadily back **270° → 45°** over about **8 s**
3. Repeat continuously — **6 cycles**
4. Then **6 more cycles the other way** (opposite hand of lock)

Smooth and even on the wind rate; the exact angles matter less than the rate being steady and the
two directions being matched.

**What it gives:** matched wind-in against wind-out at identical angles and speeds — a direct
measurement of the lag bias that contaminates every large-angle sample in the corpus. Once that
slope is known, **all 80 routes can be debiased without re-driving any of them.**

---

## M1 — constant-lock circles · ~10 min · the ground truth

Manual, constant speed, **equal duration each direction** (cancels road camber to first order).
A constant-lock circle does not *balance* wind-in and wind-out — it **removes** them.

| lock | radius | speed | lateral accel | lap time | do |
|---|---|---|---|---|---|
| 90° | 28.7 m | 6 m/s | 1.25 m/s² | 30 s | 2 laps each way |
| 135° | 19.1 m | 6 m/s | 1.89 m/s² | 20 s | 2 laps each way |
| 180° | 14.2 m | 5 m/s | 1.76 m/s² | 18 s | 3 laps each way |
| 270° | 9.3 m | 4.5 m/s | 2.18 m/s² | 13 s | 3 laps each way |
| 360° | 6.8 m | 4.5 m/s | 2.98 m/s² | 9.5 s | 4 laps each way |

**Hold the wheel dead still** — under 5 °/s. Every row clears the `v > 4 m/s` floor the estimator
needs, at 1.2–3.0 m/s², which is ordinary cornering load.

Two laps at 180° is **36 s of continuous constant-lock dwell**, against a longest episode of
**0.92 s** in everything measured so far.

### Plus the slip lever · 40 s · worth doing

Repeat the **180° circle at 8 m/s** (lateral accel 4.5 m/s² — brisk, fine on dry tarmac).

Same lock, two speeds ⇒ tyre slip is **measured** rather than assumed away. This is the clean
alternative to trusting the bicycle model's book tyre stiffnesses, which an adversarial pass showed
could be off by ~2× without the binned data noticing.

---

## Why slip is not a problem here

At 180° lock the radius is 14.2 m; at 5 m/s the lateral accel is 1.76 m/s² and the linear understeer
correction `1/(1 − sf·v²)` is **1.8 %** — and it is *modelled*, so it is corrected rather than
contaminating. Even a 2× error in `sf` leaves under 1 % at that point. The sustained constant-lock
circle is the **clean** case, not a compromised one.

SNR is strong at the same time: yaw ≈ 0.35 rad/s, and the wheel-speed differential is ~200 LSB of
the 0.01 kph quantiser — so the gyro instrument and the IMU-free wheel-speed instrument both work
and can cross-check each other.

---

## What cannot be fixed by driving

**303° and 380° of wheel are structurally unmeasurable.** 1306 s of data exists above 303° but its
median speed is **1.41 m/s** — that is parking, and only 0.1 s survives the `v > 4` gate. The
estimator divides yaw rate by speed, so that end is out of reach no matter what is driven. Those two
knots stay frozen at the fork's current values.

M1's 360° row gets closer than anything so far, but do not expect it to reach 380°.

---

## Afterwards

Grab the route and say which manoeuvre is where in it. Rough timestamps for the M1 blocks help but
are not essential — constant-lock dwells are easy to find automatically.
