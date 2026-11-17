import itertools,math
from c_pert import case
res=[]
for v in (3.0,8.0):
  for bm,xd,dl,sc,km in itertools.product((0.5,0.3,0.2,0.1,0.05),(0,10,20),(2,4),(1.0,0.5,2.0),(1.3,0.7)):
    g,T,fT,Ms,en=case(v,bm,km,0.035,dl,xd,sc)
    if g<3 or T>6: res.append((bm,v,xd,dl,sc,km,g,T,fT))
res.sort(reverse=True)
print('strict-fail (GM<3 or T>+6): bm, v, extra angle delay ms, lane delay, lane scale, k | GM, T@f')
for r in res[:14]: print('bm%.2f v%g xd%d dl%d sc%.1f km%.1f | GM%.1f T%+.1f@%.0f'%r)
print(len(res),'fails; largest bm failing =',res[0][0] if res else None)
