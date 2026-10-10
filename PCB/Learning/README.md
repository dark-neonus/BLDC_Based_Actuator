# Learning: what goes on a good robotic actuator controller board

This folder is a self-study course. Its goal: by the end you can look at any
BLDC/FOC actuator controller PCB (the SteadyWin clones, the GIM8115, the STMBL
board in `../References`) and explain **what every block is, why it is there,
and what breaks if you leave it out**. Then you are ready to design your own
board: **ESP32-S3 + WK8110 frameless motor (24 V) + USB-C flashing/serial**.

## How to use it

Read the modules in order. Each one starts with "why you care", then the
physics in plain words, then the practical rules, then "what this looks like on
the reference boards". When a module mentions an interactive demo, open the
`.html` file from [interactive/](interactive/) in any browser (double-click it;
no internet or install needed).

| # | Module | What you learn |
|---|--------|----------------|
| 00 | [Big picture](00_Big_Picture.md) | Block diagram of an actuator controller, how energy and data flow |
| 01 | [Electronics fundamentals](01_Electronics_Fundamentals.md) | R, C, L at high frequency, ESR/ESL, decoupling, ground, parasitics |
| 02 | [BLDC motors and FOC](02_BLDC_Motor_and_FOC.md) | Back-EMF, Kv/Kt, pole pairs, six-step vs FOC, Clarke/Park, control loops |
| 03 | [MOSFETs and the half-bridge](03_MOSFETs_and_Half_Bridge.md) | How MOSFETs really switch, gate charge, Miller plateau, losses, dead time, ringing |
| 04 | [Gate drivers](04_Gate_Drivers.md) | Bootstrap, gate resistors, driver ICs, built-in protections |
| 05 | [Current sensing](05_Current_Sensing.md) | Shunts, amplifiers, Kelvin connections, PWM-synchronous sampling, ADCs |
| 06 | [Position feedback / encoders](06_Position_Feedback_Encoders.md) | Magnetic encoders, magnets, dual-encoder setups, accuracy vs resolution |
| 07 | [Power input and protection](07_Power_Input_and_Protection.md) | Reverse polarity, TVS/Zener, regen (back-EMF pumping), inrush, bulk caps, regulators |
| 08 | [Communication + USB-C](08_Communication_and_USB.md) | CAN, RS-485, UART, USB-C on the ESP32-S3, termination, ESD |
| 09 | [Temperature and cooling](09_Temperature_and_Cooling.md) | NTCs, thermal paths, thermal vias, heat-sinking into the housing |
| 10 | [ESP32-S3 as a motor controller](10_ESP32_S3_for_Motor_Control.md) | MCPWM, ADC limits, pin planning, strapping pins, boot/flash over USB |
| 11 | [PCB layout and noise](11_PCB_Layout_and_Noise.md) | Placement, current loops, ground planes, layer stack, copper sizing |
| 12 | [Test, debug, indicators](12_Test_Debug_Indicators.md) | Test pads, LEDs, bring-up procedure, safety while testing |
| 13 | [Reference boards explained](13_Reference_Boards_Explained.md) | Annotated photos: every highlighted component explained |
| 14 | [Your board: requirements + checklist](14_Your_Board_Checklist.md) | Turning all of this into a spec for the ESP32-S3 + WK8110 board |
| -- | [Glossary](Glossary.md) | Every abbreviation in one place |

## Interactive demos (open in a browser)

| Demo | Shows |
|------|-------|
| [interactive/01_pwm_rl_current.html](interactive/01_pwm_rl_current.html) | Why a motor winding turns PWM voltage into smooth-ish current; ripple vs frequency |
| [interactive/02_mosfet_switching.html](interactive/02_mosfet_switching.html) | Gate charge, Miller plateau, switching loss vs gate resistor, ringing |
| [interactive/03_dead_time.html](interactive/03_dead_time.html) | Half-bridge timing, shoot-through, dead time and the body diode |
| [interactive/04_foc_vectors.html](interactive/04_foc_vectors.html) | 3-phase currents -> rotating vector -> Clarke/Park -> d/q; why FOC works |
| [interactive/05_current_shunt.html](interactive/05_current_shunt.html) | Pick shunt + gain + ADC; see resolution, heat, and headroom |
| [interactive/06_regen_bus_pump.html](interactive/06_regen_bus_pump.html) | Braking a motor pumps the supply voltage up; what a clamp/TVS does |
| [interactive/07_cascade_pid.html](interactive/07_cascade_pid.html) | Position/velocity loop tuning with encoder resolution and noise |

## Images

[images/](images/) contains annotated copies of the reference photos (the
originals in `../References` are untouched). Box colours mean the same thing on
every photo:

- red **power** (input, protection, bulk caps)
- orange **bridge** (MOSFETs, gate drive)
- cyan **sense** (current, voltage, temperature)
- green **logic** (MCU, clock, logic supplies)
- purple **comms** (CAN, RS-485, UART, USB)
- yellow **fb** (encoders / position feedback)
- white **debug** (test pads, programming, LEDs, switches)
- grey **mech** (mounting, thermal, mechanical)

To regenerate or tweak the boxes: `python3 PCB/Learning/tools/annotate_photos.py`
(needs Python + Pillow, and `pdftoppm` for the STMBL board PDF).

## A word on certainty

Chip markings on the clone boards are partly unreadable or covered. When a note
says "likely", it means the identification is from package, placement and
surrounding parts, not a readable part number. Learn the *function*; the
exact part does not matter for understanding.
