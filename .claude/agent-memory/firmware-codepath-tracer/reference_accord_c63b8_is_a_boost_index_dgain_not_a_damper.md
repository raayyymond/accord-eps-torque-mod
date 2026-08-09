---
name: reference_accord_c63b8_is_a_boost_index_dgain_not_a_damper
description: "ADVERSARIAL RESULT — 0xC63B8 (=41) is FUN_0003b66a's derivative gain, and it is LIVE (1 kHz, gate passes, cal genuinely read at 0x3b80a) but it is NOT a damper lever. gp-0x6b9a's value path is DEAD everywhere (gate-only, both consumers); the ONLY surviving value path is gp-0x6ba6 = |output| -> FUN_00034a72's boost AMPLITUDE LERPs, i.e. a rectified base-assist GAIN-SCHEDULE index at 2f. FUN_00034350's copy of that path is inert (flat-1024 LERP in modes 10/24/26/27). Mechanism = the V58/V59/V60 parametric pump, already flown and NULL."
metadata:
  type: reference
---

# `0xC63B8` — live cal, wrong mechanism (2026-08-09, `ADVERSARY-LIVENESS`, stock `code.bin`)

Adversarial review of the claim *"`FUN_0003b66a` is a live 1 kHz band-pass damper whose output reaches
the motor, so raising `0xC63B8` will change the car."* **Two conjuncts hold, the load-bearing one does not.**

## What `0xC63B8` is [EVIDENCE, byte-confirmed]
`ld.hu 0x73b8[tp],r11` @**`0x3b80a`** ⇒ `tp+0x73b8` = **`0xC63B8`**, read direct from flash every tick,
no RAM shadow, outside the bootloader's skipped `[0xC5000,0xC5FFC)`. Cal block `0xC63B0..BF` =
`00 80 33 33 33 00 01 00 29 00 00 02 00 00 00 04` ⇒
`0xC63B4`=**51** (both derivative EMA stages, α=51/1024, ≈8.13 Hz/pole) · `0xC63B6`=**1** (output scale)
· `0xC63B8`=**41** (derivative gain, ×41/1024) · `0xC63BA`=**512** (torque EMA α=0.5).

Structure (constants all decoded from the instruction bytes):
```
fVar6      = slew-limited(±565/tick), clamped(±2000) model  ≈ COLUMN RATE in °/s
             (scale check: 0xC613A=1159 /32768 × 6.0 × 4.7121 ct/°/s = 1.0005 — unity, so fVar6 is °/s)
D_pre      = EMA2(α=51/1024) of  (fVar6[n]-fVar6[n-1]) × 17.453293      -> rad/s²
D          = clamp(D_pre × 0xC63B8/1024, ±10)          @0x3b84a/0x3b856
out(r28)   = ( D×1024  +  EMA2(α=0xC63BA/1024, gp-0x4f60×4)>>2 ) × 0xC63B6
gp-0x6b9a  = out (signed, st.h @0x3b8b0)      gp-0x6ba6 = |out| (st.h @0x3b892)
```
Derivative × two 8.13 Hz poles ⇒ a band-pass peaking right on the 7.79 Hz ratchet. That shape is real.

## Why it is still not a damper [EVIDENCE]
`scan_gp_accesses.py` on stock `code.bin`, both encodings, every ext-disp candidate adjudicated as an
alias of an already-identified Format-VII instruction (no extra sites):

| cell | writers | readers | disposition |
|---|---|---|---|
| `gp-0x6b9a` (signed) | 1 (`0x3b8b0`) | 6 + 1 lockstep | **value path DEAD everywhere** |
| `gp-0x6ba6` (=\|·\|) | 1 (`0x3b892`) | 4 + 1 lockstep | one live value path only |
| `gp-0x6bcc` | 1 (`0x34438`) | **0** | dead telemetry tap |

- **`gp-0x6b9a` never carries a value.** In `FUN_00034a72` its single value use is `addi 0x6400,r15,r6`
  @`0x34c9c` and `r15` is destroyed by `ori 0xc801,r0,r15` @`0x34ca4` two instructions later — a ±25600
  plausibility gate. In `FUN_00034350` all three loads (`0x34414/41e/428`) converge on the identical
  idiom @`0x3442e`. **Its SIGN — the whole point of a damper — has no output effect anywhere.**
