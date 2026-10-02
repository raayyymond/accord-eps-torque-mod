# TRACE 2026-10-01 — the stock camera's 0xE4 byte-2 field (bits 3:2) over EVERY cached route

**Question.** V298 runs the EPS LKAS lane only when `gp-0x6803 == 2`, where `gp-0x6803` is 0xE4 (STEERING_CONTROL)
byte 2 bits 3:2. The interlock is fail-safe against the stock camera only if the camera **never** emits 2 in that
field. Round 1 measured {0, 1} on 12 routes (`_scratch/angle_loop/fork-interface/cam_e4.py`, `cam_e4_multi.py`).
This trace extends that census to every rlog segment in the kit's cache.

**Answer (EVIDENCE, method below).** Over **95 routes, 1,183 segments, 6,898,004 camera-side (bus 2) 0xE4 frames**,
byte-2 bits 3:2 took only the values **0 (5,344,781) and 1 (1,553,223)**. **Zero frames carry 2; zero carry 3.**
openpilot's own 0xE4 (sendcan, **bus 1** on this car, *not* bus 0) carried byte 2 & 0x7F = **0 on all 6,790,970
frames**, so the fork does not send 2 today and the fork change (bits 3:2 = 2 on every frame) is required.

- Script: `rlog-tools/studies/angle_loop/camera_e4_byte2_census.py` (reproducible: `python rlog-tools/studies/angle_loop/camera_e4_byte2_census.py`,
  ~100 s on 14 workers). Full output: `_scratch/logs/camera_e4_byte2_census.txt`; merged JSON:
  `_scratch/out/camera_e4_byte2_census.json` (both gitignored, regenerable).
- Cache read: `analysis-2020accord/rlogs/*--rlog.zst`, the only raw-rlog store in the kit. `_scratch/cache/`,
  `rlog-tools/_scratch/cache/` and `analysis-2020accord/_scratch/cache/` hold only derived `.npz/.json` (no raw CAN
  bytes), so they cannot answer a byte-level question and were not used.

---

## 1. Field definition and firmware extraction

| item | value | status |
|---|---|---|
| DBC (fork `_steering_control_d_ext.dbc`, imported by `honda_accord_2017_can_ext`) | `STEER_TORQUE 7\|16@0-` = bytes 0–1 BE signed · `STEER_TORQUE_REQUEST 23\|1@0+` = byte 2 bit 7 · `SET_ME_X00 22\|7@0+` = byte 2 bits 6:0 | EVIDENCE (read from the fork copy under `analysis-2020accord/studies/v295/design/harness/_scratch/fork_20d24ab79/`) |
| `gp-0x6803` | `(byte2 << 0x1c) >> 0x1e` = byte 2 bits 3:2 | EVIDENCE: `TRACE-2026-09-09-kp-kd-schedule-axis.md` (Ghidra) |
| the `>> 0x1e` is a **logical** shift | V298 image halfwords: `0x526E6 42dc` = `shl 0x1c, r8`; `0x526F6 429e` = `shr 0x1e, r8` (Format II opcode 0b010100 = `shr`, not 0b010101 `sar`). Anchor: `0x52702 329f` = `shr 0x1f, r6`, the STEER_REQUEST extraction the 09-09 trace cites at that exact address | EVIDENCE by Python halfword decode of the V298 image; **not re-confirmed in Ghidra this pass** |
| ⇒ stored value is the unsigned field 0..3, and **bits 3:2 = 0b10 ⇔ `gp-0x6803 == 2`** | (a `sar` would have mapped 0b10 → −2 and made the cmp-2 arm unreachable; it is not a `sar`) | EVIDENCE (follows from the row above) |

`_bosch_2018.dbc` additionally names `DRIVER_OVERRIDE 17|1` (byte 2 bit 1) and `CONTROL_STATE 26|3` (byte 3 bits
2:0); the script tallies both for reference.

## 2. Bus map: openpilot's 0xE4 is on bus **1**, not bus 0 (correction to the brief)

