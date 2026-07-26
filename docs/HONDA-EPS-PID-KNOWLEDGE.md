# Honda EPS Tuning — Canonical Reference

*Synthesized from a 26-day private Discord DM (2026-04-25 → 2026-05-21, 4,989 messages, 5 active hands) of the only working Honda EPS torque-mod research group. This document is the working reference for finalizing a PID tune on a Honda Civic running openpilot / sunnypilot stronger steering, and for any future agent picking up Honda EPS modification work without re-deriving the field.*

---

## 1. If You Read Nothing Else

1. **openpilot sends `0–3840` on CAN `0xE4` STEER_COMMAND; stock Clarity EPS clamps the torque-table X-axis at `1663` (rows 0–1) or `1774` (rows 2–6). Every CAN request above ~43% normalized demand collapses to the same internal value.** This was the genesis insight (`@vote_for_nobody 2026-04-26 01:55: "right now the top 53% of our requests from op saturate our eps — that is a glaring problem!"`). It re-explains every "turn lockin / slow unwind / weak feel" report previously attributed to PID gains. **If you tune PID without first confirming your firmware's actual top X value, you are tuning into a wall.** Civic-side verification is open as of corpus end. **Strong** (binary-verified, multi-driver reproduced).

2. **Sunnypilot defines the Civic twice in `interface.py`; the sunny block at `TorqueBP/TorqueV = [[0, 3840], [0, 3840]]` silently wins over any block you add lower in the file.** `@brettpakkala 2026-04-29: "When I put my TorqueBP/V at 1663 a couple days ago remember when I showed the video of the really slow steering and I couldn't understand why? Looks like the entire time we need 3840 too… except we've been running it without realizing"`. **This burned 2+ days of false hypothesis-chasing.** Before believing any current value, `grep` your interface.py for duplicate Civic blocks and confirm which one applies. **Strong** (in-channel rlog-confirmed).

3. **`--no-checksum` is a brick gun, but it is *required* for development.** The flag bypasses the outer flasher checksum, but on-device boot-time checksum bytes are **also** validated at every boot. A flash with `--no-checksum` and a malformed payload **reports success and bricks at next ignition**. 2 of 8 group members have bricked their primary-car EPS this way. The brick is silent: CAN may respond initially from RAM, then go dark after power-cycle. Recovery sequence (proven): **buy a used EPS off eBay, plug-and-play.** UART boot-mode is theoretically possible but nobody has fully recovered via this in-corpus. **Strong** (3 confirmed brick events).

4. **The upstream-of-rate-limiter PID lever is the right one.** `@vote_for_nobody 2026-05-20: "for the clarity there is a P+I filtering, which are 2 separate tables … but i leave those alone, spent about a week trying to tune those table for faster steer rates [then] figured out could scale the raw CAN torque command value because its send to the rate limit part of the firmware separately from the torque table"`. **Don't sink a week tuning P+I filter tables — the actual lever is upstream of them.** Same expected to apply to Civic. **Medium** (Clarity-confirmed, Civic-untested).

5. **`kf=0.5` for the torque controller is in a different units universe than `kf=0.00006` for the PID controller.** If you accidentally carry over a torque-controller kf value into a PID controller, you will be 4 orders of magnitude off. firestar4430's only hard floor: `kP ≥ 0.6`. Lateral-accel ceiling: 4.5 m/s² (joystick test), 4.0–4.2 m/s² (typical observed). Avoid `off_policy_v10` model (reverted for oscillation); use `popV2` or `tcpv3`. **Strong** (firestar oracle quote + multi-driver corroboration).

6. **Cache-stuck params is the #1 silent footgun.** `@brettpakkala 2026-04-28: "Silly TorqueBP and TorqueV params were stuck in the cache and never reloaded … I changed the file again with a placeholder comment on one line of code and it forced the device to recompile"`. If a gain change has no effect on car behavior, suspect this **before** you assume the gain doesn't matter. Force-recompile trick: add a no-op comment somewhere in the path. **Strong**.

7. **"There is no real bootloader."** Both Clarity and Acura RDX dumps show the dedicated boot area (`0x0000–0x3FFF`, 32 KB) is **100% `0xFF` — Honda never wrote one**. The actual boot-equivalent code lives in user-area `0x0000–0x3FFF`. `.rwd` flashes write `0x4000+` so they cannot touch boot code naturally — **the "I bricked the bootloader" model the group operated under for weeks is wrong**. This reframes recovery: bricks are checksum-fail-at-boot, not boot-stub-erased. UART recovery should always be possible *in principle*, modulo getting checksums right. **Strong** (UART-dump verified on Clarity + RDX, vfn 2026-05-16).

---

## 2. Verify Before Tuning — Pre-Flight Checklist

Joey runs this before finalizing his Civic PID tune. Each item names what to verify, why it matters, and where to look.

| # | Verify | Why | Where to look |
|---|---|---|---|
| 1 | **Sunnypilot `interface.py` Civic block — what value is the EPS actually receiving?** | Sunny block silently overrides your additions; you may believe you sent 1663 while actually sending 3840 (chunk 4 burned 2 days on this). | `grep` interface.py for `CAR.HONDA_CIVIC` and `CAR.HONDA_CIVIC_BOSCH`. Check duplicate definitions. Confirm by reading actual logged CAN STEER_COMMAND value, not from source. |
| 2 | **Dom-clamp branch — does it actually have torque-mod code?** | firestar4430 2026-05-09: *"latest Dom has the torque modified code that I could find. Tunes just need adapted for my torque controller prolly."* This claim has not been independently verified by the group. | Diff `JamesL787/StarPilot:Dom` against stock interface.py + look for `EPS_MODIFIED` flag handling. |
| 3 | **Brett's asymmetric `STEER_DELTA_UP/DOWN` rate-limit fix pulled?** | First jitter fix that actually landed (2026-05-16). "removed 75–80% of jitter" on Clarity. Lives at `github.com/nrdr/openpilot mvl-staging-05.16.2026`. | Check your branch base. If you're not on or downstream of `mvl-staging-05.16.2026`, you don't have the asymmetric rate limit. |
| 4 | **What is your firmware's actual top X value?** | The 1663/1774 saturation finding is Clarity-confirmed. Civic top-X is structurally similar (`0x1371A=1663` for TEG) but **not driver-verified end-to-end**. If your X-axis caps lower than expected, you're saturating early and no PID gain will fix it. | UART dump or `eps_tool.py` parse of your stock .rwd. Look at `0x1371A` (Civic) / `0x1380E` (Clarity) constants. |
| 5 | **Fingerprint check: `honda_civic` vs `honda_civic_bosch`?** | Elusivejg admitted he "just changed both" — masking a real architectural difference (Nidec vs Bosch CAN routing). firestar's Civic Bosch tune is **only** valid on `honda_civic_bosch` fingerprint. | Run a route, check the fingerprint line in the openpilot log. |
| 6 | **Did the flash actually take? (Cache + flash silent-noop trap)** | Sequence: pull USB-C from comma → reconnect → set to off-road → **listen for the harness-box click** → reflash. If you don't hear the click, the flash may silently no-op. | Recovery is physical — listen for the relay click. Power-cycle the car up to 10 times if needed (vfn's empirical max). |
| 7 | **Lateral model — are you on `popV2` or `tcpv3`? NOT `off_policy_v10`?** | firestar 2026-05-03: *"if you're getting oscillation and running off-policy, 90% chance that's the model fyi lol — they reverted that model due to oscillation."* Phantom controller-oscillation reports trace back to bad models. | Check your model setting; verify the model isn't on the "reverted" list. |
| 8 | **EPS calibration after factory reset?** | brett 2026-05-16: *"if you're factory resetting then you're messing up your calibration though. So a drive for the first time will be required."* | After any factory reset, drive normally for a full route before evaluating tune quality. |
| 9 | **Panda firmware version mismatch?** | xriskybiscuit hit `CAN packet version mismatch: panda's firmware v0, library v4. Reflash panda.` on the C3X. The C3X *contains* a panda IC whose firmware drifts. | `panda_reflash.sh` or watch for the error in logs. |
| 10 | **kf in the PID controller is on the `0.00006` scale, not the `0.5` torque-controller scale.** | If you copy-pasted kf, you are 4 orders of magnitude off. | brett's PID experiment used `kp=0.3, ki=0.1, kf=0.00006`. |
| 11 | **LAF after a regime change must be rescaled.** | `LAF_new = (1663/3840) × LAF_old = 0.433 × LAF` when moving to the 0–1663 regime. `STEER_DELTA × 2.30`. Claude over-shoots LAF suggestions (gave 1.46 → "too aggressive imo"). | If you change CAN-axis alignment, apply the scaling formula before tuning anything else. |
| 12 | **Lat-accel under 4.5 m/s² in joystick tests?** | firestar's hard ceiling: 4.5 joystick, 4.0–4.2 typical observed in good tunes. Above this is the safety envelope; the project explicitly stays below it. | firestar's simulator scripts (not publicly shared); rough proxy: instrument peak lat-accel in plotjuggler. |

