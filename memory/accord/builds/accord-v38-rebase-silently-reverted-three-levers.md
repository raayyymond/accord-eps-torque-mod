---
name: accord-v38-rebase-silently-reverted-three-levers
description: "V76 was cut from V38, which predates V57 — so the V76/V78/V79/V80 chain silently lost the 0xC646C decouple, re-raised the shared sensor scale 4x, and restored the low-speed steer lockout. 🛑 CORRECTED 2026-08-08 — it is SEVEN levers, not three, and any V80-vs-V75 contrast carries FIVE confounds, not four."
metadata:
  type: reference
---

> 🛑 **CORRECTED 2026-08-08 — READ THIS FIRST. IT IS SEVEN LEVERS, NOT THREE, AND HERE ARE ALL SEVEN.**
> The V38 rebase (flown V75 → `build_v76_v38base`) reverted **seven levers**. The cell table further
> down names **five cells** because **lever 4 spans three cells** — that is the whole reason the two
> counts ever disagreed.
>
> | # | lever | cells | declared in the build's `NOT_CARRIED`? |
> |---|---|---|---|
> | 1 | DTC-`0x1d` interlock | `0xC407E` 850→**511** | ✅ yes — the point of the build |
> | 2 | friction ×1.5 | 14 sites → stock | ✅ yes |
> | 3 | Path-2 damper weight | `0xC63A0` 2048→1024 | ✅ yes |
> | **4** | **V57's decouple** | `0x2A1F0` `7CD0`→`746C` **+** `0xC6CD0` 3564→`FFFF` **+** `0xC646C` 891→**3564** | ❌ **no** — and the consequence (the 4× moving back onto the **SHARED six-reader cell**) went uncosted until V80 |
> | 5 | low-speed lockout | `0xC62EA` 0→**320** | ❌ no — named in the handoff and quantified at **3.06% of engaged time**, but absent from the build's own drop-list |
> | 6 | V42's ratchet fix | `0x454FE` `B5`→`BA` | ❌ no — restored only at **V80** |
> | **7** | **`gain_A` rec0/rec1** | `0xC6A72`–`0xC6A78`, `0xC6A86`–`0xC6A8C`, 512 → Honda's | ❌ **no, and never logged ANYWHERE until 2026-08-08** |
>
> *(V73's mode-0..17 FactorC/E edits were also reverted, but **were** declared, so they are not among
> the seven.)*
>
> ⇒ 🛑 **Any V80-vs-V75 contrast carries FIVE confounds, not four.** And note lever 7: **the r26 lane is
> NOT held constant across the two lineages** — exactly the variable
> [[accord-r24-is-the-grind1-actor-r26-nearly-blind]] re-prices.
> ⇒ 🛑 **Four of the seven were UNDECLARED.** A build's own `NOT_CARRIED` list is not a lineage audit;
> byte-check the current image against the whole lever list —
> [[accord-v81-carries-neither-grind1-fix]] has the grind-#1 half.

# 🛑 THE V38 REBASE SILENTLY REVERTED ~~THREE~~ **SEVEN** LEVERS

**2026-08-07, orchestrator's own byte read across the lineage.** V76 was cut from **V38**, which predates
V57's decouple — and **nothing in the V76 → V78 → V79 → V80 chain re-applies it.**

| lever | V62 · V68 · **V74 · V75** | **V76 · V78 · V79 · V80** |
|---|---|---|
| `0x2A1F0` reader disp | `0x7CD0` → **decoupled** `0xC6CD0` = 3564 | `0x746C` → **shared** `0xC646C` = 3564 |
| `0xC646C` shared sensor scale | stock **891** | **3564 (4×)** |
| `0xC62EA` low-speed steer lockout | **0** (removed) | **320** (restored) |
| `0xC63A0` Path-2 damper weight | **2048** | 1024 |
| `0x454FE` V42 macro-ratchet fix | `0xB5` | `0xBA` (**V80 restored it to `0xB5`**) |

