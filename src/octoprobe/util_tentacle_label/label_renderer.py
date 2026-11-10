"""
Tentacle Label Renderer
"""

from __future__ import annotations

import dataclasses
import itertools
import pathlib
from collections.abc import Iterator

from reportlab.graphics import shapes
from reportlab.lib import colors, pagesizes, units
from reportlab.platypus import SimpleDocTemplate, Table

from ..util_tentacle_label.label_data import LabelData, LabelsData

THIS_FILE = pathlib.Path(__file__)


@dataclasses.dataclass(frozen=True)
class LayoutLine:
    y: float
    fontsize: float


@dataclasses.dataclass(frozen=True)
class LayoutLabelBolzone:
    """
    The geomatrical layout of a bolzone label.
    """

    width: float = 88.0 * units.mm
    height: float = 15.5 * units.mm
    width_l: float = 5.0 * units.mm
    width_margin: float = 8.0 * units.mm
    x_l: float = 0.0
    x_r: float = x_l + width
    x_l_line: float = x_l + width_l
    x_r_line: float = x_r - width_l
    x_l_label: float = x_l + width_margin
    x_r_label: float = x_r - width_margin
    y_b: float = 0
    y_text_start: float = 0

    @property
    def y_t(self) -> float:
        return self.height

    @property
    def polylines(self) -> Iterator[shapes.PolyLine]:
        for polyline in (
            (
                (self.x_l, self.y_t),
                (self.x_l_line, self.y_t),
                (self.x_l_line, self.y_b),
                (self.x_l, self.y_b),
            ),
            (
                (self.x_r, self.y_t),
                (self.x_r_line, self.y_t),
                (self.x_r_line, self.y_b),
                (self.x_r, self.y_b),
            ),
        ):
            yield shapes.PolyLine(
                polyline,  # type: ignore[arg-type]
                strokeWidth=0.1,
                strokeColor=colors.black,
            )


@dataclasses.dataclass(frozen=True)
class LayoutLabelBolzoneDue(LayoutLabelBolzone):
    """
    The geomatrical layout of a bolzone_duo label.
    """

    height: float = 33.0 * units.mm
    y_text_start: float = 22.0


@dataclasses.dataclass(frozen=True)
class RendererLabelBolzone:
    """
    Layout with three lines and left and right text
    """

    layout_label: LayoutLabelBolzone

    def text(
        self,
        text_line: LayoutLine,
        text: str,
        flip: bool = False,
        bold: bool = False,
    ) -> shapes.String:
        x = self.layout_label.x_r_label if flip else self.layout_label.x_l_label
        anchor = "end" if flip else "start"
        font = "Helvetica-Bold" if bold else "Helvetica"

        return shapes.String(
            x,
            text_line.y + self.layout_label.y_text_start,
            text=text,
            fontSize=text_line.fontsize,
            textAnchor=anchor,  # type: ignore[arg-type]
            fontName=font,
        )

    def draw(self, label: LabelData) -> shapes.Drawing:
        d = shapes.Drawing(self.layout_label.width, self.layout_label.height)

        for polyline in self.layout_label.polylines:
            d.add(polyline)

        line_a = LayoutLine(y=10.0 * units.mm, fontsize=14.0)
        line_b = LayoutLine(y=5.5 * units.mm, fontsize=10.0)
        line_c = LayoutLine(y=1.5 * units.mm, fontsize=10.0)

        d.add(self.text(line_a, text=label.serial, bold=True))
        d.add(self.text(line_a, text=label.tentacle_tag, flip=True, bold=True))

        d.add(self.text(line_b, text=label.testbed_instance))
        d.add(self.text(line_b, text=label.description, flip=True))

        d.add(self.text(line_c, text=label.testbed_name))
        d.add(self.text(line_c, text=label.tentacle_type, flip=True))

        return d


def create_report(
    filename: pathlib.Path,
    layout_label: LayoutLabelBolzone,
    labels: LabelsData,
) -> None:
    """
    Creates a pdf report with labels to be placed on the tentacle
    """
    assert isinstance(filename, pathlib.Path)
    assert isinstance(layout_label, LayoutLabelBolzone)
    assert isinstance(labels, LabelsData)

    filename.parent.mkdir(parents=True, exist_ok=True)

    if len(labels) % 2 == 1:
        # Add empty label to the end
        labels.append(LabelData())

    doc = SimpleDocTemplate(
        filename=str(filename),
        pagesize=pagesizes.A4,
        rightMargin=10.0 * units.mm,
        leftMargin=10.0 * units.mm,
        topMargin=10.0 * units.mm,
        bottomMargin=10.0 * units.mm,
    )

    renderer = RendererLabelBolzone(layout_label=layout_label)
    all_labels: list[shapes.Drawing] = []
    for label in labels:
        all_labels.append(renderer.draw(label=label))

    labels_rows = list(itertools.batched(all_labels, 2, strict=False))
    table = Table(
        labels_rows,
        colWidths=(layout_label.width, layout_label.width),
        rowHeights=layout_label.height,
    )

    doc.build([table])


def main() -> None:
    labels = LabelsData(
        [
            LabelData(
                serial="2d2e",
                tentacle_tag="ESP828266_GENERIC",
                tentacle_type="MCU",
                description="esp8266",
                testbed_name="testbed_micropython",
                testbed_instance="au_damien_1",
            ),
            LabelData(
                serial="2d2f",
                tentacle_tag="ESP828266_GENERIC",
                tentacle_type="MCU",
                description="esp8266",
                testbed_name="testbed_micropython",
                testbed_instance="au_damien_1",
            ),
            LabelData(
                serial="2d2g",
                tentacle_tag="ESP828266_GENERIC",
                tentacle_type="MCU",
                description="esp8266",
                testbed_name="testbed_micropython",
                testbed_instance="au_damien_1",
            ),
        ]
    )

    filename = THIS_FILE.with_suffix(".pdf")

    create_report(
        filename=filename, layout_label=LayoutLabelBolzoneDue(), labels=labels
    )


if __name__ == "__main__":
    main()
