# 01 - Electronics fundamentals you need for power electronics

Why you care: at DC, a wire is a wire and a capacitor is an open circuit. At
20 kHz PWM with edges switching in 20-50 ns, **every wire is an inductor, every
pair of conductors is a capacitor, and every capacitor is also an inductor**.
Almost every "mysterious" motor-controller problem (ringing, resets, noisy
current readings, dead MOSFETs) comes from these parasitics.

---

## 1. The three passive components, honestly

### Resistor: V = I × R

- Power dissipated: **P = I² × R**. A 1 mΩ shunt carrying 30 A burns
  30² × 0.001 = 0.9 W. That is why shunts are big 2512 packages (see "R001",
  "R002" on the clone boards).
- Resistors have a **power rating** and a **voltage rating**. High-voltage
  boards (like the STMBL) use large resistors or several in series for voltage
  dividers, not for power, but so the voltage across each part stays below its
  rating.
- Tolerance (1 %, 0.1 %) and **temperature coefficient** (ppm/°C) matter for
  measurement resistors: a shunt that changes value as it heats gives you a
  wrong torque.

### Capacitor: stores charge, resists *change* of voltage

- I = C × dV/dt. To change the voltage across a capacitor quickly, you need
  big current. That is exactly why we put caps next to switching parts: when a
  MOSFET suddenly demands 30 A, the cap supplies it **locally** instead of the
  long, inductive wire from the battery.
- **Impedance** Xc = 1 / (2π f C) - a capacitor "looks like" a smaller
  resistor at higher frequency. 10 µF at 20 kHz ≈ 0.8 Ω; at 1 MHz ≈ 0.016 Ω.
- **Real capacitors have ESR and ESL**:
  - ESR (equivalent series resistance) -> heat when ripple current flows.
    Electrolytics: tens of mΩ to ohms. Ceramics (MLCC): a few mΩ.
  - ESL (equivalent series inductance) -> above the *self-resonant frequency*
    the capacitor stops being a capacitor and becomes an inductor. Small
    packages (0402/0603) have lower ESL, which is why **100 nF 0402 caps sit
    directly at each IC power pin**, and big caps sit further away.
- **MLCC DC-bias derating** (very important, very often forgotten): a ceramic
  capacitor with X5R/X7R dielectric **loses capacitance when DC voltage is
  applied**. A "10 µF 50 V 1206" capacitor at 24 V may only be 3-4 µF. Always
  check the manufacturer's DC-bias curve. This is why the clone boards have
  *rows* of large MLCCs (see 3GIMD box 7, GIM box 6) rather than one.
- Electrolytic vs ceramic for the DC bus: electrolytics give lots of µF
  cheaply but have high ESR and are tall; ceramics give low ESR/ESL but little
  capacitance. Robotic actuators (flat, inside a housing) mostly use **many
  MLCCs**, sometimes plus a polymer/electrolytic or two.

### Inductor: stores energy in a magnetic field, resists *change* of current

- V = L × dI/dt. Try to change current quickly through an inductance and it
  creates a voltage spike. **Your motor winding is an inductor** - that is good
  (it smooths PWM into current, see demo 01). **Your PCB traces are inductors**
  - that is bad (they create spikes when MOSFETs switch).
- Rule of thumb: ~1 nH per mm of trace (more for thin traces, less over a solid
  ground plane). 20 mm of trace = ~20 nH. At a current change of 30 A in 20 ns:
  V = 20 nH × 30 A / 20 ns = **30 V spike**. On a 24 V bus. That kills
  MOSFETs. This single calculation is the reason power-stage layout matters so
  much (module 11).
- Inductors also appear as discrete parts in **buck converters** ("150", "470"
  markings on the GIM board = 15 µH, 47 µH) and as **ferrite beads** for
  filtering.
- Saturation: put too much current through an inductor and its core
  saturates; inductance collapses and current shoots up. Buck inductors are
  chosen with a saturation current above the peak.

> Demo: [interactive/01_pwm_rl_current.html](interactive/01_pwm_rl_current.html)
> shows a motor winding (R + L) being driven by PWM. Change frequency and see
> the current ripple shrink.

---

## 2. Parasitics: the components you did not place

| Parasitic | Where it lives | What it does |
|-----------|----------------|--------------|
| Loop inductance | Every current loop: cap -> high-side FET -> low-side FET -> back to cap | Voltage spikes, ringing at switching edges |
| Common source inductance | Shared path between gate-drive return and power current | Slows switching, causes false turn-on |
| Trace-to-trace capacitance | Neighbouring traces, especially the switch node next to a sensitive trace | Couples switching noise (dV/dt) into signals |
| MOSFET capacitances (Cgs, Cgd, Cds) | Inside the MOSFET | Define switching speed, Miller effect (module 03) |
| Capacitor ESL | Inside every capacitor | Limits how fast it can deliver current |

Two "noise injection" mechanisms to memorise:

