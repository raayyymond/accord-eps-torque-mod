# Accord TVA EPS — Torque Input→Output Code Path & Torque Tables (Hypothesized)

**Vehicle:** 2020 Honda Accord Touring, EPS `39990-TVA-A160` (V850E2, little-endian, 1 MB)
**Companion:** `HOW_TO_BUILD_ACCORD_TVA_RWD.md` (how to package a change into a flashable `.rwd`)

> **★★★ 2026-05-27 (LATEST) — V18 (2× + RAMP-ONLY) FLASHED + ROAD-VALIDATED: drives well. V16/V17 mechanism dismantled by a 4-analyst Ghidra review.** A multi-analyst disassembly review (`../assessment/`) overturned the slew/deadband EME story below, and the operator road-tested the survivor (V18). Distilled truth:
> - **V18 is the good build and is CALIBRATION-ONLY.** 2× gain `0xC646C`=1782 + clamps `0xC61B2`/`0xC61B4`=1024 + **ramp `0xC64DE` `0x11`→`0x1B` (17→27) and nothing else** (deadband stock 29491, slew stock 0). Decode-verified on the on-disk `.rwd`: exactly 15 byte changes (2 PN + 3 cal halfwords + 1 cal byte + 2 recomputed CRCs), **no code patch, no trampoline.** Operator reports it drives well — per [[feedback-operator-lived-experience]] that road result is authoritative and supersedes the analyst caveat that "ramp only fixes recovery, not the snap."
> - **The slew "fix" was INVERTED — V16 REJECTED.** `0xC61D6`=0 does NOT mean "the delivered-command limiter is disabled/passthrough." `0xC61D6` (`tp+0x71d6`, read once @`0x43350`) is the **step size** of a rate limiter on an internal persistent state `gp-0x356c` (exactly 2 refs program-wide: read @`0x434ce`, store @`0x43504`). step=0 ⇒ the state **freezes/pins at 0** = a dormant lane contributing nothing. Setting 0→14 **ACTIVATES an uncalibrated speed×torque 2D shaping map** (target = `0xC6770` speed curve × `0xC69E8` torque curve, `25·r8>>10`) onto the live command (mux byte `0xC64C9`=0 selects it → `r28`→`r20`→add @`0x43af4`→governor→±0x2000→`gp-0x6b98`). That is the opposite of "restore a damper." **Last/never lever.**
> - **Deadband-only (V17) is INERT, not a fix.** `0xC6424` (`tp+0x7424`, read once @`0x43358`, one cmp @`0x434ca`) gates ONLY the `gp-0x356c` limiter; with slew=0 that state is pinned at 0, so narrowing 29491→20000 changes nothing. Deadband and slew are **coupled** — the deadband only has meaning once slew≠0.
> - **The REAL command-cut is a DIFFERENT node.** `gp-0x6b98`→0 in the EME is driven by the **override state machine** (`gp-0x6960`, states `gp-0x355d`, stores @`0x4362a`/`0x436c2` incl. an `ori 0x8000` sentinel), **NOT** by the shaper deadband. The Era-16 memory conflated the two.
> - **Ramp `0xC64DE` LABEL was also inverted.** `tp+0x74de`=stock `0x11`=17 is the **count ceiling** of the re-engage/debounce SM in `m_steer_torque_arbitration` (read 8×; counter `gp-0x6756`, init `=(ceiling>>1)+1`, on driver-torque `gp-0x6a5e`, transitions `gp-0x3d36`/`gp-0x6809`). 17→27 **lengthens/softens** the re-engage span (≈8→≈13 steps) — it is NOT "faster re-engage." It is the only V16 lever that actually sits on the override path the EME traverses, and it targets the **recovery ratchet**, not the initial snap.
> - **No output rate-limiter exists as a cal value.** The shaper output `gp-0x6b98` has only a ±0x2000 magnitude clamp + a ±5 change *detector* (for the lockstep monitor) — no rate-of-change limit. A true asymmetric down-rate limiter would require a **CODE PATCH (a trampoline from the `0x43b52` store into the erased `0x8B218+` cave)**. This was **scoped on paper in the review but never built** — there is NO trampoline in any `.rwd` and NONE in the Ghidra project (verified this session: `../accord-firmware/analysis-2020accord/ghidra_project/code.bin` is byte-identical to the stock dump; cave all-`0xFF`; `0x43b52` is the stock `st.h`). The earlier "matches aragon's asymmetric rate-limit prior art" framing is **RETRACTED** (his `rwd-xray-2026` has no such artifact; his comma-side LPF cannot fix a firmware gate tripped by physical column torque).
> - **The EME firing gate is UNOBSERVABLE on-car** (internal RAM, not CAN; not bench-reproducible). Only passive CAN `0x427` motor-torque sees the outward signature. So no gate-specific fix can be mechanism-validated — V18 was validated by road feel.
>
> Authoritative: [[reference-accord-driver-override-plausibility-eme]] (corrected), [[reference-accord-eme-lever-semantics]] (new), `../assessment/user-A-verdict.txt` (the 11-round trace). Builder: `build_v18_tva.py`.
>
> **★ 2026-05-27 [⚠ SUPERSEDED by the ★★★ block above — the slew "re-enable" mechanism here is INVERTED; V16 was REJECTED, V18 ramp-only is the flashed fix] — EME root cause LOCATED + V16 fix + full inventory + pointer audit.** The 2× build's "whole power steering momentarily cuts out + ratchets on a sharp low-speed override (no DTC)" is resolved: base assist + LKAS merge into the shaper accumulator and exit the single command `gp-0x6b98`; a hard override drives a transient (no-DTC) re-init + the shaper **deadband** (`tp+0x7424`=`0xC6424`=29491) zeroes the command via node `gp-0x6960`, and the **delivered-command slew limiter is DISABLED** (`tp+0x71d6`=`0xC61D6`=**0**), so the drop is a hard cut+hold+jump instead of a soft dip. **FIX = re-enable slew `0xC61D6` 0→14** (V16, `build_v16_tva.py`; + deadband→20000, ramp `0xC64DE`→27; 49/49 CRC, unflashed). **Pointer-base audit:** app `tp=0xBF000` is built in THREE instrs (`movhi 0xb`+`movea 0x7000`+**`add r1=0x8000` @0x140d6**) — the missed third instr caused the earlier `0xC71D6` slew/deadband address error. Full variable+table inventory with all touchers: `fw_inventory/MASTER_INVENTORY.md`. Authoritative: `memory/reference_accord_driver_override_plausibility_eme.md`, `memory/reference_accord_pointer_base_audit.md`.