---

## 3. The Architecture — Canonical Map

### Five-Stage Pipeline (Clarity-canonical, structurally confirmed across Civic family)

```
[openpilot CAN: 0–3840]
         │
         ▼
[CAN 0xE4 STEER_COMMAND]
         │
         ▼  fn_29B6A: ÷4 (raw 3840 → 960, raw 1663 → ~415)
[RAM 0xFFF880E4]
         │
         ▼
[Torque-shaping (input clamp 0x1380E = 1663, the X-axis ceiling)]
         │
         ▼
[Main torque table — rows 0–6 × entries 0–8, 7×9×int16-BE]
         │
         ▼
[Speed-gain table @ 0x453B0 — sqrt ramp 2048×√(idx)]
         │
         ▼
[P+I controller fn_2A348]
         │
         ▼
[Output clamp 0x13910 = 1774 stock (raise toward 9011 = 55% of HW max)]
         │
         ▼
[Motor (HW init max 16384 @ 0x13642 — NEVER TOUCH)]
```

Stages that fight tunability:
- The X-axis clamp (`0x1380E = 1663` rows 0–1, `0x13810 = 1774` rows 2–6) saturates input.
- The output clamp (`0x13910 = 1774`) caps the output of P+I.
- The hardware ceiling (`0x13642 = 16384`) — touching it instant-faults LKAS.

**The SplitScale insight (2026-05-02, canonical Clarity fix):** Patch a single instruction at `0x29E0E` (`C6 3D → 46 00`, `SHLL r6` = ×2 on `cmd_08` after the split between table path and C-dynamic path). Table sees `0–1663`, rate-limiter sees `~3326` (close to old 3840). Restores fast feel without losing proportionality.

### Three Architectures (CPU + lineage split)

| Architecture | CPU | Cars | User-region size | LKAS injection path | Status |
|---|---|---|---|---|---|
| **Clarity** | Renesas SH72A0 (SH-2A) | Honda Clarity PHEV (TRW-*) | 0x60000 | `0xE4 → 0xFFF880E4 → 0x20C40 → 0x20F0E → 0x21CCA → 0x20F28 → 0x22084` | Best-mapped. Full master trace exists (`clarity_master_lkas_trace_UPDATED_2026_05_02_SplitScale.md`, 66KB). |
| **Civic family** | Renesas SH-2A | TGG (hatch), TBA (Nidec sedan), TEG (≈TBA shifted 0x160), TLA (4-ID header variant), Bosch | similar to Clarity | similar structure (`0xFFF87A98` ctx ptr, `0x1371A=1663` clamp) | High torque achievable. **Raising steer rates reliably introduces EPS noise. UNSOLVED as of 2026-05-20.** |
| **RDX/TJB** | Renesas SH-2A | Acura RDX 2019–21 (TJB-A030), Odyssey board variant | 0x80000 | thedordo physically dumped; AI-trace **could not find a reference to `0xE4`** in the dump | New territory. 48 duplicate cal banks at `0x55550` (0x180 stride). Drive-mode block at `0x5C952`. |
| Pilot / Accord | Renesas V850 | Honda Pilot 2019 (TLA), Accord 2020 Touring | unknown | not characterized | Separate architecture. mmmorks/openpilot has script for this. Unfinished territory. |

### "No real bootloader" reframing (2026-05-16, vfn)

| Region | Content | Touchable by .rwd? |
|---|---|---|
| **Boot area (separate region, read by different UDS cmd)** | 100% `0xFF` on both Clarity and RDX. Honda never wrote one. | N/A (separate physical region) |
| **User-area `0x0000–0x3FFF` (32 KB)** | The actual boot-equivalent code (SH-2A code islands in 0xFF ocean). Includes checksum routine. | **NO** — .rwd flashes always start at `0x4000`. |
| **User-area `0x4000+`** | Byte-for-byte unencrypted .rwd payload. | YES — this is the modifiable region. |

`flash_address = cal_offset + 0x4000` is the universal mapping rule for SH-2A Honda EPS. So an offset like `0x55550` in the cal file equals `0x59550` over UDS. Constantly trips people up when reading thedordo's RDX map.

### Three Chassis Lineages

- **Clarity (best-mapped):** ClarityMax family (`V2.0` → `V2.1` → `V2.2` → `V2.3.2 TeslaLike` → `4.x`).
- **Civic family:** TGGA120 (elusivejg's hatch), TBA-C020/A030 (Peter's Bosch sedan), TEGA010 (≈ TBA shifted 0x160), TLA-A040 (xriskybiscuitx, 4-ID header variant).
- **RDX (in progress):** TJB-A030 (2019–21). Note: **22+ RDX is TJB-A070; 25 RDX is TJB-A210** (driven up by an EPS recall, per MVL). thedordo's A030 work does NOT transfer forward.

---

## 4. CAN Map

### Live CAN bus addresses

| ID | Name | Bus | Direction | Notes |
|---|---|---|---|---|
| `0xE4` (228 dec) | STEER_COMMAND / STEER_TORQUE_REQUEST | F-CAN (panda BUS 1, sometimes 0 or 2) | OP/panda → EPS | Signed int. **opendbc shows `228` decimal — convert to `0xE4`** before grepping firmware. Same address across Clarity / Civic Nidec / Civic Bosch / Pilot / Acura RDX. |
| `0x18DA30F1` | UDS tester→EPS request (extended 29-bit) | panda BUS 1 | tester → EPS | ISO-TP framed UDS service IDs |
| `0x18DAF130` | UDS EPS→tester response | panda BUS 1 | EPS → tester | mirrored |
| `0x194` | (referenced in Honda Nidec safety hook) | F-CAN | — | Panda safety check passes `controls_allowed` only |

**Bus-discovery ritual:** `eps-update.py --dry-run -b 0`, `-b 1`, `-b 2`. Exactly one returns `tester present ok` + F181 part number. Use that bus for `--danger`.

### UDS services used over `0x18DA30F1`

| SID | Name | Purpose | Honda gotchas |
|---|---|---|---|
| `0x10 0x03` | DIAGNOSTIC_SESSION_CONTROL (EXTENDED) | required before security access | |
| `0x10 0x02` | DIAGNOSTIC_SESSION_CONTROL (PROGRAMMING) | required to enter erase/write | "required time delay not expired" if re-attempted too fast — power-cycle to recover |
| `0x27 0x01 / 0x02` | SECURITY_ACCESS seed/key | uses `secret` from RWD header[4] | **Honda reuses the same key across firmware variants for the same physical ECU**. vfn's fallback patch: use first-available secret when F181 mismatches. |
| `0x22 F181` | READ_DATA_BY_IDENTIFIER (App SW ID) | returns 14-char part number, e.g. `b'39990-TJB-A010\x00\x00'` | **Reliable fingerprint** for what's currently installed |
| `0x22 F180/F186/F188/F189/F182` | Boot SW ID / Active Session / etc. | all return `READ_DATA_BY_IDENTIFIER - request out of range` on Honda EPS | **Don't bother** |
| `0x31` | ROUTINE_CONTROL ERASE_MEMORY | required before WRITE_DATA_BY_IDENTIFIER(FLASH_DECRYPTION_KEY) | |
| `0x2E FLASH_DECRYPTION_KEY` | WRITE_DATA_BY_IDENTIFIER | writes 3-byte key `b'\x01\x02\x03'` (header[5]) | Required before REQUEST_DOWNLOAD |
| `0x34` | REQUEST_DOWNLOAD | tells EPS to accept flash block | Rejects with `upload download not accepted` if start/length doesn't match expected payload geometry |
| `0x36` | TRANSFER_DATA | actual flash bytes | |
| `0x37` | TRANSFER_EXIT | end of block | |
| (final) | CHECK_PROGRAMMING_DEPENDENCIES | post-flash sanity | Trip here = almost always internal-checksum mismatch → EPS likely boots dead |

