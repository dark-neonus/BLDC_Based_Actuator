#!/usr/bin/env python3
"""
Draws numbered, colour-coded boxes over the reference PCB photos so the
learning notes can say "see box 7".  Re-run after editing coordinates:

    python3 PCB/Learning/tools/annotate_photos.py

Input photos are read from PCB/References (never modified).
Output goes to PCB/Learning/images/annotated_*.png
Coordinates are in ORIGINAL image pixels: (x1, y1, x2, y2).
"""
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

HERE = Path(__file__).resolve().parent
REF = HERE.parent.parent / "References"
OUT = HERE.parent / "images"
OUT.mkdir(exist_ok=True)
Hello, I want to create my own actuator based on bldc motor. For reference I will start with 8110 frameless motor 24V. I want to design my own controll board for it based on esp32-s3. For this, at first, I need to learn what does great robotic actuator control board have on it. Including controll mosfets, communication intarfaces, temperature sensors, magnetic encoder, power protecting units(zener diods, etc), back emf protection, maybe cooling, current sensing, test pads, led indicators, component place manegment, noise protection, etc. For this in PACB/Learning create me some files teaching all that stuff(including how does individual components behave, e.g. I might do not knwo specific of how mosfets behave at high frequencies, or something like that, or even dont knwo basics of how current measurement works). Additionally to text learning you can make some simple interactive tutorials/demonstration for some electrical behavior, motor behaviour, etc, but keep it simple stupid :)
Dont touch other folders for now(dont add anything o them). You can look at specification for framless motor I am planning to use at @CAD/References/WK8110-2D-Drawing.pdf and some opensource pcb design for something that looks like actuator controller for bldc motor at @PCB/References/IRAMX-drv-v3.3brd.pdf @PCB/References/IRAMX-drv-v3.3sch.pdf 
Also I was able to land some hands physically on soe sort of SteadyWin clones and I have photos of their PCBs in @PCB/References/ 
Ideally, after tutorials and before making my own I should fully understand what are on nthat pcb and why it there and what it does. You can copy those images and draw over them(highlight components) or use them in similar way to explain something. 

For context: I am interested in best way to controll motor with great precision, so FOC or PID, or otehr will be used and good feedback is needed, so maybe a few types of feedback will be used simultaniously.  Additionally, I want ability to flash my esp32 from type-c(along with outputtting to serial throught that usb) and that type-c port should be on controller.


# One colour per functional group -> same colour means same job on every photo.
C = {
    "power":   (255, 70, 70),    # power input, protection, bulk caps
    "bridge":  (255, 160, 0),    # MOSFETs / power stage / gate drive
    "sense":   (0, 200, 255),    # current sense, voltage sense, temperature
    "logic":   (80, 255, 80),    # MCU, crystal, regulators for logic
    "comms":   (220, 90, 255),   # CAN / RS485 / UART / USB
    "fb":      (255, 255, 0),    # encoders / position feedback
    "debug":   (255, 255, 255),  # test pads, programming, LEDs, switches
    "mech":    (150, 150, 150),  # mechanical / thermal features
}

