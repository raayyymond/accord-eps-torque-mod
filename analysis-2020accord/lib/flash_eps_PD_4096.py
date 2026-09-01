#!/usr/bin/env python3
import argparse
import sys
import struct
import zlib
import time
from tqdm import tqdm
try:
  from panda import Panda
  from panda.python.uds import UdsClient, ACCESS_TYPE, MessageTimeoutError, NegativeResponseError, SESSION_TYPE, DATA_IDENTIFIER_TYPE, ROUTINE_CONTROL_TYPE, ROUTINE_IDENTIFIER_TYPE
except:
  print('Load panda failed!')

mod_version = "0.7 ram var test"

# torque_multiplier = abs(math_result_1_rshift_6) / 128 +
#	(table_c9a88_result * 32 - steer_angle_rate_acc_rshift_5) * table_cb994_result +
#	(increment_of_clamped_math_result_1_rshift_6_minus_angle_rate_acc * table_cb7d4_result) >> 3;

# Scale_factors with all 1 means no changes will be applied to the table

# Table lookup by math_result_1_rshift_6
# Must work with make_c9a88_patch_mod together
#                      0  1  2  3  4  5  6  7  8        9        10,       0, 1  2  3  4  5  6  7  8  9  10
#scale_factors_c9a88 = [1, 1, 1, 1, 1, 1, 1, 1, 160/128, 200/160, 255/240,  1, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.75, 2, 3, 1]
scale_factors_c9a88 = [1, 1, 1, 1, 1, 1, 1, 1, 1,       1,        1,       1, 1.5, 1.5, 1.5, 1.5, 1.5, 1.5, 1.75, 2, 3, 1]
#scale_factors_c9a88 = [1, 1, 1, 1, 1, 1, 1, 1, 1,       1,        1,       1, 1, 1, 1, 1, 1, 1, 1, 2, 2, 1]
#|----------------input lookup-----------------||------------output interpolation--------------|
#  0   1  2   3   4   5   6   7   8    9    10 , 11, 12   13   14   15   16   17   18   19   20   21
# [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0,  16,  28,  34,  48,  92,  124, 148, 162, 172, 0
# Input    			  HitIndex 	Output
# <= 0		 		  0		  	column[0+11]=0
# >0 && <= 12         1         (column[1+11] - column[0+11]) * (Input - column[1]) / (column[2] - column[1]) + column[0+11]
# >12 && <= 20        2         (column[2+11] - column[1+11]) * (Input - column[2]) / (column[3] - column[2]) + column[1+11]
# >20 && <= 24        3         (column[3+11] - column[2+11]) * (Input - column[3]) / (column[4] - column[3]) + column[2+11]
# ...
# > 240		 		  0		  	column[9+11]=172

patch_table_for_c9a88 = {
  'TVA-A150':[
  ],
  'TVA-A160':[
    # 00029cd0 85  87  f1  74    ld.bu      LAB_000074ee+2 [tp],r16 =>DAT_000c64f0            = F0h
    # 00029cd0 a5  87  89  78    ld.bu      0x7889 [tp],r16                                     FFh
    (0x29cd0, 0x85, 0xa5),
    (0x29cd2, 0xf1, 0x89),
    (0x29cd3, 0x74, 0x78),
    # 00029ce0 85  3f  f1  74    ld.bu      LAB_000074ee+2 [tp],r7=>DAT_000c64f0             = F0h
    # 00029ce0 a5  3f  89  78    ld.bu      0x7889 [tp],r7                                      FFh
    (0x29ce0, 0x85, 0xa5),
    (0x29ce2, 0xf1, 0x89),
    (0x29ce3, 0x74, 0x78),
    # 00029ce6 a5  87  f1  74    ld.bu      LAB_000074ee+3 [tp],r16 =>DAT_000c64f1            = F0h
    # 00029ce6 a5  87  89  78    ld.bu      0x7889 [tp],r16                                     FFh
    (0x29ce8, 0xf1, 0x89),
    (0x29ce9, 0x74, 0x78),
    # 00029cf0 a5  3f  f1  74    ld.bu      LAB_000074ee+3 [tp],r7=>DAT_000c64f1             = F0h
    # 00029cf0 a5  3f  89  78    ld.bu      0x7889 [tp],r7                                      FFh
    (0x29cf2, 0xf1, 0x89),
    (0x29cf3, 0x74, 0x78),

  ]
}

# Table lookup by math_result_1_rshift_6
#                      0  1  2  3  4  5  6  7  8  9  10, 11
scale_factors_cb994 = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1,  1]
#|--------input lookup---||----output interpolation----|
#  0  1  2   3    4    5    6    7    8    9    10   11
# [5, 0, 68, 112, 136, 208, 205, 461, 614, 696, 696, 0]
# Input    			  HitIndex 	Output
# <= 0		 		  6		  	column[6]=205
# >0 && <= 68         6         (column[7] - column[6]) * (Input - column[1]) / (column[2] - column[1]) + column[6]
# >68 && <= 112       7         (column[8] - column[7]) * (Input - column[2]) / (column[3] - column[2]) + column[7]
# >112 && <= 136      8         (column[9] - column[8]) * (Input - column[3]) / (column[4] - column[3]) + column[8]
# >=136 && < 208      9         (column[10] - column[9]) * (Input - column[4]) / (column[5] - column[4]) + column[9]
# >= 208	 		  10		column[10]=696


# Table lookup by increment_of_clamped_math_result_1_rshift_6_minus_angle_rate_acc
#                      0  1  2  3  4  5  6  7  8  9
scale_factors_cb7d4 = [1, 1, 1, 1, 1, 1, 1, 2, 2, 1]
#|---input lookup---||--output interpolation-|
#  0  1   2   3   4   5   6    7    8     9
# [4, 0, 11, 22, 32, 128, 128, 128, 128,  0] ,
# Input    			HitIndex 	Output
# <= 0		 		5		  	column[5]=128
# < 0xB				6			(column[6] - column[5]) * (Input - column[1]) / (column[2] - column[1]) + column[5]=128
# > 0xB & < 16		7			(column[7] - column[6]) * (Input - column[2]) / (column[3] - column[2]) + column[6]=128
# >0x20		 		8			column[8]=128


# Table for clamping STEER_TORQUE to 15360/4 = 3840
# Dead zone for vehicle speed > 7424
#                      0  1  2  3  4  5  6  7  8  9  10           11           12           13           14           15           16           17     18           19
#scale_factors_cb844 = [1] * 20
# Must work with make_c9a88_patch_mod together
scale_factors_cb844 = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 16384/15360, 16384/15360, 16384/15360, 16384/15360, 16384/15360, 16384/15360, 16384/15360, 16384/15360, 16384/15360, 1]
#scale_factors_cb844 = [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1]
#|-----------------input lookup----------------------------||-------------------output interpolation------------------------|
#  0  1      2     3    4     5     6     7     8     9     10     11     12     13     14     15     16     17     18     19
# [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
# [4, 0, 11, 22, 32, 128, 128, 128, 128,  0] ,
# Input    			HitIndex 	Output
# <= 0		 		5		  	column[5]=128
# < 0xB				6			(column[6] - column[5]) * (Input - column[1]) / (column[2] - column[1]) + column[5]=128
# > 0xB & < 16		7			(column[7] - column[6]) * (Input - column[2]) / (column[3] - column[2]) + column[6]=128
# >0x20		 		8			column[8]=128


accord_a150_a160_torque_table_c9a88_stock_vals = {
#          0  1   2   3   4   5   6    7    8    9  10,  0  1   2   3   4   5   6    7    8    9    10
0xe4000 : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 16, 28, 34, 48, 92, 124, 148, 162, 172, 0] ,
0xe402c : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 24, 42, 50, 62, 100, 126, 154, 166, 172, 0] ,
0xe4058 : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 11, 26, 35, 56, 129, 158, 172, 174, 180, 0] ,
0xe4084 : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 24, 42, 50, 62, 100, 126, 154, 166, 172, 0] ,
0xe40b0 : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 16, 28, 34, 48, 92, 124, 148, 162, 172, 0] ,
0xe40dc : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 11, 26, 35, 56, 129, 158, 172, 174, 180, 0] ,
0xe5000 : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 24, 42, 50, 62, 100, 126, 154, 166, 172, 0] ,
0xe502c : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 24, 42, 50, 62, 100, 126, 154, 166, 172, 0] ,
0xe5058 : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 12, 27, 36, 51, 103, 153, 180, 184, 188, 0] ,
0xe5084 : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 12, 27, 36, 51, 103, 153, 180, 184, 188, 0] ,
0xe50b0 : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 11, 26, 35, 56, 129, 158, 172, 174, 180, 0] ,
0xe50dc : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 11, 26, 35, 56, 129, 158, 172, 174, 180, 0] ,
0xe6000 : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 11, 26, 35, 56, 129, 158, 172, 174, 180, 0] ,
0xe602c : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 11, 26, 35, 56, 129, 158, 172, 174, 180, 0] ,
0xe6058 : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 11, 26, 35, 56, 129, 158, 172, 174, 180, 0] ,
0xe6084 : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 11, 26, 35, 56, 129, 158, 172, 174, 180, 0] ,
0xe60b0 : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 11, 26, 35, 56, 129, 158, 172, 174, 180, 0] ,
0xe60dc : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 11, 26, 35, 56, 129, 158, 172, 174, 180, 0] ,
0xe7000 : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 11, 26, 35, 56, 129, 158, 172, 174, 180, 0] ,
0xe702c : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 11, 26, 35, 56, 129, 158, 172, 174, 180, 0] ,
0xe7058 : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 11, 26, 35, 56, 129, 158, 172, 174, 180, 0] ,
0xe7084 : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 11, 26, 35, 56, 129, 158, 172, 174, 180, 0] ,
0xe70b0 : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 11, 26, 35, 56, 129, 158, 172, 174, 180, 0] ,
0xe70dc : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 11, 26, 35, 56, 129, 158, 172, 174, 180, 0] ,
0xe8000 : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 11, 26, 35, 56, 129, 158, 172, 174, 180, 0] ,
0xe802c : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 11, 26, 35, 56, 129, 158, 172, 174, 180, 0] ,
0xe8058 : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 11, 26, 35, 56, 129, 158, 172, 174, 180, 0] ,
0xe8084 : [10, 0, 12, 20, 24, 32, 64, 96, 128, 160, 240, 0, 11, 26, 35, 56, 129, 158, 172, 174, 180, 0] ,
}

