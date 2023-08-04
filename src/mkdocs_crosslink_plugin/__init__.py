import logging

# Set up a logger for my code to use
LOGGER = logging.getLogger("mkdocs.plugins.crosslink")

def warning(message: str) -> None:
    LOGGER.warning(f"[crosslink] {message}")

# Import local files in the correct order
# from .utils import replace_regex_matches
# from .normal_badge import replace_normal_badges
from .plugin import CrosslinkPlugin

__all__ = ["CrosslinkPlugin"]
