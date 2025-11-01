"""Top-level LLMHive package bootstrap.

This project keeps the actual Python package inside ``llmhive/src`` to play
nicely with tooling that expects a ``src`` layout.  Production deployments,
however, often import modules such as ``llmhive.app.main`` directly from the
repository root.  Without a little help those imports fail because the ``src``
directory is not automatically added to :data:`sys.path`.

By extending :data:`__path__` to include the real package directory we allow
``import llmhive`` (and its submodules) to succeed regardless of whether the
package has been installed.  This mirrors the behaviour of ``python -m pip
install -e .`` while keeping the repository runnable out of the box.
"""

from __future__ import annotations

from pathlib import Path
import pkgutil

__all__ = []

# ``pkgutil.extend_path`` preserves compatibility with namespace packages if the
# project is ever installed alongside additional ``llmhive`` components.
__path__ = pkgutil.extend_path(__path__, __name__)  # type: ignore[name-defined]

_SRC_PACKAGE = Path(__file__).resolve().parent / "src" / "llmhive"
if _SRC_PACKAGE.is_dir():
    src_package = str(_SRC_PACKAGE)
    # ``__path__`` behaves like a list; appending enables ``import llmhive.app``
    # without requiring a prior editable install.
    if src_package not in __path__:
        __path__.append(src_package)  # type: ignore[attr-defined]
