"""ISO standards references for tolerance calculations.

This module provides lookup tables and calculation engines for:
- ISO 286-1 & ISO 286-2: Geometrical Product Specifications (GPS) - ISO code system for tolerances on linear sizes (fits)
  Extended to all standard ranges from 0 mm up to 3 150 mm (21 dimensional steps).
- ISO 2768-1: General tolerances for linear, angular and broken-edge dimensions without individual tolerance indications
"""

import bisect
from dataclasses import dataclass
from typing import Literal
import re


# ISO 286-1 Size ranges (low, high] in mm from 0 up to 3 150 mm (21 normalized steps)
ISO_286_STEPS = [
    (0.0, 3.0),
    (3.0, 6.0),
    (6.0, 10.0),
    (10.0, 18.0),
    (18.0, 30.0),
    (30.0, 50.0),
    (50.0, 80.0),
    (80.0, 120.0),
    (120.0, 180.0),
    (180.0, 250.0),
    (250.0, 315.0),
    (315.0, 400.0),
    (400.0, 500.0),
    (500.0, 630.0),
    (630.0, 800.0),
    (800.0, 1000.0),
    (1000.0, 1250.0),
    (1250.0, 1600.0),
    (1600.0, 2000.0),
    (2000.0, 2500.0),
    (2500.0, 3150.0),
]

# Precomputed tuple of upper bounds for O(log N) bisection lookup via bisect.bisect_left
ISO_286_HIGH_BOUNDS = tuple(high for _, high in ISO_286_STEPS)

# Pre-compiled regex patterns to avoid recompiling on each fit string parsing call
_HOLE_PATTERN = re.compile(r"^[A-Z]+[0-9]+$")
_SHAFT_PATTERN = re.compile(r"^[a-z]+[0-9]+$")

# Standard tolerance values (IT5 to IT16) in micrometers (µm) across the 21 steps
_IT_UM: dict[str, list[float]] = {
    "IT5": [4, 5, 6, 8, 9, 11, 13, 15, 18, 20, 23, 25, 27, 32, 36, 40, 47, 55, 65, 78, 96],
    "IT6": [6, 8, 9, 11, 13, 16, 19, 22, 25, 29, 32, 36, 40, 44, 50, 56, 66, 78, 92, 110, 135],
    "IT7": [10, 12, 15, 18, 21, 25, 30, 35, 40, 46, 52, 57, 63, 70, 80, 90, 105, 125, 150, 175, 210],
    "IT8": [14, 18, 22, 27, 33, 39, 46, 54, 63, 72, 81, 89, 97, 110, 125, 140, 165, 195, 230, 280, 330],
    "IT9": [25, 30, 36, 43, 52, 62, 74, 87, 100, 115, 130, 140, 155, 175, 200, 230, 260, 310, 370, 440, 540],
    "IT10": [40, 48, 58, 70, 84, 100, 120, 140, 160, 185, 210, 230, 250, 280, 320, 360, 420, 500, 600, 700, 860],
    "IT11": [60, 75, 90, 110, 130, 160, 190, 220, 250, 290, 320, 360, 400, 440, 500, 560, 660, 780, 920, 1100, 1350],
    "IT12": [100, 120, 150, 180, 210, 250, 300, 350, 400, 460, 520, 570, 630, 700, 800, 900, 1050, 1250, 1500, 1750, 2100],
    "IT13": [140, 180, 220, 270, 330, 390, 460, 540, 630, 720, 810, 890, 970, 1100, 1250, 1400, 1650, 1950, 2300, 2800, 3300],
    "IT14": [250, 300, 360, 430, 520, 620, 740, 870, 1000, 1150, 1300, 1400, 1550, 1750, 2000, 2300, 2600, 3100, 3700, 4400, 5400],
}


def _make_h_hole(it_grade: str) -> list[tuple[float, float]]:
    """Build (EI, ES) for H hole: EI=0, ES=+IT."""
    return [(0.0, float(val)) for val in _IT_UM[it_grade]]


def _make_js_sym(it_grade: str) -> list[tuple[float, float]]:
    """Build (EI, ES) for JS hole or js shaft: EI=-IT/2, ES=+IT/2."""
    return [(-val / 2.0, val / 2.0) for val in _IT_UM[it_grade]]


def _make_h_shaft(it_grade: str) -> list[tuple[float, float]]:
    """Build (ei, es) for h shaft: ei=-IT, es=0."""
    return [(-float(val), 0.0) for val in _IT_UM[it_grade]]


