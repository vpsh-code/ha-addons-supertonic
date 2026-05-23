"""
text_normalize.py — Pre-expand units/symbols the model mispronounces.
Mirrors the same logic in the browser main.js.
"""

import re


def normalize(text: str) -> str:
    t = text

    # Temperature ranges before singles
    t = re.sub(r'(-?\d+(?:\.\d+)?)\s*[-–]\s*(-?\d+(?:\.\d+)?)\s*°F', r'\1 to \2 degree Fahrenheit', t)
    t = re.sub(r'(-?\d+(?:\.\d+)?)\s*[-–]\s*(-?\d+(?:\.\d+)?)\s*°C', r'\1 to \2 degree Celsius', t)
    # Single temperatures
    t = re.sub(r'(-?\d+(?:\.\d+)?)\s*°F', r'\1 degree Fahrenheit', t)
    t = re.sub(r'(-?\d+(?:\.\d+)?)\s*°C', r'\1 degree Celsius', t)
    t = re.sub(r'(-?\d+(?:\.\d+)?)\s*°K', r'\1 degree Kelvin', t)
    t = re.sub(r'(-?\d+(?:\.\d+)?)\s*°',  r'\1 degree', t)

    # Speed ranges
    t = re.sub(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*mph', r'\1 to \2 miles per hour', t, flags=re.I)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*kph', r'\1 to \2 kilometers per hour', t, flags=re.I)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*mph\b',   r'\1 miles per hour', t, flags=re.I)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*kph\b',   r'\1 kilometers per hour', t, flags=re.I)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*km/h\b',  r'\1 kilometers per hour', t, flags=re.I)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*m/s\b',   r'\1 meters per second', t)

    # Pressure
    t = re.sub(r'(\d+(?:\.\d+)?)\s*inHg\b',  r'\1 inches of mercury', t, flags=re.I)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*hPa\b',   r'\1 hectopascals', t, flags=re.I)
    t = re.sub(r'\((\d+(?:\.\d+)?)\s*mb\)',   r'(\1 millibars)', t, flags=re.I)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*mb\b',    r'\1 millibars', t, flags=re.I)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*mbar\b',  r'\1 millibars', t, flags=re.I)

    # Percentage
    t = re.sub(r'(\d+(?:\.\d+)?)\s*%', r'\1 percent', t)

    # Fractions (UV index, scores)
    t = re.sub(r'\b(\d+)/(\d{1,2})\b', r'\1 out of \2', t)

    # Compass directions
    for abbr, full in [('NNW','north-northwest'),('NNE','north-northeast'),
                       ('SSW','south-southwest'),('SSE','south-southeast'),
                       ('NW','northwest'),('NE','northeast'),
                       ('SW','southwest'),('SE','southeast')]:
        t = re.sub(rf'\b{abbr}\b', full, t)

    # Decimal numbers → spoken form  (23.1 → 23 point 1)
    t = re.sub(r'(\d+)\.(\d+)', r'\1 point \2', t)

    # Collapse extra spaces
    t = re.sub(r'  +', ' ', t)
    return t.strip()
