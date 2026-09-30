# -*- coding: utf-8 -*-
"""fork_real.py -- run the REAL StarPilot LatControlTorque (Dom 20d24ab79, the commit that flew on r71b) offline.

The fork is read ONLY: `ensure_extract()` makes a `git archive` of the needed subtrees of commit 20d24ab79 into
./_scratch/fork_20d24ab79 (gitignored) -- the operator's clone is never checked out, built or written.  Import
bootstrap as in studies/v294/redo_2026-09-23/fork/boot.py: `openpilot.X` -> extract/X, opendbc_repo on sys.path, and
three stubs for modules that cannot load on Windows and are not on the torque path (setproctitle, the tici hardware
layer, locationd.helpers.Pose).  Everything else -- LatControlTorque, PIDController, FirstOrderFilter, get_friction,
VehicleModel, the Accord steer-ratio map, the friction-threshold tables -- is the fork's own code, unmodified.

    import fork_real as FK
    ctl = FK.RealController(toggles)          # toggles = the runtime toggle dict recorded in r71b's meta
    out = ctl.step(active, v, angle, rate, pressed, ang_off, roll, des_curv, lat_delay, laf_off, steer_limited)
    # out = dict(torque (actuators.torque, +left), p, i, f, output (torqueState.output), la_des, la_act, jerk, error)

ANALYSIS ONLY.  Sends nothing, flashes nothing, commits nothing.
"""
import math
import os
import subprocess
import sys
import types
from types import SimpleNamespace

HERE = os.path.dirname(os.path.abspath(__file__))
FORK_REPO = r"C:/Users/dudei/Desktop/Projects/openpilots/raayyymond-StarPilot/StarPilot"
FORK_COMMIT = "20d24ab79"
EXTRACT = os.path.join(HERE, "_scratch", "fork_20d24ab79")
PATHS = ("selfdrive/controls/lib", "selfdrive/locationd/helpers.py", "common", "cereal", "opendbc_repo/opendbc",
         "starpilot/common")
STUBS = []
_READY = False


def ensure_extract():
    """git archive (READ-ONLY on the fork clone) of commit 20d24ab79 into _scratch; cereal/car.capnp is a symlink in the
    repo (-> opendbc car.capnp), which tar cannot create on Windows, so it is copied from the extracted opendbc."""
    if os.path.exists(os.path.join(EXTRACT, "selfdrive", "controls", "lib", "latcontrol_torque.py")) and \
       os.path.exists(os.path.join(EXTRACT, "cereal", "car.capnp")):
        return EXTRACT
    os.makedirs(EXTRACT, exist_ok=True)
    tar = os.path.join(HERE, "_scratch", "fork.tar")
    subprocess.run(["git", "-C", FORK_REPO, "archive", "--format=tar", "-o", tar, FORK_COMMIT, *PATHS], check=True)
    subprocess.run(["tar", "-xf", tar], cwd=EXTRACT, check=False)       # the car.capnp symlink fails; handled below
    import shutil
    shutil.copyfile(os.path.join(EXTRACT, "opendbc_repo", "opendbc", "car", "car.capnp"),
                    os.path.join(EXTRACT, "cereal", "car.capnp"))
    return EXTRACT


def _stub(name, **attrs):
    m = types.ModuleType(name)
    for k, v in attrs.items():
        setattr(m, k, v)
    sys.modules[name] = m
    STUBS.append(name)
    return m


def setup():
    global _READY
    if _READY:
        return
    root = ensure_extract()
    for p in (os.path.join(root, "opendbc_repo"), root):
        if p not in sys.path:
            sys.path.insert(0, p)
    pkg = types.ModuleType("openpilot")
    pkg.__path__ = [root]
    sys.modules["openpilot"] = pkg
    _stub("setproctitle", getproctitle=lambda: "x", setproctitle=lambda *a: None)
    hw = SimpleNamespace(get_device_type=lambda: "pc", get_sound_card_online=lambda: True)
    m = _stub("openpilot.system.hardware", PC=True, TICI=False, AGNOS=False, HARDWARE=hw)
    m.__path__ = [os.path.join(root, "system", "hardware")]
    _stub("openpilot.selfdrive.locationd.helpers", Pose=object)
    _READY = True