# ISO 286 hole limits (EI, ES) in micrometers (µm) for each of the 21 steps
ISO_286_HOLES_UM: dict[str, list[tuple[float, float]]] = {
    # Standard H holes (basis hole system)
    "H6": _make_h_hole("IT6"),
    "H7": _make_h_hole("IT7"),
    "H8": _make_h_hole("IT8"),
    "H9": _make_h_hole("IT9"),
    "H10": _make_h_hole("IT10"),
    "H11": _make_h_hole("IT11"),
    "H12": _make_h_hole("IT12"),
    "H13": _make_h_hole("IT13"),
    "H14": _make_h_hole("IT14"),
    # Symmetrical JS holes (including JS13 requested in Issue #11)
    "JS6": _make_js_sym("IT6"),
    "JS7": _make_js_sym("IT7"),
    "JS8": _make_js_sym("IT8"),
    "JS9": _make_js_sym("IT9"),
    "JS11": _make_js_sym("IT11"),
    "JS13": _make_js_sym("IT13"),
    "JS14": _make_js_sym("IT14"),
    # Clearance holes
    "F8": [
        (6, 20), (10, 28), (13, 35), (16, 43), (20, 53), (25, 64),
        (30, 76), (36, 90), (43, 106), (50, 122), (56, 137), (62, 151), (68, 165),
        (76, 186), (86, 211), (98, 238), (110, 275), (130, 325), (150, 380), (180, 460), (210, 540),
    ],
    "F7": [
        (6, 16), (10, 22), (13, 28), (16, 34), (20, 41), (25, 50),
        (30, 60), (36, 71), (43, 83), (50, 96), (56, 108), (62, 119), (68, 131),
        (76, 146), (86, 166), (98, 188), (110, 215), (130, 255), (150, 300), (180, 355), (210, 420),
    ],
    "E8": [
        (14, 28), (20, 38), (25, 47), (32, 59), (40, 73), (50, 89),
        (60, 106), (72, 126), (85, 148), (100, 172), (110, 191), (125, 214), (145, 242),
        (170, 280), (195, 320), (220, 360), (250, 415), (290, 485), (340, 570), (400, 680), (480, 810),
    ],
    "E9": [
        (14, 39), (20, 50), (25, 61), (32, 75), (40, 92), (50, 112),
        (60, 134), (72, 159), (85, 185), (100, 215), (110, 240), (125, 265), (145, 300),
        (170, 345), (195, 395), (220, 450), (250, 510), (290, 600), (340, 710), (400, 840), (480, 1020),
    ],
    "D9": [
        (20, 45), (30, 60), (40, 76), (50, 93), (65, 117), (80, 142),
        (100, 174), (120, 207), (145, 245), (170, 285), (190, 320), (210, 350), (230, 385),
        (260, 435), (290, 490), (330, 560), (380, 640), (440, 750), (520, 890), (600, 1040), (700, 1240),
    ],
    "D10": [
        (20, 60), (30, 78), (40, 98), (50, 120), (65, 149), (80, 180),
        (100, 220), (120, 260), (145, 305), (170, 355), (190, 400), (210, 440), (230, 480),
        (260, 540), (290, 610), (330, 690), (380, 800), (440, 940), (520, 1120), (600, 1300), (700, 1560),
    ],
    "G7": [
        (2, 12), (4, 16), (5, 20), (6, 24), (7, 28), (9, 34),
        (10, 40), (12, 47), (14, 54), (15, 61), (17, 69), (18, 75), (20, 83),
        (22, 92), (25, 105), (28, 118), (32, 137), (37, 162), (43, 193), (50, 225), (60, 270),
    ],
    # Transition and Interference holes
    "K7": [
        (-10, 0), (-9, 3), (-10, 5), (-12, 6), (-15, 6), (-18, 7),
        (-21, 9), (-25, 10), (-28, 12), (-33, 13), (-36, 16), (-40, 17), (-45, 18),
        (-50, 20), (-56, 24), (-64, 26), (-73, 32), (-85, 40), (-100, 50), (-120, 55), (-145, 65),
    ],
    "M7": [
        (-12, -2), (-16, -4), (-21, -6), (-25, -7), (-30, -9), (-36, -11),
        (-43, -13), (-51, -16), (-60, -20), (-70, -24), (-79, -27), (-87, -30), (-96, -33),
        (-108, -38), (-122, -42), (-138, -48), (-161, -56), (-191, -66), (-228, -78), (-267, -92), (-320, -110),
    ],
    "N7": [
        (-14, -4), (-20, -8), (-25, -10), (-30, -12), (-36, -15), (-43, -18),
        (-52, -22), (-61, -26), (-72, -32), (-83, -37), (-94, -42), (-104, -47), (-114, -51),
        (-128, -58), (-145, -65), (-164, -74), (-192, -87), (-228, -103), (-272, -122), (-320, -145), (-385, -175),
    ],
    "P7": [
        (-16, -6), (-24, -12), (-30, -15), (-36, -18), (-43, -22), (-51, -26),
        (-62, -32), (-72, -37), (-85, -45), (-98, -52), (-111, -59), (-123, -66), (-135, -72),
        (-150, -80), (-170, -90), (-193, -103), (-225, -120), (-265, -140), (-320, -170), (-375, -200), (-450, -240),
    ],
    "P9": [
        (-31, -6), (-42, -12), (-51, -15), (-61, -18), (-74, -22), (-88, -26),
        (-106, -32), (-125, -38), (-145, -45), (-167, -52), (-189, -59), (-207, -67), (-228, -73),
        (-255, -80), (-290, -90), (-333, -103), (-380, -120), (-450, -140), (-540, -170), (-640, -200), (-780, -240),
    ],
}

