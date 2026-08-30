# DRIVE CARD — V228, and the choice between it and V222

**V228 is V222 minus the 8× gain step. Four bytes apart. They ask you for different things.**

---

## The choice, in one table

| | **V222** | **V228** |
|---|---|---|
| grinding (15–22 Hz) | notch cuts it **3.6×** | **identical** — same notch, same bytes |
| the 8× vibration band (22–26 Hz) | net **0.463×** vs your car | not applicable — no gain raise |
| **ratchet (6–9 Hz)** | **could go either way, including worse** | **protected** |
| **LKAS authority** | **8×** | **6× — unchanged from what you drive now** |
| delta from your car | 23 bytes | **19 bytes** |

**Both carry Lever B at 13107** (2.50× the damping on your car) and the same 20.50 Hz notch. That is
the whole of what they share, and it is the part with evidence behind it.

---

## Why the ratchet is a risk on V222 and not on V228

You flew 8× once before — **V101, route `0x95`** — and reported:

> *"grinding/vibration now exists at all speeds… only occurs during LKAS command… I can get it to go
> away if I apply some torque… as soon as I let go, the grinding returns and grows into a steady
> state."*

V102 went back to 6× at your own choosing. V222 returns to 8×, on the argument that the notch added
since then covers it.

**In the band you actually felt, that argument holds.** 8× brings 1.65× more 22–26 Hz energy; the notch
cuts that band to 0.281× ⇒ **net 0.463×, better than your car**, and it stays a win across the full
uncertainty range.

🛑 **But the notch only spans 15.5–29.8 Hz. At the ratchet it does nothing (0.997).** So on V222:

```
  at 6-9 Hz:   forward gain raise   1.33x - 1.65x   (excitation, UP)
               Lever B raise        2.50x           (damping, UP)
```

Same order of magnitude, Lever B larger — **but that is a closed-loop question and no arithmetic I can
do settles it.** V228 declines that race by not taking the gain: every one of its 19 bytes is either a
damper raise or a filter that is flat at the ratchet.

---

## Which to fly

**Fly V228 if** the ratcheting/stuttering is what bothers you most, or if you want the grinding fix
without putting the ratchet at risk. It cannot cost you anything you have today — authority stays
exactly where it is.

**Fly V222 if** you want the LKAS authority as well and are willing to have the ratchet possibly get
worse in exchange, knowing you can fall back.

⚠ **If you are undecided, V228 is the one that cannot make anything worse.** V222 remains available
afterwards, and flying V228 first also makes V222 interpretable: the two differ in exactly one lever,
so a V228 drive followed by a V222 drive is the cleanest 8×-gain experiment this kit has ever had.

**Fallback order from either:** V221 → V217 → V122 (your car).

---

## ✅ THE PAIR IS PRE-REGISTERED

V228 and V222 differ in the forward gain and **nothing else**, so flying both gives the **first clean 8× experiment** this kit has had — the only prior 8× route, V101, **removed Lever B in the same build**, which is why the record’s 8× evidence is confounded.

What each outcome licenses is fixed **in advance** in `docs/scoring/PREREG-V228-V222-THE-8X-EXPERIMENT.md`, including the honest scope: **~21 engaged minutes per build** settles the m^1.74 dose law at 22–26 Hz, but the pair **cannot settle the ratchet** and **cannot tell a linear gain law from no effect** — those need 38–116 min/arm.

## The drive

Same protocol as V222. **Your symptom verdict is the primary readout.**

🛑 **A short drive cannot prove a band number.** Measured from real cached drives, the smallest change
one 15–30 s episode could establish is **13–15×** for grinding, **11–13×** for 9–12 Hz and **42–45×**
for the ratchet — while the expected effects are **1.2–1.8×**. To resolve them needs roughly **14 min**
of engaged symptomatic driving per arm for grinding and about **7 hours** for the ratchet, which nobody
is going to do.

⇒ **If it feels different, that is the finding.** Say it in your own words. Do not wait for a number to
confirm you, and do not let a short-drive band ratio be read as contradicting you — it cannot.

---

## Limits that apply to both builds

1. **Do not score 30–49 Hz.** Both builds move Honda's 55 Hz notch to 20.50 Hz, and 52–71 Hz folds into
   that band at the ~101 Hz log rate. Any difference there is confounded and cannot be separated
   afterwards.
2. **A ratchet null licenses nothing about `0xC63AE`.** That lever's lane share and even its sign have
   never been measured; it would need a cave sign-bit to settle.
3. The reconstruction work behind all of this is **open-loop**. It says what the firmware computes, not
   what the car does with it.

---

## Verification behind V228

- **72/72** builder assertions · **1138** close-out checks · **100 %** orphan-byte coverage
- image sha256 `6cf12db9fc49aee2…` · rwd sha256 `b90a200ce53c7f37…`
- file: `39990-TVA,A160-V228-V222BASE-GAIN.STAYS.6X.AS.CAR-0x13000-0x100000.rwd`
- builder: `analysis-2020accord/builds/v108_plus/build_v228_tva.py`

🛑 **The flash decision is yours.** Name the file and the bus, and I will repeat both back before
anything happens. openpilot/pandad must be killed first (`tmux kill-server`).