> **✅✅ RESOLVED 2026-05-26 — V14 FLASHED + ROAD-TESTED: IT WORKS (~2× LKAS at the wheel).** The arb OUTPUT gain `tp+0x746c`=`0xC646C`=891 (→1782) + the ±512 clamps `tp+0x71b2`/`tp+0x71b4` (→1024) were the LKAS magnitude binder. The LKAS path is request-limited (stock arb out ≈418, V14 ≈835) far below the 4762 governor — the doubling reaches the motor uncut; V15/governor `0xC6202` edit NOT needed for 2×. The ±0x4000/±0x2800/±0x2000 waterfall below bounds the *merged* signal above the governor and was never the LKAS binder. Authoritative: `memory/reference_accord_lkas_delivery_and_governor.md`.
>
> **⚠⚠ CORRECTION 2026-05-26 (late) — `tp`=0xBF000 (not 0xF8000), and the delivery topology is now xref-verified.** Authoritative record: `memory/reference_accord_lkas_delivery_and_governor.md`. Key fixes to this doc: (1) the LKAS arb torque is NOT amplified-then-cut and is NOT a monitor dead-end — it reaches the motor via arb→limit_and_pack→distribute_clamp(source idx 1)→`gp-0x6b4c`→`gp-0x6b94`→`gp-0x6ace`→`gp-0x6acc`→shaper `FUN_00042af8`→`gp-0x6b98`→FOC (GAP 1's mixer→FOC handoff is CLOSED — `gp-0x6b98` has 45 FOC/CAN readers). (2) The delivered high-end binder is the runtime governor `gp-0x4f64` = cal `tp+0x7202`=`0xC6202`=**4762** (applied in `FUN_0004503c` + the shaper), NOT the ±0x2000=8192 static and NOT the FOC inner-loop constants (those are present, not absent — `tp`=0xBF000). (3) The LKAS arb output magnitude is set by gain `tp+0x746c`=`0xC646C`=891 + clamps `tp+0x71b2`/`tp+0x71b4`=512 (V14's levers). The ±0x4000/±0x2800/±0x2000 waterfall below bounds the merged signal but is above the governor, so it isn't the LKAS binder.

## Trust calibration (read first)

- **[V]** verified by Ghidra/rizin disasm or byte-decode of `code.bin`/`data.bin`.
- **[LIKELY]** structurally strong but not pinned to a decompiled live read.
- **[OPEN]** unknown from the binaries in hand.

The two **endpoints** of the torque path (CAN input, motor PWM output) are Ghidra-verified. **Update 2026-05-25 (§0.5): the LKAS interior path is now traced end-to-end** — CAN `0xE4` → routed buffer `0xFEDF6BD8` → `setpoint = clamp(STEER_TORQUE×−4, ±0x4000)` @ `0xFEDF1652` → table-driven arbitration `FUN_00028ea6` → … → mixer → FOC/TSG20. GAP 1 (LKAS consumer) is **CLOSED**; the only remaining interior gap is the narrow mixer→FOC q-current-reference handoff variable. The **numeric live-control parameters of the FOC inner loop are still absent from our dump** — see the Hard Ceiling. So this document now maps the LKAS command *path* with high confidence; the deeper FOC constants and some *table roles* remain hypotheses.

> **⚠ CORRECTED 2026-05-25 — the previous `data.bin` model in this doc is WRONG.** It does NOT map to flash `0xF0000–0xFFFFF`, and `data.bin[addr - 0xF0000]` is invalid. The truth (operator-supplied base + tag structure verified by `strip_data_tags.py`): **`data.bin` is 32 KB of real flash at `0x02000000–0x02007FFF`** (the µPD70F35xx data-flash region), stored **doubled** on disk because each 4-byte data word is followed by a 4-byte tag word reading `0xFFFFFFFF` (erased) or `0x00000000` (valid). De-tag → 32 KB. **Consequence:** every "table X is real in data.bin at `0xFxxxx`" claim in this document is **probably wrong** (wrong base + the raw offset interleaved data with tag bytes) and must be re-derived against the de-tagged 32 KB at `0x02000000`. The `tp (r5) = 0xF8000` calibration base is a pure `code.bin` finding and is unaffected; the editable `0xC4000–0xFD0B8` calibration band lives in `code.bin` and is also unaffected.
>
> *Original (uncorrected) prerequisite, preserved:* ~~`data.bin` (the 64 KB second-flash dump) maps to flash `0xF0000–0xFFFFF` — the `tp`-relative window. A `tp`-relative table that reads `0xFF` in a `code.bin`-only project may be populated in `data.bin`. Always check `data.bin[addr - 0xF0000]`.~~ `tp` (r5) = `0xF8000` (calibration base, set once at boot `0x9152`, never reloaded in the motor cluster).

---

## 0. Session 2026-05-25 — verified deltas (read before trusting older sections)

This session corrected several loose attributions below and added a master key. Confidence markers as in §"Trust calibration".

- **`gp = 0xFEDF8000` [V, cross-checked ×2].** Ghidra never established the V850 global pointer from the raw bin, so the decompiler shows every small-data access as `unaff_gp - offset`. Convert: `abs_RAM = 0xFEDF8000 - offset`. Proven by (a) `FUN_0001ce68` staging CAN bytes to `gp-0x1734` = `0xFEDF68CC` (the known STEER_TORQUE slot), and (b) `DAT_fedf55d8` = `gp-0x2A28`. See `memory/reference_accord_gp_base_fedf8000.md`. CAVEAT: gp-relative accesses are still NOT xref-able (Ghidra leaves them register-relative); only absolute-mode accesses of the same RAM var show in `xrefs_list`.

- **V10A empirical result [V — road-tested]: `0xC4A42`/`0xC4A6E` are the DRIVER column-torque→assist transfer, NOT LKAS.** Linearizing+doubling them made driver steering much lighter AND killed LKAS entirely. Mechanism: inflated computed driver-torque → more assist per unit hand-torque (lighter) + continuous trip of the driver-override/hands-on gate → LKAS refuses to actuate. Corroborated by `docs/HONDA-EPS-PID-KNOWLEDGE.md` §8 (a monotonic-saturating curve is "a gain/attenuation curve, not the LUT") and the architecture table (driver-assist is a separate path from the LKAS CAN-torque path on every mapped Honda EPS). So §3c below is now CONFIRMED driver-assist, and the LKAS table/clamp/gain is a *separate, still-unlocated* structure.

- **FOC chain reclassified [V].** The ADC-complete ISR `FUN_0006404c` chain (`0x6428e`→`0x65afe`→`0x711f8`→`0x71272`→`0x710d4`) is the FOC **feedback + current regulator**, NOT torque-demand generation: `0x6428e` reads 2 phase currents; `0x65afe` resolver sin/cos (12-bit ±0x800) → atan2 rotor angle, then `0x68f52` = rotor-**speed** estimator (Δθ·120000≫14, LPF, clamp ±13000); `0x710d4`/`0x711f8` = ASIL sum self-checks of a 6-int buffer (`FUN_0006b9ee` = divergence handler); `0x71272` = the big Park/Clarke/PI/SVPWM voltage computation (emits duties `×51200.0`). It **consumes** a q-current reference written by a separate slower steering task. The older "torque setpoint lives in the `0x65afe` chain" (GAP 2) was imprecise — that chain is angle/speed/current feedback.

- **CAN RX path decoded [V].** `FUN_0001ce68` = generic mailbox-RX (`param_1`=mailbox idx, stride 0x40), stages 8 frame bytes; STEER_TORQUE (int16 BE) at `0xFEDF68CC`. `FUN_0001ddd0` = dispatcher: diag msgs via fnptr table `0xB73FC`; other msgs frame-copied to a per-index dest buffer whose address comes from a **`tp`-relative route table (absent — see Hard Ceiling)**. This is the mechanism behind GAP 1: the LKAS consumer cannot be named statically.

