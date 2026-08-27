# HANDOFF — 2026-07-10 — V31U: UDS-over-CAN RAM telemetry WORKING (DID 0x4801)

**Platform:** 2020 Honda Accord, `39990-TVA-A160`, Renesas uPD70F3508 / V850E2. **STOCK analysis program =
`code.bin`** (`../accord-firmware/analysis-2020accord/stock_fw_dump/code.bin`, flat base 0 → file offset == address). Bases:
`gp(r4)=0xFEDF8000`, `tp(r5)=0xBF000`. **V31U is FLASHED on the operator's car and its telemetry is
live-validated.**

**Supersedes** `docs/guides/SPEC-uds-can-ram-telemetry-a160.md` (which had the wrong table base + request address —
corrected in that file's banner) and the earlier UDStelem build. Read alongside the corrected memories
`memory/reference/can/reference_accord_uds_did_read_surface_a160.md` and
`.claude/agent-memory/firmware-codepath-tracer/reference_accord_a160_rdbi_handlerptr_live_dispatch.md`.

---

## 0. One-line state

`39990-TVA,A160-V31U-UDStelem-DID4801-RAMread-0x13000-0x100000.rwd` is **FLASHED and WORKING**: it is the
proven-drivable V31 cal (byte-identical) plus a repurposed UDS DID `0x4801` that reads four gentle-EME RAM
globals over CAN. On-car, `|column torque|` and `angle` track the wheel live; the two LKAS voters read 0
because openpilot was unplugged (they only move during an LKAS-active drive — the gentle-EME regime).

---

## 1. What works now (the channel)

- **Request:** ISO-TP 29-bit to **`0x18DA30F1`**, payload `22 48 01`. **Response** from **`0x18DAF130`**:
  `62 48 01 <b0..b7>`, 8 data bytes = **4× little-endian u16**:
  | bytes | signal | RAM addr | gp off |
  |---|---|---|---|
  | 0:1 | voter-MAX torque | `0xFEDF159E` | gp-0x6a62 |
  | 2:3 | voter-AVG torque | `0xFEDF15A2` | gp-0x6a5e |
  | 4:5 | \|column torque\| | `0xFEDF3098` | gp-0x4f68 |
  | 6:7 | angle | `0xFEDF133C` | gp-0x6cc4 |
- **Reader:** `tools/bench_uds_telem_read.py` (defaults already correct: addr `0x18DA30F1`, DID `0x4801`,
  bus 1, ELM327). `python3 bench_uds_telem_read.py --did 0x4801 --bus 1 --seconds 15 --yes`.
- **On-car proof (2026-07-10, `tools/uds_telem_20260710_163545.csv`, 371 reads):** `coltq` 268 distinct
  values 10..3810; `angle` 336 distinct 351..64847; `max`/`avg` static 0 (no LKAS). vs the pre-V31U reads
  (bit-exact `0/5828/104/0` under a full wheel yank) this is the live/stale flip.

---

## 2. Root-cause journey (why it took this long)

Two independent bugs, both now fixed:

1. **Wrong ECU address.** The bench tool + SPEC used `0x18DA80F1` (copied from a docstring example `b'80'`).
   The A160 EPS answers on **`0x18DA30F1`** (resolved from the firmware `%` header; the flasher dry-run TX
   proved it). Reading the wrong address got no reply → panda's `UdsClient` blocked in `bulkRead` → the
   "hang". Fixed in `tools/bench_uds_telem_read.py` (commit `c9c34db`), plus a hard-timeout canary so a
   wrong addr can't freeze the terminal again. Also reverted `--safety` to `elm327` (ALLOUTPUT injected on
   the ADAS bus and tripped Road Departure Mitigation).
