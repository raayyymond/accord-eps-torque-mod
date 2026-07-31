---
name: accord-pclk-40mhz-and-ostm0-is-500hz
description: PCLK is 40 MHz (two independent derivations), so OSTM0 runs at 500 Hz not 1 kHz - and OSTM0 is NOT the control tick; the kit's 1 kHz conclusion is right but its derivation was wrong on both counts
metadata:
  type: reference
---

## PCLK = 40.000 MHz — two independent in-image derivations

**(a) CAN bit timing.** The bus is a known 500 kbps.
- `0x0094c mov 0x4,r1` / `0x0094e st.b r1,0x8[r2]` (r2=0xFF480000) -> FCN0GMCSPRE = 4.
  Manual table (PDF p.1260): `0100B` -> fCANMOD = fCAN/5.
- `0x00966 st.b` <- halfword at ROM 0x00FD8 = `01 00` -> FCN0CMBRPRS = 1 -> fTQ = fCANMOD/2.
- `0x0096e st.h` <- halfword at ROM 0x00FDA = `0a 03` -> FCN0CMBTCTL = 0x030A ->
  TSEG1=4, TSEG2=3, SJW=1, **DBT = 8 TQ, sample point 62.5%** — an exact row of Table 20-19.
- 500000 x 8 x 2 x 5 = **40.000 MHz**. Figure 7-1 puts CAN on PCLK, so fCAN = PCLK.

**(b) CLMA1 clock monitor + option byte.**
- `0x5c8da st.h 0x53 -> CLMA1CMPH`, `0x5c8e2 st.h 0x4D -> CLMA1CMPL` -> N band 77..83, **centre 80**.
- Manual Table 7-12: CLMA1 TMON = internal system clock, TSMP = **Main OSC**, which is fixed at
  16 MHz for the uPD70F3508. N = 16 x f_TMON / f_TSMP -> HEAPCLK = 80.00 MHz (+/-3.75%).
- Option byte for this part: HEAPCLK 80 MHz requires FOP[2:0]=011, and HEAPCLK/4 is legal **only**
  at 160 MHz -> PCLK = HEAPCLK/2 = **40 MHz**. 40 MHz is in the legal set {24,32,40,48,64,80}.

## Therefore OSTM0 = 500.00 Hz, not 1 kHz
`0x14c8e mov 0x1387f,r13` / `0x14c94 st.w -> OSTM0CMP` = 79999; `0x14c8a st.b 1 -> OSTM0CTL`
(MD1=0 interval mode, MD0=1); `0x14c9c st.h 0 -> IC0CKSEL0 @0xFF83F000` -> IC0TMEN0=0 =
"PCLK fixed high", i.e. **counts PCLK ungated**. Period = 80000/40 MHz = **2.000 ms = 500.0 Hz**.
`0x14ca4 clr1 0x4,0x6405[r18]` unmasks IMR2 bit 12 = **EIINT44 = OSTM0** (ICOSTM0 at INTC
offset 0x58 -> ch 44).

## The correction that matters
The kit inferred "1 kHz control task = OSTM0 80000 counts @ 80 MHz". **Both halves are wrong**:
PCLK is 40 MHz, and OSTM0 is not the control tick at all — the tick is TAUJ1I2, see
[[accord-rtos-task-table-and-rate-scheduler]]. OSTM0 is the RTOS system-time source (started by the
kernel leaf 0x861fe) and its EIIC 0x2c0 is absent from the EI trampoline's dispatch list.

**The 1 kHz conclusion itself still stands, on the on-car anchors, not on OSTM0**: the
STEER_STATUS=4 dwell cal 0xC64DF = 100 measured 100.00 ms requires a 1.000 ms decrement period.
A 500 Hz base can produce nothing faster than 2 ms, so OSTM0 is arithmetically excluded as the
source. The measured 100 Hz CAN TX tick is then the scheduler's **/10** group off a 1 kHz base.
TAUJ1's own period could not be found in the image — no TAUJ1 configuration write was located,
so 1 kHz rests on the two on-car measurements, not on a register read. [OPEN]
