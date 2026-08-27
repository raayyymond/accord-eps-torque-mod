# HANDOFF 2026-07-27 (session 3) — the V53 drive result, and V54: the authority probe

**Nothing was flashed this session. No CAN was sent.** V53 was flashed and driven by the operator
*before* this session; this session analysed that drive and produced one build, unflashed.

**Predecessor:** `handoffs/2026-07/HANDOFF-2026-07-27-v53-fourframe2-plus-minsteerspeed0.md` (same date, session 2).
That handoff ends with a testable prediction. This one reports the result.

---

## 1. The question asked, and the answer

> *"I drove with the V53 RWD. The steer-to-zero feature worked. Are you able to see the four frame
> telemetry in the new rlog?"*

**No.** Zero frames of `0x6A0`–`0x6A3` across **301,824** CAN frames on buses 0/1/2/128/129 in route
`75604b0a432fdc89_0000001a` segment 0 (58 s, 641 distinct `(kind, bus, addr)` pairs). No stray unknown ID
anywhere that could be a misprogrammed `MID0W` either.

But the *interesting* result is that **the null carries no information about the cave**, and this session
proved that rather than assuming it. See §3.

---

## 2. ✅ Steer-to-zero is confirmed — and the model predicted it

Verified independently of the operator's report, from **raw CAN 399** rather than `carState`
(`STEER_STATUS = (byte4>>4)&0xF`, `STEER_CONTROL_ACTIVE = (byte4>>3)&1`):

```
raw 399 STEER_STATUS, whole segment:   status 0 = 5995 frames (100.0%)

  BELOW 5 km/h, latActive=True    n= 226    st0=226    | ctrl1=226
  BELOW 5 km/h, latActive=False   n=3532    st0=3532   | ctrl0=3532
  above 5 km/h, latActive=True    n=1206    st0=1206   | ctrl0=3 ctrl1=1203

openpilot 0xE4 below 5 km/h: 226 frames TORQUE_REQUEST=1, 224 with |torque|>50
```

`STEER_STATUS = 3` **never fires anywhere**, and there are 226 frames of `STEER_CONTROL_ACTIVE = 1` below
the old 5 km/h lockout — a cell that is **identically empty** on V38, where ST=3 *is* the sub-5 km/h gate.

This is the §7 prediction of the predecessor handoff, confirmed exactly. It is the **first time the golden
model has predicted an on-car state-machine change in advance and been right**, and it closes the
`0xC62EA` chain end to end: cal → two-sided window → ST=3 → `STEER_CONTROL_ACTIVE` → authority ramp.

⇒ **An rlog can now identify V53+ behaviourally** (ST=3 never firing), even though the version string
cannot distinguish any modified build.

⚠ **What V53 did to the vibration is UNANALYSED.** The prediction was deliberately two-sided — "if the
transient-just-after-pulling-away reading is right V53 should change it; if the sustained reading is
right it should not" — and *neither arm was tested*. Route 1a is a single 58 s segment, and the
newly-populated engaged-at-low-speed cell has not been examined for 21 Hz content. **That analysis is
free, requires no flash, and is the cheapest open item in the kit.**

---

## 3. ★ The telemetry null is UNINTERPRETABLE — and that is the load-bearing finding

The obvious reading — "the STRB fix didn't work either" — is not supported. In the **same rlog**:

| ID | in a Honda DBC? | present? |
|---|---|---|
| `0x14A`, `0x18F`, `0x1AB` — the three openpilot knows | yes | **yes**, 97.3 / 97.4 / 48.7 Hz |
| `0x19F`, `0x32E`, `0x64D`, `0x660`, `0x722`, `0x723` — **stock firmware broadcasts these** | some | **absent** |
| `0x669`, `0x750`, `0x674` | **no — in no Honda DBC** | **yes** (`0x750` at 50 Hz) |
| `0x6A0`–`0x6A3` — FOURFRAME2 | no | absent |

