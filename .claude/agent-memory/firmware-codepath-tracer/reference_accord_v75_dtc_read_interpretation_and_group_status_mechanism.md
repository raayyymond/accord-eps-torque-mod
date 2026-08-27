---
name: reference_accord_v75_dtc_read_interpretation_and_group_status_mechanism
description: Decodes the V75-incident UDS 0x19/0x02 DTC read (5 codes) against two PRE-V21 baseline captures found in the repo, and reverse-engineers the group-status-selection mechanism (FUN_0004c5a6/FUN_0004c560/FUN_0004c130/FUN_00047d06/FUN_000475d2) that determines what a multi-member DTC group actually reports. Resolves the months-old [UNVERIFIED] 0x1c/0x1d<->0xF00049 mapping and gives a fresh-vs-stale verdict for each of the 5 observed DTCs.
metadata:
  type: reference
---

# V75-incident DTC read, decoded against baseline — stock code.bin, 2026-08-06

## The decisive comparison [EVIDENCE — raw file read, not memory]

Two files in `flashing-2020accord/` (`dtc_script_output_stock_eps_preV21new.txt`,
`dtc_script_output_v21new_eps.txt`) are **byte-identical UDS captures from BEFORE this kit's first flash**
(app id read as `39990-TVA-A160` / `39990-TVA,A160`, i.e. pre-V21 and V21-era). Both show:
```
0x540011  status=0x40   0xC41668  status=0x08   0xD48394  status=0x40
0xF00049  status=0x48   0xF00055  status=0x40
```
The post-V75-incident read (taken during the V74 drive-to-work) shows:
```
0x540011  status=0x40  UNCHANGED
0xC41668  status=0x0C  CHANGED 0x08->0x0C (pendingDTC newly set)
0xD48394  status=0x48  CHANGED 0x40->0x48 (confirmedDTC newly set)
0xF00049  status=0x48  UNCHANGED — byte-identical to a capture predating this kit's very first flash
0xF00055  status=0x40  UNCHANGED
```
**Only 5 groups reported (mask 0xFF) both times — no 6th/new group appeared anywhere in the other 19
groups.** `0xF00049` — the ONLY EPS-disabling group among the 5, and the one containing fault indices
0x1c/0x1d (the damper shadow monitors) — carries **zero new bits**.

## DTC group table — byte-exact confirmed via `read_memory` (not just trusted from old memory)

`tp - 0x64e0 = 0xB8B20`, stride `0x68` (104B) per group, 1-indexed. Format: `[DTC code:4B LE, decoded
as bytes[2],[1],[0]][fault_id list: up to 50x uint16, zero-terminated/padded]`.

| DTC (observed) | group (1-idx) | addr | fault_id member(s) |
|---|---|---|---|
| `0x540011` | 3 | 0xB8BF0 | **17** (0x11) only |
| `0xC41668` | 18 | 0xB9208 | **81** (0x51) only |
| `0xD48394` | 20 | 0xB92D8 | **73** (0x49) only |
| `0xF00049` | 21 | 0xB9340 | **38 members**: 4,5,6,7,8,11,12,13,14,15,16,18,19,20,21,22,23,24,25,27,**28,29**,40,41,42,43,44,45,46,47,51,55,56,58,60,62,68,116, **+38 appended out-of-order in the record's LAST (50th) uint16 slot** |
| `0xF00055` | 22 | 0xB93A8 | **72** (0x48) only |