accord_a150_a160_torque_table_cb994_stock_vals = {
0xe4360 : [5, 0, 68, 112, 136, 208, 205, 461, 614, 696, 696, 0] ,
0xe4378 : [5, 0, 68, 112, 136, 208, 266, 532, 696, 696, 696, 0] ,
0xe4390 : [5, 0, 48, 128, 160, 208, 205, 410, 717, 717, 717, 0] ,
0xe43a8 : [5, 0, 68, 112, 136, 208, 248, 512, 645, 696, 696, 0] ,
0xe43c0 : [5, 0, 68, 112, 136, 208, 205, 461, 614, 696, 696, 0] ,
0xe43d8 : [5, 0, 48, 128, 160, 208, 205, 410, 717, 717, 717, 0] ,
0xe5360 : [5, 0, 68, 112, 136, 208, 266, 532, 696, 696, 696, 0] ,
0xe5378 : [5, 0, 68, 112, 136, 208, 248, 512, 645, 696, 696, 0] ,
0xe5390 : [5, 0, 64, 112, 136, 208, 248, 517, 717, 717, 717, 0] ,
0xe53a8 : [5, 0, 64, 112, 136, 208, 248, 517, 717, 717, 717, 0] ,
0xe53c0 : [5, 0, 48, 112, 160, 208, 307, 563, 666, 666, 666, 0] ,
0xe53d8 : [5, 0, 48, 112, 160, 208, 307, 563, 666, 666, 666, 0] ,
0xe6360 : [5, 0, 48, 112, 160, 208, 307, 563, 666, 666, 666, 0] ,
0xe6378 : [5, 0, 48, 112, 160, 208, 307, 563, 666, 666, 666, 0] ,
0xe6390 : [5, 0, 48, 112, 160, 208, 307, 563, 666, 666, 666, 0] ,
0xe63a8 : [5, 0, 48, 112, 160, 208, 307, 563, 666, 666, 666, 0] ,
0xe63c0 : [5, 0, 48, 112, 160, 208, 307, 563, 666, 666, 666, 0] ,
0xe63d8 : [5, 0, 48, 112, 160, 208, 307, 563, 666, 666, 666, 0] ,
0xe7360 : [5, 0, 48, 112, 160, 208, 307, 563, 666, 666, 666, 0] ,
0xe7378 : [5, 0, 48, 112, 160, 208, 307, 563, 666, 666, 666, 0] ,
0xe7390 : [5, 0, 48, 112, 160, 208, 307, 563, 666, 666, 666, 0] ,
0xe73a8 : [5, 0, 48, 112, 160, 208, 307, 563, 666, 666, 666, 0] ,
0xe73c0 : [5, 0, 48, 112, 160, 208, 307, 563, 666, 666, 666, 0] ,
0xe73d8 : [5, 0, 48, 112, 160, 208, 307, 563, 666, 666, 666, 0] ,
0xe8240 : [5, 0, 48, 112, 160, 208, 307, 563, 666, 666, 666, 0] ,
0xe8258 : [5, 0, 48, 112, 160, 208, 307, 563, 666, 666, 666, 0] ,
0xe8270 : [5, 0, 48, 112, 160, 208, 307, 563, 666, 666, 666, 0] ,
0xe8288 : [5, 0, 48, 112, 160, 208, 307, 563, 666, 666, 666, 0] ,
}

accord_a150_a160_torque_table_cb7d4_stock_vals = {
0xe4108 : [4, 0, 11, 22, 32, 128, 128, 128, 128, 0] ,
0xe411c : [4, 0, 11, 22, 32, 128, 128, 128, 128, 0] ,
0xe4130 : [4, 0, 11, 22, 32, 64, 64, 64, 64, 0] ,
0xe4144 : [4, 0, 11, 22, 32, 128, 128, 128, 128, 0] ,
0xe4158 : [4, 0, 11, 22, 32, 128, 128, 128, 128, 0] ,
0xe416c : [4, 0, 11, 22, 32, 64, 64, 64, 64, 0] ,
0xe5108 : [4, 0, 11, 22, 32, 128, 128, 128, 128, 0] ,
0xe511c : [4, 0, 11, 22, 32, 128, 128, 128, 128, 0] ,
0xe5130 : [4, 0, 11, 22, 32, 128, 128, 128, 128, 0] ,
0xe5144 : [4, 0, 11, 22, 32, 128, 128, 128, 128, 0] ,
0xe5158 : [4, 0, 11, 22, 32, 64, 64, 64, 64, 0] ,
0xe516c : [4, 0, 11, 22, 32, 64, 64, 64, 64, 0] ,
0xe6108 : [4, 0, 11, 22, 32, 64, 64, 64, 64, 0] ,
0xe611c : [4, 0, 11, 22, 32, 64, 64, 64, 64, 0] ,
0xe6130 : [4, 0, 11, 22, 32, 64, 64, 64, 64, 0] ,
0xe6144 : [4, 0, 11, 22, 32, 64, 64, 64, 64, 0] ,
0xe6158 : [4, 0, 11, 22, 32, 64, 64, 64, 64, 0] ,
0xe616c : [4, 0, 11, 22, 32, 64, 64, 64, 64, 0] ,
0xe7108 : [4, 0, 11, 22, 32, 64, 64, 64, 64, 0] ,
0xe711c : [4, 0, 11, 22, 32, 64, 64, 64, 64, 0] ,
0xe7130 : [4, 0, 11, 22, 32, 64, 64, 64, 64, 0] ,
0xe7144 : [4, 0, 11, 22, 32, 64, 64, 64, 64, 0] ,
0xe7158 : [4, 0, 11, 22, 32, 64, 64, 64, 64, 0] ,
0xe716c : [4, 0, 11, 22, 32, 64, 64, 64, 64, 0] ,
0xe80b0 : [4, 0, 11, 22, 32, 64, 64, 64, 64, 0] ,
0xe80c4 : [4, 0, 11, 22, 32, 64, 64, 64, 64, 0] ,
0xe80d8 : [4, 0, 11, 22, 32, 64, 64, 64, 64, 0] ,
0xe80ec : [4, 0, 11, 22, 32, 64, 64, 64, 64, 0] ,
}

steer_torque_req_clamped_by_vehicle_speed_table_stock_vals = {
0xe4180 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe41a8 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe41d0 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe41f8 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe4220 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe4248 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe5180 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe51a8 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe51d0 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe51f8 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe5220 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe5248 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe6180 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe61a8 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe61d0 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe61f8 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe6220 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe6248 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe7180 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe71a8 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe71d0 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe71f8 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe7220 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe7248 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe8100 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe8128 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe8150 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
0xe8178 : [9, 3200, 3413, 3627, 3840, 4736, 5632, 6528, 7424, 8320, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 15360, 0] ,
}

low_speed_lockout_addr = {
  'TVA-A150':0xc62de,
  'TVA-A160':0xc62ea
}

speed_lockout_patch_table = {
  'TVA-A150':[
  ],
  'TVA-A160':[
    # 00028ebc e5  ff  eb  72    ld.hu      PTR_DAT_000072ea [tp],lp=>WORD_000c62ea          = 001a0018
    # 00028ebc e5  ff  ed  72    ld.hu      0x72ec [tp],lp
    (0x28ebe, 0xeb, 0xed),
  ]
}