Two conclusions follow, and they matter in opposite directions:

1. **"openpilot didn't know the ID" is excluded.** The `can` service is raw pandad frames logged before
   any DBC exists in the pipeline; the DBC is applied downstream in `card`/carState. Non-DBC IDs are
   demonstrably logged. So the frames are genuinely not arriving.
2. **"the cave didn't fire" is *not* established.** Six IDs the stock firmware genuinely transmits are
   equally absent. The gateway-whitelist model predicts exactly this null whether the cave worked
   perfectly or not at all.

⇒ 🛑 **A new-mailbox CAN channel cannot deliver a measurement on this car.** Two attempts
(FOURFRAME with the STRB defect, FOURFRAME2/V53 with it fixed) have now returned silence, and the second
silence is undiagnosable without a tap upstream of the gateway. **Do not build a third.** Recorded in
`docs/BUILD-LINEAGE.md` Part 1 as a boxed rule.

---

## 4. Channel audit — what a piggyback can actually carry

Audited against the fork on disk (`opendbc/car/honda/carstate.py`, `opendbc/safety/modes/honda.h`,
the generator DBCs), not from memory. **"Constant on the wire" is not "free".**

| byte | DBC content | openpilot reads? | genuinely free |
|---|---|---|---|
| `0x14A` byte4 | bits 2:0 = `STEER_SENSOR_STATUS_1/2/3` (live in firmware) | **no** — only bytes 0-3 | **5 bits** @100 Hz |
| `0x18F` byte5 | bits 3:0 = `STEER_CONFIG_INDEX`; **bits 5:4 LIVE** (`gp-0x6880 & 3`, packer `0x55CAE`–`0x55CC2`) | no | 2 safe; **no hook located** |
| `0x1AB` byte0 | bit7 `CONFIG_VALID`, bit3, bits 1:0 = `MOTOR_TORQUE[9:8]` | no (427 never parsed) | 4, non-contiguous, 48.7 Hz |

**Corrections of record:**
- The memory note *"`0x18F` byte5 + `0x14A` byte4 are constant ⇒ a free 16-bit signal at 100 Hz"* is
  **wrong**. `0x18F` byte5 bits 5:4 are written by the firmware packer; they read constant on routes 13
  and 1a only because those bits happened not to change. A DBC-only audit misses this — check the
  **packer** as well as the DBC.
- Panda's Honda RX check list is `0x1A6`, `0x296`, `0x158`, `0x17C`, `0x326`, `0x1BE` — **none** of the
  three carriers, so no counter/quality gating from that direction.
- 🛑 **opendbc verifies Honda checksums** (`opendbc/can/dbc.py`). A bad checksum drops `can_valid`, which
  is a **disengage**, not a cosmetic glitch. Any piggyback must be written *before* the checksum call.

---

## 5. V54 — the build

```
_v54_plain_image.bin  SHA 233188ffa21d8ae685685a48410e0c15b49ffca8af2fa8d3684f987cf1a4710b
39990-TVA,A160-V54-LKAS-4x-V38base-minsteerspeed0-lockout0xC62EA-320to0
  -authority-gp0x6966-5bit-probe-can330-0x14A-byte4-bits7to3-100hz-caveC4B34-0x13000-0x100000.rwd
                      SHA 97ea51d2fa6b21d4584247be5571c34a5d3d15df742c2033324aae456c1c7517
```

**58 bytes off V38** in 5 runs: 44-byte cave @`0xC4B34`, 4-byte hook @`0x55C0E`, `0xC62EA` 320→0, two CRC
trailers. Builder `analysis-2020accord/builds/v50_v79/build_v54_tva.py` **imports** encoders + CRC gates from
`builds/telemetry/build_vfourframe_tva.py` and the lockout constants + safety scans from `builds/v50_v79/build_v53_tva.py`, so the only
thing typed fresh is the cave — the same "import, don't re-type" pattern V53 established.

