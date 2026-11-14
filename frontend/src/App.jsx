import { useRef, useState } from "react";
import TripForm from "./components/TripForm.jsx";
import RouteMap from "./components/RouteMap.jsx";
import Summary from "./components/Summary.jsx";
import Itinerary from "./components/Itinerary.jsx";
import LogSheets from "./components/LogSheets.jsx";
import EmptyState from "./components/EmptyState.jsx";
import { planTrip } from "./lib/api.js";
import { localInputValue } from "./lib/format.js";

function defaultStart() {
  const d = new Date();
  d.setMinutes(0, 0, 0);
  d.setHours(d.getHours() + 1);
  return localInputValue(d);
}

const toPayloadPlace = (p) => (p?.lat != null ? p : p?.label || "");

export default function App() {
  const [form, setForm] = useState({
    current: { label: "" },
    pickup: { label: "" },
    dropoff: { label: "" },
    cycle: 0,
    start: defaultStart(),
  });
  const [plan, setPlan] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [errors, setErrors] = useState({});
  const [activeStop, setActiveStop] = useState(null);
  const mapRef = useRef(null);

  const submit = async () => {
    const fieldErrors = {};
    if (!form.current?.label?.trim()) fieldErrors.current_location = "Enter the truck's current location.";
    if (!form.pickup?.label?.trim()) fieldErrors.pickup_location = "Enter a pickup location.";
    if (!form.dropoff?.label?.trim()) fieldErrors.dropoff_location = "Enter a drop-off location.";
    const cycle = Number(form.cycle);
    if (form.cycle === "" || Number.isNaN(cycle) || cycle < 0 || cycle > 70)
      fieldErrors.current_cycle_used = "Enter hours between 0 and 70.";
    setErrors(fieldErrors);
    if (Object.keys(fieldErrors).length) return;

    setLoading(true);
    setError(null);
    try {
      const result = await planTrip({
        current_location: toPayloadPlace(form.current),
        pickup_location: toPayloadPlace(form.pickup),
        dropoff_location: toPayloadPlace(form.dropoff),
        current_cycle_used: cycle,
        start_time: form.start || undefined,
        driver_name: form.driver_name, co_driver: form.co_driver, carrier_name: form.carrier_name,
        main_office: form.main_office, truck_number: form.truck_number, shipping_doc: form.shipping_doc,
      });
      setPlan(result);
      setActiveStop(null);
      requestAnimationFrame(() => document.getElementById("results")?.scrollIntoView({ behavior: "smooth", block: "start" }));
    } catch (e) {
      if (e.field) setErrors({ [e.field]: e.message });
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  const selectStop = (i) => {
    setActiveStop(i);
    mapRef.current?.focus(i);
  };

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <svg width="30" height="30" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="8" fill="#14213D" /><path d="M8 22 L16 8 L24 22" stroke="#F2B33D" strokeWidth="3.5" fill="none" strokeLinecap="round" strokeLinejoin="round" /></svg>
          <div>
            <b>Waypoint ELD</b>
            <span>HOS trip planner &amp; log generator</span>
          </div>
        </div>
        <div className="topbar-tags">
          <span>Property-carrying</span>
          <span>70 hr / 8 day</span>
          <span>FMCSA §395</span>
        </div>
      </header>

      <main className="layout">
        <aside className="panel">
          <TripForm form={form} setForm={setForm} onSubmit={submit} loading={loading} errors={errors} />
          {error && <div className="alert" role="alert">{error}</div>}
          <p className="assumptions">
            Assumes no adverse conditions, 1 hr on duty at pickup and drop-off, 30 min fueling every ≤1,000 mi,
            10-hr resets logged in the sleeper berth. Truck speeds capped at a 55 mph average.
          </p>
        </aside>

        <section className="content" id="results">
          {!plan && !loading && <EmptyState />}
          {loading && !plan && <Loading />}
          {plan && (
            <div className={`results ${loading ? "is-loading" : ""}`}>
              <Summary plan={plan} />
              <div className="map-row">
                <div className="map-card">
                  <RouteMap ref={mapRef} plan={plan} activeStop={activeStop} />
                  <button className="fit-btn" onClick={() => mapRef.current?.fit()}>Fit route</button>
                </div>
                <div className="itin-card">
                  <div className="card-head">
                    <h3>Stops &amp; rests</h3>
                    <span className="muted">{plan.stops.length} events</span>
                  </div>
                  <Itinerary plan={plan} active={activeStop} onSelect={selectStop} />
                </div>
              </div>
              <LogSheets days={plan.days} />
            </div>
          )}
        </section>
      </main>
    </div>
  );
}

function Loading() {
  return (
    <div className="loading">
      <div className="road"><span className="truck">
        <svg width="54" height="30" viewBox="0 0 54 30"><rect x="1" y="4" width="32" height="18" rx="2" fill="#14213D" /><path d="M33 9h10l7 7v6H33z" fill="#F2B33D" /><circle cx="11" cy="25" r="4" fill="#333" stroke="#fff" strokeWidth="2" /><circle cx="42" cy="25" r="4" fill="#333" stroke="#fff" strokeWidth="2" /></svg>
      </span></div>
      <p>Routing and checking hours of service…</p>
    </div>
  );
}
