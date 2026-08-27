---
name: reference_accord_gp6b26_two_paths_reinforce_and_pole_fork_dead
description: "gp-0x6b26's two consumer paths REINFORCE, not oppose -- four negations (two of them gp-0x6752 multiplies) make the chain net-positive, and because Path 2 passes through gp-0x6752 TWICE the relative sign is gp_0x6752^2 = +1, INVARIANT to the one cell that has repeatedly flipped this kit's sign classification. Also KILLS the pole-placement lever: the 90-180deg sector (damping AND reduced inertia) IS geometrically reachable but costs 1.9-7.1x of |H| that the Y table cannot buy back, because Y is already at 90% of its int16 cap. Both pole cals (0xC643C=37, 0xC40DC=22) are VIRGIN on all 102 images -- never-tried, not falsified."
metadata:
  type: reference
---

# `gp-0x6b26` — the two paths REINFORCE; and the pole-placement lever is dead

2026-08-22, `mechanism` task, follow-up to
[[reference_accord_v106_gp6b26_mechanism_ceiling_and_reshape]]. Script:
`analysis-2020accord/studies/sessions/v104/v107_pole_fork_and_reshape.py`.

## 🛑🛑 PATH 1 AND PATH 2 REINFORCE — and the answer is IMMUNE to `gp-0x6752`

Team-lead's worry was that Path 2 opposes Path 1 and partially self-cancels the dose. **It does not.**
Traced fresh, decompile-first, every hop:
```
1  gp-0x6b26 +d
2  FUN_00038148   S += d           (weight 0xC63A6 = 1024, >>10 => x1)
3  T = ((S * gp-0x6752 * 0xC6468=2639) >> 10) * 16          <-- NEGATION #1  (gp-0x6752)
4  ACC (gp-0x374c) EMA-tracks T, alpha = 0xC63AC=102/1024
5  residual = gp-0x6bfe - (ACC >> 4)                        <-- NEGATION #2  (subtraction)
6  gp-0x6b70 = clamp(sgn(res)*LERP(|res|), +-0xC6200=8192)   monotone odd => same direction
7  FUN_00037fe6   gp-0x6ad6 += gp-0x6b70 * byte(0xC64B0)=1, then *LERP >>10, clamp +-0x6400
8  FUN_0003a382   error = gp-0x4f60 - clamp(gp-0x6ad6, +-8192)   <-- NEGATION #3  (0x3a382)
9  PID (P/I/D all positive on the error)
10 ... * gp-0x6752 * (gp-0x6752+1 < 3)  -> gp-0x6ad4          <-- NEGATION #4  (gp-0x6752)
11 aggregator adds gp-0x6ad4 with +1  -> gp-0x6b94
```
**FOUR negations = EVEN = net POSITIVE.** Path 2 pushes `gp-0x6b94` the SAME way Path 1 does.

⭐ **AND IT CANNOT BE FLIPPED BY `gp-0x6752`.** Path 2 multiplies by `gp-0x6752` **twice** (steps 3 and
10); Path 1 never touches it. So Path-2's sign relative to Path-1 is `gp_0x6752²`, and since
`gp-0x6752 ∈ {−1, 0, +1}` that is **+1 whenever the cell is ±1** (and the whole lane is muted at 0).
⇒ **the one cell that reversed this kit's entire PID sign classification since V38 cannot reverse
this.** [EVIDENCE — both multiplies visible in the decompile; `0xC64B0`, `0xC63A6`, `0xC6468`,
`0xC63AC`, `0xC6200` all byte-read LE on stock.]

⇒ **The reshape's ratios survive in full.** Scaling `Y` scales `gp-0x6b26`, which scales BOTH paths by
the identical factor, so the net effect scales with it — the paths' ratio is invariant under any `Y`
edit. The only second-order caveats are the `sgn×LERP(|·|)` compressor at step 6 (its local slope
lives in **RAM**, `gp-0x64b8`/`gp-0x641c`, so it is not readable from the image) and the ±511 clamp.

## 🛑 CORRECTION OF RECORD — the off-by-0x1000 trap, SIXTH recurrence
`memory/accord/mechanism/accord-friction-polarity-more-friction-is-more-assist.md` step 5 cites **"`0xC74B0`=32"**.
The instruction is `ld.bu 0x74b0[tp]` and `tp = 0xBF000`, so the cell is **`0xC64B0`, whose byte is 1**
— an ENABLE FLAG, exactly the failure mode CLAUDE.md already records for this displacement.
`0xC74B0` does contain 32, which is why the wrong answer looks plausible. **The SIGN in that memory is
unaffected; the MAGNITUDE is off by 32×.**
⚠ Same memory, step 7: *"PID, P/I/D all positive-coefficient → `gp-0x6ad4` up"* **omits the
`gp-0x6752` multiply that terminates `FUN_0003a382`**. That memory predates
`[[accord-gp6752-is-negative-one]]`. Its headline conclusion ("more friction ⇒ more assist") therefore
needs re-checking by whoever owns the friction lever — **not corrected here, and it does not affect
`gp-0x6b26`**, whose Path-2 chain passes through `gp-0x6752` an even number of times.

