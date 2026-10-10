# 06 - Position feedback: encoders and friends

Why you care: FOC needs the rotor angle every PWM cycle, and your robot needs
the joint angle. With 21 pole pairs, every 0.1° of encoder error becomes 2.1°
of electrical error. "Great precision" lives and dies here.

---

## 1. Four words that are not the same thing

| Term | Meaning | Example |
|------|---------|---------|
| **Resolution** | Smallest step the sensor reports | 14-bit = 16384 counts/rev = 0.022° |
| **Accuracy** | How far the reported angle is from the true angle | ±0.5° typical uncalibrated magnetic encoder |
| **Noise / repeatability** | How much the reading jitters when nothing moves | 0.01-0.05° RMS |
| **Latency** | How old the angle is when you read it | 2-100 µs depending on chip/filter |

A 21-bit encoder with ±0.5° accuracy is still a ±0.5° encoder - but its high
resolution and low noise make velocity estimation and calibration much better.
Accuracy can be improved by **calibration** (lookup table); noise and latency
cannot be calibrated away.

---

## 2. Sensor types

| Type | How | Pros | Cons | Who uses it |
|------|-----|------|------|-------------|
| **On-axis magnetic** | Diametric magnet on the shaft end; Hall array IC directly underneath on the PCB | Cheap, absolute single-turn, robust to dust/oil, tiny | Needs a magnet on the rotation axis; sensitive to misalignment and stray fields | Nearly all small robot actuators (clone photo 2, box 1) |
| **Off-axis / ring magnetic** | Multipole magnetic ring + sensor at the side (or vernier "nonius" rings) | Works with **hollow shafts** | More expensive / more calibration | iC-MU, RLS AksIM-2, MPS MA7xx "side-shaft" mode |
| **Optical** | Light through a coded disc | Very high accuracy | Bigger, dirt-sensitive, expensive | Industrial servos |
| **Inductive** | PCB coils + metal target | Robust, accurate, immune to magnets, can be hollow | More complex analog front end | Some industrial / automotive |
| **Hall sensors (3x)** | Detect magnet poles every 60° electrical | Cheap, gives coarse absolute commutation | 60° steps only - not for FOC precision | E-bikes, backup/startup |
| **Resolver / sin-cos** | Analog transformer or sine/cosine signals | Extremely robust, analog high resolution | Needs excitation + analog front end | Industrial (the STMBL board supports these - box 8 op-amps) |

---

## 3. Magnetic encoder ICs worth knowing

| Chip | Resolution | Interfaces | Notes |
|------|------------|------------|-------|
| **AS5047P** (ams OSRAM) | 14-bit | SPI, ABI, UVW, PWM | Popular in ODrive/SimpleFOC. Dynamic angle error compensation (DAEC) for latency. |
| **MT6835** (MagnTek) | up to 21-bit | SPI, ABZ, UVW | High resolution, built-in calibration; common on newer Chinese actuators. |
| **MT6701** (MagnTek) | 14-bit | SSI, I²C, ABZ, UVW, PWM, analog | Cheap and flexible. Fine for an **output-side** encoder. |
| **MA732 / MA702** (MPS) | 14 / 12-bit | SPI, ABZ, UVW | Low latency; supports side-shaft (off-axis) mounting with calibration. |
| **TLE5012B** (Infineon) | 15-bit | SSC (SPI-like), IIF, PWM | Automotive grade. |
| **AS5600** | 12-bit | I²C, analog/PWM | Too slow and coarse for good FOC; OK for a knob. |

The chip on the back of the DM board (photo 2, box 1) is a QFN in the centre of
a white circle - an on-axis magnetic encoder; the marking is not legible enough
to name it (it is in the MT68xx class by size/placement).

---

## 4. The magnet and mechanics (more important than the chip!)

- **Diametrically magnetised disc** (N on one half of the face, S on the
  other), e.g. Ø6 × 2.5 mm NdFeB. The datasheet specifies diameter and field
  strength range.
- **Air gap**: typically 0.5-3 mm between magnet face and chip, per
  datasheet. Too close = saturation, too far = noise.
- **Centering**: the magnet axis must align with the chip centre within
  ~0.1-0.3 mm, and the PCB must sit parallel to the magnet. Misalignment ->
  **1× and 2× per revolution error**. Design the housing so the PCB is
  located by precise features (pins/bosses), not just screw holes with
  clearance.
- **Magnet holder must be non-magnetic** (aluminium, brass, plastic,
  stainless 304 - not ordinary steel). A steel shaft right behind the magnet
  distorts the field.