**Alternative wire protocol: CCP (CAN Calibration Protocol).** When UDS REQUEST_DOWNLOAD was hard-rejected on bricked RDX, thedordo switched to CCP via `ccp-tool.py` (`github.com/mmmorks/openpilot/blob/devel/panda/ccp-tool.py`) and got `holy shit it's programming` (2026-05-15). **CCP gotcha:** Later proven (2026-05-16) that CCP upload to a hard-bricked EPS was actually **doing nothing** — silent no-op despite progress bar moving. CCP works on live EPS units, **does not** recover a hard-bricked unit.

### Firmware addresses (Clarity, the canonical reference)

| Address | Meaning | Stock | Notes |
|---|---|---|---|
| `0xFFF880E4` | RAM landing for CAN 0xE4 payload | — | Convention: ends in CAN ID byte. |
| `0x20C40` | LKAS handler entry | — | |
| `0x20F0E`, `0x21CCA` | clamp/normalize live values | — | |
| `0x20F28` | JSR/N @R3 → 0x22084 (table consumer) | — | |
| `0x22084` | First verified table/helper consumer | — | |
| `0xFFF87204` | LKAS context pointer (row-selector source) | — | |
| `0x59148/54, 0x59160/6C, 0x59178/84` | Calibration table pairs (X/Y interp) | — | |
| `0x13910` | **Final output clamp (PRIMARY TORQUE CEILING)** | 1774 | Safe range 1774–7373 (45% of HW max). Raise to 9011 = ~55%. |
| `0x1390C` | fn_2A348 stage-2 clamp | 1774 | Set equal to `0x13910`. |
| `0x1390E` | fn_2A348 stage-1 delta clamp | 333 | Per-cycle delta cap. Often raised to 1774. |
| `0x13298` | B-follower rate divisor | 400 | **Diagnostic patch 400→320 = +25% follower rate** (one byte: `0x90→0x40` at `0x13299`). **NEVER VALIDATED IN-VEHICLE.** |
| `0x453B0` | Speed gain table base | sqrt ramp `2048×√(idx)` | 64 entries × 2 bytes. Output = `gain/4`. |
| `0x13BDC` | p_rate_table (Stage-2 IIR) Y-rates | 7×9 | Only rows 0 and 6 active. |
| `0x13AE0` | i_rate_table (Stage-1 IIR) Y-rates | 7×9 | Pre-feeds Stage-2. |
| `0x1380A` | fn_29F5C tracker alpha | 1999 | **NOT on CAN→torque path** (corrected 2026-04-28). Leave at stock. |
| `0x1380E` | Input clamp on torque-table X-axis | 1663 | **The genesis saturation cause.** Rows 0–1. |
| `0x13810` | Input clamp X-axis | 1774 | Rows 2–6. |
| `0x29E0E` | **SplitScale patch site** | `C6 3D` | Change to `46 00` (`SHLL r6` = ×2 of cmd_08 after split). Canonical Clarity fix. |
| `0x13642` | **HW PWM ceiling** | 16384 | **DO NOT TOUCH** — immediate LKAS fault. |
| `0x13808` / `0x1380C` | Unsigned overflow protection | 32767 / 32765 | Don't touch. |
| `0x13C60` / `0x13C62` | Driver override thresholds | ±7094 | LKAS ±3840 never trips these. |
| `0x11BE0` | Torque-output clamp (raw cipher offset) | — | The UART-byte-patched location vfn flashed in recovery experiments. |

### Civic Nidec (TGG/TBA/TEG) firmware addresses