2. **Off-by-one-ENTRY in the RDBI dispatch patch.** The RDBI per-DID table's TRUE base is **`0xB77FC`**
   (not `0xB7800`), stride `0x14`, struct `u16 did; u16 declared_len; u32 gate; u32 session; u32 group;
   u32 handler_ptr`. The **live per-DID payload dispatch reads `handler_ptr` at entry+0x10 and calls it
   with a ctx POINTER in r6** (`FUN_000209ea`, drained per-tick by `w_steer_control_task` after
   `FUN_00021036` arms a pending bit). Proven live: DID `0xF181` builds its app-id string through its own
   `handler_ptr` with the identical `ctx+0xC=len` / `FUN_000211ba` / `FUN_0002114e` / `FUN_0002073a` idiom
   the cave uses. **The old UDStelem build wrote the cave pointer into DID `0x4800`'s handler_ptr
   (`0xB780C`) instead of DID `0x4801`'s (`0xB7820`)** — so `0x4801` reads ran the stock handler and
   returned constant/stale buffer bytes. (An earlier tracer wrongly called `handler_ptr` "dead data" because
   it's called indirectly through the table → no direct xref; the `sld.w 0x10,ep,r28; jmp r28` site is the
   real dispatch. Retraction is noted in the agent memory
   `reference_accord_a160_rdbi_dispatch_table_offbyone.md`; the correct model is
   `reference_accord_a160_rdbi_handlerptr_live_dispatch.md`.)

`groupID` (byte at entry+0xC) → 7-slot jump table `0xB7568` is an **orthogonal** general response-builder
state dispatch; it passes a **masked scalar** in r6, so repointing a groupID slot to the cave would corrupt
(the cave needs r6=ctx pointer). We did NOT touch groupID.

---

## 3. V31U build + verification

Builder: `analysis-2020accord/builds/telemetry/build_v31u_uds_telem_tva.py` (plain image `../accord-firmware/analysis-2020accord/_v31u_plain_image.bin`). Built from
STOCK `code.bin`.

- **= V31 cal verbatim** (gain2x/clamps/ramp + corridor×4 + boost-floor 4096 + float mirror + PN). Byte-diff
  vs the proven `V31` .rwd = **74 bytes, ALL telemetry** — drivability is byte-identical to V31.
- **+ corrected UDS patch (TRUE `0xB77FC` scheme):**
  - `0xB7820` handler_ptr `0x0004D8DC → 0x000C4E00` (cave)  ← **the fix the old build missed**
  - `0xB7812` declared_len `56 → 10` (= 8 data + 2 DID echo)
  - `0xC4E00` 72-byte cave handler (verbatim from the old build; ABI verified: ctx ptr in r6 matches the
    `handler_ptr` call site) reads the 4 globals, appends 8 LE bytes.
  - `0xB780C` (DID 0x4800's handler_ptr) **left STOCK** `0x0004D5C2` — guarded (the old build's mistake).
- **Verify:** 49/49 CRC PASS, ECU-decode==patched, all readback asserts, byte-diff vs stock = 101 bytes in
  expected locations only, **no control code touched**. The cave is a register-clean clone of the stock
  `0xF181`-class handler (only store is `st.h r15,0xc[r6]` = the response-length field; only scratch regs
  r6/r7/r15; saves/restores lp) — verified byte-for-byte against `0x4F6D6` and empirically (executes
  correctly on-car).

**Safety note about the previously-flashed (superseded) UDStelem build:** it had the cave on DID `0x4800`,
so a dealer tool reading `0x4800` would have gotten the cave's 4-signal read instead of `0x4800`'s stock
fault data — benign (openpilot never reads it), and V31U (built from stock) restores `0x4800` fully.

---

## 4. Remaining goal — capture the gentle EME live

The two voters (`gp-0x6a62`/`gp-0x6a5e`) only move during an LKAS-active drive (that's the gentle-EME
regime: `gp-0x6a62 ≥ cal 0xC6312` = 320 fires the engage-SM torque disengage). So the actual capture needs
**openpilot steering AND the UDS poll at the same time.** The operator's red panda shares the ONE comma
harness cable, so it can't poll while the comma drives. Two ways to get simultaneous LKAS + poll:
- **CAN Y-splitter** on the comma cable (comma drives, red panda splices in parallel on bus 1 and polls).
- **← THE NEXT-SESSION TASK:** make openpilot itself poll + log the DID (below) — cleaner; no extra hardware.