The fork's `opendbc/car/honda/hondacan.py::CanBus` for Bosch-with-radar: bus 0 = ACC-CAN radar side, **bus 1 = F-CAN
powertrain (the EPS)**, bus 2 = ACC-CAN camera side; with openpilot longitudinal, `CAN.lkas = CAN.pt = 1`. The wire
agrees (EVIDENCE, every route):

| `CanData.src` / stream | what it is | frames (pooled) | byte-2 bits 3:2 = 0/1/2/3 |
|---|---|---|---|
| **can src 2** | **stock camera's 0xE4 (TARGET)** | **6,898,004** | **5,344,781 / 1,553,223 / 0 / 0** |
| can src 128 | panda TX echo on bus 0 = camera frames forwarded 2→0 once openpilot is up | 6,814,015 | 5,260,792 / 1,553,223 / 0 / 0 |
| **sendcan bus 1** | **openpilot's own 0xE4** | **6,790,970** | **6,790,970 / 0 / 0 / 0** |
| can src 129 | panda TX echo on bus 1 (openpilot's frames on F-CAN) | 6,789,491 | 6,789,491 / 0 / 0 / 0 |
| can src 193 | bus 1 + 0xC0: openpilot frames the panda did not transmit (BELIEF: blocked-TX flag; only in the first ~0.1 s of openpilot TX) | 1,420 | 1,420 / 0 / 0 / 0 |
| can src 1 | **received** on F-CAN: the stock (radar-relayed) 0xE4 the EPS sees **before openpilot starts transmitting** | 70,564 | 70,564 / 0 / 0 / 0 |
| can src 0 | received on ACC-CAN radar side before openpilot starts (relay closed) | 83,792 | 83,792 / 0 / 0 / 0 |

No `sendcan` 0xE4 on bus 0 or bus 2 and no src 130 exist anywhere, so **every src-2 frame is a frame received from
the camera**; openpilot is excluded by bus, not by content. src 0/1 frames occupy only the first ~8–10 s of segment 0
(checked on routes `a6` and `75`: src 0/1 end at 10.4–10.6 s / 8.2–8.4 s, exactly where `sendcan` bus 1 and src
128/129 begin).

## 3. Pooled results, camera (src 2)

| quantity | value |
|---|---|
| frames | 6,898,004 (95/95 routes have camera frames; min 6,151 on one route) |
| byte-2 bits 3:2 = 0 / 1 / **2** / 3 | 5,344,781 / 1,553,223 / **0** / 0 |
| byte 2 & 0x7F (whole SET_ME_X00) | only `0x00` (5,330,390), `0x04` (1,553,223), `0x01` (14,391); bits 6:4 never set |
| STEER_TORQUE_REQUEST 0 / 1 | 6,763,862 / 134,142 (68 of 95 routes have camera req = 1) |
| (req, bits 3:2) | (0,0) 5,210,843 · (0,1) 1,553,019 · (1,0) 133,938 · (1,1) 204 |
| max \|STEER_TORQUE\| | 2,560 (over all frames, and over req = 1 frames) |
| req = 1 with torque ≠ 0 | 133,672; torque ≠ 0 with req = 0: **0** |
| DRIVER_OVERRIDE (byte 2 bit 1) | 0 on every frame |
| byte 3 & 7 (CONTROL_STATE) | 0 on every frame |
| DLC | 5 on every frame |

27 routes show a camera that never requests and never sets field = 1 (camera LKAS off or unavailable on those drives);
67 routes have field = 1 frames. **No route shows 2 or 3.** openpilot (sendcan bus 1): max \|tq\| 4,096, req = 1 on
4,908,021 frames, byte 2 & 0x7F = 0 on all.

## 4. Per route

Columns: camera = can src 2; OP = sendcan bus 1; "pre-OP bus-1" = received 0xE4 on F-CAN before openpilot TX, as
`n (bits3:2 0/1/2/3)`. The script prints this table.

| route | seg | cam frames | cam bits3:2 0/1/2/3 | cam req=1 | cam max\|tq\| | cam byte2&0x7F | OP frames (sendcan b1) | OP bits3:2 0/1/2/3 | OP byte2&0x7F | pre-OP bus-1 frames (field) | errs |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `00000013--f484e75b00` | 4 | 22395 | 22395/0/**0**/0 | 0 | 0 | [0] | 22396 | 22396/0/0/0 | [0] | 0 (0/0/0/0) | 0 |
| `0000001a--a4ef772958` | 1 | 6159 | 6159/0/**0**/0 | 0 | 0 | [0] | 5366 | 5366/0/0/0 | [0] | 617 (617/0/0/0) | 0 |
| `0000001b--d2abf1af1c` | 1 | 6151 | 6151/0/**0**/0 | 0 | 0 | [0] | 5332 | 5332/0/0/0 | [0] | 647 (647/0/0/0) | 0 |
| `0000001b--d7c81cf9b5` | 2 | 12181 | 12181/0/**0**/0 | 0 | 0 | [0] | 11034 | 11034/0/0/0 | [0] | 903 (903/0/0/0) | 0 |
| `0000001c--ade8fd5b4a` | 2 | 11290 | 11290/0/**0**/0 | 0 | 0 | [0] | 10468 | 10468/0/0/0 | [0] | 645 (645/0/0/0) | 0 |
| `0000001e--28ef595061` | 23 | 133775 | 118181/15594/**0**/0 | 3854 | 1839 | [0, 4] | 132403 | 132403/0/0/0 | [0] | 750 (750/0/0/0) | 0 |
| `00000021--489af1e5b7` | 18 | 106758 | 94754/12004/**0**/0 | 1128 | 1574 | [0, 4] | 105244 | 105244/0/0/0 | [0] | 864 (864/0/0/0) | 0 |
| `00000022--00f57626e0` | 12 | 72003 | 60153/11850/**0**/0 | 404 | 523 | [0, 4] | 70627 | 70627/0/0/0 | [0] | 874 (874/0/0/0) | 0 |
| `00000023--fc5f268959` | 9 | 54140 | 46588/7552/**0**/0 | 1702 | 1823 | [0, 4] | 53105 | 53105/0/0/0 | [0] | 766 (766/0/0/0) | 0 |
| `00000024--6f4943e0a6` | 14 | 83180 | 78974/4206/**0**/0 | 774 | 1415 | [0, 4] | 81751 | 81751/0/0/0 | [0] | 882 (882/0/0/0) | 0 |
| `00000024--bc45926e80` | 16 | 94357 | 92331/2026/**0**/0 | 1246 | 2230 | [0, 4] | 93553 | 93553/0/0/0 | [0] | 754 (754/0/0/0) | 0 |
| `00000028--66ab5a2233` | 5 | 29995 | 29995/0/**0**/0 | 0 | 0 | [0] | 29975 | 29975/0/0/0 | [0] | 0 (0/0/0/0) | 0 |
| `00000029--47bc9c9d99` | 2 | 7898 | 7898/0/**0**/0 | 0 | 0 | [0] | 7163 | 7163/0/0/0 | [0] | 752 (752/0/0/0) | 0 |
| `0000002b--604bd0e8f8` | 13 | 76342 | 66616/9726/**0**/0 | 1244 | 1485 | [0, 4] | 74979 | 74979/0/0/0 | [0] | 888 (888/0/0/0) | 0 |
| `0000002b--7926e8f7e5` | 14 | 84149 | 50129/34020/**0**/0 | 322 | 778 | [0, 4] | 83264 | 83264/0/0/0 | [0] | 666 (666/0/0/0) | 0 |
| `0000002c--eb219f392c` | 9 | 51123 | 34253/16870/**0**/0 | 818 | 2114 | [0, 4] | 50273 | 50273/0/0/0 | [0] | 666 (666/0/0/0) | 0 |
| `0000002d--10714693cd` | 14 | 82509 | 50197/32312/**0**/0 | 3412 | 1527 | [0, 4] | 81117 | 81117/0/0/0 | [0] | 875 (875/0/0/0) | 0 |
| `0000002e--855ecfcf30` | 16 | 93318 | 93318/0/**0**/0 | 2954 | 2086 | [0] | 91826 | 91826/0/0/0 | [0] | 914 (914/0/0/0) | 0 |
| `00000031--0441e00d2b` | 4 | 22201 | 22201/0/**0**/0 | 0 | 0 | [0] | 21354 | 21354/0/0/0 | [0] | 686 (686/0/0/0) | 0 |
| `00000031--a680e9b2ac` | 11 | 65571 | 65571/0/**0**/0 | 0 | 0 | [0] | 64181 | 64181/0/0/0 | [0] | 904 (904/0/0/0) | 1 |
| `00000032--33a5dbbcb3` | 15 | 85539 | 57387/28152/**0**/0 | 1180 | 1346 | [0, 4] | 84136 | 84136/0/0/0 | [0] | 867 (867/0/0/0) | 0 |
| `00000033--1948a2c354` | 15 | 87006 | 69008/17998/**0**/0 | 2346 | 1175 | [0, 4] | 85604 | 85604/0/0/0 | [0] | 867 (867/0/0/0) | 0 |
| `00000034--e2d2d5381f` | 18 | 104051 | 91737/12314/**0**/0 | 1264 | 2434 | [0, 4] | 102497 | 102497/0/0/0 | [0] | 910 (910/0/0/0) | 0 |
| `00000035--580292087d` | 19 | 108497 | 96357/12140/**0**/0 | 1842 | 2496 | [0, 4] | 106919 | 106919/0/0/0 | [0] | 910 (910/0/0/0) | 0 |
| `00000035--77808fe7ce` | 3 | 14955 | 14955/0/**0**/0 | 0 | 0 | [0] | 14265 | 14265/0/0/0 | [0] | 707 (707/0/0/0) | 0 |
| `00000036--f4be1a18e9` | 15 | 89717 | 59897/29820/**0**/0 | 164 | 550 | [0, 4] | 88240 | 88240/0/0/0 | [0] | 897 (897/0/0/0) | 0 |
| `00000037--4a79da5d18` | 9 | 48416 | 48416/0/**0**/0 | 0 | 0 | [0] | 47446 | 47446/0/0/0 | [0] | 770 (770/0/0/0) | 0 |
| `00000037--6231e33f3d` | 15 | 86263 | 62105/24158/**0**/0 | 1890 | 1585 | [0, 4] | 85457 | 85457/0/0/0 | [0] | 785 (785/0/0/0) | 0 |
| `00000038--f77bddf4bd` | 15 | 84815 | 44663/40152/**0**/0 | 152 | 1069 | [0, 4] | 83658 | 83658/0/0/0 | [0] | 779 (779/0/0/0) | 0 |
| `00000039--f56039af87` | 16 | 95262 | 81002/14260/**0**/0 | 1242 | 2496 | [0, 4] | 93771 | 93771/0/0/0 | [0] | 892 (892/0/0/0) | 0 |
| `0000003a--283a39a1d6` | 13 | 73433 | 67570/5863/**0**/0 | 1344 | 1235 | [0, 4] | 72071 | 72071/0/0/0 | [0] | 872 (872/0/0/0) | 0 |
| `0000003a--4e55c1e0f4` | 7 | 37144 | 37144/0/**0**/0 | 0 | 0 | [0] | 36299 | 36299/0/0/0 | [0] | 671 (671/0/0/0) | 0 |
| `0000003b--a4a7f4dbf1` | 14 | 83047 | 53145/29902/**0**/0 | 1618 | 2496 | [0, 4] | 82274 | 82274/0/0/0 | [0] | 760 (760/0/0/0) | 0 |
| `0000003c--927965c2b4` | 13 | 74295 | 57159/17136/**0**/0 | 762 | 746 | [0, 4] | 73158 | 73158/0/0/0 | [0] | 817 (817/0/0/0) | 0 |
| `00000047--3e0b6134c0` | 26 | 150497 | 69321/81176/**0**/0 | 2438 | 2496 | [0, 4] | 149597 | 149597/0/0/0 | [0] | 691 (691/0/0/0) | 0 |
| `0000004a--346bf31d97` | 6 | 35999 | 35999/0/**0**/0 | 0 | 0 | [0] | 35992 | 35992/0/0/0 | [0] | 0 (0/0/0/0) | 0 |
| `0000004c--d0ea3c14b4` | 5 | 29999 | 29999/0/**0**/0 | 0 | 0 | [0] | 29994 | 29994/0/0/0 | [0] | 0 (0/0/0/0) | 0 |
| `0000004e--11f5b814b6` | 4 | 23999 | 23999/0/**0**/0 | 0 | 0 | [0] | 23994 | 23994/0/0/0 | [0] | 0 (0/0/0/0) | 0 |
| `0000004f--61171e660d` | 8 | 48168 | 38074/10094/**0**/0 | 1806 | 2560 | [0, 4] | 47284 | 47284/0/0/0 | [0] | 681 (681/0/0/0) | 0 |
| `00000050--50f2e00e8f` | 3 | 18166 | 18166/0/**0**/0 | 0 | 0 | [0] | 17310 | 17310/0/0/0 | [0] | 693 (693/0/0/0) | 0 |
| `00000054--4e67ae1164` | 21 | 123452 | 110578/12874/**0**/0 | 470 | 1079 | [0, 4] | 122542 | 122542/0/0/0 | [0] | 674 (674/0/0/0) | 0 |
| `00000058--1d1005262f` | 16 | 92984 | 92984/0/**0**/0 | 0 | 0 | [0] | 92112 | 92112/0/0/0 | [0] | 691 (691/0/0/0) | 0 |
| `00000059--9070b9dcee` | 15 | 88104 | 75466/12638/**0**/0 | 1752 | 2560 | [0, 4] | 87242 | 87242/0/0/0 | [0] | 681 (681/0/0/0) | 0 |
| `00000059--ad34044e59` | 13 | 77762 | 24296/53466/**0**/0 | 1820 | 1584 | [0, 4] | 76382 | 76382/0/0/0 | [0] | 855 (855/0/0/0) | 0 |
| `0000005a--2d32bec040` | 18 | 104214 | 71334/32880/**0**/0 | 600 | 1056 | [0, 4] | 103338 | 103338/0/0/0 | [0] | 674 (674/0/0/0) | 0 |
| `0000005e--03a9714d78` | 15 | 86858 | 58906/27952/**0**/0 | 794 | 1747 | [0, 4] | 85713 | 85713/0/0/0 | [0] | 779 (779/0/0/0) | 0 |
| `0000005e--857d0bd164` | 7 | 40108 | 40108/0/**0**/0 | 0 | 0 | [0, 1] | 39229 | 39229/0/0/0 | [0] | 708 (708/0/0/0) | 0 |
| `00000061--3b8f2f9278` | 13 | 76024 | 59908/16116/**0**/0 | 2006 | 1005 | [0, 1, 4] | 75149 | 75149/0/0/0 | [0] | 713 (713/0/0/0) | 0 |
| `00000062--1c7daa54e8` | 17 | 97513 | 71923/25590/**0**/0 | 1022 | 1436 | [0, 4] | 96264 | 96264/0/0/0 | [0] | 839 (839/0/0/0) | 0 |
| `00000063--1d4b188022` | 12 | 70708 | 30066/40642/**0**/0 | 812 | 1340 | [0, 4] | 69387 | 69387/0/0/0 | [0] | 854 (854/0/0/0) | 0 |
| `00000064--ce6b0b0ebb` | 16 | 91641 | 68665/22976/**0**/0 | 1456 | 1993 | [0, 4] | 90206 | 90206/0/0/0 | [0] | 871 (871/0/0/0) | 0 |
| `00000065--ae43aa0f27` | 11 | 63614 | 61360/2254/**0**/0 | 468 | 2496 | [0, 4] | 62621 | 62621/0/0/0 | [0] | 804 (804/0/0/0) | 0 |
| `00000065--b9f78988bd` | 14 | 81845 | 54675/27170/**0**/0 | 834 | 1753 | [0, 4] | 80726 | 80726/0/0/0 | [0] | 776 (776/0/0/0) | 0 |
| `00000066--276b942769` | 15 | 90169 | 88125/2044/**0**/0 | 14212 | 2519 | [0, 4] | 89251 | 89251/0/0/0 | [0] | 701 (701/0/0/0) | 0 |
| `00000067--9b3ebbe218` | 14 | 78911 | 48803/30108/**0**/0 | 1552 | 1516 | [0, 4] | 78033 | 78033/0/0/0 | [0] | 677 (677/0/0/0) | 0 |
| `00000068--0b7efae911` | 8 | 43761 | 41417/2344/**0**/0 | 1340 | 2560 | [0, 4] | 42790 | 42790/0/0/0 | [0] | 785 (785/0/0/0) | 0 |
| `0000006c--2bc842dbac` | 62 | 370232 | 194070/176162/**0**/0 | 6380 | 2138 | [0, 4] | 367634 | 367634/0/0/0 | [0] | 779 (779/0/0/0) | 0 |
| `0000006c--68c6e94b17` | 14 | 80769 | 51551/29218/**0**/0 | 214 | 678 | [0, 4] | 79405 | 79405/0/0/0 | [0] | 857 (857/0/0/0) | 0 |
| `0000006d--05e83bb04f` | 14 | 83386 | 56338/27048/**0**/0 | 3888 | 1781 | [0, 4] | 81956 | 81956/0/0/0 | [0] | 883 (883/0/0/0) | 0 |
| `0000006d--5d03a5adb4` | 12 | 68375 | 37213/31162/**0**/0 | 282 | 410 | [0, 4] | 67466 | 67466/0/0/0 | [0] | 716 (716/0/0/0) | 0 |
| `0000006d--5e7b4d2ceb` | 18 | 105949 | 64929/41020/**0**/0 | 870 | 1080 | [0, 4] | 104516 | 104516/0/0/0 | [0] | 838 (838/0/0/0) | 0 |
| `0000006e--649c462a6e` | 8 | 43812 | 23684/20128/**0**/0 | 1126 | 2502 | [0, 4] | 42578 | 42578/0/0/0 | [0] | 810 (810/0/0/0) | 1 |
| `0000006e--64b4a5fef4` | 23 | 133741 | 122951/10790/**0**/0 | 936 | 1335 | [0, 4] | 132398 | 132398/0/0/0 | [0] | 794 (794/0/0/0) | 0 |
| `0000006e--6ca3e014fd` | 15 | 86403 | 74467/11936/**0**/0 | 1622 | 2496 | [0, 4] | 84914 | 84914/0/0/0 | [0] | 937 (937/0/0/0) | 0 |
| `0000006f--80ca318af4` | 4 | 23201 | 23201/0/**0**/0 | 0 | 0 | [0] | 22149 | 22149/0/0/0 | [0] | 710 (710/0/0/0) | 0 |
| `0000006f--d876c761bc` | 13 | 75847 | 38327/37520/**0**/0 | 490 | 2537 | [0, 4] | 74742 | 74742/0/0/0 | [0] | 805 (805/0/0/0) | 0 |
| `00000070--66544f819d` | 4 | 21573 | 21573/0/**0**/0 | 0 | 0 | [0] | 20533 | 20533/0/0/0 | [0] | 734 (734/0/0/0) | 0 |
| `00000070--717f5a7866` | 19 | 113497 | 78939/34558/**0**/0 | 6558 | 2560 | [0, 4] | 111967 | 111967/0/0/0 | [0] | 917 (917/0/0/0) | 0 |
| `00000071--a7b8ba5d9d` | 17 | 102024 | 90216/11808/**0**/0 | 3238 | 2557 | [0, 4] | 100517 | 100517/0/0/0 | [0] | 888 (888/0/0/0) | 0 |
| `00000071--ac50da2a6a` | 4 | 23952 | 23952/0/**0**/0 | 0 | 0 | [0] | 22836 | 22836/0/0/0 | [0] | 809 (809/0/0/0) | 1 |
| `00000071--f2c9d073a3` | 18 | 102788 | 90484/12304/**0**/0 | 1658 | 2496 | [0, 4] | 101299 | 101299/0/0/0 | [0] | 861 (861/0/0/0) | 0 |
| `00000072--8001fc3048` | 16 | 92742 | 62270/30472/**0**/0 | 1962 | 1953 | [0, 4] | 91301 | 91301/0/0/0 | [0] | 865 (865/0/0/0) | 0 |
| `00000073--79fd149dd8` | 11 | 65821 | 38461/27360/**0**/0 | 844 | 1158 | [0, 4] | 64466 | 64466/0/0/0 | [0] | 895 (895/0/0/0) | 0 |
| `00000073--9380c74d52` | 11 | 61318 | 43220/18098/**0**/0 | 2000 | 911 | [0, 4] | 60125 | 60125/0/0/0 | [0] | 703 (703/0/0/0) | 0 |
| `00000074--2bf17ca67d` | 2 | 10738 | 10738/0/**0**/0 | 0 | 0 | [0] | 9649 | 9649/0/0/0 | [0] | 878 (878/0/0/0) | 0 |
| `00000075--6c8687d5bd` | 15 | 87134 | 72738/14396/**0**/0 | 378 | 585 | [0, 4] | 85938 | 85938/0/0/0 | [0] | 820 (820/0/0/0) | 0 |
| `00000076--c81e964e05` | 13 | 76062 | 30682/45380/**0**/0 | 660 | 941 | [0, 4] | 74745 | 74745/0/0/0 | [0] | 750 (750/0/0/0) | 0 |
| `00000076--d0b7ea7e4d` | 19 | 110479 | 102927/7552/**0**/0 | 7528 | 2496 | [0, 4] | 108937 | 108937/0/0/0 | [0] | 847 (847/0/0/0) | 0 |
| `00000077--7411859c54` | 21 | 124515 | 100671/23844/**0**/0 | 3730 | 2438 | [0, 4] | 122967 | 122967/0/0/0 | [0] | 710 (710/0/0/0) | 0 |
| `00000078--93548c06b3` | 16 | 92716 | 90326/2390/**0**/0 | 1452 | 2496 | [0, 4] | 91328 | 91328/0/0/0 | [0] | 702 (702/0/0/0) | 0 |
| `00000079--cb7538ffae` | 15 | 87472 | 42572/44900/**0**/0 | 786 | 1255 | [0, 4] | 86122 | 86122/0/0/0 | [0] | 723 (723/0/0/0) | 0 |
| `0000007d--83a5c80392` | 3 | 14116 | 14116/0/**0**/0 | 0 | 0 | [0] | 13171 | 13171/0/0/0 | [0] | 694 (694/0/0/0) | 0 |
| `0000007e--e5f2d1465f` | 14 | 80622 | 80098/524/**0**/0 | 648 | 1236 | [0, 4] | 79349 | 79349/0/0/0 | [0] | 692 (692/0/0/0) | 0 |
| `0000007f--2bb30756e7` | 14 | 83787 | 69093/14694/**0**/0 | 3018 | 1225 | [0, 4] | 82372 | 82372/0/0/0 | [0] | 806 (806/0/0/0) | 0 |
| `00000080--6c8b103892` | 2 | 10893 | 10893/0/**0**/0 | 0 | 0 | [0] | 9813 | 9813/0/0/0 | [0] | 860 (860/0/0/0) | 0 |
| `00000081--c7103d2cb4` | 3 | 18147 | 18147/0/**0**/0 | 0 | 0 | [0] | 17018 | 17018/0/0/0 | [0] | 812 (812/0/0/0) | 0 |
| `00000082--e30d55731b` | 2 | 12172 | 12172/0/**0**/0 | 0 | 0 | [0] | 11028 | 11028/0/0/0 | [0] | 871 (871/0/0/0) | 0 |
| `00000085--cad692c3d3` | 5 | 29999 | 14975/15024/**0**/0 | 2006 | 1770 | [0, 4] | 29844 | 29844/0/0/0 | [0] | 0 (0/0/0/0) | 0 |
| `00000095--6d7c6deef5` | 5 | 25703 | 25703/0/**0**/0 | 0 | 0 | [0] | 24495 | 24495/0/0/0 | [0] | 913 (913/0/0/0) | 0 |
| `00000096--57f5183b32` | 15 | 87776 | 63018/24758/**0**/0 | 1552 | 2560 | [0, 4] | 86354 | 86354/0/0/0 | [0] | 837 (837/0/0/0) | 0 |
| `00000097--489d7896b3` | 18 | 107625 | 93541/14084/**0**/0 | 6802 | 2560 | [0, 4] | 106121 | 106121/0/0/0 | [0] | 817 (817/0/0/0) | 0 |
| `0000009e--54bb0788af` | 11 | 64761 | 62991/1770/**0**/0 | 7558 | 2135 | [0, 4] | 63692 | 63692/0/0/0 | [0] | 775 (775/0/0/0) | 0 |
| `000000a4--bdd0c0aa4e` | 16 | 93789 | 70483/23306/**0**/0 | 368 | 589 | [0, 4] | 92316 | 92316/0/0/0 | [0] | 854 (854/0/0/0) | 0 |
| `000000a5--1419044ddf` | 11 | 66139 | 52889/13250/**0**/0 | 72 | 934 | [0, 4] | 64825 | 64825/0/0/0 | [0] | 817 (817/0/0/0) | 0 |
| `000000a6--78293a259e` | 26 | 155498 | 146110/9388/**0**/0 | 472 | 702 | [0, 4] | 153722 | 153722/0/0/0 | [0] | 881 (881/0/0/0) | 0 |

**Segments that could not be read whole (3 of 1,183; partial counts kept, none excluded):**
- `00000031--a680e9b2ac--10`: capnp "Message ends prematurely in first segment" after 94,122 events
- `0000006e--649c462a6e--7`: "Message ends prematurely" after 32,695 events
- `00000071--ac50da2a6a--3`: "Message ends prematurely in first segment" after 100,117 events

All three are truncated tails (upload cut). No route was unreadable; no segment yielded zero CAN events.

## 5. What this does and does not establish

**EVIDENCE**
1. Across 95 routes / 6.9 M frames (~19 h of camera 0xE4 at 100 Hz), the stock camera's byte-2 bits 3:2 ∈ {0, 1};
   **0 frames = 2**. The value that would satisfy V298's interlock never appeared on bus 2 in the cache. Round 1's
   12-route finding holds on the full cache.
2. The camera *does* actively steer on bus 2 (134,142 req = 1 frames, \|tq\| up to 2,560), so it is a live command
   source whenever its path to the EPS is closed. The interlock guards a real source, not a theoretical one.
3. openpilot's own 0xE4 has byte 2 & 0x7F = 0 on 100 % of 6,790,970 frames ⇒ with the fork as it is today,
   `gp-0x6803 = 0` and **V298's lane would never run**. The fork must set `SET_ME_X00` bits 3:2 = 2 (byte 2 = `0x88`
   with request, `0x08` without) on every frame, request-drop included, per the V298 flight prerequisites.
