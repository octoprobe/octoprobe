"""
Walks over all *.rst files and writes an error if the section structure does
not follow 'LEVEL_VALID'.
"""

import pathlib
import re
import sys

import typer

app = typer.Typer()

IGNORE_SECTION_CHECK = "IGNORE_SECTION_CHECK"

SECTION_PATTERN = re.compile(
    r'^(=+|#+|~+|\++|-+|\^+|"+)$',
)

LEVEL_VALID = '=-^~"'

CURRENT_DIRECTORY = pathlib.Path().cwd()

# pylint: disable=W0640:cell-var-from-loop
# ruff: noqa: B023  # Function definition does not bind loop variable


class RstValidator:
    def __init__(self) -> None:
        self.errors = 0

    def parse_rst_file(self, filename: pathlib.Path) -> None:
        filename_relative = filename.relative_to(CURRENT_DIRECTORY)
        content = filename.read_text()

        if IGNORE_SECTION_CHECK in content:
            return

        count_section_idx0 = 0
        lines = content.splitlines()
        last_level_idx0 = 0

        for i, line in enumerate(lines):
            if SECTION_PATTERN.match(line):
                level_char = line[0]
                level_idx0 = LEVEL_VALID.find(level_char)

                def warning(msg: str) -> None:
                    print(
                        f"{filename_relative}:{i + 1} Error: Found {level_char}. {msg}",
                        file=sys.stderr,
                    )

                def error(msg: str) -> None:
                    self.errors += 1
                    warning(msg)

                if count_section_idx0 == 0:
                    # The first section MUST be a "="
                    if level_char != "=":
                        error("First title must be a section '='!")
                        return

                if level_char == "=":
                    count_section_idx0 += 1

                if count_section_idx0 > 1:
                    warning("More than one section '='!")
                    return

                # title = lines[i - 1]
                # print(f"{level_idx0} {level_char} {title}", file=sys.stderr)
                if (level_idx0 - last_level_idx0) > 1:
                    expected_levels = [last_level_idx0 + j for j in (0, 1)]
                    expected_text = " or ".join(
                        [
                            LEVEL_VALID[k]
                            for k in expected_levels
                            if k < len(LEVEL_VALID)
                        ]
                    )
                    error(
                        f"Expected {expected_text}",
                    )

                last_level_idx0 = level_idx0

    def parse_directory(self, directory: pathlib.Path) -> None:
        for filename in directory.glob("**/*.rst"):
            self.parse_rst_file(filename)


@app.command()
def validate() -> None:
    v = RstValidator()
    v.parse_directory(CURRENT_DIRECTORY)
    sys.exit(v.errors)


if __name__ == "__main__":
    typer.run(validate)