🛑 **V80 vs V75 was therefore NEVER a single-variable damper comparison.** Any contrast between the two
lineages carries ~~four~~ **FIVE** confounds (2026-08-08: `gain_A` rec0/rec1 added — see the banner), not one.
⇒ This is the **same class** as the V53 rebase that dropped V42's `0x454FE` and V62's `sar` pair — see
[[accord-both-confirmed-fixes-were-off-the-car]]. 📋 **RULE 3 restated: byte-check the CURRENT image
against the whole lever list before reasoning from any recorded result.**

## `0xC646C` — the full reader map, and why it is **NOT** the 27 Hz driver
Exactly **6 static readers, 0 stores, 0 disp23 hits, 0 LE32-pointer hits**, established three
independent ways (Ghidra `search_instructions`, a fresh raw Python LE scan of **both** encodings, fresh
decompiles). It is a **Q15 dimensionless multiplicative scale** — `(x * cal) >> 0xf` at every site;
`3564 = 4 × 891` exactly.

| # | addr | function | role |
|---|---|---|---|
| 1 | `0x2a1ee` | `FUN_00028ea6` | **LKAS arbitration / CAN-setpoint→command — the one V57 decoupled** |
| 2 | `0x2a904` | *(orphan)* | **DEAD** — no function, no xrefs |
| 3 | `0x2b656` | `FUN_0002b62c` | **RECLASSIFIED**: output `gp-0x6af0` reaches only a private 2-function mode-flag debounce (`gp-0x677d` has exactly **2** static refs image-wide) plus a UDS packer with **0** static callers ⇒ **NO TORQUE PATH** |
| 4 | `0x2c488` | `FUN_0002c478` | output `gp-0x6b10` has **3 refs, all `st.h`, ZERO loads** — proven dead |
| 5 | `0x36686` | `FUN_00036682` | **the ONLY one reaching the motor** — multiplies RAW `gp-0x4f60`, adds into `FUN_0003aa2c` → governor → `gp-0x6b98` |
| 6 | `0x3684a` | `FUN_00036828` | modulates #5's hysteresis half-band via `gp-0x6b44` (2nd-order) |

🛑 **Reader #5 cannot drive a 27 Hz limit cycle — a BANDWIDTH argument.** Its output passes an IIR with
`alpha = tp+0x73d2 = 6` ⇒ `6/1024 = 0.00586`, corner **≈ 0.93 Hz, ≈ −26.6 dB at 21 Hz**. [EVIDENCE]
✅ **This also settles the prior "6 vs 14" discrepancy, in favour of 6** — see
[[reference-accord-c646c-shared-gain-not-lkas-only]].

⚠ **Reader #5's pre-filter `±0x200` clamp is the real cost, and it was never screened against a
V76-lineage log.** Its trigger on `|gp-0x4f60|` drops from ~**18,829** counts at stock to ~**4,707** at
4×. On route 66: `|bar|` engaged p50 174 · p90 1,424 · p99 3,346 · p99.9 3,712 · **max 3,849**; worst
event max 3,437; `|bar| ≥ 4707` fired **0 / 89,997 frames**. ⇒ **it did not bind** — but the margin is
only **22%**, and the CAN sensor's count scale is not proven identical to `gp-0x4f60`'s internal scale,
so this is *"did not fire on this drive"*, **NOT** *"cannot fire"*. **Worth a probe.**

⇒ **NET: the shared-cell 4× is a real, uncosted headroom regression that nobody signed off on — and it is
NOT the 27 Hz driver.** V81 removes the exposure for free by being cut from the V75 base.
✅ `0xC6CD0` = `0xFFFF` on V76/V78/V80 is **provably inert** — 0 instructions read `tp+0x7cd0` anywhere.

Related: [[accord-v80-flew-the-damper-is-a-relay]] · [[accord-check-build-lineage-before-proposing-lever]] ·
[[v57-decouple-built]] · [[reference-accord-c646c-shared-gain-not-lkas-only]]
