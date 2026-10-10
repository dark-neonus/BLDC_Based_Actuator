# 05 - Current sensing

Why you care: torque = Kt × current. **Your actuator's torque precision is your
current-measurement precision.** It is also your main protection sensor.

---

## 1. The basic idea: a shunt resistor

Pass the current through a tiny, precise resistor and measure the voltage
across it (Ohm's law):

```
 I ──►──[ R_shunt = 1 mΩ ]──►──
         |               |
       sense+          sense-      V = I × R = 30 A × 1 mΩ = 30 mV
```

30 mV is too small for an ADC directly -> amplify it (×10 to ×40) with a
**current-sense amplifier (CSA)**.

Choosing R_shunt is a trade-off:

| Bigger shunt | Smaller shunt |
|--------------|---------------|
| More signal -> better resolution, less sensitive to noise/offset | Less signal, offset errors matter more |
| More heat: P = I²R (1 mΩ @ 30 A = 0.9 W; 2 mΩ = 1.8 W!) | Less heat |
| Bigger voltage drop | Smaller drop |

Clone boards use **1 mΩ (R001)** and **2 mΩ (R002)** 2512-size shunts. That's
the typical range for 20-50 A actuators.

What makes a good shunt: low tempco (< 50-100 ppm/°C, metal-element/"alloy"
types), low inductance (wide, short body), enough power rating with derating,
and ideally **4-terminal (Kelvin) packages** or at least Kelvin routing.

### Kelvin connection - the most important routing rule here

At 1 mΩ, **the solder joints and copper next to the shunt are comparable to
the shunt itself**. If your sense traces connect somewhere along the
high-current copper, you measure copper resistance too (which changes with
temperature and is not known).

```
   WRONG                                   RIGHT (Kelvin)
 ════════╦═══[SHUNT]═══╦════════      ════════[SHUNT]════════
         ║             ║                       │     │
       sense+        sense-                 sense+  sense-
  (tapped off the power copper)     (thin traces from the INNER edge
                                     of each pad, routed as a tight
                                     differential pair to the amplifier)
```

Sense traces: a **tight parallel pair**, away from switch nodes, to the
amplifier, with the RC filter right at the amplifier inputs.

---

## 2. Where to put the shunt(s)

### A. Low-side shunts (most common in actuators)

One shunt between each low-side FET source and GND (see module 03 diagram).

- Pros: the voltage is near ground -> simple, cheap amplifier (even a plain
  op-amp like the RS724 on the 3GIMD board). This is what both clone boards
  and most DRV8323-based designs do.
- Cons: **current flows through the shunt only while the low-side FET is ON.**
  You must sample at the moment all low-side FETs are on - the **centre of
  the PWM period** in center-aligned PWM. At high duty cycles the low-side
  on-time becomes too short to get a settled measurement -> need ≥ 2 shunts and
  use the two phases with the longest low-side time (third current =
  -(Ia + Ib)).
- 2 shunts: minimum for FOC. 3 shunts: better (pick the best two each cycle,
  detect faults).

### B. Inline (phase) shunts

Shunt in series with the motor wire (between switch node and motor). The 1 mΩ
"R001" parts on the DM board (box 5) sit right at the phase output pads
(silkscreen "U" next to them), so they are most likely inline shunts.

- Pros: **sees real motor current all the time** - easier sampling, works at any
  duty, best quality for FOC.
- Cons: the shunt's common-mode voltage swings 0 -> 24 V every PWM edge
  (huge dV/dt). Needs an amplifier with **high common-mode range and excellent
  PWM rejection**, e.g. **TI INA240** (designed exactly for this), INA241, or
  Allegro/TI isolated sensors.

### C. DC-bus (single) shunt

One shunt in the ground return of the whole bridge.

- Cheap, good for **overcurrent protection and power measurement**.
- Reconstructing three phase currents from it needs tricky timing; not
  recommended for precision FOC. Some boards add a bus shunt *in addition* to
  phase shunts for protection (the 3GIMD has 4 shunts - likely 3 phase + 1
  bus).

### D. Hall-effect / magnetic current sensors

ICs where the current flows through a copper lead-frame inside the package and
a Hall sensor measures the field (Allegro ACS7xx, TI TMCS1100/1123, Melexis
MLX91220).

- Pros: inherently isolated, no I²R concerns at the sensor, inline placement.
- Cons: more noise/offset drift than a good shunt, sensitive to external
  magnetic fields - **like the motor right next to it**. Less common in
  precision actuators.

---

## 3. The amplifier chain

```
 shunt ──RC──► [ CSA, gain G ] ──RC──► ADC input
                 ▲
             Vref = VDDA/2 (bias, so negative current is also measurable)
```

Bidirectional current: the motor current is positive and negative, so the
amplifier output is biased at mid-supply (1.65 V on a 3.3 V ADC).

Worked example for your motor (assume you want ±40 A full scale):

- Shunt 1 mΩ -> ±40 mV.
- ADC usable swing ~ 1.65 V ± 1.5 V -> needed gain ≈ 1.5 V / 40 mV ≈ 37 -> choose
  **G = 40** (gives ±37.5 A before clipping; headroom for overcurrent detection is
  better done by the driver's VDS monitor or a comparator).
- 12-bit ADC: 3.3 V / 4096 = 0.8 mV per count -> 0.8 mV / (40 × 1 mΩ) =
  **~20 mA per count**. Real ADC noise/ENOB will make it maybe 50-100 mA
  effective. That corresponds to ~4-8 mN·m at the rotor with Kt ≈ 0.08 -
  fine for most robotics.

> Demo: [interactive/05_current_shunt.html](interactive/05_current_shunt.html)
> - pick shunt, gain, ADC bits; see the full-scale current, resolution, power
> and voltage at the ADC.

Amplifier choices:

| Option | Notes |
|--------|-------|
| CSAs inside the gate driver (DRV8323RS/8353RS) | Programmable gain 5/10/20/40, offset calibration mode, auto bias. Easiest. |
| Dedicated CSA (INA181, INA186, INA240 for inline) | Precise, matched internal resistors, high CMRR. |
| General op-amp in differential configuration (RS724 on 3GIMD) | Cheap, but gain accuracy depends on resistor matching (use 0.1 % parts). |

Important specs: offset (and its drift), gain error, **settling time** after
the PWM edge (must settle before you sample), bandwidth (≥ 10× your current-loop
bandwidth, typically > 200 kHz), and output swing.

---

## 4. Filtering

- **Differential RC at the CSA input** (e.g. 10 Ω + 1 nF across the inputs, plus
  small caps to ground matched on both lines) removes MHz switching spikes.
  Keep the time constant much shorter than the sampling window.
- **RC at the ADC input** (e.g. 100 Ω + 1-2.2 nF): provides the charge the ADC's
  sample capacitor wants and filters noise. Check the ADC's required source
  impedance.
- **Do not over-filter**: a filter delays the signal; the current loop sees
  that delay as phase lag and becomes less stable.

---

## 5. Sampling: synchronize to PWM

The most important *firmware/hardware interaction* in the whole board:

```
 PWM counter (center-aligned):       /\      /\      /\
                                    /  \    /  \    /  \
 high-side ON:                ____|‾‾‾‾|____|‾‾‾‾|____
 low-side ON:                 ‾‾‾‾|____|‾‾‾‾|____|‾‾‾‾
                                 ^         ^
       sample here (counter = 0 / "valley"): all low-sides ON,
       far from any switching edge -> cleanest measurement
```

- Trigger ADC conversions from the PWM timer at the valley (or peak for
  inline sensing).
- Sample both (all) phases **at the same instant** (simultaneous sampling ADC,
  or very fast sequential sampling).
- This is a weak point of the ESP32-S3 - see module 10 for options
  (software-triggered sampling, or an external simultaneous-sampling SPI ADC).

---

## 6. Calibration

- **Offset**: at startup with all low-side FETs on (zero current) or gates
  disabled, average 1000 samples per channel -> subtract forever after.
  DRV83xx have a built-in "CAL" mode to short the amplifier inputs.
- **Gain**: use 0.1-0.5 % shunts and accurate CSA gain; optionally calibrate
  with a known current.
- **Temperature**: shunt and CSA drift; avoid placing shunts right against the
  hottest FET.

---

## 7. Also measure: bus voltage and (optionally) phase voltages

- **Vbus**: resistor divider (e.g. 100 kΩ / 6.8 kΩ for up to ~50 V into 3.3 V)
  + 100 nF filter cap -> ADC. Needed to scale PWM commands, detect
  over/under-voltage, control regen.
- **Phase voltages** (dividers on U, V, W): optional, used for sensorless
  observers, measuring motor parameters, detecting a disconnected phase. The
  DM and GIM-style boards often add them.

Next: [06 Position feedback / encoders](06_Position_Feedback_Encoders.md)
