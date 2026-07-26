# HANDOFF — 2026-07-18 — Setpoint-limit raise, full base-assist model, `gp-0x4f60` correction, Sport-mode negative

**Platform:** 2020 Accord `39990-TVA-A160`, V850E2. **Target:** stock Ghidra `code.bin` (flat base 0), `gp=0xFEDF8000`, `tp=0xBF000`. **Tooling:** GhidraMCP + raw byte dumps of `../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin`; 4 `firmware-codepath-tracer` subagents (Sonnet), every load-bearing claim re-verified by the lead in Ghidra.

**No CAN, no UDS, no flash operation occurred. No build was produced or changed.** Analysis + model + memory pass only.

> **CORRECTION 2026-07-18 (V39 session):** the six-lane assist summary below was incomplete. `FUN_0003aa2c` also computes two inline Sensor-B torque-rate lanes (`gp-0x4f62 -> r26/r24`) and adds `FUN_00036682`; the direct `r24` lane can reach +/-8192. The `FUN_000352b4` validity branch was inverted below: normal `gp-0x4f60` inside +/-25600 stores `gp-0x6b86`, not zero. Assist-inclusive `gp-0x6acc` can conservatively reach 7322, not the old 4342/4608 estimate; final `gp-0x6b98` uses the separate `gp-0x6afe+r20` path. The canonical correction is in `eps_lkas_chain_model.py` and `HANDOFF-2026-07-18-v39-opposing-torque-rate-guard.md`.

---

## The operator's questions

1. Can we raise `arb_setpoint_limit` so it stops clipping the LKAS setpoint? Would raising it cause hard / soft / gentle EME issues downstream?
2. Fully and explicitly define the pseudocode for **assist** (not simplified).
3. Update the LKAS model chain accordingly.
4. (mid-session) Is the Accord's **Sport-mode** steering tightening applied by this EPS firmware?

---

## 1. Setpoint limit — YES, safe, but a trim; and it needs a build-script change first

The premise is correct. openpilot's `CAR.HONDA_ACCORD` uses `torqueBP = [[0, 4096]]` (`opendbc_reference/honda/interface.py:114`), so the setpoint reaches `4096 × -4` = **16384** against a **15360** clamp — the top **6.25%** of the command range is clipped.

**The mechanism is a degenerate LERP.** All 28 records across 5 banks (`0xE4180/0xE5180/0xE6180/0xE7180/0xE8100`) carry a **flat 15360 Y row** at every one of 9 breakpoints; both out-of-range early exits also return 15360. The axis is `gp-0x6a5e` (AVG voter = **driver column torque**, read `@0x28f0e`) — so this table was designed to taper LKAS authority as the driver pushes back, and was shipped flattened. That is a latent tuning surface nobody had noticed.

**Gain from raising it: +6.71% top-end at every build tier** (V9 417→445 vs clamp 512; V31 835→891 vs 1024; V38 1670→1782 vs 2048). The arb output clamp never binds.

**EME verdict:**

| mechanism | verdict | evidence |
|---|---|---|
| Gentle | **causally impossible** | `gp-0x682f = min(\|r15\|>>5, 255)`; `r15` loaded once `@0x28f26` from `gp-0x4f60` (driver torque) and never rewritten through `0x29068` — every instruction in the span read directly |
| Hard | **no new failure mode** | zero hits for float `15360.0` image-wide; no mirrored table copy; monitor `FUN_00043e44` casts the *same* int `gp-0x6acc` `@0x4467a` (`cvtf.ws`→`cvtf.sd`→`×1/1024`→`cmpf.d lt 8.0`) — a predictive-vs-actual check, not a parallel float recomputation |
| Soft | **only exposure, small** | +6.7% reaches `gp-0x6acc`, against a V31/V37/V38 bound floored at 4096/5120 vs max command ~1782 |

**[OPEN]** the transient lockstep margin during a fast setpoint slew — the ~6.7% scales a pre-existing "actual lags predicted" term against the `±5/1024` bit32 threshold. Not a new mechanism, but unquantified. **Close before flashing.**

### ~~*** BUILD BLOCKER ***~~ — RESOLVED 2026-07-18, SHIPPED IN V38

> **SUPERSEDED.** The blocker below is cleared and the raise now ships in V38. See `HANDOFF-2026-07-17-v38.md` (revised) and `memory/reference_accord_setpoint_limit_15360_lerp.md`. Historical framing retained — the fails-closed mechanism is worth remembering.

`0xE4180` sits in bootloader CRC block `[0xE4000, 0xE4FFC)` (trailer at `0xE4FFC`), confirmed by running `verify_bootloader_crc.py` on the stock dump (49 blocks, 0 mismatches). Builds through V37 recomputed only `TOUCHED_BLOCKS = [(0xC6000,0xC6FFC), (0x13000,0xC4FFC)]`.