# Should we increase the upper limit 0x8000?
boost_mode_patch_table = {
  'TVA-A150':[
  ],
  'TVA-A160':[
    # 00029396 e5  77  f9  73    ld.hu      LAB_000073f8 [tp],r14 =>DAT_000c63f8              = 0021h
    # 00029396 e5  77  fd  73    ld.hu      0x73fc [tp],r14        324
    # 00029396 e5  77  f7  73    ld.hu      0x73f6 [tp],r14        16
    (0x29398, 0xf9, 0xf7),
    # 00029474 e5  67  f9  73    ld.hu      LAB_000073f8 [tp],r12 =>DAT_000c63f8              = 0021h
    # 00029474 e5  67  fd  73    ld.hu      0x73fc [tp],r12        324
    # 00029474 e5  67  f7  73    ld.hu      0x73f6 [tp],r12        16
    (0x29476, 0xf9, 0xf7),
    # 000294a6 e5  3f  f9  73    ld.hu      LAB_000073f8 [tp],r7=>DAT_000c63f8               = 0021h
    # 000294a6 e5  3f  fd  73    ld.hu      0x73fc [tp],r7         324
    # 000294a6 e5  3f  f7  73    ld.hu      0x73f6 [tp],r7         16
    (0x294a8, 0xf9, 0xf7),
    # 8X accumulator
    # 0002a1ea af  4a           sar        0xf ,steer_angle_rate_acc_increment
    # 0002a1ea ac  4a           sar        0xc ,r9
    (0x2a1ea, 0xaf, 0xac),
  ]
}

angle_based_steering_patch_table = {
  'TVA-A150':[
  ],
  'TVA-A160':[
    # 00029a6c 61  6a           cmp        0x1 ,r13
    # 00029a6e ba  05           bne        LAB_00029a74
    # 00029a6c 00  00           nop
    # 00029a6e 00  00           nop
    (0x29a6c, 0x61, 0x00),
    (0x29a6d, 0x6a, 0x00),
    (0x29a6e, 0xba, 0x00),
    (0x29a6f, 0x05, 0x00),
  ]
}


math_result_1_rshift_6_minus_angle_rate_acc_limit_patch_table = {
  'TVA-A150':[
  ],
  'TVA-A160':[
    # 00029e62 2d  06  01  70  17  00     mov        DAT_00177001 ,r13
    # 2X
    # 00029e62 2d  06  01  28  23  00     mov        0x232801 ,r13
    #(0x29e65, 0x70, 0x28),
    #(0x29e66, 0x17, 0x23),
    # 4X
    # 00029e62 2d  06  01  98  3a  00    mov        0x3a9801 ,r13
    #(0x29e65, 0x70, 0x98),
    #(0x29e66, 0x17, 0x3a),
    # 8X
    # 00029e62 2d  06  00  78  69  00   mov        0x697800 ,r13
    #(0x29e65, 0x70, 0x78),
    #(0x29e66, 0x17, 0x69),
    # 20X
    # 00029e62 2d  06  00  88  f5  00    mov        0xf58800 ,r13
    (0x29e65, 0x70, 0x88),
    (0x29e66, 0x17, 0xf5),
  ]
}

angle_rate_acc_fine_tune_patch_table = {
  'TVA-A150':[
  ],
  'TVA-A160':[
    # 00028f86 e5  87  eb  73    ld.hu      LAB_000073ea [tp],r16 =>DAT_000c63ea              = 0618h
    # 1.5 -> 0.5
    # 00028f86 e5  87  ef  73    ld.hu      0x73ee [tp],r16
    (0x28f88, 0xeb, 0xef),
  ]
}

motor_torque_fine_tune_patch_table = {
  'TVA-A150':[
  ],
  'TVA-A160':[
    # Enable reserved code, change 0x400 to 0x3FE
    # 0002a24c e5  4f  db  73    ld.hu      LAB_000073da [tp],tmp =>DAT_000c63da              = 0400h
    # 0002a24c 20  4e  fe  03    movea      0x3fe ,r0,r9
    (0x2a24c, 0xe5, 0x20),
    (0x2a24d, 0x4f, 0x4e),
    (0x2a24e, 0xdb, 0xfe),
    (0x2a24f, 0x73, 0x03),
    # 0002a272 e5  3f  df  73    ld.hu      LAB_000073de [tp],r7=>DAT_000c63de               = 0400h
    # 0002a272 20  3e  fe  03    movea      0x3fe ,r0,r7
    (0x2a272, 0xe5, 0x20),
    (0x2a273, 0x3f, 0x3e),
    (0x2a274, 0xdf, 0xfe),
    (0x2a275, 0x73, 0x03),
    # 0002b5b6 e5  6f  b3  71    ld.hu      FUN_000071b2 [tp],r13 =>DAT_000c61b2              = 0200h
    # 0.5 -> 2.0
    # 0002b5b6 e5  6f  93  71    ld.hu      0x7192 [tp],r13
    (0x2b5b8, 0xb3, 0x93),
  ]
}

global_torque_result_1_fine_tune_patch_table = {
  'TVA-A150':[
  ],
  'TVA-A160':[
    # 2X global_torque_result_1
    # 0002a1f8 e5  87  b5  71    ld.hu      FUN_000071b2+2 [tp],clamped_math_result_1_rshif  = 0200h
    # 0002a1f8 e5  87  a5  71    ld.hu      0x71a4 [tp],r16
    (0x2a1fa, 0xb5, 0xa5),
    # 0002a20c 25  5f  b4  71    ld.h       FUN_000071b2+2 [tp],torque_sensor_raw_or_speed_  = 0200h
    # 0002a20c 25  5f  a4  71    ld.h       0x71a4 [tp],r11
    (0x2a20e, 0xb4, 0xa4),
    # 0002a212 e5  57  b5  71    ld.hu      FUN_000071b2+2 [tp],r10 =>DAT_000c61b4            = 0200h
    # 0002a212 e5  57  a5  71    ld.hu      0x71a4 [tp],r10
    (0x2a214, 0xb5, 0xa5),
    # 0002a21c e5  5f  b5  71    ld.hu      FUN_000071b2+2 [tp],torque_sensor_raw_or_speed_  = 0200h
    # 0002a21c e5  5f  a5  71    ld.hu      0x71a4 [tp],r11
    (0x2a21e, 0xb5, 0xa5),
  ]
}

torque_clamp_addr = {
  'TVA-A150':0xc61b6,
  'TVA-A160':0xc61be
}

torque_sensor_acc_increment_upper_limits_table = {
  'TVA-A150':[
    # increment_of_torque_sensor_acc_rshift_4_max_1
    (0x000c61b8, 0x0640),
    # increment_of_torque_sensor_acc_rshift_4_max_2
    (0x000c61ba, 0x0380),
    # increment_of_torque_sensor_acc_rshift_4_max_3
    (0x000c61bc, 0x0500)
  ],
  'TVA-A160':[
    # increment_of_torque_sensor_acc_rshift_4_max_1
    (0x000c61c0, 0x0640),
    # increment_of_torque_sensor_acc_rshift_4_max_2
    (0x000c61c2, 0x0380),
    # increment_of_torque_sensor_acc_rshift_4_max_3
    (0x000c61c4, 0x0500)
  ],
}

steer_angle_rate_acc_patch_table = {
  'TVA-A150':[
  ],
  'TVA-A160':[
    # Remove the negative effect of steer angle rate acc
    # 00029d78 ba  81           sub        r26 ,r16
    # 00029d78 a0  81           sub        r0,r16
    # iVar25 = iVar20 * 0x20 - uVar27;   ->   iVar25 = iVar20 * 0x20;
    (0x29d78, 0xba, 0xa0),
  ]
}

multiplier_accumulator_patch_table = {
  'TVA-A150':[
  ],
  'TVA-A160':[
    # 0002a1e6 ee  4f  20  02    mul        multiplier_accumulator ,tmp ,r0
    # 0002a1ea af  4a           sar        0xf ,tmp
    # to
    # 0002a1e6 e1  4f  40  02    mul        0x1 ,r9,r0
    # 0002a1ea a0  4a           sar        0x0 ,r9
    (0x2a1e6, 0xee, 0xe1),
    (0x2a1e8, 0x20, 0x40),
    (0x2a1ea, 0xaf, 0xa0),
  ]
}


