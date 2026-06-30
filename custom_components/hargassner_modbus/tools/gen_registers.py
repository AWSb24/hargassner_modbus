"""Generate registers.json for the hargassner_modbus HA integration.

Single source of truth: the user-curated MODBUS-Parameter-erweitert.csv (Synonym,
Kategorie, Gate, Gate-aktiv-bei, Beschreibung, Typ, Schreib-FC, Multiplikator, …).
"""
import csv, json, re, unicodedata, sys
from pathlib import Path

# Paths relative to this file: <repo>/custom_components/hargassner_modbus/tools/
_HERE = Path(__file__).resolve()
_REPO = _HERE.parents[3]            # repository root
_COMPONENT = _HERE.parents[1]       # custom_components/hargassner_modbus
SRC_CURATED = str(_REPO / "MODBUS-Parameter-erweitert.csv")
OUT = str(_COMPONENT / "registers.json")


def slugify(s):
    s = s.replace("ä","ae").replace("ö","oe").replace("ü","ue").replace("ß","ss")
    s = s.replace("Ä","ae").replace("Ö","oe").replace("Ü","ue")
    s = unicodedata.normalize("NFKD", s).encode("ascii","ignore").decode("ascii")
    s = re.sub(r"[^a-zA-Z0-9]+", "_", s).strip("_").lower()
    return s or "reg"

def num(x):
    x = (x or "").strip().replace(",", ".")
    if x == "":
        return None
    try:
        f = float(x)
        return int(f) if f.is_integer() else f
    except ValueError:
        return None

def category(desc):
    d = desc.lower()
    rules = [
        # --- distinct subsystems first (some contain words like "puffer") ---
        (r"\bmbus\b|m-bus|wärmemengenzähler|warmemengenzahler", "mbus_wmz"),
        (r"sensorplatine", "sensorplatine"),
        (r"differenzregler", "differenzregler"),
        (r"fremdwärme|fremdwarme", "fremdwaerme"),
        (r"estrich", "estrich"),
        (r"umschalteinheit|\baup\b", "umschalteinheit"),
        (r"ecleaner", "kessel"),
        (r"\bknx\b", "knx"),
        (r"\bfws ?1\b|frischwasserstation 1|frischwasser ?1\b", "frischwasser_1"),
        (r"\bfws ?2\b|frischwasserstation 2|frischwasser ?2\b", "frischwasser_2"),
        (r"\bfws ?3\b|frischwasserstation 3|frischwasser ?3\b", "frischwasser_3"),
        (r"\bfws ?4\b|frischwasserstation 4|frischwasser ?4\b", "frischwasser_4"),
        (r"\bfws\b|frischwasser", "frischwasser"),
        # --- heating circuits (full name and short "HKx" form) ---
        (r"heizkreis a\b|\bhka\b", "heizkreis_a"),
        (r"heizkreis b\b|\bhkb\b", "heizkreis_b"),
        (r"heizkreis 1\b|\bhk1\b", "heizkreis_1"),
        (r"heizkreis 2\b|\bhk2\b", "heizkreis_2"),
        (r"heizkreis 3\b|\bhk3\b", "heizkreis_3"),
        (r"heizkreis 4\b|\bhk4\b", "heizkreis_4"),
        (r"heizkreis 5\b|\bhk5\b", "heizkreis_5"),
        (r"heizkreis 6\b|\bhk6\b", "heizkreis_6"),
        # --- boilers ---
        (r"boiler a\b","boiler_a"),(r"boiler b\b","boiler_b"),
        (r"boiler 1\b","boiler_1"),(r"boiler 2\b","boiler_2"),(r"boiler 3\b","boiler_3"),
        # --- cascade / solar before buffers: "Kaskade … Puffer …" belongs to
        #     kaskade, not puffer ---
        (r"kaskade","kaskade"),(r"solar","solar"),
        # --- buffers (zusatz/zentral before generic puffer). Match "zusatzpuffer"
        #     and the HKM marker anywhere, e.g. "Zusatzpuffer-Temperatur (HKM1)" ---
        (r"zentralpuffer","zentralpuffer"),
        (r"(?=.*zusatzpuffer)(?=.*hkm1)","zusatzpuffer_hkm1"),
        (r"(?=.*zusatzpuffer)(?=.*hkm2)","zusatzpuffer_hkm2"),
        (r"puffer","puffer"),
        (r"fernleitung|fernw","fernleitung"),
        (r"außentemperatur|aussentemperatur|aussenfühler|aussenfuhler","witterung"),
        (r"kessel|rauchgas|einschub|o2|gluterhalt|entaschung|brennstoff|pellet|"
         r"rost|asche|reinigung|zündung|zundung|lambda|füllen|fullen|saug|"
         r"raumaustrag|putzeinrichtung|störung|storung|stb|netzteil|platine|nano-pk|"
         r"programmwahlschalter",
         "kessel"),
    ]
    for pat, cat in rules:
        if re.search(pat, d):
            return cat
    # diagnostics / system-wide settings that fit no specific subsystem
    return "system"