PHOTOS = {
    "SteadyWin_Clone_Photo_1.jpg": [
        (1, "comms",  (365, 92, 548, 175)),    # CAN / A-B connectors top
        (1, "comms",  (398, 1128, 585, 1198)), # CAN connectors bottom (daisy chain)
        (2, "power",  (625, 92, 778, 300)),    # XT30 in
        (2, "power",  (652, 1025, 805, 1200)), # XT30 out (daisy chain)
        (3, "power",  (415, 125, 630, 380)),   # DC-link MLCC bank
        (4, "bridge", (585, 375, 878, 915)),   # 6 power MOSFETs
        (5, "sense",  (874, 500, 925, 958)),   # R001 shunts on phases
        (6, "bridge", (355, 605, 442, 692)),   # gate driver (rotated QFN)
        (7, "logic",  (234, 692, 348, 797)),   # MCU (sticker)
        (8, "logic",  (200, 778, 265, 838)),   # crystal
        (9, "comms",  (205, 862, 292, 965)),   # SOIC-8 transceiver
        (10, "debug", (158, 583, 262, 708)),   # DIP switch
        (11, "logic", (170, 305, 405, 460)),   # buck / LDO supply area
        (12, "debug", (128, 722, 160, 800)),   # programming pads
        (13, "sense", (280, 1005, 395, 1060)), # NTC lead
        (14, "mech",  (0, 450, 105, 870)),     # gearbox ring gear
    ],
    "SteadyWin_Clone_Photo_2.png": [
        (1, "fb",     (485, 895, 565, 980)),   # magnetic encoder IC
        (2, "fb",     (330, 728, 748, 1205)),  # magnet keep-out circle
        (3, "power",  (175, 530, 525, 1035)),  # tinned phase/power bus bars
        (4, "mech",   (365, 795, 535, 1030)),  # exposed thermal pad w/ vias
        (5, "power",  (535, 575, 705, 695)),   # arc exposed copper
        (6, "power",  (640, 535, 940, 790)),   # bus input pads
        (7, "power",  (785, 715, 865, 845)),   # GND / VCC through-holes
        (8, "mech",   (720, 850, 1010, 1110)), # via stitching field
        (9, "mech",   (555, 505, 655, 595)),   # mounting hole w/ exposed ring
        (9, "mech",   (160, 1055, 245, 1135)),
        (9, "mech",   (795, 1225, 895, 1315)),
        (10, "comms", (975, 625, 1065, 905)),  # side connector
    ],
    "SteadyWin_Clone_Photo_3.png": [
        (1, "logic",  (400, 435, 605, 675)),   # MCU + crystal
        (2, "comms",  (628, 485, 725, 695)),   # CAN + RS485 transceivers
        (3, "comms",  (765, 525, 835, 665)),   # 120R termination jumpers
        (4, "comms",  (895, 465, 1045, 625)),  # comm connector
        (5, "power",  (925, 635, 1155, 835)),  # 15-60 V input
        (6, "power",  (810, 675, 915, 805)),   # TVS diode
        (7, "power",  (885, 835, 1115, 1015)), # DC link MLCC bank
        (8, "bridge", (300, 1105, 945, 1325)), # 6 MOSFETs
        (9, "sense",  (445, 1025, 515, 1155)), # shunts
        (9, "sense",  (645, 1025, 715, 1155)),
        (9, "sense",  (810, 855, 875, 975)),
        (9, "sense",  (870, 985, 940, 1095)),
        (10, "bridge",(622, 765, 738, 865)),   # gate driver TSSOP
        (11, "sense", (460, 730, 555, 835)),   # quad op-amp (CSA)
        (12, "logic", (170, 635, 425, 905)),   # buck / LDO area
        (13, "sense", (140, 835, 195, 925)),   # NTC pads
        (14, "fb",    (125, 955, 215, 1065)),  # small connector
        (15, "debug", (465, 682, 535, 712)),   # SWD pads
        (16, "bridge",(320, 1045, 935, 1105)), # gate resistors / small parts
        (17, "power", (835, 420, 905, 475)),   # brake pads
        (18, "power", (875, 1110, 945, 1205)), # exposed copper strips
        (19, "bridge",(295, 1230, 810, 1310)), # phase wire pads
        (20, "power", (245, 985, 330, 1085)),  # SMB diode
    ],
    "GIM_8115-9_Photo.jpeg": [
        (1, "logic",  (935, 705, 1302, 1075)), # STSPIN32G4
        (2, "logic",  (1335, 855, 1435, 935)), # 24 MHz crystal
        (3, "comms",  (1535, 745, 1700, 960)), # SOIC-8 transceiver
        (4, "logic",  (1450, 518, 1615, 670)), # L2 inductor
        (5, "logic",  (1418, 1045, 1700, 1265)),# L1 + D1 buck
        (6, "power",  (370, 1135, 1230, 1405)),# MLCC bulk row
        (7, "power",  (720, 1440, 1185, 2215)),# XT30
        (8, "comms",  (485, 1545, 720, 1770)), # J2 UART
        (9, "comms",  (1200, 1545, 1415, 1770)),# J1 CAN/485
        (10, "debug", (585, 205, 820, 440)),   # J5 SWD
        (11, "fb",    (1018, 212, 1345, 490)), # J4 2nd encoder I2C
        (12, "sense", (205, 550, 300, 695)),   # NTC pads
        (13, "bridge",(190, 715, 670, 1105)),  # phase pads / power stage
        (14, "bridge",(708, 495, 925, 1115)),  # gate R + diodes
        (15, "sense", (928, 550, 1315, 692)),  # small-signal passives
        (16, "power", (195, 1015, 370, 1340)), # big caps C16/C8
        (17, "debug", (1335, 528, 1448, 670)), # LED D6 + RST
        (18, "debug", (845, 1083, 905, 1137)), # TP3
    ],
    # PDF board view of the open-source STMBL IRAMX driver (rendered at 200 dpi)
    "IRAMX-drv-v3.3brd.pdf": [
        (1, "power",  (638, 47, 1006, 246)),    # 24 V + brake/fan terminals
        (2, "bridge", (1346, 47, 1802, 246)),   # HV+ and U V W terminals
        (3, "logic",  (579, 410, 954, 491)),    # 78xx linear regulators
        (4, "comms",  (316, 456, 421, 614)),    # USB
        (5, "comms",  (187, 632, 421, 1184)),   # 2x RJ45 (CMD / FB)
        (6, "comms",  (532, 649, 679, 983)),    # RS485 + line receivers
        (7, "logic",  (720, 655, 924, 901)),    # STM32F405 (servo / FOC)
        (8, "fb",     (386, 995, 655, 1299)),   # resolver / sin-cos op-amps
        (9, "mech",   (1000, 135, 1053, 1351)), # isolation gap LV | HV
        (10, "power", (1053, 579, 1199, 684)),  # isolated DC-DC
        (11, "comms", (1067, 796, 1182, 948)),  # digital isolator
        (12, "logic", (1433, 936, 1609, 1176)), # STM32F103 (HV side)
        (13, "bridge",(1773, 281, 1890, 1030)), # IRAM power module pins
        (14, "power", (1205, 287, 1784, 866)),  # bulk electrolytic cap
        (15, "sense", (1039, 146, 1287, 562)),  # HV resistors / sense
        (16, "debug", (328, 293, 410, 445)),    # LEDs LV
        (16, "debug", (1240, 1258, 1457, 1334)),# LEDs HV
        (17, "debug", (1164, 913, 1334, 971)),  # SWD header HV side
    ],
}