# ----------------------------------------------------------------------------------------------------------------------
# CarParams exactly as r71b's carParams (meta['carparams']) + the Honda interface's own scalings
# ----------------------------------------------------------------------------------------------------------------------
CP_R71B = dict(carFingerprint="HONDA_ACCORD", mass=1623.328125, wheelbase=2.8299999237060547,
               centerToFront=1.1036999225616455, tireStiffnessFactor=0.8467000126838684, steerRatio=16.329999923706055,
               steerLimitTimer=0.800000011920929, minSteerSpeed=0.0, steerActuatorDelay=0.10000000149011612,
               lat_friction=0.2120497077703476, lat_laf=1.689333438873291, torqueBP=[0, 4096], torqueV=[0, 4096])


def make_CP(cpd=CP_R71B):
    setup()
    from cereal import car
    from opendbc.car import scale_rot_inertia, scale_tire_stiffness
    CP = car.CarParams.new_message()
    CP.carFingerprint = cpd["carFingerprint"]
    CP.brand = "honda"
    CP.mass = cpd["mass"]
    CP.wheelbase = cpd["wheelbase"]
    CP.centerToFront = cpd["centerToFront"]
    CP.tireStiffnessFactor = cpd["tireStiffnessFactor"]
    CP.steerRatio = cpd["steerRatio"]
    CP.steerRatioRear = 0.0
    CP.rotationalInertia = scale_rot_inertia(CP.mass, CP.wheelbase)
    CP.tireStiffnessFront, CP.tireStiffnessRear = scale_tire_stiffness(CP.mass, CP.wheelbase, CP.centerToFront,
                                                                       CP.tireStiffnessFactor)
    CP.steerLimitTimer = cpd["steerLimitTimer"]
    CP.minSteerSpeed = cpd["minSteerSpeed"]
    CP.steerActuatorDelay = cpd["steerActuatorDelay"]
    CP.lateralParams.torqueBP = cpd["torqueBP"]
    CP.lateralParams.torqueV = cpd["torqueV"]
    tq = CP.lateralTuning.init("torque")
    tq.friction = cpd["lat_friction"]
    tq.latAccelFactor = cpd["lat_laf"]
    tq.latAccelOffset = 0.0
    tq.steeringAngleDeadzoneDeg = 0.0
    return CP.as_reader()          # controlsd holds a READER (log_from_bytes); LatControlTorque calls .as_builder()


class _CI:
    """the two callbacks LatControlTorque takes from the CarInterface -- bound to the REAL CarInterfaceBase methods
    (Honda does not override them: opendbc/car/honda/interface.py has no torque_from_lateral_accel)."""
    def __init__(self):
        from opendbc.car.interfaces import CarInterfaceBase
        self._b = CarInterfaceBase

    def torque_from_lateral_accel(self):
        return lambda la, tp: self._b.torque_from_lateral_accel_linear(self, la, tp)

    def lateral_accel_from_torque(self):
        return lambda t, tp: self._b.lateral_accel_from_torque_linear(self, t, tp)