# All DAQ-ANA channels store their value as fixed-point ×10 (tenths). The CSV
# fills the 0,1 multiplier only inconsistently, so we apply 0.1 to every DAQ-ANA
# register (confirmed live for temperatures, Programmwahlschalter, Lagerstand and
# Verbrauch Pellets). Per-address exceptions (e.g. a DAQ-ANA that is NOT tenths)
# can be forced here; this override is applied last and wins.
SCALE_OVERRIDES: dict[int, float] = {}

# Enum label overrides for registers where the CSV is missing the value labels.
# Keyed by address -> {index: label}.
ENUM_OVERRIDES: dict[int, dict[int, str]] = {
    # Programmwahlschalter HKM2 (CSV has no labels) -> same as HKM1 (11338)
    11340: {0: "Hand", 1: "Aus", 2: "Boiler", 3: "Auto"},
}

# Maps the raw CSV unit to (HA-canonical unit string, device_class, state_class).
# HA validates the unit string against the device_class, so the unit must use the
# exact casing/spelling HA expects (e.g. "L/h", "kW", "min").
UNIT_DC = {
    "°C": ("°C","temperature","measurement"),
    "%": ("%",None,"measurement"),
    "kW": ("kW","power","measurement"),
    "KW": ("kW","power","measurement"),
    "kWh": ("kWh","energy","total_increasing"),
    "Wh/kgK": ("Wh/kgK",None,"measurement"),
    "V": ("V","voltage","measurement"),
    "mV": ("mV","voltage","measurement"),
    "kV": ("kV","voltage","measurement"),
    "mA": ("mA","current","measurement"),
    "Hz": ("Hz","frequency","measurement"),
    "bar": ("bar","pressure","measurement"),
    "kg": ("kg","weight","measurement"),
    "l": ("L","volume_storage","measurement"),
    "l/h": ("L/h","volume_flow_rate","measurement"),
    "l/min": ("L/min","volume_flow_rate","measurement"),
    "h": ("h","duration","measurement"),
    "Min": ("min","duration","measurement"),
    "Sek": ("s","duration","measurement"),
    "Tage": ("d","duration","measurement"),
    "K": ("K","temperature","measurement"),
    "mm": ("mm","distance","measurement"),
}

