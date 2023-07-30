import json
from pathlib import Path

class MultiValueDict:
    def __init__(self) -> None:
        self._data = {}

    def append(self, key: str, value: str):
        if key in self._data:
            self._data[key].append(value)
        else:
            self._data[key] = [value]

    def get(self, key: str) -> list[str]:
        return self._data.get(key, [])
    
    def __str__(self) -> str:
        return json.dumps(self._data)

class FileCache:
    def __init__(self, files_root: Path, max_extension_count: int = 5) -> None:
        # A list of caches: 0 -> full file name, 1 -> without first file extension, 2 -> without second file extension, ...
        # The caches will be searched in that order. Thus for example searching for "jquery" would return "jquery.min.js".
        self.caches = [MultiValueDict() for _ in range(max_extension_count)]

        if not files_root.exists():
            raise Exception(f"Directory '{files_root}' does not exist")
        elif not files_root.is_dir():
            raise Exception(f"'{files_root}' is not a directory")

        for path in files_root.rglob("*"):
            self._add_file_to_caches(path, files_root)

    def _add_file_to_caches(self, path: Path, files_root: Path):
        if path.is_file():
            name = path.name
            path_str = str(path) #path.relative_to(files_root).
            # Add file name to caches
            for cache in self.caches:
                cache.append(name, path_str)
                # remove the last extension from the name
                parts = name.rsplit(".", 1)
                if len(parts) == 2:
                    name = parts[0]
                else:
                    # There is nothing left to split off -> exit inner look
                    break

    def get(self, key: str) -> list[str]:
        # Search the caches: first interpret it as a full file name, then as a file name without the last extension, then a filename without the last two extensions, etc
        # So for example "jquery" would match "jquery", "jquery.js", "jquery.min.js", and finally "jquery.min.js.bak" in that order
        for cache in self.caches:
            if result := cache.get(key):
                return result
        
        # No matches found
        return []
    
    def __str__(self) -> str:
        return "<FileCache>" + "".join([f"\t\nLevel {index}: {cache}" for index, cache in enumerate(self.caches)]) + "\n</FileCache>"

