# HANDOFF — 2026-07-11 — StarPilot EPS UDS telemetry logging + rlog analysis (next)

**Platform:** 2020 Honda Accord, `39990-TVA-A160`, running **V31U** EPS firmware (FLASHED, live-validated —
see `docs/HANDOFF-2026-07-10-v31u-uds-telemetry-working.md`). Openpilot side = the operator's **StarPilot**
fork on a **comma 4** at `/data/openpilot`.

**Builds on** `docs/HANDOFF-2026-07-10-v31u-uds-telemetry-working.md` §5 ("NEXT SESSION — fork sunnypilot to
log the UDS telemetry into rlogs"). That task is now DONE (code side). This session wired openpilot itself to
poll DID `0x4801` during LKAS and log it into the rlog. **NEXT = analyze the operator's rlogs** (being brought
into this repo) to catch a gentle EME live.

---

## 0. One-line state

StarPilot fork now **polls the EPS gentle-EME RAM telemetry over UDS during driving and logs it to the rlog**
(new `epsTelemetry` cereal service, ON by default). Code is built, schema-validated, end-to-end tested
against a synthetic rlog, and **pushed to the operator's fork `github.com/raayyymond/StarPilot` on both
`StarPilot` and `Dom` branches**. NOT yet run on-car. An rlog extractor lives in `rlog-tools/`. Operator is
bringing real rlogs into this repo for the actual gentle-EME analysis.

---

## 1. What was built (StarPilot fork)

A UDS poller inside `card.py` sends `22 48 01` to the EPS during LKAS, reassembles the ISO-TP reply from
`0x18DAF130`, decodes 4× LE u16, and publishes a new `epsTelemetry` cereal message that `loggerd` records
full-rate into the rlog. Read-only (SID 0x22/0x3E); the panda safety model independently gates it.

