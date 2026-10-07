# Changelog

The versions of the `onepage-engine` package, tagged `engine-vX.Y.Z`.

## Unreleased

- The parts that need Playwright (`chromium`, `load`, `print_pdf`, `screenshot`, `wait_for_fonts`,
  `Renderer`) or pypdf (`to_format`, `same_pdf`, `system_fonts`, `font_name`) are imported on first
  use: `SIZES`, `design_height` and the errors no longer need either.

## 0.1.0 (2026-09-27)

The rendering core of one-page-papers, as a package; `engine/build.py` now uses it.

- `Renderer`: a page to the PDF of a print format, or to a PNG, in one call, every render in a
  browser context of its own.
- The steps of a render: `chromium`, `load`, `wait_for_fonts`, `print_pdf`, `screenshot`,
  `to_format`, `system_fonts`, `same_pdf`, `font_name`.
- Formats: `SIZES` (ISO A0 to A5, 50 × 70 and 60 × 80 cm, US sizes) and `design_height`.
- Errors: `EngineError`, `FontLoadError`, `SystemFontError`.
- Pinned: Playwright 1.63.0 (Chromium 153.0.8010.12) and pypdf 6.19.0.
