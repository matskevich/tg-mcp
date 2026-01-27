"""
vahue app configuration skeleton
"""

from dataclasses import dataclass
import os


@dataclass
class VahueConfig:
    feature_flag: bool = bool(int(os.getenv("VAHUE_FEATURE", "1")))


config = VahueConfig()

