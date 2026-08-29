# STATE archive — superseded during the Path-2 iteration

A RECORD, NOT AN INSTRUCTION.

## 🛑🛑🛑 **`0xC4936` IDENTIFIED — A PWM HARDWARE-TIMING CAL. DO NOT TOUCH IT.**
`0xC4936` was the **only calibration operand anywhere in the FOC PI/SVPWM region** (0.25 cals/KB)
and the last open candidate for a symptom-B lever. **Identified, and it is a hard stop.**

### ✅ WHAT IT IS
Its single reader `0x6C486` sits inside **`FUN_0006c446`, a PERIPHERAL-INITIALISATION routine** that
writes the motor timer/PWM block. Region **byte-identical stock vs V122**, so this reads true for the
flying build:
```c
   _DAT_ffffcc58 = 0x1388;                                 // 5000   -- period-like
   _DAT_ffffcc5c = *(ushort *)(tp + 0x5936) * 2 + 0x50;    // cal(0xC4936)=250  ->  580
   _DAT_ffffcc6c = 0x50;   _DAT_ffffcc70 = 0x50;
   _DAT_ffffccb0 = _DAT_ffffccb4 = _DAT_ffffccb8 = 0x1428; // THREE IDENTICAL -> 3-phase compares
   _DAT_ff809220 = 0x801;  _DAT_ff809224 = 0x408;  _DAT_ff809228 = 0x515;
   _DAT_ff81c084 = 0x700;  _DAT_ff81c088 = 0x100;          // peripheral space
```
⇒ **[EVIDENCE] `0xC4936` is NOT a control-law gain. It is a PWM / timer HARDWARE CONFIGURATION
parameter**, written once at init into the inverter's timer block, as `2 × cal + 0x50`.
⊕ Three identical compare registers beside a period-like `5000` is the signature of a **3-phase PWM
generator** — consistent with the golden model's `TSG20` attribution.

### 🛑🛑🛑 WHY IT IS A HARD STOP — A FAILURE MODE WORSE THAN BRICKING
A `2×cal + offset` field in a 3-phase PWM timer block is most plausibly a **DEAD-TIME or phase
offset** register.
⇒ **Shortening inverter DEAD TIME causes SHOOT-THROUGH: both transistors of a leg conduct
simultaneously and the power stage is DESTROYED.**
⇒ **That is strictly worse than bricking the ECU.** This kit has bricked three times (V24, V27,
V48B) and recovered every time, because a bricked ECU is reflashable. **A destroyed inverter is
not.**
⇒ **[DECISION] `0xC4936` MUST NOT BE CHANGED, at any dose, for any reason short of a Honda service
document stating what the field is.** It is **virgin at 250 across all 155 images**, and it stays
that way.
⭐ **Recorded prominently because the trap is attractive**: a future session scanning for levers will
find *"a VIRGIN cal, single reader, inside the FOC region, never touched by 155 builds"* and read
that as opportunity. **It is the opposite.** Honda left the drive stage uncalibratable **on purpose**;
this one cell is not an oversight.

### ✅ SYMPTOM B — THE LAST CANDIDATE IS CLOSED, SO THE ANALYSIS IS COMPLETE
```
   1. engaged LKAS forward path       NO active switching nonlinearity (gate DORMANT, clamp INERT)
   2. cal(0xC6194)=3 in TASK 1, 1 kHz ~2 s full-scale => already smooth
   3. drive stage                     0.25 cals/KB => no calibration surface
   4. 0xC4936, the sole exception     PWM HARDWARE TIMING => must not be touched
```
⇒ **[CONCLUDED] symptom B is not reachable by any calibration edit this kit may safely make.**
The remaining explanation — the motor and inverter driven harder, ripple and commutation rising
with command amplitude, superlinear acoustics giving **m^1.74** — stands as **BELIEF**, and the only
cal that moves it is the **LKAS gain**, frozen in both directions.
⇒ **The falsifier stated last session is now down to ONE item**: a broadband source that is
engagement-conditional but **NOT** proportional to command amplitude. The forward path is traced end
to end and contains none.

### ⭐ A BYPRODUCT: THE PWM CARRIER CONFIGURATION IS NOW LOCATED
The golden model records **[OPEN] the PWM carrier frequency**. Its configuration is written in
`FUN_0006c446` — `_DAT_ffffcc58 = 5000` (period-like) with the 3-phase compares at `_DAT_ffffccb0/
b4/b8 = 0x1428`. **The register block is located; the absolute Hz still needs the clock tree** (the
kit records PCLK = 40 MHz, which would put a 5000-count period at 8 kHz edge-aligned or 4 kHz
centre-aligned — **arithmetic, NOT verified against the clock configuration**).
⇒ **pointer recorded for `eps_chain_delivery.py`; the [OPEN] is narrowed, not closed.**

