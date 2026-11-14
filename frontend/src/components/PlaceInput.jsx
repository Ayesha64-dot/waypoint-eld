import { useEffect, useRef, useState } from "react";
import { reversePlace, searchPlaces } from "../lib/api.js";

/** Search-as-you-type location field. value = {label, lat?, lon?} */
export default function PlaceInput({ id, label, marker, value, onChange, error, allowGeolocate, placeholder }) {
  const [query, setQuery] = useState(value?.label || "");
  const [results, setResults] = useState([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(-1);
  const [loading, setLoading] = useState(false);
  const [locating, setLocating] = useState(false);
  const boxRef = useRef(null);
  const skipSearch = useRef(false);

  useEffect(() => {
    if ((value?.label || "") !== query) {
      skipSearch.current = true;
      setQuery(value?.label || "");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value?.label]);

  useEffect(() => {
    if (skipSearch.current) {
      skipSearch.current = false;
      return;
    }
    if (query.trim().length < 2) {
      setResults([]);
      return;
    }
    const ctrl = new AbortController();
    const t = setTimeout(async () => {
      setLoading(true);
      try {
        const r = await searchPlaces(query, ctrl.signal);
        setResults(r);
        setActive(r.length ? 0 : -1);
        setOpen(true);
      } catch {
        /* aborted or offline - keep typed text, backend will geocode it */
      } finally {
        setLoading(false);
      }
    }, 300);
    return () => {
      clearTimeout(t);
      ctrl.abort();
    };
  }, [query]);

  useEffect(() => {
    const close = (e) => boxRef.current && !boxRef.current.contains(e.target) && setOpen(false);
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const pick = (place) => {
    if (place.label !== query) {
      skipSearch.current = true;
      setQuery(place.label);
    }
    onChange(place);
    setOpen(false);
  };

  const onKey = (e) => {
    if (!open || !results.length) return;
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => (a + 1) % results.length);
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => (a - 1 + results.length) % results.length);
    } else if (e.key === "Enter" && active >= 0) {
      e.preventDefault();
      pick(results[active]);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  };

  const geolocate = () => {
    if (!navigator.geolocation) return;
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      async ({ coords }) => {
        try {
          const place = await reversePlace(coords.latitude.toFixed(5), coords.longitude.toFixed(5));
          pick(place);
        } catch {
          pick({ label: `${coords.latitude.toFixed(4)}, ${coords.longitude.toFixed(4)}`, lat: coords.latitude, lon: coords.longitude });
        } finally {
          setLocating(false);
        }
      },
      () => setLocating(false),
      { timeout: 8000 }
    );
  };

  const confirmed = value?.lat != null;

  return (
    <div className={`place ${error ? "has-error" : ""}`} ref={boxRef}>
      <label htmlFor={id} className="field-label">{label}</label>
      <div className="place-row">
        <span className={`place-marker ${marker}`} aria-hidden="true" />
        <input
          id={id}
          className="input"
          autoComplete="off"
          placeholder={placeholder}
          value={query}
          role="combobox"
          aria-expanded={open}
          aria-controls={`${id}-list`}
          aria-invalid={!!error}
          onChange={(e) => {
            setQuery(e.target.value);
            onChange({ label: e.target.value });
          }}
          onFocus={() => results.length && setOpen(true)}
          onKeyDown={onKey}
        />
        <span className="place-state" aria-hidden="true">
          {loading ? <span className="spinner" /> : confirmed ? <CheckIcon /> : null}
        </span>
        {allowGeolocate && (
          <button type="button" className="icon-btn" title="Use my current location" onClick={geolocate} disabled={locating}>
            {locating ? <span className="spinner" /> : <CrosshairIcon />}
          </button>
        )}
      </div>
      {error && <div className="field-error">{error}</div>}
      {open && results.length > 0 && (
        <ul className="suggestions" id={`${id}-list`} role="listbox">
          {results.map((r, i) => (
            <li
              key={`${r.label}-${i}`}
              role="option"
              aria-selected={i === active}
              className={i === active ? "active" : ""}
              onMouseDown={(e) => {
                e.preventDefault();
                pick(r);
              }}
              onMouseEnter={() => setActive(i)}
            >
              <PinIcon />
              <span>{r.label}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}

const CheckIcon = () => (
  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#0F8A5F" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round"><path d="M5 12l5 5L20 7" /></svg>
);
const CrosshairIcon = () => (
  <svg width="17" height="17" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round"><circle cx="12" cy="12" r="7" /><circle cx="12" cy="12" r="2" fill="currentColor" /><path d="M12 2v3M12 19v3M2 12h3M19 12h3" /></svg>
);
const PinIcon = () => (
  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2"><path d="M12 22s7-7.2 7-13a7 7 0 10-14 0c0 5.8 7 13 7 13z" /><circle cx="12" cy="9" r="2.5" /></svg>
);
