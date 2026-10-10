# 10 - The ESP32-S3 as a motor-control MCU

Why you care: the MCU's peripherals decide how clean your PWM, current
sampling and encoder reads can be. The ESP32-S3 is very capable, but it was
not designed primarily as a motor-control chip, so it pays to know exactly
where its strengths and weak spots are - before you lay out the PCB.

---

## 1. What you get

| Feature | ESP32-S3 | Relevance |
|---------|----------|-----------|
| CPU | 2 × Xtensa LX7 @ 240 MHz, single-precision FPU | FOC math at 20 kHz is fine. Pin the control loop to one core, comms/Wi-Fi to the other. |
| **MCPWM** (motor-control PWM) | 2 units; each has 3 timers, 3 operators, 6 outputs, **hardware dead-time**, **fault inputs**, sync, capture | Exactly what a 3-phase inverter needs. One unit drives all 6 gates. |
| ADC | 2 × 12-bit SAR (ADC1: GPIO1-10, ADC2: GPIO11-20) | Usable but noisy/nonlinear; **ADC2 conflicts with Wi-Fi**. See §3. |
| SPI | SPI2, SPI3 (general purpose), DMA | Encoder, gate-driver config, external ADC. |
| PCNT | Hardware pulse counter, quadrature decode | ABZ encoder input. |
| TWAI | Classic CAN 2.0, up to 1 Mbit/s (no CAN-FD) | Robot bus with an external transceiver. |
| UART × 3 | With RS-485 half-duplex mode | RS-485, debug serial. |
| USB Serial/JTAG | Built in, on GPIO19/20 | Flash + serial console + JTAG over USB-C, no bridge chip. |
| USB OTG | Also on GPIO19/20 (shared) | Optional (TinyUSB); not needed for flashing. |
| Wi-Fi / BLE | Yes | Bench configuration/telemetry only (module 08 §6). |

---

## 2. MCPWM: the good part

- Configure a timer in **up-down (center-aligned) mode** at e.g. 20 kHz.
- Three operators (one per phase), each with a comparator setting the duty
  and two generators (high-side A / low-side B).
- **Dead-time module** inserts a delay between A and B edges in hardware ->
  firmware bugs can't easily cause shoot-through.
- **Fault module**: a GPIO (e.g. the gate driver's nFAULT, or an over-current
  comparator output) can force all outputs low **in hardware**, without
  waiting for software. Wire it!
- **Timer events** (counter = 0 or = peak) can fire an interrupt - this is where
  you trigger current sampling and run the FOC step.
- Alternative with smart drivers: the DRV8323 "3×PWM mode" takes only 3 PWM
  inputs (one per phase) and generates complementary signals + dead time
  internally. Saves pins, but you lose independent control of each FET.

---

## 3. ADC and current sampling: the weak spot (and how to live with it)

Honest list of limitations:

- **No direct hardware trigger** from MCPWM to the ADC (unlike STM32 timers
  -> ADC injected channels, which is why STM32G4 is the industry favourite for
  FOC; the STSPIN32G4 on the GIM board is one). On the S3 you start the
  conversion from software in the PWM-timer interrupt -> **some µs of jitter**.
- **One SAR per ADC unit**: two phases are converted one after the other, not
  simultaneously (a few µs apart). At 20 kHz with a motor time constant of
  ~1 ms this skew is usually acceptable, but it is a small error source.
