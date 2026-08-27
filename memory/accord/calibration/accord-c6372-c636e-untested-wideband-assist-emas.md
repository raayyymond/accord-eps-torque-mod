# ★ `0xC6372` / `0xC636E` — the only OTHER wideband lanes, and they are UNTESTED

**Byte-read little-endian 2026-07-28** from `_v55_plain_image.bin` and stock `code.bin`: both = **205**,
identical in stock and every build.

```python
# first-stage input EMA on the raw torsion bar, 1 kHz task
#   0xC6372 -> FUN_00034a72 -> gp-0x6bbe   the boost curve proper (base power steering), bound ±2048
#   0xC636E -> FUN_00034350 -> gp-0x6bd0   the damping lane,                             bound ±2048
alpha = 205                                   # /1024 = 0.2002
y += (alpha * (x - y)) >> 10

# exact digital response (the analog alpha/(2*pi*T) approximation is poor at alpha=0.2)
#   H(z) = a / (1 - (1-a) z^-1),  w = 2*pi*21/1000
#   |H| = 0.8616  = -1.29 dB      phase = -26.9 deg
```

⇒ **They pass 21 Hz essentially unattenuated.** Together with `gp-0x6ad4` (0 dB, both poles exact
identities) these are the only lanes into `gp-0x6b98` that are not band-limited well below 21 Hz:

| lane | at 21 Hz | bound |
|---|---|---|
| `gp-0x6ad4` `FUN_0003a382` | **0.00 dB** | ±10240 |
| `gp-0x6bbe` / `gp-0x6bd0` | **−1.29 dB** | ±2048 each |
| `gp-0x6b86` `FUN_000352b4` | −3.9 dB, adaptive (widens when the signal swings fast) | ±12288 |
| `gp-0x6b4c` LKAS | −12.0 dB | ±10240 |
| `FUN_00036682` | −27.0 dB | ±512 |

## Never flashed — and previously considered
`builds/v18_v49/build_v44_tva.py` pins **both** in `STOCK_CALS` as *"damping lane input EMA — NOT touched"* and
*"boost lane input EMA — **the rejected candidate B**, NOT touched"*. So they are genuinely untested, and
were rejected on judgement rather than evidence.

Lowering alpha attenuates 21 Hz in those lanes, cutting loop gain:

```python
# a=205 -> |H(21)|=0.862 (-1.3 dB), phase -26.9 deg   [stock]
# a= 64 -> |H(21)|=0.440 (-7.1 dB), phase -60.2 deg
# a= 32 -> |H(21)|=0.234 (-12.6 dB), phase -72.7 deg
```

🛑 **GATE 2 is SEVERE here, and it is the reason this is candidate #2 not #1.** `gp-0x6bbe` is the boost
curve — **base power steering itself**, always on. Lowering alpha adds 60-73° of phase lag to the
always-on assist loop. **That is the exact class that bricked V48B** ("an unmodelled lightly-damped
resonator inserted into the always-on base-assist loop"). Do not build this without its own GATE 2 pass
covering magnitude *and* phase in the assist loop.

⚠ Note the coincidence trap: `205/1024 = 0.2002` looks like it matches the measured 0.19-0.22
sensor→command transfer. **It does not — alpha is the filter pole, not the gain.** A one-pole EMA has DC
gain 1.0.

See [[reference-accord-v55-flashed-oscillation-is-internal]],
[[reference-accord-gp6ad4-lane-and-c6af0-output-gate]].
