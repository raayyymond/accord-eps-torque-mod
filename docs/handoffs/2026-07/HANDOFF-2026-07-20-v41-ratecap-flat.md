# HANDOFF - 2026-07-20 - V41: flat motor-rate cap, and two hypotheses killed

**Platform:** 2020 Accord `39990-TVA-A160`, V850E2. **Baseline:** exact on-car V38 plain image.
**Status:** V41 is BUILT and statically VERIFIED, **NOT FLASHED**. No CAN, UDS, or flash operation occurred.
**Supersedes:** the earlier V41 (CRC-fix), and V42/V43 which were deleted at operator direction.

## Operator directive (2026-07-20)

> The delivered LKAS command should be as true as possible to what the comma says it should be, relying
> on the comma's peer-reviewed safety measures. Remove (1) the limit on how fast LKAS command slew
> reaches delivered torque, and (2) the cap that reduces delivered LKAS torque at high motor
> electrical-angle rate.

Plus the correct observation that **motor electrical angle is mechanically coupled to steering angle**,
so (2) is a cap that tightens the faster you turn the wheel.

## What was executable, and what wasn't

**(2) — EXECUTED.** This is V41.

**(1) — NOTHING TO EXECUTE.** There is no live LKAS-specific slew limit.

`FUN_00026c80` contains a complete, correct-looking LKAS-lane rate limiter (cal `0xC6194`=3, bounds
`0xC6192`=2048 / `0xC6198`=3072). **It is architecturally inert.** Verified at instruction level:

```text
0x276c2:  ld.hu 0x73CC[tp], r8    -> cal 0xC63CC
0xC63CC:  bytes 00 00 00 04       -> ld.hu takes the first halfword = 0x0000
```

That zero multiplies the entire term carrying the rate-limited state, so `gp-0x6b4c` reduces to
`gp-0x3d88` alone — an unlimited per-mode passthrough with no persisted state. Blast radius swept:
`gp-0x3d6c`/`gp-0x3d84`/`gp-0x3d88` have 2 sites each, **all inside `FUN_00026c80`**. Changing
`0xC6194` cannot affect anything. **The LKAS lane already reaches the aggregator unfiltered.**

The only slew limiting that touches LKAS is the **merged-command** governor `FUN_0004503c`
(`0xC6206`/`0xC6208`), whose target is `gp-0x6b94` = the aggregator output, **LKAS + base assist**
(verified at `0x453E0`). Freeing it also frees base assist, which openpilot neither commands nor
observes — so the comma-safety rationale does not extend to it — and it is the prime suspect for V40's
ignition fault. **Left stock at 512/205.**

## Two hypotheses killed this session

| Hypothesis | Verdict |
|---|---|
| Stale `0xC5FFC` CRC caused V40's ignition fault | **Dead.** Bootloader hard-codes a bridge past that block (byte-verified `0xB070`/`0xB07A`/`0xB080`); boot path does a blank-check only; no CRC32 in app code; **zero xrefs to `0xC5FFC` image-wide** |
| Rate-limit-induced limit cycle on the LKAS lane explains the vibration | **Dead.** No live rate limiter on that lane — `0xC6194` is multiplied out by a zero gain |

## Why the cap is the ratchet

The LERP **clamps at both ends; it does not extrapolate** (verified at `0x7b658`-`0x7b67a`; both clamp
branches are unconditional jumps to `0x7b71a`, displacements confirmed):

```text
rate     stock cap   V41 flat    stock->MIN(4762)   V41->MIN(4762)
   0          5325       5325                4762             4762   <- IDENTICAL at rest
2500          2406       5325                2406             4762
>=4100         512       5325                 512             4762   <- 9.3x apart
```

At steering rate ≥4100 stock slams the cap to **512** — an **82% instantaneous cut** against V38's
~2806 command, since motion toward zero is unlimited in the governor. Recovery is then limited to
205/cycle ≈14 cycles. Fast cut + slow recovery = a several-Hz limit cycle.

