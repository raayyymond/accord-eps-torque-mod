---
name: reference-accord-fun3b8f6-gatefail-stale-and-gp6c00-exact-flag
description: FUN_0003b8f6's gate-FAIL path does NOT write gp-0x6ae0/gp-0x6ae2, so friction/inertia telemetry can be STALE and V89 cannot tell; gp-0x6c00 is an exact parameter-free gate flag (0xFFFF on fail vs 0..20000 on success), 1 writer / 0 readers, verified with both tools set-differenced.
metadata:
  type: reference
---

# `FUN_0003b8f6` — the gate-fail path leaves the friction/inertia taps STALE

Found 2026-08-10 while specifying V90's cave. Stock `code.bin`, `decompile_function 0x3b8f6`.

## [EVIDENCE] Both taps are written only on the SUCCESS arm

```c
  iVar20 = |clamp(residual * K, -20000, +20000)|;
  uVar12 = (undefined2)iVar20;                                // SUCCESS: 0 .. 20000
  *(short *)(gp + -0x6ae0) = (short)(int)(fVar14 * 1024.0);   // INERTIA  x 1024
  *(short *)(gp + -0x6ae2) = (short)(int)(fVar13 * 1024.0);   // FRICTION x 1024
  goto LAB_0003bc16;
  ...                                                          // FAIL arm:
  iVar11 = 0x7fff;  *(undefined2 *)(gp + -0x6bf6) = 0x7fff;
  uVar12 = 0xffff;
LAB_0003bc16:
  *(undefined2 *)(gp + -0x6c00) = uVar12;
  *(short  *)(gp + -0x6bfc) = (short)iVar11;
```

🛑 **CORRECTED, same day, after `ObserverMatch` narrowed it — my first version of this line said "every
friction/inertia inference from V89 is conditional on the gate", and that was OVERSTATED.**

**A gate failure HOLDS the previous value, and the previous value is typically ~41 counts — NON-ZERO. So
a gate failure cannot CREATE a zero in `gp-0x6ae2`; it can only prolong one.** ⇒ the observed zeros are
**provably fresh**, independent of gate duty. Corroborated on flown data two ways: zero-run dwell matches
non-zero-run dwell (a stale hold would freeze; this dithers), and `P(zero)` is an 80× monotone function
of wheel rate — a variable the gate does not read — reproduced on two independent drives.

**Correct statement: the taps are success-path-only writes, so a reading is FORMALLY ambiguous; the ZEROS
specifically are established fresh; NON-zero readings remain conditional.** `FlightV89`'s V89 result
survives. Lesson for me: *"written only on one arm"* ⇒ *"can be stale"*, but **stale-toward-WHAT** decides
whether that is a real confound. Check the held value before calling a success-path-only write a confound.

🛑 **The failure mode NO gate flag catches, and it matters more:** at `(char)gp-0x6752 == 0` the command
branch itself zeroes (`gp-0x6b98 × cVar5`), so **model, FRICTION and INERTIA collapse together while the
observer emits a valid non-sentinel output** — and polarity 0 **PASSES** the gate (`0+1 = 1 < 3`), so all
four sentinels read *success*. **A friction probe should carry `gp-0x6752`, not a gate flag.**

Also: at `(char)gp-0x6752 == 0` the relay term is zero, so friction decays toward 0 through the EMA ⇒
**`gp-0x6ae2 == 0` can be a POLARITY artefact, not a physical zero.** Reading `gp-0x6ae0` alongside
discriminates (polarity-zero → both go to 0; rate-crossing → only friction).

## [EVIDENCE] The four entry gates

```
|gp-0x6b98| <= 0x2000  AND  -25600 <= gp-0x4f60 <= 25600  AND  -13000 <= gp-0x6abc <= 13000
AND  (char)gp-0x6752 in {-1, 0, +1}
```

## [EVIDENCE] `gp-0x6c00` is an EXACT, parameter-free gate flag — and a write-only tap

