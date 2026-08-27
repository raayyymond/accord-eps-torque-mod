---
name: feedback-check-build-scripts-before-proposing-cal-edit
description: Before recommending any calibration address as a "new" lever, grep analysis-2020accord/build_v*_tva.py for that address — it may already be flashed and falsified.
metadata:
  type: feedback
---

Never propose a calibration-only test address without first grepping `analysis-2020accord/build_v*_tva.py`
for it. On 2026-07-26 I recommended `0xC6450` (tp+0x7450, `FUN_0003a382` Stage A pole) `1024→32` as a
"never flashed" cal-only test — team-lead corrected me: it is `builds/v18_v49/build_v46_tva.py` verbatim (same address,
same values, same predicted effect, `_v46_plain_image.bin` confirms `0xC6450=32`), **flashed and
falsified** ("V46 FLASHED... vibration UNCHANGED... LEVER A FALSIFIED", already recorded in CLAUDE.md).
This was the **second time** an agent in this kit independently re-proposed `0xC6450` as a "new" lever —
CLAUDE.md already carried a standing warning about the first occurrence, and I still hit it, because I
was reasoning purely from structural/decompile evidence (single reader, no lockstep, clean gain math)
without checking whether the edit had already been tried. The sibling constant `0xC644A` is the same trap
(V43, also flashed, also null).

**Why:** structural cleanliness (single reader, no lockstep pair, safe cal-block location) proves an edit
is SAFE to flash, not that it's NEW or UNTESTED. Those are separate questions, and only the build-script
record answers the second one. A confident, well-evidenced recommendation that turns out to be a rerun of
a known-null experiment wastes a flash cycle and erodes trust in the analysis, even though the underlying
trace was itself correct.

