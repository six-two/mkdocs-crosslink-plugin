import re
import urllib
# local
from .replacer import Replacer

LINK_TEXT_PATTERN = r"\[([^\]]*)\]" # [Some text]
LINK_TARGET_PATTERN = r"\(([^)]*)\)" # (https://example.com)
MARKDOWN_LINKS_REGEX = re.compile(LINK_TEXT_PATTERN + LINK_TARGET_PATTERN)

def patch_source_file_links_inplace(path: str, replacer: Replacer):
    with open(path) as f:
        contents = f.read()

    original_contents = contents

    # @TODO
    matches = MARKDOWN_LINKS_REGEX.findall(contents)
    for match in matches:
        print("DEBUG", path, match.group(0))

    search_start_pos = 0

    # replace / handle all matches
    while match := MARKDOWN_LINKS_REGEX.search(contents, search_start_pos):
        file_contents, search_start_pos = handle_potential_occurence(file_name, file_contents, match)

    
    
    if contents != original_contents:
        with open(path, "w") as f:
            f.write(contents)


def handle_potential_occurence(self, file_name: str, html: str, match: re.Match) -> tuple[str,int]:
    # Return the updated document and the index to start the next search from
    start, end = match.span()        
    url_full = match.group(2) # 0: full match, 1: first capture group, ...
    # Some plugins like ezlinks enquote certain characters (like the ':' character used as prefix)
    # So we need to unquote the URL before we try to inspect it
    url_full = urllib.parse.unquote(url_full)

    if not url_full.startswith(self.prefix):
        # Quickly bail out if it is definitely not for us
        return (html, start + 1)

    # If the URL ends with a hash (to jump to a section), we need to remove it and add it back after the URL is updated.
    parts = url_full.split("#", 1)
    if len(parts) == 2:
        url = parts[0]
        url_hash = "#" + parts[1]
    else:
        url = url_full
        url_hash = ""

    crosslink_name = self.get_proto_for_url(file_name, url)
    if crosslink_name:
        new_url = self.resolve_crosslink(file_name, url, crosslink_name)
        new_url_updated = self.update_file_url_if_needed(new_url, crosslink_name)
        debug(f"Resolving: {url_full} -> {new_url + url_hash} -> {new_url_updated + url_hash}")

        # update the URL
        updated_tag = html[start:end].replace(url, new_url_updated)
        html = html[:start] + updated_tag + html[end:]
        return (html, start + len(updated_tag))
    else:
        # No matches, seems to be a normal link
        return (html, start + 1)

