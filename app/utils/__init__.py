import re
from .path_util import *


def split_by_dot_or_newline(text):
    """Splits text by either "." or "\n", handling multiple consecutive delimiters."""
    return re.split(r"\.\s*|\n", text)
