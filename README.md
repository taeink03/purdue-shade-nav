# Purdue Shade Navigation

A prototype walking-route planner for Purdue University's West Lafayette campus that finds the **shadiest** (or sunniest) path between buildings for any date and time.

> **Prototype data:** building pins use real GPS coordinates. Trees, building footprints and heights, and therefore shade, are simulated.

## Features

- **Live shadows:** the sun's position is calculated for West Lafayette from the chosen date and time (Eastern time, with daylight saving). Every tree and building casts a shadow that moves with it.
- **Shade-aware routing:** Dijkstra's algorithm, where each sunlit meter costs up to 5× a shaded one. A *Shortest ↔ Shadiest* slider sets how far to detour.
- **Seek sun mode** for cold days, which flips the penalty.
- **Day chart:** the share of the walk in shade from 5 AM to 10 PM, for both the recommended and the shortest route, plus a "leave at…" suggestion when a nearby time is noticeably shadier.
- **Turn by turn:** each street or path on the route, with its shade percentage.
- **Map:** pan, pinch or Ctrl+scroll to zoom, and tap a building to start or end there.
- **Bring your own trees:** paste a JSON tree list into the page to replace the simulated ones.
- Single self-contained `index.html` with no build step and no dependencies (Google Fonts only).

## Run it

Open `index.html` in a browser, or visit the GitHub Pages site once it's enabled (see below).

## Data

| Layer | Status |
|---|---|
| Building pins (21 places) | 11 from published coordinates; 10 estimated from the official campus map grid (±50 m) |
| Walking network | 53 junctions and 79 segments approximating main streets and malls |
| Trees (~1,100) | Simulated: positions, heights and crown sizes generated from per-path canopy densities |
| Building footprints and heights | Simplified rectangles with assumed heights; the Bell Tower uses its real 160 ft |
| Sun position | Real astronomy (NOAA-style approximation) |

The full list of places, with coordinates and their source, is in the page under **About the data**.

### Tree JSON format

```json
[{"lat": 40.42610, "lng": -86.91500, "h": 14, "r": 5}]
```

`h` is the tree height in meters and `r` is the crown radius in meters.

## Enabling GitHub Pages

In this repo: **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: `main` / `(root)` → Save**.
The site will be published at `https://<your-username>.github.io/<repo-name>/`.
