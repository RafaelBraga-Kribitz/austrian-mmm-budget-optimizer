"""Layer R is not in this repository.

Charter §7: without a private agency drop the project ships Layers P + D on
disclosed synthetic truth. Inventing a 'public demo' spend series would violate
A-5 (no invented Layer R data).
"""

from __future__ import annotations


class LayerRUnavailable(RuntimeError):
    """Raised when a caller asks for Layer R artifacts that do not exist."""


def load_layer_r() -> None:
    raise LayerRUnavailable(
        "Layer R (real agency data) is not in this repository. "
        "Charter §7 degradation: run `python -m ambo.run layer_p`. See ADR-012."
    )
