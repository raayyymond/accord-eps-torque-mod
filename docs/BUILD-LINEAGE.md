# Build lineage and lever index — CHECK THIS BEFORE PROPOSING ANY CALIBRATION EDIT

**Why this file exists:** on 2026-07-27 two independent agents, in the same session, proposed
`0xC6450` 1024→32 as a "new, never-flashed" vibration lever. **It is V46 verbatim — flashed, null.** A
third nearly repeated it with `0xC644A` (V43, flashed, null). Both had read `CLAUDE.md`; the flashed
result was buried in prose.

> **RULE: before naming any calibration address as a lever, grep `analysis-2020accord/build_v*_tva.py`
> for it and check the table below. State its on-car result in your recommendation.**

---

## Part 1 — Lever index, by address

**FALSIFIED** = flashed and demonstrably changed nothing for its target symptom. It is not "untested".

| address | what it is | build | flashed? | on-car result |
|---|---|---|---|---|
| `0xC6450` | `FUN_0003a382` Stage-A carrier pole (1024 = exact unity) | **V46** | ✅ | 🛑 **FALSIFIED** — vibration unchanged |
| `0xC644A` | `FUN_0003a382` Stage-C dirty-derivative pole | **V43** | ✅ | 🛑 **FALSIFIED** — vibration unchanged |
| `0xC643F` / `0xC6445` + `0xC6A72/86/9A/AE` | `r26` adaptive torque-rate gain surface | **V42** ch.2 | ✅ | 🛑 **FALSIFIED** |
| `0xC6440/42/46`, `0xC61F6` | `r24` direct Sensor-B rate lane | **V39** | ✅ | 🛑 **FALSIFIED** |
| `0xD27C6` / `0xD27DA` | damper Factor C hands-off deadzone Y[0] | **V44** | ✅ | 🛑 **FALSIFIED** (Factor E re-zeroes the product) |
| `0xD2802/04/06`, `0xD2816/18/1A` | damper Factor E (motor-rate) deadzone | **V47** | ✅ | 🛑 marginally quieter at 5 mph, **no effect in motion** |
| `0xC4120` + `FUN_0003a382` `uVar27`→256 | type-8 carrier mute | **V48A** | ✅ | 🛑 **FALSIFIED** |
| `gp-0x4f60` broad EMA (19 carriers → `gp-0x1300`) | V52C code cave | **V52C** | ✅ | 🛑 vibration unchanged; **did change manual feel** |
| `0xC6206` (hands-off slew) | governor slew | **V45** | ✅ | 🛑 **FALSIFIED** |
| `0xC6206`/`0xC6208` ← `0xFFFF` | governor slew, both | **V40** | ✅ | ☠ **EPS lamp + no power steering at ignition.** Magnitude, not direction: `0xFFFF` made the guard never fire → snap-to-target → DTC 0x1d → motor off |
| `0xC5030`, `0xC521A`, `0xC5232` | motor-rate cap table | V40/**V41** | ✅ | 🛑 **FALSIFIED** (V41 = clean subtractive test) |
| `0x454FE` `0x65BA`→`0x65B5` | state-4 governor ratchet `bne`→`br` | **V42** ch.1 | ✅ | ✅ **CONFIRMED ROOT CAUSE** — fixed the hard-turn ratchet. Carry forward. ⚠ **NOT present in V38/FOURFRAME** |
| `0xC646C` 891→3564 | the 4× gain — **shared sensor-scale, 6 readers, 2 on feedback paths** | V22→ | ✅ | the change under investigation |
| `0xC61B2`/`0xC61B4` 512→2048 | forward-path clamps, raised ×4 with the gain | V22→ | ✅ | correct and intentional |
| `0xC64B8` 112→0xFF | DTC-0x49 fail-counter gate | **V37** | ✅ | ✅ **gentle EME RESOLVED**, no dash-light regression |
| `0xC64B4-B7`, `0xC61C0-C5`, `0xC64E2` | `STEER_STATUS` debounce SM cals | **V36** | ✅ | ⚠ fixed gentle EME but **unmasked DTC 0x49** → superseded by V37 |
| `0xC6312` 320→65535 | gentle-EME decider torque gate | **V33** | ❌ | wrong gate (fires ~10 Hz benign) |
| `0xC65C4/C8/CC` + `0xC6768/6A/6C` | soft-EME boost floor (matched int/float) | **V31** | ✅ | ✅ soft EME resolved. **Do not desync the mirror pair** |
| `0xC6202` | governor nominal | — | ❌ | **investigated and REJECTED** — buys nothing (4762 > max command), and `gp-0x4f64` is shadowed → fault `0x17`, hard-fault-eligible |
| `0xC6194` | "LKAS-only rate limiter" | — | — | **DEAD calibration** — its gain cal `0xC63CC` = 0 |

### Untested levers currently on the table
| address | what | status |
|---|---|---|
| `0xC6AF0` Y-array | `FUN_0003a382` authority→output-bound LERP | **BLOCKED** — edit *direction* unresolved; needs `gp-0x6966` measured on-car |
| `0xC62EA` 320→**0** | low-speed steer lockout, 5 km/h → 0 | **BUILT as V53** (2026-07-27), cal-only, **unflashed** |
| `0x2a1ee` retarget → `0xC6CD0` | decouple 4× forward from the feedback readers | designed + verified, **unbuilt** |

---

## Part 2 — Code caves are the only bricking class

**Three of this kit's code caves bricked the ECU: V24, V27, V48B.** Every success since V29 has been
cal-only or a single in-place branch/displacement edit.

- **V27** — bricked from **ASYMMETRY**, not magnitude (float twin doubled wholesale vs int corridor-only).
- **V48B** — bricked from (a) RAM collision: biquad state `gp-0x14FA` aliased a live monitor status byte,
  and (b) an unmodelled lightly-damped resonator inserted into the always-on base-assist loop.
- **V40** — not a cave, but the same lesson: the defect was the **magnitude** of a cal write, not its
  direction.

⇒ **TWO MANDATORY GATES for any cave / filter / dynamics change** (apply without being asked):
- **GATE 1 — RAM OWNERSHIP.** Every byte of the full multi-byte footprint proven free *including writers*
  and register-indirect / 6-byte-extended-displacement accesses. `gp-0x1401..0x1502` is poison (it is a
  subset of the `0xb7260` I/O-mailbox array). **Static clearance is not sufficient — `gp-0x1500` passed
  both static methods and still failed on-car.** A live probe is the only reliable RAM-ownership test.
- **GATE 2 — CLOSED-LOOP STABILITY.** Magnitude *and* phase of **every loop the touched signal is in**,
  especially the always-on base-assist loop. Never a single-frequency magnitude.

**A 2-byte in-place displacement or branch-condition edit is a different, far lower risk class than a
trampoline + cave.** Do not conflate them.

---

## Part 3 — Machine-generated per-build delta (vs stock `code.bin`, app region only)

Regenerate with a byte diff restricted to `[0x13000, 0x100000)`.
⚠ **A whole-file diff is meaningless** — `build_*.full_image()` writes `0xFF` filler below `0x13000` and a
naive diff reports 51,137 bogus bytes.

`0x13109` and `0x14120` appear in every build: they are the version-string bytes (`-`→`,`, giving
`39990-TVA,A160`). **Every modified build shares that string, so an rlog cannot identify which build is
flashed.**

| build | bytes | code edits (beyond version string) |
|---|---|---|
| v29–v33, v36, v37 | 27–42 | none — cal-only |
| v38 | 126 | none — cal-only (first to touch `0xE4000`/`0xE5000` bootloader blocks) |
| v39 | 174 | `0x3AC78` + cave `0xC4B34-C4B5F` |
| v40 / v41 | 162 | none — cal-only (`0xC5030`, `0xC521A`, `0xC5232`, `0xC6206/08`) |
| v42 | 153 | **`0x454FE`** (the ratchet fix) |
| v43–v48a | 129–145 | `0x454FE` only |
| v48b | 282 | `0x2C482`, `0x354D4`, `0x35AA6`, `0x3A6CC`, … + cave — ☠ **BRICKED** |
| v49 | 130 | `0x3A836`, `0x454FE` |
| v50 / v52 / v52c | 226–254 | multi-site repoints + cave `0xC4B34` |
| v49p / v50probe / v51probe | 183–216 | `0x55C0E` hook + cave (read-only probes) |
| vcantxtest | 340 | `0x55C0E` hook + cave — ⚠ carries the **STRB=0x80 defect** |
| vfourframe | 853 | `0x55C0E` hook + cave — ⚠ **STRB=0x80 defect, never transmitted** |
| **vfourframe2** | 853 | same, **STRB fixed to 0x01**, authority + reference-model signals |
| **v53** | 855 | FOURFRAME2 byte-for-byte **+ `0xC62EA` 320→0** (+ CAL CRC). Exactly 6 bytes off FOURFRAME2 |

---

## Part 4 — Flash status at a glance

**Flashed and currently the on-car baseline lineage:** V38 (fault-free) → V42 (ratchet fixed) → V43, V44,
V45, V46, V47, V48A (all null) → V48B (☠ bricked, recovered by reflash) → V52C (null for vibration,
changed manual feel) → **FOURFRAME** (telemetry, silent due to the STRB defect).

**Built and UNFLASHED:** V49, V50, V51P, V52, VCANTX-TEST, FOURFRAME2, **V53** (= FOURFRAME2 + the
minimum-steer-speed edit; supersedes FOURFRAME2 as the thing to flash — one drive answers both open
questions).

🛑 **Flash only on explicit operator instruction naming the file and the bus.**
