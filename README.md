# mkdocs-crosslink-plugin
[![PyPI version](https://img.shields.io/pypi/v/mkdocs-crosslink-plugin)](https://pypi.org/project/mkdocs-crosslink-plugin/)
![License](https://img.shields.io/pypi/l/mkdocs-crosslink-plugin)
![Python versions](https://img.shields.io/pypi/pyversions/mkdocs-crosslink-plugin)

This package allows you to add links to other MkDocs sites (or sites created with similar page generator).

## Usage

First install the PyPI package:
```bash
pip install mkdocs-crosslink-plugin
```

Add something like the following to your `mkdocs.yml`:
```yaml
plugins:
- search
- crosslink:
    crosslinks:
    - name: alpha
      source_dir: site_a/docs
      target_url: http://localhost:8000/site_a/
      use_directory_urls: False
    - name: "example"
      source_dir: /var/www/html/example.com/
      target_url: https://example.com/
      use_directory_urls: True
```

Each crosslink has the following attributes:

- `name`: How you reference the site.
    By default the schema is `x-NAME:FILE_NAME` (so for example `x-alpha:my-image.png`).
- `source_dir` is the directory containing the Markdown files.
- `target_url` is the path, where the site corresponding to the `source_dir` files are hosted.
- `use_directory_urls` should correspond to the target site's `use_directory_urls` settings.
    - If enabled `path/index.md` will be mapped to `path/` and `path/test.md` will be mapped to `path/test/`.
    - If disabled `path/index.md` will be mapped to `path/index.html` and `path/test.md` will be mapped to `path/test.html`.

Starting with version 0.0.2 you can also define multiple crosslinks at once, by using a glob-like syntax.
Inject a `*` character in the `name`, `source_dir`, and `target_url`.
The plugin will then look for directories matching the `source_dir` glob, create a crosslink for each one that was not defined before, and replace the `*` in the `name` and `target_url` with the same value that it matched in the `source_dir` value.

Starting with version 0.0.2 there is also a builtin `local` crosslink, which can be used to reference files in the current site, similar to other autolink tools.

On your pages you can reference links and images to other sites with the `x-SITE_NAME:FILE_NAME` syntax.
For example to load the image `my-image.png` somewhere from the `https://example.com/` (crosslink `example`) you would use the syntax:
```markdown
![My Image](x-example:my-image.png)
```

If multiple files with the exact same name exist, there is currently now way to reference the correct one.
In the future I plan to let you specify a part of the path to select the correct file.
From 0.0.2 on: For index files (`index.md` or `index.html`) you can reference them by the name of the parent's directory followed by a slash.
So `/path/to/some/index.md` can be referenced as `some/`.

## Compatibility with other autolink plugins

In theory, this plugin should work side by side with other autolink plugins.
This is because the default schema `x-NAME:` is basically a fake URL schema that any other plugins should not touch.
At the same time this plugin ignores normal links, which are processed by other autolink plugins.

Known problems exist with [mkdocs-ezlinks-plugin](https://github.com/orbikm/mkdocs-ezlinks-plugin/) because it expects custom URL schemas to be followed by `//` (like `x-NAME://`) as can be seen by the [`mailto:` issue](https://github.com/orbikm/mkdocs-ezlinks-plugin/issues/48).
You can work around this, by using links followed by a double slash and setting the correct suffix in the plugin settings:
```yaml
plugins:
  - search
  - crosslink:
      suffix: "://"
      crosslinks:
      - name: "site_a"
        ...
```


## Testing

Some very basic tests are in `docs` (main site), `site_a` (crosslink alpha), and `site_b` (crosslink bravo).
You can build and serve the test site by running `./build.sh`.

## Notable changes

### Version 0.0.3

- Just some bug fixes

### Version 0.0.2

- Added builtin `local` crosslink
- Reference `index.md` as `<PARENT_DIR_NAME>/`
- Added glob support for crosslinks
- Added profiling option (`show_profiling_results: True`)