Patching without adding `(0xE4000, 0xE4FFC)` → `walk()` mismatch → the builder's self-check refuses to emit the `.rwd`. **Fails closed** — safe, but a failure. Every build to that date touched only the compact `0xC6xxx` cal block.

**Resolution:** `build_v38_tva.py` adds **both** `(0xE4000,0xE4FFC)` and `(0xE5000,0xE5FFC)`. The 49-block chain survives intact because `walk()` locates each next block via u16 page fields at `block_start-8/-6`, which live in the **preceding** block's CRC range — never inside a patched block. Post-patch walk: 49 blocks, 0 mismatches.

**Patch surface as shipped: 72 halfwords across 8 records**, not 9 across 1. The narrow scope below was correct for the live record but was deliberately widened: `gp-0x674e` can take `{0,1,3,4,6,7,8,9}` and the HW-ID that fixes our slot is **not in `code.bin`** (UDS service-0x84, written at manufacture), so all 8 reachable records were raised to make the change immune to slot resolution. Unreachable records 2, 5, 10-15 left stock.

~~**Patch surface: 9 halfwords at `0xE41BC..0xE41CC`**~~ (record `0xE41A8`, selected by `gp-0x674e = 1`). An early estimate of 144 halfwords assumed the selector was the variant slot index — it is not. (Coincidentally the shipped 8-record scope is 72 halfwords, still half that bad estimate.)

### Recommendation — TAKEN

Fold into a build with other content. Gain `0xC646C` remains the lever that actually moves top-end torque; this is a correctness fix worth ~6.7% on the top 6% of range. ✅ Done: folded into V38 rather than spinning a dedicated flash cycle.

---

## 2 & 3. Base assist — modelled explicitly; two structural corrections

`analysis-2020accord/eps_lkas_chain_model.py` rewritten (new Section 3B + 6B). Runs clean; both historical regimes still reproduce (V9 soft-cut + gentle EME; V31 fixes soft; V37 fixes gentle); V38 verified at exactly 2× V31 per tick.

**Correction A — assist is SIX lanes, not one term:**

| producer | lane | role |
|---|---|---|
| `FUN_00034a72` | `gp-0x6bbe` | the boost curve proper [VERIFIED] |
| `FUN_00034350` | `gp-0x6bd0` | 5 multiplied gains, sign forced opposite `gp-0x6abe` [INFERRED: damping] |
| `FUN_00036c12` | `gp-0x6b26` | curve × `gp-0x6c2e` [INFERRED: friction] |
| `FUN_0003a382` | `gp-0x6ad4` | 3-stage cascaded IIR [INFERRED: resonance] |
| `FUN_00036388` | `gp-0x6b62` | ±1/tick accumulator + hysteresis [INFERRED: return-to-centre] |
| `FUN_000352b4` | `gp-0x6b86` | effectively inert (gate is at the ±25600 bail edge) [INFERRED] |

Role labels are structural inference — none of these functions carries a confirming string.

**Correction B — assist joins at the AGGREGATOR, not the LKAS mixer.** The mixer (`FUN_00026c80`) + distribute (`FUN_00025c32`) sum only ~11 *LKAS-internal* channels into `gp-0x6b4c`. Assist joins one stage later at `m_motor_torque_demand_aggregator` `FUN_0003aa2c` → `gp-0x6b94`. "Distribute source index 1" and "the ~10 aggregator lanes" were two separate stages conflated into one.

**Why this matters:** LKAS and assist become one scalar **before** the governor (`FUN_0004503c`), the comp-add (`FUN_000456a4`), and the soft-EME shaper (`FUN_00042af8`). So base assist passes through the *same* governor and *same* shaper as LKAS, with no bypass. That structurally explains the operator's Era 16 reframe — a soft-EME cut is felt as the *whole* power steering dropping out, not merely LKAS easing off. Previously an observation; now a consequence of the topology.

---

## 4. Sport mode — CONFIDENT NEGATIVE

**Sport-mode steering tightening is not implemented by this EPS firmware.**

The base-assist boost curve is selected by the byte `gp+0x63fd` (positive gp displacement, `0xFEDFE3FD`, read `@0x34abc`) indexing a **34-entry** array `@0xCA154`. Two families exist: *rising* (top-end 1238) and *falling* (top-end ~440). **Our A160 runs index 10** (falling: `541, 639, 653, 551, 439, 439`).

Three independent grounds for the negative:

