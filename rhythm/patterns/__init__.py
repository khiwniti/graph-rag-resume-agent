"""
Rhythm Patterns - A collection of forkable rhythm templates.

Each pattern is designed to be:
- Easy to understand
- Simple to modify
- Ready to fork into your projects
"""

from .basic_4x4 import BASIC_4X4
from .syncopated_groove import SYNCOPATED_GROOVE
from .polyrhythmic_flow import POLYRHYTHMIC_FLOW
from .breakbeat_chaos import BREAKBEAT_CHAOS

__all__ = [
    "BASIC_4X4",
    "SYNCOPATED_GROOVE",
    "POLYRHYTHMIC_FLOW",
    "BREAKBEAT_CHAOS",
]

__version__ = "1.0.0"
