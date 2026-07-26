---
name: reference-accord-a160-app-uds-session-gate-and-egress
description: "2026-07-09 Ghidra-verified (code.bin/master.bin, program 'code.bin' in accord2020_ghidra): full byte-level trace of the 2020 Accord EPS (39990-TVA-A160) app ISO-TP UDS session-gate semantics AND confirmed CAN TX egress path for RDBI responses (req 0x18DA80F1/resp 0x18DAF180). Extends reference_accord_uds_did_read_surface_a160.md (that doc's table layout was correct; this fills in the actual comparison logic + the RX/TX call chains it didn't trace)."
metadata:
  node_type: memory
  type: reference
---

> ⚠ **CORRECTED 2026-07-10** — §2's table base (0xB7800) and its `FUN_0004D5C2 = "DID 0x4801 handler"`
> attribution are WRONG (off-by-one entry): true base **0xB77FC**; `0x4D5C2` is DID **0x4800**'s handler_ptr;
> DID 0x4801 = idx1 @0xB7810 (handler_ptr @0xB7820). The live per-DID dispatch reads handler_ptr@entry+0x10.
> Request addr is **0x18DA30F1**, not 0x18DA80F1. See `reference_accord_a160_rdbi_handlerptr_live_dispatch.md`
> and working build V31U. The session-gate + FCN0-egress trace itself (the reason this file exists) stands.

# Accord A160 app-UDS: session-gate bit semantics + confirmed FCN0 egress (2026-07-09)

Traced to explain an empirical "zero CAN response" to `22 48 01` (RDBI DID 0x4801) preceded only by
`3E 00` TesterPresent in default session. Full call chain below; all addresses in `code.bin`
(gp=0xFEDF8000, tp=0xBF000, flat base 0). Two Ghidra programs are open in `accord2020_ghidra` —
always target `code.bin` (anchor check: `0x410c0` = `ld.bu -0x67fe,gp,r12`).

## 1. SESSTATE byte — the single session/SA gate register

`gp-0x1548` (abs `0xFEDF6AB8`) is ONE byte packing TWO 4-bit fields:
- **high nibble (bits 4-7) = active-session bitmask**
- **low nibble (bits 0-3) = active-SecurityAccess-level bitmask**

Confirmed by 3 independent consumers:
1. **SID-level gate**, `FUN_0002075c` @`0x207a6-0x207c8`: `(SESSTATE>>4) & (service_entry_byte3 & 0xf)`,
   NRC `0x7F` (serviceNotSupportedInActiveSession) if zero. Service-entry table `0xB75E4` (stride 8),
   raw-byte-read-confirmed idx4 (SID 0x22/RDBI) = `01 00 2F 0D 01 09 08 00`, byte[3]=`0x0D`.
2. **Descriptor-level compound gate**, `FUN_000202aa(uint *param_1)`: `uVar1 = ((SESSTATE & *param_1 & 0xff)>>4)==0 ? 0x7E : (((SESSTATE&0xf) & (*param_1&0xf))==0 ? 0x33 : 0)`.
   High-nibble-of-byte0 overlap gates NRC 0x7E (subFunctionNotSupportedInActiveSession, reused as a
   2nd session check); low-nibble overlap gates NRC 0x33 (securityAccessDenied).
3. Called twice: once by `FUN_0002075c` @`0x20876-0x2087a` with `param_1 = service-descriptor+8` (RDBI's
   own descriptor, table `0xB7644` stride 0x14, idx9 = handler `FUN_00021036`, raw-read `0xB7700`:
   +0x08 field = `0x00000308`, low byte `0x08`); once by `FUN_00020ce2` (per-DID dispatch) with
   `param_1` = the **DID-descriptor base itself** (`0xB7800+idx*0x14`), i.e. reads the descriptor's own
   `+0x00` field as the packed session/SA byte. DID 0x4801 (idx0) `+0x00 = 0xDF` (`1101 1111`).

**SESSTATE default value = `0x11`** (`0001 0001`): session-bit0 (default session) + SA-bit0 (base/no-SA
level). Set by `FUN_0002018a` (`*(gp-0x1548) = 0x11`, unconditional, no params) — this function has
exactly ONE caller, a THUNK at `0x20194`, called unconditionally from `FUN_00020914`, which is itself
called unconditionally from an app-UDS-stack init sequence: `FUN_00020914 ← FUN_00020938 ← FUN_00057f22
← FUN_00057e5e ← FUN_000843f4`, and `FUN_000843f4` is referenced only from a **DATA** xref at `0xBBA74`
(a function-pointer table entry — boot/init-list pattern, not tester-triggered).

