# EPS System Description 3455 — Driver Assist Pipeline Extraction

**Source:** "EPS System Description 3455" — Honda service manual document, printed/archived 2020-11-16, 5 pages.  
**Vehicle:** 2020 Honda Accord (61TRWD family, implied by URL path).  
**Scope:** Driver steering-assist control architecture only. Document contains no LKAS or lane-keep references; that is expected — LKAS torque sums into this pipeline externally.  
**Extraction date:** 2026-05-25.

---

## Ordered Control Pipeline (as documented)

### Stage 1 — Base Current

- **Section heading:** "Base Current" (page 1)
- **Inputs:** Steering torque, vehicle speed
- **Output:** Base current (fundamental motor drive value)
- **Description:** "The base current is a basic current value to drive the motor and is calculated using the steering torque and the vehicle speed."
- **Speed dependence:** Implicitly captured here — document overview states: "Low vehicle speeds: High power assist (for easy handling) / High speed driving: Low power assist (for stable driving) / Low speed to high speed driving: Smoothly changes from high assist to low assist." The vehicle-speed input to base current is the mechanism for this speed-dependent assist scaling.
- **Named gains/tables/maps:** None named explicitly in text. No numeric values given.
- **Clamps/limits:** None stated at this stage.

---

### Stage 2 — Inertia Compensation

- **Section heading:** "Inertia Compensation" (page 1)
- **Inputs:** Steering torque, vehicle speed, motor speed
- **Output:** Inertia compensation current (additive to base current)
- **Description:** "The torque of the EPS motor tends to be lower as the vehicle begins to move and higher as it decreases in speed due to the inertia of the rotating body. To reduce the impact of the inertia, the inertia compensation increases the base current in acceleration and decreases in deceleration."
- **Direction of correction:** Additive on acceleration, subtractive on deceleration.
- **Named gains/tables/maps:** None named explicitly.
- **Clamps/limits:** None stated.

---

### Stage 3 — Damping Compensation

- **Section heading:** "Damping Compensation" (page 1)
- **Inputs:** Steering torque, vehicle speed, motor speed
- **Output:** Damping compensation current (applied to motor current control)
- **Description:** "The steering wheel receives vibration from the road surface during braking or cornering. The damping compensation reduces the vibration of the steering wheel by applying a damping effect through the motor current control."
- **Named gains/tables/maps:** None named explicitly.
- **Clamps/limits:** None stated.

---

### Stage 4 — Target Current Formation

- **Section heading:** "Target Current" (page 1)
- **Inputs:** Base current (Stage 1), inertia compensation (Stage 2), damping compensation (Stage 3), steering torque direction
- **Output:** Target current (setpoint for feedback control loop)
- **Description:** "The target current is a value necessary to perform feedback control of the motor and is determined by applying inertia and damping compensation to the base current and adding steering torque direction."
- **Formation:** target_current = base_current ± inertia_compensation ± damping_compensation, signed by steering torque direction.
- **Named gains/tables/maps:** None named explicitly.
- **Clamps/limits:** None stated at formation; limiting stages follow separately.

---

### Stage 5 — Unloader Control (End-Stop / Lock-to-Lock Clamp)

- **Section heading:** "Unloader Control" (page 1)
- **Inputs:** Target current, motor speed
- **Output:** Reduced motor current (protective clamp near steering limits)
- **Description:** "The unloader control reduces motor current at the lock to lock (full right or left) of the steering wheel to protect the system."
- **Trigger condition:** Lock-to-lock (full right or full left) position.
- **Named gains/tables/maps:** None named explicitly.
- **Numeric limits:** None stated explicitly in document.

---

### Stage 6 — Motor Output Limit Control (Thermal / Stationary Overuse Clamp)

- **Section heading:** "Motor Output Limit Control" (page 2)
- **Inputs:** Motor temperature, internal control system temperature; trigger: repeated turning while stationary
- **Output:** Reduced motor current (gradual reduction of power assist force)
- **Description:** "The motor output limit control reduces the motor current in the event of repeated turning of the steering wheel when the vehicle is not in motion. This control gradually reduces power assist force."
- **Recovery condition:** "The power assist force resumes gradually from the steering torque of **0 N·m (0 kgf·m, 0 lbf·ft)** or from having the ignition switch in the OFF position and it may take up to **20 minutes** to go back to normal assist force conditions."
- **Activation basis:** "The activation of the motor limit control is based on the motor and the internal temperature of the control system."
- **Numeric values (verbatim):** Recovery threshold = 0 N·m steering torque; recovery time up to 20 minutes.

---

### Stage 7 — Current Feedback Control

- **Section heading:** "Current Feedback Control" (page 1)
- **Inputs:** Target current (Stage 4, after limiting stages), actual motor current (from current detection circuit)
- **Output:** Motor current command (closed-loop corrected)
- **Description:** "The current feedback control monitors the motor current through sensors and reduces any deviation of motor current compared to the target current, thus accurately running the motor."
- **Control type:** Feedback (implied PI or PID, not stated explicitly).
- **Named gains/tables/maps:** None named explicitly.

---

### Stage 8 — Steering Wheel Return Control (Active Return-to-Center)

- **Section heading:** "Steering Wheel Return Control" (page 1)
- **Inputs:** Steering angle, "other boundary conditions" (unspecified)
- **Output:** Return speed control of the steering wheel
- **Description:** "The steering wheel return control controls the return speed of the steering wheel in dependence upon the steering angle and the other boundary conditions. This control is responsible for the return and overshoot behavior of the steering wheel."
- **Note:** Responsible for both return (centering) and overshoot damping.
- **Named gains/tables/maps:** None named explicitly.
- **Clamps/limits:** None stated.

---