# The user-curated erweitert CSV is the single source of truth (Beschreibung,
# Kategorie, Gate, Synonym, Schreib-FC, Multiplikator, …). Columns are looked up
# by header name so the file can be reordered without breaking generation.
rows = list(csv.reader(open(SRC_CURATED, encoding="utf-8-sig"), delimiter=";"))
hdr = rows[0]
col = {name: i for i, name in enumerate(hdr)}
ENUM_COLS = [col[str(n)] for n in range(0, 21) if str(n) in col]
regs = []
seen = set()
skipped = 0
for r in rows[1:]:
    def g(name, _r=r):
        i = col.get(name)
        return _r[i] if (i is not None and i < len(_r)) else ""

    desc = re.sub(r"\s+", " ", g("Beschreibung").replace("\n", " ").replace("\r", " ")).strip()
    typ = g("Typ").strip()
    if typ not in ("DAQ-ANA","DAQ-DIG","INT","INT32","FLOAT","WAHL","WPROG","TPROG","BITFIELD"):
        skipped += 1
        continue
    fc_write = g("Registertyp schreiben").strip()
    address = num(g("Adresse"))
    if address is None:
        skipped += 1
        continue
    raw_mult = num(g("Multiplikator"))
    # Scale comes from the (now filled) Multiplikator column; fall back to the
    # DAQ-ANA ×10 rule only if a row was left blank.
    scale = raw_mult if raw_mult is not None else (0.1 if typ == "DAQ-ANA" else 1)
    if address in SCALE_OVERRIDES:
        scale = SCALE_OVERRIDES[address]
    unit = g("Unit").strip() or None
    vmin, vmax, vinc = num(g("Min")), num(g("Max")), num(g("Inc"))
    labels = [(r[i].strip() if i < len(r) else "") for i in ENUM_COLS]
    options = {i: lbl for i, lbl in enumerate(labels) if lbl != ""}
    if address in ENUM_OVERRIDES:
        options = dict(ENUM_OVERRIDES[address])
    has_enum = len(options) > 0

    # register count
    count = {"FLOAT":2,"INT32":2,"TPROG":4,"WPROG":5}.get(typ,1)
    # writable only if OEM write-FC present (conservative policy)
    writable = fc_write == "6"

    # platform
    if typ == "BITFIELD":
        platform = "unsupported"  # bit-coded fields -> later
    elif typ == "DAQ-DIG":
        platform = "binary_sensor"
    elif typ in ("TPROG", "WPROG"):
        platform = "sensor"  # read-only decoded schedule
    elif writable and has_enum:
        platform = "select"
    elif writable:
        platform = "number"
    else:
        platform = "sensor"

    # value encoding
    if typ == "FLOAT":
        encoding = "float32"
    elif typ == "INT32":
        encoding = "int32"
    elif typ == "DAQ-DIG":
        encoding = "bool"
    elif typ == "TPROG":
        encoding = "tprog"
    elif typ == "WPROG":
        encoding = "wprog"
    else:
        encoding = "int16"

    if unit in UNIT_DC:
        unit, dc, state_class = UNIT_DC[unit]
    else:
        # Unknown unit: keep the raw label but assign no device_class, so HA
        # does not validate (and reject) the unit string.
        dc, state_class = None, None
    # enum/state sensors: no unit/scale meaning
    if has_enum and platform in ("sensor","binary_sensor"):
        dc, state_class, unit = None, None, None

    base = slugify(desc)
    key = f"{base}_{address}"
    if key in seen:
        continue
    seen.add(key)

    # key stays based on the original description (stable unique_id); the synonym
    # (OEM parameter/DAQ code) is prepended to the display name and kept as a field.
    synonym = g("Synonym").strip()
    # Clean display name (description only); the synonym stays as an attribute.
    name = desc

    # Category + Gate hierarchy come straight from the curated CSV columns.
    cat = g("Kategorie").strip() or category(desc)
    gate = g("Gate").strip()
    gate_values = [int(t) for t in g("Gate-aktiv-bei").split(",") if t.strip().isdigit()]
    basis = g("Basis").strip().lower() in ("1", "x", "ja", "true")

    entry = {
        "key": key,
        "synonym": synonym,
        "name": name,
        "address": address,
        "type": typ,
        "platform": platform,
        "count": count,
        "encoding": encoding,
        "scale": scale,
        "unit": unit,
        "device_class": dc,
        "state_class": state_class,
        "writable": writable,
        "category": cat,
        "gate": gate,
        "gate_values": gate_values,
        "basis": basis,
    }
    if has_enum:
        entry["options"] = {str(k): v for k, v in options.items()}
    if vmin is not None: entry["min"] = vmin
    if vmax is not None: entry["max"] = vmax
    if vinc is not None: entry["step"] = vinc
    regs.append(entry)

# Disambiguate identical display names (e.g. 5x "Boiler 1 Wochenuhr" blocks)
# by appending a running index. Keys/addresses stay unique on their own.
from collections import Counter, defaultdict
_name_counts = Counter(e["name"] for e in regs)
_seen: dict[str, int] = defaultdict(int)
for e in regs:
    if _name_counts[e["name"]] > 1:
        _seen_key = e["name"]
        _seen[_seen_key] += 1
        e["name"] = f"{_seen_key} {_seen[_seen_key]}"

json.dump(regs, open(OUT,"w",encoding="utf-8"), ensure_ascii=False, indent=1)
print("written", len(regs), "registers; skipped", skipped)
print("platforms:", Counter(e["platform"] for e in regs))
print("writable:", sum(1 for e in regs if e["writable"]))
print("categories:", Counter(e["category"] for e in regs))
