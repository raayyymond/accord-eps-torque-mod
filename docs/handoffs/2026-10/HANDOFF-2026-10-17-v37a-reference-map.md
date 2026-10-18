# HANDOFF 2026-10-17 — V37A: the operator's V37 file, with the 2× moved onto the rate-reference map

**Status at close-out:** V37A **REV 3** BUILT, VERIFIED, **NOT FLOWN** — the flight candidate. Rev 1 and rev 2 SUPERSEDED.

## REV 3 (same day) — the operator's second correction
*"assist map should also not just be 2x slope, sorry, should just be linear with 2x the previous max."* Rev 3 map: every
record Y'[i] = round(2·Ytop·X[i]/240), a straight line from the origin to twice the record's stock top (V280 rev 2's formula
with K_TOP = 2). Slot 7: **0,17,29,34,46,92,138,183,229,344**; the integer LERP walk stays within 1.37 counts of the line.
Feedback clamp `0xC62E6` 7680 → **15360** (exactly 2×; Honda's 1.3953 ratio held). Torque stays V37's 2× (1782/1024/1024).
301 B vs V37, 0 code bytes. rwd `39990-TVA,A160-V37A-REV3-V37BASE-MAP.LINE.2XTOP344-GAIN1782-CLAMPS1024-FBCLAMP15360-0x13000-0x100000.rwd`
sha256 `af57a2365a1781d58410039ed6acd7303d61989253be6f13bb44ce859c040ee8`; image `_v37a_REV3_plain_image.bin` sha256
`e33a97ee2a9cd8be2e4a8080c121fec74776588c46d10f35a0ae34458487805e`. Delivered (fb = 0): idx 12 T 33 (stock 23, V37 46),
idx 60 T 275 (152/304), idx 120 T 755 (324/649), P rails from idx 128 → T 820. **Consequence to state plainly:** Honda's map
is concave, so a straight line to 2× its top sits BELOW it until idx ≈ 77 (17 vs 24 at idx 12) — small corrections ask a
slower wheel than stock while being pushed 2× as hard; the 2× ask is reached only toward full demand (344 ≈ 44.5 deg/s).
The same 2× top flew as V278 rev 3 (Honda's shape, ×6 torque: 42 deg/s hands-light, no ring). Golden `_self_check_v37a`
repointed to rev 3 (97 symbols, hash unchanged). Rev-3 delta re-check PASS_WITH_DEFECTS (`docs/review/ADV-V37A-REV3-DELTA-2026-10-17.md`): bytes/CRC/payload clean, map == formula from stock, LERP within 1.37 of the line, rail idx 128 / T 820; it corrected the crossing to idx 76–78; open: DTC 0x5E under a stalled railed lane.
Pre-registered read: full-demand hands-light rate ≈ 42 deg/s (stock 24); low-demand rate per idx 0.7–1× stock; null ⇒ inert.

*(Previous status line, kept:)* V37A **REV 2** BUILT, VERIFIED, **NOT FLOWN**. Four adversarial lenses passed rev 1 (none "do not
flash"); the focused re-check of the rev-2 delta is PASS_WITH_DEFECTS (`docs/review/ADV-V37A-REV2-DELTA-2026-10-17.md`): rail +820 (+827/−828 with D), the 1024 clamp cannot bind, no truncation, no lane-derived threshold crossed; OPEN: DTC 0x5E observer under a prolonged stall at the rail — watch its latch on the first drive.

## REV 2 (same day) — the operator's correction
After rev 1 was reported, the operator ruled: *"no, peak torque should be 2x and peak angle velocity setpoint should be 2x
too."* Rev 1 had put `0xC646C`/`0xC61B2`/`0xC61B4` back to stock (891/512/512). **Rev 2 keeps V37's 1782/1024/1024** and
carries the same map [A] and clamp [B]. Delivered rail = 2 × Honda's: 820 counts (P 15360 × 254/256 → lag 0.990 → ×1782
>> 15), under the 1024 clamp, reached from idx 63 at a stalled wheel (V37 reached 799 only at idx 240). 350 B vs V37.
rwd `39990-TVA,A160-V37A-REV2-V37BASE-MAP.SLOPE2X.NOCAP-GAIN1782-CLAMPS1024-FBCLAMP42865-0x13000-0x100000.rwd` sha256
`71652fa89e2bc90b1f54a5b3f5acc717df18ec4f14666cc892018666430ee0b0`; image `_v37a_REV2_plain_image.bin` sha256
`6b457089a831d27c8a2bad7c1ce6842b99cd5efea2e0cf8c5b8d3222de153413`. Rev 1 renamed `SUPERSEDED-DO-NOT-FLASH-REV1-…` /
`_v37a_REV1_SUPERSEDED_plain_image.bin`. Golden `_self_check_v37a` repointed to rev 2 (97 symbols, hash unchanged).
Risks shift: 2× authority arrives from idx 63; V280's 7 Hz stall mechanism at 1/3 of V280's torque; the 0xE4 RX-fault
sentinel pulse is 820 T for 2 s chasing 123 deg/s (V37: 794 T chasing 22). **Everything below describes REV 1 unless it
says otherwise; where it says "Honda's 410" or "halves", rev 2 reads 820 / "2× as V37".**
Not part of the V300 release line (`STATE.md` decision box is unchanged except for a side-build paragraph).

## What was asked
The operator pointed at `Downloads/39990-TVA-A160 (Honda Accord)/39990-TVA,A160-V37-2xTorque.rwd`: identify the
version, then "understanding all that we do now at V300, change the 2x mod implementation from 2x LKAS gain through
a constant, modify the LKAS angle velocity setpoint table to have a 2x slope w.r.t. the input (from CAN bus) and
remove the top cap (fixed 2x slope all the way up)". Naming rule: V36→V36A, so V37→**V37A**.

## Identification (EVIDENCE)
sha256 of the Downloads file `8a809d1b320957e4846c9145ee662858759d514681ce46c247a4a197784202da` == the kit's
`39990-TVA,A160-V37-V36-DTC0x49-OFF-torqueMax255-rateMax65535-dtcGate255-0x13000-0x100000.rwd`; its payload decrypts
(keys BF/10/9E, ops xor/xor/sub) to `_v37_plain_image.bin` (sha `9ce66090…`) byte for byte. V37 vs stock = 42 bytes:
the V18 2× (gain `0xC646C` 891→1782, clamps `0xC61B2/B4` 512→1024), ramp `0xC64DE`, the V25–V31 corridor ×4 and
boost floor 4096 (int + float), the V36 debounce and V37 DTC-0x49 cals, two PN bytes, two CRC trailers.

## What V37A is
`analysis-2020accord/builds/v18_v49/build_v37a_tva.py` (base = the V37 image, asserted against the Downloads rwd):
- **[A] assist map** — 28 LERP records via `0xC9A88` (`0xE4000..0xE8105`, n=10, X 0,12,20,24,32,64,96,128,160,240
  untouched). Y[i] = round(2·Y[1]·X[i]/12): a line at twice each record's own first-segment slope, no saturation.
  Live slot 7 (0xE502C): stock 0,24,42,50,62,100,126,154,166,172 → **0,48,80,96,128,256,384,512,640,960 = 4·idx
  exactly at every idx 0..240** (golden-model walk). The wire caps idx at 238/239, so no cap remains.
- **[B] `0xC62E6`** 7680 → **42865** = round(7680·960/172): Honda's sp:fb ratio 1.3953 at the new top. The one cell
  beyond the literal ask. Without it the lagged rate feedback freezes at ≈31 deg/s and above sp 240 (idx 60) the
  error could never change sign — the lane would stop damping where the new map asks most. V276/V278/V280 all
  scaled this cell with the map. 3 readers, all `ld.hu` — my own positive-controlled scan and two lenses agree.
- **[C] back to stock:** `0xC646C` 1782→891 (the lane's forward gain on this image via `ld.h 0x746c[tp]` @0x2A1EE,
  no V57 decouple; 4 more `ld.hu` readers in other assist paths also revert), `0xC61B2`/`0xC61B4` 1024→512.
- CRC trailers `0xC6FFC`, `0xE4FFC..0xE8FFC` recomputed. 356 B vs V37, 0 code bytes. Everything else carried.

**Consequence (from the images through the golden model, fb = 0 bound):** P rails from idx 63 at a stalled wheel
(stock never; Kp climbs 248→512 across idx 0..68), delivered T = **410 = Honda's rail** from idx 64 (stock 399 and
V37 799 at idx 240). At idx 120 the loop nulls at ≈62 deg/s (stock/V37 ≈19). **Peak LKAS torque halves vs V37;
the reference is 2× at small signal and 5.6× (≈124 deg/s) at the top.**

## Verification
69/69 build checks · independent rebuild bit-identical · CRC walk 49/49 + chain 50/50 (image and decoded rwd) ·
rwd payload == image · golden `_self_check_v37a` added to `eps_chain_control.py`, exported, called from
`_self_check()`: **97 symbols**, stdout hash `740f4bcd…` unchanged (CLAUDE.md count updated 94→97).

**Adversarial pass (all four PASS_WITH_DEFECTS; reports `docs/review/ADV-V37A-{ARITHMETIC,UNITS-FBCLAMP,BUILD-AUDIT,INTERLOCKS}-2026-10-17.md`):**
- Arithmetic: no overflow/sign/truncation (|E| ≤ 73585, |E·Kp| ≤ 52.8e6, D clamps at 10240 on a 0→960 step);
  Y read `ld.hu` + `mulh`; n hard-coded 10; idx ±240 via `0xC64F0/F1`; mirror reproduces rail idx 63 / T 410.
  Defect: selectors 0/2/4/5 (reachable, not live) deviate ≤ 1.17 counts from a line.
- Units + clamp: 16.1257 wire/idx and DC 30.89 re-derived from bytes; max idx 238 (+) / 239 (−) so top sp 952/956;
  the "2× slope" is exact only in the first segment, ratio 2.0→5.6× to the top; P/sum clamps bind at |E| 5650 so
  above sp 177 the reference raises authority, not rate. **Adjudicated by me:** the 0xE4 RX-fault sentinel (0x7FFF →
  idx 238) rails P for the 2.048 s ramp-down at 410 T chasing 123 deg/s (stock 397 T toward 22; V37 794 T) —
  Honda's torque, half of V37's, longer push; mitigation `0xC63F6` 16→328 exists, NOT applied.
- Build audit: hashes reproduced, 0 unexplained bytes vs V37 and vs stock, headers == V37, exactly one V37A rwd;
  census 24 load-bearing / 15 vacuous / ~10 readback of 69; 8/11 mutations caught; gap: a +1 on an interior knot of
  a non-live record passes the script (independent rebuild shows the shipped bytes are right).
- Interlocks: gp-0x6a32 has zero readers besides the lane; map table read only by the lane + a dead twin
  (FUN_0002a93a); no stall/overload timer; soft-EME floor 4096 ≫ 417; STEER_STATUS machine, ramp, gate, first-tick
  sentinel and 0xE4 gates byte-stock. Defects: DTC 0x5E observer under a stall at the rail (BELIEF, unverified);
  V36/V37 trips off ⇒ no firmware override for a hands-on driver; `0xC646C` restore halves four non-lane paths vs V37.

## Risk before the drive (also on the page)
Authority halves vs V37 · P-rail from idx 63 makes V280's 7 Hz strong-turn ripple mechanism reachable at 1/6 of
V280's torque (BELIEF: milder) · low-idx damping is the K = 2 regime V278 flew clean · sentinel pulse as above ·
V36/V37 trips stay off.

## Pre-registered read (no cave on this base; the signal is free on the wire)
Achieved wheel rate per idx at idx ≤ 60 doubles vs V37/stock (0.26 → 0.52 deg/s per idx); full-demand hands-light
rate well above stock's ≈24 deg/s, well below 124. **Null:** rate per idx unchanged ⇒ the map is not the live
setpoint source on this image (selector ≠ 7) ⇒ inert, not harmful.

## Files
Kit: `builds/v18_v49/build_v37a_tva.py` · `studies/v37a/gen_page_data.py` · `docs/artifacts/V37A-PAGE-2026-10-17.html`
(+ `docs/artifacts/v37a/page_data.json`) · `docs/review/ADV-V37A-*.md` · lineage PART6 V37A + lever-index row ·
STATE side-build paragraph · memory `memory/accord/builds/accord-v37a-built-reference-map-2x-slope-no-cap.md`.
Firmware repo: the V37A rwd (sha `c9bd3446…`) and `_v37a_plain_image.bin` (sha `7cb6fd3a…`).
Page: https://claude.ai/artifact/TavHVFCPZmYEeNng6e5Loq

## Next
The flash is the operator's call (name file + bus; openpilot killed first). If flown: read rate-per-idx at low
demand and the strong-turn ripple; if the sentinel pulse is felt, `0xC63F6` 16→328 is the designed mitigation.
