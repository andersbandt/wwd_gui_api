


## Threading

Tabs spawn `threading.Thread` directly in button callbacks with no lifecycle management.

- `guiTab_3_XDS110.py:75-127` -- 5 separate `threading.Thread(...).start()` calls, one per button
- `guiTab_4_USB.py:267,292` -- thread creation in `port_init` and `start_process`
- `guiTab_8_LOG.py:967` -- recording thread with busy-wait `time.sleep` loops

**Recommendation:** Use `StoppableThread` (already in `gui_class.py`) consistently, and move long-running work into service-layer methods that accept progress/completion callbacks.



## ATE Tab: Model Dropdown Audit

**Q: Can the model dropdown be replaced with just a connection handler dropdown?**

**Short answer: Not without losing benchmarking functionality.** The model is currently needed for two reasons:

1. **Class instantiation** — `port_init()` does `ate_temp = self.registry[model_name]` then `self.ate = ate_temp(port)`. Different instrument classes have different `__init__` signatures and different connection handler implementations. Removing the model means we lose the Python class entirely.

2. **`benchmark()` needs model-specific methods** — `ate_benchmark()` calls `self.ate.read_value` or `self.ate.test_conn`. Both are model-specific SCPI/serial sequences. Without a known model, there is no `read_value()` to call.

**What IS already model-agnostic:**
- `ate_command()` / `ate_query()` — just call `self.ate.write(cmd)` and `self.ate.query(cmd)` with a user-entered string. These could work fine with a generic connection handler and a user-typed address.
- `run_accuracy_test()` — uses `cc.ps_service` and `cc.dmm_service` exclusively; the ATE device is not involved at all.

**Possible future architecture (if model dropdown becomes a pain point):**
- Keep the connection handler selector (PyVISA / Serial) for the address-based generic send/query.
- Add a separate "benchmark command" text field so the user types the SCPI query string (e.g. `MEAS:VOLT:DC?`). The `benchmark()` helper can accept a callable or a raw command string.
- This would eliminate the need to pick a fully known model just to do timing benchmarks on an arbitrary instrument.

**Also note:** `port_close()` at line 516 calls `self.cc.set_ps(None)` — this appears to be a copy-paste bug. The ATE tab has no dedicated `cc` slot; it should either set `self.ate = None` or be left as-is if the intent was something else. Low priority since it doesn't affect correctness of the PS tab (PS tab manages its own state), but it is confusing.
