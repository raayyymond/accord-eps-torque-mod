# Accord EME Override-SM — NON-VERIFIED claims (2026-05-29)

Companion to the **verified** record in `memory/reference_accord_override_snap_state_machines.md`.
Everything below is **inference / interpretation / not-yet-pinned** — do **not** act on it as fact, and
do not flash anything derived from it without closing the gaps. Re-read `CLAUDE.md`, the verified memory,
and `analysis-2020accord/TORQUE_PATH_GUIDE.md` before using this.

Confidence tags: **[STRONG]** well-supported inference · **[OPEN]** genuinely unresolved · **[ASSUMPTION]** designer-intent guess.

---

## 0. RESOLVED 2026-05-30 — Trace A + V19 build (4-agent swarm + operator-directed re-verification)

The following open items below are now closed/upgraded. Details verified by direct decompile/disasm reads of `FUN_00042af8` L615–1196 (instruction-level), corroborated by 4 `firmware-codepath-tracer` agents:

- **§4 minimum-edit set — RESOLVED.** All three SMs arm off the **command-magnitude path**, NOT column velocity: the integrator `gp-0x3570` slews toward `uVar25 × 0x8000` where `uVar25` = the LKAS command (`gp-0x6acc`), then `uVar53 = |∫>>15|` and `uVar34 = uVar53·1092/1024`. (One swarm agent claimed a column-velocity seed at L219 — that is the `gp-0x6af8` writer, a **misread**; corrected by reading L663–720.) This is *why* the EME is 2×-only.
  - **SM1 "scale puzzle" — RESOLVED.** The `uVar19 < |uVar25|` arming compare uses `uVar19 = cal[tp+0x71de] = 0xC61DE = 2048` (loaded at decompile L756), **not** the Q15 node (`0x8000`). The node reassignment `uVar19 = *gp-0x6960` happens only *after*, inside the action branches. SM1 magnitude arm = `|cmd| > 2048` AND velocity > `tp+0x71e0`(7168) AND command opposes `gp-0x6af8`.
  - **SM3 arming — RESOLVED.** SM3 cuts when the integrator **saturates** (`uVar53 ≥ uVar39 = cal[tp+0x71dc] = 0xC61DC = 30720`) for `tp+0x7298`(20) cycles. `tp+0x71dc` is *simultaneously* the integrator clamp ceiling and SM3's trip. `30720 = 2 × 15360` (stock full authority) — a designed-at-2× guard.
  - **Complete arming threshold set (cal-addressable):** SM1 `tp+0x71de`=2048 · SM2 `tp+0x7422`=16384 · SM3 `tp+0x71dc`=30720.
  - **High-end-2× minimum edit = two halfwords, proportional rescale:** `0xC6422` 16384→32768 (SM2) + `0xC61DC` 30720→61440 (SM3+integrator clamp; arithmetic-safe, `0xF000×0x8000=0x78000000 < INT32_MAX`). **SM1 left stock** (velocity+opposition-gated; its 2048 floor is already crossed at 1×, so it is not the 2×-only culprit). Built as **V19** (`build_v19_tva.py`; 49/49 CRC, ECU-decode==patched, 17-byte diff), UNFLASHED.
- **§1 `gp-0x4f60`/`gp-0x6af8` identity — UPGRADED to [STRONG]: column/motor ANGULAR VELOCITY** (Q10; the recurring `0x6400`=25600=25×1024 clamp and the `<25.0` float gate after ×(1/1024) are the evidence). So the SMs are **anti-oscillation / fight-on-motion** monitors. (Residual [OPEN]: the ultimate source of `gp-0x6b50` is a register-indirect/HW write not resolved statically.)
- **§5 recovery timing — cals mapped.** Shaper stack args (single caller `w_steer_control_task` @0x2214a): `sp+0x38` recovery/rise step ← LERP table `tp+0x7a28`(=6); `sp+0x36` fall step ← `tp+0x7a18`(=197); counter ceilings `tp+0x74fe`/`0x74ff`(=5), `tp+0x729a`/`0x729c`(=200); dwell `tp+0x7298`(=20). (The 29491-cycles→~10 s mapping still depends on the shaper task period, still unconfirmed.)

**Still genuinely [OPEN] (do not over-claim):**
- **Command full-scale ambiguity.** A mode gate at L651 caps `uVar25` to ±0x2000/0x3000 in modes 0/2; the "~15360 full-scale" reading (which makes the SM3 edit *necessary* at 2×) relies on the active LKAS mode bypassing it. Active mode `FUN_000074c4[tp+4]` UNVERIFIED. If full-scale is ~8192, only `0xC6422` is needed and the `0xC61DC` edit is harmless-but-inert.
- **Which SM fires in the real EME is NOT discriminated on-car** (§3 stands). CAN `0x427` capture remains the discriminator — and would also pin the scale above.

---

## 1. Identity of `gp-0x4f60` / `gp-0x6af8` (the fight reference) — [OPEN → see §0: UPGRADED to STRONG = angular velocity]

