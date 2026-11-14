import { STATUS } from "../lib/constants.js";

// ---- geometry of the drawn grid (SVG user units)
const W = 1100;
const LEFT = 150;          // row-label column
const GRID_W = 864;        // 24 h * 36 px
const RIGHT = LEFT + GRID_W;
const HOUR = GRID_W / 24;
const TOP = 30;            // hour-label band
const ROW_H = 36;
const ROWS = ["OFF", "SB", "D", "ON"];
const GRID_BOTTOM = TOP + ROW_H * ROWS.length;
const REMARK_TOP = GRID_BOTTOM + 30;
const H = REMARK_TOP + 178;
const INK = "#1D3A8A";

const x = (minute) => LEFT + (minute / 60) * HOUR;
const rowY = (status) => TOP + ROWS.indexOf(status) * ROW_H + ROW_H / 2;
const hhmm = (min) => `${Math.floor(min / 60)}:${String(Math.round(min % 60)).padStart(2, "0")}`;

const ROW_LABELS = {
  OFF: ["1. Off Duty"],
  SB: ["2. Sleeper", "Berth"],
  D: ["3. Driving"],
  ON: ["4. On Duty", "(not driving)"],
};

function hourLabel(h) {
  if (h === 0 || h === 24) return ["Mid-", "night"];
  if (h === 12) return ["Noon"];
  return [String(h % 12)];
}

function Grid({ day }) {
  const ticks = [];
  for (let r = 0; r < ROWS.length; r++) {
    const y0 = TOP + r * ROW_H;
    for (let q = 1; q < 96; q++) {
      if (q % 4 === 0) continue;
      const len = q % 2 === 0 ? 12 : 7;
      const xx = LEFT + (q * HOUR) / 4;
      ticks.push(<line key={`t${r}-${q}`} x1={xx} x2={xx} y1={y0} y2={y0 + len} className="tick" />);
      ticks.push(<line key={`b${r}-${q}`} x1={xx} x2={xx} y1={y0 + ROW_H} y2={y0 + ROW_H - len} className="tick" />);
    }
  }

  // duty-status line: horizontal runs joined by vertical transitions
  let path = "";
  day.entries.forEach((e, i) => {
    const y = rowY(e.status);
    path += `${i === 0 ? "M" : "L"}${x(e.start).toFixed(2)},${y} L${x(e.end).toFixed(2)},${y} `;
  });

  return (
    <g>
      {/* row bands */}
      {ROWS.map((s, r) => (
        <rect key={s} x={LEFT} y={TOP + r * ROW_H} width={GRID_W} height={ROW_H} className={r % 2 ? "band alt" : "band"} />
      ))}
      {/* status highlight under the line */}
      {day.entries.map((e, i) => (
        <rect key={`h${i}`} x={x(e.start)} width={Math.max(0, x(e.end) - x(e.start))}
          y={TOP + ROWS.indexOf(e.status) * ROW_H + 4} height={ROW_H - 8}
          fill={STATUS[e.status].color} opacity="0.14" rx="2" />
      ))}
      {ticks}
      {Array.from({ length: 25 }, (_, h) => (
        <line key={`h${h}`} x1={LEFT + h * HOUR} x2={LEFT + h * HOUR} y1={TOP - 4} y2={GRID_BOTTOM} className={h % 6 === 0 ? "hour major" : "hour"} />
      ))}
      {ROWS.map((s, r) => (
        <line key={`r${s}`} x1={LEFT - 150} x2={W} y1={TOP + r * ROW_H} y2={TOP + r * ROW_H} className="rowline" />
      ))}
      <line x1={LEFT - 150} x2={W} y1={GRID_BOTTOM} y2={GRID_BOTTOM} className="rowline strong" />

      {/* hour labels */}
      {Array.from({ length: 25 }, (_, h) => {
        const lines = hourLabel(h);
        return (
          <text key={`l${h}`} x={LEFT + h * HOUR} y={lines.length > 1 ? 10 : 18} className={`hour-label ${lines.length > 1 || h === 12 ? "strong" : ""}`}>
            {lines.map((t, i) => <tspan key={i} x={LEFT + h * HOUR} dy={i ? 10 : 0}>{t}</tspan>)}
          </text>
        );
      })}

      {/* row labels + totals */}
      {ROWS.map((s, r) => (
        <g key={`lab${s}`}>
          <text x={8} y={TOP + r * ROW_H + (ROW_LABELS[s].length > 1 ? 15 : 22)} className="row-label">
            {ROW_LABELS[s].map((t, i) => <tspan key={i} x={8} dy={i ? 13 : 0} className={i ? "sub" : ""}>{t}</tspan>)}
          </text>
          <text x={RIGHT + (W - RIGHT) / 2} y={TOP + r * ROW_H + 23} className="row-total">{hhmm(day.totals_minutes[s])}</text>
        </g>
      ))}
      <text x={RIGHT + (W - RIGHT) / 2} y={18} className="hour-label strong">Total hrs</text>
      <text x={RIGHT + (W - RIGHT) / 2} y={GRID_BOTTOM + 20} className="row-total grand">= 24:00</text>
      <line x1={RIGHT} x2={RIGHT} y1={TOP - 4} y2={GRID_BOTTOM} className="hour major" />

      <path d={path} fill="none" stroke={INK} strokeWidth="2.6" strokeLinejoin="miter" strokeLinecap="square" />
      {day.entries.slice(1).map((e, i) => (
        <circle key={`c${i}`} cx={x(e.start)} cy={rowY(e.status)} r="2.6" fill={INK} />
      ))}
    </g>
  );
}

