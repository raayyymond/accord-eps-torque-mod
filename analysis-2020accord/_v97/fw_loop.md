# The 6–9 Hz loop, drawn from `code.bin`

fw-loop, 2026-08-12. Study/analysis only. Model: `loop_phase_model.py` (this directory).
`gp = 0xFEDF8000`, `tp = 0x000BF000`. All cals read little-endian from
`../accord-firmwares/analysis-2020accord/stock_fw_dump/code.bin` at model runtime.

⚠ Ghidra's *current* program this session was `_v96_..._plain_image.bin` with `function_count = 0`.
Every `mcp__ghidra__*` call below passed `program="code.bin"` explicitly.

---

## 1. The loop

The 7.8 Hz loop is a **driver-torque tracking servo**, not the base-assist loop.

```
gp-0x4f60 (torsion-bar torque)
  │
  ├─ PATH 2 (reference shaping) ────────────────────────────────────────────┐
  │    FUN_00036682 @0x36682   hysteresis ±0xC619C(1024) on                  │
  │      gp-0x6b48 + pol·(tq·0xC646C(891)>>15) − gp-0x6b46,                  │
  │      then clamp ±512, then IIR 0xC63D2 = 6/1024  → gp-0x6b46             │
  │    FUN_00038148 @0x38148  (1 kHz; sole caller FUN_0002214a jarl @0x22676)│
  │      sum6 = Σ w·lane,  w = 0xC63A8/AA/A6/A4/A0/A2 = 1024 each            │
  │             lanes  6b4e, 6b4c, 6b26, 6b46, 6bd0, 6bbe                    │
  │      target   = sum6·pol·0xC6468(2639)>>10 ·16          (= ×41.234)      │
  │      gp-0x374c += (target − gp-0x374c)·0xC63AC(102)>>10                  │
  │      iVar6 = gp-0x6bfe + gate(gp-0x6bfa,20000) − (gp-0x374c>>4)          │
  │      gp-0x6b70 = sign(iVar6)·RAM_LERP(|iVar6|·0xC63AE>>10), ±0xC6200     │
  │    FUN_00037fe6 @0x37fe6   st.h gp-0x6ad6 @0x38142                       │
  │      gp-0x6ad6 = clamp(−gp-0x6b4a + Σ(flagged lanes) + gp-0x6b70, ±25600)│
  │      flags 0xC64AD..0xC64B3 are BYTES, all = 1  (gp-0x6b70's is 0xC64B0) │
  │                                          = THE PID REFERENCE  ───────────┤
  ▼                                                                          │
FUN_0003a382 @0x3a382  PID                                                   │
  e = clamp( gp-0x4f60 − clamp(gp-0x6ad6, ±8192), ±10240 )   ◀───────────────┘
  P  Kp = 0xC6B26[0] = 256/1024,  ×32 @0x3a7f6,  IIR 0xC6450 = 1024 (bypass)
  I  Ki = 0xC6B12    =  98/1024,  NO ×32          (the asymmetry)
  D  Kd = 0xC6AE6    = 2048/1024, ×32 @0x3a868,  IIR 0xC644A = 1024 (bypass)
  out = ((P+I+D) >>5 @0x3a880) · 0xC67B8(1024)>>10 · pol,  clamp ±AUTH → gp-0x6ad4
  AUTH = min( LERP_{gp-0x6bda}(0xC67A2/A8), LERP_{gp-0x6a5e}(0xC67C2/C8) or 0xC61FE ,
              5120 ) · (gp-0x6765==3) · LERP(gp-0x6966)/32768
  ▼
FUN_0003aa2c @0x3aa2c  aggregator, ALL UNITY:
  gp-0x6b94 = clamp(6ade + 6b4c + 6ad4 + 6b62 + 6b26 + 6bbe + 6bd0 + 6b86
                    + r24 + r26 + FUN_00036682()→6b46, ±10240)
  ▼ FUN_0004503c governor (0xC6206 = 512 ct/tick) → gp-0x6ace
  ▼ FUN_000456a4 comp-add → gp-0x6acc
  ▼ FUN_00042af8 shaper (0xC64C8 = 0 ⇒ pass-through) → gp-0x6b08 @0x43206 → gp-0x6b98
  ▼ FUN_000757a2 → FOC (4 kHz) → motor → worm → rack → column → torsion bar → gp-0x4f60
```

### Task-1 execution order (1 kHz), from `search_instructions mnemonic=jarl function=FUN_0002214a`

| addr | callee | consequence |
|---|---|---|
| `0x22676` | `FUN_00038148` | Path 2 — reads the **previous** tick's `gp-0x6b26`/`gp-0x6b46` |
| `0x22696` | `FUN_00037fe6` | → `gp-0x6ad6` |
| `0x226a0` | `FUN_0003a382` | PID → `gp-0x6ad4` |
| `0x228cc` | `FUN_00036c12` | → `gp-0x6b26` |
| `0x2291e` | `FUN_0003aa2c` | aggregator; calls `FUN_00036682` → `gp-0x6b46` |
| `0x2293a` | `FUN_0004503c` | governor |
| `0x229ce` | `FUN_00042af8` | shaper |

⇒ **Path 1 sees the same-tick lanes; Path 2 sees them one tick (−2.8° @7.79 Hz) late.**

### Live / dead in engaged + 6–20 km/h + hands-on override

