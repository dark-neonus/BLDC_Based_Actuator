# 02 - BLDC motors and Field Oriented Control (FOC)

Why you care: you cannot design a good driver without knowing what the load
does to it. The motor decides your currents, voltages, PWM frequency, sensor
needs and what happens when the robot back-drives the joint.

---

## 1. What is inside a BLDC / PMSM

- **Stator**: steel teeth with copper coils, wired as 3 phases (U, V, W),
  usually in a star (Y). Three wires come out. Your WK8110 stator is the ring
  with teeth in the drawing.
- **Rotor**: a ring of permanent magnets (alternating N/S). In an
  outrunner/frameless pancake motor like the 8110 the magnets sit on a ring
  around (outside) the stator.
- **Pole pairs (p)**: number of N+S magnet pairs. A 42-magnet rotor has 21 pole
  pairs.

### Electrical vs mechanical angle

The controller cares about where the magnets are relative to the coils, which
repeats every pole pair:

**θ_electrical = p × θ_mechanical**

With 21 pole pairs, one mechanical revolution = 21 electrical revolutions. So:

- An encoder error of 0.1° mechanical = 2.1° electrical. High pole count motors
  **need good encoders** for smooth FOC.
- At 600 rpm mechanical (10 rev/s) the electrical frequency is 210 Hz.

How to find p on your motor: (a) count the magnets and divide by 2; or (b)
apply a small DC current through two phases (bench supply, current-limited to
~1-2 A) - the rotor snaps to a position; turn it by hand and count the "detent
steps" per revolution of strong holding positions: there are p of them; or (c)
spin it and compare electrical back-EMF frequency to mechanical speed.

---

## 2. Back-EMF: the motor is also a generator

When the rotor turns, magnets sweep past the coils and induce a voltage, the
**back-EMF**, proportional to speed:

**V_bemf = Ke × ω**

- In a PMSM (like your motor) it is roughly sinusoidal -> sinusoidal drive /
  FOC fits it best.
- It *opposes* the supply. Max speed is reached when back-EMF ≈ available
  voltage (≈ bus voltage / √3 for line-to-line peak with SVPWM, minus losses).
- **When you brake or the robot back-drives the joint, back-EMF pushes current
  back into the supply.** If the supply cannot absorb it (a lab PSU cannot; a
  battery mostly can), the bus voltage rises - "bus pumping". This is the
  "back-EMF protection" topic, and it lives in module
  [07](07_Power_Input_and_Protection.md). Demo:
  [interactive/06_regen_bus_pump.html](interactive/06_regen_bus_pump.html).

### Kv and Kt

- **Kv** [rpm/V]: no-load speed per volt. Low Kv = more torque per amp, lower
  speed. Actuator motors are low Kv (~50-150).
- **Kt** [N·m/A]: torque per amp. Physically the same constant as Ke (in SI
  units). Rule of thumb: **Kt ≈ 8.3 / Kv** (Kv in rpm/V). The exact factor
  depends on whether amps are RMS/peak and line/phase conventions, so measure
  it on your setup if precision matters.
- Example: Kv 100 -> Kt ≈ 0.083 N·m/A. At 20 A -> ~1.66 N·m at the rotor. With a
  9:1 gearbox -> ~15 N·m at the output (minus gearbox losses).

### Electrical model of one phase

```
   V_phase ---[ R ]---[ L ]---( back-EMF e = Ke·ω )--- star point
```

- R: winding resistance (copper losses I²R -> heat).
- L: winding inductance (smooths PWM, limits how fast current can change ->
  limits current-loop bandwidth).
- Time constant τ = L/R. For small actuator motors ~ 0.2-2 ms.

Measure: R with a 4-wire method or "set 1 A on a bench supply and read the
voltage" between two phases (that gives 2R in star). L with an LCR meter
between two phases (gives 2L). Many FOC firmwares (ODrive, SimpleFOC, moteus)
also measure them automatically.

---

## 3. Ways to drive it (from simple to good)

### Six-step (trapezoidal) commutation

At any time two phases conduct and one floats. The pattern changes every 60°
electrical, based on 3 Hall sensors or back-EMF zero-crossing. Simple, used in
drones and cheap e-bikes. **Torque ripple** at every step (bad for smooth,
precise, low-speed actuators). Not what you want.

### Sinusoidal commutation

Drive all three phases with sine waves 120° apart, using the encoder angle.
Smoother, but controlling the current *magnitude and phase* gets hard as speed
rises (motor inductance shifts the phase).

### Field Oriented Control (FOC) - what you will use

Idea: instead of controlling three AC currents, transform them into a frame
that **rotates with the rotor**. In that frame, at steady state, currents
become two **DC values**:

- **Iq** (quadrature): perpendicular to the magnet field -> **makes torque**.
- **Id** (direct): aligned with the magnet field -> makes no torque (just heat),
  normally regulated to 0 (or negative for field weakening at high speed).