- **`FUN_00034350`'s `gp-0x6ba6` path is INERT.** Selector `tp+0x7498`=`0xC6498`=**1** routes
  `gp-0x6ba6` into the factor-1 LERP at pointer table `0xC9CCC`, but that table is
  **Y=[1024,1024,1024,1024] (flat unity) in modes 10/24/26/27** — X=[205,1331,2355,3072]. Index-independent.
  (Corroborates MEMORY.md's "'FactorA'=seed closed, 11ch pinned 1024".)
- **⇒ The sole surviving value path is `gp-0x6ba6` → `FUN_00034a72` boost LERP1 `0xCA4F4`/LERP4 `0xCA23C`.**
  Mode 26: LERP1 X=[0,512,1490,2529,3645,5120] Y=[16384,14658,11676,9362,8245,8188]. That is a **rectified
  gain-schedule index on BASE ASSIST**, not an additive torque — memoryless, so it changes magnitude at
  every frequency identically and **never phase**. It cannot damp.

## Rate mismatch [EVIDENCE]
Producer `FUN_0003b66a` — exactly **one** call site, `jarl 0x3b66a,lp` @**`0x223d2`** (Ghidra + raw
Format-V scan agree; scanner self-checked against the known `0x2240e`→`FUN_0003b8f6` call), guarded by
`cmp r0,r28 / be 0x223d6` @`0x223cc` where `r28 = (1<<(gp-0x67fa&0xf)) & 0x830` ⇒ **states {4,5,11}, and
NOT state 10.** Runs at 1 kHz.
Both consumers (`FUN_00034a72` @`0x232c0`, `FUN_00034350` @`0x23276`) are called only from
`FUN_00022ca0` = **100 Hz** ⇒ **9 of every 10 computed values are overwritten unread.**

## Entry gate — passes; the `else` sentinel branch is NOT the normal path [EVIDENCE]
Immediates read from bytes; the decompiler's "13000 vs 0x6591" is **faithful, not a decode error**
(`addi 0x32c8` = 13000; `addi -0x6591`, 0x6591 = 26001 ⇒ symmetric ±13000):
`|gp-0x4f60| ≤ 25600` · `|gp-0x6abc| ≤ 13000` (≈±2759 °/s — unreachable; V68 measured sibling
`gp-0x6ac0` p99≈843, MAX≈2219) · `gp-0x6752 ∈ {-1,0,1}` — **boot constant +1, exactly 3 stores
image-wide (`0x490c0/0x49838/0x49844`), all in init `FUN_000490ac`** ⇒ always passes ·
`|gp-0x4f62| ≤ 25600`. ⚠ Corrects my own [[reference_accord_fun3b8f6_fir_not_biquad_inertia_friction_and_free_taps]]
§2, which recorded this window as `< 12969`.

## Dose response (integer/float mirror of the code, fs=1000)
Ratchet 1.29° p-p @7.79 Hz ⇒ column-rate amplitude 31.6 °/s. Peak D-term added to the index:

| `0xC63B8` | @7.79 Hz | @21.09 Hz | boost gain at that index (LERP1 mode 26) |
|---|---|---|---|
| **41 (stock)** | 577 ct | 387 ct | ≈0.88× |
| 82 | 1153 ct | 775 ct | ≈0.78× |
| 164 | 2306 ct | 1549 ct | ≈0.60× |
| 410 | 5766 ct | 3873 ct | ≈0.47× |

Clamp rail is 10240 ct, so the lever stays **linear** — no relay behaviour, unlike V80's damper. The
±25600 plausibility gates in both consumers are also far out of reach. **The lever is NOT vacuous** — it
moves base-assist gain a lot. It just does it as **parametric 2f modulation of assist**, not as damping.

## 🛑 The mechanism is already flown and NULL
`gp-0x6ba6` **is** the boost-amplitude index of the V58/V59/V60 arc. V60 (`0xD2006` 102→43) attacked this
exact LERP and returned NULL, closing the parametric pump. [[accord-v60-null-closes-parametric-pump]]
says in terms: *"Do not propose `0xC63BA` as a grinding fix… an adjacent lever on a mechanism that has
just been falsified, made to look fresh by a new rationale."* **`0xC63B8` is `0xC63BA` minus two bytes,
in the same function, on the same `r28`, into the same two cells, into the same LERPs.** Raising it
increases pump depth on the base-assist path (V59: eps 0.013–0.169 vs threshold 0.147 — marginal), and
changes manual steering feel, not just the LKAS lane.

Related: [[reference_accord_gp6b9a_r21_gate_and_fault_sentinel_mechanism]],
[[reference_accord_fun34350_five_factor_product_and_sign_relay_full_disasm]],
[[reference_accord_fun2214a_is_state_mask_not_phase_divider_loop_all_1khz]].
