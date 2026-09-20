import json, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
H='C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/lowspeed/d_v282low'
M=json.load(open(f'{H}/d_matched.json')); C=json.load(open(f'{H}/d_results.json'))['C']
G=['V282','V282old','T64','T64B','T5','T4']; COL=['#2a78d6','#eb6834','#1baf7a','#eda100','#e87ba4','#008300']
plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'axes.grid':True,'grid.color':'#e5e5e5'})
fig,ax=plt.subplots(2,3,figsize=(13,7.5))
for row,vb in enumerate(['2.5-8','8-15']):
    for gi,g in enumerate(G):
        xs,e,s,el,sl=[],[],[],[],[]
        for k,r in M.items():
            v,rb,ab,gg=k.split('|')
            if v!=vb or gg!=g or ab!='0-45': continue
            xs.append(r['rate']); e.append(r['err']); s.append(r['sr1835']); el.append(r['err_ci']); sl.append(r['sr1835_ci'])
        o=np.argsort(xs); xs=np.array(xs)[o]
        if not len(xs): continue
        for a,y,ci in ((ax[row,0],np.array(s)[o],np.array(sl)[o]),(ax[row,1],np.array(e)[o],np.array(el)[o])):
            a.plot(xs,y,'-o',color=COL[gi],lw=2,ms=6,label=g)
            a.vlines(xs,ci[:,0],ci[:,1],color=COL[gi],lw=1,alpha=.6)
        c=C[f'{vb}|cmd_to_rate|{g}']
        if c: ax[row,2].plot([0.65,1.5,3,7],[c[b]['coh'] for b in ['0.3-1.0','1.0-2.0','2.0-4.0','4.0-10.0']],'-o',color=COL[gi],lw=2,ms=6,label=g)
    for a in ax[row,:2]: a.set_xscale('log'); a.set_xlabel('mean |desired steering rate| in block, deg/s')
    ax[row,0].set_ylabel('1.8-3.5 Hz steering-rate RMS, deg/s'); ax[row,1].set_ylabel('angle error vs model RMS, deg (0.20 s lead)')
    ax[row,0].set_title(f'{vb} m/s, |desired angle|<45: wheel-mode band'); ax[row,1].set_title(f'{vb} m/s: tracking error, demand-matched')
    ax[row,2].set_xscale('log'); ax[row,2].set_xlabel('band centre, Hz'); ax[row,2].set_ylabel('coherence command -> steering rate'); ax[row,2].set_ylim(0,1)
    ax[row,2].set_title(f'{vb} m/s: does the wheel follow the command?')
ax[0,0].legend(frameon=False,ncol=2)
fig.suptitle('V282 (rate servo) vs torque mode below 15 m/s. Bars = route-cluster bootstrap 95% CI. EVIDENCE: d_matched.py / d_analyze.py',fontsize=10)
fig.tight_layout(); fig.savefig(f'{H}/d_fig_lowspeed_target.png',dpi=130)