- **Noise and nonlinearity**: expect ~9-10 effective bits; nonlinear near the
  ends of the range -> keep signals in the middle (bias 1.65 V, use the
  ~12 dB attenuation setting's linear region, use eFuse calibration).
- **ADC2 is unavailable while Wi-Fi is running** -> put all motor-control
  analog signals on **ADC1 (GPIO1-GPIO10)**.

Three ways to build the current sensing, from simplest to best:

| Option | How | Quality |
|--------|-----|---------|
| A. Internal ADC1, triggered in MCPWM ISR | Gate-driver CSAs (DRV8323RS) or INA181 -> RC -> ADC1 pins. This is what SimpleFOC does on ESP32. | OK for a first board. Jitter and ~10-bit performance. |
| B. A + careful averaging/oversampling | Several samples in the valley window, average | Somewhat better noise. |
| C. **External simultaneous-sampling SPI ADC** | E.g. a dual 12-16-bit simultaneous SAR ADC on SPI (AD7380-class, ADS8354-class). Start conversion with a **spare MCPWM output pin wired to the ADC's CONVST/CS** -> sampling instant is set by *hardware*, perfectly synced. Read the result over SPI in the ISR. | Best. Truly simultaneous, low noise, no jitter. Costs a chip + some layout. |

Practical recommendation for **rev A** of your board: option A **plus** a
footprint (or at least a plan) for option C, so you can learn and compare.
If later you find the ESP32-S3 limiting, a common architecture is a
**dual-MCU** board: a small STM32G4 does FOC, the ESP32-S3 does USB/CAN/
high-level logic (like the STMBL board splits work between two STM32s).

---

## 4. Pin planning (do this BEFORE schematic capture)

### Pins to avoid or treat specially

| GPIO | Why |
|------|-----|
| **GPIO0, GPIO3, GPIO45, GPIO46** | **Strapping pins** sampled at reset (boot mode, JTAG source, flash voltage, ROM log). Don't connect things that pull them the wrong way at boot. GPIO0 = BOOT button. |
| **GPIO26-GPIO32** | Connected to the internal/module SPI flash. Never use. |
| **GPIO33-GPIO37** | Used by **octal** flash/PSRAM on "R8"/"R16V"-type modules. Free on modules without octal PSRAM (check the module datasheet). |
| **GPIO19 / GPIO20** | USB D- / D+. Keep for USB-C. |
| **GPIO43 / GPIO44** | UART0 TX/RX (boot log, backup flashing). Bring to pads. |
| GPIO39-42 | Default JTAG pins if JTAG is routed to GPIO instead of USB; free when using USB JTAG. |
| ADC2 pins (GPIO11-20) | No ADC while Wi-Fi is on. Use them for digital stuff. |

### Example pin budget for your board

| Function | Pins | Notes |
|----------|------|-------|
| PWM to gate driver | 6 (or 3) | Any GPIO via matrix; group them; **external pull-downs** |
| Gate driver EN | 1 | Pull-down so gates are off at boot |
| Gate driver nFAULT | 1 | Also routed to MCPWM fault input |
| Gate driver SPI (config/status) | 4 (SCLK, MOSI, MISO, CS) | Can share SCLK/MOSI/MISO with encoder bus, separate CS |
| Phase currents | 2-3 ADC1 | GPIO1-10 |
| Vbus | 1 ADC1 | Divider |
| NTC FETs, NTC motor | 2 ADC1 | |
| Motor encoder SPI | 4 (or 1 extra CS if shared) | Dedicated SPI bus preferred for 20 kHz reads |
| 2nd (output) encoder | 2-4 | I²C or SPI CS on a connector |
| CAN (TWAI) TX, RX, + transceiver STB | 3 | |
| RS-485 TX, RX, DE (optional) | 3 | |
| USB D-/D+ | 2 | GPIO19/20 |
| UART0 TX/RX pads | 2 | GPIO43/44 |
| BOOT (GPIO0) | 1 | Button/pads |
| Status LED(s) | 1-2 | Or one WS2812 RGB on 1 pin |
| Optional: holding-brake output, ID switch, ABZ | 2-6 | |

Total ~35 pins -> fits the S3 (it has 45 GPIOs, fewer usable on modules).
Write this table in a spreadsheet and assign **actual GPIO numbers**, checking
each against the module datasheet before drawing a single wire.

---

## 5. Module or bare chip?

| Option | Size | Pros | Cons |
|--------|------|------|------|
| **ESP32-S3-MINI-1(U)** | 15.4 × 20.5 mm | Small, certified, flash inside, easy | Fewer pins exposed (check budget!) |
| **ESP32-S3-WROOM-1(U)** | 18 × 25.5 mm | Many pins, certified, easy | Bigger; check octal-PSRAM variants |
| Bare ESP32-S3 (QFN56, 7 × 7 mm) | Tiny | Smallest, full control | You add flash, 40 MHz crystal, RF matching; harder layout |

On a round ~80 mm board, a MINI-1 or WROOM-1 fits. "U" variants have an
external antenna connector instead of a PCB antenna - better in a metal
housing (or just don't use radio).

---

## 6. Power and reset details

- Supply 3.3 V with **≥ 500 mA** capability; 10 µF + 100 nF at the module.
- EN (CHIP_PU): 10 kΩ pull-up + 1 µF to GND (RC delay) + RESET button.
- Brownout detector: keep enabled - motor current spikes can sag the rails.
- **During reset and boot, GPIOs float or have weak pulls** -> every pin that
  controls a gate needs an **external pull-down** so the FETs stay off.

---

## 7. Software ecosystem to look at

- **ESP-IDF** MCPWM driver (has a BLDC/FOC example) - full control.
- **SimpleFOC** (Arduino/PlatformIO) - supports ESP32-S3 MCPWM, low-side
  current sensing, many encoders (AS5047, MT6835, MT6701...). Great to bring
  up a board quickly and learn.
- Study (even if on other MCUs): **moteus** (open-source actuator controller,
  STM32G4), **ODrive** v3 (DRV8301, STM32F4), **MIT Mini Cheetah motor
  controller** (DRV8323, STM32F4), **Ben Katz's** blog on the Cheetah
  controller - all excellent references for hardware decisions.

Next: [11 PCB layout and noise](11_PCB_Layout_and_Noise.md)
