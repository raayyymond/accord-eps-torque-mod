---
name: reference_accord_app_ram_layout_and_boot_init_loops
description: "SOLVED app RAM layout for 39990-TVA-A160: the app entry at 0x140A8 derives gp=0xFEDF8000 / tp=0xBF000 / sp=0xFEDEF91C from ori 0x8000,r0,r1; a zero-clear loop at 0x146C0 wipes 0xFEDEC000..0xFEDFFFFF via sst.w r0,disp[ep]; a .data copy at 0x14766 writes flash 0x86260..0x8AB18 into 0xFEDF11B0..0xFEDF5A68; and 0xFEDEC000..0xFEDEF920 is stack painted 0xEBEBEBEB. Lets you compute the BOOT VALUE of any gp-relative cell from flash, and classify any cell as .data vs bss vs stack. Both boot writes are INVISIBLE to every gp-relative displacement scan."
metadata:
  type: reference
---

# App RAM layout + the two boot-init loops — traced 2026-08-02 (GATE-1 audit of gp-0x683c)

Program: `code.bin` (stock dump). All addresses are file offsets == image addresses.

## 1. The app entry derives every base register [EVIDENCE, `disassemble_bytes` @0x140A8]

```
0x140C0  ori   0x8000, r0, r1      ; r1 = 0x8000
0x140C4  movhi -0x121, r0, gp      ; gp = 0xFEDF0000
0x140C8  movea 0x0,    gp, gp
0x140CC  add   r1, gp              ; gp = 0xFEDF8000      <-- the kit's gp constant, PROVEN
0x140CE  movhi 0xb,    r0, tp      ; tp = 0x000B0000
0x140D2  movea 0x7000, tp, tp      ; tp = 0x000B7000
0x140D6  add   r1, tp              ; tp = 0x000BF000      <-- the kit's tp constant, PROVEN
0x140D8  movhi -0x121, r0, sp
0x140DC  movea -0x6e4, sp, sp      ; sp = 0xFEDEF91C
0x140E0  mov   -0x4, r1
0x140E2  and   r1, sp              ; sp = 0xFEDEF91C (already aligned)
0x140E4  jarl  0x000146C0, lp      ; <- C runtime init
0x140E8  jr    0x0001600E          ; <- main
```

⇒ **`gp = 0xFEDF8000` and `tp = 0xBF000` are now derived from the binary, not assumed.** Both fall out of
the same `r1 = 0x8000`; that they reproduce the kit's two long-standing constants simultaneously is the
cross-check. The bootloader has its OWN different bases (`0x1BA`: gp=0xFEDFFB00, sp=0xFEDFFB80) — never
mix them.

## 2. Boot write #1 — full RAM zero-clear [EVIDENCE, @0x146C0]

```
0x146C0  mov 0xfedec000, ep
0x146C6  sst.w r0, 0x8, ep      \
0x146C8  sst.w r0, 0x4, ep       |  16 bytes of zero per iteration
0x146CA  sst.w r0, 0xc, ep       |
0x146D2  sst.w r0, 0x0, ep      /
0x146CC  mov 0xfedfffff, r6
0x146D4  addi 0x10, ep, ep
0x146D8  cmp r6, ep
0x146DA  bc 0x000146C6
```
⇒ **zeroes `0xFEDEC000 .. 0xFEDFFFFF`** — i.e. the entire app RAM window, `gp-0xC000 .. gp+0x7FFF`.

## 3. Boot write #2 — the `.data` copy [EVIDENCE, @0x1475C..0x14794]

```
0x1475C  mov 0x86260, r14        ; flash src
0x14766  mov 0xfedf11b0, ep      ; RAM dst
0x1476C..0x14794                 ; 16 bytes/iter, ld.w r14 -> sst.w ep
0x14786  mov 0x8ab18, r10        ; flash src END
0x14792  cmp r10, r14 / bc 0x1476C
```
⇒ **flash `0x86260..0x8AB18` (0x48B8 = 18,616 B) → RAM `0xFEDF11B0..0xFEDF5A68`**
⇒ in gp terms: **`.data` occupies `gp-0x6E50 .. gp-0x2598`.**

**Boot value of any cell in that range:** `flash[0x86260 + (addr - 0xFEDF11B0)]`.
Everything else in `0xFEDEC000..0xFEDFFFFF` boots as **0x00** (bss, from §2).

## 4. Stack [EVIDENCE, @0x14796..0x14804]
`sp = 0xFEDEF91C`, grows DOWN. The runtime paints **`0xFEDEC000..0xFEDEF920` with `0xEBEBEBEB`**
(`mov 0xebebebeb,r12` @0x147BA / @0x147EE, bounded by `mov 0xfedef920` @0x147A0/0x147E0/0x147F6) — a
stack high-water canary. ⇒ **the stack region is `0xFEDEC000..0xFEDEF91C` and NOTHING above `0xFEDEF91C`
is ever reached by stack growth.** Any RAM cell above that is out of stack reach — a cheap, decisive
exclusion for GATE-1 audits.

## 5. 🛑 Why this matters for GATE 1 — two writers no scan can see
Both §2 and §3 write via `sst.w rX, disp[ep]` with a **computed `ep`**. They are invisible to:
disp16 scans, disp23 scans, `search_instructions` on a displacement, and `get_xrefs_to`. Any
"gp-0xNNNN has ZERO writers" claim in this kit is therefore really "zero *runtime* writers" — **every
cell in `0xFEDEC000..0xFEDFFFFF` is written at boot**, and every cell in `gp-0x6E50..gp-0x2598` is
written at boot with a *specific nonzero-capable flash byte*. Check §3 before calling a cell untouched.

Bonus: because the initializer lives in flash, a build **can choose a cave cell's boot value** by editing
`0x86260 + offset` — inside the main app CRC region, so the build script must re-CRC.

## Related
[[reference_accord_gate1_gp683c_ram_ownership_audit]] — the audit this came out of.
[[feedback-cave-two-gates-ram-ownership-and-closed-loop]] — GATE 1 is the reason this was traced.