# 2X scale to torque outputs
torque_output_clamp_patch_table = {
  'TVA-A150':[
  ],
  'TVA-A160':[
    # 00029e3a e5  37  bd  71    ld.hu      LAB_000071bc [tp],r6=>DAT_000c61bc               = 3C00h
    # 2X
    # 00029e3a e5  37  dd  71    ld.hu      DAT_000071dc [tp],param_1 =>WORD_000c61dc         = 7800h
    #(0x29e3c, 0xbd, 0xdd),
    # 4X
    # 00029e3a e5  37  49  71    ld.hu      0x7148 [tp],param_1                             FA00
    (0x29e3c, 0xbd, 0x49),
    # 00029e44 e5  4f  bd  71    ld.hu      LAB_000071bc [tp],r9=>DAT_000c61bc               = 3C00h
    # 2X
    # 00029e44 e5  4f  dd  71    ld.hu      0x71dc [tp],r9                                   = 7800h
    #(0x29e46, 0xbd, 0xdd),
    # 4X
    # 00029e44 e5  4f  49  71    ld.hu      0x7148 [tp],r9
    (0x29e46, 0xbd, 0x49),
    # 00029e4a e5  6f  bd  71    ld.hu      LAB_000071bc [tp],r13 =>DAT_000c61bc              = 3C00h
    # 2X
    # 00029e4a e5  6f  dd  71    ld.hu      0x71dc [tp],r13                                   = 7800h
    #(0x29e4c, 0xbd, 0xdd),
    # 4X
    # 00029e4a e5  6f  49  71    ld.hu      0x7148 [tp],r13
    (0x29e4c, 0xbd, 0x49),
    # 00029e58 e5  4f  bd  71    ld.hu      LAB_000071bc [tp],r9=>DAT_000c61bc               = 3C00h
    # 2X
    # 00029e58 e5  4f  dd  71    ld.hu      0x71dc [tp],r9                                   = 7800h
    #(0x29e5a, 0xbd, 0xdd),
    # 4X
    # 00029e58 e5  4f  49  71    ld.hu      0x7148 [tp],r9
    (0x29e5a, 0xbd, 0x49),

    # 0002a13e e5  4f  bf  71    ld.hu      LAB_000071bc+2 [tp],r9=>DAT_000c61be             = 3C00h
    # 2X
    # 0002a13e e5  4f  dd  71    ld.hu      0x71dc [tp],r9                                   = 7800h
    (0x2a140, 0xbf, 0xdd),
    # 4X
    # 0002a13e e5  4f  49  71    ld.hu      0x7148 [tp],r9
    #(0x2a140, 0xbf, 0x49),

    # 0002a146 25  67  be  71    ld.h       LAB_000071bc+2 [tp],r12 =>DAT_000c61be            = 3C00h
    # 0002a146 25  67  dc  71    ld.h       0x71dc [tp],r12                                   = 7800h
    (0x2a148, 0xbe, 0xdc),
    # 0002a14c e5  37  bf  71    ld.hu      LAB_000071bc+2 [tp],r6=>DAT_000c61be             = 3C00h
    # 0002a14c e5  37  dd  71    ld.hu      0x71dc [tp],param_1                               = 7800h
    (0x2a14e, 0xbf, 0xdd),
    # 0002a156 e5  67  bf  71    ld.hu      LAB_000071bc+2 [tp],r12 =>DAT_000c61be            = 3C00h
    # 0002a156 e5  67  dd  71    ld.hu      0x71dc [tp],r12                                   = 7800h
    (0x2a158, 0xbf, 0xdd),
    # 10240 -> 15360
    # 00029ee8 e5  57  b7  71    ld.hu      LAB_000071b6 [tp],r10 =>DAT_000c61b6              = 2800h
    # 00029ee8 e5  57  bd  71    ld.hu      0x71bc [tp],r10
    (0x29eea, 0xb7, 0xbd),
    # 00029ef2 e5  47  b7  71    ld.hu      LAB_000071b6 [tp],r8=>DAT_000c61b6               = 2800h
    # 00029ef2 e5  47  bd  71    ld.hu      0x71bc [tp],r8
    (0x29ef4, 0xb7, 0xbd),
    # 00029ef8 e5  3f  b7  71    ld.hu      LAB_000071b6 [tp],r7=>DAT_000c61b6               = 2800h
    # 00029ef8 e5  3f  bd  71    ld.hu      0x71bc [tp],r7
    (0x29efa, 0xb7, 0xbd),
    # 00029f02 e5  47  b7  71    ld.hu      LAB_000071b6 [tp],r8=>DAT_000c61b6               = 2800h
    # 00029f02 e5  47  bd  71    ld.hu      0x71bc [tp],r8
    (0x29f04, 0xb7, 0xbd),
  ]
}

torque_sensor_upper_limits_patch_table = {
  'TVA-A150':[
    # 000291b6 85  3f  ad  74    ld.bu      LAB_000074aa+2 [tp],r7=>DAT_000c64ac             = 70h
    # 000291b6 a5  3f  e1  74    ld.bu      0x74e1 [tp],r7                                   = F0h
    (0x291b6, 0x85, 0xa5),
    (0x291b8, 0xad, 0xe1),
  ],
  'TVA-A160':[
    # 0002920a 85  67  b9  74    ld.bu      LAB_000074b6+2 [tp],r12 =>max_0                   = 70h
    # 0002920a a5  67  f1  74    ld.bu      0x74f1 [tp],r12                                   = F0H
    (0x2920a, 0x85, 0xa5),
    (0x2920c, 0xb9, 0xf1),
    # 0002921c 85  3f  b9  74    ld.bu      LAB_000074b6+2 [tp],r7=>max_0                    = 70h
    # 0002921c a5  3f  f1  74    ld.bu      0x74f1 [tp],r7                                   = F0H
    (0x2921c, 0x85, 0xa5),
    (0x2921e, 0xb9, 0xf1),
    # 0002923e 85  5f  b5  74    ld.bu      LAB_000074b2+2 [tp],r11 =>max_2                   = 70h
    # 0002923e a5  5f  f1  74    ld.bu      0x74f1 [tp],r11                                   = F0H
    (0x2923e, 0x85, 0xa5),
    (0x29240, 0xb5, 0xf1),
    # 00029256 a5  37  b7  74    ld.bu      LAB_000074b6+1 [tp],r6=>max_3                    = 40h
    # 00029256 a5  37  f1  74    ld.bu      0x74f1 [tp],param_1 =>DAT_000c64f1                = F0h
    (0x29258, 0xb7, 0xf1),
    # 00029266 85  6f  b7  74    ld.bu      LAB_000074b6 [tp],r13 =>max_4                     = 36h
    # 00029266 a5  6f  f1  74    ld.bu      0x74f1 [tp],r13                                   = F0h
    (0x29266, 0x85, 0xa5),
    (0x29268, 0xb7, 0xf1),
    # 000292b8 a5  4f  b5  74    ld.bu      LAB_000074b2+3 [tp],r9=>DAT_000c64b5             = 60h
    # 000292b8 a5  4f  f1  74    ld.bu      0x74f1 [tp],r9                                   = F0h
    (0x292ba, 0xb5, 0xf1),
    # 000292d0 a5  87  b7  74    ld.bu      LAB_000074b6+1 [tp],r16 =>max_3                   = 40h
    # 000292d0 a5  87  f1  74    ld.bu      0x74f1 [tp],r16                                   = F0h
    (0x292d2, 0xb7, 0xf1),
    # 000292e0 85  5f  b7  74    ld.bu      LAB_000074b6 [tp],r11 =>max_4                     = 36h
    # 000292e0 a5  5f  f1  74    ld.bu      0x74f1 [tp],r11                                   = F0h
    (0x292e0, 0x85, 0xa5),
    (0x292e2, 0xb7, 0xf1),
    # 0002924a e5  47  c1  71    ld.hu      LAB_000071c0 [tp],r8=>diff_max_1                 = 0640h
    # 0002924a e5  47  cd  71    ld.hu      0x71cc [tp],r8                                   = e00h
    (0x2924c, 0xc1, 0xcd),
    # 0002925e e5  7f  c3  71    ld.hu      LAB_000071c0+2 [tp],r15 =>diff_max_2              = 0380h
    # 0002925e e5  7f  cd  71    ld.hu      0x71cc [tp],r15                                   = e00h
    (0x29260, 0xc3, 0xcd),
    # 0002926e e5  4f  c5  71    ld.hu      LAB_000071c4 [tp],r9=>max_3                      = 0500h
    # 0002926e e5  4f  cd  71    ld.hu      0x71cc [tp],r9                                   = e00h
    (0x29270, 0xc5, 0xcd),
    # 000292c4 e5  3f  c1  71    ld.hu      LAB_000071c0 [tp],r7=>diff_max_1                 = 0640h
    # 000292c4 e5  3f  cd  71    ld.hu      0x71cc [tp],r7                                   = e00h
    (0x292c6, 0xc1, 0xcd),
    # 000292d8 e5  77  c3  71    ld.hu      LAB_000071c0+2 [tp],r14 =>diff_max_2              = 0380h
    # 000292d8 e5  77  cd  71    ld.hu      0x71cc [tp],r14                                   = e00h
    (0x292da, 0xc3, 0xcd),
    # 000292e8 e5  47  c5  71    ld.hu      LAB_000071c4 [tp],r8=>max_3                      = 0500h
    # 000292e8 e5  47  cd  71    ld.hu      0x71cc [tp],r8                                   = e00h
    (0x292ea, 0xc5, 0xcd),
    # 00029a78 85  47  b9  74    ld.bu      LAB_000074b6+2 [tp],r8=>max_0                    = 70h
    # 00029a78 a5  47  f1  74    ld.bu      0x74f1 [tp],r8                                   = F0h
    (0x29a78, 0x85, 0xa5),
    (0x29a7a, 0xb9, 0xf1),
    # Remove DAT_000c64a3 == '\x01
    # 0002a198 a5  87  a3  74    ld.bu      LAB_000074a2+1 [tp],clamped_math_result_1_rshif  = 01h
    # 0002a198 85  87  a3  74    ld.bu      0x74a2 [tp],r16
    (0x2a198, 0xa5, 0x85),
    # Remove DAT_fedf17f6, disable "hold steer pos state"
    # 00029a70 80  07  56  06    jr         LAB_0002a0c6
    # 00029a70 80  07  04  00    jr         LAB_00029a74
    (0x29a72, 0x56, 0x04),
    (0x29a73, 0x06, 0x00),
  ]
}

