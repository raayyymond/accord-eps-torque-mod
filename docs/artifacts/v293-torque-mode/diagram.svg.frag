<div class="figbody"><svg viewBox="0 0 1260 1080" role="img" class="flow" aria-label="Signal-flow diagram of the 2020 Accord EPS chain under V293 torque mode: openpilot's torque controller commands 0xE4, which becomes a demand index and then a setpoint through the unchanged assist map; the error is 32 times the setpoint minus a feedback operand that V293 clamps to exactly zero; P uses Kp flattened from 248 to 120, D is zero by both Kd and its clamp, the sum passes a fade and clamps through a gain of 5346 to the delivered lane torque; the r24 rate lane's arm is cut from 5244 to 2048 before the aggregator, governor, shaper and motor">
<defs>
  <marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--flow)"/></marker>
  <marker id="ahE" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="var(--v293)"/></marker>
</defs>

<!-- BAND 1 : openpilot -->
<text x="40" y="22" fill="var(--ink-mut)" font-family="var(--sans)" font-weight="700" letter-spacing=".09em" font-size="10.5">BAND 1 &#183; OPENPILOT &#8212; WHAT IT COMMANDS IS A TORQUE</text>
<rect x="40" y="32" width="274" height="52" rx="4" fill="var(--opfill)" stroke="var(--noderule)" stroke-width="1.2" stroke-dasharray="5 4"/>
<text x="177" y="54" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">modeld</text>
<text x="177" y="71" text-anchor="middle" fill="var(--ink-mut)" font-size="11" font-family="var(--mono)">20 Hz desiredCurvature</text>
<rect x="340" y="32" width="500" height="52" rx="4" fill="var(--opfill)" stroke="var(--v293)" stroke-width="2" stroke-dasharray="5 4"/>
<text x="590" y="54" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">LatControlTorque &#8212; AccordEpsTorqueMode ON</text>
<text x="590" y="71" text-anchor="middle" fill="var(--ink-mut)" font-size="11" font-family="var(--mono)">rate-plant FF OFF &#183; LAF 6.0 &#183; Kp 0.3 &#183; Ki 0.15</text>
<rect x="866" y="32" width="230" height="52" rx="4" fill="var(--opfill)" stroke="var(--noderule)" stroke-width="1.2" stroke-dasharray="5 4"/>
<text x="981" y="54" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">0xE4 STEER_TORQUE</text>
<text x="981" y="71" text-anchor="middle" fill="var(--ink-mut)" font-size="11" font-family="var(--mono)">100 Hz &#183; &#177;4096</text>
<polyline points="314,58 340,58" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<polyline points="840,58 866,58" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<text x="1112" y="50" fill="var(--v293)" font-size="11.5" font-weight="700" font-family="var(--sans)">expects TORQUE</text>
<text x="1112" y="66" fill="var(--ink-mut)" font-size="10.5" font-family="var(--mono)">V293 delivers</text>
<text x="1112" y="79" fill="var(--ink-mut)" font-size="10.5" font-family="var(--mono)">T = f(cmd)&#183;fade</text>