- **Master mode/arbitration bitfield at `0xFEDF1288`** (`gp-0x6d78`) [V]. `FUN_000197d0(n)` returns bit n; `FUN_000197ea` is a state handler clearing bit 0. The driver-override gate that V10A tripped lives in this arbitration layer, but its bit-setters are gp-relative (not xref-able) and several conditions read `tp+0x74xx` = `0xFF4xx` (absent). Mode var `0xFEDF56E0` (`gp-0x2920`) via `FUN_0006d116()`.

- **Hard Ceiling re-confirmed a 3rd time, exhaustively [V — but the `data.bin` half is now INVALID].** Checked **both** `code.bin` AND `data.bin` at the exact `tp`-relative offsets: motor/PI params `0xFE0xx`, live-control `0xFD8C8`, FOC state `0xFF4xx` are **`0xFF` in both**. ~~`data.bin`'s populated span is `0xF0010–0xFF02B` (33% non-FF, sparse) and includes the commutation table `0xF52C0`, but NOT the motor constants.~~ **⚠ 2026-05-25:** the `data.bin` portion of this is **wrong** — `data.bin` is 32 KB at `0x02000000`, not an `0xF0xxx` overlay, and was read as a tagged/doubled stream (the "33% non-FF" and "populated span `0xF0010–0xFF02B`" are artifacts of the tag words; see the §0-top CORRECTION). The Hard Ceiling conclusion still stands on the **`code.bin` half alone** (those addresses are `0xFF` in `code.bin`, which doesn't cover `0xF8000+`), so closing GAP 1/GAP 2 to *actionable numbers* still needs a complete `0xF8000+` partition dump or dynamic bench RAM/CAN capture.

- **EPS System Description pipeline (from `EPS System Description 3455.pdf`, see `_eps_sysdesc_pipeline.md`):** Base Current(torque,speed) → Inertia comp → Damping comp → **Target Current** (signed sum) → Unloader(end-stop) → Motor-output-limit(thermal) → Current FB(PI) → Steering-wheel-return → 3φ PWM. The document documents **no** driver-override or dual-sensor logic → the override gate is a firmware/LKAS-layer addition, not baseline assist.

### 0.1 Tooling envelope (this Ghidra project) [V]
What works: `functions_decompile` by exact address, `memory_read`, **DATA** `xrefs_list`. What does NOT: **CALL xrefs return 0** even for calls the decompiler shows (no call-reference DB built for this raw V850 image — consistent with `reference_rizin_ghidra_v850_quirks`); `analysis_get_callgraph` walks downstream only and renders names as `???`; `memory_disassemble` returns empty; gp-relative accesses are left register-relative (not xref-able). **Consequence: you cannot enumerate the CALLERS or bit-SETTERS of anything statically.** Forward reads + DATA xrefs only. (Re-running auto-analysis might rebuild call refs, but do NOT while a subagent is using port 8193.)

### 0.2 Arbitration / mode RAM map (gp-resolved, for bench capture) [V addresses, roles INFERRED from usage]
The control law (`FUN_00065afe`, `FUN_0006404c`) is gated by a multi-flag state machine. With `gp=0xFEDF8000` these resolve to absolute RAM — **these are the addresses to log in a dynamic RAM capture to decode LKAS-enable / mode / override state** (the recommended unblock path):

| Abs RAM | gp-offset | Observed use |
|---|---|---|
| `0xFEDF1288` | `gp-0x6d78` | **master 32-bit status bitfield**; `FUN_000197d0(n)`=get bit n; bit 9 gates resolver-correction; bit 0 cleared by state handler `FUN_000197ea` |
| `0xFEDF56E0` | `gp-0x2920` | mode var (`FUN_0006d116`), branch on `==2` |
| `0xFEDF31C2` | `gp-0x4e3e` | 3-way mode selector (`==0` / `==2` / else) at top of `FUN_00065afe` |
| `0xFEDF3192` | `gp-0x4e6e` | FOC enable/fault: `==0` runs normal loop, else `FUN_00069cfc` (degraded) |
| `0xFEDF1853` | `gp-0x67ad` | mode/enable counter (`==1` or `>2` enable an angle-offset add) |
| `0xFEDF189D` | `gp-0x6763` | direction/orientation flag (`==0xFA` → invert electrical angle `0x4000-θ`) |
| `0xFEDF68CC` | `gp-0x1734` | **LKAS STEER_TORQUE** staged (int16 BE, CAN 0xE4) |
| `0xFEDF3128` | `gp-0x4ed8` | electrical angle out (consumed by `FUN_00071272` ×2π/16384) |
| `0xFEDF563C` | `gp-0x29c4` | motor speed (clamp ±13000, from `FUN_00068f52`) |

Cross-gate by `tp+0x74bf` = `0xFF4BF` (ABSENT cal marker) — several arbitration branches can't be evaluated from the dump (Hard Ceiling).

### 0.3 Driver-assist task chain — mapped end to end [V structure, addresses gp-resolved]
Found by enumerating the 1 ms scheduler tree (subagent + forward decompile):

```
1ms scheduler FUN_0002214a → FUN_0006bb08 → FUN_0006bea8 (task-slot dispatch)
  slot 3  FUN_0006651e  TORQUE-DEMAND TASK
            - assist-mode state machine on gp-0x4e65 = 0xFEDF319B:
                0=normal → FUN_0006634e ;  1/2=transition → FUN_00068dfe ;
                3=active + dual-sensor plausibility (tp+0x5970 vs tp+0x5978;
                  on fault → FUN_000197b8(4) sets status bit4, revert to mode 1) ;
                4=fault
            - thermal gain poly: (T-70)^2*1.7e-6 + (T-70)*0.001 + 0.968   (T = gp-0x4e7a)
  └ FUN_0006634e  ASSIST-CURVE INTERP [V] — interpolates by TEMPERATURE between two
        row pointers gp-0x34ec / gp-0x34e8 = 0xFEDF4B14 / 0xFEDF4B18.
        row struct = {+4 torque, +6 speed, +8/+9, +0xc/+0xd gains(clamp 0..0x7f), +10 tempidx}
        outputs demand → gp-0x4fb8 / -0x4fbc / -0x4fb6 / -0x4fba → FUN_000690f8
  slot 0x10 FUN_00065eda  MOTOR OUTER SHELL — resolver angle FUN_0006adb2, rotor flux
        FUN_00069272, total current mag = SQRT(Id^2+Iq^2) @ gp-0x4ff4; gated by status
        bit15 (FUN_000197d0(0xf)) + fault queries FUN_0005b2be(4/5/0x2a)==3 → mode 4
  → FUN_00071272 (FOC current regulator) → TSG20 PWM
```

**Torque-sensor plausibility `FUN_00062948`** reads the THREE raw torque-sensor ADC channels `0xFEDF3174/76/78` (gp-0x4e8c/8a/88) vs refs `0xFEDF316C/6E/70`, bounds `tp+0x59ca/0x59ce`, delta limit `tp+0x59c6`; sets fault bits. Hardware ADC values — **no injection point** here.