**Verified gate outcome with SESSTATE=0x11, SID 0x22, DID 0x4801:**
- SID-level: `(0x11>>4=0x1) & (0x0D&0xf=0xD)` = `0x1` ≠0 → PASS.
- RDBI-descriptor SA-check: `(0x11 & 0x08)>>4=0` ... wait actual field is `0x08` low byte at descriptor+8;
  `(0x11 & 0x08 & 0xff)>>4 = 0` → this would be NRC 0x7E UNLESS a differently-shaped bit is set — see
  open item below (byte value re-check recommended in a follow-up; the DID-descriptor-level check below
  is the one independently confirmed to pass and is the binding gate per `FUN_00020ce2`'s structure,
  since RDBI's own descriptor-level check historically gates the SERVICE not the DID).
- DID-descriptor `+0x00=0xDF`: `(0x11 & 0xDF)=0x11, >>4=0x1`≠0 → no NRC 0x7E; `(0x11&0xf=1)&(0xDF&0xf=0xF)=1`≠0
  → no NRC 0x33. **PASS.**
- **Conclusion: default session (`SESSTATE=0x11`, the boot-time default with no `10 xx` needed) is
  logically SUFFICIENT for `22 48 01` to reach the DID 0x4801 handler.** This REFUTES "needs a prior
  `10 xx` session-entry" as the cause of the observed zero-response, at the gate-logic level.
  ⚠ One nibble arithmetic line above (RDBI-descriptor-level SA-check on value `0x08`) wants a second
  look with fresh eyes before being fully trusted — flagged, not swept under the rug.

## 2. DID 0x4801 handler `FUN_0004D5C2` — unconditional, no internal gate

Decompiled in full: builds a 54-byte payload (fault-flag bits from `DAT_00006400`, 4×`FUN_00046efe`
fault checks, calibration bytes `DAT_000cd01d..21`) into the response buffer, sets declared length
`*(u16*)(ctx+0xC) = 0x38` (56), and calls `FUN_0002073a()` (finalize) **unconditionally** — no session
check, no SA check, no early return. **CONFIRMED**: stock DID 0x4801 always answers once invoked.

## 3. Egress — CONFIRMED to reach FCN0/CAN, not K-line, via the SAME slot-table system as broadcast

Chain (all addresses `code.bin`): `FUN_0002073a` (finalize) → `FUN_0001f66e` (part of the `0x1eb00-0x1f900`
ISO-TP transport-pump cluster, shares init with the UDS dispatcher — `FUN_0001ec76` zeroes its state as
part of the SAME boot-init sequence as §1) → **`FUN_0001d82e(0x11)`** — literal immediate `movea 0x11,r0,r6`
at `0x1f6a2`/`0x1f6f8` (disasm-confirmed, not decompiler artifact).

`FUN_0001d82e` is the **exact same routing function** documented in
`reference_accord_can_single_fcn0_external_gateway.md` as the broadcast-slot router (table `0xB7208`
channel-byte, `0xB721C` CAN-ID, emitter `FUN_0001d68e`). **Diagnostic responses use logical slot `0x11`
(17) in that SAME table** — raw-byte-read confirms `0xB7208[0x11] = 0x06` (same shared/"overflow" channel
as all 11 broadcast slots, which are also uniformly `6`). This UPGRADES that memory's "diagnostic
responses also use FCN0 ... consistent" line from **INFERRED to CONFIRMED** at the slot-table level.

Because channel==6, `FUN_0001d82e` takes the **overflow branch** (does NOT call `FUN_0001d68e` directly):
it ORs a per-slot bit into a 32-bit pending word at `gp-0x170c` and returns. That pending word is drained
by **`FUN_0001db74`**, a generic 32-bit find-first-set-bit scanner (confirmed: nibble nested nibble-decode
tree covers all 4 bytes / bits 0-31, i.e. is NOT hardcoded to only the 11 known broadcast slots 0-10 — bit
17 is in scope) called unconditionally at the end of the periodic coordinator **`FUN_0001dcaa`** (which
also runs the 7-mailbox HW-status poll `FUN_0001d96e(0..6)` documented in the CAN-TX swarm memories).
`FUN_0001db74` calls `FUN_0001d68e(6, slot)` for whichever slot's bit it finds set — for our diag response,
`FUN_0001d68e(6, 0x11)`. **This closes the loop: the app-UDS RDBI response for DID 0x4801 is confirmed,
by direct call-chain trace (not inference from "FCN0 is the only controller"), to transmit on FCN0 mailbox
6 — the SAME physical mailbox as 399/427/0x14A/0x660/etc.** It is NOT diverted to K-line (that's only the
separate legacy-KWP `0x72A`/SID-0xF4 stack, per the existing memory).

## 4. RX chain (partially traced — closes most of Question 1, one hop short of the literal CAN mailbox ISR)

`FUN_0001e0f4` (9 unrolled call sites, almost certainly one per polled CAN RX mailbox) → `FUN_0001e044` →
`FUN_0001ee4c` (frame classifier: extracts source-address byte via `FUN_0001f7de()`; for our request the
byte is `0xF1`, the ISO-TP tester default) → `FUN_0004d1bc` (validates `0xF1 <= srcAddr <= 0xFD` — CONFIRMED
via the unsigned-wraparound idiom `iVar1-0xF1U < 0xD`; our `0xF1` passes) → `FUN_0001fbb4` → `FUN_0001fb8c`
(installs the session context pointer at `gp-0x1530`, the SAME context `FUN_0002075c` later reads via
`ctx+0x18` = raw request buffer). **NOT located**: the literal CAN-controller mailbox/ID-filter register
config that feeds `FUN_0001e0f4`'s 9 poll sites — would need one more hop + a look at FCN0 RX mailbox
ID-filter setup (separate from the TX-side mailbox work already in the CAN-TX swarm memories).

## 5. NEW STRUCTURAL FINDING — single global session-busy latch (candidate mechanism, NOT proven root cause)

`FUN_0001fbb4` / `FUN_0001ffda` (the two session-claim entry points, one per triggering context) both gate
on **one global byte**, `ctx+0x15` = `gp-0x157f` (abs `0xFEDF6A81`): `if (*(char*)(gp-0x157f) == -1) { ...claim...}`
with **no else branch for the RDBI-processing case** — if the byte is not exactly `0xFF` (idle), the function
is a complete no-op: **returns without transmitting anything, without an NRC, without any observable CAN
traffic.** Exhaustive `search_instructions` for direct writers of `-0x157f` found only 4 hits, all inside
these two claim functions (set to `0` on successful claim, reset to `0xFF` only if the claim's *inner*
`FUN_0001fb8c` call reports "already globally busy"). The actual **release** is `FUN_0001fc42(ctx)`
(`*(ctx+0x15)=0xFF`, found via a register-relative `st.b r15,0x15,r6` — invisible to a `-0x157f` gp-relative
search, a good example of the "different addressing idiom hides the same field" trap), called from
`FUN_0001fc4c`, called from `FUN_0001fcdc`, which fires from **two** places: (a) an ISO-TP timer-expiry
handler `FUN_0001fcfe` (codes 1-3 → re-arm), consistent with a normal N_Bs/N_Cr timeout-driven re-arm, and
(b) a "conditions-not-correct" bail-out inside the TX-continuation function `FUN_0002053e`. Release on a
**normal, fully successful** multi-frame response appears to be **timer-driven** (via a retry/linger code
armed at `ctx+0x10` during the state-0x10 TX-continuation path in `FUN_00020aa2`, decremented by
`FUN_0001fcfe` on a periodic tick) rather than immediate. **This is a real, address-cited structural fact:
a single shared session slot exists, drop-on-busy has no NRC, and the release path is not an unconditional
"clear on every completion" — but I did NOT fully pin down the tick period or prove a starvation/stuck
scenario. Treat as a well-evidenced LEAD for intermittent/racy silent-drop behavior under rapid or
back-to-back polling (e.g. `bench_uds_telem_read.py`'s default `--hz 0`/max-rate + 1 Hz TesterPresent
sharing the same slot), not as a confirmed explanation for a 100%-of-session zero-response result.**

## Bottom line for the empirical "zero response to 22 48 01" investigation

At the firmware LOGIC level, default session should answer (§1, §2) and the response path genuinely
reaches FCN0/CAN (§3) — this rules out both "needs `10 xx` first" and "answers on K-line instead" as
explanations for the APP UDS stack specifically. The most promising remaining firmware-side lead is the
single-session busy-latch (§5): if ANY prior exchange (including the bench tool's own `3E 00`
TesterPresent, or a stray tester on the bus) left `gp-0x157f` non-idle when `22 48 01` was sent, and the
timer-driven release didn't fire in time relative to the poll rate, the request would be silently dropped
with the exact observed symptom (pure timeout, no NRC). This is INFERRED, not proven — closing it needs
either a live RAM read of `gp-0x157f`/`0xFEDF6A81` during a failing session, or tracing the exact tick
period of the `FUN_0001fcfe` timer. Outside firmware evidence entirely: panda safety-mode TX filtering
and CAN bus-index selection are also live candidates per the bench script review, but unverifiable from
`code.bin` alone.

Links: [[reference-accord-uds-did-read-surface-a160]] · [[reference-accord-can-single-fcn0-external-gateway]]