```
000c4b34  ld.hu  -0x6966, gp, r7      ; AUTHORITY
000c4b38  shr    0x7, r7              ; 128 counts per bucket
000c4b3a  movea  0x1, r7, r7          ; +1 liveness bias
000c4b3e  movea  0x1f, r0, r6
000c4b42  cmp    r6, r7
000c4b44  bnh    0x000c4b4a
000c4b46  movea  0x1f, r0, r7         ; saturate
000c4b4a  shl    0x3, r7              ; -> bits 7:3
000c4b4c  ld.bu  -0x1514, gp, r6      ; 330 payload byte4
000c4b50  andi   0x7, r6, r6          ; preserve live status bits 2:0
000c4b54  or     r7, r6
000c4b56  st.b   r6, -0x1514, gp
000c4b5a  movea  -0x1518, gp, r6      ; re-exec displaced, LAST
000c4b5e  jmp    lp
```

### The hook site proves three things by itself

```
00055c0e  jarl   0x000c4b34, lp     <- our hook
00055c12  mov    0x8, r7            <- r7 REASSIGNED: dead at the hook, proven not assumed
00055c14  movea  0x14a, r0, r8      <- the literal 0x14A: this IS the 330 builder
00055c18  jarl   0x00057b24, lp     <- checksum runs AFTER us, and clobbers lp itself
```

Stock's own `jarl` overwrites `lp` four instructions later, which **proves** `lp` was dead at `0x55c0e`.
And the displaced instruction loads the buffer base as `gp-0x1518`, so `gp-0x1514` is arithmetically
**buffer+4** — byte 4 of the exact frame being built. No assumption anywhere in the chain.

### The encoding, and what each answer licenses

`wire = min((gp-0x6966 >> 7) + 1, 31)` → `0x14A` byte4 bits 7:3.

| wire | authority | `0xC6AF0` Q15 | V55 candidate |
|---|---|---|---|
| **0** | — | — | 🛑 **cave did not fire; drive is VOID** |
| 1–25 | ≤ 3199 | 32768 | lane at FULL bound ⇒ **mute** (Y→0) |
| 26 | 3200–3327 | knee | — |
| 27–28 | 3328–3583 | ramp | — |
| 29 | 3584–3711 | knee | — |
| 30–31 | ≥ 3712 | 0 | already clamped ⇒ hypothesis dies, **keep-live** (Y→32768) |
| mixed | — | — | the crossing **is** the trigger ⇒ flatten the ramp |

A coarser shift cannot work: the knees are only 327 counts apart, so `>>11` (the widest that fits 5 bits
unsaturated) puts both in the same bucket.

### Gates

50/50 CRC blocks, both bootloader walks, RWD decode-back with **every gate re-run on the readback**, and
the cave + hook **re-disassembled from the written image via GhidraMCP**.
**GATE 1 (RAM ownership):** writes one RAM byte (`gp-0x1514`, read-modify-write preserving bits 2:0);
allocates **no scratch RAM at all**, so the `gp-0x1500` failure class — which passed both static methods
and still failed on-car — does not arise; clobbers only r6/r7, a strict subset of V31P's proven-dead set.
**GATE 2 (closed-loop):** vacuous by construction — report-only, into a TX payload byte no control path
reads. `0xC6AF0` asserted stock; `0xC646C` = 3564; `0x454FE` stock `0x65BA` (no V42 ratchet fix,
matching the car).

---

## 6. Two design mistakes caught mid-build — both worth keeping

### ★ A dead probe must not decode as a valid reading
Smoke-testing `rlog-tools/probe/decode_v54_authority.py` against the **V53** rlog — firmware with no probe in
it — produced:

```
bucket 0, 5994 frames, 100.0%   "lane at FULL bound"
=> lane ran at FULL bound throughout: it CAN be the driver. V55 candidate = mute (Y->0).
```