- **Stray fields**: the motor's own magnets and winding currents produce
  fields at the sensor. Keep distance, sometimes a soft-iron shield cup around
  the magnet, and calibrate with the motor running.
- The **"magnet keep-out" circle** on the PCB (photo 2, box 2): no
  high-current traces near the chip - 10 A in a trace 5 mm away makes a
  measurable field. Route power far away from the encoder.

### Your WK8110 is frameless with a 58.5 mm bore - where does the magnet go?

The centre of the motor is a big hole, so there is no shaft end by default.
Options:

1. **Central hub/shaft**: the rotor carrier you design includes a small
   shaft or plate across the centre (often the planetary **sun gear shaft**),
   with the magnet glued at its end. The PCB sits behind the motor with the
   encoder IC on the axis. This is how most SteadyWin-style actuators do it
   (board on the back, chip in the middle on the side facing the motor).
2. **Off-axis ring**: if you want a hollow-shaft actuator (cables through the
   middle), use a multipole ring + off-axis sensor (iC-MU, AksIM-2, MA7xx
   side-shaft). More money, more care.

Decide this together with the mechanical design - **it fixes where the encoder
sits on your PCB**, which drives the whole layout.

---

## 5. Interfaces: which to use with the ESP32-S3

| Interface | Gives | ESP32-S3 support | Recommendation |
|-----------|-------|------------------|----------------|
| **SPI** | Absolute angle, on request, plus status/diagnostics | Hardware SPI (SPI2/SPI3), DMA | **Use this for the motor encoder.** Read once per FOC cycle. 16-24 bits at 5-20 MHz = 1-5 µs. |
| ABZ (quadrature) | Incremental counts, very low latency | PCNT peripheral counts in hardware | Good *addition* to SPI (absolute at boot via SPI, then fast counts). Optional. |
| UVW | Hall-like 60° signals | GPIO | Backup only. |
| I²C | Absolute, slow | Yes | Output-side encoder at ~1 kHz is OK; not for the FOC loop. |
| SSI / BiSS-C / RS-485 | Absolute over long cables, differential | SPI + RS-485 transceiver | For an output encoder on a cable in a noisy robot. |
| PWM | Angle as duty cycle | MCPWM capture | Slow (~1 kHz), avoid. |

Signal integrity tips:

- Encoder IC on the **same PCB** as the MCU when possible (short SPI lines,
  no connector). On a separate small board -> keep the cable short, add series
  resistors (22-47 Ω) on SCLK/MOSI at the driver end, and slow the clock.
- Decouple the encoder supply locally (100 nF + 1 µF), optional ferrite bead
  or a dedicated LDO for its analog supply.

---

## 6. Multiple feedback sources at the same time (sensor fusion)

You mentioned wanting several types of feedback. Typical high-end setup:

1. **Motor-side absolute encoder** (on-axis, SPI, high resolution) ->
   commutation (FOC angle) + velocity.
2. **Output-side absolute encoder** (after the gearbox) -> true joint angle,
   backlash/elastic deflection, absolute position at power-up.
3. **Phase currents** -> torque estimate (Kt × Iq).
4. **Optional**: Hall sensors as a sanity check, IMU, joint torque sensor
   (strain gauge), temperature for Kt compensation.

How they are combined:

- Velocity from the motor encoder with a **PLL/observer** (a small filter that
  estimates angle and speed together - lower noise than differentiating).
- Output position from the output encoder; **multi-turn motor position at
  boot** from the combination: if the gear ratio is N, the motor angle and
  output angle together identify which of the N motor turns you are on (works
  best if you check consistency; vernier principle).
- Difference between motor angle/N and output angle = backlash + compliance
  -> can be used for **compensation or even torque estimation** if the
  transmission is elastic.

On the PCB this means: one SPI encoder IC on board (motor), plus a **connector
for the second encoder** (power, GND, SPI or I²C or RS-485), exactly like the
GIM board's "2nd Encoder" header (box 11).

---

## 7. Calibration procedures to plan for (firmware, but the hardware must allow it)

1. **Electrical offset**: drive a fixed current vector (e.g. d-axis), let the
   rotor settle, read encoder -> that angle = electrical zero. Also checks
   direction and pole pairs.
2. **Linearity / eccentricity table**: rotate slowly in open loop at constant
   electrical speed, record encoder vs commanded angle, build a correction
   LUT (e.g. 128-1024 entries). Big win for cheap magnetic encoders.
3. **Anti-cogging map**: measure the Iq needed to hold position at many
   angles, then feed it forward. Needs a repeatable encoder.

Next: [07 Power input and protection](07_Power_Input_and_Protection.md)
