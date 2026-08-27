# TRACE 2026-08-20 — Honda's oscillation detector: why it's starved, what it would have done, and whether `0xC64FA` is a lever

**Program**: `code.bin` (stock, only program open this session, confirmed via `list_open_programs`).
**Method discipline**: decompile first, disasm to confirm crux instructions, raw Python LE byte scan as the
mandatory second method for every load-bearing count/null (per `firmware-decompile` skill and CLAUDE.md).
`gp = 0xFEDF8000`, `tp = 0xBF000`.

---

## TASK 1 — the `FUN_00046ea6(5)` gate in `FUN_000428d4`: verdict **(a), with new structural texture**

**[EVIDENCE, decompile + disasm `0x46ea6`]**
```c
undefined1 FUN_00046ea6(uint param_1) {
  if ((param_1 & 0xff) < 0x20)
      return ((*(uint*)(gp-0x18d0) | *(uint*)(gp-0x18d4)) >> (param_1 & 0x1f) & 1) != 0;
  return 0xff;   // out-of-range sentinel
}
```
Disasm (`0x46ea6-0x46eca`) confirms exactly this: two `ld.w` reads (`-0x18d4[gp]`, `-0x18d0[gp]`), an `or`,
a variable `shr` by `r6`(=param_1) then `shr 0x1`, `setfc` — i.e. **bit `param_1` of `(gp-0x18d0 | gp-0x18d4)`**.
Called as `FUN_00046ea6(5)` at `0x428d8`; `FUN_000428d4` decompile shows `if (iVar11 == 0) { …entire FSM,
including the `st.b` write to `gp-0x671a`… }` — **when bit 5 is SET, the whole reversal-FSM AND the write to
`gp-0x671a` are skipped for that tick** (falls through to an unrelated `uVar12=0x8000` / authority-slot
branch at the tail of the same function).

**What `gp-0x18d0`/`gp-0x18d4` are** [EVIDENCE, decompile + `get_function_callers` chased two levels]:
- Both are **OR-accumulators**, written only via two identical helpers: `FUN_0001601e` (`*(gp-0x18d0) |= *(param_1+8)`)
  and `FUN_000160c8` (`*(gp-0x18d4) |= *(param_1+8)`).
- Each helper has **exactly 3 callers, the SAME 3 functions for both**: `FUN_0001612c`, `FUN_000166d0`,
  `FUN_00016928`. All three decompile as **DTC/monitor debounce state machines**: each takes a DTC slot
  index (`param_1`), indexes a 28-byte-per-entry descriptor table at `tp-0x72C4` (=`0xB7D3C`, confirmed
  by `read_memory`) and a 2-byte-per-entry RAM status-word array at `gp-0x18ce`, and manipulates status
  bits that are textbook OBD-II DTC-status-byte values (`0x1603`, `0x2088`, `0x2098`, `0x20a8`, `0x20b8`
  literals observed being OR'd in) — pending/confirmed/test-failed-this-cycle bookkeeping. When a DTC's
  debounce counter confirms, the caller ORs that DTC's own bitmask (stored at its descriptor's offset+8)
  into the accumulator.
- **`FUN_0001601e`/`FUN_000160c8` never zero the word — only `FUN_000178c6` does** (`st.w r0,-0x18d0/-0x18d4,gp`).
  Its callers: `FUN_00047622` (2 callers itself — `FUN_0001702c`, a **pending-retry poll**: "if flag
  `gp-0x1bf0` is set, retry `FUN_00047622()`, clear the flag on success"; and `FUN_00047f78`, an elaborate
  **8-slot monitor-readiness consistency sweep** that calls `FUN_00047622()` only if it finds an anomaly)
  and `FUN_00057e5e`, a **one-time boot/hardware-init sequence** (touches SFR-range addresses `0xff83a000`,
  `0xffff611e`, `0xffff60b0`, calls the already-known boot-init routines `FUN_000490ac` (gp-0x6752 polarity
  init) and the gp-0x67fa state-gate init).

