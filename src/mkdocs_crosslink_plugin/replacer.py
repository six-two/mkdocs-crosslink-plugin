import os
import re
from typing import Optional
import urllib
# local files
from . import warning, debug
from .file_cache import FileCache
from .config import CrosslinkSite, CrosslinkPluginConfig


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
    def __init__(self, crosslink_list: list[CrosslinkSite], config: CrosslinkPluginConfig) -> None:
        super().__init__()
        re_flags = re.IGNORECASE
        self.regexes = []
        self.regexes += [re.compile(pattern, re_flags) for pattern in create_html_attribute_regex_patterns("a", "href")]
        self.regexes += [re.compile(pattern, re_flags) for pattern in create_html_attribute_regex_patterns("img", "src")]

        self.prefix = config.prefix
        debug(f"Schema is '{config.prefix}NAME{config.suffix}'")
        self.full_name = {}
        self.caches = {}
        self.crosslinks = {cl.name: cl for cl in crosslink_list}
        for crosslink in crosslink_list:
            self.full_name[crosslink.name] = f"{config.prefix}{crosslink.name}{config.suffix}"
            self.caches[crosslink.name] = FileCache(crosslink.source_dir)
            debug(f"Cache for '{crosslink.name}': {self.caches[crosslink.name]}")


    def handle_page(self, file_name: str, html: str) -> str:
        file_contents = html
        for regex in self.regexes:
            search_start_pos = 0

            # replace / handle all matches
            while match := regex.search(file_contents, search_start_pos):
                file_contents, search_start_pos = self.handle_potential_occurence(file_name, file_contents, match)

            # for match in regex.findall(html):
            #     warning(f"Match: '{match}' matched by {regex.pattern}")
        return file_contents


    def handle_potential_occurence(self, file_name: str, html: str, match: re.Match) -> tuple[str,int]:
        # Return the updated document and the index to start the next search from
        start, end = match.span()        
        url_full = match.group(1) # 0: full match, 1: first capture group, ...
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
    
    def get_proto_for_url(self, file_name: str, url: str) -> Optional[str]:
        proto_name_list = [name for name, full_name in self.full_name.items() if url.startswith(full_name)]

        if not proto_name_list:
            # None of our protocols match, so we return None
            return None
        elif len(proto_name_list) == 1:
            # Perfect, exactly one protocol matches -> return it
            return proto_name_list[0]
        else:
            # Multiple protocols could match
            # Best effort match: take the first one (after sorting) that can resolve a file, similar to file ambiguities
            proto_name_list = list(sorted(proto_name_list))
            warning(f"({file_name}) Ambiguity resolving '{url}'. Multiple crosslink protocols match: {', '.join(proto_name_list)}")
            for proto_name in proto_name_list:
                if self.can_resolve_crosslink(url, proto_name):
                    debug(f"({file_name}) Ambiguity resolution for '{url}' chose protocol '{proto_name}'.")
                    return proto_name
            
            # Ok, this is worse, none of the protocols match. The user must fix it
            warning(f"({file_name}) Ambiguity resolution for '{url}' found no potential matches'.")
            return None

    def can_resolve_crosslink(self, crosslink_url: str, crosslink_name: str) -> bool:
        """
        This function check, whether a URL could be resolved given the protocol.
        It can be used in case of protocol ambiguities to check which protocols are more likely (because they can resolve the file)
        """
        crosslink_proto = self.full_name[crosslink_name]
        file_path = crosslink_url[len(crosslink_proto):] # Get everything after the proto.
        if os.path.isabs(file_path):
            # Absolute URL should work -> true
            return True
        else:
            cache = self.caches[crosslink_name]
            results = cache.get_matches(file_path)
            # We do not care if there is an ambiguity in the file path, just whether there are results
            return len(results) > 0

    def resolve_crosslink(self, file_name: str, crosslink_url: str, crosslink_name: str) -> str:
        base_url = self.crosslinks[crosslink_name].target_url
        crosslink_proto = self.full_name[crosslink_name]
        file_path = crosslink_url[len(crosslink_proto):] # Get everything after the proto.
        debug(f"Split URL: {crosslink_url} -> ({crosslink_proto}, {file_path})")
        if not os.path.isabs(file_path):
            cache = self.caches[crosslink_name]
            results = cache.get_matches(file_path)
            if not results:
                warning(f"({file_name}) Error resolving '{crosslink_url}'. Could not find a file matching '{file_path}' in {cache.files_root}")
                return "#crosslink-error"
            elif len(results) == 1:
                # Only one result -> use it
                return join_url(base_url, results[0])
            else:
                # Multipe results. Send a warning. Since I do not (yet) know which is the best,
                # I sort them (to make it predictable) and return the first one
                sorted_results = list(sorted(results))
                warning(f"({file_name}) Ambiguity resolving '{crosslink_url}'. Got {len(results)} matches: {', '.join(sorted_results)}")
                return join_url(base_url, sorted_results[0])
        else:
            # It is an absolute path -> disregard the lookup rules and take it at face value
            return join_url(base_url, file_path)

    def update_file_url_if_needed(self, url: str, crosslink_name: str) -> str:
        lower_url = url.lower()
        if lower_url.endswith(".md"):
            # We have a link to a markdown file, so we need to link to the .HTML version instead
            # Cut of the last three characters: "".md"
            url_without_extension = url[:-3]
            if self.crosslinks[crosslink_name].use_directory_urls:
                # Link to the directory
                if lower_url.endswith("/index.md"):
                    # Remove the file name ('index'), so that we point to the directory
                    return url_without_extension[:-5]
                else:
                    return url_without_extension + "/"
            else:
                # Link to the html file directly
                return url_without_extension + ".html"
        else:
            # Normal file, return it unmodified
            return url


def join_url(base_url: str, path: str):
    # Prepare base_url (ends with /) and path (does not start with slash)
    if not base_url.endswith("/"):
        base_url += "/"
    while path.startswith("/"):
        path = path[1:]
    
    # Encode the path and join both parts
    # I think the URL should not include a query, but may include a hash. So we only allow the characters needed for this to be unencoded
    return base_url + urllib.parse.quote(path, safe="/#")