# ISO 286 shaft limits (ei, es) in micrometers (µm) for each of the 21 steps
ISO_286_SHAFTS_UM: dict[str, list[tuple[float, float]]] = {
    # Standard h shafts (basis shaft system)
    "h5": _make_h_shaft("IT5"),
    "h6": _make_h_shaft("IT6"),
    "h7": _make_h_shaft("IT7"),
    "h8": _make_h_shaft("IT8"),
    "h9": _make_h_shaft("IT9"),
    "h10": _make_h_shaft("IT10"),
    "h11": _make_h_shaft("IT11"),
    "h12": _make_h_shaft("IT12"),
    "h13": _make_h_shaft("IT13"),
    "h14": _make_h_shaft("IT14"),
    # Symmetrical js shafts
    "js6": _make_js_sym("IT6"),
    "js7": _make_js_sym("IT7"),
    "js8": _make_js_sym("IT8"),
    "js9": _make_js_sym("IT9"),
    "js11": _make_js_sym("IT11"),
    "js13": _make_js_sym("IT13"),
    "js14": _make_js_sym("IT14"),
    # Clearance shafts
    "g6": [
        (-8, -2), (-12, -4), (-14, -5), (-17, -6), (-20, -7), (-25, -9),
        (-29, -10), (-34, -12), (-39, -14), (-44, -15), (-49, -17), (-54, -18), (-60, -20),
        (-66, -22), (-75, -25), (-84, -28), (-98, -32), (-115, -37), (-135, -43), (-160, -50), (-195, -60),
    ],
    "f7": [
        (-16, -6), (-22, -10), (-28, -13), (-34, -16), (-41, -20), (-50, -25),
        (-60, -30), (-71, -36), (-83, -43), (-96, -50), (-108, -56), (-119, -62), (-131, -68),
        (-146, -76), (-166, -86), (-188, -98), (-215, -110), (-255, -130), (-300, -150), (-355, -180), (-420, -210),
    ],
    "f8": [
        (-20, -6), (-28, -10), (-35, -13), (-43, -16), (-53, -20), (-64, -25),
        (-76, -30), (-90, -36), (-106, -43), (-122, -50), (-137, -56), (-151, -62), (-165, -68),
        (-186, -76), (-211, -86), (-238, -98), (-275, -110), (-325, -130), (-380, -150), (-460, -180), (-540, -210),
    ],
    "e8": [
        (-28, -14), (-38, -20), (-47, -25), (-59, -32), (-73, -40), (-89, -50),
        (-106, -60), (-126, -72), (-148, -85), (-172, -100), (-191, -110), (-214, -125), (-242, -145),
        (-280, -170), (-320, -195), (-360, -220), (-415, -250), (-485, -290), (-570, -340), (-680, -400), (-810, -480),
    ],
    "e9": [
        (-39, -14), (-50, -20), (-61, -25), (-75, -32), (-92, -40), (-112, -50),
        (-134, -60), (-159, -72), (-185, -85), (-215, -100), (-240, -110), (-265, -125), (-300, -145),
        (-345, -170), (-395, -195), (-450, -220), (-510, -250), (-600, -290), (-710, -340), (-840, -400), (-1020, -480),
    ],
    "d9": [
        (-45, -20), (-60, -30), (-76, -40), (-93, -50), (-117, -65), (-142, -80),
        (-174, -100), (-207, -120), (-245, -145), (-285, -170), (-320, -190), (-350, -210), (-385, -230),
        (-435, -260), (-490, -290), (-560, -330), (-640, -380), (-750, -440), (-890, -520), (-1040, -600), (-1240, -700),
    ],
    "d10": [
        (-60, -20), (-78, -30), (-98, -40), (-120, -50), (-149, -65), (-180, -80),
        (-220, -100), (-260, -120), (-305, -145), (-355, -170), (-400, -190), (-440, -210), (-480, -230),
        (-540, -260), (-610, -290), (-690, -330), (-800, -380), (-940, -440), (-1120, -520), (-1300, -600), (-1560, -700),
    ],
    # Transition and Interference shafts
    "k6": [
        (0, 6), (1, 9), (1, 10), (1, 12), (2, 15), (2, 18),
        (2, 21), (3, 25), (3, 28), (4, 33), (4, 36), (4, 40), (5, 45),
        (6, 50), (7, 57), (8, 64), (9, 75), (11, 89), (13, 105), (16, 126), (20, 155),
    ],
    "m6": [
        (2, 8), (4, 12), (6, 15), (7, 18), (8, 21), (9, 25),
        (11, 30), (13, 35), (15, 40), (17, 46), (20, 52), (21, 57), (23, 63),
        (26, 70), (30, 80), (34, 90), (40, 106), (48, 126), (58, 150), (70, 180), (86, 221),
    ],
    "n6": [
        (4, 10), (8, 16), (10, 19), (12, 23), (15, 28), (17, 33),
        (20, 39), (23, 45), (27, 52), (31, 60), (34, 66), (37, 73), (40, 80),
        (45, 89), (51, 101), (58, 114), (68, 134), (80, 158), (95, 187), (115, 225), (140, 275),
    ],
    "p6": [
        (6, 12), (12, 20), (15, 24), (18, 29), (22, 35), (26, 42),
        (32, 51), (37, 59), (43, 68), (50, 79), (56, 88), (62, 98), (68, 108),
        (78, 122), (88, 138), (100, 156), (120, 186), (140, 218), (170, 262), (200, 310), (240, 375),
    ],
    "s6": [
        (14, 20), (19, 27), (23, 32), (28, 39), (35, 48), (43, 59),
        (53, 72), (68, 90), (87, 112), (111, 140), (130, 162), (146, 182), (166, 206),
        (190, 234), (218, 268), (250, 306), (292, 358), (345, 423), (410, 502), (485, 595), (580, 715),
    ],
}

