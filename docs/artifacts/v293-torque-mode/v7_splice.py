# -*- coding: utf-8 -*-
"""Version 7 of the V293 close-out page: V293 FLEW (route 70), the plant, the rev-2 fork side.

Applies the SAME edits to the rendered page and to the template, so the two stay in sync
(the data-json regeneration is known to time out; the page is edited directly).
Idempotent: refuses to run twice on an already-spliced file.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
TARGETS = [HERE / "v293-torque-mode.html", HERE / "page.tmpl.html"]

# ---------------------------------------------------------------- figures -> sections
figsrc = (HERE / "v7_figs.frag").read_text(encoding="utf-8")
FIGS = {}
for blk in figsrc.split("<!--#")[1:]:
    key, _, body = blk.partition("#-->")
    FIGS[key] = body.strip()
SECTIONS = (HERE / "v7_sections.src.html").read_text(encoding="utf-8")
for k, v in FIGS.items():
    SECTIONS = SECTIONS.replace(f"<!--#{k}#-->", v)
assert "<!--#" not in SECTIONS, "unfilled figure marker"

# ---------------------------------------------------------------- new CSS
CSS = """
/* --- v7: the flight, the plant, the rev-2 fork side ------------------------ */
:root{--plant:#0F7A5F;--plantsoft:rgba(15,122,95,.12);--cmt:#7C8296}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){
  --plant:#47C79B;--plantsoft:rgba(71,199,155,.14);--cmt:#767C92}}
:root[data-theme="dark"]{--plant:#47C79B;--plantsoft:rgba(71,199,155,.14);--cmt:#767C92}
.aplant{stroke:var(--plant)} .kn.plant{fill:var(--plant)}
blockquote.opquote{border-left-width:5px;border-left-color:var(--v293);background:var(--pendbg);
  font-style:normal;padding:16px 20px;margin:26px 0 0;max-width:72ch}
blockquote.opquote p{font-family:var(--serif);font-size:17px;line-height:1.5;font-style:italic}
blockquote.opquote p+p{margin-top:10px}
blockquote.opquote .attrib{font-family:var(--sans);font-size:11.5px;font-style:normal;
  letter-spacing:.1em;text-transform:uppercase;color:var(--ink-mut);margin-top:14px}
tr.hl td{background:var(--surface-2);font-weight:600}
figure+.col,.duo+.col,.tblwrap+.col,pre+.col,.kv+.col,.cards+.col{margin-top:30px}
blockquote .after{font-style:normal;font-size:14.5px;color:var(--ink-mut);margin-top:12px;
  padding-top:10px;border-top:1px solid var(--rule-soft)}
blockquote .after b{color:var(--ink)}
pre .cmt{color:var(--cmt)}
.flow2{display:block;width:100%;height:auto;min-width:1060px}
.flow2 .n2{fill:var(--nodefill);stroke:var(--noderule);stroke-width:1.2}
.flow2 .n2.op{fill:var(--opfill)}
.flow2 .n2.edit{fill:var(--editfill);stroke:var(--v293);stroke-width:1.6}
.flow2 .n2.plant{fill:var(--plantsoft);stroke:var(--plant);stroke-width:1.6}
.flow2 .bt{fill:var(--ink);font-family:var(--sans);font-size:13px;font-weight:700}
.flow2 .bs{fill:var(--ink-mut);font-family:var(--mono);font-size:10.5px}
.flow2 .bl{fill:var(--ink-mut);font-family:var(--sans);font-size:10.5px;font-weight:700;letter-spacing:.09em}
.flow2 .bandbar{fill:var(--surface-2)}
.flow2 .fl{fill:none;stroke:var(--flow);stroke-width:1.5}
.flow2 .fl.fb{stroke-dasharray:6 4}
"""

# ---------------------------------------------------------------- targeted edits
EDITS = [
    # ---- masthead ----------------------------------------------------------
    ('<p class="eyebrow">2020 Honda Accord &#183; EPS 39990-TVA-A160 &#183; close-out artifact '
     '&#183; 13 Sep 2026</p>',
     '<p class="eyebrow">2020 Honda Accord &#183; EPS 39990-TVA-A160 &#183; close-out artifact '
     '&#183; Version 7 &#8212; V293 flew &#183; 13 Sep 2026</p>'),

    ('<p class="dek">Five calibration cells clamp the LKAS rate feedback to exactly zero. '
     'The EPS stops being a rate servo and becomes a torque map: what openpilot commands is '
     'what the motor delivers, whatever the wheel is doing.</p>',
     '<p class="dek">Five calibration cells clamp the LKAS rate feedback to exactly zero. '
     'The EPS stops being a rate servo and becomes a torque map: what openpilot commands is '
     'what the motor delivers, whatever the wheel is doing. <b>It flew on 13 September, and '
     'the car underneath turned out to be a spring.</b></p>'),

    # ---- the verdict block -------------------------------------------------
    ('''  <div class="verdict cleared">
    <p class="vlbl">Verdict &#8212; CLEARED as the flight candidate, over one dissent</p>''',
     '''  <div class="verdict cleared">
    <p class="vlbl">Verdict &#8212; FLEW 13 September 2026, route 70</p>'''),

    ('<p class="vtxt"><b>V293 is CLEARED as the flight candidate over ONE dissent (B2 as '
     'written).</b> A, C and D <b>PASS</b>, with D1&#8217;s dwell residual named. B1, B3, B4, '
     'B5 and B7 <b>PASS</b>; B6 is a <b>broken-check PASS</b>. <b>V282 is the fallback.</b></p>',
     '<p class="vtxt"><b>19 segments, 1,135.7&#8239;s, 858&#8239;s laterally engaged.</b> The '
     'edit is confirmed live on the wire: <code>|CAN&nbsp;427 tap|</code> is an exact function '
     'of demand and fade with <b>R&#178; 0.986</b> and no wheel-rate term, and the tune read '
     '<b>Kp 0.3000 on 77,863 control-path frames</b>. <b>One pre-registered REVERT trigger '
     'fired</b> &#8212; a coherent 1&#8211;4&#8239;Hz line in command and angle at 0&#8211;5&#8239;m/s '
     '&#8212; and the ring clause missed its threshold by 8&#160;%.</p>'),

    ('<p class="vtxt"><b>The fork side is mandatory, not advisory</b> &#8212; <b>the Galaxy '
     'toggle config <code>toggle-config_V293_torque_mode.json</code> restored</b>, which '
     'carries lat-accel factor 6.0, <b>friction 0.00</b>, Kp 0.3, Ki 0.15 and the rate-plant '
     'feedforward bypassed &#8212; existing sliders, no fork code. <b>The first drive is an '
     'identification drive.</b> <b>A 1&#8211;4&nbsp;Hz line at low speed is the first revert '
     'trigger.</b></p>',
     '<p class="vtxt"><b>The operator: no classic grinding or stuttering, and a new symptom '
     '&#8212; the wheel &#8220;snapped between angles rather than smoothly moving between '
     'them&#8221;, with looseness, oversteer and overshoot-then-correct.</b> The drive was an '
     'identification drive and it identified the plant: <b>a spring plus Coulomb friction</b>, '
     'not the integrator every tune before it assumed. <b>The firmware stays. The fork side is '
     'rebuilt around the measured plant</b> &#8212; that is rev&#8239;2, below.</p>'),

    ('<p class="vtxt"><b>The decision to fly is the operator&#8217;s. Nothing here says the '
     'grinding or the stutter is fixed</b> &#8212; this page scores bands; he scores the '
     'symptom.</p>',
     '<p class="vtxt"><b>Nothing here says the grinding is fixed</b> &#8212; this page scores '
     'bands; the operator scores the symptom, and his three sentences are printed at the top '
     'of the drive section rather than paraphrased anywhere.</p>'),

    # ---- the precedent block ----------------------------------------------
    ('<p class="vlbl">And the precedent, stated rather than hidden</p>',
     '<p class="vlbl">What the pre-flight clearance got right, and what it got wrong</p>'),

    ('<p class="vtxt"><b>V292 was also cleared over one dissent, and then failed on the wire on '
     'clauses the model had passed.</b> That is exactly why this candidate&#8217;s ring claim '
     'rests on <b>the car&#8217;s own open-loop measurement</b> and not on the replay &#8212; '
     'and why the dissent below is printed in full rather than summarised away.</p>',
     '<p class="vtxt"><b>Right:</b> the identity, every attribution gate, F7 and the tap ripple, the 13&#8211;17&#8239;Hz '
     'shoulder, and the predicted &#215;1.5 rise in the 5&#8211;9&#8239;Hz band, which measured '
     '&#215;1.61. <b>Wrong:</b> the ring was predicted at &#215;0.28 and measured &#215;0.434 on '
     'amplitude &#8212; the replay machinery over-promised for the second build running. <b>And '
     'the residual that was named on this page as the first thing to watch is the one that '
     'fired.</b> The low-speed 1&#8211;4&#8239;Hz margin was carried as RESIDUAL, NOT CLOSED, '
     'and it was right to be.</p>'),

    ('<p class="vtxt">What the build <em>is</em> is settled: <b>torque mode &#8212; V279&#8217;s '
     'structure, which was built on 2&nbsp;September and never flown, rebased onto V282.</b> '
     'It is not a new lever. What is new is the base, the r24 dose, and the fork preset that '
     'flies it.</p>',
     '<p class="vtxt">The build itself is unchanged and stays on the car: <b>torque mode '
     '&#8212; V279&#8217;s structure, rebased onto V282.</b> Everything rev&#8239;2 changes is '
     'on the openpilot side.</p>'),

    ('<p class="supersede"><span class="chip risk">V292 &#8212; REVERT</span> <span>V292 flew on '
     'three routes today and hit two of its own pre-registered revert signatures. <b>The '
     'operator: grinding still present, stutter worse.</b> That flight read is what V293 '
     'answers; it is summarised below.</span></p>',
     '<p class="supersede"><span class="chip new">V293 &#8212; ON THE CAR</span> <span>Route 70, '
     '13 September. <b>The classic grinding did not appear; a ratchet did.</b> '
     '<span class="chip risk">V292 &#8212; REVERTED</span> V292 flew on three routes the same '
     'day and hit two of its own revert signatures; that read is what V293 answered, and it is '
     'kept below.</span></p>'),

    # ---- the pre-flight risk section, retensed -----------------------------
    ('<h2>The risk, before the drive</h2>\n    <p>Stated here so it is on the page and not only '
     'in a review file. <strong>This build raises the band the operator complained about '
     'today.</strong> It is a prediction, not a hazard the build merely tolerates.</p>',
     '<h2>The risk stated before the drive, and what route 70 did with each</h2>\n    <p>Kept '
     'as written, because a prediction is only worth what it is worth after the fact. '
     '<strong>Three of the four held. The fourth is the one that stopped the drive.</strong> '
     'The rev-2 section above is what follows from that.</p>\n    <div class="tblwrap">'
     '<table><caption class="eyebrow" style="text-align:left;padding-bottom:6px">predicted '
     '&#8594; measured on route 70</caption><thead><tr><th>prediction</th><th class="n">said'
     '</th><th class="n">measured</th><th>reading</th></tr></thead><tbody>'
     '<tr><td>5&#8211;9&#8239;Hz wheel motion rises</td><td class="n">&#215;1.74</td>'
     '<td class="n">&#215;1.61</td><td><span class="chip ev">HELD</span> broadband, no resonant '
     'line</td></tr>'
     '<tr><td>18&#8211;22&#8239;Hz ring falls</td><td class="n">&#215;0.28</td>'
     '<td class="n">&#215;0.434</td><td><span class="chip risk">MISSED</span> the gate was '
     '&#8804;&#8239;0.40; presence fell 9&#215; though</td></tr>'
     '<tr><td>7.3&#8239;Hz ripple stays down</td><td class="n">gate 0.465</td>'
     '<td class="n">F7 0.00</td><td><span class="chip ev">HELD</span> and tap ripple 0.008 of a '
     '0.25 allowance</td></tr>'
     '<tr><td>low-speed creep margin</td><td class="n">10&#8211;20&#160;%</td>'
     '<td class="n">3.55&#176; line</td><td><span class="chip risk">FIRED</span> the V276 '
     'signature, exactly where it was named</td></tr>'
     '</tbody></table></div>'),

    ('<h3>The first drive is an identification drive, not a symptom drive</h3>',
     '<h3>It was an identification drive, and this is what it was asked to do</h3>'),

    ('<h3>What one short symptomatic episode has to show</h3>',
     '<h3>What one short symptomatic episode had to show &#8212; and did</h3>'),

    # ---- the null-sentence blockquote --------------------------------------
    ('<b>the whole in-loop class, V38 through V293 &#8212; shaping, notching, pole-moving and '
     'opening &#8212; is closed.</b></p></blockquote>',
     '<b>the whole in-loop class, V38 through V293 &#8212; shaping, notching, pole-moving and '
     'opening &#8212; is closed.</b></p><p class="after"><b>It did not fire.</b> The identity '
     'held and the ring did not stay unchanged &#8212; amplitude &#215;0.434, presence a ninth. '
     'The class is not closed; the ring is mostly the loop&#8217;s after all.</p></blockquote>'),

    # ---- footer ------------------------------------------------------------
    ('<p><b>Nothing on this page was flashed, driven, or sent on any bus.</b> No CAN or UDS '
     'message was transmitted. The V293 image and its <code>.rwd</code> are build artifacts; '
     'the flash is the operator&#8217;s decision and is gated on the adversarial pass returning '
     'clear.</p>',
     '<p><b>V293 was flashed by the operator and driven on route 70 on 13 September 2026.</b> '
     'No CAN or UDS message was sent by any agent, and nothing on the rev-2 side has been '
     'applied &#8212; it is a configuration proposal with one value still open. <b>The decision '
     'to drive it is the operator&#8217;s.</b></p>'),

    ('Sources: <span class="mono">ADVERSARIAL-V293-PREREG-2026-09-13.md</span>',
     'Flight-read and plant sources: <span class="mono">V293-FLIGHT-READ-r70-2026-09-13.txt'
     '</span> &#183; <span class="mono">V293-PLANT-IDENT-2026-09-13.md</span> &#183; '
     '<span class="mono">FORK-LATERAL-PATH-V293-2026-09-13.md</span> &#183; '
     '<span class="mono">DESIGN-NOTE-INNER-LOOP-QUANTITY-2026-09-13.md</span> &#183; '
     '<span class="mono">HANDOFF-2026-09-13-v293-flew-plant-is-a-spring.md</span>. '
     'Build sources: <span class="mono">ADVERSARIAL-V293-PREREG-2026-09-13.md</span>'),

    # ---- adversarial pass: one open question the drive settled -------------
    ('<strong>Two surfaces returned a literal FAIL.</strong></p>',
     '<strong>Two surfaces returned a literal FAIL.</strong> <b>And the drive settled one of the '
     'questions it left open.</b> Adversary A flagged the live fade&#8217;s axis as OPEN &#8212; '
     'the record reads it by <code>|bar|&gt;&gt;5</code>, A read it as km/h. With the loop open '
     'the tap <em>is</em> the surface, so the identity regression adjudicates: the bar axis '
     'returns R&#178; <b>0.986</b> and the speed axis <b>0.417</b> on the same frames. '
     '<span class="chip ev">RESOLVED &#8212; the bar axis</span></p>'),
]

EXTRA_CSS_ANCHOR = "@media (max-width:560px){"
SECTION_ANCHOR = '<section>\n  <div class="col">\n    <p class="eyebrow">What the build does</p>'


def splice(path: Path) -> str:
    src = path.read_text(encoding="utf-8")
    if 'id="drive"' in src:
        sys.exit(f"{path.name}: already spliced, refusing")
    # 1. CSS
    assert src.count(EXTRA_CSS_ANCHOR) == 1, "css anchor"
    src = src.replace(EXTRA_CSS_ANCHOR, CSS.strip() + "\n" + EXTRA_CSS_ANCHOR)
    # 2. new sections, ahead of "What the build does"
    assert src.count(SECTION_ANCHOR) == 1, "section anchor"
    src = src.replace(SECTION_ANCHOR, SECTIONS.rstrip() + "\n\n" + SECTION_ANCHOR)
    # 3. targeted edits
    miss = []
    for old, new in EDITS:
        if src.count(old) != 1:
            miss.append((src.count(old), old[:70]))
            continue
        src = src.replace(old, new)
    if miss:
        for n, o in miss:
            print(f"   !! {n} hits: {o}")
        sys.exit("edit anchors failed")
    return src


for t in TARGETS:
    out = splice(t)
    t.write_text(out, encoding="utf-8")
    print(f"wrote {t.name}  {len(out.encode('utf-8')):,} bytes")
