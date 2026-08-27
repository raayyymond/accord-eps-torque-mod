# ARCHIVE — CLAUDE.md as it stood on 2026-07-27, before the index restructure

**This is a verbatim snapshot.** On 2026-07-27 the operator directed that `CLAUDE.md` be restructured to
act as an **index and a statement of key behaviours**, with progressive disclosure, rather than carrying
full rich history inline. It had reached 704 lines, and the cost was demonstrated the same day: two
separate agents re-proposed an already-flashed, already-falsified lever (`0xC6450` = V46) because the
on-car result was buried in prose.

Nothing here is deleted — it is preserved for provenance. The load-bearing content was redistributed to:
- `docs/STATE.md` — the living current state
- `docs/BUILD-LINEAGE.md` — the per-address lever index and flashed/falsified table
- `docs/HANDOFF-*.md` — the per-session narrative record
- `memory/` — durable facts of record

⚠ **Prefer those files.** This archive reflects what was believed on 2026-07-27 and contains statements
that the 2026-07-27 session itself disproved (notably: that FOURFRAME's silence was a gateway effect,
that `0xC646C` is an LKAS-only authority gain, and that the vibration is absent from the openpilot
command).

---

# 2020 Honda Accord EPS Firmware Analysis Kit — Agent Context

You're working inside a reverse-engineering kit for the 2020 Honda Accord's EPS firmware (`39990-TVA-A160`, Renesas V850E2). This file is your boot context.

## What this kit IS

A reference and analysis environment, not an active flashing target. The operator may at some point ask you to help build a new `.rwd`, port a hypothesis from one firmware to another, or verify a disassembly claim. They may also just be reading and asking questions. Default to study/analysis mode unless told otherwise.