LIVE: PID lane `gp-0x6ad4`; `gp-0x6b26` (both paths); `gp-0x6bbe`, `gp-0x6bd0`, `gp-0x6b46`;
r24/r26 (`gp-0x67ac` resolves 0 ⇒ full-sum branch); `FUN_00036682` hysteresis.

DEAD: base-assist damper FactorC×FactorE (0 on 100 % of the micro regime) — 🛑 **CORRECTED
2026-08-13 (later), record-repair pass: this is TRUE for V88/Honda's stock FactorC/FactorE only.**
Five other builds (V74/75/76/78/79) plus V80 opened both dead zones simultaneously and reached the
micro regime; three flew (V75/V76/V80). See `memory/accord-base-assist-damper-cannot-reach-the-micro-regime.md`.
`gp-0x6b62` return-centre (measured 0.0000 / 75,227 engaged frames); `gp-0x6966` soft-EME collapse
(held 0); governor slew (cannot bind below ≈10,400 ct of amplitude at 7.8 Hz).

---

## 2. Phase budget at 6 / 7.79 / 9 Hz, fs = 1000 Hz

| element | 6 Hz | 7.79 Hz | 9 Hz |
|---|---|---|---|
| PID `K(z)` | 0.2529 ∠−0.89° | 0.2565 ∠**+8.24°** | 0.2617 ∠+13.29° |
| aggregator / governor / shaper | ∠0° | ∠0° | ∠0° |
| ZOH + FOC ≈ 1 tick | ∠−2.16° | ∠−2.80° | ∠−3.24° |
| **fast-loop total** | 0.253 ∠**−3.05°** | 0.257 ∠**+5.43°** | 0.262 ∠**+10.05°** |
| `0xC63AC` = 102 Path-2 pole | 0.941 ∠−18.70° | 0.906 ∠−23.63° | 0.880 ∠−26.73° |
| `0xC63D2` = 6 → `gp-0x6b46` | 0.154 ∠−80.06° | 0.119 ∠−81.75° | 0.103 ∠−82.45° |
| Path-2 total (torque lane) | 0.145 ∠−100.92° | 0.108 ∠−108.19° | 0.091 ∠−112.42° |
| Path-2 total (`gp-0x6b26`) | 0.941 ∠−20.86° | 0.906 ∠−26.43° | 0.880 ∠−29.97° |

PID corners: `fi = 1.904 Hz`, `fd = 19.894 Hz` ⇒ **6–9 Hz sits inside the flat window**.

🛑 **Corrects STATE.md §A6b**: the PID **leads** by +8.2° at 7.79 Hz; it does not lag −11…−27°.

🛑 **CONDITIONED 2026-08-13 (later), record-repair pass — the whole table above is the UNSATURATED
gain/phase.** `tracer-6ad6` confirmed the `clamp(gp-0x6ad6, ±8192)` already drawn at line 36 of this
document's own loop diagram is a REAL, load-bearing clamp inside `FUN_0003a382` (all three of P/I/D
driven from the clamped difference; crux verified by the team lead directly in Ghidra). **When
`|gp-0x6ad6| ≥ 8192`, every gain in this table is 0, not the tabulated value.** Clamp duty is
UNMEASURED. Do not quote this table's gains without that condition.

---

## 3. Q3 — loop pole or mechanical mode?

**Verdict: the FREQUENCY is a plant resonance; the DAMPING is firmware.**

The firmware's total phase in the fast loop at 6–9 Hz is **−3° to +10°**. A phase-crossover pole
needs ≈180°. The only large firmware lag (Path 2, −108°) sits on a lane attenuated **9.3×**.
Meanwhile the kit has measured `Re(Z) < 0` at 6–9 Hz on three drives and a 7.2× engaged/manual
contrast — the firmware *is* pumping the mode; it just is not setting its frequency.

**Pre-registered falsifiable prediction:** `0xC6AE6` 2048 → 4096 adds **+19.5°** of loop lead at
7.79 Hz. Loop-phase slope from the model is ≈ +4.73 °/Hz, so a genuine loop pole would move
**≈ +4 Hz** (to ~11.9 Hz). **If the 7.79 Hz peak moves by < 0.3 Hz, it is a plant mode.**

---

## 4. Q4/Q5 — damping terms and leverage

See the parent report. Ranking at 7.79 Hz (from `loop_phase_model.py` section E):

| cal | stock | Δφ @7.79 | Δgain | lineage |
|---|---|---|---|---|
| `0xC6AE6` Kd | 2048 | →4096 **+19.5°** / →1024 −11.0° | 1.13× / 0.99× | **VIRGIN** (v43/v49 assert only) |
| `0xC63AC` Path-2 pole | 102 | →512 **+20.8°** / →51 −18.8° | 1.10× / 0.80× | **VIRGIN** (v79–v96 assert only) |
| `0xC6B12` Ki | 98 | →0 +13.0° / →392 −37.8° | 1.06× / 1.16× | **VIRGIN** |
| `0xC63D2` 36682 pole | 6 | →102 +58.1° | **7.60×** | **VIRGIN** (v52c–v64 assert only) |
| `0xC6B26` Kp | 256 | →128 +7.7° | 0.52× | **VIRGIN** |
| `0xC67C8` PID auth vs speed | 0,1024,1024 | 0° | sets the relay amplitude | **VIRGIN, 0 build scripts** |
