#!/usr/bin/env bash
# Usage: [PORT]
# Builds the site. If [PORT] is specified, the site will be served on that port

# Change into the project root
cd -- "$( dirname -- "${BASH_SOURCE[0]}" )"

if [[ -f venv/bin/activate ]]; then
    echo "[*] Using virtual environment"
    source venv/bin/activate
fi

# Install any dependencies
python3 -m pip install -r requirements.txt

# Install the pip package
python3 -m pip install .

# Build main site
# Needs to be first, since the other files will be copied into it
python3 -m mkdocs build || exit 1

build_sub_site() {
    # Switch into directory, build site, copy to the main site, switch back to initial directory
    # Hard assumption: $1 MUST NOT contain a path separator (relative and not nested)
    cd "$1"
    python3 -m mkdocs build
    cp -r site "../site/$1"
    cd ..
}

build_sub_site site_a
build_sub_site site_b

# serve site
if [[ $# -eq 1 ]]; then
    cd site
    python3 -m http.server "$1"
fi