**Arbitration API (pinned):** status bitfield `0xFEDF1288`; `FUN_000197d0(n)` = get bit n; `FUN_000197b8(n)` = `|= 1<<n` (set bit n); `FUN_000197ea` = clears bit 0. Known bits: **0** (state handler), **4** (torque-sensor plausibility fault), **9** (resolver-correction gate), **15** (motor-shell enable gate). DTC/fault query `FUN_0005b2be(code)` (`==3` = active).

### 0.4 LKAS merge point — ~~firm conclusion: data-blocked~~ **SUPERSEDED 2026-05-25 (cont.) — see §0.5, GAP 1 now CLOSED** [V]
> **⚠ This section's "data-blocked / cannot be recovered statically" conclusion is WRONG and is superseded by §0.5.** The error: it traced the **shared RX scratch** `0xFEDF68CC` (`gp-0x1734`), which the assist chain genuinely never reads — but that is *not* the LKAS-specific buffer. The dispatcher copies each frame to a **per-slot destination buffer** whose pointer table is at **absolute flash `0xB739C`** (NOT a `tp`-relative table in absent memory). For CAN `0xE4` that destination is **`0xFEDF6BD8`**, and it **is** read — by `FUN_00021724` → `FUN_00052676`. The full path is now traced end-to-end. Original text preserved below for history.

The ENTIRE driver-assist + motor + FOC chain above was decompiled (`0x6651e, 0x6634e, 0x65eda, 0x62948, 0x65afe, 0x68f52, 0x71272`) and **NONE read the LKAS staging `0xFEDF68CC` (`gp-0x1734`)** — which also has 0 absolute xrefs. The LKAS frame is consumed only via the dispatcher `FUN_0001ddd0`'s **routed copy**, whose destination pointer comes from a ~~**`tp`-relative route table in the absent `0xF8000+` partition**~~ **[CORRECTED: route table is at absolute flash `0xB739C`, present in `code.bin` — see §0.5]**. Therefore:
- LKAS is **NOT** summed into driver column torque (that path is raw ADC + plausibility, hypothesis A ruled out). It is a **separate demand merged downstream** of the assist curve (hypothesis B).
- The exact merge instruction **cannot be recovered statically** — it reads a routed buffer at an address that lives in absent memory.
- **V10A re-explained:** doubling the driver assist curve (`0xC4A42`) did not strengthen LKAS because LKAS doesn't ride that curve; it killed LKAS by tripping the **override/plausibility/state-machine** (drops assist mode `0xFEDF319B` to 1, or to fault mode 4 via `FUN_0005b2be`/`FUN_000197b8`), which gates LKAS actuation.

**To close it — bench RAM capture (the only path):** log `0xFEDF68CC` (LKAS in), `0xFEDF1288` (status bits), `0xFEDF319B` (assist mode), the demand floats `0xFEDF3048/44/4A/46` (= gp-0x4fb8/bc/b6/ba), and `0xFEDF4B14/4B18` (assist-row ptrs) while LKAS actuates, and watch where the LKAS value appears. Static analysis of these dumps is exhausted on the merge point. **[⚠ no longer needed for the merge point — closed statically in §0.5.]**

### 0.5 Session 2026-05-25 (cont.) — GAP 1 CLOSED: full LKAS command path traced statically [V]
Static analysis was **not** exhausted — §0.4 traced the wrong buffer. The CAN RX framework is a generic per-message router; the LKAS-specific buffer and its consumer are now pinned. Confidence markers per §"Trust calibration". Functions renamed in the live Ghidra project with `s_`/`m_`/`w_` = strong/medium/weak inference prefixes.

**CAN RX routing framework (all tables absolute, in `code.bin`) [V].** The dispatcher `FUN_0001ddd0` (`s_can_rx_dispatch`) routes each received frame using a set of **slot-indexed tables**. The route/dest and handler tables are referenced by **absolute literals** in the decompiled code (not `tp`-relative), so they are fully present in `code.bin`:

| Table | Flash addr | Indexed by | Holds |
|---|---|---|---|
| mailbox → slot | `0xB70F4` | `mailbox − 0x20` (u16) | logical slot index (24 RX mailboxes `0x20–0x37`) |
| mailbox CAN-ID | `0xB733C` | `mailbox − 0x20` (u32) | FCN MID register value; **stdID = `value>>18` = `high16>>2`** |
| copy length | `0xB7124` | slot (byte) | DLC bytes to copy |
| **route dest ptr** | **`0xB739C`** | slot (u32) | **RAM dest buffer pointer** (non-null = enabled) |
| dispatch handler | `0xB73FC` | slot (fnptr) | per-slot handler (null for slots 0–22 = frame-copy path; 23+ = diag) |
| post-dispatch cb | `0xB745C` | slot (fnptr) | "fresh" callback (`FUN_0001debc`) |

