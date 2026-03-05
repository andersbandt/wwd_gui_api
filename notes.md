


## Threading

**Status: resolved / acceptable.**

- `guiTab_3_XDS110.py` -- uses bare `threading.Thread` via a `_run_in_thread(func, button)` helper. Correct for fire-and-forget one-shot actions (build/flash/check/toggle). `StoppableThread` would add no value here since the tasks complete naturally and don't loop.
- `guiTab_4_USB.py` -- all `StoppableThread` (t1/t2/t3), properly stopped in `port_close()`. Clean.
- `guiTab_8_LOG.py` -- `_record_thread` uses `StoppableThread`. `_dash_thread` uses bare `threading.Thread(daemon=True)`, which is correct since Dash's `app.run()` blocks with no external stop mechanism; daemon=True ensures it dies with the process.
- `thread_record_timed` uses deadline-based sleep (`time.monotonic()`) — no busy-wait.



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
