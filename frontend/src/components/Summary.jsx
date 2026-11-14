import { STATUS } from "../lib/constants.js";
import { clock, dayShort, hm, miles } from "../lib/format.js";

export default function Summary({ plan }) {
  const s = plan.summary;
  const stats = [
    { k: "Total distance", v: miles(s.total_miles), sub: `${miles(s.miles_to_pickup)} to pickup · ${miles(s.miles_to_dropoff)} loaded` },
    { k: "Driving time", v: s.driving_label, sub: `${hm(s.on_duty_minutes)} on duty, not driving` },
    { k: "Trip duration", v: s.trip_label, sub: `${s.log_days} log ${s.log_days === 1 ? "sheet" : "sheets"}` },
    { k: "Arrives", v: clock(s.end_time), sub: dayShort(s.end_time) },
  ];
  const stops = [
    ["rests", "10-hr rests", s.rests],
    ["breaks", "30-min breaks", s.breaks],
    ["fuel", "Fuel stops", s.fuel_stops],
    ["restarts", "34-hr restarts", s.restarts],
  ];
  return (
    <section className="summary">
      <div className="stats">
        {stats.map((x) => (
          <div className="stat" key={x.k}>
            <span className="stat-k">{x.k}</span>
            <span className="stat-v">{x.v}</span>
            <span className="stat-sub">{x.sub}</span>
          </div>
        ))}
      </div>
      <div className="summary-row">
        <div className={`compliance ${s.compliant ? "ok" : "bad"}`}>
          <span className="dot" />
          {s.compliant ? "HOS compliant plan" : `${s.violations.length} HOS issue(s)`}
          <span className="muted"> · 70 hr/8 day · cycle {s.cycle_used_start_hours}h → {s.cycle_used_end_hours}h</span>
        </div>
        <div className="stop-counts">
          {stops.map(([key, label, n]) => (
            <span key={key} className={n ? "" : "zero"}><b>{n}</b> {label}</span>
          ))}
        </div>
      </div>
      {s.route_source === "estimate" && (
        <div className="notice">Live routing was unavailable, so distances are estimated (straight-line × 1.2 at 50 mph).</div>
      )}
      <TripBar plan={plan} />
    </section>
  );
}

function TripBar({ plan }) {
  const total = plan.summary.trip_minutes;
  return (
    <div className="tripbar-wrap">
      <div className="tripbar" role="img" aria-label="Trip duty-status timeline">
        {plan.timeline.map((t, i) => (
          <span key={i} className="tb-seg" title={`${t.label} · ${t.duration_label} · ${t.location}`}
            style={{ width: `${(t.minutes / total) * 100}%`, background: STATUS[t.status].color }} />
        ))}
      </div>
      <div className="legend">
        {Object.entries(STATUS).map(([k, v]) => (
          <span key={k}><i style={{ background: v.color }} />{v.label}</span>
        ))}
      </div>
    </div>
  );
}
