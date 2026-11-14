import { useState } from "react";
import PlaceInput from "./PlaceInput.jsx";
import { SAMPLE_TRIPS } from "../lib/constants.js";

export default function TripForm({ form, setForm, onSubmit, loading, errors }) {
  const [showDetails, setShowDetails] = useState(false);
  const set = (key) => (val) => setForm((f) => ({ ...f, [key]: val }));
  const cycle = Number(form.cycle) || 0;
  const available = Math.max(0, 70 - cycle);

  const loadSample = (s) =>
    setForm((f) => ({ ...f, current: s.current, pickup: s.pickup, dropoff: s.dropoff, cycle: s.cycle }));

  return (
    <form
      className="trip-form"
      onSubmit={(e) => {
        e.preventDefault();
        onSubmit();
      }}
      noValidate
    >
      <div className="form-section">
        <div className="section-head">
          <span className="eyebrow">01</span>
          <h2>Trip details</h2>
        </div>

        <div className="stops-stack">
          <span className="stack-line" aria-hidden="true" />
          <PlaceInput id="current" label="Current location" marker="m-start" placeholder="Where is the truck now?"
            value={form.current} onChange={set("current")} error={errors.current_location} allowGeolocate />
          <PlaceInput id="pickup" label="Pickup location" marker="m-pickup" placeholder="Shipper city or address"
            value={form.pickup} onChange={set("pickup")} error={errors.pickup_location} />
          <PlaceInput id="dropoff" label="Drop-off location" marker="m-dropoff" placeholder="Receiver city or address"
            value={form.dropoff} onChange={set("dropoff")} error={errors.dropoff_location} />
        </div>
      </div>

      <div className="form-section">
        <div className="section-head">
          <span className="eyebrow">02</span>
          <h2>Hours of service</h2>
        </div>
        <div className={`cycle ${errors.current_cycle_used ? "has-error" : ""}`}>
          <div className="cycle-top">
            <label htmlFor="cycle" className="field-label">Current cycle used</label>
            <div className="cycle-input">
              <input id="cycle" type="number" min="0" max="70" step="0.25" className="input input-num"
                value={form.cycle} onChange={(e) => set("cycle")(e.target.value)} />
              <span>hrs</span>
            </div>
          </div>
          <input type="range" min="0" max="70" step="0.5" value={cycle} className="range"
            style={{ "--pct": `${(Math.min(cycle, 70) / 70) * 100}%` }}
            onChange={(e) => set("cycle")(e.target.value)} aria-label="Current cycle used slider" />
          <div className="cycle-meta">
            <span><b>{+available.toFixed(2)}</b> of 70 hrs available</span>
            <span className="muted">70-hr / 8-day rule</span>
          </div>
          {errors.current_cycle_used && <div className="field-error">{errors.current_cycle_used}</div>}
        </div>

        <div className="field">
          <label htmlFor="start" className="field-label">Departure time</label>
          <input id="start" type="datetime-local" className="input" value={form.start}
            onChange={(e) => set("start")(e.target.value)} />
        </div>
      </div>

      <div className="form-section">
        <button type="button" className="disclosure" onClick={() => setShowDetails((s) => !s)} aria-expanded={showDetails}>
          <span className="eyebrow">03</span>
          <span>Log sheet header <em>(optional)</em></span>
          <svg className={showDetails ? "rot" : ""} width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5"><path d="M6 9l6 6 6-6" /></svg>
        </button>
        {showDetails && (
          <div className="details-grid">
            {[
              ["driver_name", "Driver name"],
              ["co_driver", "Co-driver"],
              ["carrier_name", "Carrier"],
              ["main_office", "Main office address"],
              ["truck_number", "Truck / trailer #"],
              ["shipping_doc", "Shipping doc / B/L #"],
            ].map(([k, l]) => (
              <div className="field" key={k}>
                <label htmlFor={k} className="field-label">{l}</label>
                <input id={k} className="input" value={form[k] || ""} onChange={(e) => set(k)(e.target.value)} />
              </div>
            ))}
          </div>
        )}
      </div>

      <button className="btn-primary" type="submit" disabled={loading}>
        {loading ? (<><span className="spinner light" /> Planning route…</>) : (<>Plan trip &amp; generate logs <span aria-hidden="true">→</span></>)}
      </button>

      <div className="samples">
        <span className="muted">Try a sample:</span>
        {SAMPLE_TRIPS.map((s) => (
          <button type="button" key={s.name} className="chip" onClick={() => loadSample(s)}>{s.name}</button>
        ))}
      </div>
    </form>
  );
}
