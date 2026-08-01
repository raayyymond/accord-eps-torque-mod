---
name: accord-gp683c-dead-gate-is-a-free-lkas-arm
description: ★★ gp-0x683c has ONE access and ZERO writers image-wide, and it gates a private calibration arm on BOTH rate lanes. Repointing that single ld.bu is a ONE-BYTE edit that makes the rate-lane gain conditional on any cell we choose -- the kit's only known conditional-gain surface with no code cave.
metadata:
  type: reference
---

# ★★ The dead `gp-0x683c` gate is a free conditional-gain arm for the rate lanes

Orchestrator-verified 2026-08-01, first-hand: Ghidra assembly context + a raw byte scan with
per-opcode displacement rules (`analysis-2020accord/scan_gp_accesses.py`, self-check pinned on
`gp-0x6b94`). This closes the *"single-method, wants a raw byte scan"* residual `build_v62_tva.py`
recorded against the zero-writer claim.

## The facts

| | |
|---|---|
| `gp-0x683c` accesses image-wide | **exactly ONE**: `ld.bu -0x683c[gp],r15` @`0x3AA94`, bytes `84 7f c5 97` |
| writers | **ZERO** (Format-VII scan at every byte offset, plus the 48-bit extended-displacement form: 0 hits) |
| its only consumer | `cmp r0,r15` @`0x3AAA6` → `setfne lp` @`0x3AAA8`. **r15 is dead after that** — reused by `mov r13,r15` @`0x3AAD4` |
| what `lp` gates | **both** rate lanes: r24 `ld.hu 0x7446[tp],r10` @`0x3AC08` (cal `0xC6446` = 512) and r26 `ld.hu 0x7444[tp],r8` @`0x3AB5E` (cal `0xC6444` = 512) |
| readers of `0xC6446` / `0xC6444` | **exactly one each**, image-wide (raw tp-relative byte scan) |

r24's gain priority chain, read off `0x3ABFA`–`0x3AC16`:
```
gp-0x671d != 0   -> 0xC6442 = 1024      (highest priority; LIVE but measured 0 on route 35)
lp (gp-0x683c)   -> 0xC6446 = 512       (DEAD -- no writer exists)
gp-0x671a >= CEIL-> 0xC6440 = 2048      (the oscillation arm; V64 proved it never arms)
else             -> the mode-indexed LERP
```

## Why it matters

**Repointing that one `ld.bu` makes the rate-lane gain conditional on any gp byte cell we choose**,
turning `0xC6446` into a live, single-halfword, condition-gated gain override. This is the only
conditional-gain surface in this chain that needs **no code cave** — and caves are the kit's only
bricking class (V24, V27, V48B).

**The edit is ONE BYTE** when the target displacement is even. For `gp-0x6806` (`0x97FA`):
```
0x3AA94  84 7f c5 97   ld.bu -0x683c[gp],r15      current
0x3AA94  84 7f fb 97   ld.bu -0x6806[gp],r15      repointed  -- only 0x3AA96 changes
0x02A1B6 84 67 fb 97   ld.bu -0x6806[gp],r12      a REAL instruction, differs only in reg2
```
🛑 V850 `ld.bu` carries the displacement's **bit 0 in hw1 bit 5**, not hw2 — so an *odd* target
displacement also moves the opcode field and is a worse provenance story. Prefer an even one.
GATE 1 is **vacuous** (read-only, no RAM claimed, no new opcode).

## 🛑 The two things that must be checked before using it

1. **CHATTER IS THE KILL CRITERION.** A gain that switches near the mode frequency is a **parametric
   pump** — the exact failure mode V58/V59/V60 spent three builds chasing. Any candidate cell must be
   measured on-car for **toggle rate**, not assumed. A threshold on a lightly-filtered driver-torque
   signal is especially dangerous: the oscillation itself is ±1400 counts on the torsion bar, so it can
   cross such a threshold *at the mode frequency*.
2. **`gp-0x671d` OUTRANKS this arm.** If it ever latches non-zero, r24's gain is pinned to
   `0xC6442` = 1024 — *below* the LERP default — and the repointed arm never applies. V64's probe read
   it 0 across all 14,980 frames of route 35; re-measure over a long drive.

⚠ Repointing also arms r26's `0xC6444` from the same `lp`. Harmless while r26 is structurally inert,
but it is not a private edit — say so in any build note.

See also [[accord-r24-gain-b-four-pointer-arrays]], [[accord-v62-fixed-the-grinding]],
[[accord-v64-null-is-on-the-gate]], [[feedback-probe-the-gate-not-just-the-output]].
