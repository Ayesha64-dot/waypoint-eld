# Loom walkthrough script (about 4 minutes)

**0:00 – 0:20 · Intro**
"Hi, this is Waypoint ELD. It's a Django and React app that takes a trip and gives back a compliant route plus the driver's daily log sheets, filled out and drawn."

**0:20 – 1:20 · Demo the inputs**
- Type a current location to show the autocomplete (Photon / OpenStreetMap). Point out the "use my location" button.
- Fill in the pickup and drop-off, or click the sample *Dallas → OKC → Los Angeles*.
- Drag the cycle slider and show the "hours available" readout.
- Open the optional log-header section and enter a driver name and carrier.
- Click **Plan trip**.

**1:20 – 2:20 · Demo the outputs**
- Summary: distance, drive time, trip duration, ETA, the compliance badge, and the colour-coded duty-status bar for the whole trip.
- Map: route line, S / P / D markers, rest (R), fuel (F), break (B) and restart (34) markers. Click an itinerary row and the map flies to that stop.
- Log sheets: step through Day 1, 2 and 3. Point out the 15-minute grid, the duty line, row totals adding to 24:00, remarks with city and state at every status change, miles driven today, and the 70-hr recap. Click **Print / PDF** to show the print layout.
- Optional: run the Seattle → Miami sample with 62 hrs used to show a **34-hr restart**.

**2:20 – 3:40 · Code tour**
- `backend/trips/hos.py`: the simulator loop. Each iteration checks, in order: 70-hr cycle (restart), 11-hr / 14-hr limits (10-hr reset), 8-hr driving (30-min break) and 1,000-mile fuel. Then it drives the largest chunk allowed by every limit. Mention the 2020 rule: the pickup or a fuel stop counts as the break.
- `validate_plan()`: an independent checker. Tests run the engine over many cycle and distance combinations and assert zero violations.
- `planner.py`: places stops on the polyline, splits the timeline at midnight, builds remarks and the recap.
- `services.py`: OSRM and Photon, no API keys, truck speed cap, offline fallback.
- `LogSheet.jsx`: the SVG grid. Show the `x(minute)` mapping and the single path that draws the duty line.

**3:40 – 4:00 · Wrap**
Cover the deployment (two Vercel projects, stateless Django API, no database), the test suite, and the stated assumptions.
