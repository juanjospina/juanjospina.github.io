# juanjospina.github.io
Personal website based on `https://startbootstrap.com/theme/resume`.

## Publications

The Publications section of `index.html` is generated from `publications.json`, which is synced
with [Google Scholar](https://scholar.google.com/citations?user=T39zSxsAAAAJ&hl=en).
Don't edit the HTML between `PUBLICATIONS:START` / `PUBLICATIONS:END`; edit the JSON instead.

- **Automatic:** the *Update publications* GitHub Action runs on the 1st of each month (or by hand
  from the Actions tab) and commits any changes.
- **Manual** (if Scholar blocks GitHub's servers):
  ```
  python3 scripts/update_publications.py
  git commit -am "Update publications" && git push
  ```

New papers appear automatically (with a DOI from Crossref when one is found). To polish an entry,
edit it in `publications.json`; the script never overwrites your edits:

| Field | Purpose |
|---|---|
| `title`, `authors`, `venue`, `url` | What is shown. Fix Scholar's lowercase titles here. |
| `doi` | Enables the Dimensions citation badge. |
| `tile`, `type` | Text on the navy tile: short venue name, and Journal / Conference / Workshop / Preprint / Patent / Thesis (inferred if omitted). |
| `hide` | `true` to hide slides, duplicates, etc. |

After editing the JSON, re-render without contacting Scholar:
`python3 scripts/update_publications.py --offline`
