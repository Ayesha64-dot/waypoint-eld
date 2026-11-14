import { STOP } from "../lib/constants.js";
import { clock, dayShort, hm } from "../lib/format.js";

export default function Itinerary({ plan, active, onSelect }) {
  // interleave driving legs between stops for a readable run-sheet
  const drives = plan.timeline.filter((t) => t.kind === "drive");
  let di = 0;
  let lastDay = null;
  return (
    <ol className="itinerary">
      {plan.stops.map((s, i) => {
        const day = dayShort(s.arrival);
        const showDay = day !== lastDay;
        lastDay = day;
        const next = plan.stops[i + 1];
        const drive = next && drives[di] && drives[di].start === (s.departure || s.arrival) ? drives[di++] : null;
        const meta = STOP[s.type];
        return (
          <li key={i} className={i === active ? "active" : ""}>
            {showDay && <div className="it-day">{day}</div>}
            <button type="button" className="it-stop" onClick={() => onSelect(i)}>
              <span className="it-pin" style={{ "--c": meta.color }}>{meta.glyph}</span>
              <span className="it-body">
                <span className="it-top">
                  <b>{s.label}</b>
                  <span className="it-time">{clock(s.arrival)}{s.departure && s.duration_minutes ? ` – ${clock(s.departure)}` : ""}</span>
                </span>
                <span className="it-loc">{s.location}</span>
                <span className="it-meta">
                  {s.duration_label && <span>{s.duration_label}</span>}
                  <span>mile {Math.round(s.mile).toLocaleString()}</span>
                </span>
              </span>
            </button>
            {drive && (
              <div className="it-drive">
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M3 13h13l3-4h2v8h-2M3 13v4h2m0 0a2 2 0 104 0m-4 0a2 2 0 114 0m0 0h6m0 0a2 2 0 104 0m-4 0a2 2 0 114 0" /></svg>
                Drive {hm(drive.minutes)} · {Math.round(drive.miles).toLocaleString()} mi
              </div>
            )}
          </li>
        );
      })}
    </ol>
  );
}