## 🛑🛑🛑 **SYMPTOM B IS UNREACHABLE BY CALIBRATION — THE DRIVE STAGE HAS NO CALS**
The last unexamined place a broadband source could live is the FOC / current-loop / PWM stage.
Measured its **calibration density** against the control stage, on V122:
```
   region                                   size   tp-cals   gp-vars   cals/KB
   FOC: PI current regulator + SVPWM        4.0 KB      1        19       0.25   <- the drive stage
   FOC: TSG20 PWM emitter                   4.0 KB      8       116       2.00
   the gp-0x6b98 writers                    1.0 KB      5        11       5.00
   CONTROL: the ACTUAL arm    (0x38148)     4.0 KB     42        90      10.50
   CONTROL: the plant model   (0x3b8f6)     4.0 KB     49        97      12.25
   CONTROL: LKAS forward path (0x2a1ee)     4.0 KB     40        42      10.00
```
⇒ **[EVIDENCE] the motor drive stage is 40–49× LESS CALIBRATABLE than the control stage.** Honda
left the current loop and PWM generation essentially without calibration operands — its gains are
immediates or RAM-resident, not cells a `.rwd` can reach.
⊕ The **whole FOC PI/SVPWM region is byte-identical stock vs V122**, and the golden model already
records **[OPEN] the PWM carrier frequency** and that these ISRs *"run asynchronously and far faster
than this steering-task tick."*
⊕ **The single exception is `0xC4936` = 250** (1 reader, `0x6c486`) — VIRGIN ({250: 155} across 155 images). It is the **only**
calibration operand anywhere in the PI/SVPWM computation, and its role is unidentified.

