# Purdue Shade Navigation

A walking-route planner for Purdue University's West Lafayette campus. It finds the **shadiest** (or sunniest) path between buildings for any date and time, using real campus buildings, sidewalks and trees from OpenStreetMap.

> **Prototype:** building outlines, the walking network and tree locations are real (OpenStreetMap). Most building heights are estimated from building type, and tree heights and crown sizes are simulated, because the map doesn't record them.

## Features

- **Live shadows:** the sun's position is calculated for West Lafayette from the chosen date and time (Eastern time, with daylight saving). Buildings cast the exact shadow of their outline at their height, and trees cast elliptical crown shadows.
- **Seasons:** trees are in full leaf from May to mid-October, thin out in November, and are bare from late November through March. In winter only buildings give shade.
- **Shade-aware routing:** Dijkstra's algorithm on the real network of sidewalks, crosswalks, campus walks, stairs and streets, where each sunlit meter costs up to 5× a shaded one. A *Shortest ↔ Shadiest* slider sets how far to detour. Covered walkways, tunnels and corridors count as shaded, and streets with separate sidewalks cost slightly more so routes stay on the sidewalk.
- **Seek sun mode** for cold days, and an **Avoid stairs** option.
- **Search** 153 named buildings by name or building code (WALC, LWSN, ARMS…), or **tap anywhere** on the map to start or end there.
- **Day chart:** the share of the walk in shade from 5 AM to 10 PM for both the recommended and the shortest route, plus a "leave at…" suggestion when a nearby time is noticeably shadier.
- **Turn by turn:** each named stretch of the route, such as Hello Walk, 3rd St Mall or the sidewalk along University St, with its shade percentage.
- No build step and no dependencies: `index.html` plus a generated data file, `campus-data.js`.

## Run it

Open `index.html` in a browser, keeping `campus-data.js` in the same folder, or use the GitHub Pages site.

## Data

| Layer | Count | Source |
|---|---|---|
| Buildings | 735 | OpenStreetMap outlines. Heights: 10 mapped, 44 from floor counts, 681 estimated by building type |
| Trees | 3,731 | OpenStreetMap locations. Heights and crown sizes simulated with a fixed seed |
| Walkways and streets | ~157 km, 9,595 junctions | OpenStreetMap |
| Places to search | 153 | Named OpenStreetMap buildings, plus the Engineering Fountain |

Map data © [OpenStreetMap contributors](https://www.openstreetmap.org/copyright), available under the Open Database License (ODbL).

### Refreshing the data

`tools/build_campus_data.py` converts an Overpass export into `campus-data.js`.

1. Go to [overpass-turbo.eu](https://overpass-turbo.eu) and run:
   ```
   [out:json][timeout:60];
   (
     way["building"](40.4220,-86.9275,40.4360,-86.9080);
     way["highway"](40.4220,-86.9275,40.4360,-86.9080);
     node["natural"="tree"](40.4220,-86.9275,40.4360,-86.9080);
   );
   out geom;
   ```
2. Click **Export → GeoJSON → download**.
3. Run `python3 tools/build_campus_data.py export.geojson campus-data.js`.

The script clips the data to campus, converts coordinates to meters, estimates missing building heights, builds the walking graph (keeping its largest connected part), names unnamed sidewalks after the nearest street, and finds the entrances nearest each named building.

## How shade is computed

1. The sun's height and direction come from a standard solar-position formula, accurate to about a degree.
2. Each building is treated as a block of its height. Its shadow is the union of one parallelogram per wall facing away from the sun, which gives the exact shadow of that block.
3. Each tree crown is treated as a sphere, so its shadow is an ellipse stretched along the sun's direction.
4. Every path segment is checked for shade every 6 m, using a 24 m spatial grid so only nearby shadows are tested.

## Enabling GitHub Pages

In this repo: **Settings → Pages → Build and deployment → Source: Deploy from a branch → Branch: `main` / `(root)` → Save**.
The site will be published at `https://<your-username>.github.io/<repo-name>/`.
