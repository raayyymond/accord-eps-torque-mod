---
name: reference_accord_two_lkas_routes_gp6b4c_bypasses_auth
description: REFUTES the "PID lane is the sole actuation route" claim. LKAS is lane 1, its mode byte 0xC4124[1]=0 routes REQ_B (gp-0x62f8[1]) into gp-0x62b0 -> gp-0x3d88 -> gp-0x6b4c -> aggregator at unity weight, NEVER touching gp-0x6ad6/PID/gp-0x6ad4/AUTH. gp-0x62f8[] is runtime-written by FUN_00025c32 at 0x26496, paired with gp-0x62e0[]. So the AUTH ramp (0xC67BE, 2->20 km/h) is real but NOT exclusive and cannot explain the slow engaged return.
metadata:
  type: reference
---

# There are TWO LKAS routes to the motor; only one sees AUTH — 2026-08-12 (`fw-return`)

Dispatched to prove/refute `fw-loop`'s *"the only route from the LKAS command to the motor is
`gp-0x6b4a` → `gp-0x6ad6` → PID → `gp-0x6ad4` → aggregator, clamped to AUTH"*, whose own stated
falsifier was *"if a second route exists, the AUTH story is wrong."* **A second route exists.**

## The chain [EVIDENCE]

1. **LKAS is lane 1** — this kit's own census, in
   [[reference_accord_gp6afe_gp6b4e_provably_zero_correction]].
2. **`0xC4124[1] = 0` ⇒ mode 0.** `0xC4124 = [0,0,5,0,5,5,0,0,0,5,0]`, identical stock→v96.
3. **Mode 0 writes `gp-0x62b0[i] = REQ_B = gp-0x62f8[i]`** (`FUN_00026c80` @`0x26c80`, else-branch
   `*puVar35 = uVar18`). **Mode 5 writes `0` there** — the only reason the sibling lane is dead.
4. **`gp-0x62f8[lane]` is RUNTIME-written, paired with `gp-0x62e0[lane]`**, by request decoder
   `FUN_00025c32`:
```
0x2647c: mov r1,r8 / 0x2647e: shl 0x1,r8            r8 = lane*2
0x26480: movea -0x62e0,gp,ep / add r8,ep / 0x26486: sst.h r12,0x0[ep]   REQ_A[lane]
0x26490: movea -0x62f8,gp,ep / add r8,ep / 0x26496: sst.h r14,0x0[ep]   REQ_B[lane]  <<<
```
   Same lane index, same decode site ⇒ **REQ_A and REQ_B are two components of ONE request.**
5. `gp-0x3d88 = Σ gp-0x62b0[i]` → `gp-0x6b4c = clamp(gp-0x3d88, ±10240)` (`0x276f0`/`0x27708`/`0x27716`)
   → aggregator `FUN_0003aa2c` @`0x3aa3e`, **unity weight** → `gp-0x6b94` → governor → shaper → FOC.

⇒ **LKAS reaches the motor without touching `gp-0x6ad6`, the PID, `gp-0x6ad4` or AUTH.**

## Where the reasoning failed — a reusable pattern
`0xC63CC = 0` really does kill `gp-0x6b4c`'s second term, leaving `gp-0x6b4c = clamp(gp-0x3d88, ±10240)`.
The error was reading the survivor `gp-0x3d88` as *unrelated to LKAS*. **It is a sum over the SAME
11-channel request structure that feeds `gp-0x6b4a`** — only the per-channel mode differs.
🛑 **Lesson: when a cal zeroes one term of a sum, check what the SURVIVING term is made of.** "It is
just X" is a claim about X's provenance, and here X was the other half of the same request.

⊕ Two independent corroborations that were already on file: the kit's own note *"the entire LKAS
contribution flows through `gp-0x6b4c` … **and** through `gp-0x6b4a`"*, and `0xC6CD0` — our 4× LKAS
forward gain, **stock 65535 → 3564 on every build v90→v96** — which sits on the `gp-0x6b4c` lane. We
have been deliberately scaling the very route the claim said carried no LKAS.

## The contrast that makes it airtight
Sibling `gp-0x62c8[]` → `gp-0x6b4e` **is** genuinely dead: mode 0 writes it an explicit `st.h r0`,
mode 5 never writes it, boot zero. **`gp-0x62b0[]` under mode 0 gets a real value instead of a zero
store.** All five arrays are boot-zero (`gp-0x62f8` @flash `0x86DB8`) ⇒ liveness rests entirely on the
runtime write at `0x26496`.

## AUTH itself — real, correctly characterised, just not exclusive [EVIDENCE]
`AUTH = min( LERP_{gp-0x6bda}, LERP_{speed}, 5120 )`.
🛑 **The speed table's header is `0xC67BE`, NOT `0xC67C8`** (that address is its `Y[0]`).
Struct `[flag][count][X…][Y…]`: count=3, **X=[128,1280,3200] ct = [2,20,50] km/h**, **Y=[0,1024,1024]**
at 64 ct/km/h ⇒ 227 @6 km/h, 455 @10, 1024 @≥20. Constant partner **5120 @`0xC679C`**; the `gp-0x6bda`
partner is X=[384,1280,12800] Y=[0,5120,5120] — it cuts authority to zero **at the rack end stop**,
converging with [[reference_accord_return_centre_is_an_end_stop_cushion_not_centring]].

## 🛑 Method trap — the request arrays are `ep`-relative
14 of the 15 `gp-0x62f8` base-setup sites are `movea -0x62f8, gp, **ep**`, and the real accesses are
**`sst.h`/`sld.h 0x0[ep]`**, which carry **no `-0x62f8` in operand text at all**. An operand search
returns the base setup and **zero actual loads/stores** — the same false-zero class as `-0x6350`, and
it applies to *every* request array here (`gp-0x62e0/62b0/6298/62c8/633c`). A Python `movea`-immediate
scan (`imm = (-off)&0xffff` in `hw2`) reproduced Ghidra's 15 sites one-for-one; use it as the second
method.

## Not established
Magnitude of `REQ_B` on lane 1 — the route is proven to exist, be runtime-written and be AUTH-free;
**what fraction of the delivered command it carries is unmeasured.** That is a probe
(`gp-0x6b4c` vs `gp-0x6ad4`), not a trace.
