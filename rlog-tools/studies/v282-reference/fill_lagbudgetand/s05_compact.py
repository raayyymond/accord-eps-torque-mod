import json
res=json.load(open('s04_cells.json'))
def g(c,nm):
    v=c[nm+'_gap']; lo,hi=c[nm+'_gap_ci']; return f"{v:+.2f}[{lo:+.2f},{hi:+.2f}]"
out=[]
for grp in ['V282old','T64','T64B','T5','T4']:
    out.append(f"\n== {grp} - V282   cols: x->sp(pred) | sp->act | act->pose | x->pose logged | x->pose COMMON  ; V282 abs x->pose, T abs x->pose")
    for c in res:
        if c['group']!=grp or c['band'].startswith('0.05'): continue
        ref=[r for r in res if r['group']=='V282' and r['band']==c['band'] and r['vb']==c['vb'] and r['terc']==c['terc']][0]
        out.append(f"{c['vb']:5s} {c['band']:8s} {c['terc']:3s} {ref['sec']:4.0f}/{c['sec']:<4.0f} {g(c,'model->setpoint')}({c['pred_shaping_gap']:+.2f}) | {g(c,'setpoint->la_act')} | {g(c,'la_act->la_pose')} | {g(c,'model->la_pose')} | {g(c,'COMMON model->la_pose')} ; {ref['model->la_pose']:.2f} {c['model->la_pose']:.2f}")
open('s05_compact.txt','w').write('\n'.join(out))