⚠ **Stock V9's max LKAS command was 417 — below the 512 floor, so stock LKAS could NEVER be capped.**
V38's 4× raise is the first build to cross it. That is why the ratchet appeared with V38.

Flattening does not raise the ceiling: flat 5325 sits above the governor nominal 4762, so the adaptive
arm simply stops binding. **At rest stock and flat are identical**, which is also why the cap flatten
cannot explain V40's stationary ignition fault.

## Artifact

```text
../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V41-LKAS-4x-V38base-ratecap-flat5325-0x13000-0x100000.rwd
```

| Artifact | SHA-256 |
|---|---|
| V41 RWD | `77fbd6aa695d63c3bdd69fd4db4be36dc879ae7fc423e0934951933ea38c60e5` |
| `_v41_plain_image.bin` | `194b0903ed79822ec6bc095b67087adaaa54afe4eb4aff0a82c87685f0d271dd` |
| `_v38_plain_image.bin` baseline | `a7391972a9db51d0e7699956755eb1d1e6b1dcc2d7d3aa0f470065fd4b14afa8` |

Builder: `analysis-2020accord/builds/v18_v49/build_v41_tva.py`. **CAL-ONLY — zero code edits, zero caves.**

## Edits — 36 bytes in 4 runs

| Address | V38 | V41 | What |
|---|---|---|---|
| `0xC5030` / `0xC5038` | `-21940,-12059,-5593,-22021` | `0,0,0,0` | Q13 slopes, both copies |
| `0xC521A` / `0xC5232` | `5325,3584,2406,1587,512` | `5325 × 5` | cap Y row, both mirror copies |
| `0xC5FFC` | `0x09C1200B` | recomputed | cap-block CRC (hygiene — nothing reads it) |

**Untouched:** the entire `0xC6000` block (so `0xC6194`=3, `0xC6206`=512, `0xC6208`=205, `0xC6202`=4762
all stock), cap X breakpoints, record counts/terminators, banks B/C, and all application code.

## Verification performed

- Bootloader walk 49/49 **and** full chain 50/50 on baseline, V41 image, and decoded RWD readback.
- V41 vs V38 = exactly 36 bytes in the 4 runs above; block `0xC6000`-`0xC7000` byte-identical.
- App code `[0x13000,0xBF000)` byte-identical to V38. Both cap mirror copies identical to each other.
- RWD round-trips byte-for-byte; x31 checksum valid; part number `39990-TVA,A160` intact.
- Re-verified independently outside the builder.

## Road-test interpretation

- **Ratchet gone:** the cap floor was the mechanism. Confirms the diagnosis.
- **Ratchet remains:** the cap was not it; the 205/cycle recovery in the merged governor is the next
  suspect — but note that raising it is exactly what V40 did, so treat carefully.
- **Vibration unchanged:** expected. Nothing in V41 targets it, and its mechanism is now unknown again.
- **EPS lamp at ignition like V40:** highly diagnostic. With the merged governor stock, the cap flatten
  would be the only remaining candidate and the startup-transient theory would be confirmed.

## Open

- **V40's ignition fault is still not root-caused.** Best-supported: removal of the merged-command slew
  limit (a low-pass filter on the torque command; at rest the target is sensor noise around zero and
  the sign-crossing reset has **no hysteresis and no minimum magnitude** — verified).
- **The vibration mechanism is unknown again.** If a rate limit shapes the LKAS lane it must be upstream
  of the `gp-0x62b0` mode-value array (computed base — a gp-relative sweep will not find it) or in
  whatever sets the `tp+0x5118` mode flags. Untraced.
- Whether the aggregator or its seven upstream lanes deadband near zero — only `FUN_0003aa2c`'s own body
  was checked (no deadband found there); the individual lanes were not.
- `FUN_00016de6(0x1d,…,1,1)` reaches motor-off with **no debounce counter** — one out-of-bounds cycle in
  `FUN_0004595a` or `FUN_00045a20` suffices. Standing fact, not specific to this bug.