# ISO 2768-1 linear tolerances (mm)
ISO_2768_1_LINEAR = {
    "f": {  # fine
        (0.5, 3.0): 0.05, (3.0, 6.0): 0.05, (6.0, 30.0): 0.1, (30.0, 120.0): 0.15,
        (120.0, 400.0): 0.2, (400.0, 1000.0): 0.3, (1000.0, 2000.0): 0.5, (2000.0, 4000.0): 0.8,
    },
    "m": {  # medium
        (0.5, 3.0): 0.1, (3.0, 6.0): 0.1, (6.0, 30.0): 0.2, (30.0, 120.0): 0.3,
        (120.0, 400.0): 0.5, (400.0, 1000.0): 0.8, (1000.0, 2000.0): 1.2, (2000.0, 4000.0): 2.0,
    },
    "c": {  # coarse
        (0.5, 3.0): 0.2, (3.0, 6.0): 0.3, (6.0, 30.0): 0.5, (30.0, 120.0): 0.8,
        (120.0, 400.0): 1.2, (400.0, 1000.0): 2.0, (1000.0, 2000.0): 3.0, (2000.0, 4000.0): 4.0,
    },
    "v": {  # very coarse
        (0.5, 3.0): 0.5, (3.0, 6.0): 0.5, (6.0, 30.0): 1.0, (30.0, 120.0): 1.5,
        (120.0, 400.0): 2.5, (400.0, 1000.0): 4.0, (1000.0, 2000.0): 6.0, (2000.0, 4000.0): 8.0,
    },
}

