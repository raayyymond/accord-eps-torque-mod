---
name: reference_accord_telemetry_ram_hook_a160
description: Free RAM window, per-cycle hook site, and capture-list variable verification for RAM telemetry design in 39990-TVA-A160 stock firmware (V850E2, code.bin)
metadata:
  type: reference
---

# Telemetry RAM & Hook Design — 39990-TVA-A160 (code.bin)

## Startup / RAM initialization summary

Entry point: `FUN_00014084` at `0x14084`.
- Sets gp = `0xFEDF8000`, tp = `0xBF000`, sp = `0xFEDF791C` (word-aligned, downward).
- Calls `FUN_000146c0` which:
  1. **bss-clear**: zeroes `0xFEDEC000`–`0xFEDFFFFF` (4 words/loop, condition `ep <= 0xFEDFFFFF`).
  2. **data-copy**: ROM `0x86260`–`0x8AB18` (0x4AB8 bytes) → RAM `0xFEDF11B0`–`0xFEDF5C67`.
  3. **Stack canary fill**: `0xFEDEC000`–`0xFEDEF91F` with `0xEBEBEBEB` (marks max stack depth).
- sp starts at `0xFEDF791C` and grows DOWN toward `0xFEDEC000`.

## Highest gp-relative addresses confirmed in code

- `gp - 0x10 = 0xFEDF7FF0` — accessed in `FUN_000757a2` (large CAN/diag handler).
- `gp - 0x1380 = 0xFEDF6C80` — LKAS timing variable, used in `FUN_00045d9e`.
- `gp - 0x257C = 0xFEDF5A84` — OS task-descriptor pointer, used widely.
- `.data` copy ends at `0xFEDF5C67`.
- **Stack region**: `0xFEDEC000`–`0xFEDEF91F` (canary fill; top of stack = sp `0xFEDF791C`).

## Free RAM window — CANDIDATE

**`0xFEDF7A00`–`0xFEDF7FFF` (0x600 = 1536 bytes)**

Rationale:
- Above sp (`0xFEDF791C`) by ~0xE4 bytes; sp grows DOWN so the stack cannot reach `0xFEDF7A00` unless the call stack is extremely deep.
- Below gp (`0xFEDF8000`) by 0x600 bytes.
- bss-clear zeros this range at boot.
- No gp-relative stores confirmed in this range (highest confirmed gp-relative access is `gp-0x1380 = 0xFEDF6C80`; the `gp-0x10` in `FUN_000757a2` is an isolated access; no multi-word structures confirmed here).
- No .data-copy target overlaps (copy ends at `0xFEDF5C67`).

**Residual risk**: The region `0xFEDF6C80`–`0xFEDF7FFF` is not exhaustively scanned — there may be gp-relative vars between `0xFEDF6C80` and `0xFEDF7A00`. The `gp-0x10` access is suspicious. A full byte-pattern scan of all gp-relative offsets between `-0x800` and `-0x10` is needed to rule out conflict.

**Safer conservative window**: `0xFEDF7C00`–`0xFEDF7FFF` (0x400 = 1024 bytes). The `gp-0x10` access at `0xFEDF7FF0` is in one large function; a ring buffer at `0xFEDF7C00`–`0xFEDF7EFF` (0x300 = 768 bytes) avoids it entirely.

**Recommended**: `0xFEDF7C00`–`0xFEDF7EFF` (768 bytes) for the ring buffer.

## Per-cycle hook point

**Hook site: `0x0004141E`** — `jarl 0x00040a50, lp`  
Bytes: `bf ff 32 f6`  

**Call chain establishing exactly-once-per-100 Hz cycle:**
1. Hardware timer ISR → `w_steer_control_task` (`0x2214a`) — called once per ~100 Hz control cycle.
2. `w_steer_control_task` → `FUN_00022ca0` (`0x22CA0`) — top-level cycle dispatcher.
3. `FUN_00022ca0` → `FUN_000413ae(6)` (`0x413AE`) — engage/disengage SM dispatcher, called ONCE per cycle unconditionally (no bitmask gate — unlike many other calls in `FUN_00022ca0`).
4. `FUN_000413ae` dispatches to SM state handlers (states 0–8), all of which may call `FUN_0003d04c` (deliver-commit decider) and update the gentle-EME suspect variables including `gp-0x679C` (engage state), `gp-0x6770` (FOC mode), `gp-0x6a62` (voter-MAX), etc.
5. After all state handlers: `FUN_000413ae` calls `FUN_00040a50` via `jarl 0x00040a50, lp` at `0x4141E`.

**All gentle-EME suspect variables are updated BEFORE `0x4141E`.**

