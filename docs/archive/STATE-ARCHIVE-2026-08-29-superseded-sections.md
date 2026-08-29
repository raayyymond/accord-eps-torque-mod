# STATE archive — sections superseded within the 2026-08-29 session

**A RECORD, NOT AN INSTRUCTION.** Each section below was written, then contradicted by
later work in the same session. They are kept because the reasoning that produced them is
part of the record, but **none of them is current** — the note above each says what replaced
it.


> 🛑 **RETRACTED in full by the cal-scan retraction section.**

## ⭐⭐⭐ **A BLIND CAL SCAN FINDS THE GRIND'S LEVER — AND NOTHING AT ALL FOR THE RATCHET**
Every lever this session came from reasoning about structure. The complementary search was still
untried: with **18 build-attributed routes** and each build's image on disk, correlate **every 16-bit
cal that actually varied** against the measured excess. **88 cells** qualify (≥3 distinct values).
Multiple comparisons are the whole difficulty, so the control is a **permutation null on the MAXIMUM
|ρ| across all cells** — family-wise, not per-test.
```
   RATCHET   family-wise 95 % threshold |rho| = 0.700
     strongest  0xC4B48 -0.620 · 0xC4BB4 -0.613 · 0xC4BB2 -0.613 · 0xC4B58 +0.578
     CELLS SURVIVING: 0

   GRIND     family-wise 95 % threshold |rho| = 0.687
     0xC40BC  rho -0.715   *** SURVIVES ***
     next     0xC4B36 +0.492 · 0xC4BC8 -0.487 · 0xC4BC4 -0.487
     CELLS SURVIVING: 1
```
⭐ **[EVIDENCE] the single surviving cell is `0xC40BC` — the Coulomb relay knee**, the exact cell
identified **independently, by structural reasoning**, as the grind's lever earlier this session
(ρ = −0.69, p 0.039 on 9 routes). **A blind scan over 88 cells with family-wise control picks out
that one and nothing else.** Two unrelated methods, one answer.
⚠ It survives **marginally** (0.715 against a 0.687 threshold) — real, not overwhelming.

### ⭐ AND THE RATCHET RESULT IS THE POSITIVE FORM OF V173's CASE
✅ **[EVIDENCE] NO cal that has ever varied tracks the ratchet** once multiple comparisons are
controlled. The best is ρ = −0.620 against a 0.700 threshold.
⇒ **the ratchet's lever must be a cell that has NOT been varied** — which is exactly what the assist
map's slope cap and section poles are (`0xC6384` and `0xC60A8..B4`, byte-identical across 161 images).
⊕ **This replaces the claim I had to retract.** *“Thirty-plus builds have not moved the ratchet”* was
an n=5 artefact. **“No cal that has varied tracks the ratchet, under family-wise control at n=18”** is
the better-founded statement, and it supports V173 more directly than the original did.
⊕ **It is consistent with the corrected build trend**: the ratchet *does* fall with build INDEX
(ρ −0.60) while tracking **no individual cal** — many cells moved together, and no one of them
explains it.
⊕ **EXTENDED AND UNCHANGED.** The first pass covered only `0xC4000-0xCD000`, missing `0xD7000` (the
damper records — V158's own lever) and `0xE4000`/`0xE5000` (V38's arbitration limits). Rerun across
**all three regions, 94 cells**: **identical verdict** — 0 surviving for the ratchet, `0xC40BC` alone
for the grind at the same ρ. The only new entry in either top-six is `0xD7FFC` (−0.472), **a CRC
trailer rather than a cal**. ⇒ **the null is not an artefact of where I looked.**


> 🛑 **SUPERSEDED by "I over-corrected: the ratchet trend is unresolved".**

## 🛑🛑 **CORRECTION: “THE RATCHET HAS NEVER MOVED” WAS AN n=5 ARTEFACT**
The headline of this session was that the grind falls monotonically post-V102 while **the ratchet does
not move at all** — the dissociation that motivated hunting a lever no build had touched. It rested on
**5 post-V102 routes**. With build attribution recovered for the rest of the corpus it rests on **11**,
and **it does not hold as stated**.
```
                          n      RATCHET              GRIND
   earlier (this session)  5     rho -0.14  p 0.787   rho -0.94  p 0.005
   full corpus            11     rho -0.60  p 0.052   rho -0.84  p 0.001
   HARD attributions only  7     rho -0.59  p 0.159   rho -0.76  p 0.049
```
🛑 **[EVIDENCE] the ratchet IS trending down post-V102** — ρ ≈ **−0.60**, p **0.052**, where n=5 showed
−0.14 (p 0.79). ✅ **And it is robust to attribution confidence**: restricting to routes whose build is
stated in memory or scored by me directly gives **−0.59** — the effect size is unchanged, only the
p-value moves with n. **It is not an artefact of the labels I inferred from filenames.**

### ✅ WHAT SURVIVES, AND WHAT DOES NOT
❌ **NOT SURVIVING**: *“thirty-plus builds have not moved the ratchet”* and *“the symptoms
dissociate”* in the strong sense of one moving and the other not. **Both fall post-V102.**
✅ **SURVIVING**: the grind falls **more strongly and more significantly** (−0.84 at p 0.001 vs −0.60
at p 0.052), so the two are still not responding identically — **a difference of DEGREE, not of kind.**
✅ **SURVIVING UNTOUCHED**: everything the build actually rests on — the ratchet is in **torque not
wheel rate**; it is **engaged-only** (7/7 vs 0/7); it is **command-driven** (CI now excludes zero); the
**assist map is the largest torque-fed term**; its **slope cap binds**; and **`0xC6384` and the curve
records are byte-identical across 161 images.** None of that came from the trend claim.

### ⭐ WHAT IT CHANGES FOR THE BUILD
⊕ **V173 stands.** Its case is that the assist map is the dominant term, the cap binds, and the
section was never retuned — **not** that other levers failed to reach the ratchet.
⊕ But the *motivation* is now weaker in one respect and **stronger in another**: weaker because the
assist map is no longer uniquely implicated by elimination; **stronger because the ratchet is
demonstrably reachable** — something has been moving it, so it is not the untouchable mechanical mode
the earlier reading implied.
⚠ **[LIMITATION]** eight of the eighteen attributions are recovered from tool and document filenames
rather than verified against an image. `r77` (97 windows, the richest route in the corpus) is
**excluded** because its candidates span V31–V91 and nothing disambiguates them — guessing to gain a
data point is how a spurious trend gets manufactured.