**7 files (identical on both branches):**
| file | change |
|---|---|
| `opendbc_repo/opendbc/safety/modes/honda.h` | Whitelist EPS tester addr `0x18DA30F1` on **bus 1** in the Bosch TX lists (`HONDA_BOSCH_TX_MSGS` + `HONDA_BOSCH_LONG_TX_MSGS`), `tx_hook`-guarded to ONLY UDS RDBI (`0x22`) / TesterPresent (`0x3E`) single frames + ISO-TP flow control (`0x30`). ⚠ compiled into panda firmware → needs a panda reflash (auto on a source build, see §3). |
| `cereal/custom.capnp` | Reserved struct → `EpsTelemetry @0xc2243c65e0340384` (fields in §2) |
| `cereal/log.capnp` | Event union field `epsTelemetry @137 :Custom.EpsTelemetry` |
| `cereal/services.py` | `"epsTelemetry": (True, 50., 1)` — `should_log=True` → loggerd records it to rlog |
| `common/params_keys.h` | `EpsTelemetryEnabled` param, **default `"1"` (ON)** |
| `selfdrive/car/eps_telemetry.py` | **NEW** `EpsTelemetryPoller` — single-outstanding-request ISO-TP state machine, ported from `tools/bench_uds_telem_read.py` |
| `selfdrive/car/card.py` | Construct poller (Honda brand only), drive it from `state_update` (reuses card's sole `sendcan` publisher + the `can` stream it already drains), publish `epsTelemetry` in `state_publish`; read `EpsTelemetryEnabled` with `default=True` |

**Where it lives (git):**
- Operator's fork: **`git@github.com:raayyymond/StarPilot.git`** (pushed):
  - `StarPilot` branch: `50fb0628` (default-on) ← `db8ec76a` (feature) ← `099b04816` (upstream StarPilot base)
  - `Dom` branch: `829dc04c` (default-on) ← `9e94607e` (feature) ← `2a3d2744` (upstream `firestar5683/Dom`, "Update camerad"). Cherry-picked; `params_keys.h` auto-merged clean.
- Local upstream clone `../openpilots/StarPilot` (`firestar5683`): currently checked out on `Dom`; local
  `StarPilot` branch retains the original commits; the pre-existing local `OP16Deep` model-swap commit is
  preserved as tag `op16deep-backup`.

**Behavioral note:** default-ON means every **Honda** running this fork transmits the diagnostic reads on bus 1
during driving (read-only, panda-gated). Non-Honda cars never construct the poller. If the operator wants it
scoped to the Accord only, gate poller construction on `"ACCORD" in self.CP.carFingerprint` instead of
`brand == "honda"` (offered, not done).

---

## 2. The telemetry channel (what's in the rlog)

`epsTelemetry` (custom.capnp `EpsTelemetry`), published at ~ECU round-trip rate (tens of Hz) while onroad:

| capnp field | type | meaning | RAM addr / gp | gentle-EME gate |
|---|---|---|---|---|
| `valid` | Bool | full 8-byte decode this sample | | |
| `voterMax` | UInt16 | voter-MAX column torque | `0xFEDF159E` / gp-0x6a62 | **≥ 320 → `0xC6312` engage-SM torque disengage (V33 decider — the prime suspect)** |
| `voterAvg` | UInt16 | voter-AVG column torque | `0xFEDF15A2` / gp-0x6a5e | ≥ 320 → `0xC62FE` deliver-commit gate (V35) |
| `colTorque` | UInt16 | \|column torque\| | `0xFEDF3098` / gp-0x4f68 | ≥ 4096 → Gate-5 (`0xC61EA`) |
| `angle` | UInt16 | steering angle | `0xFEDF133C` / gp-0x6cc4 | angle-#1 suspect |
| `did` | UInt16 | DID polled (`0x4801`) | | |
| `requestMonoTime` | UInt64 | mono ns the request was sent | | |
| `responseMonoTime` | UInt64 | mono ns the reassembly finished | | |
| `rawResponse` | Data | raw UDS bytes `62 48 01 <10 data>` | | |

**Wire format (verified against V31U on-car CSV, `tools/uds_telem_20260710_163545.csv`):** request `22 48 01`
→ `0x18DA30F1` bus 1; response `0x18DAF130` = `62 48 01` + **10** data bytes = 13 total (multi-frame ISO-TP:
FF + FC + CF). The **first 8** of the 10 data bytes are the 4× LE u16; the trailing 2 are zero padding. The
poller reads the on-wire declared length, strips `62 48 01`, and unpacks the first 8 — robust to the 8-vs-10
data-byte detail. (declared_len patched to `0x0A`=10 in the cave handler; see the V31U handoff §2.)

---

## 3. Build + deploy on the comma 4

The feature is source-only; StarPilot **ships prebuilt binaries and runs them by default**, so a plain branch
update runs the stale prebuilt and does NOT pick up these changes. Force a source build once, then the panda
auto-reflashes.

**Install URL** (comma 4 setup → Custom Software; the device prepends `https://installer.comma.ai/`):
```
raayyymond/Dom          # or raayyymond/StarPilot
```
Format proven by StarPilot's own default `installer.comma.ai/firestar5683/StarPilot`
(`tools/agnos/patch_system_reset_image.py:186`). Verify it resolves by opening
`https://installer.comma.ai/raayyymond/Dom` in a browser (installer script, not 404).

**Make the source changes take effect (+ panda reflash), on the comma 4 over SSH:**
```bash
cd /data/openpilot
# if switching the existing install to Dom instead of a URL reinstall:
git remote set-url origin https://github.com/raayyymond/StarPilot.git
git fetch origin Dom && git checkout -B Dom origin/Dom
# THE KEY STEP — build from source instead of prebuilt:
echo -n 0 > /data/params/d/UsePrebuilt
tmux kill-server
scons -j$(nproc)          # compiles openpilot + cereal gen + panda firmware
sudo reboot               # pandad sees new panda signature -> reflashes comma4 panda automatically
```
Panda auto-reflash is confirmed in `selfdrive/pandad/pandad.py:88` (`panda_signature != fw_signature →
panda.flash()`); the panda firmware includes the opendbc safety code (`panda/board/main.c:13
#include "opendbc/safety/safety.h"`, build uses `opendbc.INCLUDE_PATH` → the `opendbc_repo/` we edited).

Leave `UsePrebuilt=0` in place — from then on it behaves like a normal on-device dev branch (incremental
scons, fast boots).

---

## 4. rlog analysis tooling (THIS repo, `rlog-tools/`)

- **`rlog-tools/extract_eps_telemetry.py`** (NEW) — pulls `epsTelemetry` + steering context into a long-form
  CSV time-indexed by `logMonoTime`:
  - `src=eps`: `valid, voter_max, voter_avg, col_torque, angle, did, req_mono_ns, resp_mono_ns, rtt_ms, raw_hex`
  - `src=cs`: `str_angle_meas, str_torque_driver, str_torque_eps, str_pressed, steer_fault_temp, steer_fault_perm, v_ego` (mirrors CAN 399/427)
  - `src=cc`: `lat_active, long_active, enabled`
  ```bash
  python rlog-tools/extract_eps_telemetry.py "<route>--*/rlog.zst" -o eme.csv
  python rlog-tools/extract_eps_telemetry.py --eps-only rlog.zst -o eps.csv
  ```
- **Schema mirror** — `rlog-tools/cereal/custom.capnp` + `log.capnp` were updated with the SAME `EpsTelemetry`
  struct + `epsTelemetry @137` (identical `@ids` → identical wire format) so `rlog_parse.py` can decode the
  StarPilot rlogs. `read_messages()` loads `rlog-tools/cereal/log.capnp`.
- **Validated end-to-end this session:** synthesized a fake rlog with `epsTelemetry`+`carState`+`carControl`
  events, ran the extractor, confirmed decode order and values (raw `0000000071006cfb0000` → max=0 avg=0
  coltq=113 angle=64364; a 4-sample voter sweep 100→450 crossing the 320 cal). pycapnp round-trip OK.
- **STATUS: these three files are UNCOMMITTED in this repo** (`rlog-tools/extract_eps_telemetry.py` untracked;
  `rlog-tools/cereal/{custom,log}.capnp` modified). Commit them (with this handoff) before/at the start of the
  analysis session.
  - Note: pycapnp crashes loading the *StarPilot* cereal on Windows (heavy `$Cxx` import graph) — this is a
    Windows/pycapnp issue, NOT a schema error (unmodified `car.capnp` crashes the same way). The `rlog-tools/`
    mirror loads fine because it's the minimal self-contained copy.

---

## 5. NEXT TASK — analyze the operator's rlogs (the actual gentle-EME hunt)

**Operator is bringing rlogs into this repo.** They should contain `epsTelemetry` **only if** the comma 4 was
running a **source build** of the fork (§3) during an **LKAS-active** drive (the two voters only move under
LKAS — that's the gentle-EME regime). Confirm first with `python rlog-tools/rlog_parse.py <rlog>` → look for
`epsTelemetry` in the which-counts.

**The analysis (the whole point):** at each gentle-EME cut (~90 ms delivered-torque drop), correlate the four
EPS-internal signals against their gates and against the comma-visible CAN, to find **which gate fires first**:
1. Extract with `extract_eps_telemetry.py` → CSV (eps + cs + cc rows, shared `t_ns` timeline).
2. Find the cut: `steer_fault_temp` rising edge and/or `str_torque_eps` (CAN 427 STEER_MOTOR_TORQUE) collapse,
   and/or `lat_active` drop.
3. In the ~100–200 ms window around it, check each EPS signal vs its threshold (§2 table):
   - `voter_max ≥ 320` → the `0xC6312` engage-SM torque disengage (V33 decider — **primary hypothesis**)
   - `voter_avg ≥ 320` → `0xC62FE` (V35)
   - `col_torque ≥ 4096` → Gate-5 `0xC61EA`
   - `angle` → the angle-#1 suspect
   Whichever crosses its threshold *first, at the cut* is the real trigger.
4. Cross-check timing against comma-visible 399 (`str_torque_driver`/STEER_TORQUE) + 427
   (`str_torque_eps`/STEER_MOTOR_TORQUE) already in the same rlog (same `logMonoTime` clock).

**Deliverable:** identify the first-crossing gate → design a *targeted* gentle-EME fix (raise/reshape only
the offending gate), instead of the blunt `V33` (`0xC6312` 320→65535 disable) or `V35` (`0xC62FE`) threshold
sledgehammers. See `docs/HANDOFF-2026-07-02-v33.md` and the gentle-EME root-cause handoffs
(`-2026-06-29-gentle-eme-v32.md`, `-2026-06-30-sensorA-identity-gate-scale.md`).

---

## 6. Open items / caveats

- **Poll rate vs the 90 ms cut:** effective rate = ECU round-trip (tens of Hz, ~1 sample / 20–30 ms). Enough to
  bracket a 90 ms cut but not to resolve its leading edge finely. If samples are too sparse at the cut, consider
  raising the poll cadence or dropping the TesterPresent keepalive.
- **`epsTelemetry` absent from a log** ⇒ either not a source build (prebuilt ran), not Honda-fingerprinted,
  `EpsTelemetryEnabled=0`, or the panda blocked the TX (panda not reflashed with the honda.h change).
- **panda safety unit tests** (`opendbc/safety/tests/test_honda.py`) may need the new TX msg added to their
  expected list if the operator runs them; does not block the on-device build/flash.
- Accord-only scoping of the poller (vs all Hondas) is available if wanted (§1).
- The `frpc_darwin_*` binaries in the StarPilot working tree are unrelated (Windows couldn't write them during
  a reset); they were restored and are NOT part of any commit.

---

## 7. Iron rules (unchanged) + artifacts

- **No CAN/UDS send or flash without the operator naming the exact payload/file + bus.** The three frames this
  fork transmits (all read-only, operator-approved this build): `0x18DA30F1` bus 1 ← `02 3E 80 …`
  (TesterPresent), `03 22 48 01 …` (RDBI 0x4801), `30 00 00 …` (ISO-TP flow control).
- Analyze STOCK `code.bin` for firmware questions; the RWD/telemetry channel spec is
  `docs/HANDOFF-2026-07-10-v31u-uds-telemetry-working.md` + `memory/reference_accord_uds_did_read_surface_a160.md`.
- **Artifacts this session:** StarPilot fork commits on `raayyymond/StarPilot` (`StarPilot` + `Dom`);
  `rlog-tools/extract_eps_telemetry.py` + schema mirror (uncommitted); this handoff.
