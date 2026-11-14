import { forwardRef, useEffect, useImperativeHandle, useRef } from "react";
import L from "leaflet";
import { STOP } from "../lib/constants.js";
import { whenLabel } from "../lib/format.js";

function stopIcon(type, index) {
  const s = STOP[type] || STOP.start;
  const big = ["start", "pickup", "dropoff"].includes(type);
  const size = big ? 34 : 26;
  return L.divIcon({
    className: "stop-pin-wrap",
    html: `<div class="stop-pin ${big ? "big" : ""}" style="--c:${s.color}"><span>${s.glyph}</span></div>`,
    iconSize: [size, size],
    iconAnchor: [size / 2, size / 2],
    popupAnchor: [0, -size / 2],
  });
}

const RouteMap = forwardRef(function RouteMap({ plan, activeStop }, ref) {
  const el = useRef(null);
  const map = useRef(null);
  const layer = useRef(null);
  const markers = useRef([]);

  useImperativeHandle(ref, () => ({
    focus(i) {
      const m = markers.current[i];
      if (m && map.current) {
        map.current.flyTo(m.getLatLng(), Math.max(map.current.getZoom(), 9), { duration: 0.8 });
        m.openPopup();
      }
    },
    fit() {
      if (layer.current && map.current) map.current.fitBounds(layer.current.getBounds(), { padding: [40, 40] });
    },
  }));

  useEffect(() => {
    map.current = L.map(el.current, { zoomControl: false, scrollWheelZoom: true, attributionControl: true });
    L.control.zoom({ position: "bottomright" }).addTo(map.current);
    L.tileLayer("https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png", {
      maxZoom: 19,
      subdomains: "abcd",
      attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> &copy; <a href="https://carto.com/attributions">CARTO</a> · Routing <a href="https://project-osrm.org">OSRM</a>',
    }).addTo(map.current);
    map.current.setView([39.5, -98.35], 4);
    return () => map.current.remove();
  }, []);

  useEffect(() => {
    if (!map.current || !plan) return;
    if (layer.current) layer.current.remove();
    markers.current = [];
    const group = L.featureGroup();
    const line = plan.route.geometry;
    L.polyline(line, { color: "#14213D", weight: 8, opacity: 0.18, lineCap: "round" }).addTo(group);
    L.polyline(line, { color: "#0F8A5F", weight: 4.5, opacity: 0.95, lineCap: "round", lineJoin: "round" }).addTo(group);

    // draw the smaller stops first so start / pickup / drop-off sit on top
    const order = plan.stops.map((s, i) => i).sort((a, b) => {
      const big = (t) => (["start", "pickup", "dropoff"].includes(t) ? 1 : 0);
      return big(plan.stops[a].type) - big(plan.stops[b].type);
    });
    order.forEach((i) => {
      const s = plan.stops[i];
      const m = L.marker([s.lat, s.lon], { icon: stopIcon(s.type, i), riseOnHover: true })
        .bindPopup(
          `<div class="pop"><div class="pop-type" style="color:${STOP[s.type]?.color}">${s.label}</div>
           <div class="pop-loc">${escapeHtml(s.location)}</div>
           <div class="pop-meta">${whenLabel(s.arrival)}${s.duration_label ? ` · ${s.duration_label}` : ""}</div>
           <div class="pop-meta">Mile ${Math.round(s.mile).toLocaleString()}</div></div>`
        )
        .addTo(group);
      markers.current[i] = m;
    });
    group.addTo(map.current);
    layer.current = group;
    map.current.fitBounds(group.getBounds(), { padding: [40, 40] });
  }, [plan]);

  useEffect(() => {
    markers.current.forEach((m, i) => {
      const node = m?.getElement();
      if (node) node.classList.toggle("is-active", i === activeStop);
    });
  }, [activeStop, plan]);

  return <div ref={el} className="map" role="region" aria-label="Route map" />;
});

function escapeHtml(s = "") {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

export default RouteMap;
