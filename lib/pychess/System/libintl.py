import ctypes
import os


def _candidate_paths():
    yield "libintl.dylib"

    prefixes = []
    configured_prefix = os.environ.get("HOMEBREW_PREFIX")
    if configured_prefix:
        prefixes.append(configured_prefix)
    prefixes.extend(("/opt/homebrew", "/usr/local"))

    seen = set()
    for prefix in prefixes:
        if prefix in seen:
            continue
        seen.add(prefix)
        yield os.path.join(prefix, "opt", "gettext", "lib", "libintl.dylib")
        # Keep the traditional linked location as a compatibility fallback.
        yield os.path.join(prefix, "lib", "libintl.dylib")


def load_libintl():
    """Load libintl from the dynamic linker or a Homebrew gettext prefix."""
    for candidate in _candidate_paths():
        try:
            return ctypes.cdll.LoadLibrary(candidate)
        except OSError:
            continue
    return None
