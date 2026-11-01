# Active test policy

Only the tests declared in `production/active_engine_policy.json` are executable for the current engine.

Legacy tests are retained under this directory as `.archived.txt` audit records. They are not Python modules, are not discovered by unittest, and must not be restored to the active suite without updating the active policy and singleton guard.

Current active suite:

- `tests/test_reuse_first.py`
- `tests/test_current_engine_policy.py`