query_fw_version_return_ram_vars_patch_table = {
  'TVA-A150':[
  ],
  'TVA-A160':[
    # 0004f70c 26  06  00 31  01  00     mov        fw_version_1 ,r6                                 = 33h    3
    # 0004f70c 26  06  c4 14  df  fe     mov       0xfedf14c4 ,param_1
    (0x4f70e, 0x00, 0xc4),
    (0x4f70f, 0x31, 0x14),
    (0x4f710, 0x01, 0xdf),
    (0x4f711, 0x00, 0xfe),
  ]
}
# Dangerous code patches, for steer test on bench only
steer_status_addrs_and_stock_values = {
  'TVA-A150': [(0x29154, 7), (0x2912c, 3)], #, (0x290f8, 7)],
  'TVA-A160': [(0x291ba, 7), (0x29192, 3), (0x2915e, 7)]
}

# Dangerous code patches, for steer test on bench only
code_addrs_and_stock_values = {
  'TVA-A150': [
    (0x28eb6, 0, 1),
    (0x290d2, 0, 1),
    # jr 290fe -> jr 29a02
    (0x299f8, 0x08, 0x0c),
    (0x299f9, 0x07, 0x0),
    # jr 290fe -> jr 29a02
    (0x29a00, 0x00, 0x04),
    (0x29a01, 0x07, 0x0),
  ],
  'TVA-A160': [
    (0x28f1c, 0, 1),
    (0x29138, 0, 1),
    # jr 2a164 -> jr 29a68
    (0x29a5e, 0x08, 0x0c),
    (0x29a5f, 0x07, 0x0),
    # jr 2a164 -> jr 29a68
    (0x29a66, 0x00, 0x04),
    (0x29a67, 0x07, 0x0),
  ]
}

known_eps_versions = [
  {
    "versions": [ # Applicable versions
      b'39990-TVA-A150\x00\x00',  # stock
      b'39990,TVA-A150\x00\x00',  # mod
    ],
    "chunk_hashes": [   # For stock bin chunk check
      # start, end, hash
      ( 0x13000 , 0xc4ffc , 0x178C1C28 ),
      ( 0xc5000 , 0xc5ffc , 0x09C1200B ),
      ( 0xc6000 , 0xc6ffc , 0x3E61776C ),
      ( 0xc7000 , 0xccffc , 0x6F661870 ),
      ( 0xcd000 , 0xcdffc , 0xF23961DB ),
      ( 0xce000 , 0xceffc , 0x2DB637AE ),
      ( 0xcf000 , 0xcfffc , 0x5E56836E ),
      ( 0xd0000 , 0xd0ffc , 0x02974665 ),
      ( 0xd1000 , 0xd1ffc , 0x956D5D62 ),
      ( 0xd2000 , 0xd2ffc , 0xDB5F1BDB ),
      ( 0xd3000 , 0xd3ffc , 0xE40F155C ),
      ( 0xd4000 , 0xd4ffc , 0x16649324 ),
      ( 0xd5000 , 0xd5ffc , 0x819E8823 ),
      ( 0xd6000 , 0xd6ffc , 0x23FF4CF7 ),
      ( 0xd7000 , 0xd7ffc , 0x1CAF4270 ),
      ( 0xd8000 , 0xd8ffc , 0x73797B48 ),
      ( 0xd9000 , 0xd9ffc , 0x33F89A01 ),
      ( 0xda000 , 0xdaffc , 0x06F3C8DD ),
      ( 0xdb000 , 0xdbffc , 0x75137C1D ),
      ( 0xdc000 , 0xdcffc , 0x6E50360A ),
      ( 0xdd000 , 0xddffc , 0x1DB082CA ),
      ( 0xde000 , 0xdeffc , 0xFA29985C ),
      ( 0xdf000 , 0xdfffc , 0x89C92C9C ),
      ( 0xe0000 , 0xe0ffc , 0xA715B6C5 ),
      ( 0xe1000 , 0xe1ffc , 0xD4F50205 ),
      ( 0xe2000 , 0xe2ffc , 0xDDC10890 ),
      ( 0xe3000 , 0xe3ffc , 0xAE21BC50 ),
      ( 0xe4000 , 0xe4ffc , 0xC1DAE8B3 ),
      ( 0xe5000 , 0xe5ffc , 0x24BA0614 ),
      ( 0xe6000 , 0xe6ffc , 0xD5B8B338 ),
      ( 0xe7000 , 0xe7ffc , 0xA65807F8 ),
      ( 0xe8000 , 0xe8ffc , 0x4AE2A19A ),
      ( 0xe9000 , 0xe9ffc , 0xFB963D44 ),
      ( 0xea000 , 0xeaffc , 0x253C4B9A ),
      ( 0xeb000 , 0xebffc , 0xB60883F6 ),
      ( 0xec000 , 0xecffc , 0x9C855CC5 ),
      ( 0xed000 , 0xedffc , 0xFD6FED4C ),
      ( 0xfd000 , 0xffffc , 0xA5919245 ),
    ],
  },
  {
    "versions": [ # Applicable versions
      b'39990-TVA-A160\x00\x00',  # stock
      b'39990,TVA-A160\x00\x00',  # mod
    ],
    "chunk_hashes": [   # For stock bin chunk check
      # start, end, hash
      (0x13000, 0xc4ffc, 0x48F24975),
      (0xc5000, 0xc5ffc, 0x09C1200B),
      (0xc6000, 0xc6ffc, 0xD895ECBA),
      (0xc7000, 0xccffc, 0x6F661870),
      (0xcd000, 0xcdffc, 0xF23961DB),
      (0xce000, 0xceffc, 0x2DB637AE),
      (0xcf000, 0xcfffc, 0x5E56836E),
      (0xd0000, 0xd0ffc, 0x02974665),
      (0xd1000, 0xd1ffc, 0x956D5D62),
      (0xd2000, 0xd2ffc, 0xDB5F1BDB),
      (0xd3000, 0xd3ffc, 0xE40F155C),
      (0xd4000, 0xd4ffc, 0x16649324),
      (0xd5000, 0xd5ffc, 0x819E8823),
      (0xd6000, 0xd6ffc, 0x23FF4CF7),
      (0xd7000, 0xd7ffc, 0x1CAF4270),
      (0xd8000, 0xd8ffc, 0x73797B48),
      (0xd9000, 0xd9ffc, 0x33F89A01),
      (0xda000, 0xdaffc, 0x06F3C8DD),
      (0xdb000, 0xdbffc, 0x75137C1D),
      (0xdc000, 0xdcffc, 0x6E50360A),
      (0xdd000, 0xddffc, 0x1DB082CA),
      (0xde000, 0xdeffc, 0xFA29985C),
      (0xdf000, 0xdfffc, 0x89C92C9C),
      (0xe0000, 0xe0ffc, 0xA715B6C5),
      (0xe1000, 0xe1ffc, 0xD4F50205),
      (0xe2000, 0xe2ffc, 0xDDC10890),
      (0xe3000, 0xe3ffc, 0xAE21BC50),
      (0xe4000, 0xe4ffc, 0xC1DAE8B3),
      (0xe5000, 0xe5ffc, 0x24BA0614),
      (0xe6000, 0xe6ffc, 0xD5B8B338),
      (0xe7000, 0xe7ffc, 0xA65807F8),
      (0xe8000, 0xe8ffc, 0x4AE2A19A),
      (0xe9000, 0xe9ffc, 0xFB963D44),
      (0xea000, 0xeaffc, 0x253C4B9A),
      (0xeb000, 0xebffc, 0xB60883F6),
      (0xec000, 0xecffc, 0x9C855CC5),
      (0xed000, 0xedffc, 0xFD6FED4C),
      (0xfd000 ,0xffffc, 0xFCB8212C),
    ],
  },
  {
    "versions": [ # Applicable versions
      b'39990-TWB-H110\x00\x00',  # stock
      b'39990-TWB-H120\x00\x00',  # stock
      b'39990,TWB-H120\x00\x00',  # mod
    ],
    "chunk_hashes": [   # For stock bin chunk check
      (0x13000, 0xc4ffc,  0x77B6F3FF),
      (0xc5000, 0xc5ffc,  0x09C1200B),
      (0xc6000, 0xc6ffc,  0x7EBFE76B),
      (0xc7000, 0xccffc,  0x6F661870),
      (0xcd000, 0xcdffc,  0x33EC9803),
      (0xce000, 0xceffc,  0x2DB637AE),
      (0xcf000, 0xcfffc,  0x14128B04),
      (0xd0000, 0xd0ffc,  0xD8F0D2FF),
      (0xd1000, 0xd1ffc,  0xF191D231),
      (0xd2000, 0xd2ffc,  0xDB5F1BDB),
      (0xd3000, 0xd3ffc,  0xE40F155C),
      (0xd4000, 0xd4ffc,  0x16649324),
      (0xd5000, 0xd5ffc,  0x819E8823),
      (0xd6000, 0xd6ffc,  0x23FF4CF7),
      (0xd7000, 0xd7ffc,  0x1CAF4270),
      (0xd8000, 0xd8ffc,  0x73797B48),
      (0xd9000, 0xd9ffc,  0x33F89A01),
      (0xda000, 0xdaffc,  0x06F3C8DD),
      (0xdb000, 0xdbffc,  0x75137C1D),
      (0xdc000, 0xdcffc,  0x6E50360A),
      (0xdd000, 0xddffc,  0x1DB082CA),
      (0xde000, 0xdeffc,  0xFA29985C),
      (0xdf000, 0xdfffc,  0x89C92C9C),
      (0xe0000, 0xe0ffc,  0xA715B6C5),
      (0xe1000, 0xe1ffc,  0xD4F50205),
      (0xe2000, 0xe2ffc,  0xDDC10890),
      (0xe3000, 0xe3ffc,  0xAE21BC50),
      (0xe4000, 0xe4ffc,  0x1ED8448A),
      (0xe5000, 0xe5ffc,  0x24BA0614),
      (0xe6000, 0xe6ffc,  0xD5B8B338),
      (0xe7000, 0xe7ffc,  0xA65807F8),
      (0xe8000, 0xe8ffc,  0x4AE2A19A),
      (0xe9000, 0xe9ffc,  0xFB963D44),
      (0xea000, 0xeaffc,  0x010558DC),
      (0xeb000, 0xebffc,  0xB60883F6),
      (0xec000, 0xecffc,  0x9C855CC5),
      (0xed000, 0xedffc,  0xA94679CE),
    ]
  }
]


