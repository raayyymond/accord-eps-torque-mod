---
name: accord-0x14a-byte4-bits-0-2-are-stock-honda-cave-owns-3-7
description: "The CAN 0x14A byte-4 cell gp-0x1514 is FULL. Bits 0/1/2 are written by Honda's frame builder (0x55B06/0x55AE8/0x55AC0 from gp-0x679a/679b/6799) BEFORE the cave hook 0x55C0E; bits 3/4/7 by the three-sign rung; 5 and 6 by the V282 comparators. A \"free bit\" census must include the STOCK frame builder, not just the cave's own masks. V288 rev 1 overwrote stock bit 0 because it did not; V288 rev 2 repurposed the kit's own bit 5 = sign(y)."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 4fb8c05d-08ba-46ea-96e0-19a3b1899a03
  modified: 2026-09-08T05:31:22.152Z
---

# 0x14A byte 4: bits 0–2 are stock Honda; the cave owns 3–7 (2026-09-07)

Verified in Ghidra at 0x55AB0–0x55B0A: three `ld.bu / andi / or / st.b` sequences on gp-0x1514 with masks 0xFB, 0xFD, 0xFE,
inside FUN_00055a98 and upstream of the cave hook at 0x55C0E, so the cave runs LAST and any rung on those bits destroys a
transmitted Honda flag. The 32-bit RMW at 0x21964 masks 0xff0000ff and preserves byte 4 and byte 7; gp-0x1511 has stock
writers at 0x55BF2 / 0x55C1C plus the flown rung 0xC4BC4 (bits 6–7): census it before using it.

**How to apply:** before spending a telemetry bit, enumerate EVERY writer of the byte image-wide (Ghidra xrefs + raw scan),
not the cave region alone, and state which bits are Honda's. On V288: b4.5 = sign(y) (was |r24|≥|aggregator|, never used in
an analysis), b4.6 = |r24|≥|T| kept, b4.3/4/7 the three-sign rung, b4.0–2 stock. rlog decoders written for V282's b4.5 must
be updated for V288. See [[accord-v288r2-setpoint-prefilter-cave-built-adversarial-pass-passed]].
