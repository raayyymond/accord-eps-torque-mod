# STATE archive — superseded during the drive-tooling audit

A RECORD, NOT AN INSTRUCTION.

## 🛑🛑 **THE CREEP-AUTHORITY CHAIN IS CLOSED — LOCKOUT ALREADY PULLED, NEXT CONJUNCT NOT A CAL**
All three complaints live at **2–8 km/h**, and the kit's most on-target lever for that band is the
**low-speed steer lockout**. Followed it to the end. **Both links are closed, and the record needed
two corrections.**

### 🛑 LINK 1 — THE LOCKOUT IS **ALREADY REMOVED** ON THE FLYING BUILD
```
   0xC62EA  low-speed lockout threshold   stock 320 (4.995 km/h)   V122 = 0   => NO LOCKOUT
   across 157 images: {0: 108, 320: 49}
```
⇒ **[EVIDENCE] `0xC62EA` = 0 on V122 — the lockout has been off for most of the arc.**
⇒ **the 6.4 % command railing at 2–8 km/h is NOT caused by the low-speed lockout.** That lever is
**spent, not available**, and must not be re-proposed.

### ✅ LINK 2 — THE MEMORY'S OWN PRE-REGISTERED NEXT SUSPECT, AND IT IS **NOT CAL-REACHABLE**
`accord-low-speed-lockout-window-c62ea` pre-registered the follow-up: *"If a lowered `0xC62EA`
doesn't work, `gp-0x69aa` is the next suspect."* **It doesn't work — it is already 0 — so the suspect
is activated.** Read at its site (`0x29000–0x29200` **byte-identical stock vs V122**):
```asm
   0x290fc  ld.hu -0x69aa, gp, r14      ; the governor Q15 derate
   0x2910c  ori   0x8000, r0, r9        ; 0x8000 built as an IMMEDIATE
   0x29110  cmp   r9, r14
   0x29112  bh    0x29138               ; UNSIGNED HIGHER -> the FAILURE path (STEER_STATUS = 3)
```
🛑 **The 0x8000 threshold is a HARD-CODED IMMEDIATE (`ori 0x8000, r0, r9`), NOT `cal(0xC63F2)`.**
`0xC63F2` = 32768 is read at `0x28ECE`, a **different site** with a different role.
⇒ **[EVIDENCE] the governor-derate conjunct is NOT reachable by any calibration.** Changing it would
need an in-place instruction edit. **The pre-registered next suspect is closed as a cal lever.**

### ⚠ CORRECTION 1 — THE COMPARISON IS `<=`, NOT `==`
The memory records the conjunct as **`gp-0x69aa == 0x8000`**. The instruction is `cmp r9,r14` then
**`bh`** (branch if unsigned HIGHER) to the failure path.
⇒ **the passing condition is `gp-0x69aa <= 0x8000`, not `== 0x8000`.** Any derate BELOW unity still
passes; only values ABOVE 0x8000 fail. **[CORRECTED in the record.]**

### ⚠ CORRECTION 2 — I HIT THE OFF-BY-0x1000 TRAP, AND CAUGHT IT
I first wrote `tp+0x73F2` as **`0xC73F2`**. `tp = 0xBF000`, so it is **`0xC63F2`**.
⇒ **that is the SIXTH recorded recurrence** of the trap `CLAUDE.md` calls out (it lists five).
⇒ caught by anchoring against the memory's own stated value (32768) — the wrong address read **14**,
the right one reads **32768**. **The anchor-against-a-known-value discipline is what caught it, and
it is worth keeping in front of every session.**

### ✅ WHAT REMAINS OF THE CREEP-AUTHORITY QUESTION
```
   0xC62EA  lockout threshold        ALREADY 0 -- spent
   gp-0x69aa governor derate         threshold is a HARD-CODED IMMEDIATE -- not a cal
   gp-0x67fe substate == 2           a state, not a cal
   gp-0x69ae within +-0x4000         not yet examined
   5-channel validity test           not yet examined
   0xC61BC  setpoint clamp +-15360   VIRGIN, binding UNKNOWN  <-- the only cal candidate left
```
⇒ **of the AND-chain that gates control-active at creep, the only remaining CAL-reachable candidate
is `0xC61BC`** — which is exactly the cell the `iVar31 ≥ 5482` probe would settle.
⇒ **the probe is now the last cal-reachable question in the entire creep-authority chain.**

## 🛑🛑🛑 **ALL THREE COMPLAINTS ARE CREEP PHENOMENA — AND SPEED-SCHEDULING THE GAIN IS DEAD**
Tried to **make** a new lever rather than find one: **schedule the gain by speed** — high where
authority saturates, low where grinding lives — which would break the authority/grinding tension
outright. **It only works if the two live at different speeds. They do not.**
```
   WHERE THE COMMAND RAILS  (engaged frames, all routes pooled, 1.6 M frames)
   speed band       engaged frames     railed    rail duty
   0-2   km/h            140,277          546      0.389 %
   2-8   km/h            156,381        9,956      6.367 %   <-- THE PEAK
   8-16  km/h            438,274        3,836      0.875 %
   16-25 km/h            498,164          842      0.169 %
   25-40 km/h            372,168           34      0.009 %

   CREEP (0-8 km/h)  3.540 %      HIGHWAY (>=16 km/h)  0.101 %      ratio 35x
```
⇒ **[EVIDENCE] authority saturation is a CREEP phenomenon** — **6.4 % of engaged frames at
2–8 km/h**, falling **35x** by highway speeds.
⇒ **🛑 SPEED-SCHEDULING THE GAIN IS DEAD AS A LEVER.** There is no band where authority is needed
and grinding is absent — they are **the same band**. A gain that is high where the command rails is
high exactly where the grinding is. **Lever class closed before any build was spent on it.**

