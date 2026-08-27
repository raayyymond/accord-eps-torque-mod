# HANDOFF 2026-07-26 — Route 13: the vibration needs openpilot, FOURFRAME is invisible by design

**Route:** `75604b0a432fdc89_00000013--f484e75b00--{12,13,14,15}--rlog.zst` (4 segments, 224.1 s,
entirely 0–2.7 m/s — a deliberate parking-lot reproduction of the felt vibration).
**Firmware on-car:** FOURFRAME (V38 torque calibration + a passive read-only CAN-telemetry cave; no
torque-path change). **Nothing was built or flashed this session. No CAN was sent.**

**Operator-reported result carried in:** *V52C did not fix the vibration; it clearly changed manual
driving feel.*

---

## 1. The headline: the 21 Hz resonance exists only while openpilot is commanding

Matched test on raw CAN 399 `STEER_TORQUE_SENSOR` — **hands-OFF, moving (`vEgo > 0.3 m/s`), identical
window length and speed gate**, split on `carControl.latActive`:

| Nfft | condition | usable | K | peak | P(21 Hz) | P(3 Hz) | 21/3 |
|---|---|---|---|---|---|---|---|
| 1.28 s | **OP steering** | 23.3 s | 25 | **21.09 Hz** | 7.03e7 | 7.84e5 | 89.7 |
| 1.28 s | **OP off** | 16.8 s | 18 | 2.34 Hz | **7.62e3** | 4.62e6 | 0.002 |
| 2.56 s | OP steering | 14.4 s | 6 | 21.09 Hz | 1.26e8 | 2.20e6 | 57.4 |
| 2.56 s | OP off | 9.6 s | 5 | 2.34 Hz | 2.36e4 | 7.77e6 | 0.003 |

**9,200× less 21 Hz power with LKAS disengaged.** The disengaged pool is *not* a quiet condition — it
carries **6× more** low-frequency energy (3 Hz: 4.62e6 vs 7.84e5), which is what rules out an
excitation-level artifact.

⇒ **This is a closed-loop LKAS instability, not the "command-independent base-assist limit cycle"** the
CLAUDE.md current-state describes. It does match the operator's long-standing report that the vibration
is gone with OP disengaged. (The V48B parked full-authority slam with no LKAS command is a **different**
phenomenon — do not merge the two.)

**Confidence:** K=25 vs 18 windows at 1.28 s is thin, and this is one route. The effect size is ~4
orders of magnitude, far beyond what that noise manufactures. The command/response coherence at 21 Hz
is **not** resolved to the b9 standard here — hands-off dwell is chopped into 0.6–6 s fragments by the
low-speed lockout cycling.

### Three method traps, each of which produced a wrong answer this session

1. **Never analyse mixed hands-on/hands-off data.** A naive `latActive`-only window peaks at
   **7.42 Hz** (Q≈12) and buries the 21 Hz mode at −5.9 dB. That 7.42 Hz figure was briefly reported as
   "the vibration" and is **RETRACTED**. Splitting on `steeringPressed`: hands-OFF → 21.09 Hz dominant
   by 20×; hands-ON → broadband 2.34 Hz, Q≈0.8.
2. **The obvious objection to that split is testable and FALSE.** `steeringPressed` derives from the
   same CAN-399 torque channel, so it *looks* circular. It isn't: driver torque averages **2166
   hands-on vs 328 hands-off**, a clean 6.6× discriminator.
3. **Check the disengaged comparator is not a PARKED car.** The raw `latOFF & handsOFF` cell has
   **median vEgo 0.00 m/s, 70 % of frames < 0.3 m/s**. Gate on `vEgo > 0.3` — that leaves 20.3 s
   (longest runs 5.46 s and 4.15 s), which is enough. A subagent reported this cell as "0.0 s, the
   route structurally cannot test this"; that was wrong.

### Speed dependence, refined across three datasets

