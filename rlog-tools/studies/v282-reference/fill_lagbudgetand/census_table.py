import json
res=json.load(open('census_params_raw.json'))
KEYS=['SteerFriction','SteerLatAccel','SteerKP','SteerKI','AccordTorqueKi','AccordTorqueKiHigh','KeepLearnedLatAccelOffset','AccordRatePlantFF','AccordRefFilter',
      'AccordRateLoopGain','AccordDobHz','AccordHoldLevel','AccordHoldMap','AccordFrictionHyst','AccordFrictionHystBand','AccordFFRateGain','AccordErrorNotchQ',
      'ForceTorqueController','AdvancedLateralTune','UseAutoSteerDelay','SteerDelay','SteerDelayStock','LatSmoothSeconds','DeveloperUI','SafeMode',
      'SteerRatio','AccordVariableSteerRatio','AccordTurnFFTaper','AccordEpsGainScale','AccordEpsSpringScale','AccordDither','LateralTune','NNFF','NNFFLite','TurnDesires','HondaLateralPidKpScale','HondaLateralPidKiScale']
allk=set()
for r,per in res.items():
    for s in per: allk|=set(s.get('params',{}).keys())
extra=sorted(k for k in allk if (k.startswith('Accord') or k.startswith('Steer') or 'Lat' in k[:4]) and k not in KEYS)
KEYS+=extra
out={}
for r,per in res.items():
    col={}
    for k in KEYS:
        vals=[]
        for s in per:
            v=s.get('params',{}).get(k,'<abs>')
            if not vals or vals[-1][1]!=v: vals.append((s['seg'],v))
        col[k]=vals
    out[r]=dict(commit=per[0].get('commit'), nseg=len(per), cp=per[0].get('cp'), params=col)
json.dump(out, open('census_params.json','w'), indent=1)
rs=list(res)
short={r:r[6:8]+'-'+r[10:14] for r in rs}
print('%-28s'%'param'+''.join('%11s'%short[r] for r in rs))
for k in KEYS:
    row=[]; same=True
    for r in rs:
        v=out[r]['params'][k]
        txt=v[0][1] if len(v)==1 else '*'+'/'.join(x[1] for x in v)
        row.append(txt[:10])
    if all(x=='<abs>' for x in row): continue
    print('%-28s'%k[:28]+''.join('%11s'%x for x in row))
print('commit', [out[r]['commit'] for r in rs])
for r in rs:
    for k in KEYS:
        v=out[r]['params'][k]
        if len(v)>1: print('WITHIN-ROUTE CHANGE', r, k, v)