DC values are easy to control with simple PI controllers. That is the trick.

```
 measured Ia, Ib (Ic = -Ia - Ib)
        |
   [ Clarke ]   3-phase -> 2-axis stationary (α, β)
        |
   [ Park ]     rotate by -θe (encoder!) -> rotating (d, q)
        |
  Id, Iq ----> compare to Id_ref = 0, Iq_ref = torque/Kt
        |
   [ PI_d ], [ PI_q ]  -> Vd, Vq
        |
   [ inverse Park ]  rotate by +θe -> Vα, Vβ
        |
   [ SVPWM ]  -> three duty cycles -> MOSFETs
```

- **Clarke**: Iα = Ia, Iβ = (Ia + 2·Ib)/√3 (amplitude-invariant form).
- **Park**: Id = Iα·cosθ + Iβ·sinθ, Iq = -Iα·sinθ + Iβ·cosθ.
- **SVPWM** (space vector PWM): a way to compute the three duties that uses
  ~15 % more of the bus voltage than plain sine PWM. Equivalent trick: add the
  "min-max" common-mode offset to the three sine references.

> Demo: [interactive/04_foc_vectors.html](interactive/04_foc_vectors.html).
> Watch the three sine currents form one rotating arrow, and how the d/q view
> turns it into two steady numbers.

### What FOC needs from the hardware

1. **Rotor electrical angle**, accurate and fresh (encoder, module 06).
   Encoder offset relative to the magnets must be calibrated once ("alignment").
2. **At least two phase currents**, sampled at the same moment, synchronized
   to the PWM (module 05).
3. **Bus voltage** (to scale voltage commands to duty cycles) - a simple
   resistor divider into the ADC.
4. Fast enough MCU to run the loop at 10-40 kHz (module 10).

---

## 4. Control loops on top of FOC (where "PID" lives)

"FOC or PID" is not an either/or: **FOC is the innermost current/torque
controller; PID loops sit around it.** A typical cascade:

```
 position_ref -> [P or PID] -> velocity_ref -> [PI] -> Iq_ref -> [FOC current PI] -> motor
       ^                             ^                       ^
       |                             |                       |
   encoder angle              encoder speed             phase currents
   (~1-2 kHz)                 (~2-10 kHz)               (10-40 kHz)
```

Rules:

- Each outer loop should be ~5-10× slower (lower bandwidth) than the loop
  inside it.
- Velocity is usually computed by differentiating the encoder angle -> noise is
  amplified. Encoder resolution and noise directly limit how stiff and smooth
  your velocity and position loops can be. A PLL/observer or filter helps.
- **Feedforward** (adding the known required torque, e.g. gravity compensation
  or inertia × desired acceleration) gives much better tracking than raising
  gains.

### The "MIT mode" command (used by legged-robot actuators)

Many robot actuators (MIT Mini Cheetah, SteadyWin, DaMiao, CubeMars) accept, over
CAN, a combined command:

**τ = Kp × (θ_des - θ) + Kd × (ω_des - ω) + τ_ff**

The actuator runs this at kHz rate locally, so the robot's main computer can
set stiffness/damping and a feedforward torque at a lower rate. Plan your
firmware/communication so this mode is possible.

> Demo: [interactive/07_cascade_pid.html](interactive/07_cascade_pid.html)
> lets you tune a cascaded loop and see how encoder resolution and noise
> limit you.

---

## 5. Things that limit precision (and which hardware choice fixes them)

| Problem | Symptom | Hardware fix |
|---------|---------|--------------|
| Cogging torque (magnets prefer certain positions) | Periodic torque ripple, "notchy" at low speed | Mostly motor design; firmware anti-cogging map needs a **high-res, repeatable encoder** |
| Encoder nonlinearity | Ripple at 1× and 2× per revolution | Good magnet alignment, calibration table, better encoder |
| Current offset/gain errors | Torque ripple at electrical frequency | Good CSA, offset calibration at startup, matched gain |
| Dead-time distortion | Distortion at low current/zero crossings | Short dead time, fast MOSFETs/driver, dead-time compensation in firmware |
| Backlash in gearbox | Output position differs from motor position | **Second encoder on the output** (dual-encoder) |
| Friction / stiction | Stick-slip at low speed | Feedforward friction model, torque sensing |

---

## 6. Motor + gearbox: why the actuator board cares

The board sits inside a housing with a gearbox (the clone photo 1 shows the
planetary ring gear on the left). Consequences:

- **Reflected inertia** = motor inertia × ratio². Backdrivable actuators use
  low ratios (6:1 to 10:1) so that the robot can feel and react to impacts.
- **Output position** after a gearbox is ambiguous after power-up if you only
  measure the motor (a 9:1 ratio means 9 motor turns per output turn). Either
  home the joint, or add an absolute encoder on the output (the GIM board has a
  "2nd encoder" header for exactly this).

Next: [03 MOSFETs and the half-bridge](03_MOSFETs_and_Half_Bridge.md)
