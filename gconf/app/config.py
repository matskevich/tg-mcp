"""
gconf app configuration skeleton
"""

from dataclasses import dataclass
import os


@dataclass
class GConfConfig:
    analytics_enabled: bool = bool(int(os.getenv("GCONF_ANALYTICS", "1")))


config = GConfConfig()

