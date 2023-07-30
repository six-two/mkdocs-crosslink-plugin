from pathlib import Path
import re
# local files
from . import warning
from .file_cache import FileCache
from .config import parse_crosslinks_list


def create_html_attribute_regex_patterns(tag: str, attribute: str) -> list[str]:
    # Not perfect, but probably good enough
    # There are multiple ways to quote things: no quotes, single quotes and double quotes
    return [
        # No brackets. This usually only exists after the page has been minified
        f"<{tag}\\s+[^>]*{attribute}\\s*=\\s*([^'\"][^\\s>]*)",
        # Double quotes. This is the default way
        f'<{tag}\\s+[^>]*{attribute}\\s*=\\s*"([^"]*)"',
        # Is this even valid? I have not seen it often, but added it just in case
        f"<{tag}\\s+[^>]*{attribute}\\s*=\\s*'([^']*)'",
    ]

class Replacer():
    def __init__(self) -> None:
        super().__init__()
        re_flags = re.IGNORECASE
        self.regexes = []
        self.regexes += [re.compile(pattern, re_flags) for pattern in create_html_attribute_regex_patterns("a", "href")]
        self.regexes += [re.compile(pattern, re_flags) for pattern in create_html_attribute_regex_patterns("img", "src")]

    def handle_page(self, html: str):
        warning(f"Got page ({len(html)} bytes)")
        for regex in self.regexes:
            for match in regex.findall(html):
                warning(f"Match: '{match}' matched by {regex.pattern}")
      


