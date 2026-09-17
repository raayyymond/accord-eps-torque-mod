import sys
sys.path.insert(0, 'C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/rlog-tools/studies/v282-reference')
import v282cmp as V
import numpy as np

for rk in ['00000064--ce6b0b0ebb','0000006c--2bc842dbac','0000006c--68c6e94b17','0000006d--05e83bb04f',
           '0000006e--6ca3e014fd','00000075--6c8687d5bd','00000076--d0b7ea7e4d']:
    S = V.load(rk)
    u = V.usable(S)
    yaw = S['la_yaw'][u]
    pose = S['la_pose'][u]
    act = S['la_act'][u]
    print(rk, 'la_yaw std', np.nanstd(yaw), 'nonzero frac', np.mean(np.abs(np.nan_to_num(yaw))>1e-6),
          '| la_pose std', np.nanstd(pose), '| la_act std', np.nanstd(act))
    del S
