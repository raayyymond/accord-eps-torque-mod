  <div class="advrow pass">
    <div class="advhead"><span class="advid">B</span><span class="advname">Unit and scale chain, closed-loop stability</span><span class="chip ev">B1 B3 B4 B5 B7 PASS</span><span class="chip risk">B2 B6 FAIL AS WRITTEN</span></div>
    <p><b>B1, the pole census: PASS at 2,048 &#8212; and the dose choice decided it.</b> Unstable fits in torque mode on the V282-pole-only family: <b>2,048 gives 0 and 0</b> at the two disputed effective arms, against 4,451&#8217;s <b>5</b> and 0, and V282&#8217;s own 7 and 2. On the better-constrained family the worst plant reads &#950; <b>+0.161</b> against V282&#8217;s &#8722;0.005. <b>Had the design study&#8217;s recommended 4,451 been built, B1 would have failed.</b> The literal &#8220;&#950; &lt; 0.05&#8221; clause condemns flown V282 on 250 of 250 plants, so it was scored on its intent: no unstable fit, and no worse than the car.</p>
    <p><b>B3, the surface: PASS.</b> Rail <b>&#215;1.000000</b>, P first rails at demand index 239.</p>
    <p><b>B4, the strong-turn ripple: PASS, and it is the thinnest margin in the whole pass.</b> Tap ripple over level on loaded turns reads 0.028&#8211;0.048 against a 0.25 gate, with <b>V293 sitting between stock and V282</b> rather than outside them. Predicted F7 is about <b>1.24 per 100&nbsp;s against a threshold of 2</b> &#8212; a margin of only &#215;1.6, on a nonlinear mapping.</p>
    <p><b>B5, the 5&#8211;9 Hz rise: PASS at 2,048, and both legs were needed.</b> The band rises <b>&#215;1.50&#8211;1.59</b> against V282 and <b>&#215;1.05&#8211;1.13</b> against stock&#8217;s own engaged loop; neither leg of the two-leg gate trips. <b>At 4,451 the first leg trips on r39.</b> The rise is broadband &#8212; peakiness is unchanged &#8212; so this is lost disturbance rejection, not a new mode.</p>
    <p><b>B7, the shoulder: PASS.</b> Zero of 250 plants carry a pole under 0.10 damping in 10&#8211;18&nbsp;Hz, and the 13&#8211;17&nbsp;Hz band reads <b>&#215;1.06</b> at worst against a &#215;1.5 gate. V292&#8217;s rejected reading on that same band was &#215;1.9&#8211;2.1.</p>
    <p><b>B8, reported and not gated:</b> the command-driven 18&#8211;22&nbsp;Hz torque is <b>&#215;0.055&#8211;0.137</b> of V282&#8217;s ring <b>and has no pole, so it cannot ring.</b> That is the residual the operator may still feel with the loop open, and it is an order of magnitude down.</p>
  </div>

  <div class="advrow fail">
    <div class="advhead"><span class="advid">B2</span><span class="advname">The ring &#8212; the one dissent</span><span class="chip risk">FAIL AS WRITTEN &#183; adjudicated PASS on intent</span></div>
    <p>The clause demands the replayed 18&#8211;22&nbsp;Hz ring at or under <b>&#215;0.50</b> of V282&#8217;s, <em>after calibrating the predictor on V292</em>. The readings do not agree, and every one is printed because the choice between them <em>is</em> the decision.</p>
    <div class="tblwrap">
    <table>
      <thead><tr><th>reading</th><th class="n">ring vs V282</th><th>against the &#8804; &#215;0.50 gate</th></tr></thead>
      <tbody>
        <tr><td><b>Calibrated on V292</b>, as the clause specifies</td><td class="n">&#215;0.54 &#8211; 1.47</td><td><b>FAIL</b></td></tr>
        <tr><td>Uncalibrated replay</td><td class="n">&#215;0.285 / &#215;0.403</td><td>PASS</td></tr>
        <tr><td>Calibrated on the car&#8217;s own open-loop configuration</td><td class="n">&#215;0.47 / &#215;0.66</td><td>mixed</td></tr>
        <tr><td><b>The on-car anchor</b>, no predictor, independently re-derived</td><td class="n">&#215;0.237 / &#215;0.285 / &#215;0.265</td><td>PASS</td></tr>
      </tbody>
    </table>
    </div>
    <p><b>Why it was adjudicated PASS on intent.</b> The mandated calibration factor was measured on V292 &#8212; <b>a build that did not open the loop.</b> The fit family&#8217;s error there is in how a feedback pole reshapes the return ratio at 20&nbsp;Hz, and <b>that error has no channel when the operand is identically zero</b>: the code region is byte-identical and the clamp is a symmetric &#177;C clamp, so a return ratio of zero is an identity the bytes prove rather than a fit. Transferred to the one fully-open-loop configuration this car has actually been measured in, <b>that same calibration over-predicts the measured ring by &#215;1.3 to &#215;2.0 &#8212; the calibrated predictor fails a measured case.</b> On the clause&#8217;s intent, that the ring at least halves, the direct on-car reading is &#215;0.24&#8211;0.29 and the command-driven residual &#215;0.06&#8211;0.14, both evidence rather than model.</p>
    <p><b>The literal FAIL and its numbers stay in the table above as the dissent</b>, and the V292 precedent at the head of this page is why they stay.</p>
  </div>

  <div class="advrow fail">
    <div class="advhead"><span class="advid">B6</span><span class="advname">The outer loop &#8212; a broken check that fires cleanly</span><span class="chip risk">FAIL AS WRITTEN &#183; PASS on intent</span></div>
    <p>Re-scored at the delay <em>measured on this car</em> rather than an assumed one, V293 under the repaired preset breaks <b>3 of 10</b> controller-loop cells, worst phase margin <b>33.2&#176;</b> at 5&nbsp;m/s. <b>Flown V282, at the tune it is actually driven with, breaks 3 of 10 too</b>, worst <b>35.6&#176;</b> at 28.5&nbsp;m/s. On the path-following channel both go unstable inside the clause&#8217;s plant-gain range.</p>
    <p><b>A check that condemns the build already on the car, by the same count, is a broken check</b> &#8212; the kit&#8217;s own standing rule &#8212; so it was scored on its intent: V293&#8217;s outer loop is no worse than the car&#8217;s. The friction repair is worth <b>&#215;1.58</b> on the gain metric, and it is what makes that true.</p>
    <p><b>The residual is named, and it is the thing to watch.</b> At 5&nbsp;m/s the creep margin is only <b>10&#8211;20&nbsp;% of plant gain on BOTH builds</b>, and the failure mode there is the V276 1&#8211;4&nbsp;Hz signature. <b>That is the first revert trigger, at low speed, before anything else.</b></p>
  </div>
