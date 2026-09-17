import json, numpy as np, matplotlib
matplotlib.use('Agg'); import matplotlib.pyplot as plt
H='C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s4_texture'
C=json.load(open(f'{H}/s4_compare.json')); X=json.load(open(f'{H}/s4_extra.json')); E=json.load(open(f'{H}/s4_events.json'))
COL=dict(V282='#1f5fbf',V282old='#7fa7e0',T64='#c0392b',T64B='#e67e22',T5='#8e44ad',T4='#7f8c8d')
fig,ax=plt.subplots(1,3,figsize=(18,5.5))
st=['ge15_straight','ge15','lt15','lt15_act3','lt15_ang15']; gs=['V282old','T64','T64B','T5','T4']
for j,g in enumerate(gs):
    x=np.arange(len(st))+(j-2)*0.15
    e=[C[s][g]['mode_rms']['est'] for s in st]; lo=[C[s][g]['mode_rms']['ci_route'][0] for s in st]; hi=[C[s][g]['mode_rms']['ci_route'][1] for s in st]
    ax[0].errorbar(x,e,yerr=[np.array(e)-lo,np.array(hi)-e],fmt='o',color=COL[g],label=g,capsize=3)
ax[0].set_yscale('log'); ax[0].axhline(1,color='k',lw=.6); ax[0].set_xticks(range(len(st))); ax[0].set_xticklabels(['>=15 straight','>=15','<15','<15 moving\n(>=3 deg/s)','<15 |angle|\n>=15 deg'])
ax[0].set_title('1.8-3.0 Hz wheel-rate rms, matched ratio vs V282\n(speed x angle x activity cells; route-cluster 95% CI)'); ax[0].legend(); ax[0].grid(alpha=.3)
ev=X['events']; bins=['v0-15_rate10-40','v0-15_rate40-999','v15-40_rate0-10','v15-40_rate10-999']
for j,g in enumerate(['V282','V282old','T64','T64+T64B+T5+T4']):
    for i,b in enumerate(bins):
        o=ev.get(g,{}).get(b)
        if not o: continue
        c=COL.get(g,'#444'); ax[1].errorbar(i+(j-1.5)*0.18,o['md_post_med'],yerr=[[o['md_post_med']-o['ci'][0]],[o['ci'][1]-o['md_post_med']]],fmt='o',color=c,capsize=3,label=g if i==0 or (g=='V282' and i==0) else None)
        ax[1].annotate(str(o['n']),(i+(j-1.5)*0.18,o['md_post_med']),fontsize=7,xytext=(3,3),textcoords='offset points')
ax[1].set_yscale('log'); ax[1].set_xticks(range(4)); ax[1].set_xticklabels(['<15 m/s\npeak rate 10-40','<15 m/s\npeak rate >40','>=15 m/s\npeak rate <10','>=15 m/s\npeak rate >=10'])
ax[1].set_ylabel('deg/s'); ax[1].set_title('2-3 Hz wheel-rate rms in the 3 s after a desired-jerk event (>=0.4 m/s^3)\nmedian, route-cluster CI, n annotated'); ax[1].legend(fontsize=8); ax[1].grid(alpha=.3)
ab=['a0-5','a5-15','a15-45','a45-999']
for j,g in enumerate(['V282','V282old','T64','T64B','T5','T4']):
    L=E[g]['rate_limiter']; y=[100*L[f'v0-15_{a}']['rate_limited'] for a in ab]
    ax[2].plot(range(4),y,'o-',color=COL[g],label=g)
ax[2].set_yscale('symlog',linthresh=0.01); ax[2].set_xticks(range(4)); ax[2].set_xticklabels(['0-5','5-15','15-45','>45 deg'])
ax[2].set_title('Honda 0xE4 rate limiter binding (|d cmd| >= 120/frame), <15 m/s, % frames'); ax[2].legend(); ax[2].grid(alpha=.3)
fig.tight_layout(); fig.savefig(f'{H}/fig_texture_summary.png',dpi=110)
