"""Generates wiring.svg: Pi 5 -> breadboard (holes, columns, rails) -> sensor modules.

Edit MODS to change modules; pins/columns are derived. Render PNG with Edge/Chrome headless.
"""
W, H = 1320, 900
PITCH, X0 = 40, 70                      # column pitch, x of column index 0
BX0, BX1 = 50, 1250                     # breadboard left/right
BTOP = 235                              # breadboard top edge
ROWS_TOP = [BTOP + 22 + 22 * i for i in range(5)]      # rows a-e
GAP_Y = BTOP + 22 + 22 * 4 + 32                        # centre channel
ROWS_BOT = [GAP_Y + 30 + 22 * i for i in range(5)]     # rows f-j
RAIL_3V3 = ROWS_BOT[-1] + 50
RAIL_GND = RAIL_3V3 + 28
BBOT = RAIL_GND + 28
PI_TOP = BBOT + 90
ROW_E = ROWS_TOP[-1]

RED, ORANGE, BLACK = "#dc2626", "#ea580c", "#111827"
MODS = [  # name, pi pin, gpio, vcc source, active level, wire colour, signal label
    ("PIR HC-SR501", 11, 17, "5V", "HIGH", "#eab308", "OUT"),
    ("Sound (red board)", 13, 27, "3V3", "LOW", "#16a34a", "DO"),
    ("Flame", 15, 22, "3V3", "LOW", "#2563eb", "DO"),
    ("IR obstacle FC-51", 16, 23, "3V3", "LOW", "#64748b", "OUT"),
    ("Rain (MH-RD board)", 18, 24, "3V3", "LOW", "#9333ea", "DO"),
    ("Vibration (blue)", 22, 25, "3V3", "LOW", "#78716c", "DO"),
]


def cx(col):  # column index -> x
    return X0 + col * PITCH


o = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" font-family="Segoe UI,Arial,sans-serif">',
     f'<rect width="{W}" height="{H}" fill="#ffffff"/>',
     '<text x="30" y="36" font-size="24" font-weight="700" fill="#111827">HomeAuto wiring: Raspberry Pi 5, breadboard, sensors</text>',
     '<text x="30" y="58" font-size="13" fill="#4b5563">Modules hang over the top edge with their 3 pins in row a. A wire in rows b-e of the same column is electrically the same point (columns a-e are joined). Pin order shown is illustrative: match your module\'s silkscreen labels.</text>']

# --- breadboard body
o.append(f'<rect x="{BX0}" y="{BTOP}" width="{BX1-BX0}" height="{BBOT-BTOP}" rx="8" fill="#f3efe6" stroke="#b8b09c" stroke-width="2"/>')
o.append(f'<rect x="{BX0+4}" y="{GAP_Y-10}" width="{BX1-BX0-8}" height="20" fill="#e2dccb"/>')
o.append(f'<text x="{BX0+10}" y="{GAP_Y+4}" font-size="10" fill="#8a8370">centre gap</text>')
# holes + column numbers + row letters
for c in range(30):
    x = cx(c)
    for y in ROWS_TOP + ROWS_BOT:
        o.append(f'<circle cx="{x}" cy="{y}" r="3.2" fill="#6b6659"/>')
    o.append(f'<text x="{x}" y="{GAP_Y+4}" font-size="10" text-anchor="middle" fill="#6b6659">{c+1}</text>')
for letter, y in zip("abcde", ROWS_TOP):
    o.append(f'<text x="{BX0+12}" y="{y+4}" font-size="10" fill="#8a8370">{letter}</text>')
for letter, y in zip("fghij", ROWS_BOT):
    o.append(f'<text x="{BX0+12}" y="{y+4}" font-size="10" fill="#8a8370">{letter}</text>')
# rails
for y, colr, lab in ((RAIL_3V3, RED, "3.3V  +"), (RAIL_GND, BLACK, "GND  -")):
    o.append(f'<line x1="{BX0+8}" y1="{y-12 if colr==RED else y+12}" x2="{BX1-8}" y2="{y-12 if colr==RED else y+12}" stroke="{colr}" stroke-width="2"/>')
    for x in range(BX0 + 60, BX1 - 20, 20):
        o.append(f'<circle cx="{x}" cy="{y}" r="3.2" fill="#6b6659"/>')
    o.append(f'<text x="{BX0+10}" y="{y+4}" font-size="11" font-weight="700" fill="{colr}">{lab}</text>')

