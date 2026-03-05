# Development TODO and notes

*Generated: 2026-02-03 | Last updated: 2026-02-19*

---

### Feature Work


- [ ] look at `scripting.md` and figure out implementation plan approach
- [ ] Change tab color when something is active (e.g., connection live, recording in progress)
- [ ] should I add a mini status indicator in ATE tab next to instrument accuracy testing?


- [ ] add color normalization to graph feature

**Color normalization for filename mode** (medium) — allow the index-extracted value to drive the `normalize_colors` colormap pipeline, the same way `'data'` mode does. 
Currently `normalize_colors` only runs in the `data_value_to_color` preprocessing block which is gated on `labeling_mode in ['data', 'both']`. 
To support `'filename'` mode: collect the extracted `file_parts[idx]` values across all files in a pre-pass, feed them into `data_value_to_color` using the same normalizer logic, then use that color in the `filename` branch plot call. 
The `label_config` dict already passes `normalize_colors` through in `'both'` mode; would need to extend it for pure `'filename'` mode too.


- [ ] `guiTab_4_USB.py:124` has `"DAGA"`, and lines 141-149 map test names to codes like `"FR91"`, `"FR01"`, `"FE42"`.
- [ ] get the FUNC2 thing working again or eliminate it (would be nice to read XDM1041 datasheet)



### Future / Exploratory

- [ ] Terminal-only API (connect and control instruments on CLI)
- [ ] Web interface option (Flask/FastAPI backend)
- [ ] Database storage option (SQLite/PostgreSQL)
  - my main motiviation for this would mainly be performance (if I can sample faster). Otherwise seems clunky
- [ ] package into a standalone executable (PyInstaller didn't work previously — investigate Nuitka or cx_Freeze)
- [ ] add a simulator mode using np.random() or similar to test live plotting / logging / math features








