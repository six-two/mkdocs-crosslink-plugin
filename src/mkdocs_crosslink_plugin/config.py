from functools import wraps
import glob
import json
import os
from pathlib import Path
import re
from typing import NamedTuple, Any, Callable
from urllib.parse import urlparse
# pip dependencies
from mkdocs.config.base import Config
from mkdocs.config.config_options import Type
from mkdocs.config.defaults import MkDocsConfig
# local
from . import warning, debug

CROSSLINK_FIELDS = {
    "name",
    "source_dir",
    "target_url",
    "use_directory_urls"
}

class CrosslinkPluginConfig(Config):
    enabled = Type(bool, default=True)
    show_profiling_results = Type(bool, default=False)
    # Default pattern: x-NAME://link
    # This makes it look like a custom protocol, so no warnings should be raised
    prefix = Type(str, default="x-")
    suffix = Type(str, default=":")
    crosslinks = Type(list, default=[])


class ConfigError(Exception):
    pass


class ConfigErrorWithData(ConfigError):
    """
    Config exception that already has data of what caused it appended.
    This makes finding the error in your configuration much easier.
    """
    def __init__(self, message: str, location: str, data: dict) -> None:
        # Add problematic data to error message
        super().__init__(f"{message}\n\nCaused by data at {location}: {json.dumps(data, indent=4)}")


class CrosslinkSite(NamedTuple):
    # The name to use for referencing the site. (default schema for using the name: x-NAME://file_name.extension)
    name: str
    # The directory on your disk, where the files will be searched for. Should be the `docs/` directory of another MkDocs site
    source_dir: Path
    # The base URL of the site to link to
    target_url: str
    # Use directory URLs?
    # yes: test.md -> test/
    # no: test.md -> test.html
    use_directory_urls: bool
    # # In case multiple matching crosslinks are specified (by wildcards, defaults, etc) this will decide which one to use


def add_problematic_data_to_exceptions(function: Callable) -> Callable:
    @wraps(function)
    def wrap(data: dict, location: str, *args, **kwargs):
        try:
            return function(data, location, *args, **kwargs)
        except ConfigErrorWithData:
            # This already has more detailed data, so we just reraise it.
            # Otherwise you might have a bunch of useles exceptions in the chain adding bigger and bigger JSON dumps,
            # which makes it harder to find the actual root cause
            raise
        except Exception as ex:
            message = f"Missing key {ex}" if type(ex) == KeyError else str(ex)
            raise ConfigErrorWithData(message, location, data)
    return wrap


def create_local_crosslink(mkdocs_config: MkDocsConfig) -> CrosslinkSite:
    if mkdocs_config.site_url:
        # We extract the path. this makes it so that if you use 'https://example.com/some/dir/' 
        # the links will be to '/some/dir/path/to/file', so it will also work with 'mkdocs serve' and similar stuff
        target_url = urlparse(mkdocs_config.site_url).path
    else:
        target_url = "/"

    return CrosslinkSite(
        name="local",
        source_dir=Path(mkdocs_config.docs_dir),
        target_url=target_url,
        use_directory_urls=mkdocs_config.use_directory_urls,
    )

@add_problematic_data_to_exceptions
def parse_crosslinks_list(data_list: list[Any], location: str, dict_to_modify: dict[str,CrosslinkSite]) -> None:
    if data_list:
        for index, data in enumerate(data_list):
            parse_crosslink(data, f"{location}[{index}]", dict_to_modify)


@add_problematic_data_to_exceptions
def parse_crosslink(data: Any, location: str, dict_to_modify: dict[str,CrosslinkSite]) -> None:
    if type(data) != dict:
        raise ConfigError(f"Expected a dict, but got a {type(data).__name__}")
    
    assert_no_unknown_fields(data, CROSSLINK_FIELDS)

    name = get_string(data, "name")
    source_dir = get_directory_path(data, "source_dir")
    target_url = get_string(data, "target_url")
    use_directory_urls = get_bool(data, "use_directory_urls")

    if not (target_url.startswith("https://") or target_url.startswith("http://")):
        warning(f"URL '{target_url}' should probably start with 'https://' (or 'http://')")

    if has_wildcard(str(source_dir)) and has_wildcard(name) and has_wildcard(target_url):
        handle_glob_crosslink(name, source_dir, target_url, use_directory_urls, dict_to_modify)
    else:
        if name in dict_to_modify:
            old = dict_to_modify[name]
            raise ConfigError(f"A crosslink named '{name}' already exists: source_dir={old.source_dir}, target_url={old.target_url}")
        else:
            dict_to_modify[name] = CrosslinkSite(name=name, source_dir=source_dir, target_url=target_url, use_directory_urls=use_directory_urls)


