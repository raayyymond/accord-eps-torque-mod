---
name: reference-accord-detector-gate-input-liveness-verified
description: Fresh, independent Ghidra + raw-byte re-verification (2026-08-03) of the 1 kHz oscillation detector (FUN_000428d4/gp-0x67df/gp-0x671a) -- confirms gp-0x67df has exactly 2 accesses image-wide, the DTC gate self-clears, the detector's own call site is state-gated (not rate-divided), and gp-0x6c2c's INPUT is a live ISR-fed signal refreshed every task-1 tick regardless of the DTC gate. Also identifies that gp-0x6c2c's PRODUCTION is independent of the detector's DTC gate -- a probe on gp-0x6c2c itself would sidestep the whole gate-liveness ambiguity.
metadata:
  type: reference
---

Re-verifies (independently, not by re-quoting) the prior session's `model/eps_lkas_chain_model.py:546-607` /
`docs/handoffs/2026-08/HANDOFF-2026-08-03-the-detector-was-always-there.md` claims, which had become **verdict-affecting**
after V68 read `gp-0x67df`/`gp-0x671a` zero on 53,991 frames including the captured 28 Hz lane-change burst.
Method: GhidraMCP decompile/disasm on `code.bin` (stock) + independent Python raw LE byte scans (disp16,
disp23-extended, LE32-literal) per `firmware-decompile` skill / `reference_v850e2_extended_disp23_encoding_solved`.

## 1. `gp-0x67df` — EXACTLY 2 accesses image-wide [EVIDENCE, exhaustive]
Disp16 scan (op-correct per-opcode rules) + disp23 6-byte extended scan + LE32 absolute-address scan, whole
1,048,576-byte `code.bin`: **read** `ld.bu -0x67df[gp],r16` @`0x428e6` (bytes `a4 87 21 98`), **write**
`st.b r11,-0x67df[gp]` @`0x4299c` (bytes `44 5f 21 98`) — both inside `FUN_000428d4`, zero hits anywhere
else, zero extended-form hits, zero LE32-literal hits. `FUN_000428d4`'s sole caller is `FUN_0002214a`
@`0x22926` (direct `jarl`, unconditional, statically resolvable — not an indirect-call blind spot).

## 2. The DTC gate `FUN_00046ea6(5)` self-clears; exact DTC->bit5 mapping still open [EVIDENCE + 1 residual]
`FUN_000428d4` calls `FUN_00046ea6(5)` first; nonzero return skips the WHOLE body (jumps to `0x42a76`,
neither `gp-0x67df` nor `gp-0x671a` touched). `FUN_00046ea6(param)` = `((gp-0x18d0 | gp-0x18d4) >> param) & 1`.
- `gp-0x18d4` is **rebuilt from scratch every call** of `FUN_00046810` (the active-fault sweep): local
  accumulator starts at 0, OR's in `*(uint*)(DTCrecord+8)` only for entries that reach `LAB_00046918`
  (i.e. still-active, not-yet-confirmed-cleared faults), then `gp-0x18d4 = accumulator` (plain assignment,
  not OR-into). If the active-fault count is 0, the loop never runs and `gp-0x18d4 = 0`, unconditionally,
  every sweep. **NOT sticky.**
- `gp-0x18d0` is zeroed unconditionally at boot (`FUN_000178c6`, a RAM-clear sweep) and afterward only grows
  via OR: `FUN_0001601e` (`gp-0x18d0 |= *(uint*)(record+8)`) and inline in `FUN_00047c4a` (a DTC-clear/SID
  routine, same OR, gated on a record flag bit 0x10). Both are narrow, specific eviction/clear paths, not a
  general per-tick write.
- DTC record table: base `tp-0x72c4` = `0xB8D3C`, stride `0x1c`=28 bytes, `u16` flags at +0, `u32` mask at
  +8 (byte-read 10 records @`0xB8D3C`, mostly zero, non-zero entries at record index 3 and 7 have
  distinctive small values — table format understood, **which physical DTC number lands on bit 5 was NOT
  resolved this session**).
- Residual: I have NOT proven bit5 is always 0 on a fault-free car; I HAVE proven the mask is self-clearing
  (not permanently latched) and only grows from specific rare paths, which combined with the flight-clean
  telemetry on every flown route (V64/V67/V68: zero watchlist DTC events) is strong but not airtight
  corroboration the gate is open.

