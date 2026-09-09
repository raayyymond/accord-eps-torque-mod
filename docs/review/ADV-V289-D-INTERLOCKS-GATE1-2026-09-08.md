# ADV-V289-D — Interlocks / GATE 1 / downstream — 2026-09-08

**Agent**: `advD` (subagent, reports to `team-lead`/`main`). Adversarial pass, surface D of
`docs/review/ADVERSARIAL-V289-PREREG-2026-09-08.md`. Study/analysis only — nothing built, flashed,
or sent. GhidraMCP only, `firmware-decompile` skill loaded first.

**Image under test**: `_v289_V289-V282BASE-SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ-KP.FLAT.Y0-CAVE.R24CMP.B6-NOTCHSIGN.B5-NOTCHCMP.B7-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin`.
SHA256 **re-hashed this session**: `f0c10c29752d2b9bc4ec510800cd4de58166ebbb87f05613b5ee8e7af339a3ed` —
matches the brief exactly. Base image used for comparison: the actual
`_v282_V282-V281R3BASE-...` plain image (not stock `code.bin`), read directly from
`../accord-firmwares/analysis-2020accord/`.

## VERDICT: **PASS** against every §D criterion. No do-not-flash finding.

---

## D2 first, because it grounds everything else: full byte-scope proof

**[EVIDENCE, `analysis-2020accord/verify/adv_v289_d2_bytediff.py`]** A byte-exact diff of V289 against
its own declared base (V282), `[0x13000, 0x100000)`, finds **exactly 10 diff runs, 185 bytes total**,
and every one of them is inside the declared scope:

| range | len | what |
|---|---|---|
| `0x2A174-0x2A178` | 4 | hook: `ld.hu 0x73ee,tp,r7` → `jr 0xC4C00` |
| `0xC4BD6-0xC4BDA` | 4 | 0x14A cave-exit redirect → `jr 0xC4BDC` (tail) |
| `0xC4BDC-0xC4BF8` | 28 | new tail body |
| `0xC4C00-0xC4C8C` | 140 (3 sub-runs, 2 coincidental unchanged `0xFF`→non-`0xFF`-boundary bytes) | new notch cave body |
| `0xC4FFC-0xC5000` | 4 | CRC trailer, block `[0xC4000,0xC5000)` |
| `0xC63E8-0xC63EC` | 3 | fb-pole cal `a`/`b`: 923/1560 → 875/2301 |
| `0xC6FFC-0xC7000` | 4 | CRC trailer, block `[0xC6000,0xC7000)` |

**No other byte in `[0x13000,0x100000)` differs between V282 and V289.** This is a stronger, simpler
proof of D2's core requirement than re-deriving control flow function by function: since the entire
duplicate compiled region `[0x2A30E,0x2B421)` and everything else in the binary is **provably
byte-identical to V282**, whatever reachability verdict already held for V282 (the V288 adversarial
pass: zero live entries) carries over to V289 unchanged, by construction.

I did **not** stop at inheritance — I independently re-ran the entry scan on the **V289 image itself**:

- `get_function_callers(0x2A93A)` (the orphan duplicate feedback-clamp function) → **no callers**.
- `get_xrefs_to(0x2A30E)` (duplicate region start) → **zero references of any kind**.
- `get_function_callers(0x28EA6)` (the real `FUN_00028ea6`) → **exactly one caller**, `FUN_0002214a`.
- `get_xrefs_to(0x2A174)` → **exactly 3 predecessors**, all `UNCONDITIONAL_JUMP` from `0x2A14A`/`0x2A15E`/`0x2A162` — matches the documented 3-branch+1-fallthrough convergence exactly, no new or missing predecessor.
- `get_xrefs_to(0xC4C00)` (cave entry) → **exactly 1 predecessor**, from `0x2A174`.
- `get_xrefs_to(0xC4BDC)` (tail entry) → **exactly 1 predecessor**, from `0xC4BD6`.
- Exact byte-signature search for the cave's own first 12 bytes, and the tail's full 28 bytes, elsewhere in the image: **1 occurrence each** — no linker-duplicated second copy of the new code (the recurring "compiled-twice" pattern seen elsewhere in this binary, e.g. `FUN_0002a93a`, does not repeat here).