def check_crc32_in_bin_data(d, start, end, debug=False):
    h = zlib.crc32(d[start:(end -4)], 0)
    hash_in_file = struct.unpack("<I", d[end -4:end])[0]
    if h != hash_in_file:
      print(hex(start), hex(end-4), "%08X" % (h & 0xFFFFFFFF), 'In File:', "%08X" % (hash_in_file & 0xFFFFFFFF), h == hash_in_file)
    if debug:
      print(hex(start), hex(end-4), "%08X" % (h & 0xFFFFFFFF))
    return h == hash_in_file

def check_all(d, debug=False):
  if not check_crc32_in_bin_data(d, 0x13000, 0xc5000, debug):
    return False
  if not check_crc32_in_bin_data(d, 0xc5000, 0xc6000, debug):
    return False
  if not check_crc32_in_bin_data(d, 0xc6000, 0xc7000, debug):
    return False
  if not check_crc32_in_bin_data(d, 0xc7000, 0xcd000, debug):
    return False
  start = 0xcd000
  while start <= 0xf8000:
    if not check_crc32_in_bin_data(d, start, start + 0x1000, debug):
      return False
    start += 0x1000
  return True

def make_fw_version_mod(d):
  mod_d = bytearray(d)
  for comma_addr in [0x13105, 0x1411c]:
    mod_d[comma_addr] = ord(',')
    print('replaced char', chr(d[comma_addr]), 'in fw version with', chr(mod_d[comma_addr]), 'at offset', hex(comma_addr))
  start_addr = 0x13000
  end_addr = 0xc5000
  h_new = zlib.crc32(mod_d[start_addr:(end_addr - 4)], 0)
  mod_d[end_addr - 4:end_addr] = struct.pack("<I", h_new)
  h_old = zlib.crc32(d[start_addr:(end_addr - 4)], 0)
  print('Checksum for original', "%08X" % (h_old & 0xFFFFFFFF))
  print('Checksum for mod', "%08X" % (h_new & 0xFFFFFFFF))
  if not check_crc32_in_bin_data(mod_d, start_addr, end_addr):
    sys.exit(0)
  print('Make fw version mod done')
  return mod_d

def make_one_word_mod(d, addr, old_val, new_val, debug=False):
  old_val_in_file = struct.unpack('<H', d[addr:addr+2])[0]
  assert old_val_in_file == old_val, 'Stock val mismatch 0x%X != 0x%X, addr 0x%X' % (old_val, old_val_in_file, addr)
  mod_d = bytearray(d)
  print('Replaced ', hex(old_val), 'with', hex(new_val), 'at', hex(addr))
  mod_d[addr:addr+2] = struct.pack('<H', new_val)
  start_addr = addr - addr % 0x1000
  end_addr = start_addr + 0x1000
  h_new = zlib.crc32(mod_d[start_addr:(end_addr - 4)], 0)
  mod_d[end_addr - 4:end_addr] = struct.pack("<I", h_new)
  h_old = zlib.crc32(d[start_addr:(end_addr - 4)], 0)
  if debug:
    print(hex(start_addr), 'Original CRC', "%08X" % (h_old & 0xFFFFFFFF))
    print(hex(start_addr), 'New      CRC', "%08X" % (h_new & 0xFFFFFFFF))
  if not check_crc32_in_bin_data(mod_d, start_addr, end_addr):
    sys.exit(0)
  return mod_d

def make_one_byte_mod(d, addr, old_val, new_val, debug=False):
  old_val_in_file = struct.unpack('<B', d[addr:addr+1])[0]
  assert old_val_in_file == old_val, 'Stock val mismatch 0x%X != 0x%X, addr 0x%X' % (old_val, old_val_in_file, addr)
  mod_d = bytearray(d)
  print('Replaced ', hex(old_val), 'with', hex(new_val), 'at', hex(addr))
  mod_d[addr:addr+1] = struct.pack('<B', new_val)
  start_addr = addr - addr % 0x1000
  end_addr = start_addr + 0x1000
  h_new = zlib.crc32(mod_d[start_addr:(end_addr - 4)], 0)
  mod_d[end_addr - 4:end_addr] = struct.pack("<I", h_new)
  h_old = zlib.crc32(d[start_addr:(end_addr - 4)], 0)
  if debug:
    print(hex(start_addr), 'Original CRC', "%08X" % (h_old & 0xFFFFFFFF))
    print(hex(start_addr), 'New      CRC', "%08X" % (h_new & 0xFFFFFFFF))
  if not check_crc32_in_bin_data(mod_d, start_addr, end_addr):
    sys.exit(0)
  return mod_d

def make_one_byte_mod_13000_c5000(d, addr, old_val, new_val, debug=False):
  old_val_in_file = struct.unpack('<B', d[addr:addr+1])[0]
  assert old_val_in_file == old_val, 'Stock val mismatch 0x%X != 0x%X, addr 0x%X' % (old_val, old_val_in_file, addr)
  mod_d = bytearray(d)
  print('Replaced ', hex(old_val), 'with', hex(new_val), 'at addr', hex(addr))
  mod_d[addr:addr+1] = struct.pack('<B', new_val)
  start_addr = 0x13000
  end_addr = 0xc5000
  h_new = zlib.crc32(mod_d[start_addr:(end_addr - 4)], 0)
  mod_d[end_addr - 4:end_addr] = struct.pack("<I", h_new)
  h_old = zlib.crc32(d[start_addr:(end_addr - 4)], 0)
  if debug:
    print(hex(start_addr), 'Original CRC', "%08X" % (h_old & 0xFFFFFFFF))
    print(hex(start_addr), 'New      CRC', "%08X" % (h_new & 0xFFFFFFFF))
  if not check_crc32_in_bin_data(mod_d, start_addr, end_addr):
    sys.exit(0)
  return mod_d


def make_steer_to_zero_patch_mod(d, fw_ver, debug=False):
  # This will cause eps error
  #return make_one_word_mod(d, low_speed_lockout_addr[fw_ver], 320, 0, debug)
  print('Make steer to zero mod...')
  for addr, val, new_val in speed_lockout_patch_table[fw_ver]:
    d = make_one_byte_mod_13000_c5000(d, addr, val, new_val, debug)
  return d

def make_boost_mode_patch_mod(d, fw_ver, debug=False):
  print('Make boost mode mod...')
  for addr, val, new_val in boost_mode_patch_table[fw_ver]:
    d = make_one_byte_mod_13000_c5000(d, addr, val, new_val, debug)
  return d

def make_math_result_1_rshift_6_minus_angle_rate_acc_limit_mod(d, fw_ver, debug=False):
  print('Make math_result_1_rshift_6_minus_angle_rate_acc_limit mod...')
  for addr, val, new_val in math_result_1_rshift_6_minus_angle_rate_acc_limit_patch_table[fw_ver]:
    d = make_one_byte_mod_13000_c5000(d, addr, val, new_val, debug)
  return d

def make_angle_rate_acc_fine_tune_mod(d, fw_ver, debug=False):
  print('Make angle_rate_acc_fine_tune mod, 0.33 mod...')
  for addr, val, new_val in angle_rate_acc_fine_tune_patch_table[fw_ver]:
    d = make_one_byte_mod_13000_c5000(d, addr, val, new_val, debug)
  return d

