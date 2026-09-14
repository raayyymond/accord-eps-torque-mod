# V293 close-out artifact — sources

Published page: **https://claude.ai/code/artifact/6751b3ba-2098-4c74-894b-b74741ff4565**
Written by agent `artifact3`, subagent of `main`, 2026-09-13.

**Every firmware number on the page is read little-endian from the plain images, never from a build
script's constants.** Reproduce the whole page from this folder:

```bash
export ACCORD_FIRMWARE_ROOT=C:/Users/dudei/Desktop/Projects/accord-firmwares
python v293_page_data.py    # reads 41 images -> v293_page_data.json   (~2 min)
python v293_charts.py       # -> v293_charts.json, exact SVG geometry
python render.py            # page.tmpl.html + the two json -> v293-torque-mode.html
```

Python is the `bin_decompile` conda env (`C:/Users/dudei/anaconda3/envs/bin_decompile/python`).

| file | what it is |
|---|---|
| `v293_page_data.py` | the image reader — cross-build matrix, delivered surfaces, feedback and r24 transfers, the full-file diff and its byte attribution |
| `v293_charts.py` | turns that into exact SVG polyline geometry; nothing on the page is eyeballed |
| `render.py` | substitutes the geometry and the tables into the template |
| `page.tmpl.html` | the page, with `{{key}}` placeholders |
| `diagram.svg.frag` | the main signal-flow diagram, hand-authored inline SVG |
| `v293-torque-mode.html` | the rendered page as published |

## Version 7 — V293 FLEW (route 70), the plant, the rev-2 fork side

Added 2026-09-13 by agent `page-v7`. The data-json regeneration above is known to time out, so
v7 was **spliced directly into both `v293-torque-mode.html` and `page.tmpl.html`**, byte-identically.

```bash
python v7_charts.py    # -> v7_figs.frag   (10 inline-SVG figures, exact geometry)
python v7_splice.py    # v7_sections.src.html + v7_figs.frag -> both html files
```

`v7_splice.py` refuses to run on an already-spliced file. **To re-run it, restore both files from
git first** (`git checkout -- v293-torque-mode.html page.tmpl.html`), then run both scripts.

| file | what it is |
|---|---|
| `v7_charts.py` | the v7 figure geometry — the measured plant LERP, the FF hold ratios, the ratchet, the LAF grid, the config margins, the band scores, and the rev-2 fork signal-flow diagram |
| `v7_sections.src.html` | the four new sections, with `<!--#figN#-->` markers |
| `v7_splice.py` | fills the markers, inserts the CSS and the sections, and applies every tense/verdict edit to both files |

🛑 **`{{FRICTION}}` is a deliberate literal placeholder** and appears three times in the page
(diagram label, config block, symptom table). The orchestrator substitutes the chosen
`SteerFriction` value by find-and-replace after the describing-function check. `render.py` will
report it as an unreplaced key; that is expected.

**Every v7 number is transcribed from a measurement file, never from a script's constants:**
`rlog-tools/studies/grind/V293-FLIGHT-READ-r70-2026-09-13.txt` ·
`rlog-tools/studies/grind/V293-PLANT-IDENT-2026-09-13.md` ·
`docs/research/FORK-LATERAL-PATH-V293-2026-09-13.md` §4 ·
`docs/research/DESIGN-NOTE-INNER-LOOP-QUANTITY-2026-09-13.md` ·
`docs/handoffs/2026-09/HANDOFF-2026-09-13-v293-flew-plant-is-a-spring.md` §8.

## The reader is deliberately independent of the kit's ledger

`analysis-2020accord/studies/ledger/ledger_v38_to_v84_bytes.py` hard-codes a V38–V84 build list and a
different cell set, so it could not produce this matrix. `v293_page_data.py` is a **second
implementation of the same conventions** (flat 1 MiB images, file offset == firmware address, LE,
`[npt:u16][X×npt][Y×npt]` records, the firmware's truncating integer LERP).

**Anchors asserted before any value is used:** stock `0xC646C` = 891 · stock `0x454FE` = 0xBA ·
V282 `0x2A1F0` = 0x7CD0 · V282 `0xC63E8` = 923.

**Positive controls it passes:** it reproduces `build_v293_tva.py`'s own published §2b V282 surface
table at all six demand indices, plus 2505, 417, the output-lag DC 0.990234375 and the feedback DC
30.8911.

## Reading the surface numbers

`T_ceil` is the docstring convention (clamp → gain → output clamp). `T_ss` is the full byte-exact
steady state through the ×254/256 fade and the output lag from its cold state, and it is **1.8 % lower**.
🛑 **2505 is a clamp ceiling and is never delivered.** The delivered rail is **2461**, and it is an
**at-rest** figure — the live fade's speed half derates the whole surface as its axis rises, identically
on V282 and V293.
