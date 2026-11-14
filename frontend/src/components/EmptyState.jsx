export default function EmptyState() {
  return (
    <div className="empty">
      <svg viewBox="0 0 520 220" className="empty-art" aria-hidden="true">
        <defs>
          <pattern id="dots" width="14" height="14" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="1.3" fill="#14213D" opacity=".12" /></pattern>
        </defs>
        <rect width="520" height="220" rx="18" fill="url(#dots)" />
        <path d="M40 170 C 140 170, 150 60, 260 80 S 400 170, 480 60" fill="none" stroke="#0F8A5F" strokeWidth="5" strokeLinecap="round" strokeDasharray="1 0" />
        <path d="M40 170 C 140 170, 150 60, 260 80 S 400 170, 480 60" fill="none" stroke="#fff" strokeWidth="1.5" strokeDasharray="8 10" />
        {[[40, 170, "#14213D", "S"], [260, 80, "#E39B17", "P"], [480, 60, "#D1452F", "D"]].map(([cx, cy, c, t]) => (
          <g key={t}><circle cx={cx} cy={cy} r="17" fill={c} stroke="#fff" strokeWidth="3" /><text x={cx} y={cy + 5} textAnchor="middle" fill="#fff" fontWeight="800" fontSize="14" fontFamily="Archivo">{t}</text></g>
        ))}
        {[[150, 110, "#6C5CE7", "R"], [372, 128, "#2563EB", "F"]].map(([cx, cy, c, t]) => (
          <g key={t}><circle cx={cx} cy={cy} r="12" fill={c} stroke="#fff" strokeWidth="2.5" /><text x={cx} y={cy + 4} textAnchor="middle" fill="#fff" fontWeight="800" fontSize="11" fontFamily="Archivo">{t}</text></g>
        ))}
      </svg>
      <h2>Plan a compliant run in seconds</h2>
      <p>Enter where the truck is, the pickup and the drop-off, plus hours already used this cycle. You'll get the route, every required rest, break and fuel stop, and filled-in daily log sheets.</p>
      <ul className="rules">
        <li><b>11 hr</b> driving limit</li>
        <li><b>14 hr</b> duty window</li>
        <li><b>30 min</b> break after 8 hr</li>
        <li><b>70 hr</b> / 8-day cycle</li>
        <li><b>1,000 mi</b> fuel interval</li>
      </ul>
    </div>
  );
}
