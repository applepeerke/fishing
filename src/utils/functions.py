import os


def find_filename_path(file_name) -> str:
    """
    Return file paths matching the specified file type in the specified base directory (recursively).
    """
    if not file_name:
        return ''
    app_root = os.getenv("APP_ROOT")
    walk_path = os.path.abspath(os.curdir)
    # Try to find app root
    if app_root in walk_path and walk_path.count(app_root) == 1:
        p = walk_path.find(app_root) + len(app_root)
        walk_path = walk_path[:p]
    # Walk from app root
    for path, dirs, files in os.walk(walk_path):
        for filename in files:
            if filename == file_name:
                return os.path.join(path, filename)
