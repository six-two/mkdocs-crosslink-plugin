from pathlib import Path
import re
# pip dependency
import mkdocs
from mkdocs.config.config_options import Type
from mkdocs.plugins import BasePlugin, event_priority
from mkdocs.config.base import Config
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.pages import Page
from mkdocs.structure.files import Files
# local files
from . import warning
from .file_cache import FileCache
from .config import parse_crosslinks_list
from .replacer import Replacer


class CrosslinkPluginConfig(Config):
    enabled = Type(bool, default=True)
    # Default pattern: x-NAME://link
    # This makes it look like a custom protocol, so no warnings should be raised
    prefix = Type(str, default="x-")
    suffix = Type(str, default="://")
    crosslinks = Type(list, default=[])


class CrosslinkPlugin(BasePlugin[CrosslinkPluginConfig]):
    def on_config(self, config: MkDocsConfig, **kwargs) -> Config:
        """
        Called once when the config is loaded.
        It will make modify the config and initialize this plugin.
        """
        # Make sure that the CSS and JS badge files are included on every page
        warning("Hello, World!")
        self.crosslinks = parse_crosslinks_list(self.config.crosslinks, "crosslinks")

        #@Todo: use crosslinks
        warning(f"config file: '{config.config_file_path}'")
        root_dir = Path(config.config_file_path).parent
        file_root = root_dir / "site_a" / "docs"
        fc = FileCache(file_root)
        warning(f"cache: {fc}")

        #@TODO: move to replacer
        for crosslink in self.crosslinks:
            search_target = f"{self.config.prefix}{crosslink.name}{self.config.suffix}"


        self.replacer = Replacer()
        return config


    # @event_priority(50)
    # Earlier than most other plugins to update the tags properly. Did not work
    # SEE https://www.mkdocs.org/dev-guide/plugins/#event-priorities
    def on_page_content(self, html: str, page: Page, config: MkDocsConfig, files: Files) -> str:
        """
        The page_content event is called after the Markdown text is rendered to HTML (but before being passed to a template) and can be used to alter the HTML body of the page.
        See: https://www.mkdocs.org/dev-guide/plugins/#on_page_content
        """
        try:
            self.replacer.handle_page(html)
                

            return html
        except Exception as error:
            raise mkdocs.exceptions.PluginError(str(error))

