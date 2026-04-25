# Agent Notes

These notes capture project-specific details that are easy to rediscover the
hard way. Keep this file short and update it when tooling, tests, or packaging
behavior changes.

## Project Shape

- This is PyChess, a GTK/PyGObject desktop chess GUI.
- The importable application code lives under `lib/pychess`.
- The launcher is the executable `pychess` script at the repo root.
- Packaging still relies on `setup.py` for some workflows, including the DEB
  and RPM jobs, even though modern tooling is configured in `pyproject.toml`.
- Prefer small, compatibility-preserving changes. Several CI jobs exercise old
  packaging paths and platform-specific behavior.

## Tooling

- Use `uv` for the development environment and lockfile.
- Use Ruff for linting and formatting:

  ```bash
  uv run --only-group dev ruff check .
  uv run --only-group dev ruff format --check .
  ```

- Use Pyright for type checking:

  ```bash
  uv run --only-group dev pyright
  ```

- Run pre-commit across the tree with:

  ```bash
  uvx pre-commit run --all-files
  ```

## Unit Tests

The tests are `unittest` based and live under `testing`.

For a reliable local run, use writable XDG directories and Xvfb:

```bash
mkdir -p /tmp/pychess-test-home/config /tmp/pychess-test-home/data /tmp/pychess-test-home/cache
env XDG_CONFIG_HOME=/tmp/pychess-test-home/config \
    XDG_DATA_HOME=/tmp/pychess-test-home/data \
    XDG_CACHE_HOME=/tmp/pychess-test-home/cache \
    PYCHESS_UNITTEST=true PYTHONPATH=lib \
    xvfb-run -a python3 -m unittest discover -s testing -p "*.py" -v
```

Known caveats:

- Plain test runs may fail because PyChess writes config and log files under
  the user's XDG config/data locations.
- GTK tests need a display. Use `xvfb-run` in headless environments.
- In restricted sandboxes, GdkPixbuf image loading may fail through Glycin and
  D-Bus with `Operation not permitted`. If the same command passes outside the
  sandbox, treat that as an environment restriction rather than a test failure.
- The full suite may emit GTK parent warnings, deprecation warnings, async
  cleanup noise, and ResourceWarnings. These are worth improving separately but
  are not necessarily failures.

## Runtime Sound

If GStreamer initialization fails on newer PyGObject, check
`lib/pychess/System/gst_player.py`. `Gst.init_check` must be called with an
argument list such as `[]`, not `None`, because some versions reject `None`.

## Packaging Metadata

Old setuptools versions used by distro packaging jobs may reject modern PEP 621
license shorthand. Keep `project.license` compatible with setup.py-era
setuptools, for example:

```toml
license = { text = "GPL-3.0-or-later" }
```

Do not change this to `license = "GPL-3.0-or-later"` without checking the DEB
and RPM workflows.

## Git Hygiene

- Do not assume ignored test artifacts are meaningful source changes. Unit tests
  may generate ignored `.sqlite` and `.scout` files.
- Avoid committing local generated files such as `.codex`.
- Before committing, check:

  ```bash
  git status --short
  ```
