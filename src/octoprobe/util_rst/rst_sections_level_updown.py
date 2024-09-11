from __future__ import annotations

import pathlib

import typer

from .rst_sections_validator import LEVEL_VALID, SECTION_PATTERN

app = typer.Typer()


class RstUpDown:
    def __init__(self) -> None:
        self.errors = 0

    def level_up(self, filename: pathlib.Path, level_up: int):
        content = filename.read_text()
        lines = content.splitlines()

        for i, line in enumerate(lines):
            if SECTION_PATTERN.match(line):
                level_char = line[0]
                level_idx0 = LEVEL_VALID.find(level_char)

                new_level_idx0 = level_idx0 + level_up
                new_level_char = LEVEL_VALID[new_level_idx0]
                lines[i] = line.replace(level_char, new_level_char)

        filename.write_text("\n".join(lines))


@app.command()
def up(filename: pathlib.Path) -> None:
    v = RstUpDown()
    v.level_up(filename=filename, level_up=-1)


@app.command()
def down(filename: pathlib.Path) -> None:
    v = RstUpDown()
    v.level_up(filename=filename, level_up=1)
