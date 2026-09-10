# Heights 777

Web brochure for Heights 777 — eighteen one- and two-bedroom residences on seven storeys at Plot 777, CAD Zone A07, Parakou Street, Wuse II, Abuja FCT.

Seven pages, one file: `index.html` carries the markup, styles and interactions; `assets/` holds the visualisations and the line-art plans and section exported from the architectural drawings (October 2025). Fonts load from Google Fonts (Bodoni Moda, Jost).

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