# ISO 2768-1 broken edges (chamfers and radii) in mm
ISO_2768_1_BROKEN_EDGES = {
    "f": {(0.5, 3.0): 0.2, (3.0, 6.0): 0.5, (6.0, 4000.0): 1.0},
    "m": {(0.5, 3.0): 0.2, (3.0, 6.0): 0.5, (6.0, 4000.0): 1.0},
    "c": {(0.5, 3.0): 0.4, (3.0, 6.0): 1.0, (6.0, 4000.0): 2.0},
    "v": {(0.5, 3.0): 0.4, (3.0, 6.0): 1.0, (6.0, 4000.0): 2.0},
}

# ISO 2768-1 angular tolerances (degrees and arcminutes converted to decimal degrees)
ISO_2768_1_ANGULAR = {
    "f": {(0.0, 10.0): 1.0, (10.0, 50.0): 0.5, (50.0, 120.0): 0.333, (120.0, 400.0): 0.167, (400.0, 4000.0): 0.083},
    "m": {(0.0, 10.0): 1.0, (10.0, 50.0): 0.5, (50.0, 120.0): 0.333, (120.0, 400.0): 0.167, (400.0, 4000.0): 0.083},
    "c": {(0.0, 10.0): 1.5, (10.0, 50.0): 1.0, (50.0, 120.0): 0.5, (120.0, 400.0): 0.25, (400.0, 4000.0): 0.167},
    "v": {(0.0, 10.0): 3.0, (10.0, 50.0): 2.0, (50.0, 120.0): 1.0, (120.0, 400.0): 0.5, (400.0, 4000.0): 0.333},
}


@dataclass(slots=True)
class FitResult:
    """Result of an ISO 286 mechanical fit calculation."""
    nominal: float
    hole_symbol: str
    shaft_symbol: str
    hole_ei: float  # mm
    hole_es: float  # mm
    shaft_ei: float # mm
    shaft_es: float # mm
    min_clearance: float  # mm (J_min = hole_ei - shaft_es)
    max_clearance: float  # mm (J_max = hole_es - shaft_ei)
    fit_type: Literal["jeu", "serrage", "incertain"]
    hole_min: float # mm (nominal + hole_ei)
    hole_max: float # mm (nominal + hole_es)
    shaft_min: float # mm (nominal + shaft_ei)
    shaft_max: float # mm (nominal + shaft_es)


def _get_step_index(nominal: float) -> int:
    """Return index of ISO 286 size range for given nominal dimension in mm.

    Uses binary search (bisect_left) over the monotonic upper bounds tuple ISO_286_HIGH_BOUNDS
    in O(log N) time up to 3 150 mm.
    """
    if nominal <= 0:
        raise ValueError(f"Nominal size must be > 0, got {nominal}")
    if nominal > 3150.0:
        raise ValueError(f"Nominal size > 3150 mm not supported by ISO 286 table, got {nominal}")

    return bisect.bisect_left(ISO_286_HIGH_BOUNDS, nominal)


def get_available_iso286_symbols() -> dict[str, list[str]]:
    """Return dictionary with supported hole and shaft ISO 286 symbols."""
    return {
        "holes": list(ISO_286_HOLES_UM.keys()),
        "shafts": list(ISO_286_SHAFTS_UM.keys()),
    }


def get_iso286_limits(nominal: float, symbol: str) -> tuple[float, float]:
    """Get lower (ei/EI) and upper (es/ES) deviations in millimeters for an ISO 286 symbol.

    Args:
        nominal: Basic size in mm (up to 3 150 mm).
        symbol: Fit code, e.g. 'H7', 'JS13' (hole) or 'g6', 'h7' (shaft).

    Returns:
        tuple (ei, es) in mm.
    """
    idx = _get_step_index(nominal)
    symbol = symbol.strip()

    if symbol in ISO_286_HOLES_UM:
        ei_um, es_um = ISO_286_HOLES_UM[symbol][idx]
        return round(ei_um / 1000.0, 5), round(es_um / 1000.0, 5)
    elif symbol in ISO_286_SHAFTS_UM:
        ei_um, es_um = ISO_286_SHAFTS_UM[symbol][idx]
        return round(ei_um / 1000.0, 5), round(es_um / 1000.0, 5)
    else:
        raise ValueError(
            f"Unsupported ISO 286 symbol '{symbol}'. "
            f"Supported holes: {list(ISO_286_HOLES_UM.keys())}; "
            f"Supported shafts: {list(ISO_286_SHAFTS_UM.keys())}"
        )


