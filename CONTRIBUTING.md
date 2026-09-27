# Contributing

To suggest a text and vote for the next ones, post in [Discussions: Ideas](https://github.com/vodhash/one-page-papers/discussions/categories/ideas); a 👍 counts as a vote. There are two ways to add a text to the collection.

- **Request a poster**: open an issue with the
  [Request a poster](https://github.com/vodhash/one-page-papers/issues/new?template=request-a-poster.yml)
  form. Give the title, a primary source and what you know of its license; the checklist below
  says what is looked for.
- **Make the poster yourself**: open a pull request that adds `papers/<category>/<slug>/`, as
  [Add a paper](README.md#add-a-paper) in the README describes. The checklists below are what
  the review goes through.

Whoever proposes a text or makes its poster is credited on its page of the site, through `contributors` in its `meta.yaml`.

Texts that cannot be added yet wait in [PENDING.md](PENDING.md), with what is missing for each.
If you hold a permission or find a license for one of them, open an issue.

## License checklist

A text is added only when **every** part of the poster may be redistributed: the text, each
image, and the transcription it is taken from.

1. **Public domain in France and in the United States**, both.
   - France: every author died before 1 January 1956 (70 years after the year of death). For an
     anonymous or pseudonymous work, it was published before 1 January 1956. Count translators
     and editors whose own text is reproduced, such as notes. Official acts (laws, decrees)
     are not protected.
   - United States: published before 1 January 1931, or a work of the federal government
     (17 U.S.C. 105). A foreign work of 1931 or later may have had its copyright restored in 1996
     (URAA), so do not rely on a missing notice or renewal.
   - A work of the US government is protected in France no longer than in the United States
     (the rule of the shorter term, article L. 123-12 of the Code de la propriété
     intellectuelle), as `papers/history/kennedy-moon-speech/meta.yaml` explains.
2. **Or under an explicit license or permission** that allows redistribution.
   - It is stated by the rights holder, word for word, with a link: a license file, a notice in
     the document, the terms of the site that publishes it.
   - The poster keeps every notice that the license requires (attribution, copyright line,
     license text).
   - "Found online", "widely shared", "no copyright notice" are not licenses.
   - A license that forbids commercial use is not enough: posters can be printed and sold.
3. **Translations**: use the original. A translation only if the translation itself passes 1 or
   2.
4. **Images**: check each on its source page (for Wikimedia Commons, the file page and its
   license), including the photograph of a public domain object.
5. **Record it** in `meta.yaml` under `license`: `basis` gives the reasoning with the dates, or
   `notice` quotes the license word for word, with its URL in `note`.
6. **Say whether prints may be sold**: `commercial: true` only when the licenses of the text and of
   every image allow it, with the reason in `commercial_basis`; when in doubt, `false`.

When any point is unclear, the text goes to PENDING.md rather than into the collection.

## Fidelity checklist

1. The text comes from the primary source or a reference edition, never retyped from memory or
   copied from a site that retyped it. OCR is corrected against the page images, word by word.
2. `source` in `meta.yaml` gives the URL, the date it was retrieved, the edition, and **every**
   difference between that edition and the poster: normalizations (long s, hyphens at line
   ends, running heads), corrected misprints, moved or left-out parts.
3. The words of the poster are counted against the source, and every difference is explained.
4. An excerpt says so on the poster ("Excerpt" in the kicker) and in `source.edition`.
5. Spelling, punctuation and dashes are those of the source. A text written for the poster (a
   notice around a map, for instance) says so on the poster.

## Build checklist

```bash
make deps         # once
make <slug>       # the PDFs and the preview of your paper
make check        # file sizes, every poster fits and uses bundled fonts, the catalog
make readme       # the catalog of the README
```

- Look at the A format in a light and a dark theme: nothing overflows, the footer sits inside
  the frame, images are readable.
- `min_print` is the value the build asks for.
- Commit the paper folder, its preview in `docs/` and the README, in one commit titled
  `feat(papers): add <category>/<slug>`. Not its PDFs: git does not keep `dist/`, the CI builds
  them and publishes them on the site and in the releases.
- An image of a paper stays under 5 MiB, and any other binary file under 1 MiB: the pre-commit
  hook and the CI refuse larger ones (`engine/sizes.py`). Reduce a scan to what the poster prints.

## Where the PDFs are published

This part is for the maintainers. Every push to `master` runs the pages workflow: it builds the
PDFs, uploads those that changed to the Cloudflare R2 bucket `onepagepapers-pdf`, served at
`https://files.onepagepapers.com/` (its custom domain), then deploys the site on GitHub Pages. It
needs these secrets of the repository (Settings, Secrets and variables, Actions):

| Secret | Value |
|---|---|
| `R2_ACCESS_KEY_ID` | Access Key ID of an R2 API token with Object Read & Write on the bucket |
| `R2_SECRET_ACCESS_KEY` | its Secret Access Key |
| `R2_ENDPOINT` | `https://<account id>.r2.cloudflarestorage.com` |
| `CLOUDFLARE_API_TOKEN` | optional: an API token with Zone, Cache Purge on onepagepapers.com |
| `CLOUDFLARE_ZONE_ID` | optional: the zone ID of onepagepapers.com |

Without the last two, a PDF that changes shows within a week, when its `Cache-Control` runs out;
with them, the workflow purges it from the cache of Cloudflare at once.

The wallpapers of the site fetch a PDF from the bucket, which is another origin than the site, so
the bucket has this CORS policy (R2, the bucket, Settings, CORS policy):

```json
[
  {
    "AllowedOrigins": ["https://onepagepapers.com"],
    "AllowedMethods": ["GET", "HEAD"],
    "AllowedHeaders": ["*"],
    "MaxAgeSeconds": 86400
  }
]
```

A wallpaper therefore does not draw on `make serve`, whose origin is `http://localhost:8000`.
