/** Simple illustrations of each sensor module (inline SVG, no image files to ship). */

const Pins = ({ x, y = 62, n = 3 }) =>
  Array.from({ length: n }, (_, i) => <rect key={i} x={x + i * 9} y={y} width="4" height="10" rx="1" fill="#d9b44a" />);

const Board = ({ color, children }) => (
  <>
    <rect x="6" y="8" width="108" height="56" rx="5" fill={color} />
    <circle cx="14" cy="16" r="3" fill="#0b1220" opacity=".55" />
    <circle cx="106" cy="16" r="3" fill="#0b1220" opacity=".55" />
    {children}
  </>
);

const Pot = ({ x, y }) => (
  <>
    <rect x={x} y={y} width="20" height="20" rx="2" fill="#2f6fdb" />
    <circle cx={x + 10} cy={y + 10} r="6" fill="#cfd8e3" />
    <line x1={x + 6} y1={y + 10} x2={x + 14} y2={y + 10} stroke="#556" strokeWidth="1.5" />
  </>
);

const Chip = ({ x, y }) => (
  <>
    <rect x={x} y={y} width="22" height="9" rx="1" fill="#222" />
    <circle cx={x + 3.5} cy={y + 4.5} r="1" fill="#777" />
  </>
);

const Led = ({ x, y, color }) => <rect x={x} y={y} width="6" height="4" rx="1" fill={color} />;

const DRAWINGS = {
  // PIR: green board with a white Fresnel dome
  motion: (
    <>
      <Board color="#1f8a4c">
        <circle cx="46" cy="34" r="22" fill="#e8ecef" />
        <circle cx="46" cy="34" r="16" fill="#f7f9fa" stroke="#cfd6db" />
        <circle cx="46" cy="34" r="8" fill="#e8ecef" stroke="#cfd6db" />
        <Pot x={78} y={14} />
        <Pot x={78} y={38} />
        <Pins x={52} />
      </Board>
    </>
  ),
  // Sound: red LM393 board with a microphone can
  sound: (
    <>
      <Board color="#c0392b">
        <circle cx="38" cy="34" r="16" fill="#9aa4ad" />
        <circle cx="38" cy="34" r="10" fill="#2b2f33" />
        <circle cx="38" cy="34" r="3" fill="#555c63" />
        <Pot x={70} y={12} />
        <Chip x={72} y={40} />
        <Led x={100} y={44} color="#7CFC8A" />
        <Pins x={36} />
      </Board>
    </>
  ),
  // Flame: blue board with a clear IR photodiode
  flame: (
    <>
      <Board color="#2457b8">
        <rect x="24" y="14" width="10" height="26" rx="5" fill="#1a1a1a" />
        <rect x="26" y="16" width="6" height="22" rx="3" fill="#3a2a2a" />
        <Pot x={52} y={12} />
        <Chip x={52} y={40} />
        <Led x={84} y={44} color="#ff6b6b" />
        <Pins x={36} />
      </Board>
    </>
  ),
  // IR obstacle FC-51: two domes (emitter clear, receiver dark)
  obstacle: (
    <>
      <Board color="#2457b8">
        <ellipse cx="28" cy="26" rx="8" ry="11" fill="#e9eef2" />
        <ellipse cx="50" cy="26" rx="8" ry="11" fill="#1c1c1c" />
        <Pot x={72} y={12} />
        <Chip x={70} y={40} />
        <Led x={100} y={44} color="#7CFC8A" />
        <Pins x={36} />
      </Board>
    </>
  ),
  // Rain MH-RD: dark sensing plate with copper traces
  rain: (
    <>
      <rect x="6" y="6" width="68" height="60" rx="4" fill="#26303a" />
      {Array.from({ length: 6 }, (_, i) => (
        <path key={i} d={i % 2 ? "M12 " + (14 + i * 9) + "H68" : "M12 " + (14 + i * 9) + "H62"} stroke="#d6a65a" strokeWidth="3" fill="none" strokeLinecap="round" />
      ))}
      <rect x="82" y="16" width="32" height="40" rx="4" fill="#2457b8" />
      <Pot x={88} y={20} />
      <Chip x={86} y={44} />
      <Pins x={87} y={56} />
    </>
  ),
  // Vibration: blue board with a spring/switch can
  vibration: (
    <>
      <Board color="#2457b8">
        <rect x="22" y="22" width="34" height="14" rx="7" fill="#c8cfd6" />
        <path d="M28 29q3-6 6 0t6 0t6 0" stroke="#556" strokeWidth="1.8" fill="none" />
        <Pot x={70} y={12} />
        <Chip x={68} y={40} />
        <Led x={98} y={44} color="#7CFC8A" />
        <Pins x={36} />
      </Board>
    </>
  ),
};

export default function SensorImage({ kind, label }) {
  const drawing = DRAWINGS[kind];
  if (!drawing) return null;
  return (
    <svg className="sensor-img" viewBox="0 0 120 72" role="img" aria-label={`${label} module`}>
      {drawing}
    </svg>
  );
}