## 🛑 THE POLE-PLACEMENT FORK — reachable, and DEAD
The differencer alone gives **+86.09°** at 21.73 Hz; the two EMA poles currently subtract **−32.44°**,
leaving `phase(H)` = **+53.64°**. To rotate the phasor into the 90–180° sector (damping AND *reduced*
inertia) the poles must supply more than 86.09° of lag. Swept the **full integer cal grid** (a1 = K1/128
for K1∈[1,127], a2 = K2/64 for K2∈[1,63]):
```
phase(H)  best |H|  K1   K2   |H|/stock   Y multiple needed to restore  available
   +0deg    4.123   15    8      0.534              1.87x                1.111x   IMPOSSIBLE
  -10deg    3.309   14    6      0.428              2.33x                1.111x   IMPOSSIBLE
  -20deg    2.618   10    6      0.339              2.95x                1.111x   IMPOSSIBLE
  -40deg    1.089   11    2      0.141              7.09x                1.111x   IMPOSSIBLE
single-cal: 0xC40DC 22->2 gives phase -5.05deg at |H| x0.238 ; 0xC643C 37->4 gives -1.25deg at x0.244
```
⇒ **Geometrically reachable — say so plainly — but the −20 dB/decade cost is 1.9–7.1× of `|H|`, and
`Y` can only buy back ×1.111 because it is already at 90 % of its int16 cap.** Worse, it trades the
wrong quantity: today the term delivers `|H|·sin(φ)` = **6.22 of ADDED inertia**, and the best
*reduced*-inertia the grid can deliver anywhere is **0.90 — 6.9× smaller**, i.e. a rounding error
against the ±511 clamp. **The fork is closed. Do not reconsider pole placement as a frequency lever
on this cascade.**

## The pole cals — VIRGIN, never-tried (≠ falsified, ≠ inert)
```
0xC643C  K1 = 37   ld.hu 0x743c[tp] @0x415DA   EMA1 pole
0xC40DC  K2a = 22  ld.hu 0x50dc[tp] @0x41626   EMA-A pole (the gp-0x6c2c branch)
0xC40DA  K2b = 3                               EMA-B pole (the gp-0x6c2e sibling)
```
**37 / 22 / 3 on ALL 102 build images** (Python LE census). `0xC40DC`: **zero** hits in all 102
`build_v*_tva.py` and in all three BUILD-LINEAGE files. `0xC643C`: hits in `build_v43`/`build_v44` only
as **assert-unchanged inventory** (`0xC643C: (37, "gp-0x6abe resolver-rate filter gain")`) plus V44's
prose using it to *refute* a phase-lag argument — **never an edited value**.
🛑 Blast radius differs sharply: **`0xC643C` is SHARED** — `gp-0x6abe = EMA1(gp-0x4f50)` exactly, so it
also sets Honda's own damper's sign source in `FUN_00034350` and the whole rate-signal hub.
**`0xC40DC` is the isolated one**, touching only the `gp-0x6c2c` branch (3 consumers: the FOC
motor-model float, this friction lane, and the `FUN_000428d4` detector FSM).

## Reshape specs — Y at `0xD7A5C` (mode 26) and `0xD7A6C` (mode 27), X unchanged at (0,1280,5760)
```
                       Y triple                   LE bytes         5mph   20kmh  50kmh  90+kmh  ratio@90+
V106 (on car)   (-29490,-17202, -5898)   ce8c cebc f6e8   -24546 -17202 -12358  -5898     1.00x
RESHAPE A       (-29490,-29490,-29490)   ce8c ce8c ce8c   -29490 -29490 -29490 -29490     5.00x
RESHAPE B  ⭐   (-29490,-24000,-16000)   ce8c 40a2 80c1   -27282 -24000 -20572 -16000     2.71x
RESHAPE C       (-29490,-29490,-20000)   ce8c ce8c e0b1   -29490 -29490 -25423 -20000     3.39x
clamp knee |gp-0x6c2c| @90+ km/h:  V106 5324 · A 1065 · B 1963 · C 1570
```
All three hold `Y[0]` **exactly** at V106's −29490 ⇒ **creep clamp duty (~10 %, measured) and the relay
index (1.35) are UNCHANGED by construction.** Every entry is int16-legal (worst 90.0 % of 32767). X is
untouched so no LERP denominator can go to zero.
🛑 **Highway clamp duty is UNKNOWN** — the entire measured `|gp-0x6c2c|` corpus is <16 km/h. **B** is the
best risk-adjusted pick: it keeps a real (if shallower) speed taper, and its 1963 knee sits above
creep's p99 (1704), so even if highway acceleration content resembles creep's it lands near ~1 % duty
rather than A's ~10 %.

Related: [[reference_accord_v106_gp6b26_mechanism_ceiling_and_reshape]] ·
[[accord-gp6752-is-negative-one]] · [[accord-gp6b26-is-inertia-not-damping]] ·
[[reference_accord_fun41464_rate_signal_hub_and_fun34350_damper_hook]]