All 5 confirmed byte-for-byte against `read_memory` on `code.bin`. `28`/`29` (0x1c/0x1d, the damper
shadow monitors — see `reference_accord_gp6bd0_shadow_faultpath_0x4179_0x417a.md`) ARE genuine members
of group 21. `38` (0x26, `FUN_00070a98`'s delivery-consistency monitor) is ALSO a genuine member —
confirmed by decompiling `FUN_00070a98`, which calls `FUN_0005ae6a/afba/b650/bb04/b68c(0x26,...)`.

## Fault-descriptor EPS-disable bit — byte-confirmed at `tp-0x72bc + id*0x1c`, first 4-byte word, bit0

| fault_id | word | bit0 (EPS-disable) | note |
|---|---|---|---|
| 4 | 0x00001C01 | **1** | `FUN_00019204`, motor-init self-test, **INIT-TIME ONLY** — see below |
| 17 | 0x00000C01 | **1** | trigger not traced; status never fired (always 0x40) |
| 28 (0x1c) | 0x00003D01 | **1** | Monitor 1 shadow-consistency (`FUN_0004613e`) |
| 29 (0x1d) | 0x00003D01 | **1** | Monitor 2 / `FUN_000347b8` shadow-consistency |
| 72 | 0x00000C20 | 0 | trigger not traced; status never fired |
| 73 (0x49) | 0x00000000 | 0 | torque-arb Counter B, see below |
| 81 (0x51) | 0x00000C00 | 0 | ADC/sensor timeout, see below |

## The group-status SELECTION mechanism — new this session [EVIDENCE, full decompile chain]

A UDS 0x19/0x02 response for a multi-member group is **NOT an OR across members**. Chain:
`FUN_0004c5a6` (24-cycle cache sweep) → `FUN_0004c560(group_idx)` → `FUN_0004c130(group_idx,1,list,cats)`
(scans a **live RAM fault-log array** pointed to by `*(short**)(tp-0x7fcc)`, via `FUN_00047d06` which
searches that array for each group member and, if found, returns its slot; results are **sorted by a
priority byte read from that SAME live array**, offset+9 per 0x32-byte entry) → the group reports
`FUN_000475d2(winning_fault_id)` = `*(byte*)(gp+0x634b+fault_id)`. **If NOTHING in the group currently
qualifies in the live log, it falls back to the group's literal FIRST ROM member** (fault_id 4 for group
21) and reports THAT one's `gp+0x634b` byte.

The returned byte is masked `& 0xce` (`0b11001110` = bits 1,2,3,6,7) before being handed to the UDS
layer — **bits 0 (testFailed), 4 (testNotCompletedSinceLastClear), 5 (testFailedSinceLastClear) are
UNCONDITIONALLY zeroed, always, regardless of true internal state.** Independently confirmed this is by
design, not an oversight: `eps-read-dtcs.py`'s own `dtc_status_description()` only decodes bits
0x02/0x04/0x08/0x40/0x80 — exactly the surviving bits.

**Consequence — the central open item:** because group 21 has 38 members and the display shows only ONE
priority-selected representative, **a fresh trip of fault_id 28/29 (the damper shadow monitors) would be
INVISIBLE in this read if fault_id 4 (or any other already-logged member) currently outranks it in the
live-log priority sort — a value that lives only in RAM and could not be read (`0x23` denied, NRC 0x11,
on this ECU in all 3 captures spanning its whole history).** `0xF00049`'s unchanged status is therefore
**suggestive but not dispositive** against a fresh 0x1c/0x1d trip. It IS dispositive that **no group
anywhere (including 21) shows a fresh `pendingDTC`/`testFailedThisOperationCycle` bit** — under standard
2-trip DTC maturation, a first-ever trip of a group leaves a visible `pendingDTC` mark that outlives one
operation cycle; we see that behavior working correctly on `0xC41668` (which DID gain a fresh bit), so
the absence on `0xF00049` is real evidence, just not a proof, given fault_id 4 was ALREADY confirmed
pre-V21 and a same-fault_id-4 repeat trip would not add a NEW bit under that same 2-trip model.

## Fresh-vs-stale verdict per DTC

1. **`0x540011` (fault_id 17)** — STALE / never fired. Byte-identical across all 3 captures (0x40 only).
2. **`0xC41668` (fault_id 81, group 18)** — **GENUINELY FRESH signal.** `0x08→0x0C`, pendingDTC newly
   set. Trigger confirmed by decompile: `FUN_00053ccc` (ADC/sensor-conversion readiness dispatch,
   watches `gp-0x6bae` bit2 + 3 raw ADC reads via `FUN_000215c8/e6/604`) → counter `gp-0x32f4` saturates
   at `0x5DC`=1500 cycles → `FUN_0005471a(1,1)` → `FUN_00016de6(0x51,1,1,...)`. **Non-EPS-disabling**
   (descriptor bit0=0). Not on the damper path — no reference to `gp-0x6bd0` anywhere in `FUN_00053ccc`.
   Cause of the fresh trip not identified this session; plausible candidate is a flash/reflash-adjacent
   voltage transient, but this is [BELIEF, unconfirmed].
