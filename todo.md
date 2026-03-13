# Development TODO and notes

*Generated: 2026-02-03 | Last updated: 2026-03-04*

---

### Feature Work


- [ ] **Change tab color when something is active** — e.g. connection live, recording in progress. Probably a notebook style override or a colored indicator in the tab label.
- [ ] **Mini status indicator in ATE tab** — next to the instrument accuracy test section, show pass/fail or in-progress state.
- [ ] **Color normalization for filename labeling mode** (graph tab) — `normalize_colors` currently only runs in `data` and `both` labeling modes. To support `filename` mode: pre-pass to collect extracted `file_parts[idx]` values across all files, feed into the same normalizer/colormap pipeline, use the resulting color in the `filename` branch. `label_config` already carries `normalize_colors` in `both` mode; extend for `filename`.
- [ ] **Hardcoded serial commands in USB tab** — `ACTIVATE_TEST_CMD = "DAGA"` and `TEST_TYPE_COMMANDS` dict are hardcoded in `guiTab_4_USB.py`. Consider moving to `config/master.ini` or a config file so they can be changed without touching code.
- [x] **ATE tab `port_close()` bug** — calls `self.cc.set_ps(None)` which is clearly a copy-paste from the PS tab. ATE has no dedicated `cc` slot, so this is confusing (though not actively harmful since the PS tab manages its own state). Should be `self.ate = None` or removed.
- [ ] Simulator mode — use `np.random()` or similar to generate fake instrument data for testing live plot / logging / math columns without hardware

---

### Bugs / Polish

- [ ] **`_record_thread` not joined on stop** — `stop_record()` calls `_record_thread.stop()` (sets flag) but doesn't join the thread. If something immediately reads state after stopping (e.g. final_plot), there's a potential race. Consider adding `_record_thread.join(timeout=2)` after `stop()`.


---

### Future / Exploratory

- [ ] is there a way to simplify the UI when in heated logging? For example, switching to the PS tab just to toggle is annoying when I am constantly starting/stopping the log
- [ ] Terminal-only API (connect and control instruments from CLI, no GUI)
- [ ] Web interface option (Flask/FastAPI backend)
- [ ] Database storage (SQLite) — mainly motivated by faster sampling; otherwise adds complexity
- [ ] Package into standalone executable — PyInstaller failed previously, investigate Nuitka or cx_Freeze



---

