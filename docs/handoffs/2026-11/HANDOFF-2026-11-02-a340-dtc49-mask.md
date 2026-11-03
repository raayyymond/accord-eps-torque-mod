# HANDOFF 2026-11-02 — A340: the DTC-0x49 counter mask that the port had left out

**Ask (operator):** "For some reason we didn't make sure the same DTC 0x49 safeguard placed in A160 was done in A340. Make sure
this DTC does not fire for the A340 during driving."

**Result.** Both A340 builds are revised and re-verified, NOT FLOWN: **V37A-A340 REV 4** (image `5b71a52d…d98e`, rwd `e7728d58…d2e6`)
and **V300-A340 REV 3** (image `dc30a73b…a56e0`, rwd `2819a6f2…4917`). Each differs from its predecessor by exactly **4 code bytes +
the main-block CRC trailer**: the hw2 halfword of the two DTC-0x49 counter-gate loads at `0x2961C` and `0x2962E` goes `0x7509 → 0x7D29`,
so `ld.bu 0x7508[tp]` (0xC6508 = 112) becomes `ld.bu 0x7D28[tp]` (0xC6D28 = 0xFF, an unreferenced byte in the free run the 6× build
already hosts its gain cell in). The hand-torque index `gp-0x67f5` is a u8, so `hand > 0xFF` never passes, counter B `gp-0x671e` is
stored 0 on every tick, and the trip at 100 (`FUN_00016ed0(0x49,1,1,1)` + STEER_STATUS 7 at `gp-0x67cd`) is unreachable. The override cut
at `0x2A068/0x2A076` still reads 0xC6508 = 112, untouched. REV 3 / REV 2 artifacts deleted from `accord-firmwares` (in git history).
Adversarial pass: A/B/C all PASS_WITH_DEFECTS, none DO_NOT_FLASH (A: own mirror 0 mismatches, boot init starts the counter at 0, loads decode as ld.bu 0x7D28[tp]; B: fresh rebuild == hashes, all bytes attributed, 11 mutations caught, A160 claim 19/86 verified; C: host private 6 ways, twins dead 3 ways, override cut byte-identical, DTC 0x49 has no reachable setter left, 0x23 untouched, GATE 1/2 unaffected). Page https://claude.ai/artifact/4xPMkqRT1czKaemNg55fJw (new section "DTC 0x49 on A340").

**Why it was missing.** A160 V36 disabled STEER_STATUS=4 and with it the in-code interlock that zeroed counter B; V37 masked the
counter by setting the gate byte `0xC64B8` to 0xFF (handoff 2026-07-14). On A340 the gate byte `0xC6508` is ALSO the hand-override
demand cut (B-type fades stay at 255 up to X=80 / 154 at X=112, so the byte is the only full cutoff). The port's Lens C correctly
refused 0xFF there (REV 2 → REV 3) but the counter was then left live with the V36 package in place — the A160 V36 failure by
construction. The 2026-11-01 handoff disclosed it as "may log DTC 0x49"; the operator ruled it must not.

**Design (minimal, in-place operand edit, the A6 class).** Re-point only the two counter-gate READS; the byte itself and the override
cut stay stock. Cal-only alternatives were evaluated and rejected: raising `0xC6530/0xC6531` only delays the trip (the sum is truncated
to a byte, max 254, and the counter still free-runs above 50). The A340 counter block `0x295F2..0x29648` is the same instruction
sequence as A160's `0x291E0..0x29236` (19 of 86 bytes differ: gp/tp displacements and r11-vs-r10), so "gate reads 0xFF" on these two
sites is the behaviour A160 has flown since V37.

