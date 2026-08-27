# TRACE 2026-08-10 — the driver-torque tracking reference (`gp-0x6ad6`) vs the LKAS command

Task: adjudicate the operator's hypothesis ("the steering-feel model doesn't know about LKAS demand")
at the level of `gp-0x6ad6`, the reference `FUN_0003a382`'s PID tracks the driver against — as opposed
to the plant/observer model `FUN_0003b8f6` a prior session already closed (§1e of
`docs/handoffs/2026-08/HANDOFF-2026-08-10-v89-flew-and-the-mechanism-is-friction.md`).

Program: `code.bin` (stock), GhidraMCP only, decompile-first. `gp=0xFEDF8000`, `tp=0xBF000`.

## Q1/Q2 — full enumeration of `gp-0x6ad6`'s inputs, `FUN_00037fe6` (0x37fe6)

Decompiled in full this session. Structure:
```
iVar4 = 0
if |gp-0x6b4a| <= 0x6400 (25600): iVar4 = -gp-0x6b4a        # UNCONDITIONAL, negated, no cal weight
if gp-0x67ab != 1:                                           # gates the other 7 terms as a block
    iVar4 += Σ gated(term_i, window_i) * cal_weight_i
gp-0x6ad6 = clamp(iVar4 * speedLERP(gp-0x69aa)/1024, ±25600)  # speedLERP flat 1024 (prior session, unchanged)
```