A confident, actionable, entirely fabricated answer from a dead channel. Stock leaves those bits at zero,
so the unbiased encoding made "did not fire" indistinguishable from "low authority" — and this kit had
already eaten two silent telemetry nulls. Hence the **+1 bias**: a live probe can never emit 0. The
decoder now reports an all-zero drive as **VOID** and exits non-zero.
Generalises to any probe whose no-data state is a legal-looking value.

### Prefer a register field over a new opcode
The bias was first written as `add imm5,r7` (Format II op `0x12`) — a **new opcode value** whose only
evidence would have been the post-build re-disassembly. Replaced with `movea 0x1,r7,r7`:
`movea imm16,reg1,reg2` computes `reg2 = reg1 + imm16`, so using `reg1 = r7` instead of `r0` changes only
a **register field** in an encoder already verified against the real `movea 0x100,r0,r7` @`0x1d7ee` —
and the `reg1 != 0` form is live at the hook site itself. Same precedent FOURFRAME used for bc-vs-bnc.

---

## 7. Method traps recorded this session

1. **`Select-Object -First N` on a build pipeline truncates the pipe and kills the process.** The V54
   build appeared to succeed but had been terminated before writing its artifacts; the files were
   missing on the next read. Filter with `Select-String -NotMatch`, or capture the tail, never `-First`.
2. **`disassemble_bytes` without `dry_run` mutates the DB, and `close_program` then raises a modal
   save dialog that hangs the whole MCP server.** Recovery needed the operator to dismiss it by hand.
   The stale program also could not be deleted (`is in use`). **Workaround that avoids the lock
   entirely: copy the image to a distinct filename and import that** — it also guarantees a genuinely
   fresh import, defeating the stale-import trap in the same move.
3. A Ghidra program imported from a path is **name-bound to that path**; re-importing the same path after
   the file changes does not refresh it. Verify the copy's SHA *before* import, then disassemble.

---

## 8. Recommended next steps

1. **openpilot-side 21 Hz notch.** Zero brick risk, still untested rather than null. Keep the ±4096 rail
   fraction matched between runs — 14% of frames are railed and railed windows show no 21 Hz.
2. **Mine route `1a` for the C-low cell** — free, no flash. V53 populated "engaged below 5 km/h" for the
   first time. 226 frames is thin, but it is the cell route 13 structurally could not produce, and it
   breaks the speed/applied-torque collinearity that §5 of the predecessor handoff flagged.
3. **Flash V54**, one parking-lot drive, decode with `rlog-tools/probe/decode_v54_authority.py`.
   ⚠ **Check `wire == 0` first** — that means the cave did not fire and the drive proves nothing.
4. **The `0xC646C` decoupling** — a correctness fix, not the vibration fix.
5. Only then a `0xC6AF0` edit, in the direction the telemetry indicates.

🛑 **Flash only on explicit operator instruction naming the file and the bus.**

---

## 9. Collaterals updated this session

- `docs/STATE.md` — rewritten in place: V53 is now the on-car image with its confirmed result; V54 is the
  flash candidate; new "the measurement problem" section with the channel audit; workstream B closed;
  next steps renumbered.
- `docs/BUILD-LINEAGE.md` — `0xC62EA` moved into Part 1 as flashed + CONFIRMED; the boxed
  "new-mailbox CAN TX is unobservable" rule added; v54 added to the delta table; Part 4 flash status.
- `analysis-2020accord/model/eps_lkas_chain_model.py` — the V53 prediction block rewritten as
  PREDICTED/MEASURED with the on-car numbers; `Calibration.for_build("V54")` added; suite still exits 0.
- `analysis-2020accord/builds/v50_v79/build_v54_tva.py`, `rlog-tools/probe/decode_v54_authority.py` — new.
- `memory/` — 4 new files + `MEMORY.md`; two stale session-memory entries corrected (V53 "unflashed",
  and the "free 16-bit signal" claim).
- Both repos committed and pushed to `main`; artifacts to `accord-firmwares`.