**Full disassembly of both new blocks** (`disassemble_bytes dry_run:true`, 53 + 10 instructions):
`0xC4C00-0xC4C8C` (cave) and `0xC4BD6-0xC4BF8` (tail). **No `jarl` anywhere in either.** Only `jr`
(`0xC4C88 → 0x2A178`, independently decoded from raw bytes `b607f054` and cross-checked against
Ghidra's resolved target; `0xC4BD6 → 0xC4BDC`, independently decoded from `80070600`: `hw1=0x0780`
satisfies the Format-V `jr` fixed field exactly) and the relocated `jmp [lp]` at `0xC4BF6`, which reads
`lp` but never writes it. **`lp` is never clobbered** by the new code — closes the concern that a
corrupted `lp` could misdirect `FUN_00028ea6`'s eventual `dispose ...,lp` return into the duplicate
region.

Also independently decoded `0x2A174`'s new `jr` (`89078caa`): `hw1=0x0789` (reg2=0 ⇒ `jr`, not `jarl`);
disp = `sign_extend22(((0x0789&0x3F)<<16)|0xaa8c)` = `+0x9AA8C`; `0x2A174 + 0x9AA8C = 0xC4C00` exactly —
matches the claimed cave target, independently, not merely relayed from Ghidra.

**D2 verdict: PASS.**

---

## D1 — RAM census of `gp-0x6c44..gp-0x6c39` and neighbours

**Why this needed a full re-do**: the brief's own history note is correct and load-bearing — a prior
tracer session declared this run "fully verified free" using a `search_instructions`-based method that
**explicitly left `ld.b`/`st.b` unresolved** (its own addendum says so), and a *different* prior
"verified free" claim (`gp-0x68b0`, `gp-0x6ab0`) was subsequently falsified by exactly that gap (19 byte
accesses, and boot-initialized data, respectively). So I did not accept the inherited verdict — I
rebuilt the scanner from scratch with the corrected opcode table and ran it fresh against **this**
image.

**Method 1 [EVIDENCE, `analysis-2020accord/verify/adv_v289_d1_ram_census.py`]**: a raw little-endian
Python byte scan of the **entire V289 image**, decoding every `gp`-relative (`reg1==4`) disp16 form:
`ld.h`/`ld.w` (opcode `0x39`), `ld.hu` (opcode `0x3F`), `st.h`/`st.w` (opcode `0x3B`), `ld.b` (opcode
`0x38`, disp=hw2 exactly), `st.b` (opcode `0x3A`, disp=hw2 exactly), and gp-direct bit-ops (opcode
`0x3E`). **The `ld.b`/`st.b` decode was positive-controlled against 4 known instructions from the kit's
own record before trusting it** (`gp-0x6752`/`gp-0x6757` `ld.b`, `gp-0x6758`/`gp-0x6757` `st.b`) — all
4 decode exactly, including the odd-parity cases. A sanity check confirmed the decoder is not simply
broken (231 `ld.b` and 4166 `st.b` gp-based hits exist image-wide; the target window gets zero of them).

Result over `gp-0x6c54..gp-0x6c29` (wider than the 12-byte run, a margin of safety): **46 raw hits
total, ALL of them either (a) inside the cave/tail (`0xC4BDC-0xC4C8B`, exactly matching the design's own
claimed state accesses) or (b) on clearly different, occupied neighbouring cells** (`gp-0x6c2c`,
`gp-0x6c2a`, `gp-0x6c2e`, `gp-0x6c34`, `gp-0x6c38`, `gp-0x6c48`, `gp-0x6c4c`, `gp-0x6c50`, `gp-0x6c54`).
**Zero hits, of any form, land on the exact claimed-free run `gp-0x6c44..gp-0x6c39` outside the
cave/tail.**

**Method 2 [EVIDENCE, `search_instructions` on the V289 program, independent SLEIGH decode]**: queried
`6c44`, `6c40`, `6c3c`, `6c3a` directly. **Exact agreement with Method 1**: the only matches for each
are inside `FUN_000c4c00` (cave) or `FUN_000c4b34` (tail) — e.g. `6c44`: `ld.w -0x6c44,gp,r9 @0xC4C00`
and `st.w r13,-0x6c44,gp @0xC4C46`, nothing else, image-wide (171,806 instructions scanned). Positive
control on `6c2c` (Honda's oscillation detector's own input cell) in the same query batch: **8 real
hits** across `FUN_000428d4`, `FUN_00041464`, `FUN_00036c12`, `FUN_00071272`, `FUN_0007b022` — proving
the method finds real live cells correctly when they exist, not just returning null everywhere.