### ⭐ BUT IT UNIFIES THE THREE COMPLAINTS
```
   peak command oscillation   the command rails at its 13-bit max, 6.4 % of frames at 2-8 km/h
   LKAS authority             saturated in that same 2-8 km/h band
   grinding / ratcheting      symptom A's micro regime (1-13 deg/s) and symptom B's <10 mph
                              acoustic excess are BOTH in that same band
```
⇒ **[EVIDENCE] all three of the operator's complaints are the SAME OPERATING POINT: engaged creep,
roughly 2–8 km/h.** They have been treated as three problems for the whole arc; they are three
observations of one regime.
⇒ **any real fix must act AT CREEP**, and a fix that only works above 16 km/h addresses none of them.

### ✅ WHICH SHARPENS THE FLIGHT ORDER — V157 IS THE ONLY BUILD TARGETED AT THE RIGHT PLACE
```
   V157 / V156   act ONLY at creep      FactorC opens below 35 km/h AND FactorE below 12.73 deg/s
                                        => the damper is non-zero EXACTLY in the 2-8 km/h band
   V153 / V152   act at ALL speeds      observer poles are not speed-gated
   V149 / V150   act at all speeds      switch removal, not speed-gated
   V139          acts at all speeds     pump arms, not speed-gated
   V155 / V154   act at all speeds      inertia-lane weight, not speed-gated
```
⇒ **V157 is the ONLY queued build whose effect is confined to the band where all three symptoms
live.** Every other lever spends its effect mostly outside it.
⇒ **This is now the strongest argument for V157 first**, and it is an argument from measurement
rather than from mechanism.

## ⚠ **THE RAILED-COMMAND NATURAL EXPERIMENT IS UNDERPOWERED — RECORDED SO IT IS NOT RE-RUN**
A rail episode freezes the command at ±4096, so it is a **natural experiment**: if the ratchet
persists while the command is constant, the command is not driving it. Ran it. **The cached data
cannot support it.**
```
   tq 6-9 Hz share, RAILED / FREE windows, matched on speed bin, 1.3 s windows
   route   n_rail  n_free   6-9 Hz ratio   26-31 Hz "control"
   r75          4     316        1.73            0.31
   r77          9     465        2.21            0.32
   r9e          3     180       19.05            0.04
```
🛑 **ONLY 3 ROUTES QUALIFY, with 3–9 railed windows each**, and the ratios span **1.73 to 19.05**.
🛑 **AND THE STATISTIC IS COMPOSITIONAL** — band *share* is normalised to 1–45 Hz, so 6–9 Hz rising
**forces** the control band down arithmetically. **The control here is NOT independent evidence**,
which is precisely the failure mode `feedback-run-the-control-before-the-measurement` warns about.
⇒ **[NOT CLAIMED] anything from these numbers.**
⊕ **Directionally** all three exceed 1 while the command is frozen, which is consistent with the
ratchet not being command-driven — and that is **already established independently** by V87 (the
7.8 Hz line has prominence **12.9 in the COLUMN but 4.0 = chance in the COMMAND**). **The experiment
adds nothing V87 did not already give.**
⇒ **What would close it: rail episodes are ~0.78 % of engaged frames and only 28 % of routes have
any. This needs a drive that DELIBERATELY sustains saturation** (a long steady curve at creep) — and
even then it only re-confirms a settled point. **Low value; recorded so it is not attempted again.**

## ⚠ **THE RAILED COMMAND IS SUSTAINED ONE-SIDED SATURATION, NOT A RAIL-TO-RAIL LIMIT CYCLE**
Follow-up to the ±4096 rail finding: **is the railing a limit cycle?** Tested, and the answer is
**no — and the test that would have said yes is underpowered, which I am recording rather than
dressing up.**
```
   route     n_eng    neg%   pos%   rail-to-rail alternations   median gap   implied freq
   r78       56230   0.70%  0.32%              6                  1.25 s       0.401 Hz
   r85       12000   1.23%  4.00%              4                  5.82 s       0.086 Hz
   r96       35048   0.37%  0.70%              4                  1.84 s       0.272 Hz
   r96s11     6000   2.18%  4.10%              4                  1.84 s       0.272 Hz
   pooled: 12 intervals, median 1.84 s, quartiles 1.37 / 1.84 / 2.23
```
🛑 **ONLY 4 OF 114 ROUTES EVER SWING RAIL-TO-RAIL, and they yield 12 intervals total with a 4.7×
spread in implied frequency (0.086–0.401 Hz).**
⇒ **[NOT CLAIMED] a limit-cycle frequency.** Twelve intervals across four routes that disagree by
4.7× is not a measurement; quoting "0.27 Hz" from it would be exactly the kind of number this kit
has had to retract before.

### ✅ WHAT IT DOES ESTABLISH — AND IT SHARPENS THE EARLIER RESULT
**The command overwhelmingly rails on ONE side and STAYS there** — up to **399 frames ≈ 4 s**
continuous — rather than alternating between rails.
⇒ **the operator's "peak command oscillation" is, in the data, SUSTAINED ONE-SIDED AUTHORITY
SATURATION**, not a controller limit cycle between limits.
⇒ **that is consistent with, and strengthens, the authority diagnosis**: openpilot asks for the
maximum the field can carry and holds it, because the plant is not delivering enough per count.
⇒ **it also means no "oscillation-damping" lever applies** — there is no cycle to damp. **The fix
is torque-per-count, which is the gain (frozen) or `0xC61BC` (binding unknown).**

⊕ **This turn produced a refinement, not a breakthrough**, and the analysis remains where it was:
**eleven verified builds unflown, and the binding constraint is a drive.**