- **Magnetic (inductive) coupling**: a loop with fast changing *current*
  (dI/dt) induces voltage in any other loop nearby. Fix: make high-current
  loops **small** and keep sensitive loops small and away.
- **Electric (capacitive) coupling**: a node with fast changing *voltage*
  (dV/dt, e.g. the motor phase/switch node swinging 0 -> 24 V in 20 ns) injects
  current I = C × dV/dt into anything near it. Fix: keep switch-node copper
  small and away from signal traces; put ground between them.

---

## 3. Ground is not one point

"Ground" on a schematic is one symbol, but on the PCB it is copper with
resistance and inductance. If 30 A flows through a ground copper with 1 mΩ
resistance, there is 30 mV between its two ends. If your current-sense
amplifier references "ground" at one end and the ADC at the other, you
measure 30 mV of garbage (= amps of fake current with a small shunt!).

Rules that follow:

1. Use a **solid ground plane** (one entire layer of copper) under everything.
   Return current at high frequency flows directly *under* its signal trace -
   a solid plane gives it a short, low-inductance path.
2. Keep **high current return paths** from flowing under the sensitive analog
   circuitry. Place things so power current naturally stays in the power
   corner.
3. **Kelvin (4-wire) connections** for measurements: sense voltage at the
   exact pads of the shunt, with separate thin traces that carry no current
   (module 05).
4. Do not randomly split ground planes. Splits often make things worse. Use
   **placement** to separate, and one continuous plane.

---

## 4. Decoupling, explained once

Every IC draws current in short pulses (every clock edge). The supply trace
is inductive, so it cannot deliver those pulses quickly -> the supply voltage at
the IC pin dips -> logic errors, ADC noise, resets.

Solution: a small capacitor right at the pin acts as a local "bucket":

```
   3V3 plane ----+---- via ---- [100nF] ---- IC VDD pin
                 |                 |
                 |    (as short as possible loop)
   GND plane ----+---- via --------+-------- IC GND pin
```

- **100 nF per power pin**, within ~1-2 mm, plus a **bulk 1-10 µF** per IC or
  per small group.
- The loop formed by VDD pin -> cap -> GND pin must be tiny. Vias go
  straight down to the planes next to the cap pads.
- Same idea at a bigger scale for the power stage: MLCCs directly across each
  half-bridge (high-side drain to low-side source).

---

## 5. Diodes: one-way valves with personality

| Type | Use on a motor controller |
|------|---------------------------|
| Standard silicon (~0.7 V drop) | Rarely, slow |
| **Schottky** (~0.3-0.5 V, fast, leaks more when hot) | Buck converter freewheel (D1 on GIM), bootstrap diode, OR-ing USB power |
| **Zener** (conducts in reverse at a set voltage, low power) | Clamping a gate or signal to a safe voltage, simple references |
| **TVS** (Zener-like but built to absorb big energy spikes, kW for µs) | Clamping the DC bus against surges and regen spikes (3GIMD box 6) |
| ESD diode arrays (tiny TVS for signals) | USB data lines, CAN lines, external connector pins |
| MOSFET body diode | Exists inside every MOSFET, conducts during dead time (module 03) |
| LED | Status indicators |

Key TVS parameters: **standoff voltage** (below this it does nothing),
**breakdown voltage** (starts to conduct), **clamping voltage** (the voltage it
holds during a big surge - much higher than breakdown!). Module 07 goes deeper.

---

## 6. Op-amps in one page

An op-amp amplifies the *difference* between its + and - inputs enormously,
and with feedback resistors you get a precise gain:

- Non-inverting amplifier: Gain = 1 + Rf/Rg.
- Differential amplifier: amplifies (V+ - V-) and rejects voltage common to
  both - exactly what you want across a shunt.
- Important specs for current sensing: **offset voltage** (error at 0 A),
  **gain-bandwidth** and **slew rate** (how fast it follows), **settling
  time** after a PWM edge, **CMRR**, rail-to-rail input/output.

The "RS724" on the 3GIMD board (box 11) is a quad (4-in-one) op-amp used this
way. Dedicated current-sense amplifiers (INA240, INA181, the ones built into
DRV83xx gate drivers) package the op-amp + matched resistors together.

---

## 7. Units and quick numbers to have in your head

- 20 kHz PWM -> period 50 µs. Above human hearing, which is why it is the
  common choice (at 8 kHz motors whine).
- 1 oz copper = 35 µm thick. Rough 10 °C rise capacity for an outer-layer trace:
  ~1 A per 0.3 mm width at 1 oz (use a calculator, e.g. per IPC-2152).
- 1 mm wide, 1 oz trace: ~0.5 mΩ per mm of length (so 30 mm = 15 mΩ - at
  30 A that is 0.45 V lost and 13.5 W of heat!). Copper resistance matters.
- Via (0.3 mm drill, 1 oz plating) carries roughly 1-2 A continuous; use arrays.

Next: [02 BLDC motors and FOC](02_BLDC_Motor_and_FOC.md)