def make_motor_torque_fine_tune_mod(d, fw_ver, debug=False):
  print('Fine tune motor torque from 0.5 to 1.0 or 2.0???')
  for addr, val, new_val in motor_torque_fine_tune_patch_table[fw_ver]:
    d = make_one_byte_mod_13000_c5000(d, addr, val, new_val, debug)
  return d

def make_global_torque_result_1_clamp_mod(d, fw_ver, debug=False):
  print('global_torque_result_1 clamp changed from 512 to 1024')
  for addr, val, new_val in global_torque_result_1_fine_tune_patch_table[fw_ver]:
    d = make_one_byte_mod_13000_c5000(d, addr, val, new_val, debug)
  return d

def make_torque_output_clamp_patch_mod(d, fw_ver, scale, debug=False):
  print('Increasing torque output clamps, and 15360, 10240 limits')
  for addr, val, new_val in torque_output_clamp_patch_table[fw_ver]:
    d = make_one_byte_mod_13000_c5000(d, addr, val, new_val, debug)
  return d

# Set steer status to 0 in case it is set to 3 or 7
def make_steer_status_mod(d, fw_ver, debug=False):
  print('Modify steer status...')
  for addr, val in steer_status_addrs_and_stock_values[fw_ver]:
    d = make_one_byte_mod_13000_c5000(d, addr, val, 0, debug)
  return d

def make_code_patch_mod(d, fw_ver, debug=False):
  print('Dangerous code patch!!!')
  for addr, val, new_val in code_addrs_and_stock_values[fw_ver]:
    d = make_one_byte_mod_13000_c5000(d, addr, val, new_val, debug)
  return d

def make_torque_sensor_upper_limits_patch_mod(d, fw_ver, debug=False):
  print('Increasing torque sensor upper limits and disable hold steer pos state')
  for addr, val, new_val in torque_sensor_upper_limits_patch_table[fw_ver]:
    d = make_one_byte_mod_13000_c5000(d, addr, val, new_val, debug)
  return d

def make_steer_angle_rate_acc_patch_mod(d, fw_ver, debug=False):
  print('Removing effects of steer angle rate acc')
  for addr, val, new_val in steer_angle_rate_acc_patch_table[fw_ver]:
    d = make_one_byte_mod_13000_c5000(d, addr, val, new_val, debug)
  return d

def make_multiplier_accumulator_patch_mod(d, fw_ver, debug=False):
  print('Set multiplier_accumulator to 1')
  for addr, val, new_val in multiplier_accumulator_patch_table[fw_ver]:
    d = make_one_byte_mod_13000_c5000(d, addr, val, new_val, debug)
  return d

def make_c9a88_patch_mod(d, fw_ver, debug=False):
  print('Change clamp of math_result_1 from 0xF0 to 0xFF')
  for addr, val, new_val in patch_table_for_c9a88[fw_ver]:
    d = make_one_byte_mod_13000_c5000(d, addr, val, new_val, debug)
  return d

def make_query_fw_version_return_ram_vars_mod(d, fw_ver, debug=False):
  print('Make query_fw_version_return_ram_vars mod...')
  for addr, val, new_val in query_fw_version_return_ram_vars_patch_table[fw_ver]:
    d = make_one_byte_mod_13000_c5000(d, addr, val, new_val, debug)
  return d

def scale_a_table(d, table_name, table_stock_vals, scale_factors, debug=False):
  print(table_name, ['Column %d, %.2fX' % (i, scale_factors[i]) for i in range(len(scale_factors)) if scale_factors[i] != 1])
  mod_d = bytearray(d)
  for addr in table_stock_vals:
    assert len(table_stock_vals[addr]) == len(scale_factors), 'Length mismatch: {} != {}'.format(len(table_stock_vals), len(scale_factors))
    torques = list(struct.unpack('<%dH' % len(table_stock_vals[addr]), d[addr:(addr + len(table_stock_vals[addr]) * 2)]))
    for i in range(len(torques)):
      assert table_stock_vals[addr][i] == torques[i], 'Torque table item mismatch 0x%X item %d' % (addr, i)
    if debug:
      print(hex(addr), hex(addr - addr % 0x1000), "Old", [hex(t) for t in torques])
    for i in range(len(torques)):
      torques[i] = int(torques[i] * scale_factors[i])
    new_torque_bytes = struct.pack('<%dH' % len(torques), *torques)
    mod_d[addr:addr+len(torques)*2] = new_torque_bytes
    if debug:
      new_torques = struct.unpack('<%dH' % len(torques), mod_d[addr:addr + len(torques) * 2])
      print(hex(addr), hex(addr - addr % 0x1000), 'New', [hex(t) for t in new_torques])

  for addr in table_stock_vals:
    start_addr = addr - addr % 0x1000
    end_addr = start_addr + 0x1000
    h_new = zlib.crc32(mod_d[start_addr:(end_addr - 4)], 0)
    mod_d[end_addr - 4:end_addr] = struct.pack("<I", h_new)
    h_old = zlib.crc32(d[start_addr:(end_addr - 4)], 0)
    if debug:
      print(hex(start_addr), 'Original CRC', "%08X" % (h_old & 0xFFFFFFFF))
      print(hex(start_addr), 'New      CRC', "%08X" % (h_new & 0xFFFFFFFF))
    if not check_crc32_in_bin_data(mod_d, start_addr, end_addr):
      sys.exit(0)
  return mod_d

def make_torque_table_mod(d, fw_ver, debug=False):
  assert fw_ver in ['TVA-A150', 'TVA-A160']
  print('Tables mod')
  mod_d = bytearray(d)
  if not all([x == 1 for x in scale_factors_cb994]):
    mod_d = scale_a_table(mod_d, 'Table 0xcb994', accord_a150_a160_torque_table_cb994_stock_vals, scale_factors_cb994, debug)
  if not all([x == 1 for x in scale_factors_c9a88]):
    mod_d = scale_a_table(mod_d, 'Table 0xc9a88', accord_a150_a160_torque_table_c9a88_stock_vals, scale_factors_c9a88, debug)
  if not all([x == 1 for x in scale_factors_cb7d4]):
    mod_d = scale_a_table(mod_d, 'Table 0xcb7d4', accord_a150_a160_torque_table_cb7d4_stock_vals, scale_factors_cb7d4, debug)
  if not all([x == 1 for x in scale_factors_cb844]):
    mod_d = scale_a_table(mod_d, 'Table 0xcb844', steer_torque_req_clamped_by_vehicle_speed_table_stock_vals, scale_factors_cb844, debug)
  print('Make torque table mod done')
  return mod_d

def transfer_data(block_size, encrypted, uds_client):
  # account for service id and block sequence count (one byte each)
  chunk_size = block_size - 2
  cnt = 0
  for i in tqdm(range(0, len(encrypted), chunk_size)):
    cnt += 1
    try:
      if uds_client:
        block_size = uds_client.transfer_data(cnt & 0xFF, encrypted[i:i+chunk_size])
      # print('send chunk', i, i+chunk_size, ', ', len(encrypted[i:i+chunk_size]), 'bytes')
    except NegativeResponseError as e:
      print('eps report negative response for transfer_data', e)
      sys.exit(0)
    except MessageTimeoutError:
      print('Timeout for request_download')


def query_fw_version(uds_client):
  print('Querying fw version...')
  try:
    uds_client.tester_present()
    uds_client.diagnostic_session_control(SESSION_TYPE.DEFAULT)
    uds_client.diagnostic_session_control(SESSION_TYPE.EXTENDED_DIAGNOSTIC)
  except NegativeResponseError:
    pass
  except InvalidServiceIdError:
    print('InvalidServiceIdError for init')
    sys.exit(0)
  except MessageTimeoutError:
    sys.exit(0)
  try:
    data = uds_client.read_data_by_identifier(DATA_IDENTIFIER_TYPE.APPLICATION_SOFTWARE_IDENTIFICATION )  # type: ignore
    print('APPLICATION_SOFTWARE_IDENTIFICATION', data)
    return data
  except InvalidServiceIdError:
    print('InvalidServiceIdError for APPLICATION_SOFTWARE_IDENTIFICATION')
    sys.exit(0)
  except (NegativeResponseError, MessageTimeoutError):
    sys.exit(0)