1. **No writer is CAN-fed.** All three writers traced to instruction level (exhaustive `0x63fd[gp]` search, 31 hits, no others): `FUN_00042692 @0x426ae` (boot-once, static ROM table, gated on `gp-0x6d78 & 8`); `FUN_00042746` (runtime, but every input is internal — `gp-0x6806`/`gp-0x69b0` written *only* by `m_steer_torque_arbitration`, `gp-0x67e2`/`gp-0x67f6`/`gp-0x68ab` self-contained — a sensor-fault **failover** reselector); `FUN_0004a798 @0x4a7fc` (UDS/PasCom bench command).
2. **No drive-mode signal is decoded.** 21 standard CAN IDs decoded; none reaches this byte. **[OPEN]** semantic names for 20 of 21 (no local DBC).
3. **The data forecloses it.** Our row's four reachable columns are `{10,10,11,11}` — all the same family, ~1% apart. A real Sport mode needs a falling↔rising swing (~2.8×). **Our variant row does not contain that pair.**

Whatever tightens the wheel in Sport is another module or perceptual. No firmware evidence distinguishes those.

**Incidental, and worth knowing:** slot 0 is the blank `"00000"` no-match fallback and selects the **rising** family. An ECU whose HW-ID was never programmed would run ~2.8× more assist at high column torque. Relevant before swapping or re-IDing an EPS unit.

---

## 5. `gp-0x4f60` — a correction of record that propagates

**`gp-0x4f60` is SENSOR-B (TAS) DRIVER COLUMN TORQUE.** Decisive: the CAN-399 packer `FUN_00055c42` emits `STEER_TORQUE_SENSOR = -(gp-0x4f60 × 125/128)`.

It is **not** column/motor angular velocity (Era 18 + `segmentD` label) and **not** vehicle speed (assist-lane reading). Both errors generalized from a downstream *use* to the signal's *identity*.

**Consequence — the gentle-EME causal story is reframed.** The debounce SM watches **driver hand torque**, not the LKAS command. The correlation with saturated LKAS commands is real but incidental (hard curves are where the driver also loads the column). This explains why LKAS-command-side experiments (V33's decider gate) kept missing, and fits the operator's report of a mid-turn event *with hands on the wheel*. **V37 still works and for the believed reason** — raising the gate to 255 means `torque > 255` can never fire against a channel saturating *at* 255. Only the "why" changes.

⚠ **This same correction was made on 2026-07-07** (`docs/HANDOFF-2026-07-07`, "Gate 5 is |column torque|, not angular velocity") **and failed to propagate.** It is now recorded in a single node of record with correction banners at all five stale sites.

---

## Files changed

- `analysis-2020accord/eps_lkas_chain_model.py` — Section 3B (assist, explicit), Section 6B (aggregator), corrected `arb_setpoint_limit` block, corrected `gp-0x4f60` identity, `EpsState` assist fields, orchestration rewired.
- **New memories:** `reference_accord_setpoint_limit_15360_lerp.md`, `reference_accord_gp4f60_is_sensor_b_column_torque.md`, `reference_accord_base_assist_lane_architecture.md`, `reference_accord_assist_curve_family_sport_mode.md`, `reference_accord_ecu_id_variant_table.md`.
- **Correction banners:** `memory/MEMORY_CONSTELLATION.md` (Era 18), `memory/project_accord_torque_mod_v0.md`, `memory/reference_accord_corridor_lockstep.md` (the CONTESTED identity is now RESOLVED — neither prior candidate was right), `memory/reference_accord_corridor_vs_envelope.md`, `analysis-2020accord/.claude/agent-memory/firmware-codepath-tracer/reference_accord_segmentD_fun3d04c_full_gate_map.md`.
- `memory/MEMORY.md` — 5 new index entries.

---

## Method note — the failure mode of this session

Four errors were made and caught (two by subagents, two by the lead):

1. Guessed `STEER_MAX = 3840`; Accord uses 4096.
2. Claimed the table was patchable by existing tooling without checking the CRC block map.
3. Read 8 entries of a 34-entry array and mis-identified this car's assist curve.
4. Read the ID-table keys at record `+0x22` instead of `+0x00`, producing garbled labels.

**All four are data-extent errors, not code-path errors.** Instruction-level tracing was rigorous throughout; table *extents* were assumed. **Standing lesson: locate an array's end before drawing conclusions from its contents, and never assume a power-of-two entry count.** This pairs with the existing lesson that byte scans beat `search_instructions` for exhaustive constant enumeration.

---

## Next concrete actions

1. **If pursuing the setpoint raise:** add `(0xE4000, 0xE4FFC)` to `TOUCHED_BLOCKS`, patch the 9 halfwords at `0xE41BC..0xE41CC`, and quantify the transient lockstep margin first.
2. **[OPEN]** live UDS read of `gp-0x6408..640C` would close the "we are slot 2 / `TVAA1`" assumption. Both current conclusions survive a mis-ID among Accord keys, so this is low urgency.
3. **[OPEN]** dump `0xCA324`, `0xCA4F4`, `0xC7A58`, `0xCA23C` to finish the assist model's four unity-modelled scaling terms.
4. **[OPEN]** re-derive the soft-EME bound's IIR arm on the torque (not velocity) interpretation of `gp-0x4f60` — `reference_accord_corridor_lockstep.md`'s physical reading may shift.
