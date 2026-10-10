# 09 - Temperature sensing and cooling

Why you care: actuators are sealed, compact and often hold a load (high
current at zero speed) for a long time. Heat is the real limit on continuous
torque. You must **get heat out** and **know the temperature** to derate
before something dies.

---

## 1. Where heat comes from

| Source | Approx loss at 20 A phase current | Note |
|--------|-----------------------------------|------|
| MOSFET conduction | I² × Rds(on,hot) ≈ 400 × 3 mΩ = 1.2 W per conducting FET | Dominant at low speed / holding |
| MOSFET switching | ~0.2-0.5 W per FET at 20 kHz | Grows with f_PWM and bus voltage |
| Shunts | I²R: 0.4-0.8 W each | Also heat the board locally |
| Copper traces | Can be **watts** if traces are thin (module 01) | Use planes, multiple layers |
| Motor windings | 3 × I_rms² × R_phase (e.g. 3 × 14² × 0.1 Ω ≈ 60 W!) | **Usually by far the biggest**; heats the stator and nearby PCB |
| Gate driver, buck, MCU | 0.3-1 W total | |

Total for the board: a few watts continuously, more at peaks. A small PCB
in free air can only dump ~1-2 W without getting very hot -> you **need a
conduction path to the metal housing**.

---

## 2. Thermal resistance: the "Ohm's law" of heat

ΔT = P × Rθ (temperature rise = power × thermal resistance, °C/W). Resistances
add in series:

```
 FET junction ─RθJC─► case/pad ─R_pcb─► PCB copper ─R_tim─► thermal pad ─R_housing─► air/robot
     0.8 °C/W          ~5-20 °C/W (vias!)     ~1-5 °C/W (thermal interface)
```

Example: 1.5 W in one FET, total 15 °C/W -> 22 °C above housing temperature.
Housing at 60 °C -> FET at ~82 °C. Fine. With bad vias (40 °C/W) -> 120 °C+.

---

## 3. Getting heat out of a PCB

- **Thermal vias**: arrays of vias (0.3 mm drill, ~0.6-1 mm pitch) under each
  FET's drain pad connect it to inner/bottom copper. One via ~ 100-200 °C/W;
  20 vias in parallel ~ 5-10 °C/W. Vias in pads should be **filled/tented or
  plugged** (or at least small) so solder doesn't wick away during assembly -
  ask your PCB fab for "via-in-pad, filled and capped" if needed.
- **Thick copper**: 2 oz (70 µm) outer layers spread heat and reduce I²R.
- **Big copper areas** on all layers connected to the FET tabs.
- **Exposed copper on the bottom** pressed against the housing through a
  thermal gap pad or thermal paste - **exactly what the DM board does** (photo
  2, box 4: exposed rectangle with a dense via array). Note: the drain tab is
  electrically live (switch node / +Vbus) -> the thermal pad must be
  **electrically insulating** (silicone gap pad), or the exposed area must be a
  copper zone tied to GND only.
- Mounting screws into the housing also conduct heat (box 9 on photo 2:
  plated mounting holes with exposed rings).
- **Potting/conformal coat**: helps against moisture/dust, not much for heat
  unless it is a thermal potting compound.

---

## 4. Temperature sensors

### NTC thermistor - the standard

A resistor whose value drops as temperature rises (10 kΩ at 25 °C, "B-value"
3380-3950 typical).

```
 3.3 V ──[ R_fixed 10 kΩ ]──┬──► ADC (with 100 nF to GND)
                            │
                         [ NTC 10k ]
                            │
                           GND
```

- Convert with the Beta equation: 1/T = 1/T0 + (1/B) × ln(R/R0) (T in Kelvin),
  or a lookup table.
- Pick R_fixed ≈ NTC resistance in the temperature range you care about most
  (e.g. 10 k at 25 °C, or a lower value for better resolution at 80-120 °C).
- **Where**:
  1. **On the PCB next to the MOSFETs** (0402/0603 NTC on the same copper
     as the FETs) - board temperature.
  2. **In the motor winding** - an NTC glued into the stator coils, wired to
     the board. The red/white thin wires labelled "NTC" on the GIM (box 12),
     DM (box 13) and 3GIMD (box 13) boards are exactly this. The winding is
     often the hottest point and copper insulation (class F/H) has a hard
     limit (~155-180 °C, derate well before).
- The NTC line comes from a cable near motor wires -> add an RC filter and
  maybe ESD protection at the ADC pin.

### Alternatives

- Digital sensors (TMP117, TMP1075, LM75) over I²C: accurate, no calibration,
  slower, needs bus pins.
- Gate drivers report their own die over-temperature.
- The ESP32-S3 has an internal temperature sensor (chip temperature only - not
  useful for the power stage).

### What firmware does with it

- **Derating**: linearly reduce allowed current from e.g. 80 °C to 100 °C (FETs)
  or 100 °C to 120 °C (winding).
- **Trip**: disable above the max.
- **Kt compensation**: magnet strength drops ~0.1 %/°C (NdFeB) -> torque per
  amp drops when hot. Precise torque control can compensate using motor
  temperature.
- **Thermal model**: estimate winding temperature from I² × R over time when
  no sensor is fitted.

---

## 5. Active cooling?

Fans are rare in sealed actuators (dust, noise, size). The usual approach is
**passive conduction into the actuator housing**, which is attached to the
robot structure (a big heatsink). The STMBL board has a fan output (Q1) - it
targets bigger industrial servos. For your actuator: design the conduction
path first; a fan is a last resort.

Next: [10 ESP32-S3 for motor control](10_ESP32_S3_for_Motor_Control.md)
