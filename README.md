# mkdocs-crosslink-plugin
[![PyPI version](https://img.shields.io/pypi/v/mkdocs-crosslink-plugin)](https://pypi.org/project/mkdocs-crosslink-plugin/)
![License](https://img.shields.io/pypi/l/mkdocs-crosslink-plugin)
![Python versions](https://img.shields.io/pypi/pyversions/mkdocs-crosslink-plugin)

This package allows you to add links to other MkDocs (or similar page generator) sites.

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


On your pages you can reference links and images to other sites with the `x-SITE_NAME:FILE_NAME` syntax.
For example to load the image `my-image.png` somewhere from the `https://example.com/` (crosslink `example`) you would use the syntax:
```markdown
![My Image](x-example:my-image.png)
```

If multiple files with the exact same name exist, there is currently now way to reference the correct one.
In the future I plan to let you specify a part of the path to select the correct file.


## Testing

Some very basic tests are in `docs` (main site), `site_a` (crosslink alpha), and `site_b` (crosslink bravo).
You can build and serve the test site by running `./build.sh`.
