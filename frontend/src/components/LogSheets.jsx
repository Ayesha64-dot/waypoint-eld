import { useState } from "react";
import LogSheet from "./LogSheet.jsx";
import { dayShort } from "../lib/format.js";

export default function LogSheets({ days }) {
  const [active, setActive] = useState(0);
  const idx = Math.min(active, days.length - 1);
  return (
    <section className="logs" id="logs">
      <div className="logs-head">
        <div>
          <span className="eyebrow">ELD output</span>
          <h2>Daily log sheets</h2>
        </div>
        <div className="logs-actions">
          <div className="day-tabs" role="tablist">
            {days.map((d, i) => (
              <button key={d.date} role="tab" aria-selected={i === idx} className={i === idx ? "on" : ""} onClick={() => setActive(i)}>
                <b>Day {d.day}</b>
                <span>{dayShort(`${d.date}T00:00`)}</span>
              </button>
            ))}
          </div>
          <button className="btn-ghost" onClick={() => window.print()}>
            <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M6 9V2h12v7M6 18H4a2 2 0 01-2-2v-5a2 2 0 012-2h16a2 2 0 012 2v5a2 2 0 01-2 2h-2M6 14h12v8H6z" /></svg>
            Print / PDF all
          </button>
        </div>
      </div>
      <div className="sheets">
        {days.map((d, i) => <LogSheet key={d.date} day={d} total={days.length} hidden={i !== idx} />)}
      </div>
    </section>
  );
}
