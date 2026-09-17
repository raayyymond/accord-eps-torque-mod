"""Figures for s1_goal from s1_results.json / s1_perroute.json / s1_importance.json."""
import json, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
H='C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference/s1_goal/'
R=json.load(open(H+'s1_results.json')); C=R['cells']; P=json.load(open(H+'s1_perroute.json')); I=json.load(open(H+'s1_importance.json'))
GR=["V282","V282old","T64","T64B","T5","T4"]; COL=dict(V282="#1b7837",V282old="#7fbf7b",T64="#c51b7d",T64B="#e9a3c9",T5="#8073ac",T4="#b2abd2")
VB=["2-8","8-15","15-22",">22"]; BA=["0.05-0.15","0.15-0.3","0.3-0.6","0.6-1.2","1.2-2.5"]
def cell(g,vb,ba,t='all'):
    for c in C:
        if c['group']==g and c['vb']==vb and c['band']==ba and c['terc']==t: return c
# fig1 per-route highway |H|
fig,ax=plt.subplots(figsize=(8,4.5))
for bi,ba in enumerate(["0.05-0.15","0.15-0.3","0.3-0.6"]):
    for gi,g in enumerate(GR):
        xs=[r['H_pose'] for r in P if r['group']==g and r['band']==ba and r['v']=='>15']
        ax.scatter(np.full(len(xs),bi+(gi-2.5)*0.12),xs,color=COL[g],s=40,label=g if bi==0 else None,edgecolor='k',lw=0.4)
ax.axhline(1,color='k',lw=0.8,ls='--'); ax.set_xticks(range(3)); ax.set_xticklabels([b+" Hz" for b in ["0.05-0.15","0.15-0.30","0.30-0.60"]])
ax.set_ylabel("|H| model -> yaw-rate x v (per route)"); ax.set_title("Highway (>15 m/s) delivery gain per route; V282 = 0.86-1.18, not 1.0")
ax.legend(ncol=3,fontsize=8); fig.tight_layout(); fig.savefig(H+'fig1_highway_gain_per_route.png',dpi=130); plt.close(fig)
# fig2 tercile lag and rel error
fig,axs=plt.subplots(2,4,figsize=(13,6),sharex=True)
for j,(vb,ba) in enumerate([("15-22","0.15-0.3"),("15-22","0.3-0.6"),(">22","0.15-0.3"),(">22","0.3-0.6")]):
    for gi,g in enumerate(GR):
        cs=[cell(g,vb,ba,t) for t in ["lo","mid","hi"]]
        xs=[i+(gi-2.5)*0.1 for i,c in enumerate(cs) if c]; cs=[c for c in cs if c]
        if not cs: continue
        axs[0,j].plot(xs,[c['lag_pDa'] for c in cs],'o-',color=COL[g],label=g)
        e=[c['rE_pD'] for c in cs]; lo=[c['rE_pD']-c['rE_pD_ci'][0] for c in cs]; hi=[c['rE_pD_ci'][1]-c['rE_pD'] for c in cs]
        axs[1,j].errorbar(xs,e,yerr=[np.maximum(lo,0),np.maximum(hi,0)],fmt='o-',color=COL[g],capsize=2)
    axs[0,j].set_title(f"{vb} m/s, {ba} Hz"); axs[1,j].set_xticks([0,1,2]); axs[1,j].set_xticklabels(["lo","mid","hi"])
axs[0,0].set_ylabel("lag model->yaw x v (s)"); axs[1,0].set_ylabel("rel. error at lat_delay")
axs[1,0].set_xlabel("demand amplitude tercile"); axs[0,0].legend(fontsize=7)
fig.suptitle("Amplitude-matched highway: torque mode lags the model 0.1-0.35 s more than V282 (lat_delay lead differs by 0.1 s); gap largest at small/mid demand"); fig.tight_layout(); fig.savefig(H+'fig2_tercile_lag_error.png',dpi=130); plt.close(fig)
# fig3 importance heatmap
fig,axs=plt.subplots(1,4,figsize=(14,3.6))
for k,g in enumerate(["T64","T64B","T5","T4"]):
    M=np.zeros((4,5))
    for r in I[g]: M[VB.index(r['vb']),BA.index(r['band'])]=r['excess_share']*100
    im=axs[k].imshow(M,cmap="Reds",vmin=0,vmax=45,origin='lower')
    for a in range(4):
        for b in range(5): axs[k].text(b,a,f"{M[a,b]:.0f}",ha='center',va='center',fontsize=8)
    axs[k].set_xticks(range(5)); axs[k].set_xticklabels(BA,rotation=45,fontsize=7); axs[k].set_yticks(range(4)); axs[k].set_yticklabels(VB)
    axs[k].set_title(f"{g}: share of excess error vs V282 (%)",fontsize=9)
fig.tight_layout(); fig.savefig(H+'fig3_importance_excess_error.png',dpi=130); plt.close(fig)
# fig4 low-speed 0.6-1.2 Hz achieved/desired rms ratio
fig,axs=plt.subplots(1,2,figsize=(9,3.8),sharey=True)
for j,vb in enumerate(["2-8","8-15"]):
    for gi,g in enumerate(GR):
        xs=[];ys=[]
        for i,t in enumerate(["lo","mid","hi"]):
            c=cell(g,vb,"0.6-1.2",t)
            if c and abs(c['rho_pL'])>1e-6: xs.append(i+(gi-2.5)*0.08); ys.append(c['G_pL']/c['rho_pL'])
        axs[j].plot(xs,ys,'o-',color=COL[g],label=g)
    axs[j].axhline(1,color='k',ls='--',lw=0.8); axs[j].set_title(f"{vb} m/s, 0.6-1.2 Hz"); axs[j].set_xticks([0,1,2]); axs[j].set_xticklabels(["lo","mid","hi"])
axs[0].set_ylabel("rms(achieved)/rms(desired)"); axs[0].legend(fontsize=7)
fig.suptitle("Low speed: extra 0.6-1.2 Hz lateral motion in large-demand manoeuvres (torque mode)"); fig.tight_layout(); fig.savefig(H+'fig4_lowspeed_excess_motion.png',dpi=130); plt.close(fig)
print("ok")