Base for the relative-rendered tables is `0xB7000` (NOT the `0xF8000` calibration base — a separate base register/context; the load-bearing addresses `0xB739C`/`0xB733C` also appear as **absolute literals** so they don't depend on this base).

**STEER_TORQUE landing [V].** Decoding `0xB733C` with `stdID = high16>>2` yields a coherent Honda standard-ID set (`0x1EA,0x1D0,0x1B0,0x1A4,0x17C,0x158,0x13C,0x130,0x94,0xE4`, …). Mailbox `0x36` (table entry `0xB7394` = `0x03900000` → **`0xE4`**) → slot table `0xB70F4[22]` = **slot 17** → dest `0xB739C[17]` = **`0xFEDF6BD8`**. So the LKAS frame is copied to `0xFEDF6BD8` (NOT `0xFEDF68CC`, which is the shared pre-route scratch). STEER_TORQUE (int16 BE) = `bytes[0:1]` at `0xFEDF6BD8/9`; request/flag bits at byte2 `0xFEDF6BDA` and byte4 `0xFEDF6BDC`.

**The end-to-end command path (each hop verified by data-flow on gp-resolved RAM vars; absolute addrs):**
```
CAN 0xE4 STEER_TORQUE (int16 BE)
 → 0xFEDF6BD8                         dispatcher routed-copy dest (slot 17)
 → FUN_00021724 (s_get_lkas_steer_torque_be)  reads byte0/byte1 in IRQ-crit section, returns CONCAT11 = BE int16
 → FUN_00052676 (s_lkas_process_steer_cmd)    [INSTRUCTION-VERIFIED: sxh; shl 2; subr r0 = ×−4; clamp(-0x4000,+0x4000)]
        setpoint = clamp(STEER_TORQUE × −4, ±0x4000)  →  0xFEDF1652 (gp-0x69ae)
        (fault/inhibit paths write sentinel 0x7FFF; flag bits from byte2/byte4; 500-tick validity timeout)
 → FUN_00028ea6 (m_steer_torque_arbitration)  reads 0xFEDF1652. NOT a passthrough — table-driven:
        • 8 interp-table pointer arrays 0xCB844 / 0xCBA74 / 0xCB924 / 0xC9A88 / 0xCB7D4 / 0xCBB54 /
          0xCBC34 / 0xCBAE4 (each: u16 breakpoint[x] + value[y] arrays, linear LERP; index = mode/gear byte)
        • speed/signal-dependent LIMIT on the LKAS setpoint (|setpoint| ≤ table_out)
        • summed with the driver torque-sensor assist path; integrators (Q10/Q15), rate limits, blend gains (0x400 = unity)
        → final gated cmd 0xFEDF14C4 (gp-0x6b3c)
 → FUN_0002b422 (m_steer_torque_limit_and_pack) rate-limits, packs a command struct {flag,state,torque,blends,0x400}
 → FUN_00025c32 (m_motor_cmd_distribute_clamp)   per-channel state machine; FINAL CLAMPS ±0x4000/±0x2800/±0x384/±0x4e20;
        writes per-channel motor cmd buffers 0xFEDF1D20 (gp-0x62e0) + gain buffers (gp-0x6200 …)
 → FUN_00026c80 (m_motor_cmd_mixer)              reads those per-channel buffers; produces motor torque/current REFERENCE
        run from periodic task FUN_0002214a (= the doc's "1ms scheduler"; my w_steer_control_task)
 → [FOC current loop — already mapped in §1④/§0.3]  consumes the q-current reference:
        ADC ISR FUN_0006404c → FUN_00071272 (Park/Clarke/PI/SVPWM)
 → TSG20 PWM  FUN_0006c5ce  CMPU/CMPV/CMPW = 0xFFFFCCB0/B4/B8  = MOTOR
```

**This connects the doc's two ends.** The LKAS path (above) and the driver-assist path (§0.3 slot-3 task) are **sibling tasks under the same 1 ms scheduler `FUN_0002214a`**; both deposit demands that the mixer/FOC turn into the q-current reference and TSG20 duties. This **confirms §0.4's hypothesis B** (LKAS is a separate demand merged downstream of the assist curve) and **locates** the merge — it was never data-blocked, the prior trace just followed the scratch buffer.

**Open remainder [OPEN, narrow]:** the exact shared variable handing `m_motor_cmd_mixer`'s output to the FOC q-current reference (`FUN_00071272`) was not pinned this session; and the live numeric table *contents* behind the `0xC9A88–0xCBC34` pointer arrays still sit in the editable `0xC4000–0xFD0B8` band (their byte values are present in `code.bin`, role-mapping per §3/§4 caveats).

**Tooling note [V]:** CALL xrefs now resolve in this project (`get_function_callers`/`callees` returned real results, e.g. `FUN_00021724`←`FUN_00052676`, `FUN_00026c80`←`FUN_0002214a`) — §0.1's "CALL xrefs return 0" no longer holds (auto-analysis appears to have been re-run since). Data-flow on gp-resolved vars remains the primary method. Several motor-stage functions (`FUN_00025c32`, `FUN_00026c80`) **fail to decompile** with `Field TAUJ0RSF does not fit in structure TAUJ0_registers_t` — use `disassemble_function` for those (the `TAUJ0_registers_t` data-type def has an indexing edge case; not fixed this session to avoid project-wide type churn).

### 0.6 Session 2026-05-25 (cont.) — arbitration internals decoded + the x=4096 bottleneck chain + plot-C correction [V]

Disassembled `m_steer_torque_arbitration` (`0x28ea6`), the distributor `m_motor_cmd_distribute_clamp` (`0x25c32`), and the mixer `m_motor_cmd_mixer` (`0x26c80`) against the live `code.bin`. Full writeup in `memory/reference_accord_arbitration_limit_family.md`; figures `accord_demand_pipeline_v2.png`, `accord_bottleneck_and_limit_family.png`, `accord_plotC_by_mode.png` (generators `accord_aggregator_analysis.py`, `accord_plotC_by_mode.py`).

**Distributor lane clamps [V instr]:** struct `r6+2/+4/+6/+8` → clamp **±0x4000 / ±0x2800 / ±0x384 / ±0x4e20** (code literals @ `0x25c80/9c/b8/d4`); LKAS rides lane **+4 (±0x2800)**. Blend gains `r6+a/+c/+e` clamped **≤0x400** (unity, Q10). Byte `r6+1` = a 6-state per-slot state machine (jump table @ `0x25d18`).

**Mixer [V disasm]:** cross-slot **running MAX** on some lanes, **SUM** on others → accumulators `gp-0x3d70..3d98`; **final clamps ±0x4e20 (`0x2739e`), ±0x6400 (`0x27772`), ±0x2800, ±0xe10**. Out → `0xFEDF1502` → shaper `FUN_00042af8` (**clamp ±0x2000**).

**Arbitration limit = a FAMILY of LERP curves, NOT a single 1-D list [V].** The setpoint `0xFEDF1652` is symmetrically clamped to `±LERP(curve[mode])`. **8 pointer arrays** (`0xCB844/CBA74/CB924/C9A88/CB7D4/CBB54/CBC34/CBAE4`) are indexed by the mode/gear byte `gp-0x674e`; a 2nd selector `axis<0x7d01(=32000)` blends a hi/lo pair. **CRUCIAL: the pointer arrays at `0xC9A88–0xCBC34` point to LERP tables that live at `0xE4xxx`, NOT in the `0xC4000–0xFD0B8` band** (so §0.5's "open remainder" conflated the pointer-array address with the table-content address — the contents are at `0xE4000+`). Per-gear data finding:
- `cb844` (the hard setpoint magnitude limit, renamed `g_pArbSetpointLimitCurves`) is **mode/gear-INVARIANT** — all 12 gear slots @ `0xE4180+mode*0x28` are byte-identical (const **15360**, breakpoints `[3200..8320]`); entries 6-11 mirror 0-5 (`+0x1000`).
- `c9a88` (`g_pArbCurve_c9a88`, a 0..255-indexed torque shaping curve) **DOES vary by gear**: same axis `[0,12,20,24,32,64,96,128,160,240]`, value rows gear0 `[0,16,28,34,48,92,124,148,162,172]` / gear1 `[0,24,42,50,62,100,126,154,166,172]` / gear2 `[0,11,26,35,56,129,158,172,174,180]`.

**The x=4096 (full-scale LKAS) bottleneck chain [V]:** `setpoint = clamp(x·−4, ±0x4000)` (`s_lkas_process_steer_cmd 0x52676`) → at x=4096 lands **exactly on −0x4000** (first hard wall, code literal) → **arb limit ~15360** (first *data-driven* cut, table read) → distributor +4 **±0x2800=10240** → mixer **±0x2800** → shaper **±0x2000=8192** (tightest / binding final wall).

**CORRECTION to §3a / old `torque_transform_x4096.png` panel C:** the `0xC6518/0xC6534` speed→limit row is **NOT read by the arbitration code** (the live limit is the `0xE4xxx` family). See the inline note added to §3a.

### 0.7 Session 2026-05-25 (cont.) — gate/shaper dual range-check, the ±0x3FFF window ceiling, mixer lane pinned, V11A built [V]

Disassembled the mixer tail + gate `FUN_00042ac6` + shaper `FUN_00042af8` to verify the `TORQUE_MOD_V0.md` recipe before building. Full writeup `memory/reference_accord_lkas_window_ceiling.md`; builder `build_v11_tva.py`.

- **Mixer LKAS lane pinned [V instr].** Of the four ±0x2800 clamp blocks in `m_motor_cmd_mixer`, the LKAS lane is the **`0x27442` block** (clamps the `gp-0x3d8c` accumulator → `r26`). `r26` is preserved untouched to `0x277f2: mov r26,r6; sxh; jarl FUN_00042ac6` — the exact value handed to the gate. The other three (`0x26ea0`, `0x26ec4`, `0x276de`) are NOT the LKAS lane.
- **Gate `FUN_00042ac6` [V].** `addi 0x2800,r6,r13; addi -0x5001,r13,r0; bnc; movea 0x7fff,r0,r15; st.h r15,-0x6afe[gp]`. i.e. `|r6|≤0x2800 ? r6 : 0x7FFF` → `0xFEDF1502`. Confirmed.
- **Shaper `FUN_00042af8` is a DUAL range-check, not a plain ±0x2000 clamp [V].** At `0x43ae0` it reads `0xFEDF1502` and re-runs the SAME idiom (`0x43ae8 addi 0x2800; 0x43aec addi -0x5001; 0x43af0 cmovc 0x0,r13,r12`) → **anything outside ±0x2800 (incl. the 0x7FFF sentinel) COLLAPSES TO 0**, then a symmetric runtime limit `r10=*(gp-0x4f64)=0xFEDF309C` (`0x43af6`, itself zeroed if >0x2800), then the final ±0x2000 clamp (`0x43b0e-b1c`). **`TORQUE_MOD_V0.md` modeled only the ±0x2000 clamp and missed `0x43ae8/aec`.**
- **HARD value-edit ceiling = ±0x3FFF (~2.0×) [V].** Both range-checks use `+0x2800 / -0x5001`; widening to ±W needs 2nd imm `-(2W+1)`, and `W=0x4000` → `-0x8001` overflows imm16. So `0x3FFF` is the max. **The earlier "≈3.99× by value edit" (§0/§4 of the mod doc, and `reference_accord_demand_aggregator_pipeline`'s "±0x2000" framing) understated the gate/overstated the storage limit.** 2.5× (`0x5000`) and 3× (`0x6000`) need the comparison sequences restructured (code rewrite), and are further gated by the runtime `0xFEDF309C`.
- **V11A built [V].** `build_v11_tva.py` → `39990-TVA-A160-V11A-LKAS-2x-corrected-…rwd`: widens distributor +4 / mixer `0x27442` / gate / shaper-input / shaper-final (±0x3FFF window, ±0x4000 clamps) + arb `0xE4180`+mirror `0xE5180` (15360→16384). 3 CRC blocks recomputed (`0xC4FFC`/`0xE4FFC`/`0xE5FFC`); **49/49 walk PASS, byte-diff = only intended sites.** Study artifact, unflashed. Whether it physically delivers 2× is empirical (the `0xFEDF309C` runtime limiter is unresolved).

---

## 1. The end-to-end path: CAN torque command → motor PWM [V endpoints]

```
① CAN INPUT  [VERIFIED + opendbc-cross-checked]
   STEERING_CONTROL  CAN ID 0xE4, DLC 5 ; STEER_TORQUE = signed16 bytes[0:1] big-endian, range ±4096
   (opendbc _bosch_2018.dbc; Accord 2018-22). EPS is the DBC 'EPS' receiver.
   FUN_0001cf30 programs HW MID filters; 0xE4 entry @ 0xB7394 -> RX mailbox 54
                    |
② RX EXTRACTION  [VERIFIED]
   FUN_0001df5c -> FUN_0001df1c -> FUN_0001ce68  copies the 8 frame bytes -> staging RAM 0xFEDF68CC
   STEER_TORQUE = *(int16_t big-endian*)0xFEDF68CC
                    |
③ DISPATCH  [VERIFIED — GAP 1 CLOSED 2026-05-25, see §0.5]
   FUN_0001ddd0: diag slots -> fnptr table 0xB73FC -> 0x21xxx  [DIAG, not LKAS]
                 other msgs -> frame-copied to per-SLOT dest buffer; ptr table @ 0xB739C (ABSOLUTE, in code.bin)
   CAN 0xE4 = mailbox 0x36 -> slot 17 (0xB70F4[22]) -> dest 0xFEDF6BD8.  STEER_TORQUE = int16 BE @ 0xFEDF6BD8.
   (route table is NOT runtime-bound/absent — earlier conclusion traced the shared scratch 0xFEDF68CC by mistake.)
                    |
③b LKAS PROCESS  [INSTRUCTION-VERIFIED, see §0.5]
   FUN_00021724 (getter) -> FUN_00052676:  setpoint = clamp(STEER_TORQUE × −4, ±0x4000) -> 0xFEDF1652
   -> FUN_00028ea6 arbitration (8 interp tables @ 0xC9A88..0xCBC34, speed-limit + assist sum)
   -> 0xFEDF14C4 -> FUN_0002b422 -> FUN_00025c32 (final clamps) -> per-channel cmd 0xFEDF1D20 -> FUN_00026c80 mixer
                    |
④ CONTROL LAW  [loop verified; mixer→q-ref handoff var not pinned]   <-- GAP 2 (narrowed)
   ADC-complete ISR FUN_0006404c (INTADCA0I1, EIIC=0x600)
     -> 0x6428e -> 0x65afe -> 0x711f8 -> 0x71272 -> 0x710d4
     -> d/q current setpoint + phase duties in RAM (gp-0x2bf0 / -0x2be0 / -0x2bd0)
   (FOC inner loop: rotor atan2 angle @0x6adfe (x2pi/16384) -> Park transform -> PI current reg -> SVPWM)
                    |
⑤ MOTOR OUTPUT  [VERIFIED]
   carrier-valley ISR FUN_0001492a (INTTSG20IVLY, EIIC=0x970) -> FUN_00061614 -> FUN_0006c5ce
     -> writes TSG20 CMPU/CMPV/CMPW = 0xFFFFCCB0 / 0xB4 / 0xB8  (÷51200.0 scale, period-clamped) = MOTOR
   commutation table @ tp-0x2d40 = 0xF52C0 — [⚠ "REAL in data.bin" probably WRONG, see §0-top CORRECTION; 0xFF in code.bin]
```

**Ruled OUT as the runtime torque path** [V] (these are the flash/integrity layer, not live control): the `0x8AD6C` block-base pointer table (45-block CRC chain) → block `0xC6000`; `FUN_0001c7c8` (flash programmer using CRC engine `0x6b8f4`); `FUN_00027802` (calibration range validator). The `0xCE0B2` assist-curve axis has **no runtime xref** — it is a stored/managed calibration block, not the live-read table.

### The two open gaps

- **GAP 1 — which handler consumes the staged `0xE4` torque. ✅ CLOSED 2026-05-25 (§0.5).** The dispatcher frame-copies `0xE4` to per-slot buffer `0xFEDF6BD8` (slot 17, dest-ptr table `0xB739C`, present in `code.bin`). Consumer = `FUN_00021724` → `FUN_00052676`: `setpoint = clamp(STEER_TORQUE × −4, ±0x4000)` → `0xFEDF1652` → arbitration `FUN_00028ea6` (table-driven) → … → mixer `FUN_00026c80`. The "RAM-resident/absent" belief was an artifact of tracing the shared scratch `0xFEDF68CC` instead of the routed dest. [CLOSED]
- **GAP 2 — narrowed.** The **LKAS-side** setpoint instruction is now pinned (`0xFEDF1652`, written by `FUN_00052676`). What remains [OPEN]: the exact RAM variable carrying `m_motor_cmd_mixer` (`FUN_00026c80`) output into the FOC q-current reference (`FUN_00071272`). [OPEN, narrow]
  - **Update 2026-05-25 (GAP 2 sharpened, NOT closed):** the mixer's principal output is now traced forward — `FUN_00026c80` → `FUN_00042ac6` → `0xFEDF1502` (mixed torque ±0x2800, 1 writer/1 reader) → shaper `FUN_00042af8` (clamp ±0x2000) → demand struct `0xFEDF16E0..16EA` (id 0x38c7, `FUN_0004613e`) → serializer `FUN_000564ce` → **CSIG0 clocked-serial dispatch `FUN_00016de6`**. So the principal command routes into a **serial message frame**, and a whole-image search finds **no `st` to `gp-0x2bf0`/`-0x2be0`** (the q/d-setpoint slots above). The "mixer → on-chip FOC q-ref" handoff is therefore **not corroborated** — it may be off-die over CSIG0, written via a non-gp base, or the q-ref offsets are approximate. The on-chip FOC→TSG20 motor drive (§1⑤) is still verified independently. Full trace + 10-slot demand-vector map in `memory/reference_accord_demand_aggregator_pipeline.md`.

---

## 2. Where the torque/assist tables live

| Region | Address | What | Notes |
|---|---|---|---|
| **Calibration band** | `0xC4000–0xFD0B8` | 1,378 candidate tables: axes, paired curves, 2D maps, float blocks | In `code.bin`, editable. Mostly CRC-protected (recompute trailer on patch). |
| **Live control params** | `0xFD8C8–0xFE189` | control thresholds / gains / limits | **`0xFF` in our dump — see Hard Ceiling.** |
| **Motor params** | `0xFE000+` | R / L / flux / Park constants | **`0xFF` in our dump.** |
| **Commutation table** | `0xF52C0` | 3-phase commutation | ⚠ **2026-05-25: probably wrong** — "real in data.bin" used the bad `0xF0000` mapping; re-derive (see §0-top CORRECTION). |
| **Adaptation store** | `data.bin` @ `0x02000000–0x02007FFF` | learned/adapted runtime state | ⚠ **2026-05-25:** the `[id:2][addr:2][value:4]` record shape is **suspect** — the "`value:4`" was almost certainly the 4-byte **tag word** (`0x00000000`/`0xFFFFFFFF`), not a learned value. Re-derive from the de-tagged 32 KB. The "data-flash, no lookup tables" gist is plausible (0x02000000 = data-flash region) but the structure needs redoing. |

The calibration band is reached by the control code through a **descriptor block**, not direct address construction (which is why the `0xC6xxx` tables have no direct `movhi` xref):
`0xFD000 = 0x000C6000` (pointer to block `0xC6000`), `0xFD004 = 2` (count), `0xFD008 = 0x000FD020` (→ packed descriptor list mapping logical param IDs → `{block, offset, len}`). [V]

---

## 3. The verified-value curves (byte-confirmed, role LIKELY) [V values]

All live in calibration block `0xC6000` (CRC-protected — recompute `+0xFFC` if patched), linked to the control region via the `0xFD000→0xC6000` descriptor.

### 3a. `0xC6518 → 0xC6534` — speed-dependent LIMIT / current cap (float32)
> **⚠ CORRECTED 2026-05-25 (§0.6): NOT the live LKAS-setpoint limit.** Disassembly of `m_steer_torque_arbitration` shows the setpoint limit comes from the mode/gear-indexed `0xE4xxx` LERP family (pointer arrays `0xCB844`…), **not** this `0xC6534` row. This float curve has no confirmed runtime read on the LKAS path; its "live speed-limit" role is **downgraded** to a stored/managed or other-subsystem curve. The decode below is still byte-accurate; only the role is corrected.
- **Speed axis** `0xC6518` (km/h): `[0, 10, 25, 50, 80, 120, 200]` → mph `[0, 6.2, 15.5, 31.1, 49.7, 74.6, 124.3]`
- **Limit row** `0xC6534`: `[12000, 10000, 10000, 7000, 7000, 7000, 7000]`
- Shape: high at standstill, −42% by ~31 mph, flat to highway — a **speed-dependent assist/current-limit taper**. Units of the limit unknown (mA / torque-count / cap). [role OPEN, NOT live LKAS limit]

### 3b. `0xC6BA0 → 0xC6BD4` — breakpoint-dependent GAIN (float32)
- **Axis** `0xC6BA0`: `[0, 34, 64, 85, 100, 120, 140, 157.6, 173.6, 191.6, 208.4, 228, 477.6]`
- **Gain row** `0xC6BD4`: `[0.878, 0.887, 0.958, 1.0348, 1.0573, 1.0589 ×8]` — near-unity saturating gain.
- Axis units uncertain (`477.6` max atypical for km/h; could be motor rpm / frequency / temperature). [LIKELY gain; axis units OPEN]

### 3c. `0xC4A42 / 0xC4A6E` — Honda assist-gain archetype (int16 pair) — in **unprotected** block `0xC4000`
- `0xC4A42`: `[0, 10, 34, 82, 160, 239, 374, 717, 825, 882, 910, 928]`
- `0xC4A6E`: `[0, 10, 26, 62, 98, 165, 293, 718, 831, 887, 910, 926]`
- Monotonic saturating pair — the classic Honda input→assist gain shape. Not speed-indexed (X = input breakpoint index). **No CRC recompute needed (unprotected block).** [LIKELY]

---

## 4. The structural inventory (1,378 candidates) [LIKELY / structural]

`scan_calibration.py` over `0xC4000–0xFD0B8` (the full per-candidate dump is `scan_calibration.json`):

| Type | Count | Meaning |
|---|---|---|
| int16 monotonic axes (standalone) | 136 | breakpoint axes (speed / current / steer-rate / rpm) |
| paired int16 curves | 506 | Y-rows of 2D maps; LH/RH or forward/return variants |
| 2D clustered int16 | 275 | torque-vs-condition lookup grids |
| 2D repeated-rows int16 | 454 | maps with identical rows (template-emitted) |
| float arrays | 7 | the §3 float curves + a few constants blocks |

1,313 of 1,378 sit in **CRC-protected** blocks; 65 are free (concentrated at `0xC4000`, `0xF9000`, `0xFA000`). Highest-priority trace candidates beyond the verified seeds:

- `0xC52CA..0xC54C2` (block `0xC5000`) — 8 paired curves structurally identical to the `0xC4A42` archetype.
- `0xCE0B2..0xCE12A` + mirror `0xCF0B2..0xCF12A` — a 4-element family sharing first row `[0,150,350,600,1000,1500,2500,5000]`; smells like a multi-condition assist family. (Note: `0xCE0B2` has **no runtime xref** — managed/stored, not live-read.)

**Encoding of a calibration curve** (`0xC5000` block, representative):
```
u16 N | N×u16 X-breakpoints (strictly increasing) | N×s16 Y-values | u16 0x0000
```
Float constants in the same blocks decode to clean physical values (gains 0.04–1.06, limits in the thousands).

### The `+0xFF6` chain pointer (patch-scope caveat) [V structural]
Each CRC-protected 4 KB block carries, at `+0xFF6..+0xFF9`, a `[next_protected_page:u16 LE][own_page:u16 LE]` pointer. For 44 of 48 blocks `next = own + 2`; the other 4 (`0x00000`, `0x08000`, `0xC6000`, `0xF8000`) point to the actual next protected block — i.e. it is a **global linked list across the 48-block CRC chain**, not pairwise mirror metadata. Several blocks have near-identical bodies (`0xCE000↔0xCF000`, `0xD0000↔0xD4000`, `0xD1000↔0xD5000`, the `0xDA000..0xE1000` run). **Runtime role OPEN.** Until traced, patch only your target block (and recompute its CRC) rather than mass-mirroring.

---

## 5. HARD CEILING — the live-control numbers are NOT in our dump [V]

The block the live steering/motor loop actually reads — **`0xFD8C8–0xFE189`** (control thresholds/gains/limits) and **`0xFE000–0xFE189`** (motor R/L/flux/Park) — is `0xFF` in `code.bin`. ~~and `data.bin`~~ **⚠ 2026-05-25:** the "and `data.bin`" half is invalid — `data.bin` is 32 KB at `0x02000000` and never covered this region (see §0-top CORRECTION), so it neither confirms nor denies these slots; the conclusion rests on `code.bin` alone. The control loop reads `disp[tp]` flash directly with `tp = 0xF8000`; those addresses are in the `0xF8000+` second-flash partition our dump does not capture.

**Consequence:** the speed-indexed curves in §3 are byte-verified and descriptor-linked, but the *live-read role* is LIKELY, not proven, and the actual numeric control parameters cannot be extracted from the binaries in hand. To finish the semantic mapping and to touch the live control parameters you need either:
1. a raw dump of the `0xF8000–0xFFFFF` second-flash partition, or
2. a stock TVA `.rwd` covering those addresses,

then resolve the `0xFD020` descriptor list (which logical ID selects the `0xC6000` speed curves) and decompile the slow assist task that interpolates them.

---

## 6. Practical guidance for a torque modification

- **Editable today:** the `0xC4000–0xFD0B8` calibration tables (§3, §4). These are real, byte-addressable, and packageable via `analysis-2020accord/old_tools/build_stock_tva_v9.py`. Whether a given table is *live-read* vs *stored/managed* is the open question — the §3 `0xC6000` curves are descriptor-linked (strongest), the `0xCE0B2` family is managed-only.
- **Not editable from `code.bin`:** the `0xFD8C8+` / `0xFE000+` live control params (§5) — they're not in the dump and not in the flashed window's captured bytes.
- **After any edit:** recompute the CRC-32 trailer of each touched protected block, then run the bootloader CRC walk (`verify_bootloader_crc.walk`) — see `HOW_TO_BUILD_ACCORD_TVA_RWD.md` §5/§7. A build that fails the walk will be rejected by the ECU with NRC `0x72`.
- **Validation of feel is empirical.** Per kit policy, once a build is flashed the operator's road feel overrides abstract analysis. There is no bench model of the assist curve here.

---

## 7. Key offsets (torque path)

```
0x0E4 (CAN ID)  STEERING_CONTROL ; STEER_TORQUE = s16 BE bytes[0:1]
0xFEDF68CC      SHARED RX SCRATCH (pre-route, overwritten every frame) — NOT the LKAS buffer
0xFEDF6BD8      ** LKAS STEER_TORQUE routed buffer (slot 17, CAN 0xE4) ; int16 BE @ +0/+1; flags @ +2,+4 **  [§0.5]
0xFEDF1652      LKAS torque setpoint = clamp(STEER_TORQUE×−4, ±0x4000)  (gp-0x69ae, written by FUN_00052676) [§0.5]
0xFEDF14C4      arbitration final gated cmd (gp-0x6b3c, FUN_00028ea6→FUN_0002b422) [§0.5]
0xFEDF1D20      per-channel motor torque cmd buffer (gp-0x62e0, FUN_00025c32→FUN_00026c80) [§0.5]
0x0B7394        mailbox CAN-ID table entry for 0xE4 (=0x03900000, stdID=high16>>2) -> mailbox 0x36 (54)
0x0B70F4        mailbox→slot table (idx = mbox−0x20); [22]=slot 17
0x0B739C        ** route dest-ptr table (slot-indexed, ABSOLUTE in code.bin); [17]=0xFEDF6BD8 ** [§0.5]
0x0B73FC        per-slot dispatch handler fnptr table (null slots 0–22 = frame-copy; 23+ = diag)
0x0B745C        per-slot post-dispatch callback table (FUN_0001debc)
0xC9A88..0xCBC34 LKAS arbitration interp-table POINTER ARRAYS, mode/gear-indexed (gp-0x674e); point to LERP tables @0xE4xxx [§0.5/§0.6]
0x0E4180        g_pArbSetpointLimitCurves[0] (cb844): bp[3200..8320] -> const 15360; mode/gear-INVARIANT (all 12 slots identical) [§0.6]
0x0E4000        g_pArbCurve_c9a88[0]: bp[0..240] shaping curve; VARIES by mode/gear (gear0/1/2 differ) [§0.6]
0x021724        s_get_lkas_steer_torque_be (reads 0xFEDF6BD8/9, returns BE int16) [§0.5]
0x052676        s_lkas_process_steer_cmd (×−4, clamp ±0x4000 → 0xFEDF1652) [§0.5]
0x028EA6        m_steer_torque_arbitration (table-driven limit + assist sum) [§0.5]
0x02B422/0x025C32/0x026C80  limit-pack / distribute-clamp / mixer [§0.5]
0x01CF30        CAN mailbox config (FCN0 @ 0xFF488000) — HW MID filters
0x01CE68        universal RX extractor -> shared scratch 0xFEDF68CC
0x01DDD0        RX dispatcher (0xB73FC fnptr=DIAG; 0xB739C route table = LKAS, in code.bin) [GAP 1 CLOSED §0.5]
0x06404C        motor control-law ADC ISR -> 0x6428e->0x65afe->0x711f8->0x71272->0x710d4 [GAP 2]
0x06ADFE        rotor atan2 angle (x2pi/16384)
0x01492A        carrier-valley ISR -> 0x61614 -> 0x6c5ce
0x06C5CE        3-phase PWM duty emitter -> TSG20 CMPU/CMPV/CMPW = 0xFFFFCCB0/B4/B8 = MOTOR OUTPUT
0x0F52C0        commutation table (tp-0x2d40) — [⚠ "real in data.bin" probably WRONG; see §0-top CORRECTION]
tp (r5)=0xF8000 calibration base, set @0x9152, never reloaded in motor cluster
0xFD000         descriptor: =0x000C6000 (ptr to 0xC6000), count=2 @0xFD004, list @0xFD008=0x000FD020
0xC6518/0xC6534 speed axis [0,10,25,50,80,120,200] km/h -> limit [12000,10000,10000,7000x4]  (NOT the live LKAS limit — see §3a/§0.6 correction)
0xC6BA0/0xC6BD4 axis -> gain [0.878..1.059]
0xC4A42/0xC4A6E int16 assist-gain archetype pair (unprotected block 0xC4000)
0xFD8C8-0xFE189 LIVE control thresholds/gains/limits — ABSENT from our dump (Hard Ceiling)
0xFE000+        LIVE motor R/L/flux/Park params — ABSENT from our dump
```
