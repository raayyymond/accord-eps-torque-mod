---
name: accord-v70-built-sign-probe
description: "★★★ V70 BUILT (unflashed) 2026-08-04 — a 4-bit SIGN probe that solves build identity from the value set alone and measures BOTH open unknowns. 🛑 TWO .rwd files carry a V70 prefix with OPPOSITE control paths and byte-identical caves; the authoritative one is UNRESOLVED."
metadata:
  type: project
---

# ★★★ V70 BUILT, UNFLASHED — the repaired probe

## 🛑🛑 FIRST: "V70" IS AMBIGUOUS ON DISK. DO NOT FLASH UNTIL THE OPERATOR NAMES THE FILE.
Two `.rwd` files carry a `V70` prefix, built 19 minutes apart, with **OPPOSITE control paths** and
**BYTE-IDENTICAL caves** — so the probe cannot tell them apart on-car and **the filename is the only
discriminator before the drive.** This is the V68 three-file trap repeating.

| | **V70-A** `…LKASGATED-V68CONTROLPATH…` | **V70-B** `…SPEEDSHAPED-gateREVERTED…x2…` |
|---|---|---|
| RWD / image | `d716b1a5…` / `8bfcb1fa…` | `0bdfb0da…` / `3760d9c0…` |
| built | 07:45 | **08:04 (newer)** |
| gate `0x3AA96` | **`fb`** (gated on `gp-0x6806`) | **`c5`** (reverted to dead `gp-0x683c`) |
| arm `0xC6446` | **5244** | **512** (stock, unreachable with the gate off) |
| surface `0xD2A7E/80`, `0xD2ABA/BC` | **3072 / 2561** (stock) | **6144 / 5122** (**×2**) |
| vs V68 | **66 B** — cave + MAIN CRC, zero outside | **83 B** — cave + gate + arm + surface + 3 CRCs |
| cal CRCs | ⭐ **both return to V68's exact checksums** | blk#48 = V69's, blk#41 new |
| one line | **V68 + a new cave** | **V69's structure at half the dose** |

⚠ **The kit's tooling reproduces V70-B ONLY** — `_v70_plain_image.bin`, `build_v70_tva.py`
(`SCALE = 2`, TAG `…SPEEDSHAPED-gateREVERTED…`) and `verify_v70_image.py` (which **asserts**
`0x3AA96 == 0xC5` *and* `0xC6446 == 512`, recording the dose as *"halved on the operator override"*).
**V70-A is not reproducible from the current builder.**
⚠ Every figure above was **byte-read from both images**, not relayed.

🛑 **THE EDIT-ORDER INVARIANT IS DIRECTIONAL AND BOTH BUILDS SATISFY IT** — which is exactly why the
filename cannot be skipped. `gate == 0xFB` ⇒ `0xC6446` **must** be 5244 (shipping `fb` with 512 pins the
engaged lane **~5× BELOW stock everywhere — worse than V61**); `gate == 0xC5` ⇒ the arm is unreachable
and 512 is correct. **A-with-B's arm is the brick-adjacent combination**, asserted both directions in
builder, verifier and readback.

## ★★ THE PROBE — settled, identical on both artefacts. 68 of 68 cave bytes, ZERO spare
| bit | cell | test | B |
|---|---|---|---|
| **6** | `gp-0x6ada` | ≥ **+512** (`sar 0x9`) — r24 lane out, post-clip | 14 |
| **5** | `gp-0x67fa` | **== 10** — ★★ **THE STATE GATE** | 12 |
| **4** | `gp-0x6adc` | ≥ 0 — **r26 mirror SIGN** | 12 |
| **3** | `gp-0x6ada` | ≥ 0 — **r24 mirror SIGN**, reusing the already-shifted `r6` (`sar` preserves sign) | 6 |

⭐ **Re-decoded from the image independently of the builder:** loads @`0xC4B38`/`0xC4B4C`/`0xC4B58` carry
opcodes **`0x39` (`ld.h`) / `0x3C` (`ld.bu`) / `0x39` (`ld.h`)**, `ld.bu` displacement parity handled
(`hw2 = 0x9807` encodes `disp = 0x9806`), and **exactly ONE store in the cave** — `st.b` @`0xC4B6E` to
the CAN payload byte `gp-0x1514`. **No `st.h` (`0x3B`) anywhere.**
🛑 **The one-bit trap is live on THREE rungs now**, including **`ld.bu` `0x3C` vs `st.b` `0x3A` on
`gp-0x67fa`, which has 128 readers** — a slipped opcode writes the ECU state variable.
★ **V70 is structurally SAFER than V69**: V69's third rung read `gp-0x6ad4`, which the aggregator
**consumes** @`0x3ACA8`, so a slip would have corrupted a live lane; **V70's two `ld.h` rungs are both on
ZERO-READER mirrors** ([[accord-aggregator-lane-mirrors-6ada-6adc]]), where a slip could only produce a
wrong reading.

## ★ BUILD IDENTITY FROM THE VALUE SET ALONE — a first for this kit
`bit3 = sign(gp-0x6ada)` is **guaranteed non-constant** ⇒ the hard invariant **bit6 ⇒ bit3**, so
`bit6 = 1, bit3 = 0` is an **impossible frame** and only **12 of 16** payloads are reachable. That
excludes **absolutely: V53, V54, V65, V66, V67, V68, V69** — every build from V65 on, **including the one
on the car.**
⚠ **Residual, kept on the record: V55/V57/V58/V64** are independent-bit probes spanning all 16 payloads
⇒ **filename-only**, six-plus builds back. **Strictly smaller than V69's residual** (its immediate
predecessors), but not zero.

## 🛑 bit4 is the SIGN, not a matched `+512` threshold — a deliberate deviation, and why
The cave was **exactly 2 bytes short**, and a `≥ +512` null on r26 was the **predicted** outcome given
`0xC6564` = 40 zero bytes — i.e. straight back into the uninterpretable-zero class that wasted all three
of V69's rungs ([[feedback-size-probe-rungs-against-lane-reachable-output]]).
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

✅ Gates (for the artefact the tooling targets): 50/50 CRC PASS, 71 anchors PASS,
`diff_build_vs_stock.py v70` **0 unattributed**, RWD round-trips with every gate re-run, reproducible
bit-for-bit. Decoder `rlog-tools/decode_v70_probe.py`.

See [[accord-v69-flew-dose-response-non-monotone]], [[accord-gp67fa-state-gate-on-assist-chain]],
[[accord-r26-is-structurally-inert]].
