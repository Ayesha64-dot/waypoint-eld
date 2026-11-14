export const STATUS = {
  OFF: { label: "Off Duty", short: "OFF", color: "#8A94A6" },
  SB: { label: "Sleeper Berth", short: "SB", color: "#6C5CE7" },
  D: { label: "Driving", short: "D", color: "#0F8A5F" },
  ON: { label: "On Duty (Not Driving)", short: "ON", color: "#E39B17" },
};

export const STOP = {
  start: { label: "Start", color: "#14213D", glyph: "S" },
  pickup: { label: "Pickup", color: "#E39B17", glyph: "P" },
  dropoff: { label: "Drop-off", color: "#D1452F", glyph: "D" },
  fuel: { label: "Fuel stop", color: "#2563EB", glyph: "F" },
  break: { label: "30-min break", color: "#0EA5A4", glyph: "B" },
  rest: { label: "10-hr rest", color: "#6C5CE7", glyph: "R" },
  restart: { label: "34-hr restart", color: "#9D174D", glyph: "34" },
};

export const SAMPLE_TRIPS = [
  {
    name: "Dallas → OKC → Los Angeles",
    current: { label: "Dallas, TX", lat: 32.7767, lon: -96.797 },
    pickup: { label: "Oklahoma City, OK", lat: 35.4676, lon: -97.5164 },
    dropoff: { label: "Los Angeles, CA", lat: 34.0522, lon: -118.2437 },
    cycle: 18,
  },
  {
    name: "Chicago → Indianapolis → Atlanta",
    current: { label: "Chicago, IL", lat: 41.8781, lon: -87.6298 },
    pickup: { label: "Indianapolis, IN", lat: 39.7684, lon: -86.1581 },
    dropoff: { label: "Atlanta, GA", lat: 33.749, lon: -84.388 },
    cycle: 40,
  },
  {
    name: "Seattle → Portland → Miami",
    current: { label: "Seattle, WA", lat: 47.6062, lon: -122.3321 },
    pickup: { label: "Portland, OR", lat: 45.5152, lon: -122.6784 },
    dropoff: { label: "Miami, FL", lat: 25.7617, lon: -80.1918 },
    cycle: 62,
  },
];