| Address | Meaning | Source |
|---|---|---|
| `0xFFF87A98` | LKAS context pointer (≈ Clarity's 0xFFF87204) | vfn 2026-05-04 |
| `0x1371A` = 1663 | Civic clamp (≈ Clarity's 0x1380E) | vfn 2026-05-04 |
| `0xFFF87B3C` | Civic row selector | vfn 2026-05-04 |
| `0x1371C + row*0x12` | P1 X-axis lookup base | vfn 2026-05-04 |
| `0x1379A + row*0x12` | P1 Y-axis lookup base | vfn 2026-05-04 |
| `0x1396E / 0x139EC + row*0x12` | Stage-1/pre-P2 X/Y | vfn 2026-05-04 |
| `0x13A6A / 0x13AE8 + row*0x12` | P2 X/Y bases | vfn 2026-05-04 |
| `0x138F0` (Civic downstream P/output clamp) | 1774 → 7373 in linear45 builds | vfn 2026-05-03 |
| `0x138F2` (downstream state/ramp clamp) | 333 → 1774 | vfn 2026-05-03 |
| `0x138F4` (final output clamp) | 1774 → 7373 | vfn 2026-05-03 |
| `0xFFF879A4` | Civic shared command pointer | vfn 2026-05-04 |
| `0x2A0DC..0x2A0F0` | Generic `clamp(out, -limit, +limit)` SH2A pattern | **grep for this on any new model to find the torque clamp** |

### RDX (TJB-A030) firmware addresses

| Address | Meaning | Notes |
|---|---|---|
| `0x58100` | Payload start (vs Clarity's 0x4000) | RDX has ~22 KB of leading 0xFF before payload — **different layout from Clarity** |
| `0x55550` | First main torque bank | 48 duplicate copies at +0x180 each |
| `0x59550` | Main assist bank (flash addr) | 8 rows = 8 speed bands |
| `0x5C952` | Drive-mode limit block (flash addr) | Snow=row 1, Normal=row 4, Sport=row 6, Sport+=row 8 |
| `0x58298` | Speed breakpoints for torque-row selection | Inferred scale **raw÷64 ≈ mph** |
| `0x59412` = `0x0028` | Speed clamp (steer-enable, ≈4.0 mph) | OP patches to `0x0000` |
| `0x5C890`, `0x58270` | Rack-angle breakpoint axes | Inferred scale 0.1° |
| `0x55444` = `45°, 69°` | L/R max steer-angle candidates | Medium confidence — needs CAN confirm |

---

## 5. PID Knowledge (Load-Bearing for the Civic Tune)

### Gain values that have actually been driven

| Date | Author | Car | kp | ki | kf | LAF | Friction | Outcome |
|---|---|---|---|---|---|---|---|---|
| 2026-04-25 | brettpakkala | Clarity stock | 1.0 | 0.1 | 0.5 | — | — | "stock kf 1.0 yesterday was terrible … wobble out of control on interstate" |
| 2026-04-25 | brettpakkala | Clarity v2.0 | 0.8 | — | — | — | — | torque controller default |
| 2026-04-25 | brettpakkala | Clarity v0.0 | 0.5 | — | — | — | — | torque controller v0.0 |
| 2026-04-26 | vote_for_nobody | Clarity v13 | kp curve **23, 7.5, 3.5, 2.3** (3–10 m/s); **1.0 at 30 m/s** | — | — | 4.75 | 0.4 | Speed-bin kp curve. Replaced stock v0 `30, 11.5, 5.5, 3.5, 0.4`. **Most explicit speed-bin gain table in corpus.** |
| 2026-04-27 | brettpakkala | **Civic Bosch (PID)** | **0.3** | **0.1** | **0.00006** | — | — | "running strictly on the PID controller with the stock torque modded" — **kf is on PID-scale, not torque-scale.** |
| 2026-04-27 | vote_for_nobody | Clarity (1:1 aligned) | — | — | — | 1.45 (Claude-suggested) | — | "too aggressive" |
| 2026-04-29 | elusivejg | Civic TGG | 0.1 | — | 0.5 | 4.0 | 0.1–0.2 | grinding/jitter at low speed — never converged |
| 2026-04-29 | vote_for_nobody | Clarity | — | — | 0.5 → 1.0 (doubled) | — | — | "better unwind, but fast oscillations near center + violent 40–45 mph" |
| 2026-05-03 | **firestar4430** | (recommendation) | **≥ 0.6** | — | — | — | — | **"Don't take kP lower than 0.6"** — the only hard floor anyone has stated. |
| 2026-05-09 | vote_for_nobody | Clarity (PID, post-StarPilot) | — | — | — | — | — | "rock solid, oversteer on turns and a little jittery unwind" |

### Brett's oscillation taxonomy (commit to memory)

`@brettpakkala 2026-04-26 22:11: "Large oscillations (wobble-side-to-side) = The system is fighting with itself and you introduced too much lag. Tiny jitter oscillations = There's too much noise in the signal"`

**This is the single most useful diagnostic split in the entire corpus.** Wobble = controller lag (raise rate, drop kf, drop LAF). Jitter = plant noise (raise LPF tau, smooth filter, suspect EPS noise).

### kf scale gotcha

- **Torque-controller kf:** `0.5` (Clarity), upper bound ~0.5–0.7 before center oscillations + 40–45 mph violence appear.
- **PID-controller kf:** `0.00006` (Civic Bosch). **4 orders of magnitude different.** Don't conflate. The PID controller's feedforward formula multiplies by curvature × speed² ish, so the absolute number is much smaller.

### firestar's floors and ceilings

- `kP ≥ 0.6` (hard floor, "Don't take kP lower than 0.6")
- Lat-accel: **4.5 m/s² hard ceiling (joystick test); 4.0–4.2 m/s² typical observed in good tunes**. firestar saw elusive's peak at 4.07, said "I would stop there."
- Lateral models: **`popV2`** (firestar's pick), **`tcpv3`** (vfn's pick). **AVOID**: `SC` (aggro), `off_policy_v10` (reverted for oscillation).

### Iteration loop

1. **Hypothesis** — vfn or firestar posts what to try next (often Claude-suggested).
2. **Build** — modify .rwd via `eps_tool.py` (fix internal + outer checksums), or push branch.
3. **Drop / Push** — post to Discord with `@tester_handle`, or push to `mvl-staging-MM.DD.2026` on `github.com/nrdr/openpilot`.
4. **Flash** — `python eps-update.py <file>.rwd -b 1 --danger` (sometimes `--skip-checksum`).
5. **Drive** — 5–30 min, often same route (mountain pass, brett's 5-yr route). Watch for: EPS noise, torque drops mid-turn, oversteer, jackhammer, lock-in/no-unwind.
6. **Pull rlogs** — `.zst` from `/data/media/0/realdata/`, 1-min segments, ~10 MB each. **Watch the segment video first to confirm the event is in the rlog.**
7. **Claude analysis** — route rlogs through Claude with master trace + tuning doc as context. *Every "finding" from a log in chunk-3 is Claude-mediated.*
8. **Iterate** — usually within 10–30 minutes for OP-side changes. Hours if firmware flash needed. **~6–12 cycles per evening; ~31 .rwd files in 26 days.**

### Distinguishing controller from plant problems

The single hardest discipline in the corpus. The chat shows ~25% of "the gains are wrong" reports were actually one of these:

1. **Cache-stuck params** — interfaces.py changes silently kept old values. Fix: add a no-op comment to force recompile.
2. **EPS firmware filter masking >45 mph** — `_torque_lpf_tau = 0.1` static cliff at 45 mph. Plant problem dressed as controller behavior.
3. **53% top-end CAN saturation** — until 2026-04-27, no PID gain change could possibly matter past the saturation knee.
4. **Bad lateral model** — `off_policy_v10` was reverted for oscillation; phantom controller-oscillation reports trace back to it.
5. **USB cable angle on black panda** — elusivejg gets 100% timeouts with cable bent wrong.

### The upstream-of-rate-limiter lever (vfn's wasted-week warning)

`@vote_for_nobody 2026-05-20: "for the clarity there is a P+I filtering, which are 2 separate tables … but i leave those alone, spent about a week trying to tune those table for faster steer rates [then] figured out could scale the raw CAN torque command value because its send to the rate limit part of the firmware separately from the torque table"`

**Translation:** if you're fighting steer-rate noise, **don't tune the P+I filter tables**. The actual lever is upstream of them — scale the raw CAN torque command going into the rate-limiter. SplitScale (Clarity, `0x29E0E` instruction patch) is the canonical implementation.

### Plant-vs-controller misattribution (chunk 3's lesson)

Raising LAF makes plant problems look like controller problems. When elusivejg's Civic went super-slow after 0–1663 alignment, the team spent 5+ hours tweaking LAF and PID gains before pivoting to log-based debugging. The slow steering was structural (Civic firmware doesn't transfer Clarity values), not gain-related.

### Park-test method (brett 2026-05-16)

`@brettpakkala: "as long as your lines are bold on the dash"` (OP engaged with lane lines visible), put it in drive with brake hold and "grabby grab the wheel a bunch and watch it move you back to center." **Eliminates the drive-out-test-drive-back loop for most lat changes. Caveat: if you factory-reset to deploy, you still need a drive for calibration the first time.**

### Asymmetric STEER_DELTA_UP/DOWN (brett 2026-05-16)

`@brettpakkala: "STEER_DELTA_UP can and STEER_DELTA_DOWN can be asymmetrical. Like this issue only happens on rising never falling."` First jitter fix to actually land. `0.8 → 0.5` rate-cap experiments on Clarity → "removed 75–80% of jitter" but added "up to 2 seconds of lag at low speeds." Try this for Joey: asymmetric rate limits to attack jitter only on the rising edge.

### Quick reference — values Joey can pull from

- **Civic Bosch PID seed (brett 2026-04-27, not fully converged):** `kp=0.3, ki=0.1, kf=0.00006`
- **Civic TGG torque-controller seed (elusivejg, marginal):** `kp=0.1, kf=0.5, ki≈0`, LAF≈4.0, friction 0.1–0.2
- **Clarity v13 speed-binned kp curve (vfn):** `[23, 7.5, 3.5, 2.3]` at `[3, 6, 8, 10] m/s`-ish, then `1.0` at 30 m/s
- **firestar's floor:** `kp ≥ 0.6`
- **kf upper boundary (Clarity modified):** ~0.5–0.7
- **LAF scale for any 1663-capped firmware:** `LAF_new = LAF_old × 0.433`. `STEER_DELTA × 2.30`.
- **LPF tau cliff:** `_torque_lpf_tau = 0.1` above 45 mph. Below: variable, dominant smoothing knob for low-speed feel.

---

## 6. The Torque Tables (Honda Model Matrix)

### Clarity (TRW-*, SH-2A)

- **Stock X-axis rows 0–1:** `[0, 111, 222, 333, 443, 665, 887, 1108, 1663]`
- **Stock X-axis rows 2–6:** `[0, 222, 333, 495, 656, 887, 1108, 1552, 1774]`
- **Stock Y[8] rows 0–1:** `5120` (31% of HW max — main reason stock LKAS feels weak)
- **Row 0 only reachable in normal stock LKAS** (`fn_2AD2E` writes `active_record[0x0F]=0`)
- **Row 6 is override profile** fires ~18.6–33.1 mph under one state condition
- **Rows 1–5 are dead code in stock paths** (confirmed by trace 2026-04-25)
- **Practical implication: only edits to rows 0 and 6 produce observable behavior.**

**Row 6 cliff gotcha:** if row 6 isn't modified to match row 0, you get a torque cliff mid-turn when crossing 18.6 mph. Fix: `ClarityMax4_3.rwd` set row 6 concurrent with row 0.

Modified P-table progression (row-0):
```
V2.0:    [77,102,128,154,179,192,192,192,192]   ← stock-ish
V2.1:    [90,115,145,170,195,215,225,230,235]
V2.2:    [124,157,197,230,262,288,300,307,313]  ← aggressive
```

**Valley design** (from 564-route analysis, vfn): `Row 0: [156, 86, 89, 200, 286, 286, 300, 300, 512]` — entry[0]=156 turn initiation, entries[1–2] held slow (noise band 13–37% demand), entries[3–7] fast (real-turn ramp), entry[8]=512 saturation phase.

### Civic family (Nidec — TGG/TBA/TEG/TLA)

- **TGG (TGGA120, hatch)** — elusivejg's car, primary test mule. Weaker than sedan firmware. brett 2026-04-29: *"There's your proof that the stock hatch fw was always weaker than the sedan fw we all used. It was never strong enough to show what really happens."*
- **TBA (TBA-A030, TBA-C020)** — brettpakkala has the bin (Peter's Civic). Bosch.
- **TEG (TEGA010)** — *"TEG almost identical to TBA preliminary analysis, byte-shifted by 0x160"* (vfn 2026-04-29).
- **TLA (TLA-A040, "4.4x one")** — xriskybiscuitx's car. **4-ID header variant** (vs 3 IDs in all others) — failed first flash before this was noticed.
- **Civic Bosch (firestar's territory)** — separate fingerprint. Hit 3 Nm with the right controller tune on stock-ish firmware (2026-05-03).

**OPEN PROBLEM (unresolved as of corpus end 2026-05-21):** `@vote_for_nobody 2026-05-03: "I have not reliably been able to raise steer rates for the tgg or tba after testing with @ElusiveJG it causes eps noise and other issues."` SplitScale equivalent has not been ported to Civic. Peter/bruh2799 says Aragon previously LPF-fixed an older variant — **worth asking Aragon directly.**

### RDX (TJB-A030, SH-2A, 2019–2021)

- **8-row main assist bank at `0x59550`** — 8 speed bands (not drive modes).
- **48 duplicate copies** at `0x55550`, spaced 0x180 apart. *"WHAT DO YOU MEAN 48 COPIES"* — thedordo 2026-05-20.
- **Separate drive-mode block at `0x5C952`** — 6 valid copies, drive modes map to rows 1/4/6/8 (Snow/Normal/Sport/Sport+).
- **Drive modes affect EPS substantially:** Acura had to roll out an update for the 25 RDX because the EPS could crash in comfort mode.
- **22+ RDX is TJB-A070; 25 RDX is TJB-A210.** thedordo's A030 work does NOT transfer forward.

### Five-family .rwd lineage (31 files total)

- **ClarityMax:** V2.2_LowSpeedRates → V2.3.2_TeslaLike → 4_2 → 4_3 (mid-iteration at corpus end)
- **TGGA120 (Civic hatch):** LM45.1 → V2.0 baseline → V2.1-Linear45 (target) → +FlatGain → +SmoothP2
- **TBA (Civic Bosch sedan):** C120/C020 stock+max → V2.1-Linear45-FlatGain ported (no test results)
- **TLA (xriskybiscuit Civic variant):** stock → 4 failed test iterations on 2026-05-09 (4-ID header, CHECK_PROGRAMMING_DEPENDENCIES failures). **Unresolved.**
- **TJB-A030 (RDX, dordo):** 3 Claude-generated unverified .rwds → bench-flash brick → EPS dump → `tjb_rdx_eps_cal_maps.md` consolidation 2026-05-20. **Open.**
- **TEGA010:** one entry, checksum-fix only

Full lineage in `discord-export/subsets/06-attachments.tsv` and `synthesis/06-attribution-media.md`.

---

## 7. The Iteration Process (How They Work)

### Capture

- **Logs:** `.zst` rlogs from `/data/media/0/realdata/` on the comma device.
- **Segments:** ~1 minute long, ~10 MB max each.
- **Three transport methods** (in increasing preference):
  1. Direct upload of `.zst` to Discord.
  2. Google Drive folder of segments.
  3. **comma-connect link** (firestar's preference) — auto-stitches as segments upload, no downloads needed. Wiki: `wiki.firestar.link/faq/#how-do-i-upload-logs-for-troubleshooting`.
- **Filezilla SFTP** as a fallback (path `/data/media/0/realdata/`, port 8022 no longer required).

### Verify

- **Watch the segment video before sending the rlog.** This is the load-bearing verification step. `@vote_for_nobody 2026-04-29: "you can also look at the video in the segment folder and verify that the rlog contains the event your trying to show"`. Without it, you waste the analyst's time on the wrong minute.
- **Send small bundles, not full days.** `"don't need all of them just a few"`. The analyst hand-correlates events.

### Analyze

- **PlotJuggler** — firestar still falls back to it: *"plotjuggler still needs to be used occasionally cuz it can get confused"*
- **Claude / Codex on rlog + master trace + tuning doc as context.** vfn routes nearly everything through Claude. Caveat: Claude over-suggests aggressive LAF — discount by ~1.5–2×.
- **Ghidra / radare2 / rizin on firmware.** `@vote_for_nobody: "at first i tried using the NSA's ghidra and fumbling with the MCP server for claude/opencode, thats a crappy path... radare2 is way faster and claude works with it with ease"`. Capstone Python library is the SH-2A disassembler engine.
- **vfn's custom scripts:** `sh2a_disasm.py` (22 KB), `disasm.py` (2.5 KB), `probe_download_addr.py` (4 iterations).

### Modify

- **`.rwd` edit** via `eps_tool.py` (the cipher is a hardcoded byte→byte lookup table baked into `eps_tool.py:11`, NOT algebraic). Re-fix internal checksums + outer RWD container checksum.
- **OP branch edit** on `mvl-staging-MM.DD.2026` or `mvl-elusive-MM.DD.2026`.

### Flash

- **`python eps-update.py <file>.rwd -b 1 --danger`** (sometimes `--skip-checksum` — see Failure Modes for nuance).
- **Three buses to try:** `-b 0`, `-b 1`, `-b 2`. Exactly one returns `tester present ok`.
- **CCP fallback** for live units when UDS REQUEST_DOWNLOAD gets rejected: `ccp-tool.py` from `github.com/mmmorks/openpilot/blob/devel/panda/`. **Silent no-op on bricked units** — confirmed 2026-05-16.

### Drive

- Subjective feel — "buttery smooth", "lazy", "lawn mower", "drunk", "trolling me" — accounts for ~80% of evaluation signal.
- Wheel shake audio + visual (filmed on phone).
- Lat-accel peak from logs (firestar's scripts).
- Steer-pressed false positives (oscillation amplitude exceeds driver-override threshold).
- Saturation duty cycle (Claude analysis: "what % of frames is the controller asking for more than the EPS can give").

### Cadence

- **~10 iterations/evening** for OP-side changes.
- **~30 min cycle time** for OP-side.
- **Hours** for firmware (.rwd) changes (flash + recovery if bricked).
- **brett's daily ritual quote:** *"go all day testing then right at the very end find a new table we didn't know existed"*.

---

## 8. CAN Probing Method (How They Discover Signals)

The group is **not running live CAN bus sniffing in the SavvyCAN/candump tradition**. They reverse-engineer the firmware binary in Ghidra/radare2 and trace a known CAN ID through it. **The firmware *is* the DBC.**

### 5-step ritual (vfn's recipe for a new car)

1. **Look up the LKAS injection address in opendbc** — gotcha: DBC `BO_` lines use **decimal**, not hex. `228 = 0xE4`. Confirm before grepping firmware.
2. **Three-bus dry-run sweep** — `eps-update.py --dry-run -b 0 / -b 1 / -b 2`. The bus that returns `tester present ok` is your bus.
3. **Trace 0xE4 to its RAM landing slot** — convention: ends in the CAN ID byte. For Clarity that's `0xFFF880E4`. For new cars, grep for the LDC/MOV.B that stuffs the byte into a RAM slot whose low byte matches the CAN ID.
4. **Follow JSR/N call chains** — SH2A delayed-branch JSR/N is the function-pointer dispatch pattern. Walk it 3–4 hops to the table consumer.
5. **Find the table interp at the end** — tables come in X/Y pairs at fixed strides (Civic: `0x12` bytes per row; Clarity: similar). X-axis is raw-CAN-after-divide, Y is the gain output. **Find the `CMP/GT` + `BT/S` clamp pattern** (SH2A signature for `clamp(out, -limit, +limit)`). The 16-bit constant near it (often `0x06EE = 1774`) is the output clamp.

### Cipher gotcha

The original cipher used in `.rwd` encryption is a **hardcoded byte→byte lookup table, not algebraic**. Saved 30 min on V14.1 decrypt arc. Check `eps_tool.py:11` for the substitution table before attempting brute-force algebraic search (which returns ~7% match = random noise).

### On-device checksum hypothesis (promoted to working theory 2026-05-20)

The `.rwd` outer file checksum (bypassable with `--skip-checksum`) is **separate from** on-device boot-time checksum bytes inside the payload. Empirical evidence: vfn's UART byte-write at `0x11BE0` verified at byte-level but EPS still wouldn't boot → consistent with on-device checksum reject. Codex also mentioned a `sum16be` that must equal `0x0000`. **The group has not yet implemented or shared a checksum-recomputation function.**

### Cross-architecture comparison

The 3-step pattern (RAM landing → JSR/N chain → table interp) works on Clarity and Civic family. **On RDX, AI-trace could not find a reference to `0xE4`** in the dump — different architecture, may have separate driver-assist logic or different convention. dordo's `0xE4 → RAM(?E4) → gain-table-lookup` trace in Ghidra is the **plan-of-record for the RDX next session** (pinned 2026-05-20).

### Pattern-shape sanity check

Torque tables in this family are **roughly linear-with-knee**. If you find an exponential or logarithmic curve where you thought torque should be, you're looking at a **gain modifier or attenuation curve**, not the LUT itself. Don't reach for the table first — surrounding filters/limiters/clamps are the tunable surface.

---

## 9. Failure Modes + Recovery (NEVER skip this section)

### The brick catalog (3 confirmed)

| # | Author | Car | Trigger | Recovery actually used |
|---|---|---|---|---|
| 1 | vfn | Clarity | Modified parameter offsets *earlier than torque table / speed-clamp-lo*. Self-described as own fault. | **Bought used EPS + rack on eBay.** *"Lesson learned if I brick my eps… I'm just gonna buy another one lol"* |
| 2 | thedordo | RDX | Flashed Claude-generated `.rwd` (rwd-xray inference, no validated source firmware). Wrong part-number header (`A010` instead of `A030`). Compounded with `--no-checksum`. | **In flight as of corpus end.** Plan: physically open EPS, UART bootmode reflash. No upload script for Renesas variant yet. |
| 3 | xriskybiscuitx | Civic TLA | vfn-built `.rwd`, flashed with `--no-checksum`. Took the firmware but never booted. | **Unresolved.** No follow-up in corpus. |

### `--no-checksum` nuance (the most important brick rule)

- **The flag is *required* for development iteration** — most test `.rwd`s won't pass outer checksum check.
- **The flag is *the brick vector* when the .rwd is malformed.** The flasher bypasses checksum check, but the on-device boot checksum still validates.
- **Rule:** `--no-checksum` is fine when the .rwd was correctly *constructed* (internal checksums computed). The brick vector is `--no-checksum + malformed payload`.

### LLM-generated .rwd risks

thedordo's RDX brick (#2) is the canonical example: a Claude-generated .rwd from rwd-xray inference for an undocumented Honda model. Length mismatch + wrong header. *"I trust it as far as I can throw it"* — dordo's own framing.

**brett's lone counterexample:** he reconstructed Clarity .rwd from a different car's bin + put correct headers on it, and "somehow it worked" — but this was on an architecture the group already understood. **Don't flash speculative LLM-built firmware to your primary car.**

### Hardware-vs-firmware confounder (chunk 9's lesson)

Aragon UART-flashed verified stock and still had no steering. For ~16 hours he assumed firmware corruption. **Resolution: salvage motor swap fixed it ($160).** Soldering/UART work can physically degrade boards. **"Verified stock flash" does not mean "EPS is healthy."** Always rule out hardware before re-diagnosing firmware.

Specific operational footguns:
- **Don't write live scripts to `/tmp`** (Aragon lost his after a reboot).
- **Harnessbox relay must click** during the flash ritual.
- **USB-A port physical degradation** (elusivejg's panda needed 10+ retries when the previous panda worked instantly).
- **Battery state matters** — low battery during flash triggers CHECK_PROGRAMMING_DEPENDENCIES errors. Use a battery maintainer (>0.8 A) for bench work with ignition on.
- **Don't murder the rotation-sensor wires** when extracting motor (dordo did this on his donor RDX).

### Renesas V850 vs SH-2A wall

- **V850** = Honda Pilot 2019, Accord 2020 Touring. mmmorks/openpilot has scripts but unfinished territory.
- **SH-2A** = Clarity, Civic family, RDX. Documented, vfn's `sh2a_disasm.py` works here.
- **Don't port between them.** The 0x0–0x3FFF boot-safe-zone rule is SH-2A-specific. V850 boot region location unknown.

### Boot-safe zones don't generalize across Honda chips

Clarity boot is at user-area `0x0–0x3FFF`. RDX payload starts at `0x58100` with ~22 KB of leading `0xFF`. **Whatever's at `0x0` on RDX is not understood.** Don't reuse Clarity safe-zone assumptions for new models.

### Recovery paths (in order of reliability)

1. **Buy another EPS** — the only end-to-end-proven recovery. vfn ran "NOPEnpilot" for a week before his replacement arrived.
2. **CCP on a live unit** — works for diagnostic + flash on units that still respond. **Silent no-op on hard-bricked units.**
3. **UART boot-mode** — theoretical recovery; vfn got full write-verify roundtrip but EPS still didn't boot (suspected on-device checksum issue). **Nobody has fully recovered via this in-corpus.**

### Honda IHDS / dealer tool

- **IHDS works on the comma 4 + harness** — dordo proved it by pushing a brake-booster update.
- **IHDS refuses to enumerate a fully bricked EPS** — *"so fucked that they can't tell when it was last written to."* This is actually useful: the dealer can't tell when it was last written. dordo: *"I shall feign ignorance."*
- **Open question:** can IHDS push a stock firmware re-flash to a partially-bricked module? Not tested.

### Procedure A — Flasher won't connect / `tester_present` timeout

1. SSH into comma. `tmux kill-server` (or `pkill openpilot`).
2. Verify: `ps aux | grep openpilot` — only the grep itself should show.
3. If still timing out: unplug USB-C → reconnect → off-road state → **listen for harnessbox click** → reflash.
4. Check black-panda USB cable angle (elusivejg's 100%-reproducible mechanical bug).
5. If `CAN packet version mismatch`: panda firmware is stale; needs update.
6. **Power-cycle the car. Up to 10 times.** No rhyme no reason.

### Procedure B — Soft-brick recovery (EPS still on CAN)

1. Build a known-good `.rwd` (stock or last working tune).
2. `pkill openpilot` → verify dead.
3. `python eps-update.py --bus 1 --danger <stock>.rwd` from `/data/openpilot` (flasher branch only — switching branches each time is *"miserable"*).
4. Power-cycle. **Test with grabby-grab-the-wheel-and-watch-it-return-to-center** (brett's park-test).

### Procedure C — Hard-brick UART recovery (in flight, not yet validated)

Source: `Honda_Steering_Firmware_Dump.pdf` (in `discord-export/media/`).

1. Physically open the EPS — ~3 hours of drilling + dremeling.
2. Wiring on the PCB:
   - White → RX (chip-side TX)
   - Brown → TX
   - Red → 3.3V in
   - Black → GND
   - Magnet wires (one to 3.3V, one to GND)
   - Orange → reset; tie to GND for a sec, then hold on 3.3V for boot mode
3. Use a battery maintainer — slow over UART, kills car battery otherwise.
4. Write `user.bin + 0x0–0x4000` back to bricked EPS. (Clarity SH-2A only — V850/Acura unknown.)
5. **Caveat:** vfn's UART write-verify roundtrip was byte-perfect but EPS still wouldn't boot. Suspected on-device checksum reject. **Not yet end-to-end working.**

### Specific operational footguns (compiled)

- **Hard takeover after high-torque LKAS can fault the EPS into a no-LKAS state.** Recovery: pull negative battery terminal for ~30 sec. Treat test drives as having a soft-brick recovery cost.
- **Factory reset comma → erases EPS calibration.** Drive to recalibrate before any test means anything.
- **autoecu.io doesn't work with red panda.** Use old `eps-update.py` script via red panda; autoecu.io is for vfn's custom proxy board.
- **autoecu.io is broken on latest agnos.** Effectively unavailable to most Honda group going forward.
- **`opendbc/car/uds.py` assertion crash** (`isotp - rx: invalid consecutive frame index`) — power-cycle fixes.
- **Flasher branch is on an older agnos kernel.** Switching to it triggers kernel rebuild over slow ethernet.
- **Always-on 12V + ignition-gated power supplies.** EPS gets always-on 12V but powers down without ignition. Flashing requires ignition on.
- **70-amp fuse in battery box** — always hot, arcs on probe. Required for EPS recovery if you suspect blown fuses.

---

## 10. The Roster + .rwd Family Tree

### Active members (5 hands-on)

- **vote_for_nobody** (1,685 msgs) — **lead theorist / .rwd builder.** Authored SH-2A disassembly tooling. Generates almost every Clarity/TGGA/TLA `.rwd`. Cost receipt: ~$300 of Claude usage for the Clarity reverse-engineering effort. Mac user. `vanillagorilla.autoecu.io` for flashing. **Not Aragon** (an earlier internal attribution misread that claim — see Aragon identity resolution below).
- **thedordo** (1,221 msgs) — **hardware / reverse-engineering specialist (Acura RDX, SH-2A).** Bench-flashed used EPS, did physical dump (drill + dremel + UART). Authored RDX firmware-dump PDF + `tjb_rdx_eps_cal_maps.md`. *"If it's jank and it works, it's not jank."* 3 dead EPS units; planning a 5th. Uses Cursor Pro.
- **elusivejg** (1,068 msgs) — **primary Civic test driver + tester (TGGA120 hatch).** Almost exclusively drops video files (IMG_3xxx series) plus terse verdicts. Owns canonical baseline (`39990-TGGA120-V2.0-Linear45-StockAuthority.rwd`) and target (`39990-TGGA120-V2.1-Linear45.rwd`).
- **brettpakkala** (570 msgs) — **a.k.a. `Aragon` (Discord nickname) / `nrdr` (GitHub alt).** Fork maintainer / openpilot engineer. Owns `nrdr/openpilot` repo (mvl-staging branches, rwd-flasher fork). Cross-references Bosch Civic. Multi-car driver: Clarity + Civic + Tesla. **The PID pivot was his idea** (chunk 3 — "abandon torque controller for tau-coupled PID"). **The asymmetric `STEER_DELTA_UP/DOWN` rate-limit fix is his** (chunk 8). Self-disclosed `nrdr` in chunk 5: *"nrdr is my alt GitHub account where I do all sorts of illegal and sketchy things."* He is the person tuning Joey's PID this week (per user, 2026-05-21).
- **firestar4430** (161 msgs) — **StarPilot fork author / safety-envelope skeptic.** Wiki: `wiki.firestar.link`. Outside-perspective skeptic with humor. Engineering-grounded — uses a simulator, owns the 4.5 m/s² ISO threshold. Recommended models: `popV2`. Tunes "by hand like a freak" (no DE optimization).

### Less-active

- **xriskybiscuitx** (101 msgs) — Civic test driver on TLA-A040. Sourced original .bin. Discovered "4 IDs vs 3 IDs" header issue. Bricked his car as of corpus end.
- **bruh2799** (109 msgs) — Civic test driver on brett's mvl-staging branch.
- **raayyymond** (43 msgs) — Bench-EPS hardware tipster (2020 Accord Touring, V850). EPS power supplies require ignition high.
- **the_roen** (21 msgs) — Downstream integrator. Maintains `THERoen/Roendbc` and `RoenPilot`. Cleanup commit `9af7bf1` split `carcontroller.py` into `_ext.py`.
- **otterpupinacup** (10 msgs) — Late arrival 2026-05-20. Red-panda flash how-to (`epsflashwithredpandaandepsupdate1.txt`).

### Aragon identity — resolved canonical (2026-05-21)

**`Aragon = brettpakkala = nrdr (GitHub)`** — confirmed via raw Discord JSON.

The Discord export's `mentions` field contains the literal nickname mapping:

```json
{
  "id": "125092410333200384",
  "name": "brettpakkala",
  "discriminator": "0000",
  "nickname": "Aragon"
}
```

Of 91 messages containing the string "Aragon", **83 resolve to `brettpakkala`'s Discord user ID** via the canonical mentions field. The remaining 8 are noise (mistypes, ambient mentions). `vote_for_nobody` is the most prolific *addresser* of `@Aragon` (71 messages start with the @-ping) — vfn was talking *to* Aragon, not being addressed as Aragon. The attribution agent's earlier claim that `vfn = Aragon` is a misread; the torque-table specialist's `Aragon = nrdr = brettpakkala` was correct. Confirmed by user 2026-05-21.

**`nrdr`** is the GitHub alt brettpakkala self-disclosed in chunk 5 (*"nrdr is my alt GitHub account where I do all sorts of illegal and sketchy things"*). Joey confirmed verbally that "Aragon" is the person tuning his PID this week, so future agents reading this doc should treat `Aragon → brettpakkala → nrdr/openpilot maintainer` as a single chain of identity.

### .rwd lineage families (5)

- **ClarityMax** (3 files): V2.2_LowSpeedRates → V2.3.2_TeslaLike → 4_2 → 4_3
- **TGGA120** (10 files, Civic NA/JP Nidec): LM45.1 → V2.0 → V2.1-Linear45 → +FlatGain → +SmoothP2 [combined]
- **TBA** (5 files, Civic Bosch / Peter's variants): C120/C020 stock+max → V2.1-Linear45-FlatGain port
- **TLA** (7 files, xriskybiscuit's Civic variant): stock → 4 failed test iterations (4-ID header issue)
- **TJB** (3 files, RDX): Claude-generated unverified
- **TEGA** (1 file): checksum-fix only

Full table in `discord-export/synthesis/06-attribution-media.md`.

---

## 11. Open Problems As Of 2026-05-21

| # | Problem | Origin | Status |
|---|---|---|---|
| 1 | **Civic super-slow / wheel-shake** | chunk 3 (elusivejg's TGG slow after 0–1663 alignment) | **OPEN.** Peter/bruh2799 says Aragon previously LPF-fixed an older variant. **Worth asking Aragon directly.** |
| 2 | **TLA-A040 linear implementation** | xriskybiscuitx's car | Base torque mod exists; linear implementation pending. vfn made one attempt for a different car and bricked it. |
| 3 | **TLA-A040 silent-fail brick** (xriskybiscuitx) | 2026-05-19 | Unresolved. No recovery progress in corpus. |
| 4 | **thedordo's RDX recovery** | 2026-05-15 brick | In progress. Multiple bench attempts failed; "fake car" Cabana-replay idea floated. |
| 5 | **EEPROM dump never executed** | proposed 2026-05-16, 2026-05-17 | Chekhov's gun. If rwd handling logic lives in EEPROM, the flash-area RE is incomplete. |
| 6 | **B-follower diagnostic patch at 0x13298 never validated in-vehicle** | Clarity tuning doc | Diagnostic ladder claim (400→320 = +25% follower rate). Could be remaining rate-wall fix or could be no-op. |
| 7 | **vfn's "2 bytes" mystery** | chunk 9 msg 189 | Never explained. Likely checksum bytes. Resolved by salvage motor swap. |
| 8 | **Live-RAM-logging via firmware injection** | proposed 2026-05-20 | Designed (trampoline + 10th-frame CAN broadcast), not built. Named as the unlock for understanding mode-selection logic. |
| 9 | **CCP write-mode on bench EPS** | thedordo's plan | Not yet executed. Could enable bench testing if combined with sensor-spoofing. |
| 10 | **Civic firmware actual top X value confirmation** | open since chunk 2 | Critical for any Civic PID tune. Civic structurally similar (`0x1371A=1663`) but **not driver-verified end-to-end.** |

---

## 12. Unknown-Unknowns Library

The "huh that's clever" items pulled from across the corpus:

- **Magnet-wire-through-VIA harness** (dordo): 30 AWG magnet wire threaded *through* the PCB VIA, wicks solder onto the via, thin enough to embed in factory sealant + UV-resin. Can be routed out a hole with waterproof connector — persistent flash pigtail.
- **3D-printer-chamber thermal trick** (dordo): heat EPS assembly to ~50 C in printer enclosure → plastic expands faster than aluminum → pins release.
- **Park-test method** (brett): brake hold + grabby wheel for fast iteration — eliminates drive-out-test-drive-back loop.
- **Konik A1M as C3X replacement** (brett's setup after C3X death).
- **`wiki.firestar.link/faq`** as the doc hub for log uploads.
- **radare2/rizin > Ghidra+MCP** for SH-2A (vfn).
- **Capstone Python library** as the SH-2A disassembler engine.
- **Cursor Pro** vs **direct Claude** workflow split (dordo on Cursor, vfn on Claude with explicit *"my cursor has been so much less lobotomized than the first time I asked it half these questions"*).
- **vfn's $300/2-week Claude budget** for the Clarity reverse-engineering effort.
- **firestar tunes "by hand like a freak"** — no DE optimization or ZN method. The most algorithmic-feeling member is also manual.
- **"If I brick my eps I'm just gonna buy another one"** (vfn 2026-05-19) — operating-procedure shift after a week of NOPEnpilot.
- **Discord hidden `filetype:` search filter** (dordo 2026-05-16) — useful for finding .rwd attachments without scrolling.
- **"NOPEnpilot"** — vfn's term for running with EPS effectively bricked.
- **"dac'd it"** — in-group vocab for stress-tested via DAC voltage manipulation.
- **"daily ritual: go all day testing then right at the very end find a new table we didn't know existed"** (brett 2026-04-28).
- **"impact wrench" analogy** (brett) for EPS noise on aggressive tunes.
- **"lawn mower" sound** = LAF too aggressive for current torque level.
- **brett's 3-state LKAS lane indicator** (no lines = off / dashed = active-but-suspended / solid = actively steering). Even firestar didn't know.
- **Double-LLM cross-validation** as evidence standard ("traced by both codex and claude — same conclusion") — vfn 2026-04-26.
- **On-screen torque bar on the comma 3X display** as live diagnostic (vfn 2026-04-26) — lets you distinguish EPS-fault from controller-fault in seconds.
- **Comma device "going offline" message** in SSH (dordo, chunk 9, msg 268) — openpilot-side instrumentation worth grepping.
- **Sport mode crash on 25 RDX** — Acura OTA for it. Drive modes can crash EPS firmware in ways that look like LKAS faults.
- **"Steer to zero" hidden flag for Bosch cars** (thedordo 2026-05-20) — works on some Bosch cars, might include RDX (which is TJB-Acura but Bosch-radar-routed).
- **brett-as-nrdr self-banter** (2026-05-16): *"Hold up, I'm still on mvl-debugging-05.13.2026, I gotta go over here and steal these commits from this nrdr guy. He's always doing stuff behind my back."* Same person.
- **EPS firmware is hardware-shared across Clarity↔Civic↔CRV (non-V850)** at the board level — RDX is different layout. Soldering map from Clarity PDF works for Civic/CRV.
- **Drive-mode selector signal is on CAN; EPS reads it.** Any torque-table mod has to respect mode-switching.
- **Speed unit constant is inferred at 0.25 kph/LSB but not measured.** The 18.6–33.1 mph row-6 cliff depends on this. Worth a CAN-sniff experiment.
- **Bosch-A vs Nidec CAN routing** (LKAS→radar→ptu vs radar→LKAS→ptu) — Nidec keeps CMBS because of this routing. Most "supported cars" in openpilot are Bosch-A.

---

## 13. Reference Materials

### Docs (already in `discord-export/media/`)

- **`CLARITY_EPS_TUNING.md`** (35 KB, vote_for_nobody) — **same file Joey loads as `~/Downloads/CLARITY_EPS_TUNING(1).md`** — the canonical source. **Always read first for any Clarity work.**
- **`clarity_master_lkas_trace_UPDATED_2026_05_02_SplitScale.md`** (66 KB, vote_for_nobody) — full Clarity LKAS code-path trace with addresses.
- **`tjb_rdx_eps_cal_maps.md`** (15.5 KB, thedordo) — RDX reverse-engineering writeup (only source for TJB addresses).
- **`Honda_Steering_Firmware_Dump.pdf`** (794 KB, thedordo, shared twice) — Honda's own solder-points + photos guide for physical EPS dump. **First-of-kind documentation** in this DM. Boot mode pin layout. "True for any SH2A EPS."

### Code

- **`sh2a_disasm.py`** (22 KB, vote_for_nobody) — SH-2A disassembler with Clarity-specific bits + r2 fallback. macOS path defaults.
- **`disasm.py`** (2.5 KB, vote_for_nobody) — lightweight companion.
- **`probe_download_addr.py`** (4 iterations, ~6.2–7.0 KB, vote_for_nobody) — UDS download-address probe with erase→key→download→transfer→exit flow. **Latest iter adds erase routine before request_download.**
- **`sh-2a-write.py`** (8.9 KB, thedordo) — boot-mode UART writer.
- **`ccp_xcp_panda_skeleton.py`** (34 KB, thedordo) — CCP/XCP protocol skeleton.
- **`epsflashwithredpandaandepsupdate1.txt`** (2.8 KB, otterpupinacup) — red-panda flash how-to. **Matches Joey's PRIMARY workflow per CLAUDE.md.**

### Binary corpus

- **`EPS_Firmwares.zip`** (9.9 MB, thedordo, 2026-05-19) — **"all of the EPS firmwares that honda had as of last week on IHDS"** — high-value reference archive of every 39990* firmware.
- **`user.firmware.bin`** (163 KB, vote_for_nobody) — extracted Clarity firmware blob.
- **`user.bin`** (524 KB, thedordo, 2026-05-14) — first RDX EPS dump.
- **`user-brick.bin`** (524 KB, thedordo, 2026-05-19) — the brick. Forensic artifact.
- **`39990-TJB-A030.0x4000.bin`** (442 KB, thedordo) — offset-prefixed RDX bin.
- **`39990-TBA-C120.bin` + `39990-TBA-C020.bin`** (327 KB each, brettpakkala) — Peter's Bosch Civic firmwares.
- **`39990-TLA-A040-original.bin`** (524 KB, xriskybiscuitx) — stock TLA-A040.

### Reference repos

- **`github.com/nrdr/rwd-xray-2026`** — Aragon's (brettpakkala's) fork. The active rwd parsing tool. `eps_tool.py` is the modify-build script.
- **`github.com/nrdr/openpilot`** — branches `mvl-staging-MM.DD.2026` (canonical, latest is `mvl-staging-05.16.2026`), `rwd-flasher-2026`.
- **`github.com/mmmorks/openpilot/tree/devel-098`** + **`github.com/mmmorks/rwd-xray`** — 2019 Pilot V850 territory (mmmorks owns a Pilot).
- **`github.com/mmmorks/openpilot/blob/devel/panda/ccp-tool.py`** — CCP protocol tool.
- **`github.com/gregjhogan/renesas-bootmode`** — Renesas SH-2A bootmode dump utility.
- **`github.com/JamesL787/StarPilot`** — firestar's StarPilot fork (Dom branch has torque-mod code per firestar 2026-05-09).
- **`github.com/THERoen/Roendbc`** — Roen's integration fork.

### Attachment index

All 306 attachments indexed at: `C:\claudecode\comma4epsflash\discord-export\subsets\06-attachments.tsv`

---

## Appendix: Joey-Specific Action Items

Distilled from synthesis. Run in order before next tune.

1. **Confirm sunnypilot interface.py is sending what you think it's sending** (Check #1 in Section 2). Single biggest false-hypothesis trap in the corpus.
2. **Verify Civic firmware top X value** — UART dump or `eps_tool.py` parse. If `0x1371A` is `1663`, your saturation profile mirrors Clarity. If not, recalibrate everything.
3. **Pull Brett's asymmetric STEER_DELTA_UP/DOWN rate-limit fix** from `mvl-staging-05.16.2026` if not already on it. First jitter fix that actually landed.
4. **Set `kf` per controller scale, not by copy-paste.** PID: `0.00006`. Torque: `0.5`. Don't conflate.
5. **Stay under `kP = 0.6` floor and `4.5 m/s²` lat-accel ceiling.**
6. **If you hit steer-rate noise, don't tune P+I filter tables.** Scale the raw CAN torque command going into the rate-limiter (SplitScale pattern). vfn's wasted-week receipt is your warning.
7. **Ask Aragon (brettpakkala) directly about Civic LPF fix.** Peter/bruh2799 says Aragon previously solved a similar wheel-shake on an older Civic variant.
8. **Watch the segment video before sending any rlog for analysis.**
9. **If a gain change has no effect, suspect cache-stuck params first.** Force-recompile trick.
10. **Don't write live scripts to `/tmp`. Don't run `--no-checksum` on a malformed `.rwd`. Buy a spare EPS before you need one.**

---

*Document compiled 2026-05-21 from the synthesis stack at `C:\claudecode\comma4epsflash\discord-export\synthesis\` (6 specialist files) and `C:\claudecode\comma4epsflash\discord-export\chunks-synthesis\` (10 chunk files). For verification, raw subsets at `C:\claudecode\comma4epsflash\discord-export\subsets\*.jsonl` and chunks at `C:\claudecode\comma4epsflash\discord-export\chunks\chunk-*.jsonl`.*
