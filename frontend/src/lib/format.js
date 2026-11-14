const DAYS = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

// Backend returns naive local ISO strings ("2026-11-13T06:00"); parse without TZ shifts.
export function parseLocal(iso) {
  const [d, t = "00:00"] = iso.split("T");
  const [y, m, day] = d.split("-").map(Number);
  const [hh, mm] = t.split(":").map(Number);
  return new Date(y, m - 1, day, hh, mm);
}

export function clock(iso) {
  const dt = parseLocal(iso);
  let h = dt.getHours();
  const ampm = h >= 12 ? "PM" : "AM";
  h = h % 12 || 12;
  return `${h}:${String(dt.getMinutes()).padStart(2, "0")} ${ampm}`;
}

export const dayShort = (iso) => {
  const dt = parseLocal(iso);
  return `${DAYS[dt.getDay()]}, ${MONTHS[dt.getMonth()]} ${dt.getDate()}`;
};

export const whenLabel = (iso) => `${dayShort(iso)} · ${clock(iso)}`;

export const miles = (n) => `${Math.round(n).toLocaleString()} mi`;

export function hm(minutes) {
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  if (!h) return `${m}m`;
  return m ? `${h}h ${String(m).padStart(2, "0")}m` : `${h}h`;
}

export function hoursDecimal(h) {
  return Number.isInteger(h) ? `${h}` : h.toFixed(2).replace(/0$/, "");
}

export function localInputValue(date = new Date()) {
  const pad = (n) => String(n).padStart(2, "0");
  return `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}T${pad(date.getHours())}:${pad(date.getMinutes())}`;
}
