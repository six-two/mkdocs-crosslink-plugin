from pathlib import Path
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


class CrosslinkPluginConfig(Config):
    enabled = Type(bool, default=True)


class CrosslinkPlugin(BasePlugin[CrosslinkPluginConfig]):
    def on_config(self, config: MkDocsConfig, **kwargs) -> Config:
        """
        Called once when the config is loaded.
        It will make modify the config and initialize this plugin.
        """
        # Make sure that the CSS and JS badge files are included on every page
        warning("Hello, World!")
        self.cross_links = {
            "a": {
                "root_dir": "site_a/docs",
                "target_url": "https://example.com/site_a",
                "directory_urls": True,
            }
        }

        warning(f"config file: '{config.config_file_path}'")
        root_dir = Path(config.config_file_path).parent
        file_root = root_dir / "site_a" / "docs"
        fc = FileCache(file_root)
        warning(f"cache: {fc}")

        return config

    @event_priority(50)
    # Earlier than most other plugins so that other link plugins will not receive data intended for this plugin
    # SEE https://www.mkdocs.org/dev-guide/plugins/#event-priorities
    def on_page_markdown(self, markdown: str, page: Page, config: MkDocsConfig, files: Files) -> str:
        """
        The page_markdown event is called after the page's markdown is loaded from file and can be used to alter the Markdown source text. The meta- data has been stripped off and is available as page.meta at this point.
        """
        try:
            # We replace the links with a custom protocol, since otherwise we would get warnings like the following:
            # WARNING  -  Documentation file 'index.md' contains a link to '@a:page_a.md' which is not found in the documentation files.
            for key in self.cross_links:
                markdown = markdown.replace(f"@{key}:", f"crosslink://{key}:")
            return markdown
        except Exception as error:
            raise mkdocs.exceptions.PluginError(str(error))


    # @event_priority(50)
    # Earlier than most other plugins to update the tags properly. Did not work
    # SEE https://www.mkdocs.org/dev-guide/plugins/#event-priorities
    def on_page_content(self, html: str, page: Page, config: MkDocsConfig, files: Files) -> str:
        """
        The page_content event is called after the Markdown text is rendered to HTML (but before being passed to a template) and can be used to alter the HTML body of the page.
        See: https://www.mkdocs.org/dev-guide/plugins/#on_page_content
        """
        try:
            warning("TODO: search for <a href='X'... and <img src='X'...\nShould either use HTML parser or proper regex")
            # Undo replacement for anything that was not a link?
            for key in self.cross_links:
                html = html.replace(f"crosslink://{key}:", f"@{key}:")
            return html
        except Exception as error:
            raise mkdocs.exceptions.PluginError(str(error))

