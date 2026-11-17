# Lens B report: V300-A340 REV 4 — verdict PASS_WITH_DEFECTS (no DO_NOT_FLASH condition found)

Method: Python byte diffs/scans on REV4, REV3, stock images + Ghidra on A340_stock.bin. REV4 was NOT imported into Ghidra (shared-project mutation); 8 edited sites hand-decoded from bytes. Cave body NOT examined by this lens. The REV1 disasm file was not found on disk and was not used. Scripts: diff1.py a1.py a2.py a3.py a4.py gpscan.py tpscan.py (this folder).

## Attack 6 — REV4 vs REV3: PASS (EVIDENCE: full-image diff)
Differences are only: 0x1310D 0x43->0x44 ('C'->'D'); 0xC40D4 14->22; rows 0xD7A5C/0xD7A6C reverted to stock; CRC trailers 0xC4FFC and 0xD7FFC. No code byte differs.
F181 at 0x13100 has one reader, the UDS handler FUN_00050414 (copies 14 bytes to the reply; twin FUN_000503f0 for 0x1310E). Whole-image LE32 scan finds only those. No comparison against 0x14117, so 'D' vs 'C' is behaviourally identical.

## Attacks 1, 2, 5 — key/mode tables: PASS (EVIDENCE)
- Row selector FUN_0005904a matches the 5-byte coded key against rows 0..28 of 0xCD000 (stride 0x24). Unmatched key returns row 0 ('00000': modes [0,1,2,3], variant 0). Rows 29+ are 0xFF fill, unreachable.
- Mode column (+0x12..+0x15 -> gp+0x63fd): range 0..29, all < 34.
- Gain variant selector gp-0x6714 = key-row byte +0x1A; sole writer FUN_00043214 (0x4322C). Values 0..11 only, so no key reaches pointer-table entries 12..15 (which alias other-kind records).
- FUN_0002A740 reads all 3 speed pointer tables for Kp/Kd/Ki. All 108 records read from the REV4 image are edited (Kp 7, Kd 48, Ki 20); every X knot identical to stock.
- Dir-2 fades 0xC6C00/0xC6C10: 36 records per family all identical, and the u8 tables equal them.
- DampAxis: all 34 records and the 0xCBE40 pointers stock-identical; 0xC40D4 = 22. Zero differing bytes in 0xC7000-0xE4000, 0xE6000-end, 0xC0000-0xC4C00, 0xCE000-0xDA000.

## Attack 3 — request-off equivalence: PASS (EVIDENCE steady state; BELIEF on one point)
- Gate decodes as documented: 0x29E68 `cmp 1,r10` + `cmovne r0,r25,r8` (r10 = request gp-0x67cb, r14 = ramp gp-0x6978); 0x29E6E `be 0x29E74` -> `jr 0x2A596`. PID runs only if ramp != 0 AND request == 1 AND r25 != 0.
- Hook 0x2A340 is reachable only on the PID path (Ghidra xrefs: none into 0x2A340/0x2A348; 0x2A334 only from 0x2A2F2/0x2A30A). The skip path lands past it.
- Skip path 0x2A596 zeroes PID output (r13) and I state (gp-0x6da0), sets the sentinel. Output-lag state decays x(992/1024) per tick (about 32 ms time constant).
- Final lane term = ((r12 + r15) * polarity * 5328) >> 15, clamped to +-3072. polarity gp-0x6718 is a +-1 constant (NOT the request bit; my first reading was wrong). r15 = lag output * ramp >> 15 = 0 in manual. r12 is the stock haptic-pulse term; it is non-zero only via the pulse generator gated on gp-0x67cf == 1. gp-0x67cf has no writer (4-byte scan with positive control, Ghidra operand search, pointer-materialisation scan all agree) and boots 0 (flash 0x87991 in the .data copy 0x87320 -> 0xFEDF11C0). So r12 is 0. BELIEF residual: a register-indirect writer is not excluded. If r12 could be non-zero the x6 gain and 3072 clamp would amplify it, so this is the one point that would change the verdict.
- Filter state gp-0x3c90 / gp-0x3c8c, lag state gp-0x3c9c and I state gp-0x6da0 are read/written only inside FUN_00029230, its uncalled twin, and (I state) the cave. The fb filter fed with the angle (E1) therefore does not reach anything outside the gated PID path.
- Worst-case engaged->manual transient: request drops while the sum clamp (0xC61CE = 15360) is saturated. Steady lag output about 15210; times ramp (full) times 5328/32768 = about 2470 counts (below the 3072 clamp). Then it decays by 992/1024 per tick: below 5% in about 95 ms. Stock peaks at about 412 counts (888/32768 x 15210; cap 512), but stock keeps the PID live through the ramp-out. The tail is bounded by the engaged authority; it is not larger than what was being delivered. Identical to REV3.
- FUN_0002BFA4 (caller: FUN_00022240 only): clamps gp-0x6b0c to +-0xC61C0 and runs a mode state machine whose output gates delivery (lane value delivered only when gp-0x676a in {2,3}). The gate can only reduce output. Quirk: it seeds its mode char with the LOW BYTE of 0xC61C0; 3072 (0x0C00) and 512 (0x0200) both have low byte 0, so no change (fragile coupling).
- FUN_0002C0FC: only its caller (FUN_00022240) was checked. Its readers of 0xC61C0 (0x2C138) were NOT traced to outputs. Open.

## Attack 4 — EME ladder: PASS with defect D1
- The corridor/boost-floor cells (0xC679E/A0/AA/AC, 0xC67B8/BA/BC) are Y values of three LERP tables read only by FUN_0004367A and FUN_000449C6. In FUN_0004367A they set bounds for an integrator (gp-0x34cc) that drives a trip state and DTC 0x2A; the bounds are published only to gp-0x6ad0, 0x6ac6, 0x6ad6, and every reader of those cells lies inside those two functions (scan, positive-controlled). No clamp of the delivered command is visible, so the raised corridor/floor cannot change delivered manual assist while untripped. EVIDENCE: decompile + reader census.
- BELIEF/open: what consumes the trip flags (gp-0x674d, gp-0x34c4, FUN_00016ed0/FUN_0001cc30) was not traced; this only matters on a trip, which REV4 makes harder, not easier.
- Lockstep: int == f32*1024 exactly for all 7 pairs in REV4 (+-5120, 5120, 5120, 5120 <-> +-5.0, 5.0 x3), tolerance in the monitor is 5 counts.
- DTC plausibility thresholds that the x6 lane could cross: NOT verified.

## Defects
- D1 (MEDIUM, safety, loosening not torque-adding): A7 is not in the port spec ("carried because A160 V300 keeps A7"). It widens the soft-EME corridor from +-1024 to +-5120 and sets the floor to a constant 5120, so a manual-assist excess up to 5120 counts no longer accumulates toward the trip. Needs an explicit operator ruling.
- D2 (LOW-MEDIUM): takeover tail of up to about 2470 counts decaying over about 95 ms versus stock's about 412-count ramp-out. Bounded by engaged authority; same as REV3.
- D3 (LOW): STEER_STATUS/DTC debounce cells 0xC61D0/D2/D4 = 0xFFFF and 0xC6504..07 = 0xFF make driver-override status 4 unreachable; DTC 0x49 masked via 0xC6D28 (0xFF, only the two edited reads reference it). Inherited from REV3, not a REV4 delta.
- D4 (LOW, process): the 0xC61C0 low-byte coupling above; the gp-0x67cf residual (register-indirect writers); FUN_0002C0FC untraced; cave and DTC plausibility not covered by this lens.