Route 13 + archived `b9` + archived manual `aa5b3e0c01` (all effectively V38):

| bucket | route13 | manual archive | b9 archive |
|---|---|---|---|
| <1.5 m/s | **21.09 Hz** Q=10.2 (K=9) | — | — |
| 1.5–3 m/s | **21.09 Hz** Q=14.9 (K=16) | 21.09 Hz Q=9.0 (K=8) | 20.3 Hz (K=3, thin) |
| 3–8 m/s | — | 21.68 Hz (K=3, thin) | **21.09 Hz** Q=15.0 (K=7) |
| 8–15 m/s | — | **21.48 Hz** Q=11.0 (K=88) | **21.88 Hz** Q=11.1 (K=38) |
| >15 m/s | — | 12.50 Hz Q=7.1 (K=88) | 11.52 Hz Q=1.9 (K=68) |

⇒ **20–22 Hz continuously from <1.5 m/s through ~15 m/s**; only above 15 m/s does it become a broad,
low-Q 11–12.5 Hz shelf. CLAUDE.md's "~21.7 Hz at 3–8 m/s worst regime" is **refined — 3–8 m/s is not
special.**

## 2. Why V52C did not fix it

Its EMA (α = 74/1024 at the 1 kHz task) gives **−6.1 dB at 20.9 Hz** — so it *was* a fair test of the
`gp-0x4f60` lane, and the null is **real evidence against that lane carrying the resonance**.

One confound: it also adds **−60° of phase at 21 Hz**, which in an anti-damping loop can partly offset
the magnitude cut. So this weakens, but does not formally kill, the `gp-0x4f60` hypothesis.

The **felt manual-feel change** is best explained by the EMA's integer deadband: with round-to-nearest,
increments round to zero for `|raw − filtered| < 1024/(2·74) ≈ 7 counts` — a stiction nonlinearity
sitting directly in the assist path, at low frequency where the filter is otherwise transparent.

## 3. FOURFRAME is absent from the rlog — and that was predictable

**Verified directly (lead, not relayed): 1,111,018 CAN frames across buses 0/1/2/128/129/130/193;
zero frames of `0x6A0`–`0x6A3` or `0x555`.** Positive controls healthy: bus 1 carries `0x18F` (22,409),
`0x14A` (22,408), `0x1AB` (11,204).

Dispatch tables read with **pure Python** out of `_vfourframe_plain_image.bin` (routing `0xB7208`,
ID `0xB721C`, cadence `0xB7C9C`) — no Ghidra needed:

| slot | mbx | ID | cadence | at comma |
|---|---|---|---|---|
| 7 | 6 | 0x1AB | 2 | 50 Hz ✔ |
| **8** | **6** | **0x19F** | **1** | **ABSENT** |
| 9 | 6 | 0x18F | 1 | 100 Hz ✔ |
| 10 | 6 | 0x14A | 1 | 100 Hz ✔ |

**Slot 8 is configured identically to slot 9** — same mailbox, same cadence, both static-payload +
callback — yet never appears. Of the 11 broadcast slots, **only 3 reach the comma**; eight
(`0x720`–`0x723`, `0x660`, `0x64D`, `0x32E`, `0x19F`) do not. The gateway per-ID whitelist is now
evidenced on **8 controls instead of 1**.

⇒ **FOURFRAME's silence says nothing about whether the cave fired.** The comma rlog cannot answer that.

### ★ CORRECTION OF RECORD — the base tick is 100 Hz, not 62.5 Hz

`cadence × measured wire rate` agrees three ways (slots 7/9/10) on **100 Hz**, and CAN 399 is
independently fitted at **exactly 100.000 Hz** (period 10.0000 ms/segment). This strikes the
"62.5 Hz base tick" in `reference-accord-can-tx-architecture-new-id` and every per-slot rate derived
from it. FOURFRAME transmits at **100 Hz**, not 62.5 (bus load ≈43 kbps, not 27).

