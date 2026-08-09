# 2020 Honda Accord EPS Firmware Analysis Kit

A reverse-engineering reference kit for the 2020 Honda Accord's Electric Power Steering (EPS) firmware — `39990-TVA-A160` (Renesas V850E2). Built for working with Claude Code. Gifted from one tinkerer to another.

This is not a "press button, flash car" kit. It's the working environment of someone who's been deep in this firmware for months — the disassembly notes, the CAN→motor gating maps, the failed hypotheses, the small wins, the priming stack that keeps the agent honest, and the `.rwd` build lineage (V9 through V39) at various stages of validation.

If you're here, you probably already know what EPS firmware modification is for: more steering assist for openpilot / sunnypilot, on a car where stock assist tops out before the lateral controller is happy. The interesting work isn't "make number bigger" — it's understanding *why* a gain increase produces an unintended emergency-manual-EPS (EME) cutout, where the arbitration/shaper/debounce state machines live, and which cal values actually move the needle versus which ones are decoys or dead code.

---

## Safety

This is real-vehicle work. Please read this section before doing anything beyond reading files.

### Read this first — from the operator, who has actually done it

**This may brick your car.** I have only ever tested this on my **2020 Accord 2.0T Touring**.

**My first flash bricked my car.** The EPS would only accept a very specific memory region — and of course you have to erase the firmware *first*. I ended up writing a script that brute-forced through all the possible start and end memory addresses to get it to work. It was a nice, scary few hours of my life.

**Modifying the EPS firmware can result in very dangerous on-road failure modes.** I'm at a point with the 2× mod where I'm not experiencing anything dangerous myself — but it wasn't always like this, and I can't say it never will be, especially on someone else's car. At various points in this work I have:

- thought I might have to get the car towed and the EPS replaced or serviced
- experienced **power steering failing completely during harsh turns** — driver-side power steering gone
- experienced **power steering failing "gently" during harsh turns** — comma-side power steering assist gone

Keep in mind that a failure during harsh turns is a pretty bad failure mode: **it means the car immediately starts heading outside of the lane, at speed.**

**After flashing, run a fork that knows about the mod.** Use sunnypilot, StarPilot, or another fork that detects the modified EPS version string and auto-applies the 2× torque PID tuning settings. Running the modified firmware against stock tuning is not the configuration any of this was validated in.

### The non-negotiable rules

1. **Never send a CAN message without explicit confirmation of the exact payload — including UDS reads.** This is the iron rule. `CLAUDE.md` codifies it for the agent; hold the line yourself too.
2. **Never run `eps-update.py` or any flash operation unless the firmware file and the bus are explicitly named.** Repeat the filename back before proceeding.
3. **Before any flash, openpilot/pandad MUST be killed** (`tmux kill-server` on a comma device). A failed flash with openpilot still running has been observed to light every error indicator on the dash — recoverable, but retry only after killing openpilot.
4. **All `.rwd` files are reference/study artifacts by default.** They are data, not flash candidates.
5. **Firmware is car/year/revision specific.** Every `.rwd` here is built for `39990-TVA-A160` on one specific 2020 Accord. Confirm the part number before building for a car, and **do not cross-flash onto a different part number.** A failed flash with the wrong firmware for the wrong car/year/revision has not been characterized and could plausibly require ECU replacement.
6. **`tools/comma4_panda_test.py` is read-only and safe at any time after openpilot is killed.** It opens the panda, dumps CAN traffic, and exits. It does not transmit. Run it any time to verify your hardware path works. **Everything else that touches the ECU writes** — `flashing-2020accord/eps-update-tva.py` performs a UDS sequence that erases and reprograms the EPS ECU.

### Code caves are the only bricking class

Three builds have bricked this ECU — **V24, V27 and V48B** — and all three were code caves. Every success since V29 has been either cal-only or a single in-place branch/displacement edit.

Any cave, filter, or dynamics change has two mandatory gates:

- **GATE 1 — RAM ownership**, including writers and register-indirect access. Static clearance is **not** sufficient: `gp-0x1500` passed both static methods and still failed on-car.
- **GATE 2 — closed-loop stability**, magnitude *and* phase, in every loop the signal is in.

Detail in `docs/BUILD-LINEAGE.md` Part 2.

### Flash at your own risk

No part of this kit is warranted for use on any vehicle. The operator flashes their own car after rigorous validation. You should do the same.

---

## Credits

- **Joey** — the original curator of the agent firmware analysis kit.
- Community PID-tuning knowledge distilled into `docs/HONDA-EPS-PID-KNOWLEDGE.md` came out of a private Honda EPS tuning Discord working group (26 days, 4,989 messages); see `discord-export/` for the raw scrollback.

Use of this work in your own builds is welcomed. Attribution where it makes sense.

---

## License

Licensed under the **GNU General Public License v3.0**. See [`LICENSE`](LICENSE) for the full text.

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but **WITHOUT ANY WARRANTY**; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.