**Bit 5's owner** [EVIDENCE, `read_memory` of the descriptor table, 10 entries sampled at `0xB7D3C`]:
scanning offset+8 of entries 0-9, only **entry index 3** (`0xB7D3C+3*0x1C=0xB7D90`) has bit 5 set in its
mask (raw value 45 = `0b101101`, bits 0/2/3/5). Every other sampled entry's mask (`0xC00`, `0x1C00`,
`0x1C01`, `0xC01`, `0`) omits bit 5. **The exact DTC this slot corresponds to is NOT identified this
session** (no DTC-number lookup table was traced) — flagged as [BELIEF: it's some specific EPS
self-monitor, likely NOT "any fault at all"] pending that lookup.

**Verdict — (a), tuning starvation, not (b) structural block** [EVIDENCE + one inference marked BELIEF]:
- The gate is a **narrow DTC-confirmed interlock on ONE specific monitor slot**, not an always-1 sentinel
  and not an OR of "any fault whatsoever." Nothing in its producer chain latches it permanently — it is
  reset at boot and re-evaluated by a monitor-readiness sweep that runs repeatedly (not just once).
- **[BELIEF, circumstantial]**: V67 (186,321 frames) and V68 (53,991 frames) are both recorded fault-free
  in `BUILD-LINEAGE.md`. If bit 5's DTC had been continuously confirmed-active through those drives, that
  would very likely have surfaced as an MIL/DTC report, which is not in the record. This makes it more
  likely than not that bit 5 was clear (0) for most/all of those drives — i.e. `FUN_00046ea6(5)` was
  **not** the reason for the FSM's 0.000% duty; the FSM's **own internal magnitude threshold**
  (`|gp-0x6c2c| > T`, `T = cal 0xC620A = 12800`, a completely separate, already-documented gate) is the
  more likely cause. This is an inference, not a direct read of the flag's live value — see Open Questions.

---

## TASK 2 — the three (four) readers. **PID first.**

### `FUN_0003a382` (the PID) — **[EVIDENCE, disasm `0x3a4a6-0x3a50a` + `read_memory` `0xC67B0`] a fully verified, unconditional NO-OP**

```
0003a4a6  ld.bu -0x671a,gp,r14      ; r14 = gp-0x671a (the counter, byte)
0003a4aa  movea 0x77b0,tp,r15
0003a4ae  ld.hu 0x77b2,tp,r11       ; BASE  (own dedicated cal, 0xC67B2 -- NOT 0xC64FA)
0003a4b8  mov   r14,r13             ; r13 = axis
0003a4be  cmp   r11,r13 / bh 0x3a4ca   ; if axis > BASE: walk; else: Y[0]
0003a4ca  ld.hu 0x77b6,tp,r8        ; X_max
0003a4d0  bnc   0x3a4dc             ; if axis>=X_max: Y_max; else: walk X[0..1]/Y[0..2]
```
This is a **genuine continuous LERP index** — architecturally capable of a different result at every
value of `gp-0x671a`, unlike the other two readers' binary threshold. But the table itself, byte-read
twice (raw `read_memory` + disasm-confirmed field offsets, exact match):

| field | addr | value |
|---|---|---|
| BASE | `0xC67B2` | 5 |
| X[0] | `0xC67B4` | 10 |
| X_max | `0xC67B6` | 15 |
| **Y[0]** | `0xC67B8` | **1024** |
| **Y[1]** | `0xC67BA` | **1024** |
| **Y_max** | `0xC67BC` | **1024** |

