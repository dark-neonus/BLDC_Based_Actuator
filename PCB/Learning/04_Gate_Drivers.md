# 04 - Gate drivers

Why you care: the gate driver is the translator between your 3.3 V MCU and
six MOSFETs that need amps of gate current at 10-12 V, one of them floating on
a 24 V switch node. A good driver also watches for faults faster than the MCU
ever could.

---

## 1. What a gate driver does

1. **Level shifts**: 3.3 V logic PWM in -> ~10-12 V gate drive out.
2. **Current boost**: sources/sinks 0.5-3 A peak to charge/discharge the gate
   capacitance quickly.
3. **High-side floating supply** via a bootstrap (section 2) or charge pump.
4. **Protection**: undervoltage lockout (UVLO), shoot-through prevention,
   minimum dead time, often over-current detection (VDS monitoring) and
   over-temperature, reporting via a nFAULT pin.
5. Sometimes **extras**: built-in current-sense amplifiers (CSA), buck/LDO
   regulators, SPI configuration.

---

## 2. Bootstrap: how the high side gets its gate voltage

```
   VDRV (12 V) ──►|──┬────────── BST pin (high-side driver supply)
          D_boot     │
                   [C_boot] 100 nF - 1 µF
                     │
   switch node ──────┴────────── SH pin (high-side driver "ground")
```

- When the **low-side** FET is on, the switch node is ~0 V. C_boot charges to
  ~12 V through the diode.
- When the high side turns on, the switch node rises to 24 V and "lifts"
  C_boot with it. BST is now at ~36 V, i.e. 12 V above the source of the
  high-side FET: exactly the gate voltage needed.
- The diode blocks the 36 V from flowing back into the 12 V rail.

Limitation: **the bootstrap cap must be recharged regularly**, which only
happens when the low side is on. So you **cannot run 100 % duty** forever;
FOC firmware limits max duty to ~95-98 %. Some drivers (DRV8353, DRV8323) use a
**charge pump** instead or in addition, which allows 100 % duty.

Sizing: C_boot ≥ ~10 × Qg_total / ΔV_allowed. For Qg = 50 nC and 1 V droop ->
≥ 0.5 µF; use a low-ESR ceramic, place it right at the driver pins.

---

## 3. Gate resistors (and that diode)

Each gate has a series resistor between driver and FET (a few Ω to ~20 Ω).

- Controls switching speed (dV/dt) -> trade between switching losses and
  ringing/EMI.
- Damps the LC loop formed by gate trace inductance and Cgs.
- Turn-on and turn-off can be tuned separately: **Rg_on** in series, plus
  a **diode + small Rg_off** in parallel so turn-off is fast and the gate is
  held strongly low (protects against dV/dt turn-on, module 03 §4). That's
  the D2-D7 + resistor column on the GIM board.
- A **pull-down resistor (10-100 kΩ) gate-to-source** keeps the FET off while
  the driver is unpowered (during power-up the gate must never float).

Modern "smart" drivers like the TI DRV83xx family use **programmable gate
current** (IDRIVE) instead of resistors: you set source/sink current by SPI or
a resistor on a pin. Fewer parts, tunable from firmware.

---

## 4. Driver families you will meet

| Driver | Type | Notes |
|--------|------|-------|
| **TI DRV8323R(S/H)** | 3-phase smart driver, 6-60 V | Built-in 3 CSAs, buck regulator (in DRV8323R), SPI config, VDS over-current protection. Very common in hobby FOC boards (moteus r4 era, many ODrive-like). |
| **TI DRV8353 / DRV8350** | 3-phase smart driver, up to 100 V | Similar, higher voltage; S variant has 3 CSAs. |
| **TI DRV8301/8302** | Older 3-phase driver with buck + 2 CSAs | ODrive v3 used DRV8301. |
| Fortior **FD6288T**, **EG2133/EG3112** | Simple 3-phase bootstrap drivers | Very cheap, common on Chinese boards; no protection features, no CSA. The TSSOP on the 3GIMD (box 10) is likely in this class. |
| **STSPIN32G4** | STM32G431 MCU + 3-phase gate driver + buck + LDOs **in one package** | Used on the GIM8115 board (box 1). Very compact. |
| Infineon **6EDL7141** | 3-phase smart driver | Programmable, CSAs, charge pump. |
| Discrete half-bridge drivers (IR2101, UCC27211, ...) | 1 per phase | Flexible, more parts. |

For an ESP32-S3 design, a **DRV8323RS / DRV8353RS-class** driver is an
excellent learning choice: it gives you current-sense amplifiers, protection,
and SPI fault reporting, and is extremely well documented (and widely used in
open-source FOC projects). Read its datasheet once fully - it is a free
textbook on everything in modules 03-05.

---

## 5. Protection features (and why each exists)

| Feature | Protects against |
|---------|------------------|
| **UVLO** on VCC/VDRV and bootstrap | Driving gates with too little voltage -> FET half-on -> burns |
| **Shoot-through lockout / minimum dead time** | Firmware bug commanding both FETs on |
| **VDS over-current monitor** | Short circuit: the driver measures the voltage across each ON FET; if Rds(on) × I exceeds a threshold, it shuts off within µs. Much faster than an MCU ADC loop. |
| **Over-temperature** of the driver die | Driver self-heating |
| **nFAULT pin** | Tells the MCU something happened (route it to an interrupt-capable GPIO and also to the MCPWM fault input so PWM stops in hardware!) |
| **ENABLE pin** | MCU can kill all gates. Pull-down by default so the board starts safe. |

Design rule: **the default state of every gate-related line at power-up and
during MCU reset must be "all FETs off"**. Pull-downs on EN and PWM inputs.

---

## 6. Gate-driver layout rules (preview of module 11)

- Driver within ~10-15 mm of its FETs.
- Gate trace and its return (source / SH trace) routed **as a pair**, close
  together -> small loop, low inductance.
- High-side return (SHx) connected **directly at the high-side FET source**,
  low-side return at the low-side FET source (Kelvin source if the FET has a
  dedicated pin).
- Bootstrap and VCP/VDRV caps right at the driver pins.
- Keep the switch-node copper away from the driver's analog pins (CSA inputs).

Next: [05 Current sensing](05_Current_Sensing.md)