3. **`0xD48394` (fault_id 73, group 20)** — **CHANGED (`0x40→0x48`, confirmedDTC newly set) but BEST
   EXPLAINED AS STALE, from a documented ~3.5-week-old event, not V75.** This is DTC 0x49 = "torque-arb
   Counter B" — `builds/v18_v49/build_v37_tva.py`'s own text documents an **on-car trigger of exactly this DTC during
   V36 testing (2026-07-14)**: "under sustained torque>112 the DTC counter free-runs to 100 ... and fires
   STEER_STATUS=7 + `FUN_00016de6(0x49,1,1,1)` = DTC 0x49. That set a burst of dashboard warning lights
   and dropped LKAS." V37 (built same session) permanently disabled the mechanism by raising cal
   `0xC64B8` (`tp+0x74b8`) from 112 to 0xFF — since the gated signal `gp-0x682f` is itself byte-clamped
   to max 255, `255 < gp-0x682f` can never be true. **Verified BYTE-LEVEL this session** that `0xC64B8 =
   0xFF` on the STOCK image is 112 (0x70) but reads **0xFF** on `_v74_engagedcols_x12_plain_image.bin`
   AND on `_v75_c566_ex1200_magprobe_plain_image.bin` — i.e. the mechanism was dead on BOTH the actual
   V74 and the actual V75 flashed images. The counter (`gp-0x6758`) cannot have advanced during the V75
   incident. The `confirmedDTC` bit's appearance is best read as the DTC finally maturing (2nd trip, or
   simply a delayed status write) from the documented V36-era pending state — **unrelated to V75, non-EPS
   -disabling regardless** (descriptor bit0=0).
4. **`0xF00049` (group 21, 38 members incl. 0x1c/0x1d)** — **UNCHANGED across all 3 captures spanning
   this kit's ENTIRE recorded history.** The ONLY EPS-disabling group of the 5. See the caveat above:
   this is evidence against a fresh 0x1c/0x1d (or any other member's) trip, strengthened by the fact the
   read correctly showed a fresh bit elsewhere (`0xC41668`) when one genuinely occurred, but it is **not
   a proof**, because the group's displayed representative is priority-selected from a live RAM array
   this ECU's `0x23` service will not let us read (denied NRC 0x11, all 3 captures, all 3 firmware eras).
   Best circumstantial account: the representative is fault_id **4** (`FUN_00019204`, motor-init
   self-test — **fires only once, at power-on**, matching a stable, non-recurring historical event) —
   consistent with total silence on this group across a ~6+ week testing span with dozens of ignition
   cycles.
5. **`0xF00055` (fault_id 72)** — STALE / never fired. Byte-identical across all 3 captures (0x40 only).

## Whether the observed set is consistent with "hard shutdown fired"

**All 5 observed DTCs are structurally NON-EPS-disabling except `0xF00049`, and `0xF00049` shows no fresh
bit.** If the V75 hard-shutdown latch (`gp-0x685c=1`, per
`reference-accord-consistency-monitor-hardshutdown.md` / `reference_accord_hard_shutdown_full_map_v75_incident.md`)
really fired via the documented `FUN_00016de6`→`FUN_00018738` DTC path, this read **does not corroborate
it** — it is either (a) genuine evidence the DTC-based monitors (Monitor 1/2, `FUN_00034350`/`347b8`,
`FUN_00045a20`) did NOT trip, strengthening the "proximate monitor not identified" verdict already on
record, or (b) a fresh 0x1c/0x1d trip masked behind fault_id 4 in the group-21 display — genuinely
unresolved from static analysis alone. **This does not change the mechanism finding** (which member wins
the UDS display has no bearing on whether `FUN_00018738`'s per-fault_id threshold logic itself latched —
that check runs on the individual fault_id inside `FUN_00016de6`, independent of display selection) —
it only limits what THIS READ can tell us about which monitor fired.

## What would resolve the remaining ambiguity
- A **live** `0x23` read of `gp+0x634b+0x1c` and `gp+0x634b+0x1d` (RAM) would show fault_id 28/29's own
  status directly, sidestepping the group-representative-selection question entirely — but `0x23` reads
   to gp-relative fault-state addresses have been denied (NRC 0x11) in every capture on this ECU to date;
  no reason to expect a retry would succeed.
- Alternatively, `FUN_0004786e` (the live-log entry-count function) and the pointer at `tp-0x7fcc`'s
  pointee were not traced to their RAM layout this session — doing so would at least establish array
  capacity/eviction policy, informing whether an old fault_id-4 entry could ever be displaced.

## Related
[[reference_accord_dtc_construction_mechanism]] (superseded on the "OR across group" assumption — this
file corrects that to priority-selection) · [[reference_accord_consistency_monitor_hardshutdown]] ·
[[reference_accord_hard_shutdown_full_map_v75_incident]] · [[reference_accord_gp6bd0_shadow_faultpath_0x4179_0x417a]]