## 3. Task-1 call chain confirmed structurally [EVIDENCE]
`FUN_0002214a` (the function containing `FUN_000428d4()`'s only call site) has **zero Ghidra-resolved
callers** (`get_xrefs_to` returns none — the known indirect/table-dispatch blind spot). An LE32 literal scan
for `0x0002214a` finds exactly one hit, `0xBB928`, which is offset+8 inside the FIRST of an 8-pointer TCB
table at `0xBB858` (pointers `0xBB920/950/980/9B0/9E0/BBA10/BBA40/BB8B8`, stride `0x30` for 7 of 8) —
matches the kit's established "task 1, TCB table `0xbb858`" claim, now independently re-derived via a
literal scan rather than trusted from memory.

Inside `FUN_0002214a`, `FUN_000428d4()` is called under `if (uVar4 != 0)` where
`uVar4 = (1 << (gp-0x67fa & 0xf)) & 0x830` — an **ECU-STATE one-hot mask** (state ∈ {4,5,11}), matching the
kit's settled "`0x930/0xc30/0xd30` are one-hot ECU-state masks, not a phase counter" finding. This is a
**different, narrower** gate than the mod-100 divider: `FUN_0002214a` separately and explicitly invokes the
already-established divider `FUN_00014be4()` (`if (iVar1==1) FUN_00014be4();`, `iVar1` from `gp-0x42fc`) to
throttle a DIFFERENT subset of its own calls down to ~100 Hz. `FUN_000428d4`'s call is **not** behind that
divider — it fires on every `FUN_0002214a` invocation while the state gate holds, i.e. at task-1 rate
(~1 kHz, per the kit's separately on-car-confirmed dwell-time measurement — not re-derived today).

## 4. `gp-0x6c2c`'s input `gp-0x4f50` is a live, ISR-fed hardware signal [EVIDENCE, exhaustive]
Exhaustive scan: `gp-0x4f50` has **exactly 1 writer** program-wide, `st.h r28,-0x4f50[gp]` @`0x68FDE`
inside `FUN_00068fbe`; 10 other accesses are all reads. `FUN_00068fbe`:
```
__disable_irq(); sVar2 = gp-0x29c4; __enable_irq(); gp-0x4f50 = sVar2;
```
(classic torn-read guard against a value an ISR concurrently updates). `gp-0x29c4`'s sole writer is
`FUN_00068f52`, called only from `FUN_00065afe` (resolver sin/cos → rotor electrical angle). `FUN_00068f52`
re-decompiled fresh: wraps a raw angle difference to `±0x2000` (mod `0x4000`=16384 counts/electrical rev),
scales `*120000>>14`, 2-tap-boxcars with the previous sample, clamps to **exactly ±13000**, writes
`gp-0x29c4`. `FUN_00068fbe` is invoked via `FUN_0006bb08(3, uVar2)`, which `FUN_0002214a` calls
**unconditionally** (not behind the `0x830`/`0xd30` state gates) — `gp-0x4f50` refreshes from live hardware
every task-1 tick regardless of ECU state.

## 5. `gp-0x6c2c`'s own arithmetic re-confirmed [EVIDENCE]
Fresh decompile of `FUN_00041464` matches the golden model's documented Q-format exactly: K1 = cal
`0xC643C` (>>7, first-stage EMA blending `rate_raw*1024` toward `ema_old`); `acc = clamp(step*32,
±0xFA0000)`; `gp-0x6c2c = (EMA2, cal 0xC40DC >>6) >> 9`; sibling `gp-0x6c2e = (EMA2, cal 0xC40DA >>7) >> 9`.
**The `|rate_raw|>13000` fault-sentinel branch is proven unreachable**: the test is
`(gp-0x4f50 + 13000) > 26000` as an unsigned/pointer compare, and since `gp-0x4f50` is clamped to exactly
`±13000` at its own source (§4), the sum is always in `[0,26000]`, never `>26000` — the live arithmetic
path always executes. Cal bytes fresh-read from the currently open `code.bin` and all match documented
values: T (`0xC620A`) = 12800, HYST (`0xC64DD`) = 50, CEIL (`0xC64FA`) = 5, SPD_THRESH (`0xC62DE`) = 640,
RELEASE (`0xC6270`) = 5000 — no staleness.

## 6. ★★★★★ KEY NEW FINDING — `gp-0x6c2c`'s PRODUCTION is independent of the detector's DTC gate
`FUN_00041464` (producer of `gp-0x6c2c`) is called from `FUN_0002214a` under its OWN state mask
`uVar2 & 0xd30` (state ∈ {4,5,8,10,11}) — **not** through `FUN_00046ea6` at all. `FUN_00046ea6(5)` only
wraps `FUN_000428d4`'s FSM/counter update (`gp-0x67df`/`gp-0x671a`). Since `0xd30 ⊇ 0x830`, `gp-0x6c2c` is
fresh every tick the detector itself would run, AND in two additional states (8, 10) where the detector
doesn't. **A probe reading `gp-0x6c2c` (or a peak/envelope of it) directly, instead of the downstream FSM
flags, sidesteps BOTH open ambiguities at once**: the DTC-gate liveness question (§2) and the `T`/`CEIL`
quantization that has produced every null to date (V64/V67/V68). It would also be a genuine positive
control — the raw band-passed rate signal should read continuously nonzero/varying under any normal
driving, unlike the binary FSM flags which have never fired in this kit. **Recommended as the next probe
design** if the operator wants to close the "quiet band vs dead instrument" question definitively.

## Bottom line for the V68 null
Structural evidence assembled today rules out "dead instrument" in the strong sense: the input chain is
demonstrably live hardware (not a stuck constant, not a disconnected/test source), the arithmetic path to
`gp-0x6c2c` is unconditionally reachable, and the detector's own call site is un-divided (state-gated only).
What is NOT closed: (a) the exact DTC↔bit5 mapping for the enable gate (residual, §2), and (b) whether the
real captured event's amplitude on `gp-0x4f50`'s own (still-[OPEN]) units came anywhere near the sizing
table's trip amplitudes — that sizing table was computed for synthetic sinusoids, not measured on the real
28 Hz burst, since `gp-0x4f50`/`gp-0x6c2c` themselves were never probed directly, only the downstream FSM.
⇒ V68's null is **evidence of a quiet band, conditional on the gate being open** (which is now well but not
airtight supported) — **not** evidence the instrument is dead. §6's direct-`gp-0x6c2c` probe is the cleanest
way to remove the remaining conditionality.

## Related
[[reference_accord_boost_index_input_is_resolver_rate_not_torque]] — established gp-0x4f50/gp-0x29c4 chain,
independently re-derived here.
[[reference_accord_common_mode_rate_signal_6abe_6ac0_full_chain]] — the sibling `gp-0x6abe`/`gp-0x6ac0`
outputs of the same `FUN_00041464`, phase/gain-characterized.
[[reference_accord_state671a_is_oscillation_reversal_counter]] — original FSM semantics for
`gp-0x67df`/`gp-0x671a`, confirmed structurally intact here.
