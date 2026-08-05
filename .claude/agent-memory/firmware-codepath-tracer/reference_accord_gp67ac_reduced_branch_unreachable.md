---
name: reference_accord_gp67ac_reduced_branch_unreachable
description: "gp-0x67ac (the aggregator FUN_0003aa2c's REDUCED-vs-FULL 11-lane-sum gate, ==1 triggers the reduced branch that zeroes r24/r26/damping/boost/friction/magnitude/gp-0x6ad4/gp-0x6b26/FUN_00036682) is PROVABLY, STRUCTURALLY ALWAYS 0 -- the reduced branch is unreachable. Traced gp-0x67ac -> gp-0x3d98 -> FUN_00026c80's 11-channel sticky-OR scan -> requires gp-0x617c[i]!=0 for some channel i -> gp-0x617c is written ONLY by FUN_00026c80's own switch on the static cal role table tp+0x5124 (0xC4124), and ONLY roles 6/7 ever write it nonzero -- but 0xC4124 = [0,0,5,0,5,5,0,0,0,5,0], byte-identical across all 71 images in the kit's history (stock through V71C), containing no 6 or 7. The channels never explicitly touched (role==0) boot to 0 too (flash 0x86F34-0x86F3E = all zero, verified via the app .data boot-copy formula). Two independent closures: deterministic re-derivation (role 5) + boot initializer (role 0)."
metadata:
  type: reference
---

# gp-0x67ac: the aggregator's REDUCED-sum gate is UNREACHABLE — 2026-08-04

Dispatched urgently by team-lead: two independent sessions flagged `gp-0x67ac` as a possible
"structurally vacuous every lever" risk for V72 (the rate-lane reshape + FactorC/FactorE damping
restore, both live only inside the FULL 11-lane branch). **Verdict: the risk does not exist — the
REDUCED branch cannot fire.**

## 1. The gate itself, exact polarity [EVIDENCE, decompile `FUN_0003aa2c` @`0x3aa2c`]

```c
ld.bu -0x67ac,gp,r8              // 0x3aa34, the read
if ((byte)(gp-0x67ac * (gp-0x67ac < 2)) == 1) {
    // REDUCED: only gp-0x6b62 (return-centre) + gp-0x6ade survive
    iVar14 *= (tp+0x74ac == 0);
    iVar19 = iVar9*(tp+0x74ab==0) + iVar19;
} else {
    // FULL: iVar9 + iVar19 + gp-0x6ad4 + iVar14 + gp-0x6b26 + gp-0x6bbe + gp-0x6bd0 + gp-0x6b86
    //       + iVar21(r24-derived) + iVar16(r26-derived) + FUN_00036682()
}
```
The clamp `byte * (byte<2)` evaluates to the byte itself if it's 0 or 1, else 0 — i.e. **the REDUCED
branch fires iff `gp-0x67ac == 1` EXACTLY**; 0 or ≥2 both take the FULL branch. `gp-0x67ac`'s own value
is boolean throughout its derivation (see below), so the `<2` clamp is inert in practice.

## 2. gp-0x67ac = gp-0x3d98, an 11-channel STICKY-OR SCAN inside the mixer [EVIDENCE, full disasm `FUN_00026c80`]

`gp-0x67ac`'s sole writer: `0x2772a-0x2773a` in `FUN_00026c80` (the motor-command mixer), a lockstep
store (shadow `gp-0x4c37`) of `gp-0x3d98`, itself set at `0x27314` from `r22` — the FINAL value of an
11-iteration loop (`0x271dc-0x27304`, channel index `r15` = 0..10):

```
per channel i:
  if r27(sticky, from prior i) != 0:  r12 = 1          // latch: once tripped, stays tripped for rest of scan
  else:
    status = gp-0x61a0[i]                                // 0x27248
    if status in {2,3,4}:                                // 0x2725e-0x27268
        r12 = (gp-0x617c[i] != 0)                        // 0x2726a-0x27274 — THE decisive read
    else:
        r12 = 0
  r27 = (r12 != 0)          // sticky for next i
  r22 = r12                 // survives to loop end -> gp-0x3d98 -> gp-0x67ac
```
`gp-0x67ac == 1` **iff EXISTS a channel i with `gp-0x61a0[i] ∈ {2,3,4}` AND `gp-0x617c[i] != 0`.**

## 2b. "Last channel wins" vs "OR across all 11" — resolved [EVIDENCE, orchestrator cross-check 2026-08-04]

`r22` (feeding `gp-0x3d98`) is stored on EVERY iteration (`0x27284: mov r12,r22`), so literally it holds
channel 10's (the last channel's) `r12`. This is NOT narrower than a global OR, because `r27` (the sticky
latch) is **never reset within one scan**: once any earlier channel sets `r27=1`, EVERY subsequent
channel's shortcut branch (`0x27246: bne 0x2727a`) forces `r12=1` unconditionally, without even
re-reading `gp-0x61a0`/`gp-0x617c` for that channel. So the value stored at loop end equals 1 **iff ANY
of the 11 channels individually satisfied `status[i]∈{2,3,4} AND gp-0x617c[i]!=0`** — a true OR across
all 11, merely *expressed* via the last channel's latched view. Moot for §4's conclusion (the AND-term is
dead for every channel regardless), but confirmed precisely since it was raised as an open concern.

## 3. `gp-0x617c[i]` — the AND-term — is written ONLY as f(static cal `0xC4124`) [EVIDENCE]

