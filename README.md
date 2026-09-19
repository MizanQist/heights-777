# Heights 777

Web brochure for Heights 777 — eighteen one- and two-bedroom residences on seven storeys at Plot 777, CAD Zone A07, Parakou Street, Wuse II, Abuja FCT.

Seven pages, one file: `index.html` carries the markup, styles and interactions; `assets/` holds the visualisations and the line-art plans and section exported from the architectural drawings (October 2025). Fonts load from Google Fonts (Bodoni Moda, Jost).

## Location map

The location page carries an interactive map built on [Leaflet](https://leafletjs.com) 1.9.4, vendored in `assets/leaflet/`, which loads only when the page scrolls near. Street tiles come from OpenStreetMap (desaturated and warmed with a CSS filter to sit with the palette) and the aerial view from Esri World Imagery; both need the network and both must keep their attribution. `assets/map-data.js` holds the indicative plot outline, the landmarks, the highlighted streets (OpenStreetMap geometry, where Parakou Street is mapped as Parakou Crescent) and the driving routes from the gate, routed with OSRM at build time by `tools/map/build_data.py` from the extracts beside it. Edit the `LANDMARKS` list there and re-run it (it needs the network) to change the places shown; group names and drive times are in the `GROUPS` object inside the map script in `index.html`.

## Print edition

`heights-777-brochure.pdf` is a twelve-sheet A4 landscape edition of the site, built by `tools/make_pdf.py` (Python 3 with Playwright and Pillow). The script lifts the design tokens, component rules, the floor-stack drawing, the `ROOMS` markers, the metre site plan, the specification and the contact block from `index.html`, writes a static `tools/print/print.html`, and prints it with headless Chromium, so the PDF never drifts from the site. Interactive states are replaced by complete static ones: the noon-to-dusk slider becomes the two views side by side, the floor stack gets a level list and a level-by-level page, the plan tabs become two plan sheets with the numbered markers and grouped legend, and the neighbourhood map becomes a screenshot of the site's own Leaflet map (`--maps` re-renders it; it needs the network for tiles). Drawings are flattened onto the panel colour so the PDF carries no soft masks, and the renders are re-encoded at print size in `tools/print/`. Re-run the script after any change to the site or its assets.

## Hosting

The site is static. On GitHub Pages, serve the `main` branch from `/` — `.nojekyll` is included so nothing is processed. `robots.txt` and the page's robots meta keep the brochure out of search results; remove both when the development goes public.

## Editing

- Copy and figures live in `index.html`; the floor-stack text is in the `LEVELS` array near the top of the script.
- The floor plans are text-free rasters of the drawings (`assets/plan-*.png`); the numbered markers and legend come from the `ROOMS` list in the script (positions in percent of the plan image). No room areas are shown by design.
- The site plan is drawn in metres by `buildSite()` in the script, from site plan sheet A101.
- Contact links on the closing page: the UK number opens WhatsApp, the Nigerian number dials, the email opens a mail client and the handle opens Instagram.
- Replace or add visualisations in `assets/` and update the gallery `LB` array and figure elements together.

## Visualisations

The seven renders in `assets/` were upscaled from the supplied images with Real-ESRGAN (x4 for the cover and the smaller renders, x2 for the larger ones) and re-encoded as progressive JPEGs. The line-art plans and section were rendered directly from the drawings PDF.

To upscale new renders the same way, download `real_esrgan_x2.onnx` and `real_esrgan_x4.onnx` from huggingface.co/SceneWorks/real-esrgan-onnx into `tools/`, edit the `JOBS` list in `tools/upscale.py`, and run it with Python 3 (needs `onnxruntime`, `numpy`, `pillow`). It runs on the CPU; allow a few minutes per image.