def handle_glob_crosslink(name: str, source_dir: Path, target_url: str, use_directory_urls: bool, dict_to_modify: dict[str,CrosslinkSite]) -> None:
    # Allow globs for people like me, who store all/most projects in the same directory
    # and do not want to define it manually for each one. Just be sure to use the same
    # 'use_directory_urls' settings or define
    # Native globs have some problems (other characters like '[', '?', etc) and extracting the value that star replaced is likely non-trivial
    source_dir_str = str(source_dir).replace("\\", "/")
    prefix_full, suffix_full = source_dir_str.split("*", 1)
    prefix_dir, prefix_name = os.path.split(prefix_full)
    if "/" in suffix_full:
        suffix_name, suffix_child = suffix_full.split("/")
    else:
        suffix_name, suffix_child = suffix_full, ""

    dir_name_regex = re.compile("^" + re.escape(prefix_name) + "(.+)" + re.escape(suffix_name) + "$")

    for dir in Path(prefix_dir).iterdir():
        match = dir_name_regex.match(dir.name)
        if match and dir.is_dir():
            # Seems to match and is a directory, lets also check with suffix_child
            full_dir = dir.joinpath(suffix_child)
            if full_dir.exists() and full_dir.is_dir():
                star_value = match.group(1)
                new_name = name.replace("*", star_value)
                new_url = target_url.replace("*", star_value)

                if new_name in dict_to_modify:
                    # If one already exists just do nothing, it was probably added manually to overwrite this entry
                    debug(f"glob expansion: Not adding '{new_name}' ({full_dir}), because it already points to {dict_to_modify[new_name].source_dir}")
                else:
                    # This crosslink does not yet exist -> add it
                    debug(f"glob expansion: Adding '{new_name}' ({full_dir})")
                    dict_to_modify[new_name] = CrosslinkSite(name=new_name, source_dir=full_dir, target_url=new_url,
                                                             use_directory_urls=use_directory_urls)


def has_wildcard(string: str) -> bool:
    count = string.count("*")
    if count > 1:
        # More than one star: problematic, so we ignore it and print a warning
        warning(f"String '{count}' contains {count} wildcard characters ('*), but should probably only contain a single one")
    return count == 1


def get_string(data: dict, name: str) -> str:
    value = data.get(name, None)
    if value:
        if type(value) == str:
            return value
        else:
            raise ConfigError(f"Field '{name}' should be a string, but has type {type(value).__name__}")
    else:
        raise ConfigError(f"Field '{name}' should be set and needs to have a non-empty value")


def get_bool(data: dict, name: str) -> bool:
    value = data.get(name, None)
    if value == None:
        raise Exception(f"Field '{name}' does not exist")
    elif type(value) != bool:
        raise ConfigError(f"Field '{name}' should be a boolean, but has type {type(value).__name__}")
    else:
        return value


def get_directory_path(data: dict, name: str) -> Path:
    value = Path(get_string(data, name))

    if has_wildcard(str(value)):
        # Do not check if the literal folder exists, if this is a wildcard path
        return value
    elif value.exists():
        if value.is_dir():
            return value
        else:
            raise ConfigError(f"'{value}' needs to be a directory")
    else:
        raise ConfigError(f"'{value}' does not exist")


def assert_no_unknown_fields(data: dict, known_field_names: set[str]) -> None:
    unexpected_fields = set(data).difference(known_field_names)
    if unexpected_fields:
        raise ConfigError(f"Unexpected field(s): {', '.join(unexpected_fields)}\n[Hint] Allowed fields are: {', '.join(known_field_names)}")