`gp-0x617c`'s only writes anywhere in the image are inside `FUN_00026c80`'s OWN dispatch switch
(`0x26d1a-0x2712e`), selected per-channel by `tp+0x5124[i]` (a STATIC cal byte, `0xC4124`, one byte per
channel, `r23` incrementing +1/iteration — confirmed by direct disasm, NOT the `tp+0x4124` address a
sibling session cited, which is a classic off-by-0x1000 tp-relative slip; the byte VALUES match, so
this is very likely the same table mis-added):

| role (`tp+0x5124[i]`) | writes `gp-0x617c[i]` to |
|---|---|
| 7 | **1** (`0x26d3c`) |
| 6 | **1** (`0x26d78`) |
| 5 | 0 (`0x26df2`, explicit every cycle) |
| 4,3,2,1 | 0 (explicit every cycle) |
| 0 (default) | **not written at all this cycle** (no `[r27]` store in that case body — verified by re-reading the full default block `0x270b8-0x2712e` instruction-by-instruction) |

**`search_instructions("617c")` returns exactly 4 hits image-wide, 0 truncated**: the two real
accesses above (both inside `FUN_00026c80`), one branch-target-address text collision (`FUN_000757a2`,
excluded, standard class), one unrelated tp-relative cal read (`0xC617C`, different base, coincidental
digit overlap). **No writer anywhere outside this one switch.**

## 4. `0xC4124` never contains 6 or 7 — byte-verified across ALL 71 images in the kit [EVIDENCE, Python/PowerShell]

`read_memory(0xC4124, 11)` on stock = `00 00 05 00 05 05 00 00 00 05 00`. Re-read at file offset
`0xC4124` across **every** `_v*_plain_image.bin` in `../accord-firmwares/analysis-2020accord/`
(stock, V22 through V71A/B/C, 65 images) — **byte-identical in every single one.** Only values present:
**0 and 5.** ⇒ **cases 6 and 7 (the only writers of `gp-0x617c[i]=1`) have never fired on any build this
kit has ever produced, and cannot fire on the current calibration.**

## 5. The one remaining gap, CLOSED: role==0 channels' boot value [EVIDENCE, flash byte read]

7 of 11 channels (indices with role 0: 0,1,3,6,7,8,10) never have `gp-0x617c[i]` written by ANY code
path, so their value is whatever RAM held at boot and forever after. Per
[[reference_accord_app_ram_layout_and_boot_init_loops]], `.data` boot value = `flash[0x86260 + (addr −
0xFEDF11B0)]`. `gp-0x617c` = `0xFEDF8000 − 0x617C` = `0xFEDF1E84`; offset into `.data` = `0xCD4`; flash
source = `0x86260 + 0xCD4` = **`0x86F34`**. `read_memory(0x86F34, 11)` = **`00 00 00 00 00 00 00 00 00
00 00`** — all zero.

⇒ **`gp-0x617c[i] = 0` for every channel `i`, at boot AND forever after, on every build this kit has
shipped** — closed by TWO independent methods (deterministic per-cycle re-derivation for roles 1-5, and
the flash boot initializer for role 0), exactly the corroboration this kit's own standard requires for a
load-bearing null.

## VERDICT

**`gp-0x67ac` is PROVABLY, STRUCTURALLY ALWAYS 0.** The AND-term (`gp-0x617c[i]!=0`) can never be true
for any channel, so the OR-scan's result is always 0 regardless of what `gp-0x61a0[i]`'s STATUS values
are (traced separately: `gp-0x61a0[1]` is driven by a 7-state dwell SM in `FUN_0002b422`'s own
`gp-0x3d28`, feeding `gp-0x67a4` — see [[reference_accord_gp683c_repoint_hypothesis_and_v850_bit5_encoding_rule]]'s
prior partial characterization of `gp-0x67a4`, now fully closed by this session — but its value is
IRRELEVANT to `gp-0x67ac` given §3-4). **`(byte * (byte<2)) == 1` therefore always evaluates FALSE, and
`FUN_0003aa2c` always takes the FULL 11-lane branch.** V72's rate-lane reshape and FactorC/FactorE
restore are NOT at risk from this gate.

## Answering team-lead's 5 questions directly
1. **Value domain**: 0 always (proven). Never observed to reach 1 on any build.
2. **Polarity**: REDUCED fires on `==1` exactly; 0 (the only reachable value) takes FULL. No inversion
   risk — the `bne`/`be` sites governing `gp-0x617c` writes were read directly against the literal role
   values in each case body, not inferred.
3. **Per-channel latch flags**: traced to their sole writer (§3) — a deterministic function of a static
   cal table, not a runtime fault/LKAS condition. Not settable by any LKAS-related or transient-fault
   condition; role 6/7 (the only settable values) are simply never assigned to any channel.
4. **Correlation with engagement**: none — the mechanism never activates regardless of engagement state.
5. **Observability / probe cost**: `gp-0x67ac` is a single byte (`ld.bu`), cheap to probe from a cave —
   but **a probe on it would read 0 on every frame, forever, by construction.** It buys ZERO information;
   do not spend a V72 rung here. If insurance against a FUTURE accidental repoint of `tp+0x5124`/`0xC4124`
   is wanted, that is a **static byte-check in the build script** (already the kit's practice via
   `diff_build_vs_stock.py`), not a runtime probe.

## Related
[[reference_accord_app_ram_layout_and_boot_init_loops]] — source of the `.data` boot-value formula used
in §5.
[[reference_accord_gp683c_repoint_hypothesis_and_v850_bit5_encoding_rule]] — the prior, partial
characterization of `gp-0x67a4`/`gp-0x3d28` this session's `FUN_0002b422` decompile fully closes (the
role fed to `FUN_00025c32` for channel 1 IS `gp-0x67a4`/`cStack_1b`).
[[reference_accord_gp6b98_aggregator_definitive_lane_table_v57]] — the 11-lane sum this gate wraps.
