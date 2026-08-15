"""JANUS — credit model integrity.

The LLM decides what to investigate. This package produces every number.
"""

from janus.data_gen import FEATURES, generate_portfolio
from janus.levers import MUTABILITY_MODEL

__version__ = "0.3.0"
__all__ = ["FEATURES", "MUTABILITY_MODEL", "generate_portfolio"]
