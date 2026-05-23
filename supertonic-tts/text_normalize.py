"""
text_normalize.py — Pre-expand units/symbols the model mispronounces.
Mirrors the same logic in the browser main.js.
"""

import re


# ── Month names for date expansion ────────────────────────────────────────────
_MONTHS = [
    '', 'January', 'February', 'March', 'April', 'May', 'June',
    'July', 'August', 'September', 'October', 'November', 'December',
]


# ── Roman numeral expansion ────────────────────────────────────────────────────

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

# Only expand after known title/name prefixes — prevents "World War the Second",
# "Model the Tenth", "Section the Fourth", etc.
_ROMAN_RE = re.compile(
    r'\b((?:King|Queen|Emperor|Empress|Prince|Princess|Pope|Cardinal|'
    r'Charles|Henry|Louis|Elizabeth|James|George|Edward|Richard|William|'
    r'John|Paul|Francis|Benedict|Clement|Pius|Gregory|Leo|'
    r'Gustav|Carl|Philip|Frederick|Margaret|Catherine|Peter|Ivan|'
    r'Napoleon)\s+)'
    r'(M{0,3}(?:CM|CD|D?C{0,3})(?:XC|XL|L?X{0,3})(?:IX|IV|V?I{0,3}))\b'
    r'(?=\W|$)',
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
    prefix, numeral = m.group(1), m.group(2)
    if not numeral:
        return m.group(0)
    val = _roman_to_int(numeral)
    return prefix + _ORDINALS.get(val, numeral)


def normalize(text: str) -> str:
    t = text

    # 1. Normalize Unicode whitespace (non-breaking space, thin space, etc.)
    t = re.sub(r'[^\S\n]+', ' ', t)

    # 2. Normalize dash variants
    t = t.replace('\u2212', '-')   # mathematical minus → hyphen
    t = t.replace('\u2014', '\u2013')  # em dash → en dash (used in ranges)

    # 3. Thousands separators (1,234 → 1234) — must run before decimal comma
    t = re.sub(r'\b(\d{1,3}),(\d{3})\b', r'\1\2', t)

    # 4. ISO dates (2026-06-07 → 7 June 2026)
    def _expand_date(m: re.Match) -> str:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        if 1 <= mo <= 12:
            return f"{d} {_MONTHS[mo]} {y}"
        return m.group(0)
    t = re.sub(r'\b(\d{4})-(\d{2})-(\d{2})\b', _expand_date, t)

    # 5. Time (7:30 AM → 7 30 AM  |  18:05 → 18 05)
    t = re.sub(r'\b(\d{1,2}):([0-5]\d)\s*([AaPp][Mm])\b', r'\1 \2 \3', t)
    t = re.sub(r'\b([01]?\d|2[0-3]):([0-5]\d)\b', r'\1 \2', t)

    # 6. Temperature ranges before singles
    t = re.sub(r'(-?\d+(?:\.\d+)?)\s*[-–]\s*(-?\d+(?:\.\d+)?)\s*°F', r'\1 to \2 degree Fahrenheit', t)
    t = re.sub(r'(-?\d+(?:\.\d+)?)\s*[-–]\s*(-?\d+(?:\.\d+)?)\s*°C', r'\1 to \2 degree Celsius', t)
    t = re.sub(r'(-?\d+(?:\.\d+)?)\s*°F', r'\1 degree Fahrenheit', t)
    t = re.sub(r'(-?\d+(?:\.\d+)?)\s*°C', r'\1 degree Celsius', t)
    t = re.sub(r'(-?\d+(?:\.\d+)?)\s*°K', r'\1 degree Kelvin', t)
    t = re.sub(r'(-?\d+(?:\.\d+)?)\s*°',  r'\1 degree', t)

    # 7. Speed — km/h before plain km (order matters)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*mph', r'\1 to \2 miles per hour', t, flags=re.I)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*kph', r'\1 to \2 kilometers per hour', t, flags=re.I)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*km/h', r'\1 to \2 kilometers per hour', t, flags=re.I)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*mph\b',   r'\1 miles per hour', t, flags=re.I)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*kph\b',   r'\1 kilometers per hour', t, flags=re.I)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*km/h\b',  r'\1 kilometers per hour', t, flags=re.I)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*m/s\b',   r'\1 meters per second', t)

    # 8. Pressure
    t = re.sub(r'(\d+(?:\.\d+)?)\s*inHg\b',  r'\1 inches of mercury', t, flags=re.I)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*hPa\b',   r'\1 hectopascals', t, flags=re.I)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*mbar?\b',  r'\1 millibars', t, flags=re.I)

    # 9. Energy / power — kWh before Wh, Wh before W, kW before W
    t = re.sub(r'(\d+(?:\.\d+)?)\s*kWh\b', r'\1 kilowatt hours', t, flags=re.I)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*Wh\b',  r'\1 watt hours', t)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*kW\b',  r'\1 kilowatts', t)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*W\b',   r'\1 watts', t)

    # 10. Electrical
    t = re.sub(r'(\d+(?:\.\d+)?)\s*V\b', r'\1 volts', t)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*A\b', r'\1 amps', t)

    # 11. Air quality
    t = re.sub(r'\bCO2\b',   'carbon dioxide', t, flags=re.I)
    t = re.sub(r'\bPM2\.5\b', 'P M two point five', t, flags=re.I)
    t = re.sub(r'\bPM10\b',   'P M ten', t, flags=re.I)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*ppm\b', r'\1 parts per million', t, flags=re.I)

    # 12. Distance / precipitation — ranges before singles, km/h already handled above
    t = re.sub(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*mm\b', r'\1 to \2 millimeters', t, flags=re.I)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*mm\b', r'\1 millimeters', t, flags=re.I)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*cm\b', r'\1 centimeters', t, flags=re.I)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*km\b', r'\1 kilometers', t, flags=re.I)

    # 13. Currency
    t = re.sub(r'€\s*(\d+(?:\.\d+)?)',  r'\1 euros', t)
    t = re.sub(r'\$\s*(\d+(?:\.\d+)?)', r'\1 dollars', t)
    t = re.sub(r'£\s*(\d+(?:\.\d+)?)',  r'\1 pounds', t)
    # Rupee — handle crore/lakh suffix (₹6 crore → 6 crore rupees)
    t = re.sub(r'₹\s*(\d+(?:\.\d+)?)\s*(crore|lakh|lacs?)\b', r'\1 \2 rupees', t, flags=re.I)
    t = re.sub(r'₹\s*(\d+(?:\.\d+)?)', r'\1 rupees', t)
    t = re.sub(r'(\d+(?:[.,]\d+)?)\s*SEK\b', r'\1 Swedish kronor', t, flags=re.I)
    t = re.sub(r'(\d+(?:[.,]\d+)?)\s*kr\b',  r'\1 kronor', t, flags=re.I)

    # 14. Percentage range before single
    t = re.sub(r'(\d+(?:\.\d+)?)\s*[-–]\s*(\d+(?:\.\d+)?)\s*%', r'\1 to \2 percent', t)
    t = re.sub(r'(\d+(?:\.\d+)?)\s*%', r'\1 percent', t)

    # 15. Decimal comma — Swedish locale (1,5 → 1.5); run after thousands separator
    #     Convert to dot-decimal so the TTS model reads it natively (no "point" pause)
    t = re.sub(r'\b(\d+),(\d+)\b', r'\1.\2', t)

    # 16. Fractions (UV index, scores)
    t = re.sub(r'\b(\d+)/(\d{1,2})\b', r'\1 out of \2', t)

    # 17. Compass directions — multi-letter only with case-insensitivity
    #     Single-letter (N/S/E/W) omitted — too many false positives
    for abbr, full in [('NNW', 'north-northwest'), ('NNE', 'north-northeast'),
                       ('SSW', 'south-southwest'), ('SSE', 'south-southeast'),
                       ('NW', 'northwest'), ('NE', 'northeast'),
                       ('SW', 'southwest'), ('SE', 'southeast')]:
        t = re.sub(rf'\b{abbr}\b', full, t, flags=re.I)

    # 18. Roman numerals — name-prefixed only (Charles XII, Pope John Paul II, etc.)
    t = _ROMAN_RE.sub(_expand_roman, t)

    # 19. Decimal numbers — let the TTS model read them natively (20.1, 12.5, etc.)
    #     Do NOT expand to "point" — Supertonic's prosody model handles decimals correctly
    #     and the "point" word introduces an audible pause in the output.

    # 20. Collapse extra spaces
    t = re.sub(r'  +', ' ', t)
    return t.strip()
