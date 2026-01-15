"""Presentation protocol and types for unified formatting of data structures.

This module defines a protocol for objects that can be presented in tabular format,
along with the type definitions for the presentation specification.
"""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from datetime import datetime
from typing import Protocol, TypedDict

# Scalar values that can appear as leaf values in presentation data.
# These are types that can be straightforwardly serialized as JSON leaf types.
ScalarValue = str | int | float | bool | datetime | None


class PresentationSpec(TypedDict):
    """Specification for presenting an object in tabular format.

    Attributes:
        scalar: Header/metadata fields as key-value pairs.
                These are displayed above the table (e.g., "path: /foo/bar").
        collection: Rows of data for tabular display.
                   Each row is a mapping of column names to scalar values.
    """

    scalar: Mapping[str, ScalarValue]
    collection: Sequence[Mapping[str, ScalarValue]]


class Presentable(Protocol):
    """Protocol for objects that can produce a presentation specification.

    Classes implementing this protocol can be formatted by any formatter
    that understands PresentationSpec, enabling decoupled presentation logic.
    """

    def to_presentation(self) -> PresentationSpec:
        """Convert this object to a presentation specification.

        Returns:
            A PresentationSpec containing scalar metadata and collection rows.
        """
        ...


class TableFormatter:
    """Formats PresentationSpec data as a human-readable table with box-drawing characters."""

    PLACEHOLDER = "-"
    MAX_COL_WIDTH = 80

    def __init__(self, merge_first_column: bool = False) -> None:
        """Initialize the table formatter.

        Args:
            merge_first_column: If True, merge cells in the first column when consecutive
                                rows have the same value. Defaults to False.
        """
        self.merge_first_column = merge_first_column

    def format(self, spec: PresentationSpec) -> str:
        """Format a PresentationSpec as a table string.

        Args:
            spec: The presentation specification to format.

        Returns:
            A formatted string with scalar fields as header and collection as table.
        """
        lines: list[str] = []

        # Format scalar fields as header
        scalar = spec["scalar"]
        if scalar:
            type_ = scalar.get("type")
            path = scalar.get("path")
            if type_ and path:
                lines.append(f"{type_}: {path}")
            elif type_:
                lines.append(str(type_))

            for key, value in scalar.items():
                if key in ("type", "path"):
                    continue
                lines.append(f"  {key}: {self._format_value(value)}")

        # Format collection as table
        collection = spec["collection"]
        if collection:
            if lines:
                # Add separator between header and table
                lines.append("")
            lines.extend(self._format_table(collection, self.merge_first_column))

        return "\n".join(lines)

    def format_presentable(self, obj: Presentable) -> str:
        """Convenience method to format any Presentable object.

        Args:
            obj: An object implementing the Presentable protocol.

        Returns:
            A formatted string representation.
        """
        return self.format(obj.to_presentation())

    def _format_value(self, value: ScalarValue) -> str:
        """Format a scalar value for display."""
        if value is None:
            return self.PLACEHOLDER
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, bool):
            return "yes" if value else "no"
        return str(value)

    def _format_table(
        self, rows: Sequence[Mapping[str, ScalarValue]], merge_first_column: bool
    ) -> list[str]:
        """Format collection rows as a box-drawing table.

        Args:
            rows: The collection rows to format.
            merge_first_column: If True, merge cells in the first column when consecutive
                              rows have the same value.
        """
        if not rows:
            return ["(empty)"]

        # Get all column names from all rows (preserving insertion order)
        columns: list[str] = []
        for row in rows:
            for key in row.keys():
                if key not in columns:
                    columns.append(key)

        # If merging first column, prepare rows with merged values
        processed_rows: list[dict[str, ScalarValue]] = []
        if merge_first_column and columns:
            first_col = columns[0]
            previous_value: ScalarValue = None
            for row in rows:
                current_value = row.get(first_col)
                # If current value equals previous, replace with None to indicate merge
                if current_value == previous_value and previous_value is not None:
                    # Create a new dict with merged cell
                    merged_row = dict(row)
                    merged_row[first_col] = None
                    processed_rows.append(merged_row)
                else:
                    processed_rows.append(dict(row))
                    previous_value = current_value
        else:
            processed_rows = [dict(row) for row in rows]

        # Calculate column widths (using processed rows for accurate width calculation)
        col_widths: dict[str, int] = {}
        for col in columns:
            header_width = len(col)
            max_value_width = max(
                len(self._format_value(row.get(col))) for row in processed_rows
            )
            col_widths[col] = min(self.MAX_COL_WIDTH, max(header_width, max_value_width))

        # Build table
        lines: list[str] = []

        # Top border
        top_segments = [f"━{'━' * col_widths[col]}━" for col in columns]
        lines.append(f"┏{'┳'.join(top_segments)}┓")

        # Header row
        header_cells = [f" {col.ljust(col_widths[col])} " for col in columns]
        lines.append(f"┃{'┃'.join(header_cells)}┃")

        # Header separator
        sep_segments = [f"━{'━' * col_widths[col]}━" for col in columns]
        lines.append(f"┣{'╇'.join(sep_segments)}┫")

        # Data rows
        for i, row in enumerate(processed_rows):
            if i > 0:
                # Row separator
                row_sep_segments = [f"─{'─' * col_widths[col]}─" for col in columns]
                lines.append(f"┠{'┼'.join(row_sep_segments)}┨")

            cells: list[str] = []
            for col in columns:
                value = self._format_value(row.get(col))
                if len(value) > self.MAX_COL_WIDTH:
                    value = value[: self.MAX_COL_WIDTH - 3] + "..."
                cells.append(f" {value.ljust(col_widths[col])} ")
            lines.append(f"┃{'│'.join(cells)}┃")

        # Bottom border
        bottom_segments = [f"━{'━' * col_widths[col]}━" for col in columns]
        lines.append(f"┗{'┷'.join(bottom_segments)}┛")

        return lines

