import re
from typing import Dict, Any, List, Optional


class LayoutAnalyzer:
    """Formats PP-Structure regions into structured text for LLM consumption.

    Pure domain service — takes the regions list produced by PP-Structure
    (typed regions: title, text, table, list, figure) and produces
    structured text that preserves document layout for the LLM.
    """

    def format_for_llm(
        self,
        regions: List[Dict[str, Any]],
        char_budget: int = 3500,
    ) -> Optional[str]:
        """Format PP-Structure regions into LLM-ready text.

        Args:
            regions: List of dicts with keys: type, bbox, page, content.
            char_budget: Maximum character length for the output.

        Returns:
            Structured text string, or None if no regions.
        """
        if not regions:
            return None

        parts: List[str] = []

        for region in regions:
            region_type = region.get("type", "text")
            content = region.get("content", "").strip()
            if not content:
                continue

            if region_type == "title":
                parts.append(f"[HEADER] {content}")

            elif region_type == "table":
                md_table = self._html_table_to_markdown(content)
                if md_table:
                    parts.append(md_table)

            elif region_type == "figure":
                parts.append("[Figure]")

            else:
                # text, list, or unknown — include as-is
                parts.append(content)

        if not parts:
            return None

        result = "\n".join(parts)

        # Smart truncation: trim from the end if over budget
        if len(result) > char_budget:
            result = result[:char_budget].rsplit("\n", 1)[0]

        return result

    @staticmethod
    def _html_table_to_markdown(html: str) -> Optional[str]:
        """Convert an HTML table string to a markdown table."""
        if not html:
            return None

        rows: List[List[str]] = []
        # Split on </tr> to get rows
        tr_parts = re.split(r'</tr>', html, flags=re.IGNORECASE)
        for tr in tr_parts:
            if '<td' not in tr.lower() and '<th' not in tr.lower():
                continue
            # Extract cell contents
            cells = re.findall(r'<(?:td|th)[^>]*>(.*?)</(?:td|th)>', tr, re.IGNORECASE | re.DOTALL)
            if cells:
                # Strip nested tags from cell content
                clean_cells = [re.sub(r'<[^>]+>', '', c).strip() for c in cells]
                rows.append(clean_cells)

        if not rows:
            return None

        # Normalise column count
        max_cols = max(len(r) for r in rows)
        for row in rows:
            while len(row) < max_cols:
                row.append("")

        # Build markdown table
        lines = []
        lines.append("| " + " | ".join(rows[0]) + " |")
        lines.append("| " + " | ".join(["---"] * max_cols) + " |")
        for row in rows[1:]:
            lines.append("| " + " | ".join(row) + " |")

        return "\n".join(lines)
