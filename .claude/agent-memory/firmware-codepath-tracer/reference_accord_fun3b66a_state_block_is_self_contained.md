---
name: reference-accord-fun3b66a-state-block-is-self-contained
description: "The 8.131 Hz band-pass damper's filter-state block gp-0x365c..gp-0x3640 (eight 32-bit floats/ints) is touched by NOTHING outside FUN_0003b66a — exhaustive both-encoding census, 22 accesses in gp-0x3660..gp-0x3635, every one attributed. Neighbours are cleanly partitioned: gp-0x3660 is FUN_0003b49a's, gp-0x363c/0x3638 are FUN_0003b8f6's FIR. Clears the lane for a gain change on RAM-ownership grounds."
metadata:
  type: reference
---

# `FUN_0003b66a`'s filter-state block is self-contained (2026-08-09, `GATE1-RAM-OWNERSHIP`)

Question asked: if `0xC63B8` (the band-pass damper gain, stock 41 ≈ 4% of range) is to be raised as a
**cal-only** lever, is its state block private? If anything outside the function writes there, the lane is
not self-contained and raising the gain has unseen consequences.

**Answer: it is private. `[EVIDENCE]`**

## Method
Exhaustive scan of `gp-0x3660..gp-0x3635` (`0xFEDF49A0..0xFEDF49CB`) on stock `code.bin`, **both
encodings** (4-byte disp16 all six opcode families + 6-byte disp23), **footprint-aware**, **even offsets**,
plus method F (`movea disp,gp,rN` array bases) and an image-wide LE32 literal check. **22 accesses found,
every one attributed.** All 16 in-function hits were then cross-checked against Ghidra's own
`disassemble_function` listing of `FUN_0003b66a` and matched exactly.

## The partition — perfectly clean, one function per block

| cells | owner | note |
|---|---|---|
| `gp-0x3660` | **`FUN_0003b49a`** (0x3b49a-0x3b669) | `ld.w` @`0x3b59c`, `st.w` @`0x3b660`; Ghidra-confirmed. Its own private EMA state, one cell BELOW the damper block. Function ends at 0x3b669, `FUN_0003b66a` starts at 0x3b66a — adjacent, non-overlapping |
| `gp-0x365c`, `gp-0x3658` | `FUN_0003b66a` | 3-tap FIR shift register, coeffs `tp+0x5018/501c/5020` = `0xC4018/1C/20` |
| `gp-0x3654`, `gp-0x3650` | `FUN_0003b66a` | **the band-pass damper's two float EMA states** (alpha `tp+0x73b4`) |
| `gp-0x364c`, `gp-0x3648` | `FUN_0003b66a` | the parallel **integer** 2-stage EMA (alpha `tp+0x73ba`, `sar 0xa`) |
| `gp-0x3644`, `gp-0x3640` | `FUN_0003b66a` | previous-input / previous-output floats for the difference term |
| `gp-0x363c`, `gp-0x3638` | `FUN_0003b8f6` | the OTHER 3-tap FIR, coeffs `0xC4048/4C/50` — see [[reference_accord_fun3b8f6_fir_not_biquad_inertia_friction_and_free_taps]] |

**Each of the eight `FUN_0003b66a` cells has exactly ONE reader and ONE writer, both inside the function.**
Read sites `0x3b6c8/0x3b6dc/0x3b780/0x3b7b6/0x3b7c0/0x3b7cc/0x3b7d0/0x3b818`; write sites
`0x3b6d0/0x3b726/0x3b7e4/0x3b810/0x3b81c/0x3b828/0x3b83c/0x3b850`.

## Negative checks
- **LE32 registry literals within ±256 B: NONE** — the block is not a table-registered buffer (this is
  the check that catches the `gp-0x1500` class).
- **`movea`-gp array bases**: 40 sites within ±512 B, but the nearest below the block is `0xFEDF4950`
  (`gp-0x36b0`), **80 B below `gp-0x3660`**, and the SCALAR-BOUND test breaks its shadow — `gp-0x3690`,
  `gp-0x368c`, `gp-0x3688`… are each individually `st.w`-addressed, so no array can reach the block.
- **Out of stack reach** (`sp = 0xFEDEF91C`, grows down; block is ~+20 KB above it).

## 🛑 One false alarm, and how it was killed — worth remembering
An all-offset byte scan reported `st.b …,-0x3641[gp]` at **`0x30a1f`**, i.e. a byte store from
`FUN_000308f2` landing on the **high (exponent/sign) byte of the float at `gp-0x3644`** — the exact V48B
aliasing shape, inside the damper's own state block. **It is an ALIAS, not an instruction.** `0x30a1f` is
an ODD address and V850 instructions are 2-byte aligned; Ghidra's `disassemble_function` on
`FUN_000308f2` shows `mulf.s r8,r14,r8` @`0x30a1c` followed by `ld.w 0xc8[r15],r23` @`0x30a20` — nothing
begins at `0x30a1f`. ⇒ **`gp-0x3641` is not written from outside.**
The general lesson is in [[reference-accord-gate1-movea-gp-array-blindspot-and-scalar-bound]]: resolve a
suspected alias with `disassemble_function` on the containing function, **never** with
`get_assembly_context` (which returned `{}` for every address this session, including real ones).

## Scope of this clearance
This clears the lane on **RAM-ownership** grounds only: raising `0xC63B8` cannot corrupt, or be corrupted
by, any other subsystem's state. It says **nothing** about the two gates that actually decide the lever —
the **sign at the summing junction** and the **±10 clamp headroom** — nor about the rectification finding
that the lane is a boost-gain modulator rather than an additive damper
([[reference_accord_fun3b66a_8hz_bandpass_is_rectified_not_a_damper]],
[[reference_accord_fun3b66a_bandpass_is_boost_gain_modulator]]).
