import os
# pip dependency
import mkdocs
from mkdocs.plugins import BasePlugin
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.structure.pages import Page
from mkdocs.structure.files import Files
# local files
from .config import parse_crosslinks_list, create_local_crosslink, CrosslinkPluginConfig, CrosslinkSite
from .replacer import Replacer
from .profiling import Profiler
from .migrate_links import patch_source_file_links_inplace

PROFILER = Profiler()


class CrosslinkPlugin(BasePlugin[CrosslinkPluginConfig]):
    @PROFILER.profile
    def on_config(self, config: MkDocsConfig, **kwargs) -> MkDocsConfig:
        """
        Called once when the config is loaded.
        It will make modify the config and initialize this plugin.
        """
        self.crosslinks: dict[str,CrosslinkSite] = {}
        parse_crosslinks_list(self.config.crosslinks, "crosslinks", self.crosslinks)

        # If not already created/overwritten by the user, provide a default value for 'local'
        local_crosslink = create_local_crosslink(config)
        if local_crosslink.name not in self.crosslinks:
            self.crosslinks[local_crosslink.name] = local_crosslink

        self.replacer = Replacer(list(self.crosslinks.values()), self.config) # @TODO: make it work with a dict?
        return config

    @PROFILER.profile
    def on_page_markdown(self, markdown: str, page: Page, config: MkDocsConfig, files: Files) -> str:
        """
        If the special flag is set, we can patch the source files so that we can migrate from plugins like ezlinks to this one.
        """
        if self.config.dangerous_migrate_links:
            path = os.path.join(config.docs_dir, page.file.src_path)
            try:
                patch_source_file_links_inplace(path, self.replacer)
            except Exception as ex:
                raise mkdocs.exceptions.PluginError(f"Error migrating {path}: {ex}")

    # @event_priority(50)
    # SEE https://www.mkdocs.org/dev-guide/plugins/#event-priorities
    @PROFILER.profile
    def on_page_content(self, html: str, page: Page, config: MkDocsConfig, files: Files) -> str:
        """
        The page_content event is called after the Markdown text is rendered to HTML (but before being passed to a template) and can be used to alter the HTML body of the page.
        See: https://www.mkdocs.org/dev-guide/plugins/#on_page_content
        """
        if self.config.dangerous_migrate_links:
            raise mkdocs.exceptions.PluginError("Build is aborted due to using the 'dangerous_migrate_links' option being enabled. Your source files have been patched, so disable this option again to actually build the site.")
        try:
            html = self.replacer.handle_page(page.file.src_path, html)
            return html
        except Exception as error:
            raise mkdocs.exceptions.PluginError(str(error))

    def on_post_build(self, config: MkDocsConfig) -> None:
        if self.config.show_profiling_results:
            PROFILER.log_stats()
