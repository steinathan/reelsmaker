import os


def search_file(directory, file) -> str | None:
    assert os.path.isdir(directory)
    import re

    pattern = re.compile(re.escape(file), re.IGNORECASE)
    for cur_path, directories, files in os.walk(directory):
        for filename in files:
            if pattern.search(filename):
                return os.path.join(directory, cur_path, filename)
    return None
