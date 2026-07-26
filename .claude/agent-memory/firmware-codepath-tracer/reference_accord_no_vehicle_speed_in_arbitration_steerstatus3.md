---
name: reference_accord_no_vehicle_speed_in_arbitration_steerstatus3
description: m_steer_torque_arbitration (FUN_00028ea6) has ZERO vehicle-speed reads; STEER_STATUS=3 is a torque/engagement fallback, not a speed compare. Closes half of the LOW_SPEED_LOCKOUT open item.
metadata:
  type: reference
---

**Entry point / identity**: `FUN_00028ea6` (body `0x28ea6`-`0x2a30d`), sole caller `FUN_0002214a`
(`w_steer_control_task`, the confirmed ~1kHz control task — see [[control-task-tick-confirmed-1khz]]).
This is `m_steer_torque_arbitration` (the function memory already named as containing the live-inlined
debounce+arb logic, distinct from the dead `FUN_0002a30e` twin that immediately follows it in the image).
[VERIFIED: `get_function_callers(0x28ea6)` -> only `0002214a`; body range from `get_function_by_address`.]

**Finding 1 — no vehicle/wheel-speed read anywhere in this function.** Full decompile (1310 lines)
scanned for every `gp`-relative read in the 0x1000-0x3000 offset band (where raw CAN-RX scratch would
live, by contrast with the 0x4000-0x7000 band used by the LKAS/torque signal pipeline). Only hit:
`gp-0x257c` at line 1295, used as a **pointer** (`*(int*)(gp-0x257c)+0x14`) into a per-state lookup
struct for a history/logging array — not a speed value. Every other input to this function is
torque-sensor validity (`gp-0x6a5e` voted Sensor-A torque, `gp-0x4f60` Sensor-B torque, `gp-0x6a44/40/
3c/38/46` per-channel range checks), the assist engagement substate (`gp-0x67fe`, see
[[eps-gp67fe-trump-engaged-holding-substate]]), and setpoint/rate variables (`gp-0x69aa`, `gp-0x69ae`).
[VERIFIED by direct decompile + grep sweep, this session.]

**Finding 2 — STEER_STATUS=3 (the DBC "LOW_SPEED_LOCKOUT" value) is a torque/engagement FALLBACK, not a
speed compare.** Structure (addresses from the decompile, function-relative line numbers noted):
```
if (bVar3 && iVar28!=1 && gp-0x67fa!=8 && gp-0x6807!=7) {      // outer "system ready" gate
    if ((flags & 8) == 0) {                                     // some readiness bit clear
        if (bVar2) { ...torque/rate debounce escalation to STATUS=4/7, same shape as the
                      already-documented FUN_0002a30e debounce SM (0xC64B4/0xC64B7/0xC61C0 family)... }
        else {
            gp-0x6807 = 3;      // <-- STEER_STATUS = 3, unconditional inside this else
            gp-0x6758 = 0;
            gp-0x6757 = -cVar15;
        }
    } else { gp-0x6807 = 6; ... }
} else { gp-0x6807 = 7; ... }
```
`bVar2` (the gate that must be TRUE to even attempt the torque/rate debounce path, else STATUS falls to
3) requires ALL of: `gp-0x69aa` in `[uVar7, 0x8000]` (a cal/setpoint-window check), Sensor-A torque
validity (`bVar1`), a separate torque-window flag (`bVar2_old`, itself gated on `gp-0x6a5e` vs
tp+0x72e8/0x72ea cals), AND **`gp-0x67fe == 2`** (assist substate must be the "engaged" value) — only
then does it further require `|gp-0x69ae| < 0x4000` (setpoint magnitude window). **None of these terms
is a decoded vehicle speed.** [VERIFIED structurally; the exact semantics of `gp-0x69aa`/`gp-0x69ae`
were not re-derived this session — they read as setpoint/rate cal windows, consistent with existing
setpoint-limit memory, not re-proven here.]

**Inference (not proven this session)**: the kit's own rlog analysis found STEER_STATUS=3 empirically
correlates with vehicle speed (100% at 0-2mph, 0% by 5mph, release ~3-4mph — see
`eps_lkas_chain_model.py` lines ~2868-2887, `_ss_vs_speed.py`). Given Finding 1+2, the most likely
explanation is that this is a DOWNSTREAM ARTIFACT of openpilot's own `minSteerSpeed`=3mph cutoff: below
that speed openpilot stops requesting steer entirely (`latActive=False`), so `gp-0x67fe` never reaches
its "engaged" substate (or the setpoint/torque windows never populate) and the function falls through
to the STATUS=3 default — not because the EPS firmware measured wheel speed and gated on it. This
would mean the operator's ~5mph grinding is NOT explained by a discrete firmware speed threshold.

**Closes (partially) the "Firmware LOW_SPEED_LOCKOUT producer is not located in the command pipeline"
open item** in the CLAUDE.md "Acknowledged knowns/unknowns" list: the producer (`FUN_00028ea6`) IS now
located and traced, and it is confirmed to NOT depend on a wheel-speed CAN value. The item's other half
(the actual VSA wheel-speed CAN decoder feeding `KFC_WHEELSPD_PLAUSI`/`KFC_RACKPOS`, presumably a
rack-position cross-check unrelated to LKAS) remains genuinely open — see
[[reference_accord_can_1d0_wheelspeed_dtc_names_no_decoder]].
