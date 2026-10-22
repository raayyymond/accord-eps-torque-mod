# V300 rev 2 (sha 7d58c823...) LKAS PID: integer mirror of the angle-error -> P -> sum clamp chain.
# Every constant byte-read LE from the V300 image. Steady state: theta[n]==theta[n-1], D==0 (wheel still).
import struct
IMG='C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v300_V300-REV2-RELEASE-ANGLELOOP.FROMSTOCK-KP112.KD48.KI40.ICL8192-FRZ1229.CAP4096.6144-NOTELEMETRY.NOMAP.STOCKASSIST.DAMPAXIS.V299.A16C_plain_image.bin'
v=open(IMG,'rb').read(); h=lambda a:struct.unpack_from('<H',v,a)[0]; sh=lambda a:struct.unpack_from('<h',v,a)[0]
A_FB,B_FB,FBCLP = sh(0xC63E8),h(0xC63EA),h(0xC62E6)       # 0 , 8192 , 65535
KP_REC=struct.unpack_from('<I',v,0xCB994+4*7)[0]; KP=[h(KP_REC+0xC+2*k) for k in range(5)]
KD_REC=struct.unpack_from('<I',v,0xCB7D4+4*7)[0]; KD=[h(KD_REC+0xA+2*k) for k in range(4)]
PCLP,ICLc,DCLP,SCLP,OCLP = h(0xC61BC),h(0xC61BA),h(0xC61B6),h(0xC61BE),h(0xC61B4)
KI,DB = h(0xC63E6),h(0xC62E4)
GAIN = sh(0xC6CD0); LAG_A,LAG_B = sh(0xC63EC),h(0xC63EE)
TBL=[(h(a),h(a+2),sh(a+4)) for a in range(0xC4CDA,0xC4D04,6)]
assert set(KP)=={112} and set(KD)=={48}
def sar(x,n): return x>>n                                  # python >> on int == arithmetic shift
def G(vw):                                                 # cave 0xC4C18..0xC4C52
    X0,Y0,_=TBL[0]
    if vw<=X0: return TBL[0][1]                            # 0xC4C28 bh / 0xC4C2A ld.hu 2[r9]
    k=0
    while TBL[k+1][0] < vw: k+=1                           # 0xC4C30..0xC4C3C (bnh exits when vw<=Xnext)
    X,Y,s=TBL[k]; return sar((vw-X)*s,12)+Y                # 0xC4C3E..0xC4C52
def fb(theta,theta_prev):                                  # 0x28F4C..0x28FBE (a=0,b=8192)
    t_prev = sar(B_FB*theta_prev,10)+sar(A_FB*0,10)
    t = sar(B_FB*theta,10)+sar(A_FB*t_prev,10)             # 0x28F8E..0x28FA2
    return max(-FBCLP,min(FBCLP,t_prev+t))                 # 0x28FA4 add, clamp 0x28FA6..0x28FBC
def E_prime(wire,theta,vw):
    sp=max(-0x4000,min(0x4000,-4*wire))                    # 0x526CC..0x526F2 -> gp-0x69ae ; 0x29D6A ld.h
    E=4*sp - fb(theta,theta)                               # 0xC4C00 shl 2 ; 0xC4C02 sub r26
    return sar(E*G(vw),8)                                  # 0xC4C54 mul ; 0xC4C58 sar 8
def P(Ep): return max(-PCLP,min(PCLP,sar(Ep*KP[0],8)))     # 0x29E34..0x29E5C
def cap(vw,theta_dir):                                     # cave freeze cap, in I>>7 (= sum) units
    t=max(0,theta_dir)
    if vw>0xB40: c=64*t+0x4E2                              # 0xC4CA6
    else: c=min(16*t+0x4E2, 0x1000 if vw<=0x566 else 0x1800)  # 0xC4C86..0xC4CA0
    return min(c, sar(ICLc<<10,3)>>7)                      # hard ICL 0x29DA0..0x29DC2
def taper(S,fac=254): return sar(fac*S,8)                  # 0x2A0B4..0x2A0C2, fac=((255*255)&0xFFFF)>>8
def sumclamp(Sp): return max(-SCLP,min(SCLP,Sp))           # 0x2A13E..0x2A162
print('Kp',KP,'Kd',KD,'Pclp',PCLP,'ICL->I>>7',sar(ICLc<<10,3)>>7,'Dclp',DCLP,'Sclp',SCLP,'Oclp',OCLP,'Ki',KI,'DB',DB,'gain',GAIN)
print('G table',TBL)
# smallest pre-taper S with taper(S)>=SCLP
S_need=next(S for S in range(15000,16000) if taper(S)>=SCLP); print('pre-taper S reaching Kmax:',S_need)
def first_delta(vw,target):          # smallest error (0.1-deg counts) with P>=target; wire=-(theta+delta), theta=0
    for d in range(0,40000):
        if P(E_prime(-d,0,vw))>=target: return d
    return None
for kmh in [0,10,20,21.6,25,30,40,45,50,60,70,80,100,120]:
    vw=int(kmh*64); g=G(vw)
    row=[f'{kmh:6} km/h vw={vw:5} G={g:4}']
    dP=first_delta(vw,PCLP); row.append(f'P-clamp at {dP/10 if dP else None} deg')
    for lab,I in [('I=1250(theta0)',cap(vw,0)),('I=capmax',cap(vw,10**6)),('I=ICL8192',8192)]:
        tgt=S_need-I; d=first_delta(vw,tgt) if tgt>0 else 0
        row.append(f'{lab}:{I} -> P>={tgt} at {d/10} deg')
    print(' | '.join(row))
# output side: delivered for S'=15360 through the lag (DC) and gain, ramp full, polarity -1, r11=0
s=0
for n in range(5000):
    t=sar(LAG_A*s,10)+sar(SCLP*LAG_B,10); y=sar(s+t,5); s=t
out=sar(y*32768,15); dl=sar(out*(-1*GAIN),15)
print('lag y at S=15360:',y,'delivered',dl,'(clamp',OCLP,') S needed for out clamp:',next(S for S in range(0,40000) if abs(sar((S*LAG_B*2>>10)//32*1,0))>0 and abs(sar(sar((S*LAG_B*2)>>10,5)*-GAIN,15))>=OCLP) if False else 'n/a')
