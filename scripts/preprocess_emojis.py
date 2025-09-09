import re
import sys
import os

# List your allowed emojis here
ALLOWED_EMOJIS = [
    "🚀",  # rocket
    "⛓️‍💥",  # chain breaking (may appear as a sequence)
    "🐛",  # bug
    "📄",  # page
    "🛡️",  # shield
    "📌",  # pin
]

# Create regex pattern to match any of the listed emojis
emoji_pattern = re.compile("(" + "|".join(re.escape(e) for e in ALLOWED_EMOJIS) + ")")


def replace_emojis(text):
    # Replace each matched emoji with \emoji{...}
    return emoji_pattern.sub(lambda x: r"\emoji{" + x.group(0) + "}", text)


def process_file(filepath):
    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()
    new_content = replace_emojis(content)
    if new_content != content:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(new_content)
        print(f"Processed allowed emojis in {filepath}")


if __name__ == "__main__":
    # Only process CHANGELOG.rst in the current directory or as provided
    filename = "CHANGELOG.rst"
    if len(sys.argv) > 1:
        filename = sys.argv[1]
    if os.path.exists(filename):
        process_file(filename)
    else:
        print(f"{filename} does not exist.")