def do_flashing(encrypted, bin_data, bin_decryption_key, memory_address, memory_size, eps_versions, args, skip_fw_ver_check=False):
  tx_addr = 0x18DA30F1
  rx_addr = None
  security_key = b'\x02\x11\x02\x12\x12\x20'
  # For A150 and A160
  flash_inprogress_fw_ver = b'39990-TVA-A110\x00\x00',  # stock fw, flashing in progress
  print('Patch length', hex(memory_size), 'bytes')
  if args.dry:
    transfer_data(4082, encrypted[memory_address:memory_address+memory_size], None)
    if args.save_mod:
      with open('mod.bin', 'wb') as of:
        of.write(mod_d)
        print('Mod bin saved to mod.bin')
    sys.exit(0)

  panda = Panda()
  panda.set_safety_mode(Panda.SAFETY_ELM327)
  bus = 1 if panda.has_obd() else 0
  uds_client = UdsClient(panda, tx_addr, rx_addr, bus, timeout=5*60, debug=args.debug)

  fw_ver = query_fw_version(uds_client)
  fw_ver_found = False
  bin_hash_matched = True   # For accord only
  if fw_ver == flash_inprogress_fw_ver:
    print('Unfinished flash detected, go ahead for new flash session.')
    fw_ver_found = True
  else:
    for x in eps_versions:
      if any([v == fw_ver for v in x['versions']]):
        fw_ver_found = True
      if fw_ver_found:
        print('Validating chunk hash for stock fw bin.')
        for start_addr, end_addr, h in x['chunk_hashes']:
          h_result = zlib.crc32(bin_data[start_addr:(end_addr)], 0)
          hash_in_file = struct.unpack("<I", bin_data[end_addr:end_addr+4])[0]
          if h != h_result:
            bin_hash_matched = False
            print('Chunk hash calculated mismatch', hex(start_addr), h, h_result)
            break
          if h != hash_in_file:
            bin_hash_matched = False
            print('Chunk hash mismatch', hex(start_addr), h, hash_in_file)
            break
        break
  if not skip_fw_ver_check and not fw_ver_found:
    print(fw_ver, 'is unknown')
    sys.exit(0)
  if not skip_fw_ver_check and not bin_hash_matched:
    sys.exit(0)

  try:
    uds_client.diagnostic_session_control(SESSION_TYPE.EXTENDED_DIAGNOSTIC)
  except NegativeResponseError:
    print('eps report negative response for EXTENDED_DIAGNOSTIC')
  except MessageTimeoutError:
    print('Timeout for EXTENDED_DIAGNOSTIC')

  try:
    security_seed = uds_client.security_access(ACCESS_TYPE.REQUEST_SEED)
    print('Got security_seed', security_seed)
  except NegativeResponseError as e:
    print('eps report negative response for REQUEST_SEED', e)
    sys.exit(0)
  except MessageTimeoutError:
    print('Timeout for REQUEST_SEED')

  seed = struct.unpack('>H', security_seed)[0]
  k1, k2, k3 = struct.unpack('>HHH', security_key)
  print('Seed', hex(seed), 'k1', hex(k1), 'k2', hex(k2), 'k3', hex(k3))
  security_key = (k2 * seed % k3) ^ (k1 + seed)
  bin_security_key = struct.pack('>H', security_key)
  try:
    uds_client.security_access(ACCESS_TYPE.SEND_KEY, bin_security_key)
    print('SEND_KEY done, ready for erase and flashing.')
  except NegativeResponseError as e:
    print('eps report negative response for SEND_KEY', e)
    sys.exit(0)
  except MessageTimeoutError:
    print('Timeout for SEND_KEY')

  try:
    uds_client.diagnostic_session_control(SESSION_TYPE.PROGRAMMING)
  except NegativeResponseError:
    print('eps report negative response for PROGRAMMING')
    sys.exit(0)
  except MessageTimeoutError:
    print('Timeout for PROGRAMMING')
    sys.exit(0)

  try:
    uds_client.routine_control(ROUTINE_CONTROL_TYPE.START, ROUTINE_IDENTIFIER_TYPE.ERASE_MEMORY)
    print('ERASE_MEMORY done')
  except NegativeResponseError:
    print('eps report negative response for ERASE_MEMORY')
    sys.exit(0)
  except MessageTimeoutError:
    print('Timeout for ERASE_MEMORY')
    sys.exit(0)

  try:
    uds_client.write_data_by_identifier(0xF101, bin_decryption_key)
    print('Set programming key done')
  except NegativeResponseError:
    print('eps report negative response for set programming key')
    sys.exit(0)
  except MessageTimeoutError:
    print('Timeout for set programming key')
    sys.exit(0)

  try:
    block_size = uds_client.request_download(memory_address, memory_size)
    print('request_download done, block_size', block_size)
  except NegativeResponseError as e:
    print('eps report negative response for request_download', e)
    sys.exit(0)
  except MessageTimeoutError:
    print('Timeout for request_download')
    sys.exit(0)

  transfer_data(block_size, encrypted[memory_address:memory_address+memory_size], uds_client)

  try:
    uds_client.request_transfer_exit()
    print('request_transfer_exit done')
  except NegativeResponseError:
    print('eps report negative response for request_transfer_exit')
    sys.exit(0)
  except MessageTimeoutError:
    print('Timeout for request_transfer_exit')

  try:
    uds_client.routine_control(ROUTINE_CONTROL_TYPE.START, ROUTINE_IDENTIFIER_TYPE.CHECK_PROGRAMMING_DEPENDENCIES)
  except NegativeResponseError as e:
    print('eps report negative response for CHECK_PROGRAMMING_DEPENDENCIES', e)
    sys.exit(0)
  except MessageTimeoutError:
    print('Timeout for CHECK_PROGRAMMING_DEPENDENCIES')
  print('Flashing done!')

  if True:
    print('Waiting 30 secs for eps to get ready')
    time.sleep(10)
    print(query_fw_version(uds_client))

if __name__ == "__main__":
  parser = argparse.ArgumentParser()
  parser.add_argument('--bin', default="39990-TVA-A160.bin")
  parser.add_argument('--debug', action='store_true')
  parser.add_argument('--dry', action='store_true')
  parser.add_argument('--stock', action='store_true')
  parser.add_argument('--save_mod', action='store_true')
  parser.add_argument('--scale', default=2)
  parser.add_argument('--fw_ver', default="TVA-A160")
  args = parser.parse_args()

  bin_decryption_key =  b'\x00\x00\x00'
  memory_address = 0x13000
  memory_size = 0xed000

  with open(args.bin, 'rb') as f:
    bin_data = f.read()
  print('Bin size', len(bin_data), 'bytes')
  # Check the checksum of original bins
  if not check_all(bin_data, args.debug):
    sys.exit(-1)
  if not args.stock:
    mod_d = make_fw_version_mod(bin_data)
    # Mods for bench only, don't flash them to car!
    #mod_d = make_code_patch_mod(mod_d, args.fw_ver, args.debug)
    #mod_d = make_steer_status_mod(mod_d, args.fw_ver, args.debug)

    # Mods for car
    # Increase items in torque table.
    mod_d = make_torque_table_mod(mod_d, args.fw_ver, args.debug)
    # Increase torque output clamps.
    mod_d = make_torque_output_clamp_patch_mod(mod_d, args.fw_ver, args.scale, args.debug)
    # Increase torque sensor upper limits
    mod_d = make_torque_sensor_upper_limits_patch_mod(mod_d, args.fw_ver, args.debug)
    # Remove negative effects of steer angle rate acc, change the math?
    # mod_d = make_steer_angle_rate_acc_patch_mod(mod_d, args.fw_ver, args.debug)
    # Set multiplier_accumulator to 1
    # mod_d = make_multiplier_accumulator_patch_mod(mod_d, args.fw_ver, args.debug)
    # Increase math_result_1_rshift_6_minus_angle_rate_acc limit
    mod_d = make_math_result_1_rshift_6_minus_angle_rate_acc_limit_mod(mod_d, args.fw_ver, args.debug)
    # Change clamp of math_result_1 from 0xF0 to 0xFF
    mod_d = make_c9a88_patch_mod(mod_d, args.fw_ver, args.debug)
    # Change clamp of global_torque_result_1 from 512 to 1024
    mod_d = make_global_torque_result_1_clamp_mod(mod_d, args.fw_ver, args.debug)
    #mod_d = make_query_fw_version_return_ram_vars_mod(mod_d, args.fw_ver, args.debug)
    # Fine tune motor torque from 0.5 to 2.0
    # mod_d = make_motor_torque_fine_tune_mod(mod_d, args.fw_ver, args.debug)
    # Decrease steer angle_rate_acc's effect to 1/3
    # mod_d = make_angle_rate_acc_fine_tune_mod(mod_d, args.fw_ver, args.debug)
    # Steer to zero by instruction patching.
    #mod_d = make_steer_to_zero_patch_mod(mod_d, args.fw_ver, args.debug)
    # Enable boost mode.
    #mod_d = make_boost_mode_patch_mod(mod_d, args.fw_ver, args.debug)
    # Enable steer angle based steering
    #mod_d = make_angle_based_steering_patch_mod(mod_d, args.fw_ver, args.debug)
    if not check_all(mod_d, args.debug):
      sys.exit(-1)
  else:
    mod_d = bin_data
  # No encryption for accord
  encrypted = mod_d
  print('fw version %s, mod version %s, mod hash %X' % (args.fw_ver, mod_version, zlib.crc32(mod_d, 0)))
  do_flashing(encrypted, bin_data, bin_decryption_key, memory_address, memory_size, known_eps_versions, args, skip_fw_ver_check=True)