<!-- BAND 2 : reference path -->
<text x="40" y="120" fill="var(--ink-mut)" font-family="var(--sans)" font-weight="700" letter-spacing=".09em" font-size="10.5">BAND 2 &#183; EPS REFERENCE PATH &#8212; THE DEMAND BECOMES A SETPOINT (UNCHANGED)</text>
<rect x="40" y="130" width="222" height="52" rx="4" fill="var(--nodefill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="151" y="152" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">gp&#8722;0x69ae</text>
<text x="151" y="169" text-anchor="middle" fill="var(--ink-mut)" font-size="11" font-family="var(--mono)">clamp(&#8722;4&#183;wire, &#177;0x4000)</text>
<rect x="288" y="130" width="236" height="52" rx="4" fill="var(--nodefill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="406" y="152" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">demand index idx</text>
<text x="406" y="169" text-anchor="middle" fill="var(--ink-mut)" font-size="11" font-family="var(--mono)">&#247;16.125736 &#183; cap 240</text>
<rect x="550" y="118" width="264" height="106" rx="4" fill="var(--nodefill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="682" y="137" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">assist map 0xE502C</text>
<g transform="translate(634,146)">
  <rect x="-2" y="-2" width="100" height="48" fill="var(--surface-2)" stroke="var(--rule-soft)" stroke-width="1"/>
  <polyline points="{{mini.map_stock}}" class="ln thin astock"/>
  <polyline points="{{mini.map_v282}}" class="ln thin a293"/>
</g>
<text x="682" y="215" text-anchor="middle" fill="var(--ink-mut)" font-size="10.5" font-family="var(--mono)">UNCHANGED &#183; linear 4.30/idx to 1032</text>
<rect x="840" y="130" width="120" height="52" rx="4" fill="var(--nodefill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="900" y="161" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">setpoint sp</text>
<circle cx="1056" cy="156" r="21" fill="var(--nodefill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="1056" y="163" text-anchor="middle" fill="var(--ink)" font-size="18" font-weight="600" font-family="var(--sans)">&#931;</text>
<polyline points="981,84 981,104 24,104 24,156 40,156" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<text x="500" y="100" text-anchor="middle" fill="var(--ink-mut)" font-size="10.5" font-family="var(--mono)">the 0xE4 command, into the ECU</text>
<polyline points="262,156 288,156" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<polyline points="524,156 550,156" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<polyline points="814,156 840,156" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<polyline points="960,156 1035,156" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<text x="998" y="148" text-anchor="middle" fill="var(--ink-mut)" font-size="10.5" font-family="var(--mono)">&#215;32</text>
<text x="1090" y="120" fill="var(--ink-mut)" font-size="11.5" font-family="var(--mono)">E = 32&#183;sp &#8722; fb</text>
<text x="1090" y="136" fill="var(--v293)" font-size="12" font-weight="700" font-family="var(--mono)">&#8594; E = 32&#183;sp</text>

<!-- BAND 3 : the PID -->
<text x="40" y="262" fill="var(--ink-mut)" font-family="var(--sans)" font-weight="700" letter-spacing=".09em" font-size="10.5">BAND 3 &#183; THE RATE PID &#8212; EDITS 2 AND 3 LAND HERE</text>
<rect x="40" y="272" width="300" height="106" rx="4" fill="var(--editfill)" stroke="var(--v293)" stroke-width="2.2"/>
<text x="190" y="291" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">P = (E&#183;Kp) &gt;&gt; 8, clamp 15,360</text>
<g transform="translate(142,300)">
  <rect x="-2" y="-2" width="100" height="48" fill="var(--surface)" stroke="var(--rule-soft)" stroke-width="1"/>
  <polyline points="{{mini.kp_stock}}" class="ln thin astock"/>
  <polyline points="{{mini.kp_v282}}" class="ln thin a282"/>
  <polyline points="{{mini.kp_v293}}" class="ln thin a293"/>
</g>
<rect x="40" y="355" width="300" height="19" rx="9.5" fill="var(--v293)"/>
<text x="190" y="369" text-anchor="middle" fill="var(--on-bar)" font-size="10.5" font-weight="700" font-family="var(--mono)">0xCB994 &#183; Kp 248 &#8594; 120, all 28 records</text>
<rect x="366" y="272" width="300" height="106" rx="4" fill="var(--editfill)" stroke="var(--v293)" stroke-width="2.2"/>
<text x="516" y="291" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">D = (&#916;E&#183;Kd) &gt;&gt; 3, clamp</text>
<g transform="translate(468,300)">
  <rect x="-2" y="-2" width="100" height="48" fill="var(--surface)" stroke="var(--rule-soft)" stroke-width="1"/>
  <polyline points="{{mini.kd_v282}}" class="ln thin a282"/>
  <polyline points="{{mini.kd_v293}}" class="ln thin a293"/>
</g>
<rect x="366" y="355" width="300" height="19" rx="9.5" fill="var(--v293)"/>
<text x="516" y="369" text-anchor="middle" fill="var(--on-bar)" font-size="10.5" font-weight="700" font-family="var(--mono)">Kd 128 &#8594; 0  AND  0xC61B6 10,240 &#8594; 0</text>
<rect x="692" y="298" width="220" height="52" rx="4" fill="var(--nodefill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="802" y="320" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">I &#8212; Ki = 0</text>
<text x="802" y="337" text-anchor="middle" fill="var(--ink-mut)" font-size="11" font-family="var(--mono)">0xC63E6, Honda ships it off</text>
<circle cx="1000" cy="324" r="21" fill="var(--nodefill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="1000" y="331" text-anchor="middle" fill="var(--ink)" font-size="18" font-weight="600" font-family="var(--sans)">&#931;</text>
<polyline points="1056,177 1056,238 190,238 190,272" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<polyline points="516,238 516,272" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<polyline points="802,238 802,298" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<text x="640" y="234" text-anchor="middle" fill="var(--ink-mut)" font-size="10.5" font-family="var(--mono)">the error E, to all three terms</text>
<polyline points="190,378 190,392 1000,392 1000,345" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<polyline points="516,378 516,392" fill="none" stroke="var(--flow)" stroke-width="1.6"/>
<polyline points="912,324 979,324" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<text x="1032" y="318" fill="var(--v293)" font-size="11.5" font-weight="700" font-family="var(--mono)">S = P alone</text>
<text x="1032" y="333" fill="var(--ink-mut)" font-size="10.5" font-family="var(--mono)">I &#8801; 0, D &#8801; 0</text>

<!-- BAND 4 : fade, clamps, gain, delivery -->
<text x="40" y="416" fill="var(--ink-mut)" font-family="var(--sans)" font-weight="700" letter-spacing=".09em" font-size="10.5">BAND 4 &#183; FADE, CLAMPS, GAIN, DELIVERY &#8212; ALL UNCHANGED, SO NO RANGE CHANGE ANYWHERE</text>
<rect x="40" y="426" width="270" height="106" rx="4" fill="var(--nodefill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="175" y="445" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">fade &#8594; sum clamp 15,360</text>
<g transform="translate(127,454)">
  <rect x="-2" y="-2" width="100" height="48" fill="var(--surface-2)" stroke="var(--rule-soft)" stroke-width="1"/>
  <polyline points="{{mini.sD}}" class="ln thin a282"/>
  <polyline points="{{mini.taper}}" class="ln thin astock"/>
</g>
<text x="175" y="523" text-anchor="middle" fill="var(--ink-mut)" font-size="10.5" font-family="var(--mono)">&#215;254/256 at rest &#183; byte-stock</text>
<rect x="336" y="452" width="252" height="52" rx="4" fill="var(--nodefill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="462" y="474" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">output lag 992 / 507</text>
<text x="462" y="491" text-anchor="middle" fill="var(--ink-mut)" font-size="11" font-family="var(--mono)">5.05 Hz &#183; DC 0.990234</text>
<rect x="614" y="452" width="252" height="52" rx="4" fill="var(--nodefill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="740" y="474" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">T = (y&#183;5346) &gt;&gt; 15</text>
<text x="740" y="491" text-anchor="middle" fill="var(--ink-mut)" font-size="11" font-family="var(--mono)">clamp &#177;3072 &#183; gain 0xC6CD0</text>
<rect x="892" y="440" width="252" height="76" rx="4" fill="var(--nodefill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="1018" y="461" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">gp&#8722;0x6b38</text>
<text x="1018" y="478" text-anchor="middle" fill="var(--ink-mut)" font-size="11" font-family="var(--mono)">the delivered lane torque</text>
<text x="1018" y="496" text-anchor="middle" fill="var(--v293)" font-size="10.5" font-family="var(--mono)">&#8594; CAN 427, 8 counts/LSB, 50 Hz</text>
<polyline points="1021,324 1150,324 1150,408 175,408 175,426" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<polyline points="310,478 336,478" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<polyline points="588,478 614,478" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<polyline points="866,478 892,478" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>

<!-- BAND 5 : the feedback leg -->
<text x="40" y="570" fill="var(--v293)" font-family="var(--sans)" font-weight="700" letter-spacing=".09em" font-size="10.5">BAND 5 &#183; THE FEEDBACK LEG &#8212; EDIT 1, AND IT NOW RETURNS A HARD ZERO</text>
<rect x="40" y="580" width="222" height="52" rx="4" fill="var(--nodefill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="151" y="602" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">column rate gp&#8722;0x6abe</text>
<text x="151" y="619" text-anchor="middle" fill="var(--ink-mut)" font-size="11" font-family="var(--mono)">8 counts per deg/s</text>
<rect x="288" y="580" width="236" height="52" rx="4" fill="var(--nodefill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="406" y="602" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">gp&#8722;0x6a56</text>
<text x="406" y="619" text-anchor="middle" fill="var(--ink-mut)" font-size="11" font-family="var(--mono)">&#215;1.697754, sat &#177;12000</text>
<rect x="550" y="580" width="264" height="52" rx="4" fill="var(--nodefill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="682" y="600" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">lag filter 923 / 1560, then sum</text>
<text x="682" y="617" text-anchor="middle" fill="var(--ink-mut)" font-size="10.5" font-family="var(--mono)">state gp&#8722;0x3d30 KEEPS RUNNING</text>
<rect x="840" y="566" width="304" height="106" rx="4" fill="var(--editfill)" stroke="var(--v293)" stroke-width="2.2"/>
<text x="992" y="585" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">clamp &#177;[0xC62E6] &#8594; fb</text>
<g transform="translate(944,594)">
  <rect x="-2" y="-2" width="100" height="48" fill="var(--surface)" stroke="var(--rule-soft)" stroke-width="1"/>
  <line x1="0" y1="{{mini.fb_zero}}" x2="96" y2="{{mini.fb_zero}}" class="zl"/>
  <polyline points="{{mini.fb_v282}}" class="ln thin a282"/>
  <polyline points="{{mini.fb_v293}}" class="ln thin a293"/>
</g>
<rect x="840" y="649" width="304" height="19" rx="9.5" fill="var(--v293)"/>
<text x="992" y="663" text-anchor="middle" fill="var(--on-bar)" font-size="10.5" font-weight="700" font-family="var(--mono)">46,080 &#8594; 0 &#8212; zero on all three branches</text>
<polyline points="262,606 288,606" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<polyline points="524,606 550,606" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<polyline points="814,606 840,606" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<polyline points="1144,619 1214,619 1214,156 1077,156" fill="none" stroke="var(--v293)" stroke-width="2.2" marker-end="url(#ahE)"/>
<text x="1206" y="330" text-anchor="end" fill="var(--v293)" font-size="11" font-weight="700" font-family="var(--mono)">fb &#8801; 0 at every frequency</text>

<!-- BAND 6 : the r24 lane -->
<text x="40" y="710" fill="var(--v293)" font-family="var(--sans)" font-weight="700" letter-spacing=".09em" font-size="10.5">BAND 6 &#183; THE r24 RATE LANE &#8212; EDIT 4, AND THE ONLY RATE-FED TERM LEFT IN THE ECU</text>
<rect x="40" y="720" width="222" height="52" rx="4" fill="var(--nodefill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="151" y="742" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">torsion-bar twist</text>
<text x="151" y="759" text-anchor="middle" fill="var(--ink-mut)" font-size="11" font-family="var(--mono)">gp&#8722;0x4f60 &#183; what hands load</text>
<rect x="288" y="720" width="236" height="52" rx="4" fill="var(--nodefill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="406" y="742" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">4-tap derivative</text>
<text x="406" y="759" text-anchor="middle" fill="var(--ink-mut)" font-size="11" font-family="var(--mono)">d = (bar[n] &#8722; bar[n&#8722;4])&#183;&#189;</text>
<rect x="550" y="706" width="284" height="106" rx="4" fill="var(--editfill)" stroke="var(--v293)" stroke-width="2.2"/>
<text x="692" y="725" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">arm 0xC6446 &#183; r24 = &#8722;(d&#183;K) &gt;&gt; 10</text>
<g transform="translate(644,734)">
  <rect x="-2" y="-2" width="100" height="48" fill="var(--surface)" stroke="var(--rule-soft)" stroke-width="1"/>
  <line x1="0" y1="{{mini.r24_zero}}" x2="96" y2="{{mini.r24_zero}}" class="zl"/>
  <polyline points="{{mini.r24_5244}}" class="ln thin a282"/>
  <polyline points="{{mini.r24_2048}}" class="ln thin a293"/>
</g>
<rect x="550" y="789" width="284" height="19" rx="9.5" fill="var(--v293)"/>
<text x="692" y="803" text-anchor="middle" fill="var(--on-bar)" font-size="10.5" font-weight="700" font-family="var(--mono)">5,244 &#8594; 2,048  (&#215;5.12 &#8594; &#215;2.00)</text>
<rect x="860" y="733" width="284" height="52" rx="4" fill="var(--nodefill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="1002" y="755" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">deadband &#177;3 &#183; clamp &#177;8192</text>
<text x="1002" y="772" text-anchor="middle" fill="var(--ink-mut)" font-size="11" font-family="var(--mono)">&#8594; gp&#8722;0x6ada</text>
<polyline points="262,746 288,746" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<polyline points="524,746 550,746" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<polyline points="834,759 860,759" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>

<!-- BAND 7 : motor chain -->
<text x="40" y="864" fill="var(--ink-mut)" font-family="var(--sans)" font-weight="700" letter-spacing=".09em" font-size="10.5">BAND 7 &#183; AGGREGATOR TO MOTOR &#8212; BYTE-IDENTICAL, AND THE TWO LANES CARRY UNIT WEIGHT</text>
<rect x="40" y="874" width="210" height="52" rx="4" fill="var(--nodefill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="145" y="896" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">gp&#8722;0x6b4c</text>
<text x="145" y="913" text-anchor="middle" fill="var(--ink-mut)" font-size="11" font-family="var(--mono)">clamp &#177;0x2800</text>
<rect x="276" y="874" width="230" height="52" rx="4" fill="var(--nodefill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="391" y="896" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">aggregator gp&#8722;0x6b94</text>
<text x="391" y="913" text-anchor="middle" fill="var(--ink-mut)" font-size="11" font-family="var(--mono)">FUN_0003aa2c</text>
<rect x="532" y="874" width="180" height="52" rx="4" fill="var(--nodefill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="622" y="896" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">governor</text>
<text x="622" y="913" text-anchor="middle" fill="var(--ink-mut)" font-size="11" font-family="var(--mono)">FUN_0004503c</text>
<rect x="738" y="874" width="180" height="52" rx="4" fill="var(--nodefill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="828" y="896" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">EME shaper</text>
<text x="828" y="913" text-anchor="middle" fill="var(--ink-mut)" font-size="11" font-family="var(--mono)">FUN_00042af8</text>
<rect x="944" y="874" width="200" height="52" rx="4" fill="var(--plantfill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="1044" y="896" text-anchor="middle" fill="var(--ink)" font-size="13" font-weight="600" font-family="var(--sans)">motor &#183; column &#183; rack</text>
<text x="1044" y="913" text-anchor="middle" fill="var(--ink-mut)" font-size="11" font-family="var(--mono)">the plant</text>
<polyline points="1144,466 1186,466 1186,818 145,818 145,874" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<text x="700" y="814" text-anchor="middle" fill="var(--ink-mut)" font-size="10.5" font-family="var(--mono)">the LKAS lane</text>
<polyline points="1002,785 1002,846 391,846 391,874" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<text x="700" y="842" text-anchor="middle" fill="var(--ink-mut)" font-size="10.5" font-family="var(--mono)">the r24 lane</text>
<polyline points="250,900 276,900" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<polyline points="506,900 532,900" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<polyline points="712,900 738,900" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<polyline points="918,900 944,900" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<polyline points="1144,900 1240,900 1240,690 22,690 22,606 40,606" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<text x="560" y="686" text-anchor="middle" fill="var(--ink-mut)" font-size="10.5" font-family="var(--mono)">the measured column rate &#8212; still measured, no longer used</text>
<polyline points="1044,926 1044,952 14,952 14,746 40,746" fill="none" stroke="var(--flow)" stroke-width="1.6" marker-end="url(#ah)"/>
<text x="560" y="948" text-anchor="middle" fill="var(--ink-mut)" font-size="10.5" font-family="var(--mono)">bar twist &#8212; the driver&#8217;s hands and the road, into r24 and into the fade</text>

<!-- BAND 8 : telemetry -->
<text x="40" y="986" fill="var(--ink-mut)" font-family="var(--sans)" font-weight="700" letter-spacing=".09em" font-size="10.5">BAND 8 &#183; LIVE TELEMETRY, CARRIED BYTE-IDENTICAL FROM V282 &#8212; NO NEW CAVE BIT IS NEEDED</text>
<rect x="40" y="996" width="1056" height="52" rx="4" fill="var(--cavefill)" stroke="var(--noderule)" stroke-width="1.2"/>
<text x="128" y="1014" text-anchor="middle" fill="var(--v293)" font-size="12" font-weight="700" font-family="var(--mono)">b7</text>
<text x="128" y="1029" text-anchor="middle" fill="var(--ink-mut)" font-size="10" font-family="var(--mono)">sign(gp&#8722;0x6b4c)</text>
<text x="128" y="1042" text-anchor="middle" fill="var(--v293)" font-size="9.5" font-family="var(--mono)">0.996 &#8594; 0.808, the mover</text>
<line x1="216" y1="996" x2="216" y2="1048" stroke="var(--noderule)" stroke-width="1"/>
<text x="304" y="1014" text-anchor="middle" fill="var(--ink)" font-size="12" font-weight="700" font-family="var(--mono)">b6</text>
<text x="304" y="1029" text-anchor="middle" fill="var(--ink-mut)" font-size="10" font-family="var(--mono)">|r24| &#8805; |T|</text>
<text x="304" y="1042" text-anchor="middle" fill="var(--ink-mut)" font-size="9.5" font-family="var(--mono)">not pre-registered</text>
<line x1="392" y1="996" x2="392" y2="1048" stroke="var(--noderule)" stroke-width="1"/>
<text x="480" y="1014" text-anchor="middle" fill="var(--ink)" font-size="12" font-weight="700" font-family="var(--mono)">b5</text>
<text x="480" y="1029" text-anchor="middle" fill="var(--ink-mut)" font-size="10" font-family="var(--mono)">|r24| &#8805; |aggregator|</text>
<line x1="568" y1="996" x2="568" y2="1048" stroke="var(--noderule)" stroke-width="1"/>
<text x="656" y="1014" text-anchor="middle" fill="var(--v293)" font-size="12" font-weight="700" font-family="var(--mono)">b4</text>
<text x="656" y="1029" text-anchor="middle" fill="var(--ink-mut)" font-size="10" font-family="var(--mono)">sign(r24)</text>
<text x="656" y="1042" text-anchor="middle" fill="var(--v293)" font-size="9.5" font-family="var(--mono)">the NEGATIVE CONTROL</text>
<line x1="744" y1="996" x2="744" y2="1048" stroke="var(--noderule)" stroke-width="1"/>
<text x="832" y="1014" text-anchor="middle" fill="var(--ink)" font-size="12" font-weight="700" font-family="var(--mono)">b3</text>
<text x="832" y="1029" text-anchor="middle" fill="var(--ink-mut)" font-size="10" font-family="var(--mono)">sign(gp&#8722;0x3680)</text>
<text x="832" y="1042" text-anchor="middle" fill="var(--ink-mut)" font-size="9.5" font-family="var(--mono)">measured aliased</text>
<line x1="920" y1="996" x2="920" y2="1048" stroke="var(--noderule)" stroke-width="1"/>
<text x="1008" y="1014" text-anchor="middle" fill="var(--ink)" font-size="12" font-weight="700" font-family="var(--mono)">b2&#8211;b0</text>
<text x="1008" y="1029" text-anchor="middle" fill="var(--ink-mut)" font-size="10" font-family="var(--mono)">stock Honda</text>
<text x="1108" y="1014" fill="var(--ink-mut)" font-size="10.5" font-family="var(--sans)" font-weight="700">CAN 0x14A</text>
<text x="1108" y="1028" fill="var(--ink-mut)" font-size="10.5" font-family="var(--sans)" font-weight="700">byte 4</text>
<text x="1108" y="1042" fill="var(--ink-mut)" font-size="10" font-family="var(--mono)">100 Hz</text>
</svg></div>
