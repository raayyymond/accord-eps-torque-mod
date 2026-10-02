import sys
from types import SimpleNamespace
import pytest
from opendbc.car import Bus
from opendbc.car.honda.tests.test_angle_v299 import make_cp, FW_A16B, FW_A160
from opendbc.car.honda.carstate import CarState
from opendbc.car.honda.hondacan import honda_checksum
with pytest.MonkeyPatch.context() as mp:
  CP = make_cp(mp, FW_A16B, True); CP0 = make_cp(mp, FW_A160, True)
cs = CarState(CP, SimpleNamespace(flags=0)); pt = cs.get_can_parsers(CP)[Bus.pt]
st = pt.message_states[0x1AB]
print("0x1AB state:", "ignore_alive", st.ignore_alive, "ignore_checksum", st.ignore_checksum, "ignore_counter", st.ignore_counter)
print("A160 parser has 0x1AB:", 0x1AB in CarState(CP0, SimpleNamespace(flags=0)).get_can_parsers(CP0)[Bus.pt].message_states)
bus = pt.bus
def frame(s10, cnt, good=True):
  mag = abs(s10) & 0x1FF; raw = mag | (0x200 if s10 < 0 else 0)
  d = bytearray([(raw >> 8) & 3, raw & 0xFF, (cnt & 3) << 4])
  ck = honda_checksum(0x1AB, None, d); d[2] |= (ck if good else (ck + 1) & 0xF)
  return bytes(d)
t = 1_000_000_000
# 50 Hz good frames with a 0x18F-like other frame on the bus, then bad checksum + random counters, then 0x1AB dead
out = []
for i in range(200):
  t += 10_000_000
  frames = [(0x18F, b"\x00" * 8, bus)]
  if i % 2 == 0 and i < 100: frames.append((0x1AB, frame(-100 if i < 50 else 37, i // 2, True), bus))
  if i % 2 == 0 and 100 <= i < 140: frames.append((0x1AB, frame(200, (i * 7) % 4, False), bus))
  pt.update([(t, frames)])
  v = cs.update_accord_eps_torque(pt)
  out.append((i, v, cs.accord_eps_torque_stale, st.counter_fail))
for i in (0, 10, 48, 52, 98, 100, 108, 110, 112, 120, 139, 150, 199):
  print(out[i])
print("max counter_fail on 0x1AB:", max(o[3] for o in out), "state.valid:", st.valid(pt._last_update_nanos, False))