**Absolute-pointer / register-indirect check**: a whole-image scan for the literal 4-byte LE address
of each target cell — **zero hits**. A `movhi`/`movea`-pair proximity scan (base landing within
`±0x60` of any target cell) — **zero hits**, whole image. Additionally decompiled `FUN_000428d4`
(the nearest live neighbour, owning `gp-0x6c2c`) directly: it uses **only direct `gp`/`tp`-relative
addressing**, plus one **read-only** `tp`-relative LERP-table pointer-walk that stays entirely in
cal/flash space — no register-indirect RAM-write pattern of any kind. `gp-0x6c44..gp-0x6c39`
(displacements `0x6c39-0x6c44`) also falls **outside** the documented true stack range
(`gp-0xC000..gp-0x86E4`) — no stack-growth collision possible.

**Boot-value check, new this session [EVIDENCE, computed directly from the V289 image using the
documented `.data`-copy mechanism, `reference_accord_app_ram_layout_and_boot_init_loops.md`]**: all
four cells (`gp-0x6c44`, `gp-0x6c40`, `gp-0x6c3c` — words — and `gp-0x6c3a` — halfword) fall **inside**
the `.data`-initialized band (`gp-0x6E50..gp-0x2598`), i.e. they are **not** simply bss-zero by
assumption. I computed each cell's exact flash source offset (`0x86260 + (addr-0xFEDF11B0)`) and read
the bytes directly: **all four decode to exactly `0x00000000`/`0x0000`** in this image. **The notch
state provably boots to zero** — stronger than "no path bypasses the hook, so no sentinel is needed";
even a hypothetical missed path would see a state that starts at exactly zero, not stale garbage.

**Residual, stated plainly**: a sufficiently indirect, far-displaced computed-pointer chain elsewhere in
the ~2000-function image was not exhaustively hunted function-by-function — only the immediate
neighbours and the proximity/absolute-pointer scans were checked. This is the same class of
un-provable-by-static-scanning residual this kit's own doctrine already accepts for every prior
"free cell" finding (the `gp-0x1500` precedent), not a new gap specific to this build.

**D1 verdict: PASS.**

---

## D3 — downstream consumers

- **`gp-0x6b2e`** (the "S" telemetry cell, now carrying the **notched** value `y` after the hook, since
  the cave's last act is `jr 0x2A178` with the notch output in `r12`, and `0x2A17C` stores `r12` there
  unchanged): `search_instructions operand_pattern:"6b2e"` finds **exactly 2 writers** — the live
  `st.h @0x2A17C` and the pre-existing **unreachable** orphan `st.h @0x2B064` inside `FUN_0002a93a`
  (no callers, confirmed above) — and **zero readers of any kind, anywhere in the image**. This is
  *stronger* than the brief's own claim ("only an unreachable `ld.h` at `0x2A896`") — I could not find
  that instruction as a `gp-0x6b2e` access under either method; `gp-0x6b2e` is a pure dead/telemetry-only
  publish with **no internal consumer at all**, so no interlock reads it directly.
- **fb-pole cal cells `0xC63E8`/`0xC63EA`**: re-queried directly on V289 — **exactly 2 live readers**,
  both inside `FUN_00028ea6` (`0x28F86`, `0x28F8A`), matching the pre-existing GATE 1 record exactly.
  V289 adds no new reader. (Other substring hits on `73e8`/`73ea` are branch-target digit coincidences
  — `bne 0x173e8` etc. — adjudicated and excluded, the documented false-positive class.)
- **Honda's oscillation detector `FUN_000428d4`** reads `gp-0x6c2c` — independently confirmed (D1's
  census) to be a wholly separate, occupied cell with no overlap with the notch's state or with
  `gp-0x6b2e`. Decompiled directly (see D1): no code path in this function touches the notch's RAM.
- **Output-lag filter, gain stage, EME shaper, lockstep monitor, and any DTC/governor logic** downstream
  of `0x2A178`: **byte-identical to V282** (the D2 diff proves zero bytes changed anywhere past the
  hook except the two cal bytes and the two CRC trailers). Their code is untouched; their *input* value
  legitimately changes because `S` is now notched — that is the design's intended effect, already priced
  in the design doc's own loop-shaping analysis (§6), not a code-level defect this pass can or should
  re-litigate. No truncation risk beyond what already existed: both `S` and `y` are published via the
  same 16-bit `st.h` at `0x2A17C` that always existed, and both remain within the design's own stated
  `±15360`-scale magnitude domain.