# --- modules, wires
def wire(x1, y1, x2, y2, colr, w=3.5):
    o.append(f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{colr}" stroke-width="{w}" stroke-linecap="round"/>')
    o.append(f'<circle cx="{x1}" cy="{y1}" r="5" fill="{colr}"/><circle cx="{x2}" cy="{y2}" r="5" fill="{colr}"/>')


# Pi box
o.append(f'<rect x="40" y="{PI_TOP}" width="1230" height="120" rx="10" fill="#dcfce7" stroke="#15803d" stroke-width="2"/>')
o.append(f'<text x="60" y="{PI_TOP+106}" font-size="15" font-weight="700" fill="#14532d">Raspberry Pi 5 - GPIO header (pins used)</text>')


def terminal(x, name, pin, colr):
    o.append(f'<circle cx="{x}" cy="{PI_TOP}" r="6" fill="{colr}"/>')
    o.append(f'<text x="{x}" y="{PI_TOP+24}" font-size="11" text-anchor="middle" fill="#14532d">Pin {pin}</text>')
    o.append(f'<text x="{x}" y="{PI_TOP+38}" font-size="11" font-weight="700" text-anchor="middle" fill="#14532d">{name}</text>')


for g, (name, pin, gpio, vcc, active, col, sig) in enumerate(MODS):
    c_vcc, c_sig, c_gnd = 5 * g + 1, 5 * g + 2, 5 * g + 3
    xv, xs, xg = cx(c_vcc), cx(c_sig), cx(c_gnd)
    # module body above the board
    o.append(f'<rect x="{xs-85}" y="95" width="170" height="{BTOP-95}" rx="8" fill="#e0f2fe" stroke="#0369a1" stroke-width="1.5"/>')
    o.append(f'<text x="{xs}" y="120" font-size="14" font-weight="700" text-anchor="middle" fill="#0c4a6e">{name}</text>')
    o.append(f'<text x="{xs}" y="140" font-size="11" text-anchor="middle" fill="#0c4a6e">active {active} · AO unused</text>')
    o.append(f'<text x="{xs}" y="156" font-size="11" text-anchor="middle" fill="#0c4a6e">breadboard columns {c_vcc+1}-{c_gnd+1}</text>')
    for x, lab, colr in ((xv, "VCC", RED if vcc == "3V3" else ORANGE), (xs, sig, col), (xg, "GND", BLACK)):
        o.append(f'<text x="{x}" y="{BTOP-18}" font-size="11" font-weight="700" text-anchor="middle" fill="{colr}">{lab}</text>')
        o.append(f'<rect x="{x-2.5}" y="{BTOP-12}" width="5" height="{ROWS_TOP[0]-BTOP+12}" fill="#475569"/>')
    # wires (in row e, same column as the module pin)
    if vcc == "3V3":
        wire(xv, RAIL_3V3, xv, ROW_E, RED)
    else:
        wire(xv, PI_TOP, xv, ROW_E, ORANGE)          # 5V straight from the Pi
        terminal(xv, "5V", 2, ORANGE)
    wire(xg, RAIL_GND, xg, ROW_E, BLACK)
    wire(xs, PI_TOP, xs, ROW_E, col)
    terminal(xs, f"GPIO{gpio}", pin, col)

# Pi power -> rails (right end)
wire(1205, PI_TOP, 1205, RAIL_3V3, RED)
terminal(1205, "3V3", 1, RED)
wire(1237, PI_TOP, 1237, RAIL_GND, BLACK)
terminal(1237, "GND", 6, BLACK)

# legend
ly = PI_TOP + 150
o.append(f'<text x="30" y="{ly}" font-size="13" font-weight="700" fill="#111827">Wires (20 total: 9 Pi-to-breadboard + 11 rail-to-module)</text>')
o.append(f'<text x="30" y="{ly+20}" font-size="12" fill="#374151">Pi to breadboard (female-to-male): 3V3 to rail, GND to rail, 5V to PIR VCC column, plus 6 signal wires. Rails to modules (male-to-male): 5 VCC + 6 GND.</text>')
o.append(f'<text x="30" y="{ly+38}" font-size="12" fill="{RED}">Only the PIR uses 5V (direct from Pi pin 2, no 5V rail). Every other module stays on the 3.3V rail. Power the Pi off while wiring.</text>')
o.append('</svg>')
open("wiring.svg", "w", encoding="utf-8").write("\n".join(o))