All three Y knots equal 1024, and the combine divides by 1024 (Q10) elsewhere in the same function
(matching Stage A/B/C's own confirmed unity-gain poles). **`gainD_raw`/1024 = 1.000000 exactly, for
every value of `gp-0x671a` from 0 to 255 — not just below 5.** This resolves the flagged uncertainty in
`reference_accord_fun3a382_pid_structure_aggregator_addsign_and_freqresponse.md` ("gainD_raw ~1024/1024,
NOT independently re-verified") as a confirmed fact. **The 0.000%-duty caveat from Task brief does not
even apply here — there is no threshold to be starved of; Honda shipped a live index into a dead table.**
🛑 Note precisely: this is a **separate cal cell** (`0xC67B2`) from `0xC64FA`; it is not part of the
"shared CEIL" family at all, despite also currently holding the value 5.

### `FUN_00036c12` (friction lane, `gp-0x6b26`) — **[EVIDENCE, fresh decompile this session, matches this agent's own prior-session memory `reference_accord_friction_lane_fun36c12_smooth_no_stickslip.md` / `reference_accord_gp671a_creep_value_and_friction_lane_schedule.md`]**
```c
if (gp-0x671a < 0xff && gp-0x67f4 == 1) {
    if (gp-0x671a < cal(0xC64FD)=5)  { /* normal speed-indexed LERP, table 0xCBE74[mode] */ }
    else                              sVar7 = cal(0xC640A) = -8192;   // flat "stale" fallback
} else                                sVar7 = cal(0xC640C) = -3277;   // flat "invalid" fallback
```
**Predicate is `< cal(0xC64FD)=5`** — a **different, private cal** from `0xC64FA` (currently the same
value, 5, but a distinct RAM/cal cell — confirmed distinct addresses). **Answer to "what changes for
non-zero-but-below-5": nothing.** Counter values 0, 1, 2, 3, 4 all take the identical branch to the
identical LERP — computationally indistinguishable from counter=0. Only reaching 5 flips the branch.

### `FUN_00035b20` — **NOT in the original three, found this session: a 4th `gp-0x671a` consumer, and it feeds directly into the biquad function**

**[EVIDENCE, decompile + disasm confirms `bVar1 = gp-0x671a < cal(0xC64FA)=5` at the exact same address
the arm-condition search flagged]**. Structure: computes THREE independent LERPs — `uVar5` (axis
`gp-0x69a8`), `uVar4`="LERP_B" and `uVar7`="LERP_C" (both axis `gp-0x6a64`) — then selects
`bVar1 ? LERP_C : LERP_B`, takes `min(selected, uVar5)`, asymmetric-ramp-rate-limits it, and stores to
`gp-0x37c0` (float state) / **`gp-0x69a0`**. `gp-0x69a0` has exactly 2 touches image-wide (`search_instructions`
"69a0", cross-checked, no false positives plausible given both hits are `st.h`/`ld.hu` inside named
functions): the sole write here, and the **sole read is inside `FUN_000352b4` — the dead-biquad function**
(`0x352e2 ld.hu -0x69a0,gp,r18`). Table bytes, `read_memory` `0xC6910`:

| | BASE | X pts | Y pts |
|---|---|---|---|
| LERP_B (`gp-0x671a>=5`) | 640 | 3200/6400/12800 | 358/307/307/307 |
| LERP_C (`gp-0x671a<5`, normal) | 356 | 1636/3200/6016 | 358/358/461/512 |

At moderate-to-high axis, LERP_B tops out at **307** vs LERP_C's **461-512** — a real but modest
(~33-40%) ceiling reduction when oscillation is detected, feeding a rate-limited value directly into the
biquad function regardless of that function's own notch-arm state (peak-hold/IIR machinery there is
otherwise live every tick per prior memory). **This consumer's downstream numeric role inside
`FUN_000352b4` (`r18`'s exact use) was NOT re-traced this session** — inherited structural
characterization only; flagged BELIEF for that specific point.

---

## TASK 3 — what Honda's detector would have done, and the frequency mismatch

Full consequence set if `gp-0x671a` reached 5 under stock wiring:
1. **`FUN_000352b4` notch arms** — pole ≈**42.3 Hz**, zero ≈**55.2 Hz** [EVIDENCE, inherited from this
   agent's own prior verified sessions, `reference_accord_dead_biquad_fun352b4_pole_characterized_and_reversal_counter_arm.md`
   / `reference_accord_biquad_is_a_notch_v103_armed_and_recentering_priced_short.md` — V103 changed only
   the arm SOURCE (`gp-0x6806` instead of `gp-0x671a`), not the filter coefficients, so these numbers
   describe what stock's own gate would have produced had it ever fired].
2. **`FUN_0003aa2c` r24/r26 "third arm"** selects `0xC6440=2048`/`0xC643E=1536` over the mode-indexed LERP
   default (already-documented, `build_v63/v67/v68_tva.py`).
3. **`FUN_00035b20`** switches the ceiling feeding the biquad's `r18` from ~461-512 to a flat 307 (new
   this session, above).
4. **`FUN_0003a382` (PID)**: no effect (flat table, Task 2).
5. **`FUN_00036c12` (friction)**: flips to a flat -8192 gain on a DIFFERENT cal (`0xC64FD`), not gated by
   `0xC64FA` at all.

**Is this well-matched to the car's actual problems? [EVIDENCE for the frequencies being compared,
BELIEF for the interpretive conclusion]** — **No.** The notch (42-55 Hz) sits **5-7x above** both
measured symptom bands this kit has repeatedly instrumented on-car: the ratchet at **7.79 Hz** (Q 14-29,
`accord/mechanism/accord-ratchet-is-a-lightly-damped-resonance.md`) and the split-half-stable **21.73 Hz** line. The
r24/r26 third-arm cells and the friction flat-fallback are non-frequency-selective gain changes, so they
don't carry a frequency mismatch the same way, but they were also extensively fought over V42-V88 and
found either falsified or unreachable through this same gate. **[BELIEF]**: a 42-55 Hz notch reads as
built for a **high-frequency buzz or an electrical/sensor-glitch class of oscillation**, not a
lightly-damped low-teens-Hz mechanical resonance — plausibly tuned for a different application of this
EPS platform, or a rare edge-case transient, rather than this car's actual, sustained failure mode. This
is inference about Honda's intent, not something derivable from the disassembly alone.

---

## TASK 4 — `0xC64FA`: lever or landmine? **Landmine, confirmed and now wider than previously recorded.**

**Reader/toucher census, two independent methods, cross-validated:**

1. **Ghidra `search_instructions`, correct operand text `"74fa"`** (the earlier attempt searched `"64fa"`
   — the resolved absolute address — and got 2 branch-target-text false positives; `tp`-relative operands
   render as the raw displacement `0x74fa`, not `0xC64FA` — a self-caught methodology error, corrected
   before reporting): **8 hits**, all `ld.bu 0x74fa,tp,rX` — 5 inside `FUN_000428d4` itself (the
   producer's own re-reads of CEIL for its clamp/latch logic), 1 each in `FUN_000352b4` (biquad arm),
   `FUN_00035b20` (new 4th consumer), `FUN_0003aa2c` (r24/r26 arm).
2. **Raw Python LE byte scan, whole 1 MiB image, both `ld.bu` parities (`hw2==0x74FA` and `0x74FB`)**:
   **21 raw candidates.** Adjudicated every one:
   - The same 8 Ghidra hits, confirmed.
   - **10 NEW hits, `0x260BC-0x261A2`, all inside `FUN_00025c32`** (a function `get_function_by_address`
     confirms as defined, body `0x25c32-0x26c7f`) — **completely missed by `search_instructions`**, a
     direct instance of the documented "scans only already-analysed instructions, reports `truncated:false`
     anyway" trap. Disasm-confirmed (`disassemble_bytes`, `dry_run:true`) as a genuine unrolled loop over
     4 sub-slots per pass, each doing `ld.bu 0x74fb,tp,rX` (CEIL) twice per rung as an increment-and-compare
     bound — structurally a **debounce/match-window counter unrelated to `gp-0x671a`** (no reference to
     `gp-0x671a` appears anywhere in this loop). **This function's exact purpose is not characterized this
     session** — flagged as an open item, but its use of `0xC64FA` as a shared numeric constant is solid.
   - **3 excluded, with reason**: `0x7B2B6` — disasm shows the bytes there are actually a 2-byte `sst.w`
     instruction; the apparent `hw2=0x74FA` was a byte-alignment coincidence spanning instruction
     boundaries (verified, not assumed). `0xBDB7B`, `0xBEEBB` — `get_function_by_address` returns "No
     function found" for both; they sit below `tp` in what is very likely a data/table region, not code.

**Total: 18 real, verified touches across 5 functions** — this **reconciles exactly** with
`builds/v80_v107/build_v103_tva.py`'s docstring figure ("~18 in-code readers"), which this session initially could not
confirm via Ghidra alone and can now confirm as accurate.

**Verdict: LANDMINE, and more so than the existing record states.** Not only does `0xC64FA` gate 4
distinct oscillation-response consumers (producer + 3 confirmed arms) simultaneously — it is **also
reused, unrelated, inside a completely different subsystem (`FUN_00025c32`)** for what looks like a
debounce/match-window count. Editing its value would move both families at once. **Confirmed, not
merely inherited from the record.**

🛑 Not checked this session: the 6-byte extended-displacement (disp23) encoding form. All 18 confirmed
touches use the cheap 4-byte form; no evidence of the 6-byte form was sought. Flagged as a residual gap,
consistent with how this same gap has been flagged for other cals in this kit's memory.

**Private in-place repoint candidates (the V103 pattern — repoint one consumer's source/predicate without
touching the shared cal):**
- `FUN_000352b4` (biquad) — **already done**, V103, flown. Not a new candidate.
- `FUN_0003aa2c` (r24/r26 third arm) — structurally repointable the same way, but `0xC6440`/`0xC643E`
  are **not virgin** (V42-V88, reverted, "the rate lane" era) — a private repoint would still need fresh
  cal values, and per the operator's constraint against introducing more resonance, this is not obviously
  safe to recommend without further work.
- **`FUN_00035b20` — a genuinely unexplored candidate**, named here for the first time: site
  `0x35BE6` (`ld.bu 0x74fa,tp,r8`, compared against `r13`=gp-0x671a shortly after). Repointing its
  compare source the same way V103 repointed `FUN_000352b4`'s would give the ceiling-reduction behavior
  (Task 3, item 3) a live arm without touching the shared cal. **Not specified to the byte level this
  session** — would need the same careful displacement-arithmetic verification V103's build script did.

---

## Open questions / verification needed

1. **Bit 5's exact DTC identity.** Would need either a DTC-index-to-OBD-code lookup table trace (not
   located this session) or live telemetry reading `gp-0x18d0`/`gp-0x18d4` bit 5 directly. This is the
   one gap standing between the (a)-verdict-by-inference and a directly-measured confirmation.
2. **Live value of `gp-0x671a` during ordinary fault-free driving**, ideally on a current (8x-gain-era)
   build — the existing 0.000% figures (V67/V68) predate the 8x gain and predate this session's
   discovery that the FSM-skip gate is DTC-keyed rather than a blanket block. A telemetry tap on
   `gp-0x671a` itself (not just the `>=5` predicate) would settle whether it moves at all in [1,4] and
   whether it reaches 5 more often under the current gain regime.
3. **`FUN_00025c32`'s actual purpose** — not decompiled this session (4KB function); its 10 touches on
   `0xC64FA` are confirmed real but its semantic role (and therefore the full blast radius of editing
   `0xC64FA`) is not.
4. **`FUN_000352b4`'s exact use of `r18`(=gp-0x69a0)** — inherited structural characterization
   ("peak-hold output stage"), not re-verified against this specific register this session.
5. **6-byte extended-displacement form for `0xC64FA`** — not swept.

None of the above change the headline verdicts (Task 1: (a), tuning not structural, moderate confidence;
Task 4: landmine, high confidence) — they would sharpen them.
