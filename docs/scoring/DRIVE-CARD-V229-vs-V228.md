# DRIVE CARD — V229 vs V228: the 55 Hz question, open since V172

## 🚗 AT THE CAR

```
  V229   39990-TVA,A160-V229-V228BASE-HONDA.55HZ.NOTCH.RESTORED-0x13000-0x100000.rwd
         rwd sha256 443fa080307cf221...      image sha256 078da4b1f22903a5...

  V228   39990-TVA,A160-V228-V222BASE-GAIN.STAYS.6X.AS.CAR-0x13000-0x100000.rwd
         rwd sha256 b90a200ce53c7f37...      image sha256 6cf12db9fc49aee2...

  BEFORE anything: kill openpilot/pandad  ->  tmux kill-server
```

🛑 **The flash decision is yours. Name the file and the bus, and I will repeat both back before
anything happens.** Nothing is flashed without that.

---

## The one thing to understand

**There is exactly ONE filter cell in this ECU. Honda uses it as a 55 Hz notch.**

Every build since V172 — about 56 of them — has **moved** that cell down to ~20 Hz, to put a cut where
the 15–22 Hz grinding is. Moving it **vacates Honda's 55 Hz cut**. Nobody priced that, because CAN's
Nyquist is 50.5 Hz: 55 Hz folds down and masquerades as 30–49 Hz content, so **no CAN-based instrument
in this kit could ever have seen the bill.**

```
                |H| 18.5 Hz   |H| 55 Hz
  your car         0.8978       0.0063     <- Honda's 159x cut at 55 Hz
  V228             0.2045       0.6285     <- 4.4x quieter at 18 Hz, 100x LOUDER at 55 Hz
  V229             0.8978       0.0063     <- Honda's notch back; V228's 18 Hz cut given up
```

**One 2nd-order section cannot notch 18 Hz and 55 Hz. The trade is structural — no retuning escapes it.**

## Why this is worth a drive

On the alias-free audio, engaged vs not-engaged, **matched on both speed and gear**, bootstrapped over
routes:

```
  band (Hz)    direct acoustic       AM of broadband carrier
  15-22       1.45x [1.03, 3.70]      1.21x [1.05, 1.39]     <- where V228 cuts
  50-60       2.13x [1.13, 3.82]      1.58x [1.10, 2.70]     <- where Honda/V229 cuts
  60-72       2.22x [1.27, 5.04]      1.34x [1.06, 2.05]
```

**Both bands carry real, licensed LKAS-caused noise.** So the question is which cut is worth more —
and the cut depths differ by **32×**: V228 buys 4.9× at 18.5 Hz while giving up 159× at 55 Hz.

⚠ **What is NOT claimed:** that 50–72 Hz is *worse* than 15–22 Hz. Tested properly — paired within
route, because the band CIs overlap — it is **not licensed** on either channel (1.73× [0.48, 2.55]
direct; 1.23× [0.87, 1.86] AM). The notch program is not aimed at the wrong band. It is aimed at one
licensed band out of several, and it pays for that aim with a much deeper cut elsewhere.

## Which to drive

**Drive V229 first.** It is closer to your car than any build in the last 56: the only difference from
V228 is 12 bytes of filter coefficient, and it puts the 9–12 Hz phase back on the one geometry that has
actually been driven. V228 carries −39.3° at 10.5 Hz where nothing has ever flown past −21.3°.

**While driving — the whole job:** *does the car feel acceptable?* One episode is enough and **your
verdict is final.** If it feels wrong, **stop** — that is a complete result.

**Stop and say so if:**
- the **ratchet is clearly worse** than your car → fall back **V221 → V217 → V122**
- anything faults, or the EPS lamp lights

## What each outcome means

| you report | what it settles |
|---|---|
| **V229 better than V228** | the 55 Hz cut matters more than the 18 Hz cut — **56 builds of notch relocation were the wrong trade**, and the direction is to keep Honda's notch and attack 15–22 Hz some other way |
| **V228 better than V229** | your grinding really is at 15–22 Hz; the relocation is justified, and the 54–74 Hz cost is one worth paying |
| **no difference** | the biquad is not where your symptom lives at all, and the whole notch axis can be retired — which would be worth knowing after 56 builds |

**Every one of those is a result.** This is the first single-variable test of an assumption the kit has
been making since V172 without ever checking it.

## Cost, plainly

V229 gives up V228's 4.9× cut at 18.5 Hz. **If your grinding is genuinely at 15–22 Hz, V229 will be
worse there than V228.** That is the honest mirror of V228's own cost, and it is exactly why the pair
is worth driving rather than either alone.

## What V229 keeps

Everything else in V228, byte for byte: Lever B `0xC6446` = 13107 (the kit's only measured on-car win,
from V88), `0xC40DC` = 22, `0xC63AE` = 512, the `0xC407E` = 511 fault interlock, the friction lane at
the car's values, the 427 telemetry tap, and the 164-byte cave **byte-identical** — so this is not the
bricking class.

It also **satisfies a standing constraint V228 violates.** `BUILD-LINEAGE.md` on `0xC40DC`: *"it must
ship WITH the notch revert or not at all."* V228 ships `0xC40DC` = 22 — which passes **more** HF
(corner 21.3 → 67.0 Hz) — alongside a notch that no longer cuts 54–74 Hz. Both cells push the same way.
V229 is that notch revert.