### Stage 9 — EPS Motor Control Circuit (Output Formation — Three-Phase PWM)

- **Section heading:** "EPS Motor Control Circuit" (page 1–2)
- **Inputs:** CPU current command (output of feedback control loop)
- **Output:** Three-phase PWM drive signals to FET bridge → EPS motor
- **Hardware components:** System control CPU, FET drive circuit, FET bridge, power relay, fail-safe relays, electric current detection circuit, relay drive circuit.
- **Description:** "With the signal from the input sensor, the CPU calculates and outputs the appropriate three-phase current by duty cycle for the FET drive circuit. This operation is duty controlled."
- **Motor current feedback path:** Electric current detection circuit feeds back to CPU (closes Stage 7 loop).

---

## Supplementary Control Loops (not in the main torque-command path)

### Steering Wheel Vibration Warning Control

- **Trigger:** EPS control unit receives steering wheel vibration request from multipurpose camera unit via F-CAN.
- **Action:** Drives motor to generate vibration on steering wheel (haptic alert).
- **Pipeline relevance:** Externally-commanded current injection via CAN — same actuator path, separate command source.

### Steering Angle Detection (Sensor Pipeline)

- **Page:** 2
- **Chain:** Motor angle sensor → (A) motor rotational angle → × reduction ratio of worm gear → (B) assist pinion shaft angle → VGR (Variable Gear Ratio) conversion map + initial steering angle → (C) manual pinion shaft angle → + torsion bar torsional angle correction (from torque sensor) → (D) steering wheel angle.
- **VGR map:** Named but not characterized numerically in this document.
- **Relevance:** Steering angle output (D) feeds Steering Wheel Return Control (Stage 8) and steering angle neutral position learning.

### Steering Angle Neutral Position Learning (page 3)

- **Types:** Initial learning (first drive after clear) and regular learning (drift correction during driving).
- **Trigger for initial:** Vehicle judged to be going straight based on all sensor signals.
- **Clear conditions:** Replacing EPS motor/control unit; disconnecting 12V battery; disconnecting power from EPS control unit; decreasing EPS control unit supply voltage.

### Motion Adaptive-EPS Control (pages 3–4)

- **Inputs:** VSA modulator-control unit data, yaw rate sensor, acceleration sensor.
- **Output:** Correction current added to steering torque.
- **Sub-modes:**
  - Mitigates Oversteer: countersteer direction torque compensation.
  - Mitigates Understeer: steering torque correction to control oversteer and hold tire grip.
  - Stabilizes braking on split-mu surfaces: torque compensation during abnormal vehicle behavior under braking.
- **Stop condition:** Stopped if VSA system failure detected.

### Straight Driving Assist (page 5)

- **Condition:** Cruise control active + speed set.
- **Function:** Detects and reduces steering effort when driving on a sloped road (cross-slope compensation). Returns to normal when no longer on slope.

---

## Fail-Safe Actions (page 5)

On detection of failure in: motor system, torque sensor system, power supply system, communication system, or CPU — EPS indicator illuminates and one of:

1. Stop assist
2. Limit assist
3. Start alternative assist (limited control)

---

## Explicit Numeric Values in Document

| Value | Context | Source |
|-------|---------|--------|
| 0 N·m (0 kgf·m, 0 lbf·ft) | Motor Output Limit Control recovery threshold — steering torque at which gradual assist restoration begins | Page 2 |
| Up to 20 minutes | Motor Output Limit Control — maximum time to return to normal assist after thermal limiting activation | Page 2 |

No other numeric gains, table values, clamp levels, thresholds, or PID parameters are stated in this document.

---

## Key Absences / What This Document Does NOT State

- No dual torque-sensor (main/sub) plausibility check is described or mentioned.
- No driver-override / hands-on / torque-plausibility detection logic is described or thresholded. The document does not address how the system detects driver intent or hand-presence.
- No numeric assist table values, column/row breakpoints, or speed-dependent gain curves are given.
- No explicit clamp values for the main current path (other than Unloader at lock-to-lock and Motor Output Limit at thermal threshold).
- No q-axis / d-axis current decomposition is described; the document uses "motor current" / "three-phase current" without FOC-level detail.
- No torque sensor signal conditioning or main/sub plausibility logic is documented.
- No friction compensation term is named (inertia and damping are named; friction is not).

---

## Summary Pipeline Diagram (text form)

```
[Steering Torque + Vehicle Speed]
        |
        v
[1. BASE CURRENT]  <-- speed-dependent assist scaling
        |
        +-- [2. INERTIA COMPENSATION]  (inputs: torque, speed, motor speed)
        |
        +-- [3. DAMPING COMPENSATION]  (inputs: torque, speed, motor speed)
        |
        v
[4. TARGET CURRENT]  = base ± inertia ± damping, signed by torque direction
        |
        +-- [5. UNLOADER CONTROL]      (clamp at lock-to-lock, uses target + motor speed)
        |
        +-- [6. MOTOR OUTPUT LIMIT]    (thermal/stationary overuse clamp; recovery at 0 N·m, ≤20 min)
        |
        v
[7. CURRENT FEEDBACK CONTROL]  (closed loop: target vs. actual motor current)
        |
        v
[9. EPS MOTOR CONTROL CIRCUIT]  (3-phase PWM, FET bridge, duty-controlled)
        |
        v
    [EPS MOTOR]

Parallel / additive:
[8. RETURN-TO-CENTER CONTROL]  (inputs: steering angle + boundary conditions) --> adds to motor command
[Motion Adaptive EPS]           (VSA/yaw/accel data) --> correction current into torque
[Vibration Warning]             (F-CAN request from camera) --> haptic injection
[Straight Driving Assist]       (cruise active + slope detected) --> assist injection
```