`ld.h` sign-extends. Success range `0..20000` is non-negative; fail value `0xFFFF` is `-1`. ⇒ a single
signed `cmp 0,r6 ; bge` separates them **with no calibration constant at all** — the cheapest exact
predicate found in this firmware so far.

**Census, both tools set-differenced, every hit adjudicated: 1 writer, 0 readers.**
Python LE scan of `[0x13000,0xC5000)` over all three encodings (4-byte Format VII, 6-byte
extended-displacement, `movhi 0xFEDF`+register-indirect with opcode and 96-byte locality filters) and
Ghidra `search_instructions`: **exactly `st.h r9,-0x6c00,gp` @ `0x3BC16`** (bytes `644f 0094`).
Ghidra's four extra hits adjudicated out — `0x26BF4`/`0x26BF8` are `bne 0x00026c00` branch-target
*text*; `0x5DFFA`/`0x5F5B0` are `movea 0x6c00,r0,r7`, an immediate against **r0**, not `gp`.

⇒ It is the best class of cave source per
[[reference_accord_gate1_write_only_diag_taps_are_the_best_cave_ram]], and `0x3BC16`'s hw2 `0094` is
the verbatim displacement twin for a cave `ld.h -0x6c00[gp],r6`.

## FOUR equivalent gate sentinels, and the cheapest way to read one

`gp-0x6c00 == 0xFFFF` ⟺ `gp-0x695c == 0xFFFF` ⟺ `gp-0x6bf6 == 0x7FFF` ⟺ `|gp-0x6b70| ≥ 8193`.
They fire together deterministically (`gp-0x6bfc = 0x7FFF` fails `FUN_0003bc20`, which sets `gp-0x695c`
and `gp-0x6bfe`, which makes `FUN_00038148` write `gp-0x6b70 = 0x7FFF`). `gp-0x6b70`'s success path is
clamped to ±8192 (`0xC6200`) so `≥8193` is EXACT, and V86/V86B/V87/V88 **already cave-probe `gp-0x6b70`**
at threshold 64 ⇒ on those builds it is a threshold change, not a new bit. Census [EVIDENCE, both tools]:
`gp-0x695c` **1W/0R** (`0x3BC42`) · `gp-0x6b70` **1W/1R** (`0x382D2`/`0x38006`) · `gp-0x6bf6` **2W/0R**
(`0x3BAC0` success, `0x3BC0E` fail — written on BOTH arms ⇒ never stale, unlike `gp-0x6ae0`/`gp-0x6ae2`).

🛑 **Named trap: the FAIL path writes a NON-ZERO sentinel, so a `!= 0` rung does NOT detect it.** A claim
that "non-zero 99.80 % ⇒ the gate rarely fails" was retracted for exactly this reason.

⊕ **`gp-0x695c` is a plain RAM status word (0x400 ok / 0xFFFF bad), 1W/0R — if UDS-readable at rest the
gate question closes with NO build at all.** Needs the operator's explicit payload confirmation first.

## `gp-0x6bf6` = the model, before friction/inertia are subtracted [EVIDENCE, re-verified]

`gp-0x6bf6 = clamp(cal(0xC6468)=2639 × model, ±20000)`, stored at `0x3BAC0` *before*
`iVar20 = (model − (friction + inertia)) × 2639` is formed. With `gp-0x6ae2` it separates `|model|` from
`ratio` exactly: `ratio = (gp-0x6ae2/1024) / (|gp-0x6bf6|/2639) × (1024/K1)`. **Better than `gp-0x6ae0`,
which is a DERIVATIVE of the rate, not the rate.** The number that separates *justifying* a friction dose
from *sizing* it.

Related: [[reference_accord_fun3b8f6_fir_not_biquad_inertia_friction_and_free_taps]],
[[reference_accord_v90_cave_gate1_census_and_hook_critical_section]].