Once captured: correlate the four signals at the ~90 ms cut against comma-visible 399 (STEER_TORQUE /
gp-0x4f60) + 427 (STEER_MOTOR_TORQUE = the delivered-torque cut) + STEER_STATUS to identify which voter
crosses 320 first, then design the real gentle-EME fix (vs the blunt V33 threshold-to-65535 disable).

---

## 5. NEXT SESSION — fork sunnypilot to log the UDS telemetry into rlogs

**Goal:** have the operator's sunnypilot fork poll DID `0x4801` (`22 48 01` → `0x18DA30F1`, resp
`0x18DAF130`) during a normal LKAS drive and record the decoded 8-byte telemetry into the rlog, so the
gentle-EME cut is captured with the voters live — no second panda, no Y-splitter.

**Why this is the right shape:** openpilot ALREADY does UDS-over-CAN via the panda — see
`openpilot/selfdrive/car/isotp_parallel_query.py` and `fw_versions.py` (firmware fingerprinting queries at
startup). That machinery (ISO-TP over `panda`, `UdsClient`-style) is the template. The bench reader
`tools/bench_uds_telem_read.py` has the exact working read logic (addr, DID, ISO-TP reassembly, decode) to
port in.

**The three hard parts to solve next session (research these first, in order):**
1. **TX permission during active control.** openpilot's Honda safety model only allows specific control TX;
   a 29-bit diagnostic frame to `0x18DA30F1` is normally blocked. Startup FW queries work because the panda
   is in **OBD-multiplexing** mode with control off. Determine whether we can (a) periodically enable a
   diagnostic/OBD window during driving, (b) use a safety-allowed diagnostic address, or (c) patch panda
   safety to allow this one tester addr. This is the gating question — settle it before writing much code.
   (Note the EPS diagnostic is on the **camera/EPS bus = comma bus 1**, the same wire openpilot uses.)
2. **Where to poll.** A small periodic querier (new process, or a thread in an existing one) that sends
   `22 48 01`, reassembles the multi-frame ISO-TP response (the reply is >7 bytes → first-frame + flow
   control + consecutive), decodes 4× LE u16. Poll as fast as the round-trip allows (target ≥50 Hz for the
   ~90 ms cut; the bench tool sustains tens/sec).
3. **How to log into rlog.** Add a cereal message (or reuse spare fields) carrying the 8 bytes + a
   timestamp, publish it, and confirm `system/loggerd` records it (loggerd logs the cereal services it
   subscribes to — the new service must be added to the logged set). Then `rlog-tools/` (in this repo) can
   extract it post-drive, and it lines up with the comma-visible 399/427 already in the log.

**Deliverable of that session:** a sunnypilot fork branch that logs `[MAX, AVG, |coltq|, angle]` at ≥tens of
Hz into the rlog during LKAS, plus an rlog-tools extractor. Keep the kit's iron rules (no flash / no new CAN
TX pattern without the operator naming it; the diagnostic read is SID 0x22 = state-changeless, but it IS a
new TX during driving — treat the safety question seriously).

---

## 6. Iron rules (unchanged) + artifacts

- **No CAN/UDS send or flash without the operator naming the exact payload/file + bus; repeat it back.**
- Analyze STOCK `code.bin` only; `_*_plain_image.bin` are build outputs.
- Before any on-car flash: openpilot/pandad killed. `comma4_can_inventory.py` / `panda_can_sniff.py` /
  `panda_rx_health.py` are read-only (SILENT) and safe.
- **Artifacts this session** (pushed to `main`): `builds/telemetry/build_v31u_uds_telem_tva.py`, `../accord-firmware/analysis-2020accord/_v31u_plain_image.bin`, the
  V31U `.rwd`, the fixed `bench_uds_telem_read.py`, diagnostics `panda_rx_health.py` / `panda_can_sniff.py`
  / `sniff_can_id.py`, the corrected RDBI-dispatch memories, and this handoff.