def parse_iso_fit(designation: str) -> tuple[str, str]:
    """Parse ISO fit designation (e.g., 'H7/g6' or 'H8 / f7') into hole and shaft symbols.

    Returns:
        (hole_symbol, shaft_symbol)
    """
    parts = designation.split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid fit designation: '{designation}'. Expected format 'H7/g6'")

    hole = parts[0].strip()
    shaft = parts[1].strip()

    if not _HOLE_PATTERN.match(hole):
        raise ValueError(f"Invalid hole format: '{hole}'")
    if not _SHAFT_PATTERN.match(shaft):
        raise ValueError(f"Invalid shaft format: '{shaft}'")

    return hole, shaft


def calculate_fit(nominal: float, hole_symbol: str, shaft_symbol: str) -> FitResult:
    """Calculate mechanical fit limits and characteristics between a hole and a shaft.

    Args:
        nominal: Basic size in mm (up to 3 150 mm).
        hole_symbol: Hole tolerance code, e.g. 'H7', 'JS13'.
        shaft_symbol: Shaft tolerance code, e.g. 'g6', 'h6'.

    Returns:
        FitResult with clearance/interference values and classification.
    """
    hole_ei, hole_es = get_iso286_limits(nominal, hole_symbol)
    shaft_ei, shaft_es = get_iso286_limits(nominal, shaft_symbol)

    j_min = round(hole_ei - shaft_es, 5)
    j_max = round(hole_es - shaft_ei, 5)

    if j_min >= 0:
        fit_type: Literal["jeu", "serrage", "incertain"] = "jeu"
    elif j_max <= 0:
        fit_type = "serrage"
    else:
        fit_type = "incertain"

    return FitResult(
        nominal=nominal,
        hole_symbol=hole_symbol,
        shaft_symbol=shaft_symbol,
        hole_ei=hole_ei,
        hole_es=hole_es,
        shaft_ei=shaft_ei,
        shaft_es=shaft_es,
        min_clearance=j_min,
        max_clearance=j_max,
        fit_type=fit_type,
        hole_min=round(nominal + hole_ei, 5),
        hole_max=round(nominal + hole_es, 5),
        shaft_min=round(nominal + shaft_ei, 5),
        shaft_max=round(nominal + shaft_es, 5),
    )


def get_iso2768_linear_tolerance(
    nominal: float,
    grade: Literal["f", "m", "c", "v"] = "m",
) -> float:
    """Get ISO 2768-1 general linear tolerance (+/- mm) for a nominal size and tolerance class."""
    if nominal <= 0:
        raise ValueError(f"Nominal dimension must be > 0, got {nominal}")
    if grade not in ISO_2768_1_LINEAR:
        raise ValueError(f"Unknown ISO 2768-1 grade '{grade}'. Must be 'f', 'm', 'c' or 'v'")

    table = ISO_2768_1_LINEAR[grade]
    for (low, high), tol in table.items():
        if low <= nominal <= high:
            return tol
    if nominal < 0.5:
        return table[(0.5, 3.0)]
    return max(table.values())


def get_iso2768_broken_edges_tolerance(
    nominal: float,
    grade: Literal["f", "m", "c", "v"] = "m",
) -> float:
    """Get ISO 2768-1 broken edges tolerance (+/- mm) for chamfers and transition radii."""
    if nominal <= 0:
        raise ValueError(f"Nominal dimension must be > 0, got {nominal}")
    if grade not in ISO_2768_1_BROKEN_EDGES:
        raise ValueError(f"Unknown ISO 2768-1 grade '{grade}'")

    table = ISO_2768_1_BROKEN_EDGES[grade]
    for (low, high), tol in table.items():
        if low <= nominal <= high:
            return tol
    if nominal < 0.5:
        return table[(0.5, 3.0)]
    return max(table.values())


def get_iso2768_angular_tolerance(
    nominal: float,
    grade: Literal["f", "m", "c", "v"] = "m",
) -> float:
    """Get ISO 2768-1 general angular tolerance (+/- degrees) for length of shorter side in mm."""
    if nominal <= 0:
        raise ValueError(f"Length of shorter side must be > 0, got {nominal}")
    if grade not in ISO_2768_1_ANGULAR:
        raise ValueError(f"Unknown ISO 2768-1 grade '{grade}'")

    table = ISO_2768_1_ANGULAR[grade]
    for (low, high), tol in table.items():
        if low < nominal <= high:
            return tol
    return list(table.values())[-1]