- The **writer chain is verified** (`gp-0x6af8` @`0x42c3a` = gated `gp-0x4f60`). The **semantic identity is not.**
- Agent A (traced the writer `FUN_0007f3f8` from raw `gp-0x6b50`, slew-limited; consumer `FUN_00043e44` floats it and compares to **25.0** rpm/deg-s): **signed steering-column angular velocity.** [STRONG but single-agent]
- Agents B and C *assumed* it was a torque/demand magnitude without tracing the writer. [weaker]
- **Why it matters:** if it's velocity, the "fight" = LKAS opposing the direction the wheel is physically *moving* (anti-oscillation / fights-your-hands-in-motion). If it's torque, it's a different relationship. This changes how a setpoint-gain build will *feel* and which safety purpose dominates.
- **To close:** disassemble `FUN_0007f3f8` fully and confirm `gp-0x6b50`'s source register/units; confirm the `25.0` comparison's units.

## 2. The SM's safety PURPOSE — [ASSUMPTION]

Structure is consistent with several purposes; none is proven:
- anti-oscillation / control-stability damping (opposing-motion + sustained signature),
- actuator authority / runaway limiting (50%-of-Q15 magnitude gate),
- driver-override authority handoff,
- it also **broadcasts the trip to another core** (CSIG `0x2a`) — so part of its role may be *informing* a higher arbiter, not just the local cut.
The `0x4000` = exactly-50%-of-`0x8000` structure **suggests** a threshold *relative to the authority envelope* (which would make a proportional rescale defensible) — but that is an inference about designer intent, not evidence.

## 3. The EME = these SMs firing — [STRONG, not discriminated]

The SMs are *a* verified cut path with the right (sustained, 2×-only, opposing-motion) signature. **Not** proven to be the *sole* actor in the operator's actual event. Still-live alternates: assist-mode dropout (`gp-0x4e65` 3→1), governor dip (`gp-0x4f64`→0 at low speed), or the **other core acting on the CSIG `0x2a` report**. Only a CAN `0x427` motor-torque + steering capture through one real event discriminates.

## 4. The minimum edit for high-end 2× — [OPEN, do NOT build yet]

- Lead candidate: **`tp+0x7422` (`0xC6422`) `0x4000` → `0x8000`** — rescales SM2's arming to the 2× envelope. [STRONG that it addresses SM2]
- **Incomplete:** the three SMs are OR-linked (3-way min), so SM1 *and* SM3 must also not trip.
  - SM1 magnitude arming is `|cmd| > current node`; the node is normally `0x8000`=32768 while the shaped command is clamped ≤ 8192 → **scale puzzle, unresolved** [OPEN] (either the command at that stage is on a wider scale, or `uVar19`/the node isn't what Agent A labeled).
  - SM3 (`gp-0x355f`) arming is `r21` vs `r24` — **entirely untraced** [OPEN].
- So a complete, confident minimum-edit *set* is **not yet known**. It could be one byte or several.
- **Safety judgment:** raising `0xC6422` is a **real loosening** — it lets a 2× LKAS oppose the steering motion to the same *proportional* degree the stock system tolerated at 1×, but **double the absolute torque**. Acceptable only if the threshold is truly authority-relative (see §2) and the operator accepts the trade. Off-limits by default per the project's "don't defeat a safety monitor" rule.

## 5. Recovery timing — [OPEN]

The ~10 s ratchet is believed to come from slew step **`sp+0x38`** (caller stack value) and/or the dwell timeout `tp+0x7424`=29491 *cycles* × (shaper task period). **Task period unknown** from static analysis → the 29491→~10 s mapping is unconfirmed. `sp+0x9/0xc/0x2c/0x34/0x36/0x38` are not yet mapped to cal addresses (need the shaper-caller trace).

## 6. CSIG `0x2a` recipient behavior — [OPEN]

We know the trip is broadcast every cycle. We do **not** know what the receiving core does with it (independent torque inhibit? logging only?). Relevant because suppressing the local cut may not suppress a downstream reaction.

## 7. Setpoint-gain build avoids the EME — [STRONG, not road-confirmed]

Mechanism predicts it (demand self-caps < 16384 at full command, so no SM arms). But V12A (the `shl3` setpoint lever) was **never road-tested in the EME maneuver**, so EME-absence is not empirically established — only mechanistically expected.


---

## RESOLVED 2026-05-30 (drive-data + corrected-address re-trace) — see analysis-2020accord/SESSION-2026-05-30-EME-RESOLUTION.md
Many §-items above are now closed; do not re-open without reading
`SESSION-2026-05-30-EME-RESOLUTION.md`:
- §0 "command full-scale ambiguity / which SM fires": logged EME = **SM2/SM3 wind-up**
  (accumulator of command-excess-over-envelope). SM1 ruled out (stationary column at cut).
- Integrator is ACCUMULATOR not tracker → SM2/SM3 reachable, V19 LIVE.
- Shaper = **1000 Hz** (dwell cals SM2 0xC64FF=5, SM3 0xC6298=20 → dwell is a weak lever).
- SM3 cut value cal 0xC6420=0 confirmed; SM3 arm max=0xFFFF; SM2 wrap at uVar53~61454.
- Envelope LIVE (polarity gp-0x6752=±1); LERP tables 0xC6748/0xC6754 plateau ±1024 — DECLINED
  as a lever (high-v tail unresolved).
- Off-shaper instant cuts (observer-edge, fault-bit-8, gp-0x67f4, gp-0x67a4) all ruled out for
  the hands-off 2× short-turn case. **gp-0x4e65 mislocated** — not on the LKAS torque path.
- Builds V20A/V20B produced (UNFLASHED).