**Byte-exact mirror** (`dtc49_counter_b_tick` in `build_v37a_a340.py`, every line addressed): threshold `(0xC6530+0xC6531)&0xFF = 100`
at `0x295C4/C6`; `< 50` path (`0x2962A..`) resets unless hand > gate AND a request is live; `≥ 50` path (`0x29600..`) free-runs unless
status == 2 with no request, in which case it consults the gate. Sweep: hand 0..255 × r22 × status × start counters — stock gate fires
up to 3× in 250 ticks and re-arms; masked gate from any start < 50: max counter 0, zero trips; a start ≥ 50 would give at most one trip then pin
at 0, and Lens A traced that state UNREACHABLE (boot zero-fill at 0x14720 + the .data copy start the counter at 0 from flash 0x87A42;
the 2× script now asserts that byte is 0). Also from Lens A: the hand index gp-0x67f5 saturates at 255 (both masked compares are strict,
so the mask still holds); r22 is the clamped lane command, not a flag.

**Scanner trap caught on the way.** The port scripts' `tp_readers` compares `hw2 & 0xFFFE`, so for a BYTE cell it counts the odd
parity neighbour: it reported 8 readers of 0xC6508, two of which (`0x46020`, `0x460F0`, op 0x3D) read 0xC6509. `byte_readers`
(parity-exact) was added and the census assertions use it; 0xC6508 has exactly 6 readers (2 counter gates, 1 override cut, 3 in the
uncalled twins `FUN_0002ae74` / `FUN_0002b4a0`).

**Verification.** V37A-A340 REV 4: 142/142 (49 substantive), V300-A340 REV 3: 159/159 (92 substantive), both reproduce their hashes
from a fresh process in < 10 s; full diffs attributed; CRC 49/49 + 50/50 two ways; rwd payload == image; the D6b constants in the 6×
script are asserted equal to the 2× script's (one definition). Mirror + sweep as above. Tracer `tracer-dtc49-a340` (report in
`_scratch/out/a340_dtc49/TRACER-REPORT.md`, summarised in the lineage) re-derived the path from the image, both scan methods agreeing.

**What the operator loses / keeps.** Counter-sourced DTC 0x49 + STEER_STATUS 7 off on A340 (as A160 since V37). STEER_STATUS 7 still
reachable from the fault/timeout block at 0x29570; all other DTC paths untouched. With the V36 package: hand-transient trip and the
over-torque counter both off; the hand-override demand cut at index 112 stays. Lens C census: DTC 0x49's only two setters are the counter trip and its dead twin ⇒ NO reachable code sets 0x49 after this build; DTC 0x23 (12 setters) untouched; STEER_STATUS 7 (fault block) and 4 (counter A, held off by V36 cals) still reachable; STEER_STATUS 2 from this counter is gone (as A160 V37). Lens A: hand index gp-0x67f5 saturates at 255 (not 254), both masked compares are strict; r22 = clamp(gp-0x6976, ±LERP); boot zero-fill 0x14720 + .data copy (flash 0x87320.. → RAM 0xFEDF11C0; counter from 0x87A42 = 0) ⇒ the residual ≥50 start is unreachable; gp-0x67cd << 4 is the 0x18F STEER_STATUS nibble (FUN_000569CC). BELIEF (Lens A residual): a cal overlay copy to 0xFA800000 at boot with runtime write helpers having no static caller — same exposure as every cal on A160. Lens A also noted the part-number bytes differ between the builds (2× changes 0x13109 + 0x14120 as A160 V37; 6× changes 0x13109 + the letter 0x1310D and leaves 0x14120, as A160 V300 D11) — intended, unchanged from the 2026-11-01 port.

**Open.** First on-car dry run on the A340 car (part gate, diag address) still outstanding; the 0x23 DTC path not re-traced; the two
external STEER_STATUS readers (`FUN_0004f3fa`, `FUN_000569cc`) not fully decoded (BELIEF: unaffected, state 7 remains reachable).

**Files.** `analysis-2020accord/builds/a340/build_v37a_a340.py` (REV 4), `build_v300_a340.py` (REV 3); lineage PART6 entries
"V37A-A340 REV 4" and "V300-A340 REV 3"; STATE.md A340 box; memory `accord-a340-port-v37a-built-v300-mapped-2026-11-01.md` updated.
