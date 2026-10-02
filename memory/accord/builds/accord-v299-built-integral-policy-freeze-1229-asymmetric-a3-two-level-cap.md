---
name: accord-v299-built-integral-policy-freeze-1229-asymmetric-a3-two-level-cap
description: "V299 BUILT 2026-10-02, VERIFIED, NOT FLOWN: V298 + 67 bytes, all inside V298's cave at 0xC4C00 + F181 + CRC (no relink, 0 RAM): hard-freeze 512→1229 (= Honda's 1200-count steeringPressed level), the opposing-hand 300 clause REMOVED, the A3 integral bound ASYMMETRIC (toward centre = 1250 S), the cap TWO-LEVEL (4096 S ≤ 6 m/s, 6144 S at 6–12.5 m/s, none above), F181 39990-TVA,A16B; image sha 30ff05fa…, rwd sha 4ecdab83… (header A110/A160/A16A/A16B); golden _self_check_v299 (95 symbols, hash unchanged), H1 0 mismatches, CRC 50/50 + 49/49, four adversarial lenses PASS_WITH_DEFECTS (none a flash blocker); V299 RAISES NO CEILING — the 6–12.5 m/s integral ceiling falls 53→40 % of rail; the authority gain is the integral's duty (r79 replay: discarded integration 28.3→0.8 %, toggles 325→13 /min) and no setpoint snap; fork Dom c6452361 (local): NO override (operator ruling), bar from 0x1AB, A16 family detection, AccordAngle* params; config A = drive 2, config B (cap 250 alone) optional later; drive-2 card + instrument ready"
metadata:
  type: reference
---

Design `docs/specs/design/v299/DESIGN-V299-SYNTHESIS-rev3-2026-10-02.md` (judge panel: 5 designers → 3 scorers → 3 judges →
ONE Fable 5.1 synthesis → 3 refuters → rev 2 + 3 re-refuters → rev 3); build `analysis-2020accord/builds/v108_plus/build_v299_tva.py`;
verification `analysis-2020accord/studies/angle_loop/v299_build/` (MIRROR-H1, adversarial/, fork-review/, INSTRUMENT-V299.md);
card `docs/scoring/DRIVE-CARD-V299-drive2-2026-10-02.md`; page https://claude.ai/artifact/C1N9L3hj5utWWyQyMrz1nz.

**Why these bytes:** route 79 showed the V298 freeze (512 / opposing 300) firing on the hands-off reaction twist (torque word p90
607–681 below 8 m/s) — the measured ratchet (stall-surges enriched 2.7–5.6× at the crossings) and the lost integral (26–37 %
discarded). Rejected on evidence: Kp ×1.5/×2 (PM −10/−20°), A3 cap 8192 (overshoot 12°), raising the lane rail (unreplayed EME
band), cap 250 + clip ×1.6 together (re-arms the twist relay through the fork's debounce). A single 4-byte cap tripped F4 at 3 m/s,
hence the two-level cap.

**Declared costs (BELIEF until drive 2):** moderate-hand band 550–1150 counts holds 37–63 % of rail against a drag at 5–8 m/s
(no fork override; F7b observation, R9 decides); outward light co-steer release swing up to ~10° on the heavy plant member
(F3 bars 12/9/8/5° by band); 6144-cap curve-hold shortfall 3–7° at 8–10 m/s on 2.5 m/s² holds (null sentence licenses 7168);
low-speed overshoot ≤ 7° on 20–45° turns at ≤ 4.5 m/s (F4b 8.5°); the cap never lowers an integral carried above it when
braking into a turn (inherited, V299 ≤ V298). Not addressed: small-correction stick-slip, highway authority.

**Process:** the builder was classifier-stopped; the mirror agent (briefed to continue) built the image; the interlocks lens was
stopped twice while writing and the orchestrator adjudicated it from the lens's own scripts.
Related: [[accord-v298-flew-route79-loop-live-freeze-and-o1-fire-on-reaction-twist]],
[[feedback-no-fork-override-in-the-angle-interface-rely-on-the-eps-fade]],
[[feedback-goal-criterion-1-6-3hz-replaced-by-stutter-readouts]].
