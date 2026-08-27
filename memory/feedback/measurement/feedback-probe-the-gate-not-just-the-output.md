# 🛑 Probe the GATE and the INPUT, not just the output

**Standing lesson from V63 → V64, 2026-07-31.**

**V64's probe was built to remove V63's ambiguity, and it worked.** A bare V63 null could not distinguish
*"the detector never tripped"* from *"the damping rise was too small"*, and V64's bit6 separated them
cleanly on the first drive. That was the right call and it saved a flash.

**But it measured the mechanism's OUTPUT (`gp-0x671a`, `gp-0x67df`, `gp-0x671d`) and not its INPUT or its
ENABLE.** So when all four bits read zero, a *new* ambiguity appeared one layer up:

- did `|gp-0x6c2c|` never reach `T`? — or
- did `FUN_000428d4`'s body never execute at all? (it is entirely gated on `FUN_00046ea6(5) == 0`)

Closing that took a separate firmware trace **after the drive**, when it could no longer be measured. It
resolved favourably (bit 5 has exactly one caller image-wide, so the detector did run) — but that was
luck, not design. Had it gone the other way, the drive would have been wasted.

## Why

Every gated mechanism is a chain: **`enable → input → threshold → state → effect`.** A probe on the
*state* collapses everything upstream of it into one undifferentiated null. **The number of drives you
need scales with how many upstream stages you left unmeasured.**

## How to apply

When instrumenting a gated mechanism, budget cave bits for **the enable flag and the raw input**, not just
the latched output. Ask: *"if every bit reads zero, how many different stories explain that?"* If the
answer is more than one, the probe is not finished.

For this detector specifically, a future probe should carry **`gp-0x6c2c`** (a single gp-relative i16 —
trivial cave addition) and the **bit-5 inhibit state**, alongside `gp-0x671a`. With those, the V64 drive
would have answered the sizing question directly instead of leaving a bound.

⚠ Note the tension with the 68-byte cave extent: V64 used **68/68 bytes, zero budget left**. Adding the
input and the enable means dropping a state bit or finding more room — which is exactly the trade to make,
because the state bits are the ones that go ambiguous.

Related: [[accord-state671a-is-an-oscillation-detector]], [[accord-gp6c2c-is-the-detector-input]].