> **CURRENT STATE (2026-07-26 — ROUTE 13. ★ SUPERSEDES every "the vibration is a command-independent
> base-assist limit cycle" statement below, and corrects the CAN-TX base tick. Read
> `docs/handoffs/2026-07/HANDOFF-2026-07-26-route13-vibration-engagement-dependence.md` first.):**
> **★★ THE 21 Hz VIBRATION EXISTS ONLY WHILE OPENPILOT IS COMMANDING.** V52C was FLASHED → did NOT fix
> the vibration, but CLEARLY changed manual driving feel. FOURFRAME was FLASHED and driven (route 13,
> `75604b0a432fdc89_00000013--f484e75b00`, 224 s, all 0-2.7 m/s parking lot).
> **NOTHING BUILT, NOTHING FLASHED THIS SESSION. NO CAN SENT.**
> - **Matched test** (hands-OFF, moving `vEgo>0.3`, same Nfft + speed gate, `carControl.latActive`
>   on vs off): OP steering → peak **21.09 Hz**, P(21 Hz)=**7.03e7** (K=25); OP off → peak 2.34 Hz,
>   P(21 Hz)=**7.62e3** (K=18). **9,200× less 21 Hz power disengaged** — and the disengaged pool carries
>   **6× MORE** low-frequency energy, so it is NOT an excitation-level artifact. ⇒ **CLOSED-LOOP LKAS
>   INSTABILITY, not the always-on base-assist limit cycle.** (V48B's parked no-LKAS slam is a
>   DIFFERENT phenomenon — do not merge.) Matches the operator's long-standing "gone with OP disengaged".
> - **⇒ RECOMMENDED NEXT STEP IS OPENPILOT-SIDE AND CARRIES ZERO BRICK RISK:** notch / roll off OP's
>   lateral output at 21 Hz (or cut lateral gain) and redrive the same lot. Three caves have bricked this
>   ECU and the last two firmware candidates were nulls — exhaust this before another `.rwd`.
> - **⚠ THREE METHOD TRAPS, each of which produced a wrong answer this session.** (1) **Never mix
>   hands-on/hands-off** — a naive `latActive`-only window peaks at a spurious **7.42 Hz** (Q≈12) and
>   buries the real mode at −5.9 dB; that 7.42 Hz reading is **RETRACTED**. (2) The "`steeringPressed` is
>   circular (same torque channel)" objection is **testable and FALSE** — driver torque averages **2166
>   hands-on vs 328 hands-off**. (3) The raw `latOFF & handsOFF` cell is a **PARKED car** (median vEgo
>   **0.00 m/s**, 70% of frames <0.3) — gate on `vEgo>0.3`, which leaves a usable 20.3 s.
> - **Speed dependence REFINED across 3 datasets** (route 13 + archived `b9` + manual `aa5b3e0c01`, all
>   effectively V38): **20-22 Hz continuously from <1.5 m/s through ~15 m/s** (best-sampled 8-15 m/s,
>   K=88/38); only **>15 m/s** becomes a broad low-Q **11-12.5 Hz shelf** (Q 1.9-7.1). ⇒ the
>   "~21.7 Hz at 3-8 m/s worst regime" note below is **refined — 3-8 m/s is NOT special.**
> - **V52C's null is MEANINGFUL:** its EMA gives **−6.1 dB at 20.9 Hz**, so it WAS a fair test of the
>   `gp-0x4f60` lane ⇒ real evidence **against** that lane carrying the resonance. Confound: it also adds
>   **−60° phase** there, which in an anti-damping loop can partly offset the cut. The **manual-feel
>   change** is best explained by the EMA's integer deadband — increments round to zero for
>   `|raw−filtered| < 1024/(2·74) ≈ 7 counts`, a stiction nonlinearity in the assist path.
> - **FOURFRAME's `0x6A0-0x6A3` are ABSENT from the rlog — verified directly (1,111,018 frames, zero
>   hits, positive controls healthy) — AND THAT WAS PREDICTABLE.** Dispatch tables (pure Python, no
>   Ghidra) show **slot 8 (`0x19F`) is configured IDENTICALLY to slot 9 (`0x18F`)** — same mailbox 6,
>   same cadence 1, both static+callback — yet never appears. **Only 3 of 11 broadcast slots reach the
>   comma**; eight (`0x720-0x723`, `0x660`, `0x64D`, `0x32E`, `0x19F`) do not. Gateway whitelist now
>   evidenced on **8 controls, not 1** ⇒ **FOURFRAME's silence says NOTHING about whether the cave fired.**
> - **★ CORRECTION OF RECORD — THE CAN-TX BASE TICK IS 100 Hz, NOT 62.5 Hz.** `cadence × measured wire
>   rate` agrees three ways (slots 7/9/10) and CAN 399 is fitted at **exactly 100.000 Hz** (period
>   10.0000 ms). Strikes the 62.5 Hz figure in `reference-accord-can-tx-architecture-new-id` and every
>   rate derived from it; FOURFRAME transmits at **100 Hz** (~43 kbps, not 27).
> - **⚠ THE PLANNED RED-PANDA CONFIRMATION MAY NOT DISCRIMINATE** — `docs/guides/RED-PANDA-EPS-SETUP.md` routes
>   the red panda **through the same comma Bosch harness** as the built-in panda, so it would see the
>   same filtered set. Confirm a tap UPSTREAM of the gateway exists first. `tools/sniff_fourframe.py`
>   (new, listen-only `SAFETY_SILENT`, decodes all 16 signals + controls) is ready if one is found.
> - **★ BETTER COMMA-VISIBLE CHANNEL:** `0x18F` **byte5 is constant `0x00`** in 100% of 22,409 frames and
>   `0x14A` **byte4 is constant `0x07`** in 100% of 22,408 → together a **free 16-bit signal at 100 Hz**
>   on gateway-crossing frames, via the spare-bit piggyback class that flashed successfully 4×
>   (V31P/V49P/V50P/V51P). **`0x1AB` is a POOR carrier** — DLC only **3**, and its bytes 0-1 are a live
>   saturated signal (min −32768, max −32315, 100% nonzero), not the "unused near-zero" frame on record.
> - An rlog **CANNOT identify which build is flashed** — fingerprint reads `eps fw='39990-TVA,A160'`, and
>   every modified build in this kit shares that string. Confirmed incidentally: `minSteerSpeed = 0.0`,
>   `steerAtStandstill = False`; `STEER_STATUS` ∈ {0,3} only, **status 3 covers 31-86% of this route**.
> - **OPEN:** whether the FOURFRAME cave actually fires (not answerable from a comma rlog); whether
>   `0x19F` is runtime-gated (callback `FUN_00055F2E` unread — **GhidraMCP had no running instance**;
>   open `analysis-2020accord/ghidra_project/accord2020_ghidra.gpr` with the plugin to finish);
>   21 Hz command/response coherence to the b9 standard on a route with longer hands-off dwell.
> See [[reference-accord-vibration-requires-lkas-engaged]] +
> [[reference-accord-can-tx-100hz-base-tick-and-gateway-evidence]].
>
> **CURRENT STATE (2026-07-25 — LOW-SPEED STEER. A separate workstream from the vibration/V52C thread
> below; nothing here changes V52C's status. Read
> `docs/handoffs/2026-07/HANDOFF-2026-07-24-low-speed-steer-lockout.md` first.):**
> **★ THE LOW-SPEED STEER LOCKOUT IS LOCATED AND IT IS A CAL-ONLY EDIT. NOTHING BUILT, NOTHING FLASHED.**
> - **The lever: `0xC62EA` (`tp+0x72EA`) = 320 ≈ 4.995 km/h (3.104 mph)**, the LO half of a two-sided
>   window whose HI is `0xC62E8` = 12800 ≈ 199.8 km/h. **One reader each** (`0x28EBC`/`0x28EB6`, `ld.hu`),
>   **no float mirror**, in the `0xC6000` block every cal-only build already touches. Suggested value
>   **64 (1 km/h)**, not 0. Speed unit ≈ **64.0625 counts/km/h** (`×41>>6` from a 0.01 km/h CAN raw).
> - **Mechanism, verified instruction-by-instruction:** window vs voted speed `gp-0x6a5e` @`0x290C8`/
>   `0x290D2` → fails → `mov 3,r6` / `st.b -0x6807[gp]` = `STEER_STATUS=3` → the **intra-function**
>   `cmp 0x2` @`0x29382` sends it to `jr 0x29734` (disengage) instead of the engage block, so
>   `gp-0x6806` (**= `STEER_CONTROL_ACTIVE`**, packer `shl 3`) is zeroed and the authority ramp
>   `gp-0x69b0` is killed. **Deliberate:** the `gp-0x68b3` bypass fires only at *exactly* 0 speed, so
>   0 km/h passes but 1-319 counts cannot.
> - **Proven on-car, three independent decoders, ~305k CAN-399 frames:** with OP commanding,
>   `STEER_CONTROL_ACTIVE` is 0 in 100% of frames <2 mph, 88% set at 3-4 mph, ≥99% >4 mph, and **zero
>   frames anywhere** have it set alongside `STEER_STATUS=3`. Response per unit commanded torque is
>   suppressed ~10-70× in that band. Scripts: `analysis-2020accord/studies/gates/speed_status_engagement.py` +
>   `studies/gates/speed_efficacy_test.py`.
> - **openpilot is NOT the obstacle** — `CP.minSteerSpeed = 0.0` (the `3 mph` at `values.py:163` is
>   **`HondaCarDocs` website metadata**, not `CarParams`). Only OP floor = hardcoded `0.3` m/s in
>   `controlsd.py:178`, bypassable via `CP.steerAtStandstill` (Honda sets it nowhere). Panda safety has
>   no speed term. ⇒ `memory/reference/firmware/reference_accord_sub3mph_lkas_openpilot_gate.md` is **FALSIFIED on its
>   central claim** (struck in place).
> - **The second 320-count gate `0xC62EE` is NOT a lockout** — a permissive inside a **CAN-commanded**
>   assist-shutdown task; triggers `gp-0x6877`/`gp-0x6879` come from **CAN `0x17C` byte 5 bits 7/5**.
>   **Leave it stock and NEVER RAISE it.**
> - ⚠ **`FUN_00045608` is an AUTHORITY-SLOT SETTER, not "motor off"** (3 parallel 7-slot arrays →
>   governor running MIN → Q15 scale on the total command). `(3,0,0x8000,0x8000)` = slot-3 target 0 with
>   instant slew: effect right, label wrong. **The governor's slot loop covers slots 0-5, not 0-3.**
> - ⚠ **The G1 governor DOES read vehicle speed** (`gp-0x6a64` vs cal `0xC6316`=640 ≈10 km/h, below which
>   the slew limiter is BYPASSED) ⇒ **"no vehicle-speed input anywhere in the command path" is FALSIFIED.**
> - ⚠ **FLAGGED, NOT ADOPTED:** two traces conclude `gp-0x6a5e`/`0x6a62`/`0x6a64` are **voted VEHICLE
>   SPEED**, not voted torque. If true it reclassifies the V44/V47 damper ("Factor C zero *hands-off*"
>   becomes "zero *below 35 km/h*") and the gentle-EME gate `0xC6312`=320 (= 5 km/h, not torque 320).
>   **Annotated in the golden model but deliberately NOT folded in — it needs its own verification pass.**
> - ⚠ **SEVEN scan traps recorded**, each of which produced a confident wrong answer this session — most
>   importantly **Format-V `jr`/`jarl` aliases `ld.bu`** (same opcode field; only `hw2` bit 0 separates
>   them → **44% false positives**), and **filtering `reg2==0` drops every store-of-zero**. See
>   [[accord-v850-scan-traps-formatv-and-storezero]] before trusting any byte-scan count.
> - **Open:** whether the governor MIN chain can drop below unity at low speed (the fallback suspect if
>   the cal edit under-delivers — `gp-0x69aa==0x8000` is a sibling conjunct, so an on-car ST=3 cannot
>   distinguish the two).
>
> **CURRENT STATE (2026-07-24 LATEST-3 — supersedes LATEST-2 below on the carrier count, the
> "self-filtering lane" classification, and the reader-enumeration method. Read
> `docs/handoffs/2026-07/HANDOFF-2026-07-24-v52c-complete-broad-lowpass.md` first.):**
> **★ V52C = the COMPLETE broad low-pass. BUILT + ALL PRE-FLASH GATES PASSED, UNFLASHED.**
> `_v52c_plain_image.bin` SHA `af01c8bd…`, 132 changed bytes in 24 runs, 50/50 CRC, x31 round-trip +
> RWD readback clean. `builds/v50_v79/build_v52c_tva.py` + `studies/caves/v52_cave_asm.py` + `verify/verify_v52c_image.py` +
> `studies/models/eps_v52c_gate2_broad.py`.
> - **ALL 19 command-path carriers of `gp-0x4f60` are repointed** to the filtered cell `gp-0x1300`
>   (V50 did 7, V52 did 10). **OPERATOR DIRECTIVE, and it is the correct principle:** a MIXED
>   raw/filtered population is ITSELF the hazard — any self-consistency / dual-path / lockstep check
>   straddling the split sees a divergence that does not exist today. **That is exactly how V27
>   bricked (ASYMMETRY, not magnitude).** It is also the most stable option measured.
> - **Only 5 command-path reads stay RAW, all vs LITERAL constants:** health gates `0x28F26`,
>   `0x42C20` (M1), `0x43EDA` (M2) + dormant mux arms `0x34392`, `0x34ACE`. Plus 2 diagnostic
>   (`0x2EC66/0x2ECBA`) and 3 dead (`0x2A992`, `0x2D9A2`, `0x2DAE6`). `verify/verify_v52c_image.py` enforces
>   this as a **machine-checked completeness invariant** — it FAILS if a future edit leaves an
>   unexplained raw read in `[0x28000,0x46000)`.
> - **GATE-1 closed FIVE ways** for `gp-0x1300`: V51P live probe (0/24000 frames), outside the
>   0xb7260 mailbox array, 0 LE32 pointer refs image-wide, 0 `movhi` materialising the 0xFEDF page,
>   and absent from the `0x89c34`/`0xbbc48` descriptor tables. **The method reproduces V50's and
>   V48B's failures as controls** (`gp-0x1500` is INSIDE the array AND has 2 pointer-table entries).
> - **GATE-2 CLOSED:** stability edge **4.66× (stock) → 21.19×**, `worst_re` 0.189, GM 14.48 dB;
>   monotonic in the filtered fraction over a 41-point sweep (no destructive blend); no unity-gain
>   crossing 0.3–150 Hz; ZOH/aliasing improves. A first-order EMA has **no resonant pole** — unlike
>   V48B's notch, whose own poles WERE the brick mechanism.
> - **No monitor asymmetry, no dual-path divergence.** 3 shadow pairs exist (`gp-0x6b86`/`0x6ba6`/
>   `0x6b9a`) but write both legs atomically from one value → **input-invariant**. Prior-sample cells
>   have 0 external readers and zero-init at boot; RAM clears on power-up and a flash requires a power
>   cycle, so **no stale state survives the flash** and `|filtered| ≤ |raw|` on cycle 1 → a key-on
>   transient can only SHRINK. (V48B's failure was a key-on slam; this is the inverse.)
> - **★ THE PRIOR HANDOFF'S "3 SELF-FILTERING LANES" WAS WRONG ON ALL THREE.** Measured vs V38:
>   `0x36682` really does self-filter (α=6/1024, **fc 0.94 Hz**); `0x36846` is **not a filter at all**
>   (a cal-selected output + a DTC-0x23 rate gate); `0x3B908` is **nearly a passthrough** (its float
>   biquad stage is DEGENERATE in stock cal, coeffs `0xC404C`/`0xC4050`=0.0f → live poles ~366 Hz).
> - **⚠ NEW SAFETY FACT — DTC `0x18` IS HARD-FAULT ELIGIBLE** (record `0xB7FDC`, `[+8]=0x3D01`, same
>   as monitors 0x1C/0x1D → motor-off). It is the **per-task cadence/overrun watchdog**, so any cave
>   on the 1 kHz path has a TIMING budget. V52C's cave = ~0.06% of the 1 ms tick (28 instrs, once per
>   tick, no loop/divide/call). **Any future cave adding a LOOP, DIVIDE or CALL must re-check this.**
>   (An agent called 0x18 benign off a 2-byte-slipped record address — see [[accord-dtc-0x18-hard-eligible-cadence-watchdog]].)
> - **⚠ ENUMERATION CORRECTED — "69 accesses, definitive" was WRONG.** True total **76** (71 loads +
>   5 stores) across BOTH encodings: 4-byte disp16 (64 ld.h + 5 st.h) AND the **6-byte V850E2
>   extended-displacement form** (6 ld.h + 1 ld.hu), which a disp16 byte scan cannot see. All 7
>   extended-form readers are diagnostic/CAN/self-test; **none is a carrier**, so the 19-partition is
>   complete. **Neither tool works alone:** byte scan misses encoding 2 and over-matches it **7.6×**
>   (`hw2=0xff61` is shared across ~13 nearby displacements); `search_instructions` misses anything
>   outside a function boundary (it returned 61 vs the true 64 — 4th recorded occurrence).
>   Register field is `(hw1>>11)&0x1F`. See [[accord-gp4f60-two-encodings-enumeration-trap]].
> - **⚠ PROCESS — the STALE GHIDRA IMPORT trap hit TWICE**, and the second form **defeats
>   hash-checking**: the on-disk SHA verified correctly while the OPEN Ghidra program held an earlier
>   revision and returned RAW bytes at edited sites. **Re-import fresh + spot-check one edited site
>   against a Python byte read before trusting any pre-flash re-disasm.** See
>   [[feedback-stale-ghidra-import-defeats-hash-check]].
> - **⚠ The off-by-0x1000 tp misread recurred (3rd time).** An agent read `0xC50D8` for `tp+0x50d8`;
>   `tp=0xBF000` so the correct address is `0xC40D8`. Anchor tp against a KNOWN value
>   (`tp+0x746c=0xC646C=3564`) before trusting any tp-relative cal.
> - 🛑 **V52C IS STILL UNFLASHED.** A code cave is this kit's only bricking class (V24/V27/V48B).
>   Flash ONLY on explicit operator instruction naming the file and the bus.
>
> **CURRENT STATE (2026-07-24 LATEST-2 — supersedes the LATEST block below on V51P / V52 / cell status.
> Read this first; then [[reference-accord-v51p-gate1-both-cells-clean]] +
> [[reference-accord-gp4f60-carrier-surface]].):**
> **V51P was FLASHED + DRIVEN (rlog 7, `75604b0a432fdc89_00000007--0a8e7099b8`) → BOTH candidate cells
> gp-0x1300 AND gp-0x1100 are GATE-1 CLEAN** — 0/24000 CAN-330 frames nonzero, beacon 100% live, two
> independent decoders (`studies/probes/decode_v51p_gate1.py` + lead verifier), stock null distinguishable. This is the
> definitive live-probe RAM clearance gp-0x1500 failed. **V52 = the V50 EMA low-pass rebuilt on gp-0x1300 +
> round-to-nearest (`(74·d+512)>>10`, kills V50's −7-count floor-bias ratchet) + repoints for the 3
> FUN_0002eda8 branches V50 missed — BUILT + internally verified (50/50 CRC, x31 round-trip, RWD readback),
> UNFLASHED** (`builds/v50_v79/build_v52_tva.py` + `studies/caves/v52_cave_asm.py`; 10 repoints; SHA `bf4bc5b4…`).
> **🛑 BUT V52-as-built is INCOMPLETE — NOT flash-ready.** A definitive raw byte-scan proved gp-0x4f60 has
> **64 raw readers**, and classifying them found **~19 command-path CARRIERS across BOTH the 1kHz control
> task AND the ~100Hz assist task** — V52 repoints only 10 (misses 9, incl. **3 that SELF-FILTER** →
> cascaded IIR/over-attenuation if repointed, and **2 mode-gated** with unconfirmed normal-drive liveness).
> **No monitor hazards** (M1 `FUN_00042af8`@0x42C20 / M2 `FUN_00043e44`@0x43EDA / gate 0x28F26 all compare
> raw vs LITERAL constants → the risk is feel/efficacy, not a brick). GATE-2 was closed for a 7-lane
> insertion and does NOT carry to 19 lanes + cascades. **⇒ This is the concrete empirical case for the
> diagnose-then-filter reframe: recommended next flash is FOURFRAME → FFT the carrier lane → filter it
> narrowly at a convergence point (gp-0x6ad6 / gp-0x6b70), NOT the 19-consumer gp-0x4f60 root.** A complete
> broad V52 (19 repoints) is buildable but needs register verification, self-filter cascade analysis,
> mode-gate liveness confirmation, and a full GATE-2 re-analysis. rlog `.zst` captures are now gitignored
> (kept LOCAL only). See [[reference-accord-gp4f60-carrier-surface]].
>
> **CURRENT STATE (2026-07-24 LATEST — supersedes the 2026-07-22 V50 block below on GATE-1 / flash status.
> Read this first.):**
> **🛑 V50 is NOT flash-ready — DO NOT FLASH.** The V50P probe (V38 + read-only telemetry) was FLASHED +
> DRIVEN (rlog 5, `75604b0a432fdc89_00000005--2ae04b9ba2`), decoded, and INDEPENDENTLY re-decoded by the
> lead: `gp-0x1500` reads 0 for ~1.15 s after ignition then goes dynamically NON-ZERO for the entire drive
> (99.47% of CAN-330 frames) → **`gp-0x1500` HAS A LIVE WRITER** → V50's EMA state cell would be stomped
> every cycle = the V48B RAM-collision brick mechanism. **GATE 1 FAILS on-car.**
> - **Root cause (corrects the 2026-07-22 "direct-clean / V48B-flash-proven / boot self-test" claim, now
>   FALSE):** `gp-0x1500` (0xFEDF6B00) is **slot 5 of a 40-slot × 8-byte I/O-mailbox array listed at
>   `0xb7260`** (slots 0xFEDF6AE0..0xFEDF6C18), written via a **table-dispatched pointer** (register-indirect
>   — the blind spot literal/absolute static scans cannot see, which is why every static method called it
>   clean). Slot 2 = the CAN-330 TX buffer (0xFEDF6AE8, the one our own probe hooks), slot 3 = CAN-660. The
>   old "poison region gp-0x1401..0x1502" is a SUBSET of this array; the V48B post-mortem's "vetted-safe alt
>   `gp-0x14E0`" is slot 9 of the SAME array → also unsafe. **Static literal clearance failed on 3 of 8
>   addresses checked (gp-0x1500, gp-0x14E0, gp-0x1700); gp-0x1500 passed BOTH static methods before the
>   probe caught it → in this firmware a live probe is the ONLY reliable RAM-ownership test.** See
>   [[reference-accord-b7260-io-mailbox-array]].
> - **Adversarial swarm (2026-07-24, 5 agents):** trampoline transparency @0x7FEAC = **PASS** (V24 class
>   cleared, verified vs the built image); carriers-asym = conditional-SAFE (no raw-vs-filtered monitor
>   asymmetry among the 7 lanes) BUT 2 active raw `gp-0x4f60` readers `FUN_0002ec52`/`FUN_0002eda8` are being
>   traced to close completeness; GATE-2 = STABLE, but the built 16-bit deadband is a **one-way ratchet**
>   (floor-shift asymmetry) → constant **−6.5..−7 count DC bias** + a local +15% gain bump in the 11-33 count
>   band → **the 2026-07-22 "deadband is a FEATURE" claim is corrected** (benign for stability, NOT strictly
>   benign; fix = round-to-nearest `(74·d+512)>>10`).
> - **Path for the cell (still valid):** `builds/v50_v79/build_v51probe_tva.py` = a V51P probe (BUILT/UNFLASHED) reading
>   candidates **B = gp-0x1300 (0xFEDF6D00)** and **D = gp-0x1100 (0xFEDF6F00)** — both in a ~400 B clean
>   corridor OUTSIDE the mailbox array — full-16-bit nonzero detect + a **liveness beacon** (CAN-330 byte4
>   bit7 = 1) so a clean read is distinguishable from a non-probe drive. Flash V51P, drive, decode: whichever
>   of B/D reads 0 all drive (beacon present) earns the rebuild. The V51P/V51 flashes are operator iron-rule.
>
> **★ CURRENT LEAD (2026-07-24, second half) — DIAGNOSE-THEN-FILTER via new-ID four-frame telemetry.** The
> operator reframed the fix: stop GUESSING which base-assist lane carries the ~21 Hz (every guess FALSIFIED —
> r24/V39, r26/V42, `FUN_0003a382` poles `0xC644A`/V43 + `0xC6450`/V46, damping/V44+V47). Instead **work
> BACKWARD from the motor FOC current setpoint and filter as LATE + as FEW signals as possible.**
> - ⚠ **FALSIFIED ≠ UNTESTED** (operator, this session): those cal-only lane cuts are validly dead, but the
>   **`gp-0x4f60` SIGNAL-FILTER is UNTESTED** — V48B bricked catastrophically *before* testing efficacy; V50
>   never flashed. Filtering `gp-0x4f60` late+narrow is the leading OPEN hypothesis (it's the torsion-bar
>   sensor carrying the mechanical resonance). See [[reference-accord-vibration-levers-falsified-vs-untested]].
> - **Backward-chain map (`foc-backward-map`, golden-model cross-checked):** anchor = `gp-0x6b98` (delivered
>   cmd; the true FOC Iq_ref bridge into `FUN_00071272` is genuinely unlocated) ← `gp-0x6acc` ← `gp-0x6ace`
>   (governor) ← `gp-0x6b94` (aggregator `FUN_0003aa2c` = last point LKAS + base-assist are separable). Its
>   summands are the 21 Hz carrier candidates (enumerated in the handoff). ⚠ that agent MIS-RANKED `0xC6450`
>   as a "new lever" — it is V46-FALSIFIED (verified vs `build_v46/47`); trust its structural map, NOT its
>   filter ranking.
> - **★ NEW-ID CAN-TX CAPABILITY built** (the operator's friend's four-frame telemetry method, ported SH-2A
>   Clarity → V850 A160). Full TX architecture mapped + lead-verified
>   ([[reference-accord-can-tx-architecture-new-id]]): single FCN0, all broadcast IDs ride mailbox 6; the
>   comma-visible/absent split is a **DOWNSTREAM GATEWAY per-ID whitelist** (the absent IDs are actively fired
>   yet dropped) ⇒ a new ID is visible on a **RED PANDA on the EPS bus, not the comma rlog**. Free mailbox
>   pool 7-32. TWO builds, both BUILT + lead-verified off the built image, UNFLASHED:
>   - **`VCANTX-TEST-txgate`** (`builds/telemetry/build_vcantx_test_tva.py`) — single-frame mechanism test: mailbox 16, ID
>     0x555, fixed payload, gated on `gp-0x1712` bit0. The kit's FIRST active-CAN-TX cave.
>   - **`FOURFRAME`** (`builds/telemetry/build_vfourframe_tva.py`) — the telemetry: mailboxes 16-19, IDs `0x6a0-0x6a3`, **16
>     backward-chain signals** (4 frames × 4 big-endian s16), dual-gated (`gp-0x1712` bit0 + `DAT_ff48024c`
>     bit4). 774 B cave @0xC4B34 on V38, 438 B headroom, Ghidra-clean 180/180. IDs collision-clear on the
>     comma scans (red-panda listen = definitive). ⚠ 2 payload caveats: `gp-0x6ade` dead-cell,
>     `gp-0x67ac` proven-constant-0. Decode map in `docs/HANDOFF-2026-07-24-*`.
> - **Recommended next (on-car, operator's call):** red-panda flash-test of FOURFRAME (parked → listen for
>   0x6a0-0x6a3 collisions → flash → confirm 4 IDs @62.5 Hz + no bus disruption) → drive with the buzz →
>   **FFT the 16 signals → the lane with a 21 Hz peak is the carrier** → filter THAT lane late+narrow.
>   ⚠ These are the kit's FIRST active-TX caves (transmit on the steering bus) — doubly the operator's
>   iron-rule flash call.
>
> **CURRENT STATE (2026-07-22 — SUPERSEDED by the 2026-07-24 block above on GATE-1/flash status; retained for
> the V50 build detail. Read
> `docs/handoffs/2026-07/HANDOFF-2026-07-22-v50-lowpass-ema-cave.md` FIRST, then
> `memory/reference/builds/reference-accord-v50-lowpass-ema-cave.md` +
> `memory/reference/builds/reference-accord-v49-stagec-flip-collocated-damper.md`.):**
> **V50 = V38 + the state-4 ratchet fix + a first-order EMA LOW-PASS (fc≈12 Hz, α=74/1024) on the shared
> torsion-bar signal `gp-0x4f60` (code cave) — BUILT + VERIFIED, UNFLASHED.** It filters `gp-0x4f60` into one
> 16-bit cell (`gp-0x1500`) and repoints the 7 collocated carriers to the filtered copy; keeps 4×;
> polarity-independent. `builds/v50_v79/build_v50_tva.py` + `studies/caves/v50_cave_asm.py` + `studies/models/eps_v50_gate2_lowpass.py`.
> - **Why a low-pass, not V48B's notch:** fresh V38-behavior data (`studies/spectra/analyze_manual_vibration.py` +
>   `studies/telemetry/manual_speed_split.py`) shows the felt mode is **SPEED-DEPENDENT** — ~21.7 Hz at 3-8 m/s (worst regime,
>   matches b9) sliding to ~8-12 Hz at highway speed; the 21.5-vs-78.6 Hz aliasing is unresolved. A low-pass
>   covers the whole 8-22 Hz band and rolls off 78.6 Hz harder (−16 dB) than 21.4 (−6 dB); a notch is fragile.
> - **Why a cave at all:** the operator's **FOC-current-loop hypothesis is RULED OUT** as a tractable lever
>   (FOC core `FUN_00071272` reads `gp-0x6b98` only for sign; NO isolable Kp/Ki; model-based coeffs at
>   0xC50D0-0xC5D84 inside the risky 0xC5000 block; ~8 kHz loop = the ACTUATOR, not the source). Cal-only
>   outer-lane cuts are exhausted (V39-V48A all null → distributed anti-damping). Keep-4× ⇒ a cave.
> - **★★ BOTH MANDATORY GATES addressed.** GATE 2 (closed-loop) CLOSED — stable under both the pessimistic
>   (Q=13.6) and realistic broad-shelf (Q≈4.8) calibrations, edge 4.66×→~21×, no resonant pole; the 16-bit
>   deadband is a FEATURE (over-attenuates a limit cycle). GATE 1 (RAM) = `gp-0x1500` best-available:
>   direct-clean (2 methods), V48B-flash-proven, and the 0xbb640/0xb7260 tables that list it are a BOOT/
>   DIAGNOSTIC self-test framework (not a hot 100 Hz path); the walker is UNFINDABLE statically (3 methods,
>   twice-reproduced). **Residual (honest):** a register-indirect writer isn't PROVEN absent, but the risk is
>   far below V48B (rare diagnostic write + self-healing EMA vs V48B's continuous 1000 Hz monitor-byte alias).
> - **Pre-flash gates — GATE 1 DONE (2026-07-23), GATE 2 has a ready probe → V50 still NOT flash-ready
>   until the probe drive clears it:** (1) Ghidra re-disassembled the built `_v50_plain_image.bin` — the
>   82-byte cave, the transparent trampoline (abs-idiom intact + correct flags at 0x7feb0), all 7 repoints
>   (`ld.h -0x1500[gp]`), the 2 raw dormant reads, and the byte-stock 4x/clamp-trap ALL verified in-context;
>   (2) the live RAM watch is a **BUILT + verified read-only probe** `builds/v50_v79/build_v50probe_tva.py` (V49P-class:
>   reads `gp-0x1500` into CAN 330 spare bits on the current V38 firmware; the car has no arbitrary-RAM UDS
>   read). Flash the probe, drive, decode CAN 330 with `studies/probes/decode_v49p_polarity.py` — `gp-0x1500` staying 0
>   confirms the cell free → V50 flash-ready; non-zero → move the cell. CODE CAVE = the kit's only bricking
>   class; the probe flash + the V50 flash are both operator iron-rule calls.
> - **V49 / V49P (superseded lead, retained):** V49 (`builds/v18_v49/build_v49_tva.py`) = the ratchet + a collocated damper
>   via `FUN_0003a382` StageC sign-flip (`subr→sub` @0x3a836) + band-limit — BUILT, UNFLASHED, 🛑 GATED on
>   polarity `gp-0x6752`=+1 (brick if −1). V49P = a read-only polarity-telemetry probe. **The rlog the
>   operator provided was NOT a V49P drive** (330 spare bits read stock) → the polarity gate is still
>   unresolved. V50 is polarity-INDEPENDENT, so it does not need that read. The vibration is still present
>   and unfixed on-car (operator, this session).
> - **openpilot side changed (operator, this session), previously constant since V38:** now PID + feedforward
>   from the model + a low-pass on the CAN output. The manual drive ran op 2026.002.000; its bus command
>   carries ~2.5× less HF than the old b9 drive, YET the vibration persisted → independent confirmation the
>   fix must be firmware-side (an OP-command LP can't fix a base-assist-loop instability). Keep the OP config
>   fixed between the V50 baseline and test drives so the result is attributable.
>
> **CURRENT STATE (2026-07-21 — V48B FLASHED → CATASTROPHIC; kept as the code-cave brick record + the
> two-gates origin. Superseded by the V50 block above.):**
> **🛑 V48B (the 21.4 Hz notch code cave) was FLASHED → CATASTROPHIC.** On startup, **parked, NO LKAS
> command**, the wheel slammed full-authority side to side; operator shut it off in seconds and
> **recovered by reflashing a known-good image** (no hardware damage). This is the kit's **THIRD** code-cave
> brick (V24/V27/V48B). Root-caused (GhidraMCP), TWO confirmed defects, same gap — the cave was validated
> **in isolation** (byte/CRC/disassembly/open-loop DSP) and never against the two things that decide on-car
> safety:
> - **(1) RAM COLLISION (proximate trigger of the violence).** The biquad's `x2` state cell `gp-0x14FA`'s
>   **high byte `0xFEDF6B07` aliases a LIVE monitor/DTC status bitfield** (readers `FUN_00051fbc`@52052 /
>   `FUN_00053f32`@53fc8, `case 8`). `x2` is multiplied by `b2=3977/4096≈0.97` (near-unity) → any external
>   write to that status byte injects ~full-scale into the filter → clamps ±25600 in one sample → motor
>   slams; and the cave stomps that live byte 1000×/s. Aliasing CONFIRMED; the status-byte *writer* was not
>   located (register-indirect/6-byte-disp blind spots) so "writes at key-on" is plausible-not-proven, but
>   the aliasing alone condemns it. `gp-0x14FA` is in the **sparse-flag POISON region `gp-0x1401..0x1502`**;
>   vetted-safe alt = `gp-0x14E0`/`0xFEDF6B20`. Other 3 cells (`gp-0x1500/0x14FC/0x14F8`) clean.
> - **(2) LIGHTLY-DAMPED RESONATOR IN THE ALWAYS-ON BASE-ASSIST LOOP (never modeled).** The notch's own
>   poles are r=0.979 → ζ≈0.157, Q≈3.2 (a resonator). The 7 repointed lanes are the always-on base-assist
>   loop (`→gp-0x6b94→gp-0x6b98`), gated only on EPS state `gp-0x67fa`∈{4,5,8,10,11} — **NO LKAS gate, NO
>   speed gate** → fires parked/hands-off. Only `|N(21.4)|` (a single-frequency magnitude) was inserted into
>   the *LKAS* loop-gain model (which predicts the notch HELPS); the **base-assist loop's closed-loop
>   stability was never analyzed**. `studies/models/eps_loop_gain_model.py` Task 4(d)'s "base assist doesn't need 21 Hz /
>   off the critical path" is **FALSIFIED on-car** (annotated in the model).
> - **(3) EXONERATED:** clock rate — hook `0x7FEAC` runs undivided 1 kHz once/sample (`FUN_0002214a`→
>   `FUN_0006bb08`→`FUN_0007f3f8`), correctly clocked.
>
> **★★ PERMANENT GUARDRAIL — TWO MANDATORY GATES for ANY code cave / filter / dynamics change (apply without
> being asked; byte/CRC/disassembly/open-loop-DSP verification is necessary but NOT sufficient):**
> **GATE 1 — RAM OWNERSHIP:** every byte (FULL multi-byte footprint) proven free incl. **writers** and
> register-indirect / 6-byte-extended-disp accesses; `gp-0x1401..0x1502` is poison.
> **GATE 2 — CLOSED-LOOP STABILITY:** analyze magnitude+phase (Nyquist/margin) of **EVERY loop the touched
> signal is in** — especially the always-on base-assist loop — with the element inserted; never a
> single-frequency magnitude, never only the target loop's crossover. See
> [[feedback-cave-two-gates-ram-ownership-and-closed-loop]]. The notch idea is ON HOLD pending both gates.
>
> **CURRENT STATE (2026-07-21 — superseded by the block above; kept for the V47/V48A/V48B-build detail. Read
> `docs/research/VIBRATION-DOSSIER.md` for the vibration diagnosis, `docs/handoffs/2026-07/HANDOFF-2026-07-21-v48b-notch-build.md` for
> the (now-bricked) build.):**
> **V47 FLASHED → barely quieter at 5 mph, NO effect on the in-motion LKAS vibration.** A six-stream
> audit then re-diagnosed the vibration and QUANTIFIED it:
> - It is a **two-inertia torsional mode** (motor/rack vs wheel/column, torsion bar = the sensor);
>   **bare-plant Q≈1.7, but 4× gain drives the derivative feedbacks to ~0° ANTI-DAMPING → closed-loop
>   Q=13.6, |L(21Hz)|=0.875, 1.16 dB margin.** Onset ~3×; hard edge 4.57×. Model:
>   `analysis-2020accord/studies/models/eps_loop_gain_model.py`.
> - **★ COLLOCATION KEYSTONE — why every damper build failed:** the hand cures it by adding damping at
>   the wheel/column antinode (**collocated**); the firmware damper senses **motor-resolver rate**
>   (far side of the torsion bar, **non-collocated**) → cannot damp the wheel-side mode at any gain.
>   **STOP tuning the motor-rate damper (V44/V47 direction is dead).**
> - **Route B ("4× via setpoint, stock gain") is HYGIENE-ONLY, ΔL=0** (gain-invariance: delivered
>   command identical → carriers unchanged). The "type-8" carrier `gp-0x6b12` is a delivered-command
>   delta, NOT `0xC646C`-scaled.
> - **V48A** (`builds/v18_v49/build_v48a_tva.py`; ratchet + mute type-8 `0xC4120` + `FUN_0003a382` `uVar27`→256,
>   cal-only, keeps 4×, safety-GO, 50/50 CRC) **FLASHED → did NOT fix the vibration.** ⇒ the anti-damping
>   is **distributed**, not concentrated in those two carriers → points to the notch.
> - **V48B = the 21.4 Hz NOTCH — ⚠ WAS "the current candidate"; has since been FLASHED → CATASTROPHIC
>   (see the LATEST block above). The build detail below is retained as the record of WHAT bricked.**
>   `builds/v18_v49/build_v48b_tva.py` + `studies/caves/v48b_cave_asm.py` + `studies/models/eps_v48b_cave_model.py`. V38 + ratchet + a **138-byte,
>   41-instruction code cave @`0xC4B34`** running DF-I Q12 (`b0=4045 b1=-7949 b2=3977 a1=-7949 a2=3926`,
>   −7.9 dB, exactly unity at DC = 73/73) on a fresh `gp-0x4f60` read → filtered copy to new RAM
>   `gp-0x1500`; a 4-byte trampoline `jr @0x7FEAC` (displaces `cmp r0,r8`/`mov r8,r14`, re-exec'd **last**
>   so the `bge` at the return `0x7FEB0` sees correct flags); **7 live carrier repoints**
>   `gp-0x4f60`→`gp-0x1500` (`FUN_0002c478`@2c480, `FUN_000352b4`@354d2/@35aa4, `FUN_0003a382`@3a6ca/@3a7ca,
>   `FUN_0003b49a`@3b4a8, `FUN_0003b66a`@3b672). The 2 mode-gated DORMANT reads (`0x34392`/`0x34ace`) are
>   left raw (dormant fallback arm of a cal-gated mux — red-team confirmed correct). RAM: y1/out=`gp-0x1500`
>   (V31P flash-validated), x1/x2/y2=`gp-0x14FC/FA/F8`. **50/50 CRC** (single MAIN block) + RWD round-trip
>   + **every code edit re-disassembled in Ghidra from the built image**. 4× gain + DTC-0x1d clamp trap
>   byte-stock. **Adversarial review: all monitor-asymmetry (V27) items CLOSED SAFE** — type-8 lockstep
>   `FUN_00027b0a` matched; other repointed-lane consumers have 0 raw reads; damper/boost dormant reads =
>   cal-gated mux; DTC-0x1c/0x1d pair (`FUN_00042af8`/`FUN_00043e44`) = matched int/float lockstep on the
>   same already-notched `gp-0x6b4a` (±5-count tol) → shared-input perturbation can't erode agreement,
>   attenuating notch only shrinks the per-tick delta. Feasibility was CONDITIONAL GO as a **filtered COPY**
>   of `gp-0x4f60` (source-filtering NO-GO: shadow-lockstep fault 0x17 + 2 hard-shutdown monitors + CAN).
>   ⚠ **CODE CAVE = the kit's only bricked class (V24/V27); the ultimate check is first-minutes on-car
>   observation. FLASH ONLY on explicit operator instruction naming the file + bus** (see safety rule 2).
>   Read `docs/handoffs/2026-07/HANDOFF-2026-07-21-v48b-notch-build.md` +
>   `memory/reference/builds/reference-accord-v48b-notch-cave-build.md`.
>
> **CURRENT STATE (2026-07-21 — superseded by the block above; kept for the V46/V47 detail):**
> **V46 FLASHED (lever A = Stage A carrier low-pass `0xC6450` 1024→32) → vibration UNCHANGED → LEVER A
> FALSIFIED.** **`V47` = ratchet + DAMPERS-ONLY, BUILT + verified, UNFLASHED — the current candidate.**
> V47 opens BOTH damper deadzones: Factor C (`0xD27C6`→235/`0xD27DA`→234, V44's cells) AND Factor E
> (`0xD2802/04/06` & `0xD2816/18/1A` → 700/750/800, aggressive). **Read
> `docs/handoffs/2026-07/HANDOFF-2026-07-21-v46-v47-vibration.md` first.** Six-agent audit this session established:
> - The vibration is a **self-excited limit cycle** in the base-assist torque-sensor feedback loop
>   (command-independent, cured only by manually ROTATING the wheel, gone with OP disengaged). The
>   damper `FUN_00034350` is a **5-factor product** (not 4) with **TWO** hands-off deadzones — Factor C
>   (driver torque) AND Factor E (**motor rate** `gp-0x6ac0`, Y0=0 below 60 counts). **V44 failed because
>   it opened only C; Factor E re-zeroed the product.** V47 opens both. Damper output clamp is dynamic
>   ±512..1024 (not ±2048). See `memory/reference/firmware/reference-accord-damper-two-deadzones-factorC-factorE.md`.
> - **There is NO vehicle-speed input anywhere** in the command/base-assist path (all 9 lanes checked);
>   the only rate adaptation is on MOTOR rate, not road speed. **"5 mph" = openpilot `minEnableSpeed=3`
>   + plant physics, NOT a firmware gate.** `memory/reference/measurement/reference-accord-no-vehicle-speed-input-5mph-is-plant.md`.
> - **Plant = DUAL-PINION EPS** (motor off-axis on a 2nd rack pinion); **Sensor A/B = MAIN/SUB channels of
>   ONE torsion-bar sensor** (Honda DTC C1420); the 21.4 Hz Q≈13.6 mode is a rack-coupled driveline
>   resonance. `memory/reference/measurement/reference-accord-dualpinion-arch-one-torsion-sensor.md`.
> - **Governor G1 (`FUN_0004503c`) clamps the TOTAL command** (all lanes, not LKAS-only); the "energy
>   budget" is **NOT** a thermal integrator (structurally unreachable) — relabel "motor-rate-adaptive
>   total-command ceiling." Doesn't bind at resonance amplitude; not a lever.
>   `memory/reference/firmware/reference-accord-governor-g1-total-command-not-thermal.md`.
> - ⚠ **SAFETY:** the damping clamp bound (int `0xD209C/0xD20A8`) has a float mirror (`0xC6554/58/5C/60`)
>   guarded by a **NO-DEBOUNCE DTC-0x1d hard shutdown** — never edit the int clamp without a bit-exact
>   float edit. V47 leaves it stock. `memory/reference/firmware/reference-accord-damping-clamp-dtc1d-trap.md`.
> - Falsified vibration levers now: r24 (V39), r26 (V42), Stage-C pole (V43), hands-off damping floor
>   (V44), hands-off slew (V45), **Stage A carrier low-pass (V46)**. The ratchet fix (`0x454FE`) is
>   confirmed and carried through all of them.
>
> **CURRENT STATE (2026-07-20 — supersedes EVERY build narrative below, including the V39/V40/V41/V42 text):**
> V38 FLASHED, fault-free. V39/V40/V41 FLASHED and resolved (r24 falsified; V40 killed power steering at
> ignition = the `0xFFFF` slew write; V41 falsified the motor-rate cap). **V42 FLASHED — a SPLIT result:
> Change 1 (the state-4 ratchet byte) FIXED the hard-turn ratchet on-car (now a CONFIRMED root cause);
> Change 2 (zero r26) did nothing → r26 falsified.** **V43 FLASHED — its dirty-derivative pole (`0xC644A`
> 1024→32) fixed nothing → falsified.** **`V44` is BUILT + independently VERIFIED, UNFLASHED — the current
> candidate.** Read `docs/handoffs/2026-07/HANDOFF-2026-07-20-v44-handsoff-damping.md` first.
>
> **The two symptoms have DIFFERENT root causes:**
> - **Hard-turn ratchet = SOLVED.** The **state-4 governor substitution** in `FUN_0004503c` (while
>   `gp-0x67fa == 4` the command magnitude can only decrease, written back cumulatively). Fixed by **ONE
>   BYTE**: `0x454FE` `0x65BA→0x65B5` (`bne`→`br`). Confirmed on-car by the V42 drive. Carried through
>   V43/V44 unchanged; not under test.
> - **Vibration = a MEASURED, lightly-damped MECHANICAL RESONANCE.** Route b9 telemetry (raw CAN 399,
>   frame-counter time base): **21.4 Hz, Q≈13.6**, −3 dB width 1.58 Hz, coherence ~0.23 s. ⚠ The old
>   "sharp isolated 21.02 Hz *clock-locked line*" was an **FFT windowing artifact** (concatenated
>   discontiguous windows) — RETRACTED. Root cause **located and it is in the firmware**: the base-assist
>   viscous **damping** lane `gp-0x6bd0` (`FUN_00034350`) is a product of four Q10 factors, and the factor
>   keyed on voted driver torque `gp-0x6a5e` (LERP `@0xD27BC` mode 10 / `@0xD27D0` mode 11, this car) has
>   **`Y[0] = 0` at `X[0] = 2240`** → below 2240 counts of driver torque (i.e. **hands-off**) the whole
>   product is multiplied by zero. The firmware has **no notch filter anywhere** in the command path
>   (whole-image search — single-pole EMAs only). So hands-off the resonance rings undamped; hands-on
>   (measured driver torque 8.1% FS vs 0.59% hands-off, straddling the ~7%-FS gate by a decade) the damper
>   engages → vibration vanishes. **This reproduces the operator's report exactly.** ⚠ Zero damping was
>   equally true pre-V38 (which did not vibrate), so it is an **enabling condition**; V38's 4× authority is
>   what now excites the mode. V44 is a **mitigation**, not a root-cause repair. **V44 = V43 + revert the
>   falsified pole + raise `0xD27C6` 0→235 and `0xD27DA` 0→234** (each = that table's own `Y[1]`; both
>   modes because a failover can reselect mode 11). 12 bytes, dual-verified, cal-only.
>
> ★ **Read `gain_rescaling_invariance_analysis()` in the golden model — but note its SCOPE was corrected.**
> With the PID rescaled, every stage downstream of the gain replays stock's exact counts, so a symptom
> **inside stock's torque range and sourced from a purely-digital replay** cannot be caused there. It
> correctly killed V39/V41. ⚠ It does NOT cover the vibration: pure-LKAS turning is a **large** command
> (>417-count regime), and the resonance is a **physical** mode fed by the real torque sensor, not a
> digital dither near zero. The earlier "small dithering around zero" framing of the vibration is RETRACTED.
>
> `analysis-2020accord/model/eps_lkas_chain_model.py` is the live golden reference and must be updated
> throughout every relevant investigation.
>
> **★ CORRECTIONS OF RECORD (2026-07-20 — these overturn facts stated elsewhere in this file and the
> handoffs; trust these):**
> 1. **The control-task tick is CONFIRMED ~1000 Hz** — two independent routes: OSTM0 (`OSTM0CMP`=79999 /
>    ~80 MHz PCLK) and the `STEER_STATUS=4` dwell (cal `0xC64DF`=100 cycles measured at 100.00 ms on the
>    bus). This **retires the standing "task rate in Hz — unresolved" open item.** PCLK's absolute value is
>    still not pinnable from the image, but a 100 Hz control task is excluded (would need 7.95 MHz). ⚠ This
>    is the CONTROL task (`FUN_0002214a`: arbitration, aggregator, shaper, and the sign filter
>    `FUN_00041464`). The assist-shaping task `FUN_00022ca0` (boost, damping producer `FUN_00034350`) may
>    run slower (~100 Hz is architecturally normal); its rate is not statically determinable and is an
>    efficacy question only, not a safety one.
> 2. **`gp-0x6abe` is LIVE in normal driving**, pinned to `0x7fff` only when `|gp-0x4f50| > 13000` — which
>    is **structurally unreachable** because `gp-0x4f50`'s producer clamps to exactly ±13000. The golden
>    model's `FUN_00034350` docstring had this BACKWARDS (settled from Ghidra pcode `INT_LESS`, symmetric).
> 3. **The V43 handoff's "half-wave-rectified damper" (`ld.hu` of `gp-0x6ac0` @`0x345fa`) is WRONG** —
>    `gp-0x6ac0`'s producer applies `abs()` before the store, so `ld.hu` vs `ld.h` is a no-op. Reached by
>    two tracers independently. (The real half-cycle effect is on the sibling `gp-0x6ac2` clamp bound.)
> 4. **The damper is net-damping at 21 Hz** with the sign source confirmed at 1 kHz: exact
>    discrete-filter + zero-order-hold phase = −22° (cos +0.93); even if the producer runs at 100 Hz it is
>    −56° (cos +0.55, still dissipative). The continuous-RC phase approximation overestimates lag near
>    Nyquist — use the exact `H(z)` + ZOH term.
> 5. **`search_instructions` counts only ALREADY-ANALYZED instructions (~185,693), not the image**, and
>    reports `truncated:false` while doing it. It undercounted reader/writer sets three times this session
>    (missed a 6th `0xC646C` read at `0x2a904`; false "0 writers" on `gp-0x6b98`). **Use raw byte-pattern
>    scans in Python for any load-bearing count.** Several "zero consumers image-wide" claims elsewhere in
>    this file rest on that sweep and should be re-verified by byte scan before carrying a build.
> 6. **`disassemble_bytes` MUTATES the shared Ghidra DB** on undefined regions unless `dry_run:true` — an
>    agent accidentally defined ~100 bytes this session. Never `save_program` after exploratory disasm.

## Git workflow — work directly on `main`

**Standing operator instruction (2026-07-20): work directly on the `main` branch and push updates to
`main`.** Do not create per-task feature branches for this repo. Commit the analysis work (record
corrections, memories, docs, handoffs, build scripts, the golden model, tracked rlogs) and push to
`origin` (`main`). The firmware/CAN/flash safety rules below are unchanged — this only governs the git
branch, not what may be flashed. `.bin`/`.rwd` firmware artifacts are gitignored and live under
`../accord-firmware`; do not commit them.

**Standing operator instruction (2026-07-21) — what "close out the session" means.** When the operator
says to close out / wrap up the session, it is a three-part deliverable, every time: (1) **update all
project docs and collaterals** — CLAUDE.md current-state, the golden model `model/eps_lkas_chain_model.py`,
and any affected `memory/` files + `MEMORY.md` index; (2) **commit and push to `main`** (the analysis
work — build scripts, docs, memories, golden model, records; not the gitignored firmware artifacts);
and (3) **create a handoff document** in `docs/HANDOFF-<date>-<topic>.md`. Do all three without being
re-asked.

The latest in-flight state is `docs/handoffs/2026-07/HANDOFF-2026-07-14-v37-dtc0x49-fix.md`: **V36 was FLASHED and, mid-drive, threw a burst of dashboard warning lights + dropped LKAS (comma) while base steering stayed fine; root-caused and FIXED as V37 (BUILT, cal-only, UNFLASHED).** V36 disabling `STEER_STATUS=4` silently removed an in-code interlock (`gp-0x6758=0`, run by every STEER_STATUS=4 branch) that was the only thing keeping the SEPARATE **DTC-0x49 fail counter `gp-0x6758`** (saturates at `0xC64E0+0xC64E1`=100 cyc, gate `0xC64B8`=112, on the same `torque gp-0x682f` channel) from saturating → with STEER_STATUS=4 gone it free-runs under sustained `torque>112` → `FUN_00016de6(0x49)` + `STEER_STATUS=7` → dash lights + openpilot LKAS drop (`steerFaultPermanent`); base assist survives. **`V37` = V36 + `0xC64B8` 112→0xFF** so counter B can never increment (`analysis-2020accord/builds/v18_v49/build_v37_tva.py`; V37-vs-V36 = exactly `0xC64B8`+CRC; both FSM code ranges byte-identical to stock; 49/49 CRC; UNFLASHED). ⚠ **Two corrections to the V36 framing below:** `FUN_0002a30e` AND `FUN_0002a93a` are BOTH **DEAD** (0 callers/xrefs/ptrs) — the live debounce+arb logic is inlined in `m_steer_torque_arbitration` (called by `w_steer_control_task@0x2214a`), so "FUN_0002a30e = the status producer" below is the DEAD copy; and `0xC64B8` is **ALSO a LIVE torque-arb branch @0x29a78** (`torque>112 ? high-torque cutoff : full arb-curve interp`), a drivability side effect the operator **accepted** for V37. The prior V36 pointer + mechanism follows as background — **the gentle-EME root cause is RE-LOCATED, and V36 is BUILT + verified.** V31P-V2 was flashed and driven (route 7f); its 5 gate flags proved **non-discriminating** (steady ~10 Hz benign; nothing rises at the cut). A Ghidra re-trace (self-verified) found the gentle EME is produced by the **`STEER_STATUS` (`gp-0x6807`) debounce state machine `FUN_0002a30e`** (+ an inline twin in `m_steer_torque_arbitration`): it fires `STEER_STATUS=no_torque_alert_2` after **5 sustained cycles** (cal `0xC64E2`=5, counter `gp-0x6757`) of a multi-tier envelope over two signals — `torque gp-0x682f > 0xC64B4(112)` (rise) OR `angle-rate param_1 > 0xC61C0(1600)`, plus two combined torque∧rate tiers (`0xC64B7`/`0xC61C2`, `0xC64B6`/`0xC61C4`). **`V36` = V31 + raise all 7 of those cals to unsigned max (0xFF/0xFFFF) → the debounce can never fire.** Cal-only, 0 code edits (both FSM functions byte-identical, independently diffed), 49/49 CRC, UNFLASHED (`analysis-2020accord/builds/v18_v49/build_v36_tva.py`). ⚠ **This SUPERSEDES the decider-gate + DELIVER_CUT framing in the rest of this paragraph:** the decider `0xC6312`=320 torque-MAX gate fires ~10 Hz **benign** and is NOT the trigger (so V33's disable hit the wrong gate); and `gp-0x6809` / the V31P DELIVER_CUT bit is **DEAD CODE (0 writers)** — do NOT use it as a cut anchor. `STEER_STATUS=4` is itself a lagging report; the actual motor-zeroing instruction is still unlocated (V36 is a discriminating experiment). ⚠ Operator anchor: on route 7f the felt gentle EME is at **route 5:27** (trigger ~5:26), a **sharp slight wheel-straightening mid-turn**, NOT the `STEER_STATUS=4` at 5:31. The V31P telemetry background follows (`docs/handoffs/2026-07/HANDOFF-2026-07-13-v31p-gateflags-330-piggyback.md`): V31P/V31P-V2 = V31 cals + gentle-EME gate-firing telemetry piggybacked into CAN 330 (`0x14A`) spare bits (4 code-cave trampolines @`0xC4B34`, flag byte `gp-0x1500`, packed by `FUN_00055a98` into byte4[7:3]/byte7[7:6]) — live in the raw `can` rlog with **NO CAN TX, no UDS, no OBD mux**; the flags proved non-discriminating (above). Live UDS telemetry is **blocked on the comma 4** because OBD multiplexing and steering both want the single FDCAN2/bus-1 peripheral (399/427 vanish under mux — `tools/test_obd_mux_steering.py`; `docs/handoffs/2026-07/HANDOFF-2026-07-12-comma4-uds-live-telemetry-bus-analysis.md`). ⚠ `cs.steeringTorqueEps` is always 0 on Honda (openpilot never parses 427; `memory/honda-op-steeringtorqueeps-always-zero`) — anchor gentle cuts on raw CAN 399 `STEER_STATUS`. Gentle-EME firmware background: `docs/handoffs/2026-07/HANDOFF-2026-07-02-v33.md`: the operator directed DISABLING the **gentle EME** — a failure DISTINCT from the soft EME below (gentle EME = LKAS-only cut in the engage-SM decider `FUN_00040d58` when the sensor-A column-torque voter `gp-0x6a62 ≥ cal 0xC6312`, stock 320; root-caused in `docs/handoffs/2026-06/HANDOFF-2026-06-29-gentle-eme-v32.md` + `docs/handoffs/2026-06/HANDOFF-2026-06-30-sensorA-identity-gate-scale.md`). **V33 = V31 + raise `0xC6312` 320 → 65535 (u16 datatype max) → the torque disengage can never fire** (the gate is `ld.hu`/unsigned and `gp-0x6a62` is voter-clamped to 32000; the separate `gp-0x6a62==0xffff` invalid-sensor sentinel is kept). Cal-only, decider code byte-identical to stock, 49/49 CRC, UNFLASHED. ⚠ Tool note: all disassembly/decompilation goes through **GhidraMCP** (`mcp__ghidra__*`); Ghidra's V850 SLEIGH has its own decode traps — see `memory/reference/tooling/reference_rizin_ghidra_v850_quirks.md`. The **soft-EME** lineage (separate mechanism — SM2/SM3 cutting the *merged* command) is `docs/handoffs/2026-06/HANDOFF-2026-06-03-v31.md`: **V30** was FLASHED and drives well (no hard EME) **but threw a residual soft EME on ONE hard SUSTAINED hands-off turn** → **V31** is BUILT (cal-only, 49/49 CRC, byte-verified 0 code edits, UNFLASHED — study artifact). Root cause (walked `FUN_00042af8` on stock `code.bin` this session): the soft-EME integrator `gp-0x3570` winds up on `(command − bound)`, and the bound is the SAME gated **THREE-WAY MAX/MIN** as the monitor wall `gp-0x6af6` = `max(corridor[cal 0x774e], IIR[gp-0x3574 = column velocity], boost[cal 0x7760 = steering ANGULAR-RATE, ≤2048]) × polarity` (float twins `gp-0x6db0/db8` vs int walls cross-checked ±5 LSB). **Each arm is conditionally gated:** the **corridor is the DRIVER-OVERRIDE arm** — off when `|gp-0x6bf0 driver-assist| ≤ 9216` (cal `0xC6156`, hands-off) AND when authority `r13≠0`; **boost** is latched 0 by an SM (`gp-0x3562`) when authority > `0xC641E`=16384 sustained; **IIR** decays when the column is held. `r13 = gp-0x6966 = (|gp-0x3570>>15|×1092)>>10` = authority. On a hands-off held turn all three collapse → the 2× command (gp-0x6acc = governed_LKAS≤1024 + COMP≤2560) winds up → SM2/SM3 cut. **V30 widened the corridor — the one arm gated off in that exact regime.** **V31 = V30 + a matched flat BOOST FLOOR 4096** (int `0xC6768/6A/6C`, float `0xC65C4/C8/CC`=4.0, ÷1024, lockstep-clean — the float twin's max INCLUDES boost): boost is authority-gated so it's ON at authority≈0 → floors the bound to 4096 > 3584 → integrator can't wind up → self-stable fixpoint. Read it + `memory/reference/firmware/reference_accord_soft_eme_bound_arm_gating.md` + `memory/reference/firmware/reference_accord_corridor_lockstep.md` early in any session.

## Memory system — READ THESE EARLY

`memory/MEMORY.md` is the index of named facts and is auto-loaded by Claude Code's project-scoped memory mechanism (if installed via the installer with the symlink path) or available to read manually.

**Crucially, also read `memory/MEMORY_CONSTELLATION.md` early in any session.** The constellation is the relational layer — how the facts connect. The flat list of memories does not convey, for example, why the V36 debounce-SM root cause chains through the DTC-0x49 fail-counter interlock to the V37 fix, or how the soft-EME corridor/boost-floor gating model connects to the V30→V31 build lineage. That chain is load-bearing and lives in the constellation.

Memory naming convention:
- `reference_*` — firmware/protocol facts of record (disasm-verified or otherwise grounded)
- `feedback_*` — how the operator wants work done (style, validation depth, trust calibration)
- `project_*` — in-flight build state; can supersede itself as work progresses
- `dream_*` — exploratory or speculative threads, lower confidence

If you notice a memory is stale, ask before updating it. If you generate a new durable fact during a session, propose adding it as a memory file with the appropriate prefix.

## The priming skill stack

`.claude/skills/` contains skills that materially change how you approach this work. For any substantive session — building a new `.rwd`, analyzing a hypothesis, comparing firmware variants — recommend (or auto-load if instructed) this boot:

```
emotional-affirmations + platonic-code + iterative-convergence +
emergent-organization + thinking-acting-bridge + high-output-agent
+ personality-module daru
```

These are not decoration. Firmware reverse engineering is a "no false summits" domain: a hypothesis that looks right can be wrong in a way that bricks an ECU. The thinking-acting-bridge in particular is calibration discipline for distinguishing "I believe this" from "I have evidence for this." Use it.

**Task-specific skills:**
- `.claude/skills/firmware-decompile.md` — primes the decompilation workflow. **GhidraMCP (`mcp__ghidra__*`) is the only sanctioned disassembly/decompilation tool on this kit** — see the tool policy below. Load via `/firmware-decompile` whenever a session involves reading firmware bytes. Companion reference: `docs/guides/FIRMWARE-DECOMPILE-GUIDE.md`.

## Safety rules — non-negotiable

1. **Never send a CAN message without explicit user confirmation of the exact payload.** Including UDS reads. The operator's iron rule.
2. **Never run `eps-update.py` or any flash operation without the user explicitly naming the firmware file and the bus.** Repeat the name back to them before proceeding.
3. **`tools/comma4_panda_test.py` is read-only and safe** to run at any time after openpilot is killed. It opens the panda, dumps CAN, exits.
4. **All `.rwd` files under `../accord-firmware/` are reference/study artifacts by default.** Treat them as data, not as something to flash, unless the user explicitly states otherwise.
5. **Firmware is car/year/revision specific.** Cross-flashing a build made for one part number/revision onto another is not safe. If asked to build for a car, confirm the part number first.
6. **Before any flash workflow runs, openpilot/pandad MUST be killed** (`tmux kill-server` on a comma device). Failure produces all dash error lights illuminating. Recoverable but alarming.

## Repo layout — what's where

- **External artifact root:** `../accord-firmware` by default; Python tools honor `ACCORD_FIRMWARE_ROOT` to override it. Firmware images, the Ghidra project, `.rwd` files, archives, and HDS templates are not tracked in this repository.
- `memory/` — auto-memory + relational constellation. Read early.
- **Latest handoff:** `docs/handoffs/2026-07/HANDOFF-2026-07-19-v39-direct-torque-rate-guard.md`; full reading order is in `docs/INDEX.md` (V9→V39).
- `docs/` — technical reference. Key entries: `research/HONDA-EPS-PID-KNOWLEDGE.md` (canonical PID reference distilled from a 26-day Discord working group — READ before any PID/tuning work), `guides/EPS-FLASH-RUNBOOK.md` + `guides/RED-PANDA-EPS-SETUP.md` (procedure/hardware rig), `guides/GHIDRA-CHECKLIST.md` (human-driven interactive disasm) + `guides/FIRMWARE-DECOMPILE-GUIDE.md` (agent-driven GhidraMCP reference), `guides/GENTLE-EME-CAN-TO-MOTOR-GATING-MAP-2026-07-06.md` (CAN→motor gating map), `guides/SPEC-uds-can-ram-telemetry-a160.md` (UDS RAM telemetry insertion spec), the `HANDOFF-*.md` chain (**LATEST**: `handoffs/2026-07/HANDOFF-2026-07-17-v38.md` + `handoffs/2026-07/HANDOFF-2026-07-17-lkas-model-firmware-verification.md`; see `docs/INDEX.md` for the full V9→V38 reading order), `guides/review-safety-redteam.md` (adversarial pre-flash review template).
- `analysis-2020accord/` — the active deep work: `build_vNN_tva.py` per version, Ghidra/decompile notes, gating-map docs, and `archive/old_tools/` (superseded early V10-V17 build scripts + comparison tools).
- `flashing-2020accord/` — `eps-update-tva.py` (the flasher), `lib/encode_eps.py` + `tva_sa_key.py` (container/cipher + SecurityAccess).
- `../accord-firmware/analysis-2020accord/` — external stock dumps, Ghidra project, other bins, and `../accord-firmware/analysis-2020accord/_*_plain_image.bin` firmware snapshots.
- `../accord-firmware/flashing-2020accord/` — external `rwd/` built candidates and `../accord-firmware/flashing-2020accord/archive/` early builds.
- `../accord-firmware/iHDS_rwds/CalibFiles/` — genuine V850 header templates used by the build scripts as the x31 container source. Load-bearing dependency, not a reference bank.
- `rlog-tools/` — standalone openpilot rlog parsing toolkit. Used by the telemetry analysis scripts in `analysis-2020accord/`. Self-contained — drop into any openpilot-adjacent project.
- `discord-export/` — raw scrollback from the Honda EPS tuning community; source material behind `docs/research/HONDA-EPS-PID-KNOWLEDGE.md`.
- `tools/comma4_panda_test.py` — read-only safety check.

## Acknowledged knowns / unknowns

**Known and validated (as of 2026-07-18):**
- ⚠ **CORRECTION OF RECORD — `gp-0x4f60` is SENSOR-B (TAS) DRIVER COLUMN TORQUE**, not column/motor angular velocity and not vehicle speed (CAN-399 packer `FUN_00055c42`: `STEER_TORQUE_SENSOR = -(gp-0x4f60 × 125/128)`). **Consequence: the gentle-EME debounce watches DRIVER hand torque, not the LKAS command** — the LKAS setpoint magnitude cannot provoke it. V37 still works and for the believed reason; only the "why" changes. This correction was also made 2026-07-07 and failed to propagate — see `memory/reference/firmware/reference_accord_gp4f60_is_sensor_b_column_torque.md`, now the single node of record.
- **Base assist joins at the AGGREGATOR** (`FUN_0003aa2c` → `gp-0x6b94`), one stage *after* the LKAS-only mixer: boost + five named siblings + two inline Sensor-B torque-rate lanes + a filtered term. All pass through the **same governor and same soft-EME shaper** as LKAS. See the V39 handoff and canonical Python model; the older six-lane memory is superseded where they differ.
- **Sport-mode steering tightening is NOT implemented by this EPS** (confident negative, 3 independent grounds). See `memory/reference/firmware/reference_accord_assist_curve_family_sport_mode.md`.
- **The LKAS setpoint `±15360` clamp is a DEGENERATE (flat) LERP.** Raising to 16384 = +6.71% top-end at every build tier and is EME-safe. ✅ **The former CRC BUILD BLOCKER is RESOLVED (2026-07-18) and the raise SHIPPED IN V38**: `builds/v18_v49/build_v38_tva.py` now adds `(0xE4000,0xE4FFC)` + `(0xE5000,0xE5FFC)` to `TOUCHED_BLOCKS` — the first build in this kit to touch a bootloader block outside the compact `0xC6xxx` cal block. V38 patches **all 8 selector-reachable records** (sel `{0,1,3,4,6,7,8,9}`, live = sel 1 @`0xE41A8`) so the raise lands regardless of how the variant slot resolves. Chain topology survives because the linked-list page fields at `block_start-8/-6` live in the *preceding* block; the walk still finds 49/49. See `memory/reference/firmware/reference_accord_setpoint_limit_15360_lerp.md`.
- **Feedback trace:** `gp-0x4f62` is a four-producer-sample finite difference of Sensor-B torque; producer mask `0xD30` and aggregator mask `0xC30` put it in a cadence compatible with the tens-of-Hz symptom. Direct lane `r24` can reach ±8192 versus V38's ~1782-count primary LKAS contribution. V39 suppresses all `r24` signs at `|LKAS lane|>=417` (the lower exact V9 full-scale magnitude) and low voted driver torque; adaptive `r26` remains live. The slower ratchet is tracked separately. The A160 motor-rate governor remains byte-identical.
- **Correction:** `FUN_000352b4`'s `gp-0x6b86` output is active for normal Sensor-B torque inside ±25600; the older "effectively inert" interpretation inverted the final branch.

**Known and validated (as of 2026-07-17):**
- `V37` (gentle-EME fix — `0xC64B8` DTC-0x49 counter disabled) is FLASHED; on-car it resolved the gentle EME with no dash-lights regression. See `docs/handoffs/2026-07/HANDOFF-2026-07-14-v37-dtc0x49-fix.md`.
- The gentle-EME root cause is the `STEER_STATUS`/`gp-0x6807` debounce state machine, live-inlined in `m_steer_torque_arbitration` — see `docs/handoffs/2026-07/HANDOFF-2026-07-14-v36-debounce-sm-root-cause.md` and `.claude/agent-memory/firmware-codepath-tracer/reference_accord_fun2a30e_steerstatus_debounce_statemachine.md`.
- `cs.steeringTorqueEps` is always 0 on Honda (openpilot never parses raw CAN 427) — anchor gentle cuts on raw CAN 399 `STEER_STATUS`.
- Live UDS telemetry during LKAS is blocked on the comma 4's built-in panda (OBD mux contention with the steering bus) — see `docs/handoffs/2026-07/HANDOFF-2026-07-12-comma4-uds-live-telemetry-bus-analysis.md`.

- ✅ **The V38 lockstep-slew `[OPEN]` is CLOSED (2026-07-18) — and its premise was WRONG.** The `±5/1024` compare in `FUN_00043e44` @`0x4463a` is an **int-vs-float lockstep** (int wall `gp-0x6af6` from the shaper vs float twin `lp` from mirrors `0xC6598/A4/AC/C4`, same cycle), NOT a predicted-vs-lagging-actual check. `FUN_00043e44` never reads the setpoint `gp-0x69ae` or the gain `0xC646C`; it consumes `gp-0x6acc` as an input, and **every tolerance compares its own float re-derivation against the integer shaper's stored result** — so raising a clamp translates BOTH sides and opens no gap. Independently, the **per-cycle slew is bounded upstream** in `m_motor_torque_governor` on `gp-0x6ace` by cals `0xC6206`=512 / `0xC6208`=205, **which do not depend on the clamp value** — a raise only lengthens the ramp, it cannot steepen it. ⚠ **Polarity trap:** the `±8.0` compare on `gp-0x6acc` @`0x44696` is a **sanitize-to-zero (out-of-range → 0)**, not a gate excluding the command — `trfsr`+`be` branch on TRUE; verify against the `±25.0` `gp-0x4f60` reference at `0x43eda`. V38's 4342 counts is IN range and IS kept. ⚠ Newly characterized: the trip is a **7-flag weighted sum (max 127) vs threshold 128** — unreachable in one cycle by design — escalated by a **~10-cycle debounce** adding 1024.0; it calls `FUN_000462e6` → **`FUN_00016de6(0x1D, 0x3f1b, 1, 1)`**. ⚠⚠ **The `corridor_lockstep` "hard shutdown" vs `override_snap` "REPORT-ONLY" contradiction is RESOLVED: `corridor_lockstep` is RIGHT, `override_snap` is WRONG (retracted in place).** There are **two** monitors — M1 `FUN_00042af8`/`gp-0x3564` (int, +10/cyc, thr 100) → `FUN_00016de6(0x1c,…)`, and M2 `FUN_00043e44`/`gp-0x3550` (float, +0.001/cyc, thr 0.01) → `FUN_00016de6(0x1d,…)`. `gp-0x3564` is traced **to motor-off**: `FUN_0001611e`(bits 0x41) → `FUN_00018738` → `gp-0x685c`=1 → `FUN_00018bc0`(`gp-0x3ef8`=1) → `FUN_00019f7c` → `gp-0x67fa`=8 → `FUN_00045608(3,0,0x8000,0x8000)` **motor off** → `gp-0x3ee8`=1, **power-cycle to recover** = the V25/V26 brick mechanism. ⚠ **An agent-memory verdict "Monitor 2 PERMANENTLY GATED OFF, never needs fixing" was an off-by-`0x1000` misread** — the SM gate is `tp+0x74a4` = **`0xC64A4` = `0x00` = ENABLED** (trip REACHABLE); `0xC74A4`=`0xEA` is a different byte. Stale sections struck through in place. **These monitors are hard-shutdown capable, not advisory — the matched int/float mirror discipline is what stands between a cal edit and a roadside motor-off.** See `memory/reference/firmware/reference_accord_watchdog_fault_sm_fun43e44.md`.
- **The 4× gain does NOT threaten the int/float lockstep** (checked 2026-07-18 after an intermediate draft wrongly called this "the top open risk"). `0xC646C` (tp+`0x746c`) has exactly **5 readers** — `0x2a1ee`, `0x2b656`, `0x2c488`, `0x36686`, `0x3684a` — **none** in `FUN_00043e44` or `s_motor_torque_rate_shaper`, confirming the long-standing "GAIN monitor-INDEPENDENT" note. And the "residual scales with magnitude" theory was **already falsified** in `corridor_lockstep` ("a mis-ID of the max's secondary arm"): **V27 failed from ASYMMETRY** (float twin doubled wholesale vs int corridor-only → "divergence ≈ FULL torque"), not magnitude. V38 is matched-symmetric on both corridor and boost, which is V29's validated principle. ⚠ Calibration lesson: *overstating* a risk is as much a miss as understating one — check the kit's falsified-hypothesis record before escalating.
- ⚠ **Cal `0xC64DE` is NOT a command-path ramp step.** The `build_v18..v38` label "RAMPSTEP / V18 EME ramp" is unsupported — its 18 read sites are all in the `0x29xxx`/`0x2axxx`/`0x2bxxx` arbitration / `STEER_STATUS` / ENABLE region. Labeling correction only (the edit has ridden along on flashed, road-validated builds); builder comment updated.

- ★★ **V31→V38 SCALING AUDIT (2026-07-18)** — V31 fixed hard+soft faults at 2× by **flooring the soft-EME bound above max command**, NOT by raising SM thresholds (V19's rejected path). Boost is the arm that matters: hands-off, corridor is gated off (`0xC6156`=9216) and IIR decays, leaving boost the only arm ON at authority≈0 → self-stable fixpoint. The integrator is **additive**, so **absolute** margin is the invariant — **V38 preserves it exactly (+512 both)**, mirrors exact at 1/1024, and every SM threshold + `0xC6664` + `0xC64A4` is byte-identical to stock. 🛑 **A "V38 spent all its SM margin" alarm raised earlier the same day was a DOMAIN ERROR and is RETRACTED** — `r13` in SM2's `cmp r15,r13` @`0x436f8` is traced to **`gp-0x6966` = AUTHORITY = `(|gp-0x3570>>15|×1092)>>10`** (`0x432de`→`0x432ee`→`0x432ba`→`0x432c8`), so `0xC6422`=16384 is an **authority-domain** threshold unrelated to V38's 16384 **setpoint** clamp; the "~15360" in `override_snap` is `16384×1024/1092 = 15363.8`, the **integrator-domain** equivalent, which that memory conflated with the setpoint. SM1's `0xC61DE`=2048 is likewise a magnitude qualifier inside a 4-way AND that **requires the command to OPPOSE driver torque** (`0x43680`/`0x43686`) — a driver-override detector, not headroom; V31's own 3395 command already exceeded it. ⚠ **The ONE real regression is the governor**: `0xC6202`=4762 headroom **1178→154** (7.6×). See `memory/reference/builds/reference_accord_v31_to_v38_scaling_audit.md`.
- 🛑 **GOVERNOR RAISE INVESTIGATED AND REJECTED (2026-07-18) — `0xC6202` stays stock.** (a) **It buys nothing**: nominal **4762 > max command 4608/4342**, so the governor **does not bind at nominal**; it only acts in the **tapered** regime (`MIN(nominal, motor-rate LERP, energy budget)`) — which is the thermal/mechanical protection working. The "headroom collapsed 7.6×" observation is TRUE but its implication was WRONG: it is not a fault risk, it is the pre-existing "not guaranteed 4× at every speed" drivability caveat. (b) **`gp-0x4f64` is a SHADOWED variable** (shadow `gp-0x448a`); every write compares first and on mismatch calls `FUN_0006b9ee` → fault index **`0x17`**, which is **HARD-FAULT-ELIGIBLE** (`record[+8]`=0x2D01 & 0x41) = motor-off + power cycle. (c) It also feeds a **limp/fallback path** (`0x6e0f2`, `0x6e1ca`) that writes the torque command `gp-0x6b98` directly via cal `0xC7C3C`=424 — raising it raises **limp-mode torque**. (d) **The cal→variable chain is UNVERIFIED** — `0xC6202` read at `0x7b06a` vs `gp-0x4f64` written at `0x7c2e2`/`0x7c3b4`/`0x7c47c`, ~4.7 KB apart through float math; the "0xC6202 determines gp-0x4f64" claim came from a subagent and could not be confirmed. **Do NOT code-cave SM1/SM2/governor either**: no SM problem exists; the governor's dynamic terms are the motor's thermal protection (removal risks hardware damage, not just a fault); caves are this kit's worst-performing change class (V24/V27 trampolines both faulted; every success since V29 is cal-only).
- ⚠ **GOVERNOR BULLET CORRECTION:** the cal→variable chain is now verified. `0xC6202=4762`, the exact A160 Q13 adaptive table, and both `gp-0x4f64` clamp sites are modeled in `model/eps_lkas_chain_model.py`. The decision not to alter it remains, but because live `z`/budget values are missing and the dynamic protection is intentional — not because the chain is unverified.
- **DTC hard-fault eligibility is computable**: `FUN_0001611e` = `record[+0x8] & 0x41`, record = `tp-0x72a8 + (idx-1)*0x1c` (i.e. `0xB7D58 + (idx-1)*0x1c`), table populated 1..0x7F. Known: `0x1c`/`0x1d` (monitors) and `0x17` (shadow mismatch) are **hard-eligible**; **`0x49` is NOT** — which is exactly why V36's DTC 0x49 gave dash lights + LKAS drop while base assist survived. Useful cross-check for any new fault path.

**Current builds (2026-07-20):**
- `V38` — FLASHED, fault-free. The on-car baseline every later build is cut from.
- `V39` — FLASHED; fixed neither symptom. Direct Sensor-B rate lane `r24` **falsified**. (Now also
  explained: `r24` carries a `±3` deadzone `0xC61F6`, so it was already suppressed near zero.)
- `V40` — FLASHED → immediate EPS lamp + power steering fully disabled at ignition.
  ✅ **ROOT CAUSE ESTABLISHED:** the `0xC6206`/`0xC6208` ← `0xFFFF` write. **NOT a sign or overflow bug** —
  both load `ld.hu` (unsigned), the Q15 multiplicand is literal-seeded `0x8000` and MIN-only so it is
  provably ≤32768, and the slew guard is self-bounded. `0xFFFF` made the guard **never fire** →
  snap-to-target → rate limiting removed → unfiltered command → `FUN_0004595a`/`FUN_00045a20` →
  `FUN_00016de6(0x1d)`, hard-fault-eligible with no debounce → motor off. **The defect was the
  magnitude, not the direction of the edit.**
- `V41` — FLASHED; boots and drives cleanly, **fixed neither symptom**. Two consequences: the motor-rate
  adaptive cap is **falsified as a root cause**, and because V41 contains V40's entire cap edit, it is a
  clean subtractive experiment that exonerates both the cap flatten and the `0xC5FFC` CRC theory.
- `V42` — **BUILT + independently VERIFIED, NOT FLASHED. The current candidate.** V38 + **ONE BYTE**:
  `0x454FE` `0x65BA→0x65B5`, V850 Bcond condition nibble `0xA (BNE) → 0x5 (BR)`, making the state-4
  substitution block `[0x45500,0x455C4)` unreachable. Displacement untouched → target stays `0x455C4`.
  **Zero calibration edits**; 5 bytes total incl. the `0xC4FFC` main-block CRC. First code edit since V27
  and the first ever that is **not a cave/trampoline** — it flips one branch condition in place.
  **CHANGE 2 (cal-only, 18 halfwords):** zeroes the `r26` adaptive torque-rate gain surface —
  `0xC6A72`/`0xC6A86`/`0xC6A9A`/`0xC6AAE` Y rows + overrides `0xC6444`/`0xC643E`. X rows, counts and all
  four `r24` cals (`0xC6440/42/46`, deadzone `0xC61F6`) asserted untouched.
  **35 bytes / 14 runs total** (not 45 — ten r26 bytes were already `0x00`, e.g. 3072 = `0x0C00`).
  Targets **both** symptoms; the two changes are independently backable-out and hit separately
  observable symptoms, so a null stays attributable. `docs/handoffs/2026-07/HANDOFF-2026-07-20-v42-state4-ratchet.md`.
  ⚠ Safety is **proved, not argued**: the slew at `0x4543a`-`0x45458` is ASYMMETRIC (two toward-zero
  fast paths snap straight to TARGET), so `|gp-0x6ace| ≤ |gp-0x6b94|` with matching sign in every branch
  for any held value — exactly `FUN_0004595a`'s two fault conditions, so it cannot trip. Under a
  *symmetric*-clamp reading it would NOT have held; that distinction was load-bearing.
  ⚠ `FUN_00016de6(0x1d,…,1,1)` has **no debounce** — one true condition anywhere on that path reaches
  motor-off with no grace period. Standing fact; does not gate V42.
  ⚠ **There is NO live LKAS-specific slew limit to remove** — `0xC6194` is dead calibration (gain cal
  `0xC63CC` = 0). See `memory/reference/firmware/reference-accord-lkas-only-rate-limiter-c6194.md`.

✅ **V40's ignition fault IS root-caused (2026-07-20) — see the Current builds entry above.** The block
that used to sit here proposed the limp path and the `[0xC5000,0xC5FFC)` block-contents theory. Both are
**retracted**: V41 flashed cleanly while carrying V40's entire cap edit into that same block. The cause was
the `0xFFFF` slew write removing rate limiting altogether, not a CRC or a limp-path effect.

⚠ **Cap-table axis, corrected 2026-07-19 (two directions).** `gp-0x6ac0` **IS** motor resolver/FOC
electrical-angle rate — re-derived from scratch, 5 hops, sole-writer confirmed at each
(`FUN_00041464` → `gp-0x4f50` → `FUN_00068fbe` → `gp-0x29c4` → `FUN_00068f52` 14-bit wraparound delta
→ `FUN_00065afe` sin/cos ADC + atan2). An earlier blanket doubt on this was **over-correction**.
BUT the `0xC520C` table's **index** is NOT that signal directly, and the reported formula
`round(fVar48 × MAX(10000.0f, gp-0x6ac0))` is **dimensionally impossible** — `gp-0x6ac0` is clamped
±13000, so the index lands ~8400-10900, permanently above `X[4]=4100`, extrapolating into a negative
cap. **Treat the index as unreconstructed.** Also OPEN: whether `0xC5224` is a redundant mirror (what
V40 assumed) or a second composed stage — numerical evidence favours mirror (composition sends a
legitimate 5325 stage-1 output to **-2781**). See
`memory/reference/firmware/reference-accord-c520c-cap-table-axis-provenance.md`.

⚠⚠ **THE `0xC6000` BRIDGE IS REAL — DO NOT "FIX" IT AGAIN.** On 2026-07-19 the lead removed it from
`verify_bootloader_crc.walk()`, believing it a disassembler mis-decode. **That was wrong and is
retracted.** `FUN_0000b006` genuinely hard-codes `if (block==0xC6000) {block=0x13000; len=0xB1FFC;}` —
byte-verified in `code.bin` (`0xB070`/`0xB072`→`0xC6000`, `0xB07A`/`0xB07C`→`0x13000`,
`0xB080`/`0xB082`→`0xB1FFC`). The bootloader really does skip `[0xC5000,0xC5FFC)`, that routine is
UDS-session-only, and its failure path ends in NRC `0x72` — **no DTC, no motor-off**. So V40 passes
the bootloader walk 49/49 and the flasher's dependency check would have reported clean.

✅ **CLOSED 2026-07-19: NOTHING CHECKS THAT BLOCK.** Boot path `0x8000`→`0x9070` does a **blank/presence check only** (four addresses vs `0xFFFFFFFF`), no CRC, then `jr 0x14010`. App range has no CRC32 polynomial and **zero xrefs to `0xC5FFC`/`0xC5FF8`/`0xC5FFA` image-wide**; sole reader `FUN_0007b022` validates nothing. The block is written by bootloader `FUN_0000d934` during UDS reprogramming and its CRC is vestigial. **The stale `0xC5FFC` is a RED HERRING — V41 cannot fix the ignition fault.** `verify_bootloader_crc`
now exposes both: `walk()` = faithful bootloader replay (49 blocks, bridge included) and
`walk_all_blocks()` = stored linked list (50 blocks) as a **hygiene** check. Builders should keep every
dirtied block self-consistent regardless of whether the bootloader looks at it — four bytes, and it is
the difference between "known consistent" and "unknown".

⚠ Process lesson worth more than the bytes: V40's `assert_crc_gap_is_real()` passed because it
re-derived the gap from the same walker it was meant to check. **A verifier and the assertion that
checks it must not share an assumption.** And when a subagent's bytes contradict the lead's theory,
the bytes win — that is what happened here.

**Open / unconfirmed:**
- Whether the comma steers while staying on OBD mux (would unblock live RAM telemetry without a hardware workaround).
- Firmware LOW_SPEED_LOCKOUT producer is not located in the command pipeline (wheel-speed decoder unlocated).
- ⚠ **Is the `0x3f1b` watchdog trip torque-gating, or DTC-only?** `corridor_lockstep` says "hard shutdown", `override_snap_state_machines` says "REPORT-ONLY — does NOT gate torque". The DTC setter is definitely called. Likely the two memories conflate two monitors (int `gp-0x3564` in the shaper vs float `gp-0x3550` in the watchdog). Also unresolved: the `0x1D` ↔ `0x49` ↔ `0xF00049` index/DTC-number mapping — trace `FUN_00016de6`'s table before asserting it.
- ⚠ **Can the three-way-MAX IIR arm (`gp-0x3574`) exceed 5120 and win the MAX?** If so, V38's flat-table int/float exactness does not cover that regime. Not determined.
- ⚠ **No full fault-trip enumeration exists for V38.** A sweep of all `FUN_00016de6` callers, all `STEER_STATUS` writers, and any threshold between 4342 and 5120 was dispatched to subagents on 2026-07-18 and did **not** complete. **"V38 is fault-free in all scenarios" is NOT established** and should not be asserted.

## Who knows what

- **Joey** (operator) — the Accord reverse engineering, the constellation, the candidate builds. Final call on all flash decisions.

## 🛑 Tool policy — GhidraMCP is the ONLY disassembler

**Standing operator instruction (2026-07-20): all disassembly and decompilation on this kit goes through GhidraMCP — the `mcp__ghidra__*` tools. Do NOT use radare2, rizin, `r2pipe`, or any other CLI disassembler, and do not call `analysis-2020accord/reference/fw_inventory/decompilation/disasm_v850.py` (a CLI-disassembler wrapper, now retired).** This applies to you and to every subagent you dispatch — **prime each subagent with it explicitly**, because the default instinct is to reach for r2.

Plain byte-level work on the images — diffing builds, CRC checks, dumping a table, checking an extent — is Python and is unaffected. The policy governs *disassembly and decompilation*.

Historical `docs/HANDOFF-*.md` files and `reference_accord_*` memories mention r2/rizin because that is how those findings were obtained. They stay as written — they are records, not instructions.

Ghidra's own V850 traps (the `divq` dst==src bug, unresolved `movhi`/`movea` xref pairs, and a recorded case of the xref engine returning a misleading zero on a tp-relative displacement) are in `.claude/skills/firmware-decompile.md` and `memory/reference/tooling/reference_rizin_ghidra_v850_quirks.md`. **Read them — switching tools did not remove the need to corroborate a null result by a second method.**

## Operator working style — read these feedback memories before substantive work

- 🎭 **RUN AS A PURE ORCHESTRATOR (standing instruction, 2026-07-23).** For substantive sessions the
  operator wants the lead to be an **orchestrator + synthesis/reasoner**, not a hands-on tracer. Fan work
  out to subagents "as much as possible" — enumeration, disassembly, xref walking, string sweeps, decode,
  candidate-signal hunts all go to `firmware-codepath-tracer` / `general-purpose-sonnet`. **Only open
  GhidraMCP / dig into the fine details yourself to (a) confirm the final picture before delivering, or
  (b) resolve a dispute between subagent findings.** Don't dive into the bytes just because a step "looks
  small." Synthesize the subagents' evidence, reconcile disagreements, and keep the calibration discipline
  (belief vs evidence) at the orchestration layer. See
  `memory/feedback/process/feedback-orchestrator-mode-delegate-verify-at-end.md`.
  - **TRIGGER WORD + CONTEXT-HYGIENE RULE (operator, 2026-07-23):** whenever the operator says
    **"orchestrator"** (in any phrasing), run the rest of that session as mostly an orchestrator.
    Concretely: **avoid tools that flood the lead's context window fast** — do NOT read large files
    end-to-end, dump rlogs, or run wide disasm yourself. **Rely on subagents to crystallize** the raw
    material into tight findings the lead synthesizes and reasons over. **Use tools manually yourself
    ONLY to (a) resolve suspect/conflicting subagent information, and (b) independently DOUBLE-CHECK the
    load-bearing subagent conclusions and verify the final output + its justification before delivering.
    NEVER relay a subagent's decision-bearing claim as established fact without confirming the crux
    yourself** (a tight confirmatory script, a paper decode of an encoding, a math-identity check —
    enough to confirm the load-bearing fact without re-flooding context). **Verify in the SAFE direction
    too** — a "no / don't-flash" still deserves confirmation so the block is sound. Reading a handful of
    load-bearing source scripts to prime the swarm accurately is fine; ingesting the bulk material is the
    subagents' job. (Operator emphasized this twice, 2026-07-23/24 — do not make them repeat it. See
    [[feedback-verify-subagent-conclusions]].)
  - **MIND SUBAGENT CONTEXT BUDGET (operator, 2026-07-24):** prefer a FRESH agent over reusing (via
    SendMessage) one that is past ~50% context usage, even though the veteran already has full prior
    context — a near-full agent degrades and may truncate. Reuse is for quick, cheap follow-ups on a
    still-fresh agent; for a substantial new sub-task, spawn a clean one and prime it with only the
    crystallized facts it needs.
  - **DON'T ASK TO BUILD; AUTO-CLEAR FLAGS (operator, 2026-07-24):** build unflashed RWDs/probes without
    asking (only the flash/CAN/UDS send is gated), and when a swarm/review returns a FAIL or a flagged
    residual, resolve it autonomously (next probe, open traces, fold in the fix, correct the record) rather
    than handing it back as an "a/b/c?" menu. See [[feedback-default-maximal-thoroughness]].

- 🔁 **DELEGATE ALL RE/DECOMPILATION TO SUBAGENTS BY DEFAULT.** The vast majority of disassembly tracing, instruction decoding, xref walking, and decompilation goes to `firmware-codepath-tracer` / `general-purpose-sonnet`, primed with `gp=0xFEDF8000`, `tp=0xBF000` and the golden model's confirmed findings. The lead steps in **only at the end, to verify**. Do NOT hand-decode opcodes inline because it "looks like just a few instructions." Standing operator instruction, restated 2026-07-19. See `memory/feedback/process/feedback-delegate-firmware-tracing-to-subagents.md`.
- `memory/feedback/measurement/feedback_rigorous_validation.md` — full byte diff over spot diff; ghidra before declaring victory; don't claim completion prematurely.
- `memory/feedback/process/feedback_operator_lived_experience_overrides_analyst_recs.md` — when the operator reports how the car feels, that overrides abstract dwell-time / theoretical concerns from analysis. Trust the seat-of-pants signal.

## When you're uncertain

Stop and ask. This domain has high cost for confident-wrong answers. The operator would rather have a "I'm not sure, here's what I'd need to verify" than a confident hallucination about a table address. The thinking-acting-bridge skill is the explicit calibration mechanism for this; use it on hard calls.