**Hook displacement**: Replace `jarl 0x00040a50, lp` (4 bytes, `bf ff 32 f6`) at `0x4141E` with `jarl <cave>, lp`. The cave stub runs capture, then executes `jarl 0x00040a50, lp` with re-encoded offset from the cave address. `jarl disp22` is PC-relative and fully relocatable — no gp/tp-relative dependency.

**Code cave**: `0xC4E00`–`0xC4FEF` (496 bytes of `0xFF`, confirmed by memory read). Inside CRC block `[0x13000, 0xC4FFC)` — CRC must be recomputed after patching.

## Capture-list variable verification

| Variable | gp offset | Abs address | Access form confirmed |
|---|---|---|---|
| voter-MAX (`gp-0x6a62`) | -0x6a62 | 0xFEDF159E | `ld.hu -0x6a62, gp` — confirmed, many sites including `0x24012`, `0x40dae` (FUN_00040d58 = gentle-EME gate) |
| voter-rate (`gp-0x6a60`) | -0x6a60 | 0xFEDF15A0 | `ld.hu -0x6a60, gp` — confirmed, `0x3c3e2`, `0x40d78`, etc. |
| voter-AVG (`gp-0x6a5e`) | -0x6a5e | 0xFEDF15A2 | `ld.hu -0x6a5e, gp` — confirmed, `0x1c25e`, `0x28f0e`, etc. |
| col-torque src (`gp-0x4f60`) | -0x4f60 | 0xFEDF30A0 | `ld.h -0x4f60, gp` (SIGNED) — confirmed, `0x1c09e`, `0x28f26`, etc. |
| `|torque|` (`gp-0x4f68`) | -0x4f68 | 0xFEDF3098 | `ld.hu -0x4f68, gp` — confirmed, `0x2438c`, etc. |
| deliver flag (`gp-0x6809`) | -0x6809 | 0xFEDF17F7 | `ld.bu -0x6809, gp` — confirmed in `m_steer_torque_arbitration` at `0x2975a`, `0x29808` |
| trump (`gp-0x67FE`) | -0x67FE | 0xFEDF1802 | `ld.bu -0x67fe, gp` — confirmed, `0x290f8` etc. |
| engage state (CORRECTED) | **-0x679C** | **0xFEDF1864** | `ld.bu -0x679c, gp` — confirmed, written by `FUN_00040d38` at `0x40d44`, read by `FUN_000413ae` at `0x413ba`. **NOT `gp-0x67DC` as specified.** |
| FOC mode (`gp-0x6772`) | -0x6772 | 0xFEDF188E | `ld.bu -0x6772, gp` — confirmed, `0x3bd88` etc. |
| mode (`gp-0x6770`) | -0x6770 | 0xFEDF1890 | `ld.bu -0x6770, gp` — confirmed, `0x3c594`, also WRITTEN by `FUN_0003d04c` |
| angle (`gp-0x6cc4`) | -0x6cc4 | 0xFEDF133C | **`ld.w -0x6cc4, gp` (32-bit WORD, not u16)** — confirmed, `0x3bce4`, `0x3bf0e`, etc. |
| CAN-TX bitfield | N/A (abs) | 0xFEDF693C | Accessed via `mov 0xFEDF693C, ep/r` — NOT gp-relative. 3 access sites: `0x1D5C6`, `0x1D9D2`, `0x1E3D0`. |
| mode-gate (`gp-0x1688`) | -0x1688 | 0xFEDF6978 | `ld.bu -0x1688, gp` — confirmed, `0x1e714`, `0x1e726`, etc. |

## FLAG: address corrections

- **`gp-0x67DC` does NOT EXIST** in the binary. Zero `ld.bu`/`st.b`/`ld.h` hits. The engage-SM state is at `gp-0x679C = 0xFEDF1864`.
- **`gp-0x6cc4` is a 32-bit word** (`ld.w`), not a u16 as specified.
- **`gp-0x6770` absolute address = `0xFEDF1890`**, not `0xFEDF1690` as specified (the HANDOFF says `0x1690`; the disasm shows `ld.bu -0x6770, gp` which is `0xFEDF8000 - 0x6770 = 0xFEDF1890`).

## Code cave feasibility

`jarl <cave>, lp` at `0x4141E` with cave at e.g. `0xC4E00`:
- Displacement = `0xC4E00 - 0x4141E = 0x809E2`, but V850 disp22 range is ±1 MB (0xFFFFF). `0x809E2` < `0xFFFFF` — fits.
- Cave stub structure: `prepare`/save regs → store captures to ring-buffer addr → `dispose`/restore → `jarl 0x00040a50, lp` (re-encoded) → `jmp [lp]`.
