# STATE archive

A RECORD, NOT AN INSTRUCTION.

## ⚠⚠ **V158's NAMED RISK — `gp-0x6bd0` FEEDS *BOTH* AGGREGATORS, AND PATH 2 INVERTS ITS SIGN**
Found in the golden model's **facade header** (`eps_lkas_chain_model.py`, "KNOWN MODELLING GAPS"),
which the four modules do not repeat — so a session that reads only `lanes`/`control` never sees it.

> *“`gp-0x6bd0` is called ‘damping’. **True for PATH 1 only.** `FUN_00038148` (Path 2) applies its
> **OWN extra `pol` multiply**, so with **pol = −1 the SAME cell arrives PUMPING-signed there.** The
> sign does not transfer between the two aggregators.”*

✅ **[EVIDENCE] byte-confirmed — `gp-0x6bd0` has 5 readers, and two are the two aggregators:**
```
   0x3AC78   FUN_0003aa2c   PATH 1 aggregator   -> DAMPS
   0x38150   FUN_00038148   PATH 2 consumer     -> extra pol multiply => PUMPS at pol = -1
   0x34726 / 0x347BC  its own writer function     0x1C114  (unattributed)
```
✅ **[EVIDENCE] `gp-0x6752` (pol) is −1 on this car** — verified three ways, ★★★★★ in memory.
=> **V158 raises a term that damps in Path 1 and pumps in Path 2.**

### ⊕ WHY THIS IS A CAVEAT, NOT A CANCELLATION
- Path 1 is the **primary** torque aggregator; Path 2 is the **disturbance-observer** loop.
- Path 2's contribution reaches the car through **f′, which is compressed 6.3x when the driver
  pushes** — the same mechanism that explained V89's and V97's nulls.
- **V74 already flew this cell's dose** (delivered 50 at the ratchet's operating point, 67.4 % duty
  at engaged creep, 0 frames at the ceiling) with no adverse report attributable to it.
- The golden model **prescribed this exact edit knowing the architecture.**
⚠ But it **cannot be certified**: the model states Path 2's loop gain is unlocated (below), so the
relative weight of the damping and pumping contributions is **unknown**.
⭐ **THIS IS THE NAMED MECHANISM FOR THE “WORSE” BRANCH.** The pre-registered decision tree already
routes *worse → revert to V122*; it now has a **specific predicted cause** rather than a bare
possibility, which makes the drive strictly more informative.

## ⛔ **CORRECTION TO THE GOLDEN MODEL — PATH 2's “EIGHT FLOAT COEFFICIENTS” ARE NOT AT THOSE ADDRESSES**
The model says Path 2's loop gain *“lives in EIGHT float coefficients at `tp+0x50d4/0x50d8/0x504c/
0x5050/0x50bc/0x50d0/0x50d2/0x50d6` — **NEVER BYTE-READ BY ANY SESSION**”*. Read now:
```
   tp+0x504C 0xC404C  0.0             tp+0x50D4 0xC40D4  2.2592335e-38
   tp+0x5050 0xC4050  0.0             tp+0x50D6 0xC40D6  2.8350151e-30
   tp+0x50BC 0xC40BC  6.7593616e-37   tp+0x50D8 0xC40D8  2.8067167e-40
   tp+0x50D0 0xC40D0  9.3677923e-39   tp+0x50D2 0xC40D2  1.3885641e-37
```
⛔ **Every one is a DENORMAL**, and three of the addresses are **the kit's own known u16 cals**:
`0xC40BC` = the relay knee (3000), `0xC40D0` = the friction EMA pole (408), `0xC40D2` = K1 (1020).
**No firmware uses denormals as filter coefficients.** => **the stated addresses are WRONG** —
consistent with the model's own admission that they were never verified, and with CLAUDE.md's
*“off-by-0x1000 on tp-relative cals has recurred FIVE times.”*
⭐ **THE TRAP THIS DEFUSES**: a future session reading those cells as floats gets ≈ 0 and could
conclude **“Path 2's loop gain is zero, so Path 2 is dead”** — a wrong and consequential inference,
because Path 2 demonstrably runs (V89/V97 measured f′ compression through it).
=> **Path 2's loop gain remains UNLOCATED. GATE 2 for Path 2 stays uncertifiable** — now for the
sharper reason that the coefficients have never actually been found, not merely never read.
**[OPEN] what would close it**: locate the real coefficient block from `FUN_0003b8f6`'s decompile
(float loads, not u16), then re-derive the loop gain.

