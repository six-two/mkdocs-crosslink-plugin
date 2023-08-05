from functools import wraps
import glob
import json
from pathlib import Path
from typing import NamedTuple, Any, Callable
from urllib.parse import urlparse
# pip dependencies
from mkdocs.config.base import Config
from mkdocs.config.config_options import Type
# local
from . import warning

CROSSLINK_FIELDS = {
    "name",
    "source_dir",
    "target_url",
    "use_directory_urls"
}

class CrosslinkPluginConfig(Config):
    enabled = Type(bool, default=True)
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


def create_local_crosslink(mkdocs_config: Config) -> CrosslinkSite:
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
            parse_crosslink(data, f"{location}[{index}]")


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

    if "*" in source_dir and "*" in name and "*" in target_url:
        # Allow globs for people like me, who store all/most projects in the same directory
        # and do not want to define it manually for each one. Just be sure to use the same
        # 'use_directory_urls' settings or define
        for directory in glob.glob(source_dir):
            star_value = "TODO: resume here"
    else:
        if name in dict_to_modify:
            dict_to_modify[name] = CrosslinkSite(name=name, source_dir=source_dir, target_url=target_url, use_directory_urls=use_directory_urls)
        else:
            old = dict_to_modify[name]
            raise ConfigError(f"A crosslink named '{name}' already exists: source_dir={old.source_dir}, target_url={old.target_url}")


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

    if value.exists():
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


