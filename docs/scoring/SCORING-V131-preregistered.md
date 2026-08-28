# SCORING V131 — pre-registered BEFORE the drive, 2026-08-28

🛑 **Written and committed before any V131 flight exists.** Supersedes `SCORING-V127-preregistered.md`
as the flight card; the V127 rail-duty fork below is carried over unchanged, because V131 inherits
V127's probe.

## What V131 is

V127 + **V62's Lever A restored** (`0x3AB76`, `0x3AC20`: `sar 0xa → 0x9`). 2 payload bytes,
68/68 assertions, CRC 50/50.
image `4bb43e7f15c3df61fa44cfdfda75f25b2cadf6a34ae28d4f4d535f3038315e28`

It is the first image to carry **every edit this kit has ever measured on-car**: V42 `0x454FE`,
V62 Lever A, V88 sign fix, Lever B `0xC6446`, V106's ×3 engaged `Y`, V112's relay ladder, V14's
clamps — plus 8× forward gain, α2 5, `0xC640A` −1966, and the rail-duty probe.

⊕ **V131's rate lane is byte-for-byte V62's** (all six cells verified), so V62's route-37 result is
the historical comparator.

---

## 🛑 WHAT THE DRIVE MUST CONTAIN — this is not optional

V62's headline result (**42× at 18–22 Hz**) was measured at **engaged creep**, in the
`|rate| 16–32 °/s` cell. Scoring r22 vs r23 (both V112) shows that cell is **empty on highway
routes** — n=2 and n=0 — because they speed-match at 36–69 km/h.

⇒ **A highway-only drive cannot reproduce V62's endpoint.** The drive needs:

1. **Engaged creep, 2–10 mph**, with real steering activity — enough to populate `|rate| 16–32 °/s`.
   This is where V62's 42× was measured and where the operator originally said *"grinding is gone."*
2. **Engaged 15–40 mph** — the band the operator currently reports grinding in.
3. **At least one slow hard turn, hands-off, engaged** — the peak-command oscillation. The V122
   instance was segment 11, 09:15:12, 44 km/h, 7.81 Hz.
4. **Some highway** — for the authority leg and the 90 km/h end of the `Y` schedule.

Without (1) the grind endpoint has no comparator; without (3) the oscillation edit is inert by
construction, since `0xC640A` only applies once the reversal counter has saturated.

## Detection floor, stated in advance

Same-firmware routes (r22 vs r23, both V112) give CIs of **[0.80, 1.20] at 21–26 Hz** and
**[0.59, 1.34] at 18–22 Hz**. ⇒ **effects smaller than ~20 % (21–26) or ~40 % (18–22) are not
resolvable on one drive.** Do not read a ratio of 0.9 as an improvement.

---

## PRIMARY — the operator's report

The kit's standing rule is *score bands, let the OPERATOR score symptoms*, and the 21–26 Hz
instrument has already been shown not to track what he hears (V122 read "NOT RESOLVED" while he
reported a real improvement). Three questions, each vs **V122**, the build he last drove:

1. **grinding** — better / same / worse, **and at which speeds**;
2. **peak-turn oscillation**, hands-off engaged in a slow hard turn;
3. **LKAS authority** — V131 is only the second build since V112 to change it (8× vs 6×).
   Expect ×1.333 at the rail, less after the 2.9× efficiency fall ⇒ **≈1.1–1.2× in delivered
   rate**, not 1.33×.

## SECONDARY A — grind bands, `score_v131_grind.py <route> r24`

Episode-clustered, speed-matched, with a **30–40 Hz negative control**. A ratio that moves in the
signal band **and** in the control band is a global change, not a grind result.
Null control (`--null`, r22 vs r23, same firmware) passes: all four bands span 1.0.

## SECONDARY B — the rail-duty fork, `score_v127_rail.py <route>`

Unchanged from the V127 card. Worst engaged bin:

| rails | next build | why |
|---|---|---|
| **> 10 %** | **V129** (`Y[2]` → −5898) | the term is a relay; de-rail it |
| **≤ 2 %** | **V130** (`Y[1]/Y[2]` ×1.856) | the term is LINEAR ⇒ the deficit is DAMPING |
| **2–10 %** | neither as built | size `Y` to the measured duty |

⚠ If the drive contains **no oscillation episode**, the counter never saturates, `0xC640A` is
inert by construction, and the rail bins will read near zero **for the wrong reason**. **Check the
engaged-episode count before concluding.**

## What will NOT be claimed

- No spectrum from the 427 wire (49.9 Hz ⇒ Nyquist 24.95; the lane lives at 25–153 Hz).
- No open-loop rail-duty prediction — V107 missed by **32×** because the lane is a closed loop.
- No grind claim from the 427 wire; grind is scored from `cs_rate` at 99.8 Hz, or by the operator.

## Confounds stated in advance

- **V131 changes both the rate lane and, vs V122, the forward gain.** They are not separable on
  one drive. The rate-lane change is expected to reduce grinding; the gain change to increase
  assist and, per `accord-the-8x-gain-is-the-carrier`, to *increase* the ~23 Hz excitation. If
  grinding is unchanged, that cancellation is a live explanation and not a null.
- **α2 and `Y` multiply**, and V131 sits at 0.54× of V106's in-band damping product. The rate-lane
  restore does not change that; only V129/V130 do.
