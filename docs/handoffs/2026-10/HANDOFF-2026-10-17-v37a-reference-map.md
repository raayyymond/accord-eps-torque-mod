# HANDOFF 2026-10-17 — V37A: the operator's V37 file, with the 2× moved onto the rate-reference map

**Status at close-out:** V37A BUILT, VERIFIED, ADVERSARIALLY PASSED (four lenses, none "do not flash"), **NOT FLOWN**.
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
