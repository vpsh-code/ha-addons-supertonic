"""
text_normalize.py — Pre-expand units/symbols the model mispronounces.
Mirrors the same logic in the browser main.js.
"""

import re


# ── Roman numeral expansion ────────────────────────────────────────────────────

_ROMAN_MAP = [
    (1000, 'M'), (900, 'CM'), (800, 'DCCC'), (700, 'DCC'), (600, 'DC'),
    (500, 'D'),  (400, 'CD'), (300, 'CCC'),  (200, 'CC'),  (100, 'C'),
    (90,  'XC'), (80,  'LXXX'),(70, 'LXX'), (60,  'LX'),  (50,  'L'),
    (40,  'XL'), (30,  'XXX'), (20, 'XX'),  (19,  'XIX'),  (18,  'XVIII'),
    (17,  'XVII'),(16, 'XVI'), (15, 'XV'),  (14,  'XIV'),  (13,  'XIII'),
    (12,  'XII'), (11, 'XI'),  (10, 'X'),   (9,   'IX'),   (8,   'VIII'),
    (7,   'VII'), (6,  'VI'),  (5,  'V'),   (4,   'IV'),   (3,   'III'),
    (2,   'II'),  (1,  'I'),
]

_ORDINALS = {
    1: 'the First',    2: 'the Second',   3: 'the Third',    4: 'the Fourth',
    5: 'the Fifth',    6: 'the Sixth',    7: 'the Seventh',  8: 'the Eighth',
    9: 'the Ninth',   10: 'the Tenth',   11: 'the Eleventh',12: 'the Twelfth',
    13: 'the Thirteenth', 14: 'the Fourteenth', 15: 'the Fifteenth',
    16: 'the Sixteenth',  17: 'the Seventeenth', 18: 'the Eighteenth',
    19: 'the Nineteenth', 20: 'the Twentieth',   21: 'the Twenty-first',
    22: 'the Twenty-second', 23: 'the Twenty-third', 24: 'the Twenty-fourth',
    25: 'the Twenty-fifth',
}

# Valid Roman numeral pattern (I–XXV covers all monarchs/popes in practice)
_ROMAN_RE = re.compile(
    r'(?<=[A-Za-z][ ])'           # preceded by a word then space (name context)
    r'\b(M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3}))\b'
    r'(?=\W|$)',                   # followed by any non-word char or end of string
    re.UNICODE,
)


def _roman_to_int(s: str) -> int:
    result, prev = 0, 0
    for ch in reversed(s.upper()):
        val = {'I': 1, 'V': 5, 'X': 10, 'L': 50,
               'C': 100, 'D': 500, 'M': 1000}.get(ch, 0)
        result += val if val >= prev else -val
        prev = val
    return result


def _expand_roman(m: re.Match) -> str:
    s = m.group(1)
    if not s:
        return m.group(0)
    val = _roman_to_int(s)
    return _ORDINALS.get(val, m.group(0))


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

    # Roman numerals in name context (Charles XI → Charles the Eleventh)
    t = _ROMAN_RE.sub(_expand_roman, t)

    # Decimal numbers → spoken form  (23.1 → 23 point 1)
    t = re.sub(r'(\d+)\.(\d+)', r'\1 point \2', t)

    # Collapse extra spaces
    t = re.sub(r'  +', ' ', t)
    return t.strip()