| term | signal | gate window | cal weight | producer | LKAS-derived? |
|---|---|---|---|---|---|
| 0 (unconditional) | `gp-0x6b4a` | ±25600 | none (implicit ×1, negated) | `FUN_00026c80` (LKAS mixer) | **YES — direct** |
| 1 | `gp-0x6bc2` | ±10240 | `0xC64AE`=1 | `FUN_00036f30` | not traced this session |
| 2 | `gp-0x6b60` | ±15360 | `0xC64B2`=1 | orphaned block @0x36352, mode `gp+0x6440/41==2` only | driver-override/peak-hold envelope, not LKAS |
| 3 | `gp-0x6b2a` | ±10240 | `0xC64B3`=1 | `FUN_0003b49a` | driver-torque/speed LERP, not LKAS |
| 4 | `gp-0x6bce` | ±10240 | `0xC64AD`=1 | **DEAD, 0 writers** (2-method confirmed, prior session) | n/a |
| 5 | `gp-0x6b6e` | ±10240 | `0xC64B1`=1 | `FUN_0003b338` | angle-rate integrator, not LKAS |
| 6 | `gp-0x6bbc` | ±10240 | `0xC64AF`=1 | **DEAD, 0 writers** | n/a |
| 7 | `gp-0x6b70` | ±10240 gate / own clamp ±8192 | `0xC64B0`=1 | `FUN_00038148` (plant-model observer residual) | **YES — indirect** (§1e's `gp-0x6b4e≡gp-0x6afe` unity path) |

Cal weights `0xC64AD..0xC64B3` re-read fresh this session: `01 01 01 01 01 01 01` — confirms prior sessions.

## MAJOR FINDING: a second, direct, unconditional LKAS term into `gp-0x6ad6`

`gp-0x6b4a`'s producer, `FUN_00026c80` (0x26c80), decompiled in full this session. It is the SAME
11-lane mixer that produces `gp-0x6b4c`, which `analysis-2020accord/model/eps_lkas_chain_model.py:2318-2344`
already documents as `[VERIFIED]`: arb_command → limit_and_pack → distribute_clamp → this mixer, "~11
LKAS-internal distribute sources" summed into `gp-0x6b4c`, "the LKAS lane into the aggregator."

Decompile shows both cells descend from the SAME internal aggregate `iVar13`:
```
iVar13 = <split-sum of gp-0x6298[] across 11 lanes> + <rate/slew term> + <gp-0x6a62-indexed LERP term>
gp-0x6b4a = clamp(iVar13, ±0x6400)                                                       @0x277be
gp-0x6b4c = clamp(gp-0x3d88_component + polarity(gp-0x6752)*((iVar13*cal(0xC63CC))>>10), ±0x2800)  @0x27722
```
`gp-0x6b4a` is the wider, pre-combine sibling of the LKAS lane, NOT rescaled from a driver-torque
signal. I independently confirmed lane 9 (the driver-torque-CORDIC lane, `gp-0x6b6c`, per
`reference_accord_fun2eda8_lane9_raw_torque_command_path.md`) does not reach `iVar13`/`iVar14` — its
struct fields that would route there are zeroed at the source (`FUN_000339cc`), consistent with that
memory's finding "lane 9 does NOT feed gp-0x6b4a/gp-0x6b4c."

**⇒ `gp-0x6ad6` has TWO LKAS-command-descended terms, not one:**
1. Term 0, `gp-0x6b4a` — direct, unconditional, ±25600 window (== the cell's own final clamp).
2. Term 7, `gp-0x6b70` — indirect, via the plant-model observer, gated behind `gp-0x67ab != 1`, capped
   at ±8192 by its own upstream clamp (`0xC6200`, re-confirmed this session = 0x2000).

**Authority (clamp-ceiling comparison, EVIDENCE):** term 0's gate window equals the CELL's own clamp —
`gp-0x6b4a` alone can drive `gp-0x6ad6` to its full rail. Term 7 is capped at 8192/25600 = 32% of that
range. **Whether `gp-0x6b4a` actually approaches its ceiling in real driving is UNMEASURED** — no
telemetry exists on it in this kit's record.

`gp-0x67ab`'s trigger (whether the 7-term block, including term 7, runs at all) has exactly ONE writer,
inside the SAME `FUN_00026c80` mixer (`0x2775c st.b r6,-0x67ab,gp`), fed by a per-lane OR-reduction over
mode bytes I did not fully resolve this session (an inherited open item across multiple prior memories,
re-confirmed still open). **Flag: if `gp-0x67ab==1` in normal operation, term 7 (`gp-0x6b70`, friction/
observer) drops out ENTIRELY and `gp-0x6ad6` reduces to `-gp-0x6b4a` alone — the direct LKAS term would
be the WHOLE story.** Not resolved; next step below.

## Sign direction of term 0 (new this session, not in any prior memory)

Downstream of `gp-0x6ad6` both terms share the identical machinery (`FUN_0003a382`, decompiled in full
this session, disassembly cross-checked): `bias=clamp(gp-0x6ad6,±8192)`, `err=clamp(gp-0x4f60-bias,
±0x2800)`, P/I/D combine (all-positive gains, see below), `out=combine*authorityLERP(gp-0x671a,≥0)/1024
*polarity(gp-0x6752)`, ADDED (never subtracted) into the aggregator — this ADD-not-subtract fact is
independently confirmed in `reference_accord_fun3a382_pid_structure_aggregator_addsign_and_freqresponse.md`.

`gp-0x6752` ("assist polarity") is **boot-initialized to +1** and static thereafter (per
`reference_accord_fun3a382_pid_structure_aggregator_addsign_and_freqresponse.md` and
`reference_accord_arb_input_cluster.md`: writers are `FUN_000490ac`/`FUN_000497e6`, init/watchdog only,
~50 read-only consumers elsewhere) — not a per-direction sign flip. With that pinned:

```python
def gp_6ad6_term0(gp_6b4a):                       # 0x37fea/0x37ffa, this session's decompile
    return -gp_6b4a if abs(gp_6b4a) <= 25600 else 0

# increasing gp_6b4a (more LKAS-descended command)
#   -> term0 more negative -> gp_6ad6 (bias) more negative (other terms held)
#   -> err = gp_4f60 - bias INCREASES (subtracting a more-negative bias)
#   -> P,I,D all positive-coefficient (Kp/Ki/Kd read this session, see below) -> combine INCREASES
#   -> out = combine * authorityLERP(>=0)/1024 * (+1) INCREASES
#   -> gp-0x6ad4 ADDED into the aggregator -> gp-0x6b94 INCREASES, same direction
```
**⇒ term 0 is structurally REINFORCING, not cancelling: as the direct LKAS-descended quantity
`gp-0x6b4a` rises, this reference-tracking side-channel adds MORE torque in the same direction as
LKAS's own direct contribution (`gp-0x6b4c`), on top of it.** This is the SAME qualitative shape as the
already-established friction/K1 mechanism (`docs/STATE.md` §6b: "more modelled friction ⇒ more assist").

Labelled EVIDENCE: the P/I/D-positive-gain fact, the ADD-not-subtract aggregator fact, and `gp-0x6752`'s
boot-static +1 are each independently sourced/re-confirmed. BELIEF: that `gp-0x6b4a`'s raw sign
convention is the same as `gp-0x6b4c`'s / the aggregator's overall convention — a reasonable structural
inference (they are literally the same pre/post-combine pair) but not independently pinned by a
polarity test this session.

## Q3 — quantified, see authority paragraph above. `gp-0x6b70`'s own ceiling: ±8192 (`0xC6200`, re-read
this session: bytes `00 20` = 0x2000 = 8192, confirms all prior records). `gp-0x6ad6`'s own final
clamp: ±25600 (`0x6400` in the `FUN_00037fe6` decompile, byte-identical to term 0's gate).

## Q4 — `gp-0x4f60`'s producer and filtering (flagged UNSWEPT in `docs/STATE.md`: "raw CAN → gp-0x4f60
producer... unswept" — swept this session)

Writers (5 sites, `search_instructions` mnemonic=st.h operand=4f60, `truncated:false`,
183,570 instructions scanned): `FUN_0007ec34` (1, zero-write, a fault/reset path) and `FUN_0007f3f8`
(4 sites: 2 zero-writes on fault paths, 1 direct passthrough, 1 the "valid" compensated write).
`get_xrefs_to` on the absolute address returned a FALSE "no references" — the misleading-zero trap this
kit's skill warns about; `search_instructions` (operand-text) is what found the real writers.

`FUN_0007f3f8` (caller: `FUN_0006bb08`) decompiled in full. It is a **dual-channel plausibility/
cross-check state machine**: reads two redundant candidate channels indexed by a channel byte
(`gp-0x27fa`), computes a candidate value via `FUN_0006af38`/`FUN_0007f300`, plausibility-gates it
against `gp-0x4f60`'s OWN prior value (`|candidate - gp-0x4f60| vs threshold gp-0x4f56`), and on
failure escalates DTC-maturing counters (`FUN_0005bb04`/`FUN_0005ae6a`/`FUN_0005b650` — the kit's
established DTC-maturing call pattern) rather than storing. On the VALID path, a cal-gated correction
runs (`tp+0x74c3` = `0xC63C3`, byte-read this session = **4, i.e. ENABLED on stock**):
```
iVar8 = clamp(gp-0x6b50 + ((iVar8 * gp-0x698c) >> 10), ±gp-0x4f54)
gp-0x4f60 = iVar8
FUN_0007e74a()          # called AFTER the store — a consumer/dispatcher, not a filter on gp-0x4f60
```
**No EMA/IIR/z⁻¹ appears anywhere in this store path** — `iVar8` is built entirely from THIS cycle's
candidate, `gp-0x6b50` (an offset/bias per prior memory, "self-calibration term") and `gp-0x698c` (a
scale, "learned gain") — no reference to `gp-0x4f60`'s own history. **This CONFIRMS (with the actual
producer now traced, closing the "unswept" flag) `docs/STATE.md`'s existing claim that `gp-0x4f60` is
unfiltered** — refined: it is a single-sample compensated (scale+offset+clamp) measurement, not a raw
ADC passthrough, but has no LOW-PASS content. A reaction torque appearing physically in the sensor at
6-9 Hz would reach `gp-0x4f60` with NO firmware-side attenuation.

🛑 **IDENTITY CONFLICT FOUND, FLAGGED NOT RESOLVED:** `reference_accord_gp6af8_fight_trigger.md`
(2026-05-29, this kit's own memory) labels this SAME cell "SIGNED MOTOR/COLUMN ANGULAR VELOCITY," citing
the identical `FUN_0007f3f8`/`gp-0x6b50`/`gp-0x698c` writer chain I independently re-derived this
session. Every later, more-corroborated source (the golden model, `docs/STATE.md`, dozens of
`reference_accord_gp4f60_*` memories, and — decisively — the direct CAN399 `STEER_TORQUE_SENSOR` bridge
in `reference_accord_gp6a5e_sensorA_magnitude_no_can_bridge.md`: `CAN399.STEER_TORQUE_SENSOR =
-floor(gp-0x4f60*125/128)`, an externally-DBC-grounded TORQUE field) calls it **torque**. I did not
re-derive the DBC bridge myself this session (inherited), but its existence is strong evidence for
"torque" over "velocity" — a velocity signal driving a documented torque CAN field would be a much
larger anomaly than one old memory being wrong. **Working conclusion: torque (BELIEF, not re-verified
this session), flagging the conflict for whoever next touches `gp-0x4f60`'s identity.**

## Q5 — `FUN_0003a382`'s P/I/D gains, cal addresses, values (fresh `read_memory` this session)

All three gain LERPs are indexed on `gp-0x6ac0` (motor rate). Byte-read from stock `code.bin`:

| term | cal region | stock values | note |
|---|---|---|---|
| K_p | `0xC6B1E`(thr=0)/`0xC6B20,22`(X:300,2000)/`0xC6B24`(upper=4000)/`0xC6B26,28`(Y:256,256)/`0xC6B2C`(Y-hi=153) | **0.250** for motor_rate<4000, **0.1494** above | flat below 4000, one step down above |
| K_i | `0xC6B0A`(thr=0)/`0xC6B0C,0E`(X:400,1500)/`0xC6B10`(upper=3000)/`0xC6B12,14,16,18`(Y: all 98) | **0.0957** | FLAT — constant across every motor rate |
| K_d | `0xC6ADE`(thr=50)/`0xC6AE0,E2`(X:400,1500)/`0xC6AE4`(upper=3000)/`0xC6AE6,8,EA,EC`(Y: all 2048) | **2.000** | FLAT — constant across every motor rate |

(Values are Q10, `/1024`.) P-term's own IIR alpha = `tp+0x7450`=`0xC6450` = **1024/1024 = 1.0 (stock)**
— NO lag at stock (matches memory: V46 build moved it to 32, away from this stock unity). D-term's own
IIR alpha = `tp+0x744a`=`0xC644A` = **1024/1024 = 1.0 (stock)** — likewise no lag (V43 moved it to 64,
also away from stock unity). **⇒ at STOCK calibration, Honda's P and D branches are literally
UNFILTERED — this "PID" is a plain discrete PID at the 1 kHz control-task rate, no internal poles.**
Soft-start slew (`tp+0x744c`/`0xC644C`, `tp+0x744e`/`0xC644E`) = 32768/32768 (Q15 full-scale) — the
authority ramp is a single 1 kHz tick, i.e. effectively instantaneous at stock, not a real ramp.

**Loop-gain bound at 6-9 Hz (Python mirror, discrete-to-continuous approximation, T=1ms sample):**
```python
import math
T = 1e-3
for f in (6, 9):
    w = 2*math.pi*f
    Kp, Ki, Kd = 0.250, 0.0957, 2.000     # stock, motor_rate<4000
    p_gain = Kp
    i_gain = Ki/(w*T)                     # discrete accumulator ~ integrator
    d_gain = Kd*(w*T)                     # discrete backward-diff ~ derivative
    combined = (p_gain + i_gain + d_gain) / 32     # the >>5 in the decompile
    print(f, p_gain, round(i_gain,3), round(d_gain,3), round(combined,4))
# 6 Hz: P=0.250  I=2.538  D=0.075  combined ~= 0.0895
# 9 Hz: P=0.250  I=1.692  D=0.113  combined ~= 0.0642
```
This is BOUNDED, not exact: the final `* authorityLERP(gp-0x671a)/1024` factor was not resolved to a
specific value this session (a related-but-DIFFERENT ceiling LERP, `0xC6AF0`/`0xC6AFC`/`0xC6AFE`, is
on record as selecting unity 100% of normal operation per V54's on-car measurement — NOT the same cell,
so this is suggestive, not proof, that `gp-0x671a`'s LERP is also ≈unity in practice). **Treating it as
≈1 (unverified), loop gain error→`gp-0x6ad4` at 6-9 Hz ≈ 0.064-0.090** (dimensionless, same units as
`gp-0x6ad6`/`gp-0x4f60` counts). The I-term dominates in this band (integrator gain rising as 1/f) —
this is the FIRST time this kit has written down this loop's gain at the ratchet frequency.

## Q6 — adversarial re-check of the inherited §1e claims

- `FUN_0003b8f6`'s first instruction: **`0003b8f6: ld.h -0x6b98[gp],r7`** — re-disassembled fresh this
  session. CONFIRMS the inherited claim exactly (loads the delivered motor command).
- `tp+0x73a8` = `0xC63A8`: re-read fresh this session via `read_memory(0xC63A0,16)` covering the whole
  `FUN_00038148` SUM_6ch weight block. Byte layout: `0xC63A0..AA` = `1024,1024,1024,1024,1024,1024`,
  `0xC63AC`=**102** (the EMA alpha, matches multiple prior sessions exactly), `0xC63AE`=1024. **`0xC63A8`
  (the `gp-0x6b4e` weight, 5th of the six) = 1024 — CONFIRMS the inherited claim exactly**, both the
  address resolution and the value.

## Open questions / next steps

1. `gp-0x67ab`'s exact trigger (1 writer found, `0x2775c` in `FUN_00026c80`, condition not fully
   resolved) — **the single most consequential unknown in this trace**: if it's usually 1, term 7
   (`gp-0x6b70`) never fires and term 0 (`gp-0x6b4a`, direct LKAS) is the ENTIRE reference-model story.
   Next: full decompile of the per-lane reduction loop at `0x274xx-0x2775c` in `FUN_00026c80`, or a
   live UDS/telemetry read of `gp-0x67ab` during an engaged drive.
2. `gp-0x6b4a`'s typical magnitude in real driving — unmeasured; needed to know whether it actually
   approaches its ±25600 ceiling or sits at a small fraction of it in practice.
3. The `gp-0x4f60` identity conflict (torque vs. velocity) — not re-resolved from first principles this
   session; the CAN399 bridge is inherited evidence, not independently re-derived here.
4. `gp-0x671a`'s exact authority-scale LERP table — not fully resolved (address arithmetic attempted,
   not confidently closed); needed to turn the Q5 bound into an exact number.
5. Terms 1/3/5 (`gp-0x6bc2`/`gp-0x6b2a`/`gp-0x6b6e`) — producers identified by address/memory but not
   independently re-traced this session; none of the three look LKAS-derived on the existing record.