4. The only stock 0xE4 observed on the EPS-side bus (F-CAN, src 1), the ~8–10 s before openpilot TX on each route,
   had field 0, req 0, torque 0 on all 70,564 frames.

**BELIEF / not covered**
- The census is of **camera behaviour while openpilot is running** (plus the startup window). The relay-close hazard
  is the camera's command reaching the EPS *through the radar* when openpilot is not transmitting. Whether the radar
  passes byte 2 through unchanged or re-packs it is not observed at speed: the only radar-relayed sample (src 1) is
  the startup window at standstill, where the camera is idle. The firmware interlock does not depend on this (any
  value ≠ 2 blocks the lane), but "the radar never writes 2" is BELIEF from absence, not measured while moving.
- The camera's field could in principle take 2 in a state never visited in these drives (a fault, a camera software
  revision). 0 in 6.9 M bounds the per-frame rate below ~4.3e-7 (95 % one-sided, rule of three) *for the states
  visited*; it is not a proof about unvisited states. The field's meaning is unknown (it looks like a camera
  status/arm selector: 1 on 22.5 % of frames, almost never with req = 1, only 204 frames).
- src 193's meaning (blocked-TX flag) is BELIEF; it does not affect the census.
- The `shr` decode in §1 is a Python halfword decode of the V298 image, consistent with the Ghidra-derived 09-09
  trace, not an independent Ghidra pass.
