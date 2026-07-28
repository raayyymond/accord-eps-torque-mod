# ★ V56 BUILT, UNFLASHED — V55's probe + the `0xC6AF0` mute

**Built 2026-07-28.** All gates pass; independently spot-checked with a fresh little-endian Python read.

```
_v56_plain_image.bin  SHA 8c5c8a73425bf269c03b2e93144a7b8340983e5d873d70ea6009c0e68eacc7a0
V56 .rwd              SHA ffccf6e779498379e5d31326ba5bd7ed68da189d362b5f7ed925499df68343f4
```

**V56 = V55 + exactly 6 bytes:** `0xC6AFC` Y[0] 32768→0, `0xC6AFE` Y[1] 32768→0, + the CAL CRC trailer.
Only 2 cal bytes actually move — `32768 = 00 80` little-endian, so muting to 0 changes only the **high**
byte of each halfword. 84 bytes off V38 total. 50/50 CRC blocks, both bootloader walks, RWD decode-back
with every gate re-run on the readback. Count word and X row asserted unchanged; Y[2..4] asserted stock;
V55's cave and hook byte-identical.

**Builder is a POST-PROCESSOR over `_v55_plain_image.bin`** (`build_v56_tva.py`) — it transcribes nothing
from V55, not the cave, not the hook, not the encoders. Same principle V53 used with FOURFRAME2's cave;
it removes the whole class of transcription defects.

⚠ **`V53.assert_stock_cals()` correctly refused this edit** — it asserts the `0xC6AF0` LERP must stay
stock because "its edit direction is UNRESOLVED". V54's drive resolved that direction. **Do not weaken
that shared guard** (five builders depend on it). V56 instead runs the **unmodified** guard against the
pre-edit V55 source and re-expands its other two components (`STOCK_CALS` dict + ratchet check) against
the post-edit image, so coverage is strictly preserved.

⚠ **Build gate caught a real over-specification of mine:** the initial diff assert expected 4 changed cal
bytes and got 2. The gate was right; the expectation was wrong. Fixed to assert *containment* in the
permitted footprint plus explicit halfword-value checks plus "the CRC trailer must have moved".

## Why this and not the `0xC646C` decoupling
The operator proposed decoupling the 4× gain onto the LKAS-only path for V56. **It cannot fix the
vibration:** `FUN_0003a382` is **not among the six `0xC646C` readers** (function-scoped search: 0 matches
across 468 instructions), so the retarget would not touch the carrier at all. Do it as the *correctness*
fix it is — it is verified safe and byte-minimal — but not as the vibration lever.
See [[reference-accord-c646c-shared-gain-not-lkas-only]].

## What the drive should answer
Keep the probe: this is a lever **and** a measurement.
- vibration gone → root cause found.
- vibration persists **but the command's 21 Hz drops** → the lane was a carrier, not the loop.
- neither moves → `gp-0x6ad4` eliminated as a class; next candidates are `0xC6372`/`0xC636E`.

🛑 **GATE 2 is only partially closed** — damping sign and manual feel are open. Reversible experiment,
not a known-good fix. Revert = reflash V55.
See [[reference-accord-gp6ad4-lane-and-c6af0-output-gate]].

🛑 **Flash only on explicit operator instruction naming the file and the bus.**