### ✅ SYMPTOM B — THE ARGUMENT IS NOW CLOSED END TO END
```
   1. the engaged LKAS forward path has NO active switching nonlinearity
      command -> [deadband + sign gate: DORMANT engaged] -> x gain -> x polarity -> >>15
              -> clamp cal(0xC61B4) (INERT) -> gp-0x6b30
   2. the assist-arbitration slew limit cal(0xC6194)=3 runs in TASK 1 at 1 kHz
      => ~2 s full-scale => already smooth, not a broadband source
   3. the motor drive stage carries 0.25 cals/KB => no cal reaches it
```
⇒ **the gain-laddered broadband excess (1x -0.04 | 4x 0.84 | 6x 1.13 | 8x 2.24 dB) does not
originate in any cal-reachable element.**
⇒ **[BELIEF, and the honest reading] it is the motor and inverter being driven harder** — current
ripple and commutation noise rising with command amplitude, with a superlinear acoustic response
giving the measured **m^1.74**.
⇒ **🛑 SYMPTOM B IS IRREDUCIBLE BY CALIBRATION.** The only cal that changes it is the **LKAS
gain**, and that is frozen in **both** directions — raising it to 8x **doubles** the excess (fails the
operator's own stated condition) and lowering it is barred by
[[accord-4x-lkas-gain-is-the-frozen-variable]].

### ⭐ WHAT WOULD OVERTURN THIS — stated so it is falsifiable, not just asserted
1. **a broadband source that is engagement-conditional but NOT proportional to command amplitude.**
   None exists anywhere in the forward path; the path is now traced end to end.
2. **`0xC4936`** turning out to be a current-loop gain or carrier divisor. **1 reader, VIRGIN ({250: 155} across 155 images)** — worth
   identifying, and it is the *only* candidate left in the drive stage.
3. **an in-place instruction edit in the FOC** — the class that bricked V24, V27 and V48B, on the
   one region of this firmware with no calibration surface at all. **Not proposed, and should not
   be** without a reason far stronger than any now in hand.

### 🛑 THE HONEST TWO-SYMPTOM POSITION
```
   SYMPTOM A  the ~7.8 Hz ratchet   a MECHANICAL resonance, motor/rack side, Q 14-29.
                                    Firmware can change EXCITATION and LOOP PHASE, not the mode.
                                    => V153 (matched observer poles) is the best remaining lever.
   SYMPTOM B  the audible GRINDING  BROADBAND, above every CAN Nyquist, scales as gain^1.74.
                                    NO cal-reachable element produces it.
                                    => not fixable by calibration; only the frozen gain touches it.
```
⊕ **Neither symptom can be "100 % eliminated" by a calibration build**, and saying so is more
useful than shipping another candidate that cannot reach the mechanism. **Substantial reduction of
A remains available and untested on-car — that is what the queue is for.**

## 🛑🛑🛑 **SYMPTOM B IS UNREACHABLE BY CALIBRATION — THE DRIVE STAGE HAS NO CALS**
The last unexamined place a broadband source could live is the FOC / current-loop / PWM stage.
Measured its **calibration density** against the control stage, on V122:
```
   region                                   size   tp-cals   gp-vars   cals/KB
   FOC: PI current regulator + SVPWM        4.0 KB      1        19       0.25   <- the drive stage
   FOC: TSG20 PWM emitter                   4.0 KB      8       116       2.00
   the gp-0x6b98 writers                    1.0 KB      5        11       5.00
   CONTROL: the ACTUAL arm    (0x38148)     4.0 KB     42        90      10.50
   CONTROL: the plant model   (0x3b8f6)     4.0 KB     49        97      12.25
   CONTROL: LKAS forward path (0x2a1ee)     4.0 KB     40        42      10.00
```
⇒ **[EVIDENCE] the motor drive stage is 40–49× LESS CALIBRATABLE than the control stage.** Honda
left the current loop and PWM generation essentially without calibration operands — its gains are
immediates or RAM-resident, not cells a `.rwd` can reach.
⊕ The **whole FOC PI/SVPWM region is byte-identical stock vs V122**, and the golden model already
records **[OPEN] the PWM carrier frequency** and that these ISRs *"run asynchronously and far faster
than this steering-task tick."*
⊕ **The single exception is `0xC4936` = 250** (1 reader, `0x6c486`) — VIRGIN ({250: 155} across 155 images). It is the **only**
calibration operand anywhere in the PI/SVPWM computation, and its role is unidentified.

### ✅ SYMPTOM B — THE ARGUMENT IS NOW CLOSED END TO END
```
   1. the engaged LKAS forward path has NO active switching nonlinearity
      command -> [deadband + sign gate: DORMANT engaged] -> x gain -> x polarity -> >>15
              -> clamp cal(0xC61B4) (INERT) -> gp-0x6b30
   2. the assist-arbitration slew limit cal(0xC6194)=3 runs in TASK 1 at 1 kHz
      => ~2 s full-scale => already smooth, not a broadband source
   3. the motor drive stage carries 0.25 cals/KB => no cal reaches it
```
⇒ **the gain-laddered broadband excess (1x -0.04 | 4x 0.84 | 6x 1.13 | 8x 2.24 dB) does not
originate in any cal-reachable element.**
⇒ **[BELIEF, and the honest reading] it is the motor and inverter being driven harder** — current
ripple and commutation noise rising with command amplitude, with a superlinear acoustic response
giving the measured **m^1.74**.
⇒ **🛑 SYMPTOM B IS IRREDUCIBLE BY CALIBRATION.** The only cal that changes it is the **LKAS
gain**, and that is frozen in **both** directions — raising it to 8x **doubles** the excess (fails the
operator's own stated condition) and lowering it is barred by
[[accord-4x-lkas-gain-is-the-frozen-variable]].

### ⭐ WHAT WOULD OVERTURN THIS — stated so it is falsifiable, not just asserted
1. **a broadband source that is engagement-conditional but NOT proportional to command amplitude.**
   None exists anywhere in the forward path; the path is now traced end to end.
2. **`0xC4936`** turning out to be a current-loop gain or carrier divisor. **1 reader, VIRGIN ({250: 155} across 155 images)** — worth
   identifying, and it is the *only* candidate left in the drive stage.
3. **an in-place instruction edit in the FOC** — the class that bricked V24, V27 and V48B, on the
   one region of this firmware with no calibration surface at all. **Not proposed, and should not
   be** without a reason far stronger than any now in hand.

### 🛑 THE HONEST TWO-SYMPTOM POSITION
```
   SYMPTOM A  the ~7.8 Hz ratchet   a MECHANICAL resonance, motor/rack side, Q 14-29.
                                    Firmware can change EXCITATION and LOOP PHASE, not the mode.
                                    => V153 (matched observer poles) is the best remaining lever.
   SYMPTOM B  the audible GRINDING  BROADBAND, above every CAN Nyquist, scales as gain^1.74.
                                    NO cal-reachable element produces it.
                                    => not fixable by calibration; only the frozen gain touches it.
```
⊕ **Neither symptom can be "100 % eliminated" by a calibration build**, and saying so is more
useful than shipping another candidate that cannot reach the mechanism. **Substantial reduction of
A remains available and untested on-car — that is what the queue is for.**

## 🛑🛑🛑 **SYMPTOM B IS UNREACHABLE BY CALIBRATION — THE DRIVE STAGE HAS NO CALS**
The last unexamined place a broadband source could live is the FOC / current-loop / PWM stage.
Measured its **calibration density** against the control stage, on V122:
```
   region                                   size   tp-cals   gp-vars   cals/KB
   FOC: PI current regulator + SVPWM        4.0 KB      1        19       0.25   <- the drive stage
   FOC: TSG20 PWM emitter                   4.0 KB      8       116       2.00
   the gp-0x6b98 writers                    1.0 KB      5        11       5.00
   CONTROL: the ACTUAL arm    (0x38148)     4.0 KB     42        90      10.50
   CONTROL: the plant model   (0x3b8f6)     4.0 KB     49        97      12.25
   CONTROL: LKAS forward path (0x2a1ee)     4.0 KB     40        42      10.00
```
⇒ **[EVIDENCE] the motor drive stage is 40–49× LESS CALIBRATABLE than the control stage.** Honda
left the current loop and PWM generation essentially without calibration operands — its gains are
immediates or RAM-resident, not cells a `.rwd` can reach.
⊕ The **whole FOC PI/SVPWM region is byte-identical stock vs V122**, and the golden model already
records **[OPEN] the PWM carrier frequency** and that these ISRs *"run asynchronously and far faster
than this steering-task tick."*
⊕ **The single exception is `0xC4936` = 250** (1 reader, `0x6c486`) — VIRGIN ({250: 155} across 155 images). It is the **only**
calibration operand anywhere in the PI/SVPWM computation, and its role is unidentified.

### ✅ SYMPTOM B — THE ARGUMENT IS NOW CLOSED END TO END
```
   1. the engaged LKAS forward path has NO active switching nonlinearity
      command -> [deadband + sign gate: DORMANT engaged] -> x gain -> x polarity -> >>15
              -> clamp cal(0xC61B4) (INERT) -> gp-0x6b30
   2. the assist-arbitration slew limit cal(0xC6194)=3 runs in TASK 1 at 1 kHz
      => ~2 s full-scale => already smooth, not a broadband source
   3. the motor drive stage carries 0.25 cals/KB => no cal reaches it
```
⇒ **the gain-laddered broadband excess (1x -0.04 | 4x 0.84 | 6x 1.13 | 8x 2.24 dB) does not
originate in any cal-reachable element.**
⇒ **[BELIEF, and the honest reading] it is the motor and inverter being driven harder** — current
ripple and commutation noise rising with command amplitude, with a superlinear acoustic response
giving the measured **m^1.74**.
⇒ **🛑 SYMPTOM B IS IRREDUCIBLE BY CALIBRATION.** The only cal that changes it is the **LKAS
gain**, and that is frozen in **both** directions — raising it to 8x **doubles** the excess (fails the
operator's own stated condition) and lowering it is barred by
[[accord-4x-lkas-gain-is-the-frozen-variable]].

### ⭐ WHAT WOULD OVERTURN THIS — stated so it is falsifiable, not just asserted
1. **a broadband source that is engagement-conditional but NOT proportional to command amplitude.**
   None exists anywhere in the forward path; the path is now traced end to end.
2. **`0xC4936`** turning out to be a current-loop gain or carrier divisor. **1 reader, VIRGIN ({250: 155} across 155 images)** — worth
   identifying, and it is the *only* candidate left in the drive stage.
3. **an in-place instruction edit in the FOC** — the class that bricked V24, V27 and V48B, on the
   one region of this firmware with no calibration surface at all. **Not proposed, and should not
   be** without a reason far stronger than any now in hand.

### 🛑 THE HONEST TWO-SYMPTOM POSITION
```
   SYMPTOM A  the ~7.8 Hz ratchet   a MECHANICAL resonance, motor/rack side, Q 14-29.
                                    Firmware can change EXCITATION and LOOP PHASE, not the mode.
                                    => V153 (matched observer poles) is the best remaining lever.
   SYMPTOM B  the audible GRINDING  BROADBAND, above every CAN Nyquist, scales as gain^1.74.
                                    NO cal-reachable element produces it.
                                    => not fixable by calibration; only the frozen gain touches it.
```
⊕ **Neither symptom can be "100 % eliminated" by a calibration build**, and saying so is more
useful than shipping another candidate that cannot reach the mechanism. **Substantial reduction of
A remains available and untested on-car — that is what the queue is for.**

## 🛑🛑🛑 **SYMPTOM B IS UNREACHABLE BY CALIBRATION — THE DRIVE STAGE HAS NO CALS**
The last unexamined place a broadband source could live is the FOC / current-loop / PWM stage.
Measured its **calibration density** against the control stage, on V122:
```
   region                                   size   tp-cals   gp-vars   cals/KB
   FOC: PI current regulator + SVPWM        4.0 KB      1        19       0.25   <- the drive stage
   FOC: TSG20 PWM emitter                   4.0 KB      8       116       2.00
   the gp-0x6b98 writers                    1.0 KB      5        11       5.00
   CONTROL: the ACTUAL arm    (0x38148)     4.0 KB     42        90      10.50
   CONTROL: the plant model   (0x3b8f6)     4.0 KB     49        97      12.25
   CONTROL: LKAS forward path (0x2a1ee)     4.0 KB     40        42      10.00
```
⇒ **[EVIDENCE] the motor drive stage is 40–49× LESS CALIBRATABLE than the control stage.** Honda
left the current loop and PWM generation essentially without calibration operands — its gains are
immediates or RAM-resident, not cells a `.rwd` can reach.
⊕ The **whole FOC PI/SVPWM region is byte-identical stock vs V122**, and the golden model already
records **[OPEN] the PWM carrier frequency** and that these ISRs *"run asynchronously and far faster
than this steering-task tick."*
⊕ **The single exception is `0xC4936` = 250** (1 reader, `0x6c486`) — VIRGIN ({250: 155} across 155 images). It is the **only**
calibration operand anywhere in the PI/SVPWM computation, and its role is unidentified.

### ✅ SYMPTOM B — THE ARGUMENT IS NOW CLOSED END TO END
```
   1. the engaged LKAS forward path has NO active switching nonlinearity
      command -> [deadband + sign gate: DORMANT engaged] -> x gain -> x polarity -> >>15
              -> clamp cal(0xC61B4) (INERT) -> gp-0x6b30
   2. the assist-arbitration slew limit cal(0xC6194)=3 runs in TASK 1 at 1 kHz
      => ~2 s full-scale => already smooth, not a broadband source
   3. the motor drive stage carries 0.25 cals/KB => no cal reaches it
```
⇒ **the gain-laddered broadband excess (1x -0.04 | 4x 0.84 | 6x 1.13 | 8x 2.24 dB) does not
originate in any cal-reachable element.**
⇒ **[BELIEF, and the honest reading] it is the motor and inverter being driven harder** — current
ripple and commutation noise rising with command amplitude, with a superlinear acoustic response
giving the measured **m^1.74**.
⇒ **🛑 SYMPTOM B IS IRREDUCIBLE BY CALIBRATION.** The only cal that changes it is the **LKAS
gain**, and that is frozen in **both** directions — raising it to 8x **doubles** the excess (fails the
operator's own stated condition) and lowering it is barred by
[[accord-4x-lkas-gain-is-the-frozen-variable]].

### ⭐ WHAT WOULD OVERTURN THIS — stated so it is falsifiable, not just asserted
1. **a broadband source that is engagement-conditional but NOT proportional to command amplitude.**
   None exists anywhere in the forward path; the path is now traced end to end.
2. **`0xC4936`** turning out to be a current-loop gain or carrier divisor. **1 reader, VIRGIN ({250: 155} across 155 images)** — worth
   identifying, and it is the *only* candidate left in the drive stage.
3. **an in-place instruction edit in the FOC** — the class that bricked V24, V27 and V48B, on the
   one region of this firmware with no calibration surface at all. **Not proposed, and should not
   be** without a reason far stronger than any now in hand.

### 🛑 THE HONEST TWO-SYMPTOM POSITION
```
   SYMPTOM A  the ~7.8 Hz ratchet   a MECHANICAL resonance, motor/rack side, Q 14-29.
                                    Firmware can change EXCITATION and LOOP PHASE, not the mode.
                                    => V153 (matched observer poles) is the best remaining lever.
   SYMPTOM B  the audible GRINDING  BROADBAND, above every CAN Nyquist, scales as gain^1.74.
                                    NO cal-reachable element produces it.
                                    => not fixable by calibration; only the frozen gain touches it.
```
⊕ **Neither symptom can be "100 % eliminated" by a calibration build**, and saying so is more
useful than shipping another candidate that cannot reach the mechanism. **Substantial reduction of
A remains available and untested on-car — that is what the queue is for.**

