# 🛑 When asked what a build DOES, answer functionally and against STOCK — not as a per-build delta

**Standing operator preference, stated 2026-07-31.** Asked "what does V62 do", the first answer was a
per-build delta ("V62 = V59 + two `sar` immediates"). That is the *engineering* framing and it is not what
the operator wants. They asked for, and explicitly modelled, this shape:

> * 4x LKAS gain + hard, soft, and gentle EME fixes
> * LKAS steer to zero
> * Something about dampers...
> * Live telemetry of \<insert details here\>
> * ...also anything else I might've missed

## The rules
1. **Baseline is STOCK `39990-TVA-A160`, cumulative** — every edit the car is carrying, not the delta
   from the previous build. The operator is asking "what is on my car", not "what changed this week".
2. **Group by what it does for the CAR**, one bullet per capability, in plain language. Addresses and
   build numbers are supporting detail *inside* a bullet, never the bullet itself.
3. **Say what is notably ABSENT.** The "anything else I might've missed" follow-up is a standing part of
   the request. Things that surprise: a lever reverted by a later build, or a confirmed root-cause fix
   that is *not* in the current line.
4. 🛑 **Derive it from the IMAGE, not from the lineage doc.** Run
   `analysis-2020accord/verify/diff_build_vs_stock.py <build>`; it attributes every differing byte to a named
   edit and **fails loudly on any byte it cannot account for**. Attribution is derived empirically by
   walking `_v*_plain_image.bin`, not read off `BUILD-LINEAGE.md`. This has already caught two things a
   doc-based answer would have got wrong (see below).
5. Separate **CRC bookkeeping bytes** from **functional bytes** so the totals mean something.

## Why deriving it from the image matters — two live examples
- **`0xC646C` is back at STOCK 891.** V22/V38 raised it 891→1782→3564, then **V57 reverted it** and moved
  the 3564 onto the private cell `0xC6CD0`. A lineage-based answer would have reported a raised shared
  gain that is not there.
- **`0x454FE` (V42's state-4 governor fix) is NOT in this build line** — a *confirmed root cause* of the
  hard-turn ratchet, marked "carry forward", absent because V53+ descend from V38/FOURFRAME. Benign in
  practice (`ST==4` has fired in 0 of 143,933 frames) but exactly the kind of thing the "what did I miss"
  question is for. Both are now asserted in the script so the claim cannot rot.

Related: [[feedback_eps_lkas_chain_model_golden_reference]], [[accord-check-build-lineage-before-proposing-lever]].
