---
name: feedback-shared-scratchpad-use-a-private-subdir
description: Parallel tracer subagents share ONE session scratchpad — another agent overwrote my gpscan.py/movhi.py mid-session and my next run imported ITS module and printed its output; always write scripts into a private subdir with unique module names
metadata:
  type: feedback
---

**Rule.** When running as one of several parallel subagents, write every helper script into a
**private subdirectory** of the scratchpad, such as `scratchpad/<agent-name>/`. Give modules
agent-unique names, such as `tsr_gp.py` rather than `gpscan.py`.

**Why.** On 2026-09-30 three tracers ran at once (`tracer-angle`, `tracer-hook`, `tracer-speed-ram`).
Another agent wrote its own `gpscan.py` and `movhi.py` into the shared scratchpad root. My next
`from gpscan import *` silently imported that module instead of mine. It printed a census for different
cells and then crashed. A run that had not crashed would have produced numbers from someone else's scanner
under my name. That is a confident wrong answer.

**How to apply.**
- Before the first script, run `mkdir scratchpad/<name>/` and `cd` into it.
- If an import ever prints output you did not write, stop. Run `ls` on the scratchpad and check for a
  name collision before trusting any result.
- Re-run the positive controls after recreating the module.

[[reference-accord-angle-loop-cave-inputs-speed-torque-ram-homes-v295]]
