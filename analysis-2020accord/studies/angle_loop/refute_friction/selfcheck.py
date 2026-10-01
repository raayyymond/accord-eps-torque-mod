import numpy as np, sys
import fric_lib as F
import lane_mirror_v295 as LM
import harness_time as HT
cal = HT.base_cal()
# 1. LaneC0 (cave off, bleed off) == scalar byte-exact mirror with the C0 cals, random inputs, run always or skip(ramp0&req0)
c = dict(cal, kp=((0,68,112,136,208),(450,)*5), Ki=199, ICL=4096, DB=0, kd=((0,11,22,32),(16,)*4), DCL=10240)
ed = LM.Edits(x_src="angle", fb_op="sum", sp_src="69ae", d_src="rate")
rng = np.random.default_rng(3)
lane = F.LaneC0(1, cave=False, bleed=False)
st = LM.LaneState()
ang=rate=tq=0; raw=0; mism=0; N=40000
for t in range(N):
    ang = int(np.clip(ang + rng.integers(-40,41), -6000, 6000)); rate=int(np.clip(rate+rng.integers(-30,31),-3000,3000))
    if t%10==0: raw=int(rng.integers(-4000,4000))
    tq = int(np.clip(tq + rng.integers(-100,101), -3000, 3000))
    sk = (t//500)%7==3
    ramp, req = (0,0) if sk else (0x8000,1)
    cmd = LM.e4_handler(raw)
    Ts = LM.lane_tick(st, c, ed, rate=rate, angle=ang, cmd69ae=cmd, tq=tq, speed=3000, ramp=ramp, act6806=1, req6805=req, pol=-1)
    Tv = lane.tick(ang, rate, cmd, tq, 3000, ramp, 1, req)
    if int(Ts)!=int(Tv[0]) or (st.log.get('I') or 0)!=int(lane.log['I'][0]):
        mism+=1
print("CHECK 1 LaneC0(cave off) vs lane_mirror_v295 scalar, %d ticks: %d mismatches" % (N, mism))
# 2. the cave table: G at the knots and at every v, vs the Honda divq LERP over (X, G)
X=[691,1152,1843,2880,4378,5990]; Y=[256,284,341,569,1422,1707]
d=[abs(F.cave_G(v)-LM.lerp(X,Y,v)) for v in range(0,65536)]
print("CHECK 2 cave G vs Honda LERP over 0..65535: max |diff| %d ; G at knots %s ; G(0)=%d G(65535)=%d" % (max(d), [F.cave_G(x) for x in X], F.cave_G(0), F.cave_G(65535)))
for v in (3,4,5,5.5,6,6.5,7,8,10,12.5,15,19,22,26,30):
    print("   v %5.1f m/s  counts %5d  G %4d  Kp_eff %6.1f  T/deg(hands-off, f=254/256) %5.1f" % (v, F.spd_counts(v), F.cave_G(F.spd_counts(v)), F.kp_eff(v), F.kp_eff(v)*16*10/256*254/256*5346/32768))
