import os
from pathlib import Path
import re
import urllib
# local files
from . import warning
from .file_cache import FileCache
from .config import parse_crosslinks_list, CrosslinkSite, CrosslinkPluginConfig


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

        self.full_name = {}
        self.caches = {}
        self.crosslinks = {cl.name: cl for cl in crosslink_list}
        for crosslink in crosslink_list:
            self.full_name[crosslink.name] = f"{config.prefix}{crosslink.name}{config.suffix}"
            self.caches[crosslink.name] = FileCache(crosslink.source_dir)


    def handle_page(self, file_name: str, html: str) -> str:
        warning(f"({file_name}) Got page ({len(html)} bytes)")
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
        
        url = match.group(1) # 0: full match, 1: first capture group, ...
        proto_names = [name for name, full_name in self.full_name.items() if url.startswith(full_name)]

        if proto_names:
            if len(proto_names) > 1:
                # Best effort match: take the first one (after sorting), similar to file ambiguities
                proto_names = list(sorted(proto_names))
                warning(f"({file_name}) Ambiguity resolving '{url}'. Multiple crosslink protocols match: {', '.join(proto_names)}")

            # Perfect, only one fake protocol / is left. So let's replace it
            crosslink_name = proto_names[0]
            new_url = self.resolve_crosslink(file_name, url, crosslink_name)
            updated_tag = html[start:end].replace(url, new_url)
            html = html[:start] + updated_tag + html[end:]
            return (html, start + len(updated_tag))
        else:
            # No matches, seems to be a normal link
            return (html, start + 1)

    def resolve_crosslink(self, file_name: str, crosslink_url: str, crosslink_name: str) -> str:
        base_url = self.crosslinks[crosslink_name].target_url
        crosslink_proto = self.full_name[crosslink_name]
        file_path = crosslink_url[len(crosslink_proto):] # Get everything after the proto.
        if not os.path.isabs(file_path):
            # Relative path or just a file name. Look it up 
            # @TODO later: check the path and use it in case of duplicates?
            name = os.path.basename(file_path)
            cache = self.caches[crosslink_name]
            results = cache.get(name)
            if not results:
                warning(f"({file_name}) Error resolving '{crosslink_url}'. Could not find a file called '{name}' in {cache.files_root}")
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

def join_url(base_url: str, path: str):
    # Prepare base_url (ends with /) and path (does not start with slash)
    if not base_url.endswith("/"):
        base_url += "/"
    while path.startswith("/"):
        path = path[1:]
    
    # Encode the path and join both parts
    # I think the URL should not include a query, but may include a hash. So we only allow the characters needed for this to be unencoded
    return base_url + urllib.parse.quote(path, safe="/#")

