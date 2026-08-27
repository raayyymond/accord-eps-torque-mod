# ★★ `gp-0x6ba6 == |gp-0x6b9a|` is the boost AMPLITUDE index — and `builds/v50_v79/build_v58_tva.py` was wrong

**Type:** reference · **Byte-verified 2026-07-30** against `_v58_plain_image.bin` (SHA `4311174…`)

## What the build script claimed, and why it's wrong
`builds/v50_v79/build_v58_tva.py` said `gp-0x6b9a` *"is the FIR chain's output and indexes boost's NON-flat table
0xD28DC."* **Wrong on both counts.** Corrected in place; the docstring keeps the original with the
correction attached (this kit does not rewrite history).

**(1) `0xD28DC` hangs off pointer table `0xca4f4`, NOT `0xca23c`.** All 34 modes, LE byte read:
```
0xca4f4 -> …0xD08DC 0xD18DC 0xD28DC…      0xD28DC PRESENT (mode 10)
0xca23c -> …0xD0888 0xD1888 0xD2888…      0xD28DC ABSENT
0xca154 / 0xc7970 / 0xca06c / 0xca40c / 0xca324:  ABSENT
```

**(2) `gp-0x6b9a` indexes nothing.** Its only live consumer in `FUN_00034a72` is a **five-input
plausibility gate**: `|gp-0x6b9a| ≤ 25600` (`addi 0x6400 / ori 0xc801 / cmp / bnc` @`0x34c9c-cb4`,
symmetric) ANDed with `gp-0x6ba6`, `gp-0x4f68`, `gp-0x4f60`, `gp-0x6c2e` into r21, which zeroes r24
@`0x34fc8`. r15 is overwritten @`0x34ca4`, so no value path survives. **Its SIGN has no output effect.**
Two of its three reads there (`0x34b5e`, `0x34b68`) are **dead** — `tp+0x7499 = 1` (`0xC6499`,
byte-verified) takes the branch @`0x34b3c`.

## The actual chain
```
0x3b874  cmp r0,r28 / mov r28,r13 / bge 0x3b886 / subr r0,r13     r13 = |r28|
0x3b87e  ori 0xffff,r0,r13   /  movea 0x7fff,r0,r28               FAULT sentinels
0x3b892  st.h r13,-0x6ba6[gp]      SOLE writer image-wide
0x3b8b0  st.h r28,-0x6b9a[gp]      SOLE writer image-wide
```
⇒ **`gp-0x6ba6 == |gp-0x6b9a|`**, a signed/magnitude pair from one r28 in `FUN_0003b66a`.
`gp-0x6ba6` indexes **both** amplitude LERPs, relayed via scratch `gp-0x6bba` (the 4-state FSM clobbers r9):
```
LERP1 0xD28DC  X=(0,512,1490,2529,3645,5120)  Y=(16384,14657,11672,9365,8244,8187)
LERP4 0xD2888  X=(0,307,1024,1741,3072,6144)  Y=(16384,14392,10265,8997,8176,8176)
```

## The mechanism (INFERENCE, depth unmeasured)
V58 measured the **signed** sibling crossing zero at 20.93 Hz **only when LKAS applies** (13.69 vs 0.61
toggles/s at matched creep; per-run coherence 0.649/0.970/0.769/0.881). The index is therefore that
signal **full-wave rectified** — a minimum at every zero crossing — sweeping both curves at **~2× the
mode frequency on the BASE ASSIST path**.

Delivered swing by depth: `<512 ⇒ ≤1.12×` · `1024 ⇒ 1.27×` · `2048 ⇒ 1.58×` · `2529 ⇒ 1.75×` · `≥5120 ⇒ 2.00×`.
⚠ **"Below 512" is WEAK, not inert** — the LERP interpolates from X = 0, so it is pinned at 16384 only
at exactly zero. An earlier framing this session called it inert; that was wrong.

🛑 **V59 measures the depth. Do not move `0xD28DC` / `0xD2888` / `tp+0x73ba` until it has flown** — all
three sit on the **base assist** path, so they change manual feel, not just the LKAS lane. GATE 2 open.

## Two collateral corrections
- **`FUN_0003b66a` branch A is NOT a biquad.** `tp+0x5018/501c/5020` = `0xC4018/1C/20` = **(1.0,0.0,0.0)**
  and the code is `y = b0·x[n] + b1·x[n−1] + b2·x[n−2]` with two *input* delay states — a delay line, not
  feedback. **Stateful ≠ recursive.** "No biquad anywhere" survives; no new notch candidate.
  Also `tp+0x74be = 0` makes `0x3b736–0x3b758` dead code.
- ⚠ **`search_instructions` undercounted again**: 8 sites vs **9** from a Python byte scan (it missed
  V58's own cave read at `0xC4B4E`). Never rest a writer/reader set on it alone.

See [[accord-v58-drive-grinding-engagement-gated-creep-only]], [[accord-sign-probe-needs-zero-crossings]],
[[accord-angle-rate-lane-gp6bbe-top-candidate]], [[accord-v850-scan-traps-formatv-and-storezero]].
