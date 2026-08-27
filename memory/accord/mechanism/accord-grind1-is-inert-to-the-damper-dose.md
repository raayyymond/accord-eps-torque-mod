---
name: accord-grind1-is-inert-to-the-damper-dose
description: RETRACTION — across k = 0.58 to 4.16 on one instrument, every grind-#1 point sits inside its own split-half noise floor. V80 did not overshoot an optimum; grind #1 never responded to damper dose at all. The micro-ratchet DOES respond, and is best at V80's dose.
metadata:
  type: reference
---

# 🛑🛑 RETRACTION — **GRIND #1 IS INERT TO THE DAMPER DOSE**

**2026-08-07.** Four builds re-scored on **ONE instrument**
(`rlog-tools/studies/grind/compare_v75_v76_v80_grind.py`: NFFT 256 / hop 128, p99 analytic band envelope, ~10.2 s
bootstrap blocks **nested inside engagement runs**). Ratios are to V76.

| band | V74 `k`=0.58 | V76 `k`=1.39 | V75 `k`=1.58 | V80 `k`=4.16 |
|---|---|---|---|---|
| **18–22 grind #1** | 1.166 [0.98, 1.41] | 1.000 ref | 0.735 [0.50, 1.22] | 0.835 [0.64, 1.07] |
| 6–9 micro-ratchet | 0.818 [0.70, 1.09] | 1.000 ref | 0.821 [0.66, 1.09] | **0.418 [0.33, 0.61]** |
| 26–31 | 0.823 [0.72, 1.02] | 1.000 ref | 0.865 [0.71, 1.20] | 1.197 [0.80, 1.52] |
| **40–49 grind #2** | 0.810 [0.70, 0.97] | 1.000 ref | 0.961 [0.77, 1.24] | **2.017 [1.32, 2.83]** |
| **30–49 HF floor** | 0.820 [0.73, 1.01] | 1.000 ref | 0.953 [0.81, 1.26] | **2.091 [1.46, 2.70]** |
| **32–38 neg control** | 0.865 [0.76, 1.03] | 1.000 ref | 0.959 [0.82, 1.22] | **2.035 [1.45, 2.57]** |

**Split-half nulls (300 halvings, per route): 18–22 Hz ≈ [0.63, 1.60].**
⇒ **EVERY grind-#1 point sits inside its own noise floor across `k` = 0.58 → 4.16.** [EVIDENCE]

## What this retracts
🛑 **The 18–22 Hz dose-response is WITHDRAWN.** Two memories asserted it with a CI that excluded zero —
[[accord-damper-fixes-the-grind-but-is-flat-on-the-ratchet]] (`d ln y/dk` = −0.599 [−0.856, −0.348]) and
[[accord-grind1-dose-limited-ratchet-dose-independent]] (−0.614 [−0.810, −0.416], with V76's *point*
prediction held to 0.19 dB). Both are annotated in place; **read this node before quoting either.**
🛑 **"V80 overshot an optimum in `k`" is the wrong framing** — grind #1 never responded to `k` at all,
so there was no optimum to overshoot.
🛑 On this instrument, **V75's "no grind #1" versus V76's "still grind #1" is a creep-EXPOSURE
difference, not a dose difference**: V76's creep windows carry **3.4×** V75's steering effort.

⚠ **What is NOT retracted:** V62's `sar`-pair result (the kit's only measured 8× grind-#1 fix) is a
different lane entirely, and the operator's *lived* reports stand on their own
([[feedback_operator_lived_experience_overrides_analyst_recs]]). This retraction is about the **damper
dose axis**, nothing else.

## ★ The operationally useful statement that survives
> **`k ∈ [1.39, 1.58]` buys most of the ratchet benefit at ZERO HF cost. Something switches on between
> 1.58 and 4.16 that costs 2× broadband HF plus a sustained limit cycle. WHERE in that gap it switches
> on is UNMEASURED.**

★ **The micro-ratchet is the band that DOES move**, and it is best at V80's dose (**0.418 [0.33, 0.61]**,
clearing its own null). That is consistent with — not contrary to — the older estimate that *"the ratchet
needs `k` = 4.2–13.5"*: V80 is the first build to reach that neighbourhood. **If the operator wants the
ratchet gain back, it is a V82 question — not a reason to keep V80's flat top.**

## 🛑 V80's CREEP NUMBERS ARE AN EXPOSURE ARTEFACT — do not read them
V80's engaged creep windows have median sustained effort **173 counts** and median `|angle rate|`
**1.3 °/s**, against V74/V76/V75's **685/588/1113** counts and **33/33/48** °/s. **ZERO matched cells.**
An earlier claim this session that *"V80 is 3–30× quieter than V76 at creep"* is **RETRACTED** — the
driver was not turning the wheel. ⚠ Also unresolvable: whether V80's near-zero creep angle rate is itself
an *effect* of a 412-count-at-all-speeds damper making the wheel feel sticky.
⚠ Also not comparable: the **>80 km/h** stratum — V75 never exceeded 65 km/h and V80 has **1 engagement
run / 3 blocks** there (the limit-cycle event itself). **The 10–40 and 40–80 km/h strata are well matched
and carry the load.**

📋 **METHOD RULE this is the second instance of:** get the noise floor from a **split-half null on the
same instrument** *before* quoting any ratio, and re-score every build on ONE instrument before fitting a
dose axis across them — see [[feedback-episodes-not-windows-and-the-noise-floor]].

Related: [[accord-v80-flew-the-damper-is-a-relay]] · [[accord-two-ratchets-micro-is-the-779hz-line]] ·
[[accord-v62-flashed-grinding-is-fixed]]
