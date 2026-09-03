---
name: feedback-attribute-the-build-from-the-tap-not-from-the-label
description: 2026-09-02 -- the operator filed r32/r33 as "driven on V278"; the CAN-427 tap showed the V280 rev 2 line map (lane pushing at 143-155 deg/s where rev 3 brakes above 44.5). One agent modelled the whole drive under the wrong map before the sibling caught it. Before any drive analysis, ATTRIBUTE THE BUILD FROM THE WIRE (push/brake crossover rate at full demand, chain-mirror corr against every candidate map) and only then model. Also: the same comparison ("smooth on V112") had TWO deltas (V268 base + the map) -- always full-file diff the flown image against the comparison build before naming a cause.
metadata:
  type: feedback
---

# Attribute the build from the tap, not from the label -- 2026-09-02

**Why:** r32/r33 arrived labelled V278 rev 3. The tap says V280 rev 2 (EVIDENCE: hands-light full-demand rate p90
143-155 deg/s with the lane pushing; under x2 the lane brakes above 44.5 deg/s, as r31 showed). An agent modelled the
drive under x2 and read "wheel above reference, fb clamp 26-90 %" -- a wrong model that a sibling agent's chain-mirror
census (corr per candidate map) exposed. The full-image diff also showed the operator's "V112 vs now" comparison carried
V268's base-assist edit as a second delta that V112 never had.

**How to apply:** first step of every drive read = build attribution from the wire (push/brake crossover at idx>=200,
chain-mirror corr against every candidate map, max field) and a full-file diff of the flown image against the comparison
build. State both in the report header before any number. If the label and the wire disagree, the wire wins and the operator
is asked to confirm.

Related: [[feedback-diff-against-the-flown-image-not-stock]], [[accord-lanechange-ring-is-the-outer-loop-the-map-never-touches-the-eps-rate-feedback-gain]].