function Remarks({ day }) {
  let lastLoc = null;
  return (
    <g>
      <text x={8} y={REMARK_TOP - 8} className="row-label">Remarks</text>
      <line x1={0} x2={W} y1={REMARK_TOP + 170} y2={REMARK_TOP + 170} className="rowline" />
      {day.remarks.map((r, i) => {
        const xx = x(r.minute);
        const sameLoc = r.location === lastLoc;
        lastLoc = r.location;
        const text = sameLoc ? r.note : `${r.location} — ${r.note}`;
        return (
          <g key={i}>
            <line x1={xx} x2={xx} y1={GRID_BOTTOM} y2={REMARK_TOP + 4} stroke={INK} strokeWidth="1.2" />
            <path d={`M${xx - 5},${REMARK_TOP + 4} L${xx},${REMARK_TOP + 9} L${xx + 5},${REMARK_TOP + 4}`} fill="none" stroke={INK} strokeWidth="1.2" />
            <text transform={`translate(${xx + 3},${REMARK_TOP + 16}) rotate(52)`} className="remark">
              <tspan className="remark-time">{r.time}</tspan> {truncate(text, 34)}
            </text>
          </g>
        );
      })}
    </g>
  );
}

const truncate = (s, n) => (s.length > n ? `${s.slice(0, n - 1)}…` : s);

export default function LogSheet({ day, total, hidden }) {
  const [y, m, d] = day.date.split("-");
  return (
    <article className={`sheet ${hidden ? "sheet-hidden" : ""}`} aria-label={`Daily log ${day.date}`}>
      <header className="sheet-head">
        <div className="sheet-title">
          <h3>Driver's Daily Log</h3>
          <span>24-hour period · Day {day.day} of {total}</span>
        </div>
        <div className="date-boxes" aria-label="Date">
          <div><b>{m}</b><span>month</span></div>
          <i>/</i>
          <div><b>{d}</b><span>day</span></div>
          <i>/</i>
          <div><b>{y}</b><span>year</span></div>
        </div>
        <div className="sheet-copy">Original — submit to carrier within 13 days<br />Duplicate — driver retains for 8 days</div>
      </header>

      <div className="sheet-route">
        <div><span>From:</span><b>{day.from_location}</b></div>
        <div><span>To:</span><b>{day.to_location}</b></div>
      </div>

      <div className="sheet-fields">
        <Field label="Total miles driving today" value={Math.round(day.total_miles).toLocaleString()} mono />
        <Field label="Truck / tractor & trailer no." value={day.truck_number} />
        <Field label="Name of carrier" value={day.carrier_name} />
        <Field label="Main office address" value={day.main_office} />
        <Field label="Driver" value={day.driver_name} script />
        <Field label="Co-driver" value={day.co_driver} />
      </div>

      <div className="sheet-graph">
        <svg viewBox={`0 0 ${W} ${H}`} className="log-svg" role="img"
          aria-label={`Duty status graph: off duty ${hhmm(day.totals_minutes.OFF)}, sleeper ${hhmm(day.totals_minutes.SB)}, driving ${hhmm(day.totals_minutes.D)}, on duty ${hhmm(day.totals_minutes.ON)}`}>
          <Grid day={day} />
          <Remarks day={day} />
        </svg>
      </div>

      <div className="sheet-bottom">
        <div className="shipping">
          <span className="lbl">Shipping documents</span>
          <span>DVL / Manifest / B/L no.: <b>{day.shipping_doc || "—"}</b></span>
          <span className="muted small">Enter name of place you reported and where released from work and when and where each change of duty occurred.</span>
        </div>
        <div className="recap">
          <span className="lbl">Recap · 70 hr / 8 day</span>
          <div className="recap-grid">
            <div><b>{hhmm(day.totals_minutes.D + day.totals_minutes.ON)}</b><span>On duty today<br />(lines 3 + 4)</span></div>
            <div><b>{day.cycle_used_end_hours.toFixed(2)}</b><span>Total on duty<br />last 8 days</span></div>
            <div className={day.cycle_available_hours < 11 ? "warn" : ""}><b>{day.cycle_available_hours.toFixed(2)}</b><span>Available<br />tomorrow</span></div>
          </div>
        </div>
      </div>

      <details className="remark-table">
        <summary>Duty status changes ({day.remarks.length})</summary>
        <table>
          <thead><tr><th>Time</th><th>Status</th><th>Location</th><th>Activity</th></tr></thead>
          <tbody>
            {day.remarks.map((r, i) => (
              <tr key={i}>
                <td className="mono">{r.time}</td>
                <td><span className="status-dot" style={{ background: STATUS[r.status].color }} />{STATUS[r.status].label}</td>
                <td>{r.location}</td>
                <td>{r.note}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </article>
  );
}

function Field({ label, value, mono, script }) {
  return (
    <div className="sheet-field">
      <b className={`${mono ? "mono" : ""} ${script ? "script" : ""}`}>{value || " "}</b>
      <span>{label}</span>
    </div>
  );
}
