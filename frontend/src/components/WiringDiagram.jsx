// Breadboard wiring diagram drawn from /api/wiring data (stays in sync with pinmap.py).
// Layout: modules hang over the top edge with pins in row a; wires go in rows b-e of the
// same column (columns a-e are joined). Rails + Pi at the bottom.

const PITCH = 40;
const X0 = 70;
const RED = "#dc2626";
const ORANGE = "#ea580c";
const BLACK = "#111827";
const SIGNAL_COLORS = ["#eab308", "#16a34a", "#2563eb", "#64748b", "#9333ea", "#78716c", "#0d9488", "#be123c"];

const cx = (col) => X0 + col * PITCH;

function Wire({ x1, y1, x2, y2, color }) {
  return (
    <g>
      <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeWidth="3.5" strokeLinecap="round" />
      <circle cx={x1} cy={y1} r="5" fill={color} />
      <circle cx={x2} cy={y2} r="5" fill={color} />
    </g>
  );
}

export default function WiringDiagram({ wiring }) {
  const { modules, power, columns_total: ncols } = wiring;
  const BX0 = 50;
  const BX1 = cx(ncols - 1) + 20;
  const W = BX1 + 70;
  const BTOP = 235;
  const rowsTop = [0, 1, 2, 3, 4].map((i) => BTOP + 22 + 22 * i);
  const gapY = rowsTop[4] + 32;
  const rowsBot = [0, 1, 2, 3, 4].map((i) => gapY + 30 + 22 * i);
  const rail3v3 = rowsBot[4] + 50;
  const railGnd = rail3v3 + 28;
  const bBot = railGnd + 28;
  const piTop = bBot + 90;
  const rowE = rowsTop[4];
  const H = piTop + 150;
  const pin = (name) => power.find((p) => p.name === name)?.physical_pin;

  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="wiring-svg" role="img" aria-label="Breadboard wiring diagram" fontFamily="Segoe UI, Arial, sans-serif">
      <rect width={W} height={H} fill="#ffffff" />

      {/* breadboard body */}
      <rect x={BX0} y={BTOP} width={BX1 - BX0} height={bBot - BTOP} rx="8" fill="#f3efe6" stroke="#b8b09c" strokeWidth="2" />
      <rect x={BX0 + 4} y={gapY - 10} width={BX1 - BX0 - 8} height="20" fill="#e2dccb" />
      {Array.from({ length: ncols }, (_, c) => (
        <g key={c}>
          {[...rowsTop, ...rowsBot].map((y) => (
            <circle key={y} cx={cx(c)} cy={y} r="3.2" fill="#6b6659" />
          ))}
          <text x={cx(c)} y={gapY + 4} fontSize="10" textAnchor="middle" fill="#6b6659">{c + 1}</text>
        </g>
      ))}
      {"abcde".split("").map((l, i) => (
        <text key={l} x={BX0 + 12} y={rowsTop[i] + 4} fontSize="10" fill="#8a8370">{l}</text>
      ))}
      {"fghij".split("").map((l, i) => (
        <text key={l} x={BX0 + 12} y={rowsBot[i] + 4} fontSize="10" fill="#8a8370">{l}</text>
      ))}

      {/* rails */}
      {[[rail3v3, RED, "3.3V  +", rail3v3 - 12], [railGnd, BLACK, "GND  -", railGnd + 12]].map(([y, color, label, line]) => (
        <g key={label}>
          <line x1={BX0 + 8} y1={line} x2={BX1 - 8} y2={line} stroke={color} strokeWidth="2" />
          {Array.from({ length: Math.floor((BX1 - 20 - (BX0 + 60)) / 20) }, (_, i) => (
            <circle key={i} cx={BX0 + 60 + i * 20} cy={y} r="3.2" fill="#6b6659" />
          ))}
          <text x={BX0 + 10} y={y + 4} fontSize="11" fontWeight="700" fill={color}>{label}</text>
        </g>
      ))}

      {/* Pi box */}
      <rect x="40" y={piTop} width={BX1 - 20} height="120" rx="10" fill="#dcfce7" stroke="#15803d" strokeWidth="2" />
      <text x="60" y={piTop + 106} fontSize="15" fontWeight="700" fill="#14532d">Raspberry Pi 5 - GPIO header (pins used)</text>

      {/* modules + wires */}
      {modules.map((m, i) => {
        const c = m.columns;
        const xv = cx(c.vcc - 1);
        const xs = cx(c.signal - 1);
        const xg = cx(c.gnd - 1);
        const sigColor = SIGNAL_COLORS[i % SIGNAL_COLORS.length];
        const vccColor = m.vcc === "5V" ? ORANGE : RED;
        return (
          <g key={m.key}>
            <rect x={xs - 85} y="20" width="170" height={BTOP - 20} rx="8" fill="#e0f2fe" stroke="#0369a1" strokeWidth="1.5" />
            <text x={xs} y="46" fontSize="14" fontWeight="700" textAnchor="middle" fill="#0c4a6e">{m.label}</text>
            <text x={xs} y="66" fontSize="11" textAnchor="middle" fill="#0c4a6e">active {m.active} · AO unused</text>
            <text x={xs} y="82" fontSize="11" textAnchor="middle" fill="#0c4a6e">columns {c.vcc}-{c.gnd}</text>
            {[[xv, "VCC", vccColor], [xs, m.signal_label, sigColor], [xg, "GND", BLACK]].map(([x, label, color]) => (
              <g key={label}>
                <text x={x} y={BTOP - 18} fontSize="11" fontWeight="700" textAnchor="middle" fill={color}>{label}</text>
                <rect x={x - 2.5} y={BTOP - 12} width="5" height={rowsTop[0] - BTOP + 12} fill="#475569" />
              </g>
            ))}
            {m.vcc === "5V" ? (
              <>
                <Wire x1={xv} y1={piTop} x2={xv} y2={rowE} color={ORANGE} />
                <circle cx={xv} cy={piTop} r="6" fill={ORANGE} />
                <text x={xv} y={piTop + 24} fontSize="11" textAnchor="middle" fill="#14532d">Pin {pin("5V")}</text>
                <text x={xv} y={piTop + 38} fontSize="11" fontWeight="700" textAnchor="middle" fill="#14532d">5V</text>
              </>
            ) : (
              <Wire x1={xv} y1={rail3v3} x2={xv} y2={rowE} color={RED} />
            )}
            <Wire x1={xg} y1={railGnd} x2={xg} y2={rowE} color={BLACK} />
            <Wire x1={xs} y1={piTop} x2={xs} y2={rowE} color={sigColor} />
            <circle cx={xs} cy={piTop} r="6" fill={sigColor} />
            <text x={xs} y={piTop + 24} fontSize="11" textAnchor="middle" fill="#14532d">Pin {m.physical_pin}</text>
            <text x={xs} y={piTop + 38} fontSize="11" fontWeight="700" textAnchor="middle" fill="#14532d">GPIO{m.gpio}</text>
          </g>
        );
      })}

      {/* Pi power -> rails */}
      <Wire x1={BX1 - 45} y1={piTop} x2={BX1 - 45} y2={rail3v3} color={RED} />
      <circle cx={BX1 - 45} cy={piTop} r="6" fill={RED} />
      <text x={BX1 - 45} y={piTop + 24} fontSize="11" textAnchor="middle" fill="#14532d">Pin {pin("3V3")}</text>
      <text x={BX1 - 45} y={piTop + 38} fontSize="11" fontWeight="700" textAnchor="middle" fill="#14532d">3V3</text>
      <Wire x1={BX1 - 13} y1={piTop} x2={BX1 - 13} y2={railGnd} color={BLACK} />
      <circle cx={BX1 - 13} cy={piTop} r="6" fill={BLACK} />
      <text x={BX1 - 13} y={piTop + 24} fontSize="11" textAnchor="middle" fill="#14532d">Pin {pin("GND")}</text>
      <text x={BX1 - 13} y={piTop + 38} fontSize="11" fontWeight="700" textAnchor="middle" fill="#14532d">GND</text>
    </svg>
  );
}