**D3 verdict: PASS** (the interlocks' *inputs* change as designed; no interlock's *code* changes, and
no interlock gains a new, undocumented data dependency on the notch's internal state).

---

## D4 — the 0x14A byte-4 rung, plus a self-caught false alarm

Decompiled `FUN_000c4b34` directly. Ghidra merges the **pre-existing, unchanged** 166-byte comparator
block (`0xC4B34-0xC4BDA`) with the **new** 28-byte tail (`0xC4BDC-0xC4BF8`) into one function, since
they are contiguous — this initially looked like the tail was writing to `gp-0x1511` (frame byte 7),
which the brief never mentioned. **I checked this against my own D2 byte diff and a fresh writer-search
on both V282 and V289 before reporting it**: the `gp-0x1511` write (`0xC4BC4`/`0xC4BCE`) is
**byte-identical in both images** — it is old, pre-existing code, untouched by V289's tail. Recording
the false alarm and its resolution, per this kit's own doctrine, rather than either hiding it or
reporting it as a finding.

The tail's **actual new** code (confirmed via full disassembly, `0xC4BDC-0xC4BF8`):
```
ld.hu -0x6c3a,gp,r7   ; FLAG
andi  0xa0,r7,r7      ; keep bits 5,7 only
ld.bu -0x1514,gp,r6   ; existing byte 4
andi  0x5f,r6,r6      ; clear bits 5,7 only
or    r7,r6
st.b  r6,-0x1514,gp   ; write back
movea -0x1518,gp,r6   ; relocated: recompute frame pointer
jmp   [lp]            ; relocated: return (lp untouched, see D2)
```
Exactly matches the brief's description, byte-for-byte. Cross-checking the two earlier comparator
blocks (pre-existing, unchanged) in the same decompile:
- **bit 6** (`|r24| ≥ |T|`) is set once, early, and every subsequent mask (`0xdf`, `0x67`, `0x5f`) keeps
  bit 6's value — **untouched by the new tail**, matches "b4.6 stays."
- **bits 3/4** (`sign(gp-0x3680)`, `sign(r24)`) are set by the middle block and left alone by the final
  overwrite — matches "b4.3/b4.4 stay."
- **bits 5/7** are the *only* bits the final, new write changes. Both are the design doc's own declared
  spend: bit 5 was V282's `|r24| ≥ |aggregator|` comparator ("never used in an analysis"), bit 7 was
  `sign(gp-0x6b4c)`, the 11-slot fault-sum sign ("never used") — both pre-existing computations still
  run (now wasted work, harmless) and are overwritten by the FLAG-derived value. This is the documented,
  intentional remap, not an undocumented clobber.
- **Bits 0-2** are never written by this function at all (every mask preserves them) — Honda's bits
  stay Honda's, confirmed directly on the byte-identical, unchanged block.

**D4 verdict: PASS.**

---

## Timing (unchanged from the existing record — no new evidence this session)

Not re-derived fresh; deprioritized in favor of the higher-priority D1 gap the brief itself flagged.
Carrying forward the existing bounded estimate: the full cave (53 instructions, including the
rectification/flag-pack tail) is still a small fraction of a 1 kHz tick even under a pessimistic
per-instruction cycle count — structurally negligible, same caveat as before (no watchdog/overrun
counter has ever been found in this firmware; the argument is structural, not measured against a real
headroom figure).

---

## Summary for `team-lead`

| criterion | verdict | deciding evidence |
|---|---|---|
| D1 (RAM census) | **PASS** | 2 independent methods (corrected raw scan + Ghidra SLEIGH) agree exactly: zero non-cave/tail touches on `gp-0x6c44..gp-0x6c39`; boot value computed = exactly 0 |
| D2 (control flow) | **PASS** | byte-diff vs actual V282 base: only the declared 185 bytes differ, everywhere else provably identical; independently re-ran entry/xref scan on the V289 image itself; no `jarl` in either new block |
| D3 (downstream) | **PASS** | `gp-0x6b2e` has zero readers (stronger than claimed); fb-pole readers unchanged at 2; all downstream code byte-identical to V282, only its input value changes as designed |
| D4 (0x14A rung) | **PASS** | byte-exact tail disassembly matches the brief; bits 0-2/6 provably untouched; bits 5/7 are the documented, previously-unused spend; a self-raised false alarm on a different byte was checked and closed |

**No FAIL finding under §D.** The image can proceed on this surface; A/B/C-series adversaries' verdicts
are independent of this report.

Files: this doc; `analysis-2020accord/verify/adv_v289_d1_ram_census.py`;
`analysis-2020accord/verify/adv_v289_d2_bytediff.py`.