**How to apply:** before writing any sentence recommending a cal address as a test candidate — anywhere,
in any report — run `grep -rniE "0xADDR" analysis-2020accord/build_v*_tva.py` (or the tp-relative
equivalent) for that exact address AND its known aliases (tp-offset form, absolute form). If a build
script already touches it, read that script's docstring for what it changed it to and what the on-car
result was (check CLAUDE.md's "Current builds" section too) before saying anything else about it. This
check takes one Bash call and should happen before, not after, a recommendation goes out. See
[[reference_accord_fun3a382_engagement_gated_residual_loop]] for the specific incident and the corrected
finding it led to (authority-gated output bound in the same function, a genuinely untested lever).

---

## 🛑 2026-08-10 — A HIT IS NOT A CHECK. Grepping and then not reading the hits is the same failure.

`DampAxis`. I ran the grep on `0xCBE74` and it returned **seven** build scripts (V73–V77, V81). I filed
that under "context for §5" and moved on **without opening one of them to see whether they WROTE it**.
Later I reported *"`0xCBE74` is virgin on V89"* — literally true, and the team-lead read it as
"never written" and moved to cut a build on it. Only when explicitly asked to *"confirm from the images"*
did I dereference `0xCBE74 + mode*4` across the lineage and find the Y row **flown at ×1.5 on V74/V75/V77**
(introduced by V73), with **V74 and V75 both hard-faulting.** I nearly let an already-flown lever be
re-cut as a new one — the exact failure CLAUDE.md's standing warning names.

**Why it slipped:** the grep *succeeded*, which felt like the check was done. But the grep answers
"is this address mentioned?", and the decision needs "was this cell's VALUE changed, to what, and what
happened on the car?" Those are three different questions and only the last one gates a build.

**How to apply — the check has FOUR steps, not one:**
1. `grep` the address across `build_v*_tva.py`. **A non-empty result is the START of the check.**
2. **Open each hit** and classify it: *written* vs *asserted-stock* vs *mentioned in a docstring*.
   (`builds/v50_v79/build_v74_tva.py:79` said "LEVER D' — THE FRICTION LANE ×1.5" in plain text.)
3. 🛑 **Dereference the cell across the IMAGES**, not the scripts — mode-indexed cells hide behind a
   pointer array, so the literal address never appears where the value lives. One Python loop over
   `_v*_plain_image.bin` reading `ptr = u32(img, ARRAY + mode*4)` settles it beyond argument.
4. Read the **on-car result** in `BUILD-LINEAGE.md` for every build that wrote it, and check for a
   *correction of record* (this one had one, dated 2026-08-07, reattributing the edit from V74 to V73).

**Scope-widening rule:** "virgin on build X" ≠ "never written". **Never state a virginity claim scoped to
a single image** — if the claim is decision-bearing, scope it to the whole lineage or don't make it.

### Same day, second overstatement: **A GLOB IS NOT A CHECK — two artifacts can share a build number**

Having found the ×1.5 flight history, I told team-lead *"×1.5 was on the car for the V73→V77 era with
grinding present throughout ⇒ treat it as a known-null rung"* — and they were about to put that to the
operator as the reason to skip ×1.5 and go to ×3. **It was wrong.** My cross-build table came from a
`glob` on filename prefixes, which **silently picked one of TWO V76 artifacts**:

```
_v76_gate_fb_arm5244_gateprobe   m26 x1.5, clamp 850   <- what my glob matched
_v76_v38base_relu_damper         m26 STOCK, clamp 511  <- THE ONE THAT FLEW
```
`BUILD-LINEAGE`'s V76 row reads `| V76 | V38 | … | FLEW route 65 |` — **the BASE column ("V38") is the
discriminator**, and the flown artifact had the ×1.5 reverted by the V38 rebase (that row's own note:
*"the V38 rebase silently reverted SEVEN things"*). True history: ×1.5 flew **three** times — V73 clean,
V74 and V75 hard-faulted — i.e. **ONE clean route of evidence, not an era.** That materially reopened ×2
as a dose option, which my overstatement had closed off.

**How to apply:**
- 🛑 **When two images share a build number, the `BUILD-LINEAGE` row's BASE column tells you which flew.**
  Never infer from the filename prefix alone, and never let a `glob` pick for you — enumerate ALL matches
  and print them, so a second artifact is visible rather than silently dropped.
- 🛑 **A hard-faulted build yields almost no driving data.** Do not count it as exposure. "Flew" and
  "produced evidence" are different claims; "N builds carried it" is not "N builds tested it".
- **Both of today's lineage errors share one root cause: I matched something and then asserted from the
  match instead of opening it.** The grep, and then the glob. **Matching is not reading.**

### Third overstatement, same cell, same day: 🛑 **AN ADDRESS IS NOT A MODE**

After retracting "an era" I wrote a corrected table saying **"V73 | ×1.5 | FLEW CLEAN, n=1"** — while my
own byte table *three paragraphs earlier in the same message* read `_v73_plain_image  stock  stock`.
**I shipped a self-contradiction.** Team-lead caught it. A 34-mode dereference settles it: **V73 dosed
exactly ONE friction Y row — m10, a DISENGAGED mode on another variant's row ⇒ inert on this car.**
⇒ **×1.5 on a live column flew twice (V74, V75) and both hard-faulted. ZERO clean flights**, not one.
That killed the ×2 option I had just reopened on the strength of the phantom clean flight.

**And team-lead's own correction carried the mirror-image error**: they named `0xD6A5C` as mode 24's Y
row. It is **mode 23's**. Mode 24's is `0xD6A6C`. Their list was the set **V74 dosed**, which is not the
set **V90 should write** — V74 never touched m24. A builder handed it would have written another
variant's column: **the V69 failure, inside the message warning about the V69 failure.**

**How to apply:**
- 🛑 **Never let a raw address stand in for a mode anywhere in a spec, a table, or a sentence.**
  Dereference `arr + mode*4` and **print the mode number beside every address.** That single habit would
  have caught V69, my error, and team-lead's.
- 🛑 **"The set a previous build dosed" ≠ "the set this build should write."** Check the intersection
  explicitly; here it was 1 of 2.
- 🛑 **Cross-check your own summary row against your own byte table before sending.** The contradiction
  was inside one message. Re-read the evidence block, not just the conclusion.
- **Name Y-array addresses, never record bases.** Layout is `[count | X×n | Y×n]`, Y at `base+2+2n`.
  Writing Y values at `base+2` corrupts X **silently** — negatives read as large u16 by the LERP's
  unsigned compare, so every index falls below `X[0]` and the table returns a flat `Y[0]`. Plausible
  output, wrong experiment, no crash.
