"""Put ``track1_engine/`` on ``sys.path`` so the tests import it without setup.

``tests/test_engine.py`` does ``import prioritization`` -- a flat import of a sibling
package directory, not of an installed module. Without this file that only works if
the caller happens to have exported ``PYTHONPATH``, which cost time once already.
pytest imports ``conftest.py`` before collecting, so putting the path fix here means
``pytest`` works from the repository root, from ``track1_engine/``, and from an IDE
runner, with no environment variable at all.
"""
from __future__ import annotations

import sys
from pathlib import Path

ENGINE_DIR = Path(__file__).resolve().parent.parent
if str(ENGINE_DIR) not in sys.path:
    sys.path.insert(0, str(ENGINE_DIR))
