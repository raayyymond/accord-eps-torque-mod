# -*- coding: utf-8 -*-
"""v293r5_page_build.py -- writes the rev-5 Artifact page (docs/artifacts/V293-REV5-PAGE-2026-09-15.html) from
_scratch/v293r5_page_embed.json (v293r5_pagedata.py + the reduce step).  Static content is written here by the
orchestrator; the graphs are drawn by a small inline SVG plotter from the embedded data.  No libraries."""
import json, os
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, "..", "..", ".."))
DATA = open(os.path.join(HERE, "_scratch", "v293r5_page_embed.json"), encoding="utf-8").read()
OUT = os.path.join(KIT, "docs", "artifacts", "V293-REV5-PAGE-2026-09-15.html")

HTML = r"""<title>Rev 5 Observer</title>
<meta name="description" content="V293 torque mode, fork rev 5: what the real rev-4 drive said, the disturbance observer that replaces the integrator, every new term drawn, the risk and the pre-registered read.">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:ital,wght@0,400;0,500;0,600;1,400&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>
:root{
  --bg:#f4f3ee; --bg2:#ebe9e1; --ink:#1b1e23; --ink2:#4a4f58; --ink3:#7a7f88; --line:#d6d3c8;
  --r4:#a35a12; --r5:#0b6e69; --plant:#4b5563; --bad:#a3262a; --good:#256b2f; --accent:#0b6e69; --accent-bg:#d8ebe8;
  --mono:'IBM Plex Mono',ui-monospace,Menlo,Consolas,monospace; --sans:'IBM Plex Sans',system-ui,Segoe UI,Roboto,sans-serif;
}
@media (prefers-color-scheme: dark){:root:not([data-theme="light"]){
  --bg:#15181d; --bg2:#1d2128; --ink:#e8e6df; --ink2:#b7b4ab; --ink3:#868a93; --line:#343943;
  --r4:#e0904a; --r5:#4fc1b8; --plant:#a3adba; --bad:#e06b6f; --good:#6fc07a; --accent:#4fc1b8; --accent-bg:#173a38;}}
:root[data-theme="dark"]{
  --bg:#15181d; --bg2:#1d2128; --ink:#e8e6df; --ink2:#b7b4ab; --ink3:#868a93; --line:#343943;
  --r4:#e0904a; --r5:#4fc1b8; --plant:#a3adba; --bad:#e06b6f; --good:#6fc07a; --accent:#4fc1b8; --accent-bg:#173a38;}
body{background:var(--bg);color:var(--ink);font-family:var(--sans);font-size:15px;line-height:1.5;margin:0;padding-inline:clamp(16px,4vw,40px);padding-block:28px 64px}
main{max-width:1040px;margin:0 auto}
h1{font-size:clamp(26px,3.4vw,38px);line-height:1.12;margin:0 0 6px;font-weight:600;letter-spacing:-.01em;text-wrap:balance}
h2{font-size:21px;margin:44px 0 10px;font-weight:600;letter-spacing:-.005em;text-wrap:balance}
h3{font-size:16px;margin:24px 0 6px;font-weight:600}
p{max-width:72ch;margin:8px 0}
.lede{font-size:17px;color:var(--ink2);max-width:80ch}
.eyebrow{font-family:var(--mono);font-size:12px;letter-spacing:.08em;text-transform:uppercase;color:var(--ink3)}
.tag{display:inline-block;font-family:var(--mono);font-size:12px;padding:1px 7px;border:1px solid var(--line);border-radius:4px;color:var(--ink2);margin-right:6px}
.ev{color:var(--good);font-weight:500}.be{color:var(--r4);font-weight:500}
.verdict{border-left:4px solid var(--accent);background:var(--accent-bg);padding:14px 18px;margin:18px 0 6px;border-radius:0 6px 6px 0}
.verdict p{max-width:none}
.grid{display:grid;gap:18px;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));align-items:start}
figure{margin:18px 0;padding:0}
figcaption{font-size:13.5px;color:var(--ink2);margin-top:6px;max-width:80ch}
svg.plot{width:100%;height:auto;display:block;overflow:visible;font-family:var(--mono);font-size:11px}
svg.plot text{fill:var(--ink2)}
svg.plot .axis{stroke:var(--line);stroke-width:1}
svg.plot .grid{stroke:var(--line);stroke-width:.6;stroke-dasharray:2 4}
svg.plot .r4{stroke:var(--r4)}.r5{stroke:var(--r5)}.plant{stroke:var(--plant)}.bad{stroke:var(--bad)}.good{stroke:var(--good)}
.legend{display:flex;gap:16px;flex-wrap:wrap;font-family:var(--mono);font-size:12px;color:var(--ink2);margin:4px 0 0}
.legend i{display:inline-block;width:18px;height:0;border-top:2.5px solid;vertical-align:middle;margin-right:5px}
.legend .d{border-top-style:dashed}
table{border-collapse:collapse;font-size:13.5px;margin:10px 0;font-variant-numeric:tabular-nums;width:100%}
th,td{padding:5px 9px;border-bottom:1px solid var(--line);text-align:right;vertical-align:top}
th{font-weight:500;color:var(--ink2);text-align:right}
td:first-child,th:first-child{text-align:left}
.tw{overflow-x:auto}
.mono{font-family:var(--mono);font-size:13px}
.note{font-size:13.5px;color:var(--ink2)}
.flow{width:100%;height:auto;display:block;font-family:var(--mono);font-size:12px}
.flow text{fill:var(--ink)}.flow .box{fill:var(--bg2);stroke:var(--ink3);stroke-width:1}.flow .new{fill:var(--accent-bg);stroke:var(--accent);stroke-width:1.6}
.flow .arrow{stroke:var(--ink2);stroke-width:1.3;fill:none}.flow .sub{fill:var(--ink3)}
.flow .eps{fill:none;stroke:var(--r4);stroke-width:1.2;stroke-dasharray:5 4}
.kv{display:grid;grid-template-columns:max-content 1fr;gap:4px 14px;font-size:14px;max-width:80ch}
.kv b{font-weight:500;color:var(--ink2)}
hr{border:0;border-top:1px solid var(--line);margin:36px 0}
.risk{border:1px solid var(--bad);border-radius:6px;padding:12px 16px;background:var(--bg2)}
code{font-family:var(--mono);font-size:.92em;background:var(--bg2);padding:1px 4px;border-radius:3px}
@media (prefers-reduced-motion: reduce){*{animation:none!important;transition:none!important}}
</style>
<main>
<div class="eyebrow">2020 Accord EPS · V293 torque mode · StarPilot fork rev 5 · 2026-09-15</div>
<h1>Rev 5: a disturbance observer takes over from the integrator</h1>
<p class="lede">The real rev-4 drive (route <span class="mono">00000075--6c8687d5bd</span>, 803 s engaged) says rev 4 fixed the tracking <em>gain</em> at speed but left 20–30 % of the planner signal as error, most of it below 1 Hz, with the integrator carrying a third of the torque. Rev 5 estimates that unmodelled torque directly from the wheel and the controller's own past output, adds it to the feedforward, and drops the integral gain to 0.3 flat. <b>Firmware unchanged: V293 stays in the car. Nothing flashed, nothing sent on CAN.</b></p>

<div class="verdict">
<div class="eyebrow">the decision</div>
<p><b>Fork <span class="mono">Dom e44b6cd31</span> + <span class="mono">toggle-config_V293_torque_mode_r5.json</span>.</b> New term <code>AccordDobHz 0.6</code> (the observer's corner), <code>SteerKP 0.85 → 1.0</code>, <code>AccordTorqueKi 0.6 → 0.3</code> flat with <code>AccordTorqueKiHigh 0</code> (the rev-4 schedule to 2.5 is OFF), <code>AccordRateLoopGain 6e-4 → 1e-3</code>, and the rate-measurement filter in code 0.03 → 0.01 s. Everything else is rev 4. Revert = <span class="mono">toggle-config_V293_torque_mode_r5_REVERT_to_r4.json</span> (observer off, rev-4 gains) — no fork rollback needed. The observer's output is on the wire (<code>starpilotLateralState.accordObserverTorque</code>), so the read is direct.</p>
<p class="note"><span class="ev">EVIDENCE</span> = read from the wire or from the built fork; <span class="be">BELIEF</span> = simulation or inference. The plant's damping between 15 and 22 m/s is the one thing the drive did not settle, and the design is chosen to be safe either way.</p>
</div>

<h2>1 · What the rev-4 drive said <span class="tag">EVIDENCE · route 75 vs route 72</span></h2>
<p>Attribution from the wire: <span class="mono">GitCommit 08a5a706 / Dom</span>, Kp 0.8500 and LAF 14.0000 on every active frame, <code>AccordTorqueKiHigh 2.5</code> in initData. The operator: <em>"still a little loose; still jerky on hard turns; not as smooth, confident and well-controlled as the 1 kHz inner loop; the command has to overshoot to get over friction."</em></p>
<div class="tw"><table>
<tr><th>hands-off, planner desire vs actual lateral acceleration</th><th>1–8 m/s</th><th>8–15</th><th>15–22</th><th>&gt;22</th></tr>
<tr><td>tracking gain · rev 3 (route 72) → rev 4 (route 75)</td><td>0.96 → 0.98</td><td>0.98 → 0.97</td><td><b>0.80 → 0.98</b></td><td><b>0.74 → 0.97</b></td></tr>
<tr><td>lag planner → actual, s</td><td>0.00 → 0.29</td><td>0.11 → 0.13</td><td>0.46 → 0.31</td><td>0.52 → 0.45</td></tr>
<tr><td>rms error / rms signal · rev 4</td><td>0.19</td><td>0.26</td><td>0.21</td><td>0.30</td></tr>
<tr><td>share of the error below 0.3 Hz / 0.3–1 Hz · rev 4</td><td>49 / 34 %</td><td>66 / 23 %</td><td>62 / 18 %</td><td>69 / 17 %</td></tr>
<tr><td>integrator's share of the torque · rev 4</td><td>0.32</td><td>0.29</td><td>0.29</td><td>0.33</td></tr>
<tr><td>turn hold, actual/planner at &gt;1.5 m/s²</td><td>0.94</td><td>0.93</td><td>0.97</td><td>–</td></tr>
</table></div>
<p>So the rev-4 mechanism did what it was designed for — the schedule to Ki 2.5 pulled the high-speed gain from 0.74–0.80 to 0.97–0.98 — and the operator still calls it loose, because the residual is a slow, integrator-paced catch-up: half to two thirds of the error energy sits below 0.3 Hz and a further fifth to a third in 0.3–1 Hz.</p>

<h3>The hard-turn jerk is the 2–2.7 Hz wheel mode</h3>
<div class="grid">
<div>
<p>In hands-off hard turns below 10 m/s (25 s on route 75) the wheel moves in bursts: 24 bursts above 80 deg/s, 0.12 s long, spaced <b>0.53 s</b> apart (1.9 Hz); the torque command has a <b>+6.9 dB line at 1.95 Hz</b>. Between 10 and 20 m/s (9 s) the closed loop <b>amplifies planner content 2.3× at 2 Hz</b> with coherence 0.99, and 47 % of the 0.3–8 Hz wheel-rate energy sits in 1.6–3 Hz. Route 72 (rev 3) showed the same burst spacing (0.56 s). This is the lightly damped closed-loop spring–inertia mode, stick-slip-locked at low speed — not the friction relay (that was route 73) and not a command staircase.</p>
<p>Zero stiction dwells by the route-70 definition (wheel still ≥0.3 s while in error) on either drive: the rev-3 hysteresis term is doing its job; what remains is motion at the mode frequency.</p>
</div>
<div class="tw"><table>
<tr><th>hard turns, hands-off · route 75</th><th>v 2–10</th><th>v 10–20</th></tr>
<tr><td>seconds</td><td>25</td><td>9</td></tr>
<tr><td>wheel-rate energy 0.3–1 / 1–1.6 / 1.6–3 / 3–5 Hz</td><td>59 / 8 / 19 / 3 %</td><td>22 / 10 / 47 / 8 %</td></tr>
<tr><td>torque-command peak 0.8–6 Hz</td><td>1.95 Hz, +6.9 dB</td><td>1.17 Hz, +1.5 dB</td></tr>
<tr><td>wheel-rate peak 0.8–6 Hz</td><td>0.98 Hz, −12.5 dB</td><td>2.73 Hz, +13.2 dB</td></tr>
<tr><td>des→act |H| at 1.2 / 2.0 Hz</td><td>1.32 / 1.11</td><td>1.23 / 2.28</td></tr>
<tr><td>|rate|&gt;80 deg/s bursts, spacing</td><td>24, median 0.53 s</td><td>7 (&gt;40), 0.26 s</td></tr>
</table></div>
</div>

<h3>Is the plant lightly or heavily damped? Both, by speed</h3>
<p>The time-domain fit of <span class="mono">u(t−Td) = hold(θ) + b θ' + J θ'' + F sign θ'</span> on hands-off stretches gives <b>b ≈ 0.0005–0.0009 torque per deg/s below 15 m/s on both drives</b> (the "mode" world the rev-3/4 design assumed) and ≈ 0.004 only above 22 m/s (2–4 stretches, R² 0.73–0.86). The joint-IO transfer at 15–30 m/s leans lightly damped below 0.6 Hz and has no coherence above it. The 2026-09-13 identification's b (0.0018–0.0049 by band) is therefore <span class="be">BELIEF</span> below 20 m/s; the design below keeps every candidate stable in <em>both</em> worlds and five mismatch worlds besides.</p>

<h2>2 · Why a 100 Hz loop cannot linearise friction here <span class="tag">EVIDENCE · linear model of the flown loop</span></h2>
<p>It is not the 100 Hz rate; it is the ~60 ms round trip (CAN command → EPS → wheel → angle sensor → openpilot) plus the loop's own filters. A P loop through that delay has a static stiffness of only 1 + Kp<sub>torque</sub>/k = 1.7 (≈3 at the most Kp the margins allow), so a hold-map level error, a road crown or the friction the hysteresis term missed leaves 1/1.7 of it in the angle until the integrator arrives at its own 0.2–0.5 Hz corner. A rate damper has phase −(ω·Td + atan ω·RC): it damps only where that is above −90°.</p>
<figure>
<div class="legend"><span><i style="border-color:var(--r4)"></i>RC 0.03 s (rev 4)</span><span><i style="border-color:var(--r5)"></i>RC 0.01 s (rev 5)</span><span><i class="d" style="border-color:var(--ink3)"></i>−90°: damping becomes pumping</span></div>
<svg class="plot" id="p_rlphase" role="img" aria-label="Phase of the rate-loop damping torque relative to the wheel rate versus frequency, for the two measurement filters; it crosses minus ninety degrees near 2.8 Hz with the old filter and near 3.3 Hz with the new one"></svg>
<figcaption>The rate loop's phase through the 60 ms round trip. With the 0.03 s filter it stops damping at ≈2.8 Hz and pumps 3–5 Hz — the +2.6 to +4 dB 3–5.5 Hz wheel-rate hump every rev-3/4 drive shows. The 0.01 s filter moves the boundary to ≈3.3 Hz. It cannot be moved to the 1 kHz loop's tens of Hz from outside the EPS.</figcaption>
</figure>

<h2>3 · The new term, drawn: where the observer sits <span class="tag">fork rev 5</span></h2>
<figure>
<svg class="flow" viewBox="0 0 1040 470" role="img" aria-label="Signal flow of the fork's Accord torque controller on the V293 torque-map EPS, with the new disturbance observer block feeding the feedforward from the measured wheel state and the delayed controller output">
<defs><marker id="ah" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse"><path d="M0 0L10 5L0 10z" fill="currentColor" style="color:var(--ink2)"/></marker></defs>
<!-- planner row -->
<rect class="box" x="12" y="30" width="118" height="46" rx="4"/><text x="71" y="49" text-anchor="middle">planner</text><text x="71" y="65" text-anchor="middle" class="sub">desired curvature</text>
<path class="arrow" d="M130 53H172" marker-end="url(#ah)"/>
<rect class="box" x="172" y="30" width="126" height="46" rx="4"/><text x="235" y="49" text-anchor="middle">reference filter</text><text x="235" y="65" text-anchor="middle" class="sub">2 poles · 0.12 s</text>
<path class="arrow" d="M298 53H340" marker-end="url(#ah)"/>
<rect class="box" x="340" y="30" width="150" height="46" rx="4"/><text x="415" y="49" text-anchor="middle">angle_des, rate_des</text><text x="415" y="65" text-anchor="middle" class="sub">SR map · roll comp</text>
<!-- feedforward stack -->
<path class="arrow" d="M415 76V104" marker-end="url(#ah)"/>
<rect class="box" x="322" y="104" width="186" height="76" rx="4"/>
<text x="415" y="122" text-anchor="middle">plant feedforward</text>
<text x="415" y="139" text-anchor="middle" class="sub">hold(angle_des, v) · move b·rate_des</text>
<text x="415" y="155" text-anchor="middle" class="sub">hysteresis friction ±0.015</text>
<text x="415" y="171" text-anchor="middle" class="sub">rate loop Kv·(rate_des − rate)  RC 0.01</text>
<!-- P/I -->
<rect class="box" x="322" y="212" width="186" height="60" rx="4"/>
<text x="415" y="232" text-anchor="middle">P + I in lat-accel space</text>
<text x="415" y="248" text-anchor="middle" class="sub">Kp 1.0 · Ki 0.3 flat · notch Q1 at √(k/J)</text>
<text x="415" y="264" text-anchor="middle" class="sub">÷ LAF 14 → torque</text>
<path class="arrow" d="M415 180V212" marker-end="url(#ah)"/>
<!-- sum + output -->
<circle cx="600" cy="242" r="14" class="box"/><text x="600" y="247" text-anchor="middle">Σ</text>
<path class="arrow" d="M508 242H586" marker-end="url(#ah)"/>
<path class="arrow" d="M614 242H660" marker-end="url(#ah)"/>
<rect class="box" x="660" y="219" width="110" height="46" rx="4"/><text x="715" y="238" text-anchor="middle">Honda limiter</text><text x="715" y="254" text-anchor="middle" class="sub">±3/frame · 0xE4</text>
<path class="arrow" d="M770 242H812" marker-end="url(#ah)"/>
<rect class="eps" x="812" y="200" width="216" height="130" rx="6"/><text x="920" y="218" text-anchor="middle" class="sub">EPS · V293 (unchanged)</text>
<rect class="box" x="826" y="228" width="188" height="40" rx="4"/><text x="920" y="245" text-anchor="middle">torque map ×6</text><text x="920" y="260" text-anchor="middle" class="sub">rate loop OPEN · fb clamp 0 · Kd 0</text>
<path class="arrow" d="M920 268V282" marker-end="url(#ah)"/>
<rect class="box" x="826" y="282" width="188" height="40" rx="4"/><text x="920" y="299" text-anchor="middle">wheel · J θ″ + b θ′ + hold(θ) + F</text><text x="920" y="314" text-anchor="middle" class="sub">lightly damped 2–2.7 Hz mode</text>
<!-- measurement back -->
<path class="arrow" d="M920 322V372H600" marker-end="url(#ah)"/>
<text x="760" y="366" text-anchor="middle" class="sub">0x18F rate · angle · 100 Hz · ≈60 ms round trip</text>
<!-- P/I error path -->
<path class="arrow" d="M600 372V304H415V272" marker-end="url(#ah)"/>
<text x="500" y="298" text-anchor="middle" class="sub">measured curvature → error</text>
<!-- DOB block -->
<rect class="new" x="590" y="86" width="260" height="106" rx="6"/>
<text x="720" y="106" text-anchor="middle" style="font-weight:600">DISTURBANCE OBSERVER  (new, rev 5)</text>
<text x="720" y="124" text-anchor="middle" class="sub">w = hold(θ) + b(v)·θ′ + J·θ″ − u(t − 0.06)</text>
<text x="720" y="140" text-anchor="middle" class="sub">Q(f): two poles at AccordDobHz 0.6 · clip ±0.3</text>
<text x="720" y="156" text-anchor="middle" class="sub">fade 3→6 m/s · held while safety-limited or driver holds</text>
<text x="720" y="172" text-anchor="middle" class="sub">reset on engage · published: accordObserverTorque</text>
<path class="arrow" d="M600 372V300H560V192" marker-end="url(#ah)"/>
<text x="548" y="330" text-anchor="end" class="sub">θ, θ′</text>
<path class="arrow" d="M640 242V206" marker-end="url(#ah)"/>
<text x="652" y="222" class="sub">u (own output, delayed 6 frames)</text>
<path class="arrow" d="M590 139H540V160H508" marker-end="url(#ah)"/>
<text x="552" y="132" text-anchor="end" class="sub">+ŵ to the feedforward</text>
</svg>
<figcaption>The LKAS demand path end to end, as it runs on the car: openpilot's planner → the fork's Accord torque controller (feedforward + P/I) → the Honda rate limiter → the V293 EPS, which is a pure ×6 torque map with its 1 kHz rate loop open → the wheel → the 100 Hz measurements. The observer (teal) is the only structural change: it reads the measured wheel state and the controller's own output six frames back, and adds its low-passed estimate of what the model missed to the feedforward. Nothing on the EPS side moved.</figcaption>
</figure>

<h2>4 · The observer's own response <span class="tag">BELIEF · linear · sim</span></h2>
<div class="grid">
<figure>
<div class="legend"><span><i style="border-color:var(--r5)"></i>|Q| at 0.6 Hz (ships)</span><span><i class="d" style="border-color:var(--r4)"></i>|Q| at 0.8 Hz (rejected: rang with delays ×1.5)</span></div>
<svg class="plot" id="p_qmag" role="img" aria-label="Magnitude of the observer's two-pole low-pass Q against frequency, for a 0.6 hertz and a 0.8 hertz corner"></svg>
<figcaption>Q(f) = 1/(1 + jf/f<sub>Q</sub>)². Below its corner the observer cancels whatever the model missed — a wrong hold level, a crown, unmodelled friction — at full strength; above it the correction fades and lags. Its own loop closes only through model mismatch, |Q|·|P/P<sub>m</sub> − 1| &lt; 1, not through the plant's phase, which is why the corner can sit above the integrator's.</figcaption>
</figure>
<figure>
<div class="legend"><span><i style="border-color:var(--r5)"></i>Re Q, 0.6 Hz</span><span><i class="d" style="border-color:var(--r4)"></i>Re Q, 0.8 Hz</span></div>
<svg class="plot" id="p_qre" role="img" aria-label="Real part of Q against frequency: positive below the corner, negative above it, so a damping mismatch in the model adds damping below the corner and removes it above"></svg>
<figcaption>The sign that decides the trade. The observer's residual carries (b<sub>model</sub> − b<sub>plant</sub>)·rate, so it injects damping Δb·Re Q(f): positive below f<sub>Q</sub>, <b>negative above it</b>. With the fork's model b above the plant's (as the drive suggests below 15 m/s) the observer installs the model's damping under 0.6 Hz and takes a little from the 2 Hz mode. That is the whole reason the corner ships at 0.6 and not 0.8.</figcaption>
</figure>
</div>
<figure>
<div class="legend"><span><i style="border-color:var(--plant)"></i>plant b, lightly damped world</span><span><i class="d" style="border-color:var(--plant)"></i>plant b, identified world</span><span><i style="border-color:var(--r4)"></i>rate loop rev 4 (Kv 6e-4, RC 0.03)</span><span><i style="border-color:var(--r5)"></i>rate loop rev 5 (Kv 1e-3, RC 0.01)</span><span><i class="d" style="border-color:var(--r5)"></i>observer Δb·Re Q (0.6 Hz)</span></div>
<svg class="plot" id="p_damp12" role="img" aria-label="Damping budget in torque per degree per second versus frequency at 12 metres per second: the plant's own damping, the rate loop's contribution for rev 4 and rev 5, and the observer's contribution, which is positive below 0.6 hertz and negative above"></svg>
<figcaption>The damping budget at 12 m/s (torque per deg/s). The rate loop damps below ≈3 Hz and pumps above; rev 5's higher gain and faster filter widen the positive region. The observer adds ≈+0.003 below 0.3 Hz (four times the plant's own b in the lightly damped world) and removes ≈0.0003 at the 2 Hz mode. Net at the mode: still positive, but thinner than rev 4 — the price paid for the hold.</figcaption>
</figure>

<h2>5 · Before and after, same axes <span class="tag">BELIEF · simulation, lightly damped world</span></h2>
<div class="grid">
<figure>
<div class="legend"><span><i class="d" style="border-color:var(--ink3)"></i>planner</span><span><i style="border-color:var(--r4)"></i>rev 4 (flown)</span><span><i style="border-color:var(--r5)"></i>rev 5</span></div>
<svg class="plot" id="p_step8" role="img" aria-label="Lateral acceleration response to a 1 metre per second squared planner step at 8 metres per second: rev 4 overshoots by half, rev 5 by a quarter"></svg>
<figcaption>Planner step 1 m/s² at 8 m/s. Overshoot 0.49 → 0.25; error at 1 s −0.45 → −0.17 m/s². The observer's damping injection below its corner is what removes the slow swing back.</figcaption>
</figure>
<figure>
<div class="legend"><span><i class="d" style="border-color:var(--ink3)"></i>planner</span><span><i style="border-color:var(--r4)"></i>rev 4</span><span><i style="border-color:var(--r5)"></i>rev 5</span></div>
<svg class="plot" id="p_step19" role="img" aria-label="Lateral acceleration response to a planner step at 19 metres per second: rev 4 overshoot 0.57, rev 5 0.22"></svg>
<figcaption>The same step at 19 m/s: overshoot 0.57 → 0.22, error at 1 s −0.25 → +0.08 m/s². (Rev 4 here carries its Ki 2.5 schedule; rev 5 runs Ki 0.3 flat and the observer.)</figcaption>
</figure>
<figure>
<div class="legend"><span><i style="border-color:var(--r4)"></i>rev 4</span><span><i style="border-color:var(--r5)"></i>rev 5</span></div>
<svg class="plot" id="p_dist19" role="img" aria-label="Lateral acceleration error after a 0.03 torque disturbance step at 19 metres per second, rev 4 versus rev 5"></svg>
<figcaption>A 0.03-torque disturbance step (a crown, a hold-map level error) at 19 m/s while holding straight. |e| at 0.5 / 1 / 2 s: rev 4 0.165 / 0.085 / 0.021 → rev 5 0.127 / 0.035 / 0.027 m/s². The first half second is the delay's and does not move; the observer takes the next second.</figcaption>
</figure>
<figure>
<div class="legend"><span><i class="d" style="border-color:var(--ink3)"></i>planner</span><span><i style="border-color:var(--r4)"></i>rev 4</span><span><i style="border-color:var(--r5)"></i>rev 5</span><span><i class="d" style="border-color:var(--r5)"></i>observer torque ×10</span></div>
<svg class="plot" id="p_hard8" role="img" aria-label="Hard turn to 2.5 metres per second squared at 8 metres per second with friction one and a half times the model: rev 4 holds 0.22 below the target, rev 5 0.04; the observer's torque is drawn scaled by ten"></svg>
<figcaption>Hard turn at 8 m/s, Coulomb friction ×1.5 the model. Hold error 0.22 → 0.04 m/s²; peak wheel rate 119 → 103 deg/s. The observer's estimate (dashed, ×10) rises to 0.074 torque during the hold — the friction and hold-level torque the map did not know about.</figcaption>
</figure>
</div>

<h2>6 · The gains that moved, before and after <span class="tag">config + one fork constant</span></h2>
<div class="grid">
<figure>
<div class="legend"><span><i style="border-color:var(--r4)"></i>rev 4: Ki 0.6 → 2.5 from 18 m/s</span><span><i style="border-color:var(--r5)"></i>rev 5: Ki 0.3 flat</span></div>
<svg class="plot" id="p_ki" role="img" aria-label="Integral gain versus speed: rev 4 ramps from 0.6 at 8 metres per second to 2.5 at 18; rev 5 is 0.3 everywhere"></svg>
<figcaption>Integral gain (per second, lat-accel space through LAF 14). The schedule to 2.5 is what fixed rev 3's high-speed gain; the observer replaces it 3–5× faster and without the reference-path lag the operator asked to avoid. Ki 0.3 stays as the slow backstop the observer's clip and freeze leave.</figcaption>
</figure>
<figure>
<div class="legend"><span><i style="border-color:var(--r4)"></i>rev 4: Kv 6e-4 · min(1, 12/v)</span><span><i style="border-color:var(--r5)"></i>rev 5: Kv 1e-3 · min(1, 12/v)</span><span><i class="d" style="border-color:var(--ink3)"></i>observer fade (right axis 0–1)</span></div>
<svg class="plot" id="p_kv" role="img" aria-label="Rate-loop gain versus speed for rev 4 and rev 5, both tapered above 12 metres per second, plus the observer's fade-in from 3 to 6 metres per second"></svg>
<figcaption>The rate loop's gain (torque per deg/s of wheel-rate error). It is the only term that damps 1–2.8 Hz; the sim's hard-turn 1.6–3 Hz wheel-rate energy fell 15–20 % from the gain and the faster filter together. The observer fades in over 3–6 m/s because the plant is unidentified below 8.</figcaption>
</figure>
</div>
<div class="tw"><table>
<tr><th>quantity</th><th>rev 4 (flown)</th><th>rev 5</th><th>where</th></tr>
<tr><td>SteerKP (P gain, lat-accel space)</td><td>0.85</td><td>1.00</td><td>config</td></tr>
<tr><td>AccordTorqueKi / AccordTorqueKiHigh</td><td>0.6 / 2.5 (schedule 8→18 m/s)</td><td>0.3 / 0 (flat)</td><td>config</td></tr>
<tr><td>AccordRateLoopGain (Kv)</td><td>0.0006</td><td>0.001</td><td>config</td></tr>
<tr><td>AccordDobHz (observer corner)</td><td>— (no term)</td><td>0.6</td><td>config, new key</td></tr>
<tr><td>HONDA_ACCORD_RATE_LOOP_RC</td><td>0.03 s</td><td>0.01 s</td><td>fork constant</td></tr>
<tr><td>notch Q1 at √(k/J)/2π · hysteresis 0.015 · ref 0.12 s · hold map · LAF 14 · SteerFriction 0 · live delay</td><td colspan="2">unchanged</td><td>config</td></tr>
</table></div>

<h2>7 · Robustness: five plant worlds, six tests <span class="tag">BELIEF · sim, speed-averaged 6–26 m/s</span></h2>
<p>Every candidate was run at 6/8/12/19/26 m/s in a lightly damped world (b 0.0006), the identified world (b 0.0018–0.0049), each with the hold map ×1.5 wrong, with the delays ×1.5, and with the inertia ×1.5. Tests: T1 disturbance step, T2 planner step, T3 kick (ringing), T5 slow ramp against stiction, T7 small step, T8 hard turn.</p>
<div class="tw"><table>
<tr><th>world</th><th>config</th><th>T1 |e| at 1 s</th><th>T2 overshoot</th><th>T3 ring, max pk-pk °</th><th>T8 hold error</th><th>T8 1.6–3 Hz rate rms</th></tr>
<tr><td rowspan="2">lightly damped</td><td>rev 4</td><td>0.074</td><td>+0.51</td><td>1.84</td><td>0.219</td><td>3.20</td></tr>
<tr><td><b>rev 5</b></td><td><b>0.029</b></td><td><b>+0.20</b></td><td><b>0.92</b></td><td><b>0.086</b></td><td>3.48 <span class="be">(+9 %)</span></td></tr>
<tr><td rowspan="2">lightly damped, hold ×1.5</td><td>rev 4</td><td>0.062</td><td>+0.12</td><td>1.82</td><td>0.163</td><td>3.04</td></tr>
<tr><td><b>rev 5</b></td><td><b>0.033</b></td><td><b>+0.05</b></td><td>1.79</td><td>0.203 <span class="be">(worse at 19–26)</span></td><td>3.16</td></tr>
<tr><td rowspan="2">identified</td><td>rev 4</td><td>0.073</td><td>+0.20</td><td>0.96</td><td>0.329</td><td>1.06</td></tr>
<tr><td><b>rev 5</b></td><td><b>0.049</b></td><td><b>+0.12</b></td><td>1.35</td><td><b>0.159</b></td><td>1.10</td></tr>
<tr><td rowspan="2">identified, delays ×1.5</td><td>rev 4</td><td>0.075</td><td>+0.23</td><td>1.00</td><td>0.378</td><td>1.17</td></tr>
<tr><td><b>rev 5</b></td><td><b>0.050</b></td><td><b>+0.17</b></td><td>1.53</td><td><b>0.181</b></td><td>1.25</td></tr>
<tr><td rowspan="2">lightly damped, delays ×1.5</td><td>rev 4</td><td>0.065</td><td>+0.59</td><td>2.18</td><td>0.266</td><td>4.06</td></tr>
<tr><td><b>rev 5</b></td><td><b>0.020</b></td><td><b>+0.30</b></td><td><b>0.73</b></td><td><b>0.108</b></td><td>4.96 <span class="be">(+22 %)</span></td></tr>
<tr><td rowspan="2">lightly damped, J ×1.5</td><td>rev 4</td><td>0.071</td><td>+0.65</td><td>2.15</td><td>0.250</td><td>2.72</td></tr>
<tr><td><b>rev 5</b></td><td><b>0.029</b></td><td><b>+0.34</b></td><td><b>0.96</b></td><td><b>0.125</b></td><td>3.10 <span class="be">(+14 %)</span></td></tr>
</table></div>
<p class="note">Units: T1/T2/T8 error in m/s²; T3 in degrees of wheel ringing after a 0.05-torque kick; T8 rate rms in deg/s over the hard turn. The one row where rev 5 loses (hold ×1.5 at 19–26 m/s, lightly damped) is rev 4's Ki 2.5 winding faster than the observer converges in the first second of the hold; the observer's clip (0.3) is never reached.</p>

<h3>What was tried and rejected, with the numbers</h3>
<ul>
<li><b>Kp 1.2 with the observer at 0.8 Hz</b> (the first rev-5 draft): best tracking, but +40 to +150 % 1.6–3 Hz wheel-rate energy in hard turns in the lightly damped world, and the 0.8 Hz corner rang (T3 4.0°) with the delays ×1.5. Kp 1.0 / 0.6 Hz keeps most of the tracking gain at a third of the cost.</li>
<li><b>Observer model with the LOW damping (b 0.0006)</b>: in the identified world it strips the plant's own damping below the corner — T2 overshoot +0.37 to +0.49 and hold error 0.48–0.84 m/s², worse than rev 4. The model must carry the higher b; being wrong high costs a little mode damping, being wrong low costs the hold.</li>
<li><b>A model-predicted rate damper</b> (propagate the measured wheel state 60 ms forward through the model, close the rate loop on the prediction): <span class="bad" style="color:var(--bad)">divergent</span> at 26 m/s in the lightly damped world with the identified-b model (T3 pk-pk 179–462°) and in the delays-×1.5 world (T8 rate rms 41 deg/s, error 20 m/s²), and biased during stiction (it predicts motion the friction is holding). Dead until the damping is identified per speed; it is left in the simulator, not in the fork.</li>
<li><b>Moving the error notch to the closed-loop mode frequency (×1.35)</b>: unstable at 26 m/s (T3 834°). The notch stays at the plant's √(k/J).</li>
<li><b>Ki 0 with the observer</b>: works in the sim; kept at 0.3 as the backstop for the observer's freeze and clip.</li>
<li><b>Dither</b> (a small torque oscillation to keep friction "broken"): not simulated and not proposed — a 7–10 Hz motor-torque dither sits on the 7 Hz strong-turn ripple this kit fought in V281 and would pass through the base-assist path with hands off.</li>
</ul>

<h2>8 · Risk before the drive <span class="tag">state it, then drive</span></h2>
<div class="risk">
<p><b>Authority.</b> The observer adds up to ±0.3 torque units (30 % of the ±1 command range) to the feedforward, faded to zero below 3 m/s and full from 6 m/s; the total command is still clipped at ±1 and still passes the Honda ±3/frame limiter and the panda safety limits. The EPS authority is unchanged (V293's ×6 map, as flown since 2026-09-13).</p>
<p><b>Failure modes and what they look like.</b> A wrong-signed or runaway estimate would be a one-sided pull that builds over ~0.5 s and pins at the clip — <code>accordObserverTorque</code> at ±0.3 for more than 2 s is the revert signature on the wire; the operator would feel a steady pull. A model mismatch large enough to close the observer's own loop would show as a 0.6–1.5 Hz oscillation in lateral acceleration. Both are covered by the freeze (safety-limited or driver holding) and by the config revert <span class="mono">_r5_REVERT_to_r4</span>, which turns the observer off without a fork rollback.</p>
<p><b>What the sim says the operator may feel.</b> Better hold and less catch-up everywhere; in tight low-speed turns possibly the same or slightly more of the 2 Hz burstiness he already reports. If that is what he feels, the next move is <code>AccordDobHz 0.4</code> and/or <code>SteerKP 0.85</code> by config — not a fork change.</p>
</div>

<h2>9 · The pre-registered read <span class="tag">v293r5_observer_read.py · written before the drive</span></h2>
<div class="kv">
<b>O1 on the wire</b><span>|accordObserverTorque| median &gt; 0.002 torque on active frames; frozen &lt; 30 % of hands-off frames.</span>
<b>O2 "loose"</b><span>planner-error rms in 0.05–0.3 Hz and 0.3–1 Hz at 8–30 m/s falls ≥ 30 % vs route 75 (0.048/0.040 · 0.064/0.056 · 0.067/0.030 m/s² by band); integrator share 0.25–0.29 → &lt; 0.15.</span>
<b>O3 "confident"</b><span>des→act |H| at 0.5 Hz within 0.85–1.15 and at 1 Hz within 0.7–1.3 (route 75: 1.07–1.19 / 0.72–0.82); no resonance above 1.3.</span>
<b>O4 "jerky"</b><span>hard-turn 1.6–3 Hz wheel-rate share below 10 m/s not more than 10 points above route 75's 19 %; sign reversals ≤ 1.5× route 75's.</span>
<b>O5 sensible estimate</b><span>sign(observer) = sign(command) on &gt; 60 % of frames; p90 &lt; 0.15 torque; &lt; 40 % of its spectrum in 0.2–1 Hz (no hunting).</span>
<b>revert</b><span>any oscillation the operator feels · a one-sided pull at rest · the estimate pinned at the clip &gt; 2 s · a des→act resonance &gt; 1.5 at 0.5–1.5 Hz.</span>
<b>the operator scores</b><span>loose · jerky on hard turns · smooth / confident / well-controlled vs the 1 kHz loop · the overshoot-to-break-friction feel. The instruments above are bands; his words are the verdict.</span>
</div>

<h2>10 · What is on the car <span class="tag">EVIDENCE · read back from the device</span></h2>
<div class="kv">
<b>EPS firmware</b><span>V293 (torque mode, cal-only on V282): fb clamp 0, Kd 0, Kp flat 120, r24 2048, map linear to ×6 — <b>unchanged this session, nothing flashed, nothing sent on CAN</b>.</span>
<b>fork</b><span><span class="mono">raayyymond-StarPilot @ Dom e44b6cd31</span> (pulled on the device from 08a5a7064; params library rebuilt for <code>AccordDobHz</code>). Tests on the comma: 254 passed, 2 failed = the pre-existing Bolt / Palisade failures.</span>
<b>config</b><span><span class="mono">toggle-config_V293_torque_mode_r5.json</span> — 22 keys, rev 4 + AccordDobHz 0.6, SteerKP 1.0, AccordTorqueKi 0.3, AccordTorqueKiHigh 0.0, AccordRateLoopGain 0.001. Revert file <span class="mono">_r5_REVERT_to_r4</span>.</span>
<b>wire instrument</b><span><code>starpilotLateralState.accordObserverTorque</code> (torque frame, the term added this frame) and <code>accordObserverFrozen</code>, appended fields @8/@9; the kit's flight read decodes both.</span>
<b>open item</b><span><code>SteerFriction</code> read 0.212 (stock) on route 75 after reading 0.0 on route 74 twenty minutes earlier; the file's timestamp shows it was rewritten ~30 s into a boot. Functionally moot on this controller (the relay is off under the hysteresis term) but a canary: a reproduction is armed — 0.0 written before this reboot, read back after it.</span>
</div>

<hr>
<p class="note">Sources: <span class="mono">rlog-tools/studies/grind/</span> — <span class="mono">v293r3_read.py</span> (routes 75/72/73), <span class="mono">v293r5_read.py</span>, <span class="mono">_scratch/hardturn_spec.py</span>, <span class="mono">v293r5_design_pred.py</span>, <span class="mono">v293r5_design_dobb.py</span>, <span class="mono">v293r5_design_jerk.py</span>, <span class="mono">v293r5_design_ship.py</span> (reports <span class="mono">V293-REV5-DESIGN-*-2026-09-15.txt</span>), <span class="mono">v293r5_pagedata.py</span>. Fork patch <span class="mono">scratchpad/patch_fork_rev5_dob.py</span>, applied as <span class="mono">Dom e44b6cd31</span>.</p>
</main>
<script>
const D = __DATA__;
function plot(id, series, o){
  const svg = document.getElementById(id); if(!svg) return;
  const W = 520, H = o.h || 250, ml = 52, mr = o.right ? 44 : 14, mt = 10, mb = 34;
  svg.setAttribute('viewBox', `0 0 ${W} ${H}`);
  const xs = series.flatMap(s => s.x), ys = series.filter(s=>!s.right).flatMap(s => s.y);
  let x0 = o.x0 ?? Math.min(...xs), x1 = o.x1 ?? Math.max(...xs);
  let y0 = o.y0 ?? Math.min(...ys), y1 = o.y1 ?? Math.max(...ys);
  if (o.pad){ const p=(y1-y0)*0.08; y0-=p; y1+=p; }
  const logx = !!o.logx;
  const X = v => ml + (logx ? (Math.log10(v)-Math.log10(x0))/(Math.log10(x1)-Math.log10(x0)) : (v-x0)/(x1-x0)) * (W-ml-mr);
  const Y = v => mt + (1-(v-y0)/(y1-y0))*(H-mt-mb);
  const Yr = v => mt + (1-(v-(o.ry0??0))/((o.ry1??1)-(o.ry0??0)))*(H-mt-mb);
  let g = '';
  const xt = o.xticks || (logx ? [0.1,0.2,0.5,1,2,5,10].filter(v=>v>=x0&&v<=x1) : ticks(x0,x1));
  const yt = o.yticks || ticks(y0,y1);
  for (const v of yt){ g += `<line class="grid" x1="${ml}" x2="${W-mr}" y1="${Y(v)}" y2="${Y(v)}"/><text x="${ml-6}" y="${Y(v)+4}" text-anchor="end">${fmt(v)}</text>`; }
  for (const v of xt){ g += `<line class="grid" x1="${X(v)}" x2="${X(v)}" y1="${mt}" y2="${H-mb}"/><text x="${X(v)}" y="${H-mb+14}" text-anchor="middle">${fmt(v)}</text>`; }
  if (o.right){ for (const v of (o.rticks||[0,0.5,1])){ g += `<text x="${W-mr+6}" y="${Yr(v)+4}">${fmt(v)}</text>`; } }
  g += `<line class="axis" x1="${ml}" x2="${W-mr}" y1="${H-mb}" y2="${H-mb}"/><line class="axis" x1="${ml}" x2="${ml}" y1="${mt}" y2="${H-mb}"/>`;
  if (o.hline!==undefined) g += `<line class="grid" style="stroke:var(--ink3);stroke-dasharray:4 4" x1="${ml}" x2="${W-mr}" y1="${Y(o.hline)}" y2="${Y(o.hline)}"/>`;
  for (const s of series){
    const yy = s.right ? Yr : Y;
    let d = '', pen = false;
    for (let i=0;i<s.x.length;i++){ const x=s.x[i], y=s.y[i]; if (x<x0||x>x1||y===null||!isFinite(y)){pen=false;continue;} const yc=Math.max(mt-8,Math.min(H-mb+8,yy(y))); d += (pen?'L':'M')+X(x).toFixed(1)+' '+yc.toFixed(1); pen=true; }
    g += `<path d="${d}" fill="none" stroke-width="${s.w||2}" class="${s.cls||''}" style="${s.style||''}" stroke-linejoin="round"/>`;
  }
  g += `<text x="${(ml+W-mr)/2}" y="${H-4}" text-anchor="middle">${o.xl||''}</text>`;
  g += `<text transform="translate(12 ${(mt+H-mb)/2}) rotate(-90)" text-anchor="middle">${o.yl||''}</text>`;
  svg.innerHTML = g;
}
function ticks(a,b){ const r=b-a; const step=Math.pow(10,Math.floor(Math.log10(r)))*( r/Math.pow(10,Math.floor(Math.log10(r)))>5?1:(r/Math.pow(10,Math.floor(Math.log10(r)))>2?0.5:0.2)); const t=[]; for(let v=Math.ceil(a/step)*step; v<=b+1e-9; v+=step) t.push(+v.toFixed(6)); return t; }
function fmt(v){ return Math.abs(v)>=100?v.toFixed(0):(Math.abs(v)>=10?v.toFixed(0):(Math.abs(v)>=1?(+v.toFixed(2)).toString():(+v.toFixed(4)).toString())); }
const dash = 'stroke-dasharray:6 4';
// rate loop phase
plot('p_rlphase', [
  {x:D.rlphase.f, y:D.rlphase.rc03, cls:'r4'}, {x:D.rlphase.f, y:D.rlphase.rc01, cls:'r5'}], {logx:true, x0:0.1, x1:10, y0:-300, y1:0, yticks:[-270,-180,-90,0], hline:-90, xl:'Hz', yl:'phase of the damping torque, deg'});
// Q
plot('p_qmag', [{x:D.Q.f, y:D.Q.mag, cls:'r5'}, {x:D.Q8.f, y:D.Q8.mag, cls:'r4', style:dash}], {logx:true, x0:0.05, x1:10, y0:0, y1:1.05, yticks:[0,0.25,0.5,0.75,1], xl:'Hz', yl:'|Q|', xticks:[0.05,0.1,0.2,0.5,1,2,5,10]});
plot('p_qre', [{x:D.Q.f, y:D.Q.re, cls:'r5'}, {x:D.Q8.f, y:D.Q8.re, cls:'r4', style:dash}], {logx:true, x0:0.05, x1:10, y0:-0.3, y1:1.05, yticks:[-0.25,0,0.25,0.5,0.75,1], hline:0, xl:'Hz', yl:'Re Q', xticks:[0.05,0.1,0.2,0.5,1,2,5,10]});
// damping budget 12 m/s
const d12 = D.damping['12'];
plot('p_damp12', [
  {x:d12.f, y:d12.f.map(_=>d12.b_mode), cls:'plant', w:1.5}, {x:d12.f, y:d12.f.map(_=>d12.b_ident), cls:'plant', w:1.5, style:dash},
  {x:d12.f, y:d12.rl_r4, cls:'r4'}, {x:d12.f, y:d12.rl_r5, cls:'r5'}, {x:d12.f, y:d12.dob, cls:'r5', style:dash}],
  {logx:true, x0:0.05, x1:10, y0:-0.0012, y1:0.0042, yticks:[-0.001,0,0.001,0.002,0.003,0.004], hline:0, xl:'Hz  (the plant mode sits at ≈'+d12.mode_hz.toFixed(1)+' Hz open, 2–2.7 Hz closed)', yl:'damping, torque per deg/s', xticks:[0.05,0.1,0.2,0.5,1,2,5,10]});
// traces
function tr(id, key, opts){
  const t = D.traces[key]; const s = [];
  if (t.des) s.push({x:t.t, y:t.des, style:'stroke:var(--ink3);'+dash, w:1.5});
  s.push({x:t.t, y:t.R4.meas, cls:'r4'}); s.push({x:t.t, y:t.R5.meas, cls:'r5'});
  if (opts.dob) s.push({x:t.t, y:t.R5.dob.map(v=>v*10), cls:'r5', style:dash, w:1.5});
  plot(id, s, Object.assign({xl:'s', yl:'lateral acceleration, m/s²', pad:true}, opts));
}
tr('p_step8', 'step_8', {x0:0.5, x1:5, y0:-0.1, y1:1.6, yticks:[0,0.5,1,1.5]});
tr('p_step19', 'step_19', {x0:0.5, x1:5, y0:-0.1, y1:1.6, yticks:[0,0.5,1,1.5]});
tr('p_dist19', 'dist_19', {x0:1.5, x1:6, y0:-0.25, y1:0.05, yticks:[-0.2,-0.1,0], yl:'lateral acceleration error, m/s²'});
tr('p_hard8', 'hard_8', {x0:0.5, x1:8, y0:-0.2, y1:3.0, yticks:[0,1,2,3], dob:true});
// LERPs
plot('p_ki', [{x:D.lerp.v, y:D.lerp.ki_r4, cls:'r4'}, {x:D.lerp.v, y:D.lerp.ki_r5, cls:'r5'}], {x0:0, x1:32, y0:0, y1:2.8, yticks:[0,0.5,1,1.5,2,2.5], xl:'speed, m/s', yl:'Ki', xticks:[0,8,12,18,26,32]});
plot('p_kv', [{x:D.lerp.v, y:D.lerp.kv_r4, cls:'r4'}, {x:D.lerp.v, y:D.lerp.kv_r5, cls:'r5'}, {x:D.lerp.v, y:D.lerp.dob_fade, right:true, style:'stroke:var(--ink3);'+dash, w:1.5}],
  {x0:0, x1:32, y0:0, y1:0.0011, yticks:[0,0.0002,0.0004,0.0006,0.0008,0.001], right:true, ry0:0, ry1:1, rticks:[0,0.5,1], xl:'speed, m/s', yl:'Kv, torque per deg/s', xticks:[0,3,6,12,18,26,32]});
</script>
"""

html = HTML.replace("__DATA__", DATA)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
open(OUT, "w", encoding="utf-8", newline="\n").write(html)
print("written", OUT, len(html) // 1024, "KB")
