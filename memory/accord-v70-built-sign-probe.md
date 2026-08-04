---
name: accord-v70-built-sign-probe
description: "★★★ V70's 4-bit SIGN probe — solves build-CLASS identity from the value set alone, and measures both open unknowns (gp-0x67fa's state, r26's liveness). Probe unchanged across V70 re-cuts. 🛑 A superseded first V70 .rwd with the OPPOSITE control path is renamed SUPERSEDED-DO-NOT-FLASH (done, accord-firmwares 9d44efc)."
metadata:
  type: project
---

# ★★★ V70's SIGN PROBE — the durable part of V70

🛑 **NO SHAs OR BUILD STATUS HERE ON PURPOSE.** V70 has been re-cut and its hashes, filename and control
path change with each cut — those live in `docs/STATE.md`'s **"V70 — BEING RE-CUT"** block. **The probe
does not change**, so it is recorded here.

## THE SUPERSEDED FIRST V70 — built, OVERRIDDEN by the operator, renamed
A first V70 **restored V67/V68's control path** (gate `0x3AA96` = `fb`, arm `0xC6446` = 5244, surface
back to stock). **The operator overrode it** — *"V70 just reverts back to V68, which has the high-speed
grind #2 issue"* — and he was right; that decision is **why the current V70 exists**, and the reasoning
is [[feedback_operator_lived_experience_overrides_analyst_recs]]. **It was never a live alternative.**
✅ **Renamed `SUPERSEDED-DO-NOT-FLASH-…`** (`accord-firmwares` `9d44efc`), filesystem-verified: exactly
ONE flashable `V70` file remains. ⚠ **The rename was load-bearing** — its cave is **byte-identical** to
the current one, so **the probe could not have separated them on-car** and the filename was the only
discriminator before a drive.
🛑 **What is NOT fixed: its image is gone and it is unverifiable by the kit's own gates.** See
[[accord-recut-overwrites-the-previous-plain-image]].

## ★★ THE PROBE — 68 of the proven 68 cave bytes, ZERO spare
Base `0xC4B34`, hook `0x55C0E`, extent unchanged.

| bit | cell | test | B |
|---|---|---|---|
| **6** | `gp-0x6ada` | ≥ **+512** (`sar 0x9`) — r24 lane out, post-clip | 14 |
| **5** | `gp-0x67fa` | **== 10** — ★★ **THE STATE GATE** | 12 |
| **4** | `gp-0x6adc` | ≥ 0 — **r26 mirror SIGN** | 12 |
| **3** | `gp-0x6ada` | ≥ 0 — **r24 mirror SIGN**, reusing the already-shifted `r6` (`sar` preserves sign) | 6 |

⭐ **Re-decoded from the image independently of the builder:** loads @`0xC4B38`/`0xC4B4C`/`0xC4B58` carry
opcodes **`0x39` (`ld.h`) / `0x3C` (`ld.bu`) / `0x39` (`ld.h`)** on `gp-0x6ADA`/`gp-0x67FA`/`gp-0x6ADC`,
`ld.bu` displacement parity handled (`hw2 = 0x9807` encodes `disp = 0x9806`), and **exactly ONE store in
the cave** — `st.b` @`0xC4B6E` to the CAN payload byte `gp-0x1514`. **No `st.h` (`0x3B`) anywhere.**
🛑 **The one-bit trap is live on THREE rungs**, including **`ld.bu` `0x3C` vs `st.b` `0x3A` on
`gp-0x67fa`, which has 128 readers** — a slipped opcode there writes the ECU state variable.
★ **Structurally SAFER than V69**: V69's third rung read `gp-0x6ad4`, which the aggregator **consumes**
@`0x3ACA8`, so a slip would have corrupted a live lane; **V70's two `ld.h` rungs are both on
ZERO-READER mirrors** ([[accord-aggregator-lane-mirrors-6ada-6adc]]), where a slip could only produce a
wrong reading.

## ★ BUILD-CLASS IDENTITY FROM THE VALUE SET ALONE — a first for this kit
`bit3 = sign(gp-0x6ada)` is **guaranteed non-constant** ⇒ the hard invariant **bit6 ⇒ bit3**, so
`bit6 = 1, bit3 = 0` is an **impossible frame** and only **12 of 16** payloads are reachable. That
excludes **absolutely: V53, V54, V65, V66, V67, V68, V69** — every build from V65 on, **including the one
on the car.**
⚠ **Residual: V55/V57/V58/V64** are independent-bit probes spanning all 16 payloads ⇒ **filename-only**,
six-plus builds back. **Strictly smaller than V69's residual** (its immediate predecessors), not zero.
🛑 **And it cannot separate two V70 cuts from each other** — their caves are identical.
**Build-CLASS identity is not FILE identity.**

## 🛑 bit4 is the SIGN, not a matched `+512` threshold — a deliberate deviation, and why
The cave was **exactly 2 bytes short**, and a `≥ +512` null on r26 was the **predicted** outcome given
`0xC6564` = 40 zero bytes — straight back into the uninterpretable-zero class that wasted all three of
V69's rungs ([[feedback-size-probe-rungs-against-lane-reachable-output]]).
**COST, STATED: V70 measures r26 LIVENESS, not the quantitative `a`.**

| observation | verdict |
|---|---|
| **bit4 ≈ 1.000 while bit3 toggles** | **r26 inert** — LEG 2 holds, r24 carries the lane |
| **bit4 tracks bit3** | **r26 live** — and V67/V68's gate has been cutting damping **6×** |

★ **UNPLANNED BENEFIT:** bit3 is **amplitude-independent**, so it carries the ~7.4 Hz line **even when
the lane never reaches +512** ⇒ **bit6 measures the ratchet's SIZE, bit3 its PRESENCE.** *If bit3 detects
and bit6 does not, the ratchet is real and small* — which **no prior probe could have said.**

## 📋 PRE-REGISTERED: bit5 reads LOW
V67's `gp-0x6806` tracked `latActive` at **99.983%**, which a flag going stale in state 10 could not do.
⇒ **bit5 ≈ 0 ⇒ the five-build detector null is GENUINE and those builds are vindicated; bit5 materially
non-zero ⇒ the nulls were on the gate** and the detector programme needs replanning.
**Non-vacuous in both directions** — the failure every V69 rung shared.

See [[accord-v69-flew-dose-response-non-monotone]], [[accord-gp67fa-state-gate-on-assist-chain]],
[[accord-r26-is-structurally-inert]], [[feedback_operator_lived_experience_overrides_analyst_recs]].