### ⚠ The planned red-panda confirmation may not discriminate

`docs/guides/RED-PANDA-EPS-SETUP.md` routes the red panda **through the comma Bosch harness** — the *same* tap
as the comma's built-in panda. If that is the only tap available, it sees the same filtered set and
cannot separate "gateway dropped it" from "cave never fired". **Confirm a tap upstream of the gateway
exists before wiring anything up.** `tools/sniff_fourframe.py` (new this session; listen-only,
`SAFETY_SILENT`, decodes all 16 signals plus positive controls) is ready if one is found.

### Better comma-visible telemetry channel

Per-byte entropy over all of route 13:

- **`0x18F` byte5 = constant `0x00` in 100 % of 22,409 frames** — a fully free byte at 100 Hz
- **`0x14A` byte4 = constant `0x07` in 100 % of 22,408 frames** — a fully free byte at 100 Hz
- **`0x1AB` is a poor carrier**: DLC only **3**; the s16 at bytes 0–1 is a live saturated signal
  (min −32768, max −32315, 100 % nonzero) — not the "near-zero unused" frame previously assumed

⇒ combining `0x18F` byte5 + `0x14A` byte4 carries a **full 16-bit signal at 100 Hz** on frames proven to
cross the gateway, using the spare-bit piggyback class that has flashed successfully four times
(V31P/V49P/V50P/V51P) — far lower risk than FOURFRAME's new-mailbox programming. **Verify both bytes are
constant on other routes before building on this.**

## 4. Incidental confirmations

- rlog fingerprint: `ecu=eps addr=0x18DA30F1 fw='39990-TVA,A160'` — the comma proves a **modified**
  image is running, but every build in this kit shares that string, so **an rlog cannot identify which
  build is flashed**.
- `minSteerSpeed = 0.0`, `steerAtStandstill = False` — openpilot is not the low-speed obstacle,
  as the `0xC62EA` workstream concluded.
- `STEER_STATUS` distribution is only {0 normal, 3 low-speed-lockout}; **status 3 covers 31–86 % of
  frames** on this route, and openpilot commands into a dead lockout for 3.2–14.3 % of frames. No
  status 4 or 7 anywhere. 399 counter shows zero dropped frames; Honda checksum 100 % clean.

## 5. Recommended next step

**Run an openpilot-side experiment first — it carries zero brick risk.** The mode requires OP to be
commanding, so a notch or steeper rolloff around 21 Hz on its lateral output (or a lateral gain
reduction) is a free test of the closed-loop hypothesis, repeatable in the same parking lot. Given that
three code caves have bricked this ECU (V24/V27/V48B) and the last two firmware candidates were nulls,
this should be exhausted before another `.rwd` is built.

If firmware telemetry is still wanted afterwards, build the `0x18F`-byte5 + `0x14A`-byte4 piggyback
rather than relying on FOURFRAME reaching the comma.

**Open / unresolved:**
- Whether the FOURFRAME cave actually fires — **not answerable from a comma rlog**; needs an upstream
  tap or a whitelisted-ID channel.
- Whether `0x19F` is genuinely transmitted or runtime-gated. The dispatch tables show no gate, but the
  callback `FUN_00055F2E` was not read — **GhidraMCP had no running instance this session**. Open
  Ghidra on `analysis-2020accord/ghidra_project/accord2020_ghidra.gpr` with the GhidraMCP plugin to
  finish it.
- 21 Hz command/response coherence, to the b9 standard, on a route with longer hands-off dwell.

## Scripts (scratchpad, not tracked)

`lead_verify.py` (CAN-ID absence), `lead_buses.py` (per-bus inventory), `lead_fft.py` (independent
FFT), `lead_txtables.py` (dispatch tables), `lead_1ab.py` (payload entropy), `lead_fw.py` (fingerprint),
`lead_adjudicate2.py` (4-way condition split), `lead_confound.py` (parked-car check),
`lead_matched.py` (**the matched test above**).
