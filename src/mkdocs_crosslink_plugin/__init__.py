import logging
from mkdocs.utils import warning_filter

# Set up a logger for my code to use
LOGGER = logging.getLogger("mkdocs.plugins.crosslink")
LOGGER.addFilter(warning_filter)

def warning(message: str) -> None:
    LOGGER.warning(f"[crosslink] {message}")

# Import local files in the correct order
# from .utils import replace_regex_matches
# from .normal_badge import replace_normal_badges
from .plugin import BadgesPlugin

__all__ = ["BadgesPlugin"]
