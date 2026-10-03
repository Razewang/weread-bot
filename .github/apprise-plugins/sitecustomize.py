# Loaded automatically by Python when its directory is on PYTHONPATH.
# apprise.Apprise() (Python API) does not scan plugin directories by
# default, so register the custom plugins found in APPRISE_PLUGIN_PATH.
import os as _os

_paths = [p for p in _os.environ.get("APPRISE_PLUGIN_PATH", "").split(_os.pathsep) if p]
if _paths:
    try:
        import apprise as _apprise

        _apprise.AppriseAsset(plugin_paths=_paths)
    except ImportError:  # apprise not installed in this interpreter
        pass
    except Exception as _exc:  # never break interpreter start-up
        import sys as _sys

        print("sitecustomize: apprise plugin load failed: %s" % type(_exc).__name__,
              file=_sys.stderr)
