"""ISO standards references for tolerance calculations.

This module provides lookup tables and helpers for:
- ISO 286: Geometrical Product Specifications (GPS) - ISO code system for tolerances on linear sizes
- ISO 2768-1: General tolerances for linear and angular dimensions without individual tolerance indications
"""

from typing import Literal

# ISO 286 fundamental deviations for shafts (lowercase) and holes (uppercase)
# Values in micrometers (µm) for basic sizes up to 500mm
ISO_286_FUNDAMENTAL_DEVIATIONS_SHAFT = {
    "a": 270, "b": 140, "c": 60, "d": 20, "e": 14, "f": 6, "g": 2,
    "h": 0, "js": 0, "j": -2, "k": -6, "m": -20, "n": -60, "p": -140,
    "r": -270, "s": -430, "t": -600, "u": -800, "v": -1000, "x": -1200,
    "y": -1400, "z": -1600,
}

ISO_286_FUNDAMENTAL_DEVIATIONS_HOLE = {
    "A": -270, "B": -140, "C": -60, "D": -20, "E": -14, "F": -6, "G": -2,
    "H": 0, "JS": 0, "J": 2, "K": 6, "M": 20, "N": 60, "P": 140,
    "R": 270, "S": 430, "T": 600, "U": 800, "V": 1000, "X": 1200,
    "Y": 1400, "Z": 1600,
}

# ISO 286 standard tolerance grades (IT01 to IT18) - values in µm for size ranges
# Simplified: only common grades for typical mechanical design
ISO_286_TOLERANCE_GRADES = {
    1: 0.8, 2: 1.2, 3: 2, 4: 3, 5: 4, 6: 5, 7: 6, 8: 7, 9: 8, 10: 9,
    11: 11, 12: 13, 13: 15, 14: 18, 15: 20, 16: 22, 17: 25, 18: 28,
}

# ISO 2768-1 general tolerances for linear dimensions (fine, medium, coarse, very coarse)
# Values in mm
ISO_2768_1_LINEAR = {
    "f": {  # fine
        (0, 3): 0.05, (3, 6): 0.05, (6, 30): 0.1, (30, 120): 0.15,
        (120, 400): 0.2, (400, 1000): 0.3, (1000, 2000): 0.5,
        (2000, 4000): 0.8,
    },
    "m": {  # medium
        (0, 3): 0.1, (3, 6): 0.1, (6, 30): 0.2, (30, 120): 0.3,
        (120, 400): 0.5, (400, 1000): 0.8, (1000, 2000): 1.2,
        (2000, 4000): 2.0,
    },
    "c": {  # coarse
        (0, 3): 0.2, (3, 6): 0.3, (6, 30): 0.5, (30, 120): 0.8,
        (120, 400): 1.2, (400, 1000): 2.0, (1000, 2000): 3.0,
        (2000, 4000): 4.0,
    },
    "v": {  # very coarse
        (0, 3): 0.5, (3, 6): 0.5, (6, 30): 1.0, (30, 120): 1.5,
        (120, 400): 2.5, (400, 1000): 4.0, (1000, 2000): 6.0,
        (2000, 4000): 8.0,
    },
}

# ISO 2768-1 general tolerances for angular dimensions
ISO_2768_1_ANGULAR = {
    "f": {  # fine
        (0, 10): 1.0, (10, 50): 0.5, (50, 120): 0.3, (120, 400): 0.2,
        (400, 1000): 0.1, (1000, 2000): 0.05,
    },
    "m": {  # medium
        (0, 10): 1.5, (10, 50): 1.0, (50, 120): 0.5, (120, 400): 0.3,
        (400, 1000): 0.2, (1000, 2000): 0.1,
    },
    "c": {  # coarse
        (0, 10): 3.0, (10, 50): 2.0, (50, 120): 1.0, (120, 400): 0.5,
        (400, 1000): 0.3, (1000, 2000): 0.2,
    },
    "v": {  # very coarse
        (0, 10): 5.0, (10, 50): 4.0, (50, 120): 2.0, (120, 400): 1.0,
        (400, 1000): 0.5, (1000, 2000): 0.3,
    },
}


def get_iso286_tolerance(basic_size: float, grade: int) -> float:
    """Get IT tolerance value for a basic size and grade (simplified)."""
    # Simplified: returns grade value directly in µm
    # Real implementation would use size ranges from ISO 286 tables
    return ISO_286_TOLERANCE_GRADES.get(grade, 0.0)


def get_iso2768_linear_tolerance(nominal: float, grade: Literal["f", "m", "c", "v"] = "m") -> float:
    """Get ISO 2768-1 general linear tolerance for a nominal size and grade."""
    table = ISO_2768_1_LINEAR[grade]
    for (low, high), tol in table.items():
        if low < nominal <= high:
            return tol
    # For sizes beyond table, return largest value
    return max(table.values())


def get_iso2768_angular_tolerance(nominal: float, grade: Literal["f", "m", "c", "v"] = "m") -> float:
    """Get ISO 2768-1 general angular tolerance for a nominal angle and grade."""
    table = ISO_2768_1_ANGULAR[grade]
    for (low, high), tol in table.items():
        if low < nominal <= high:
            return tol
    return max(table.values())


def parse_iso_fit(designation: str) -> tuple[str, int, str, int]:
    """Parse ISO fit designation (e.g., 'H7/g6') into hole/shaft components.
    
    Returns: (hole_letter, hole_grade, shaft_letter, shaft_grade)
    """
    # Simplified parser - real implementation would be more robust
    parts = designation.split("/")
    if len(parts) != 2:
        raise ValueError(f"Invalid fit designation: {designation}")
    hole = parts[0].strip()
    shaft = parts[1].strip()
    # Extract letter(s) and number
    import re
    hole_match = re.match(r"([A-Z]+)(\d+)", hole)
    shaft_match = re.match(r"([a-z]+)(\d+)", shaft)
    if not hole_match or not shaft_match:
        raise ValueError(f"Invalid fit format: {designation}")
    return hole_match.group(1), int(hole_match.group(2)), shaft_match.group(1), int(shaft_match.group(2))