def load(name):
    """Photos are opened directly; PDFs are rendered to PNG with pdftoppm."""
    src = REF / name
    if src.suffix.lower() != ".pdf":
        return Image.open(src).convert("RGB")
    import subprocess, tempfile
    with tempfile.TemporaryDirectory() as td:
        subprocess.run(["pdftoppm", "-r", "200", "-png", "-singlefile",
                        str(src), str(Path(td) / "page")], check=True)
        return Image.open(Path(td) / "page.png").convert("RGB")


def font(size):
    for p in ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
              "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"):
        try:
            return ImageFont.truetype(p, size)
        except OSError:
            pass
    return ImageFont.load_default()


def annotate(name, boxes):
    img = load(name)
    w, h = img.size
    s = max(w, h) / 1600            # scale line widths with image size
    lw = max(3, int(4 * s))
    f = font(int(26 * s))
    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)
    for _, grp, box in boxes:
        od.rectangle(box, fill=C[grp] + (45,))
    img = Image.alpha_composite(img.convert("RGBA"), overlay)
    d = ImageDraw.Draw(img)
    for num, grp, (x1, y1, x2, y2) in boxes:
        d.rectangle((x1, y1, x2, y2), outline=C[grp], width=lw)
        r = int(20 * s)
        cx, cy = max(x1, r + 2), max(y1, r + 2)
        d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(0, 0, 0), outline=C[grp], width=lw)
        t = str(num)
        tw, th = d.textbbox((0, 0), t, font=f)[2:]
        d.text((cx - tw / 2, cy - th / 2 - 2 * s), t, fill=C[grp], font=f)
    # colour legend strip at the bottom
    lf = font(int(20 * s))
    pad = int(10 * s)
    strip_h = int(44 * s)
    canvas = Image.new("RGB", (w, h + strip_h), (20, 20, 20))
    canvas.paste(img.convert("RGB"), (0, 0))
    d = ImageDraw.Draw(canvas)
    x = pad
    used = []
    for _, g, _ in boxes:
        if g not in used:
            used.append(g)
    for g in used:
        d.rectangle((x, h + pad, x + int(24 * s), h + strip_h - pad), fill=C[g])
        x += int(30 * s)
        d.text((x, h + pad), g, fill=(230, 230, 230), font=lf)
        x += d.textbbox((0, 0), g, font=lf)[2] + int(22 * s)
    out = OUT / ("annotated_" + Path(name).stem + ".png")
    canvas.save(out, optimize=True)
    print("wrote", out)


if __name__ == "__main__":
    for n, b in PHOTOS.items():
        annotate(n, b)
