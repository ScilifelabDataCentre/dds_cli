import re
import sys
import os

# Emoji regex pattern (simple, covers most emojis)
emoji_pattern = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # emoticons
    "\U0001F300-\U0001F5FF"  # symbols & pictographs
    "\U0001F680-\U0001F6FF"  # transport & map symbols
    "\U0001F700-\U0001F77F"  # alchemical symbols
    "\U0001F780-\U0001F7FF"  # Geometric Shapes Extended
    "\U0001F800-\U0001F8FF"  # Supplemental Arrows-C
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols and Pictographs
    "\U0001FA00-\U0001FA6F"  # Chess Symbols
    "\U0001FA70-\U0001FAFF"  # Symbols and Pictographs Extended-A
    "\U00002702-\U000027B0"  # Dingbats
    "\U000024C2-\U0001F251"
    "]+",
    flags=re.UNICODE,
)


def replace_emojis(text):
    return emoji_pattern.sub(lambda x: r"\emoji{" + x.group(0) + "}", text)


def process_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    new_content = replace_emojis(content)
    if new_content != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Processed emojis in {filepath}")


def walk_and_process(root, exts=(".rst", ".md")):
    for dirpath, _, filenames in os.walk(root):
        for filename in filenames:
            if filename.endswith(exts):
                process_file(os.path.join(dirpath, filename))


if __name__ == "__main__":
    # Default to 'docs' if no arguments
    folder = sys.argv[1] if len(sys.argv) > 1 else "docs"
    walk_and_process(folder)