class RealController:
    """controlsd's lateral slice around the REAL LatControlTorque, per 100 Hz frame, in controlsd's order:
    pid._k_p <- toggles.steerKp ; VM.update_params(stiffness, accord SR map(angle - offset, level)) ;
    update_live_torque_params(LAF custom, offset learned, friction custom) ; LaC.update(...).
    Returns actuators.torque (+left) and the torqueState fields."""

    def __init__(self, toggles, cpd=CP_R71B, dt=0.01):
        setup()
        from opendbc.car.vehicle_model import VehicleModel
        from openpilot.selfdrive.controls.lib.latcontrol_torque import LatControlTorque
        from openpilot.selfdrive.controls.lib import latcontrol_vehicle_tunes as VT
        self.VT = VT
        self.CP = make_CP(cpd)
        self.tg = SimpleNamespace(**toggles)
        self.LaC = LatControlTorque(self.CP, _CI(), dt)
        self.VM = VehicleModel(self.CP)
        self.sr_level = float(self.tg.steerRatio) if getattr(self.tg, "use_custom_steerRatio", False) else None
        self.use_vsr = bool(getattr(self.tg, "accord_variable_steer_ratio", True))

    def step(self, active, v, angle, rate, pressed, ang_off, roll, des_curv, lat_delay, laf_off, steer_limited,
             stiffness=1.0, lp_sr=16.84, curvature_limited=False):
        tg = self.tg
        self.LaC.pid._k_p = tg.steerKp
        ang = angle - ang_off
        sr = self.VT.get_honda_accord_steer_ratio(ang, self.sr_level) if self.use_vsr else max(lp_sr, 0.1)
        self.VM.update_params(max(stiffness, 0.1), sr)
        laf = float(tg.latAccelFactor) if getattr(tg, "use_custom_latAccelFactor", False) else None
        fric = float(tg.friction) if getattr(tg, "use_custom_friction", False) else None
        self.LaC.update_live_torque_params(float(laf), float(laf_off), float(fric))   # capnp Float32 fields
        if not active:
            self.LaC.reset()
        CS = SimpleNamespace(vEgo=v, steeringAngleDeg=angle, steeringRateDeg=rate, steeringPressed=bool(pressed),
                             standstill=False)
        lp = SimpleNamespace(angleOffsetDeg=ang_off, roll=roll)
        torque, _, pl = self.LaC.update(bool(active), CS, self.VM, lp, bool(steer_limited), des_curv, curvature_limited,
                                        lat_delay, None, None, tg)
        L = self.LaC
        # p/i/f/la_* below are the controller's FLOAT64 internals; log_* are the torqueState fields as logged (capnp
        # Float32 read-backs).  On inactive frames pid_log carries zeros; la_act is still the controller's measurement.
        return dict(torque=float(torque), p=float(L.pid.p), i=float(L.pid.i), f=float(L.pid.f), output=float(torque),
                    la_des=float(L.prev_desired_lateral_accel) if active else 0.0, la_act=float(L.previous_measurement),
                    log_p=float(pl.p), log_i=float(pl.i), log_f=float(pl.f), log_output=float(pl.output),
                    log_la_des=float(pl.desiredLateralAccel), log_la_act=float(pl.actualLateralAccel),
                    jerk=float(pl.desiredLateralJerk), error=float(pl.error), active=bool(pl.active),
                    sat=bool(pl.saturated))

    def measured_curvature(self, angle, ang_off, v, roll):
        """controlsd's curvature from the angle (same VM, same SR map) -- for the harness's own use."""
        ang = angle - ang_off
        sr = self.VT.get_honda_accord_steer_ratio(ang, self.sr_level) if self.use_vsr else 16.84
        self.VM.update_params(1.0, sr)
        return -self.VM.calc_curvature(math.radians(ang), v, roll)


def honda_rate_limit_and_can(torque_cmd, last_torque, steer_max=4096, delta=3, dt=0.01):
    """opendbc honda/carcontroller.py: limited = rate_limit(cmd, last, -3*DT, +3*DT) ; apply = int(interp(-limited*4096,
    [-4096, 0, 4096], [-4096, 0, 4096])) -- int() truncates toward zero.  Returns (limited, can_counts)."""
    lim = min(max(torque_cmd, last_torque - delta * dt), last_torque + delta * dt)
    x = -lim * steer_max
    x = min(max(x, -steer_max), steer_max)
    return lim, int(x)
