# HANDOFF — 2026-08-18 — V101 EME audit and commit

**Chain:** ← `HANDOFF-2026-08-14-v100-flew-six-levers-closed.md`

---

## Session summary

A single-question session: **"Did V101 account for all the 4× torque mod fixes up to V37?"**

**Answer: YES.** The V101 build script (`build_v101_tva.py`) was read and every EME-prevention
address cross-referenced against the built image on disk. All fixes from V25 through V37 are
carried in V101's `VS_STOCK` ledger and verified at build time with explicit assertions.

### EME fixes confirmed in V101

| Address(es) | Origin | Fix | V101 |
|---|---|---|---|
| `0xC64B4`–`0xC64B9` | V36/V37 | STEER_STATUS debounce disable + DTC-0x49 (`0xC64B8`→`0xFF`) | ✅ |
| `0xC61C0`–`0xC61C6` | V36 | debounce cal values maxed | ✅ |
| `0xC6598`–`0xC65B4` | V29→V38 | soft-EME boost floor FLOAT `1.0f→5.0f` | ✅ |
| `0xC65C6`–`0xC65CF` | V31→V38 | soft-EME boost floor FLOAT `1.5f→5.0f` | ✅ |
| `0xC674E`–`0xC676E` | V25→V38 | soft-EME boost floor INT `1024→5120` | ✅ |
| `0xC64DE`–`0xC64DF` | pre-V38 | re-engage ramp `17→27` | ✅ |
| `0xE4180`–`0xE5260` | V38 | LKAS clamp taper both banks | ✅ |

**Hard-fault interlock** `0xC407E` = 511 (Honda's own value). **Verified from the built image
on disk** (not from the build script's claims).

**The 8× authority check:** soft-EME floor INT 5120 > 4096 (the new forward-path clamp) — asserted
at build time.

### Collateral updates

- `STATE.md` — updated header to reflect V101 exists as built-but-unflashed.
- `BUILD-LINEAGE.md` — V101 row added.
- V101 build script committed to kit repo.
- V101 artifacts (`.rwd` + `_plain_image.bin`) committed to `accord-firmwares`.

### What is on the car

**V100** — flown as route `0x85`, 2026-08-13. Zero calibration bytes; the control law is V99's.

### Next step

Flash V101 at the operator's discretion. It carries the 8× LKAS gain, Lever B removed, and all
EME protections verified.
