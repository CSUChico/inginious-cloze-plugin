#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
from dataclasses import dataclass, field
from html.parser import HTMLParser
from pathlib import Path
from typing import Union

from convert_moodle_cloze_xml import _read_quiz_root, _sanitize_moodle_html


Node = Union[str, "ElementNode"]


@dataclass
class ElementNode:
    tag: str
    attrs: list[tuple[str, str | None]] = field(default_factory=list)
    children: list[Node] = field(default_factory=list)


class _HtmlTreeBuilder(HTMLParser):
    VOID_TAGS = {"br", "hr", "img", "input", "meta", "link"}

    def __init__(self) -> None:
        super().__init__(convert_charrefs=False)
        self.root = ElementNode("root")
        self.stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = ElementNode(tag.lower(), attrs=list(attrs))
        self.stack[-1].children.append(node)
        if tag.lower() not in self.VOID_TAGS:
            self.stack.append(node)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        for index in range(len(self.stack) - 1, 0, -1):
            if self.stack[index].tag == lowered:
                del self.stack[index:]
                break

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.stack[-1].children.append(ElementNode(tag.lower(), attrs=list(attrs)))

    def handle_data(self, data: str) -> None:
        if data:
            self.stack[-1].children.append(data)

    def handle_entityref(self, name: str) -> None:
        self.stack[-1].children.append(f"&{name};")

    def handle_charref(self, name: str) -> None:
        self.stack[-1].children.append(f"&#{name};")


def _render_attrs(attrs: list[tuple[str, str | None]]) -> str:
    rendered = []
    for key, value in attrs:
        if value is None:
            rendered.append(key)
        else:
            escaped = (
                value.replace("&", "&amp;")
                .replace('"', "&quot;")
                .replace("<", "&lt;")
                .replace(">", "&gt;")
            )
            rendered.append(f'{key}="{escaped}"')
    return (" " + " ".join(rendered)) if rendered else ""


def _render_node(node: Node) -> str:
    if isinstance(node, str):
        return node
    attrs = _render_attrs(node.attrs)
    inner = "".join(_render_node(child) for child in node.children)
    if node.tag in _HtmlTreeBuilder.VOID_TAGS:
        return f"<{node.tag}{attrs}>"
    return f"<{node.tag}{attrs}>{inner}</{node.tag}>"


def _text_content(node: Node) -> str:
    if isinstance(node, str):
        return node
    return "".join(_text_content(child) for child in node.children)


def _clone_node(node: Node) -> Node:
    if isinstance(node, str):
        return node
    return ElementNode(node.tag, list(node.attrs), [_clone_node(child) for child in node.children])


def _children_with_tag(node: ElementNode, tag: str) -> list[ElementNode]:
    return [child for child in node.children if isinstance(child, ElementNode) and child.tag == tag]


def _table_rows(table: ElementNode) -> list[ElementNode]:
    rows: list[ElementNode] = []
    for child in table.children:
        if isinstance(child, ElementNode) and child.tag in {"tbody", "thead"}:
            rows.extend(_children_with_tag(child, "tr"))
        elif isinstance(child, ElementNode) and child.tag == "tr":
            rows.append(child)
    return rows


def _row_cells(row: ElementNode) -> list[ElementNode]:
    return [
        child
        for child in row.children
        if isinstance(child, ElementNode) and child.tag in {"td", "th"}
    ]


def _attrs_to_dict(attrs: list[tuple[str, str | None]]) -> dict[str, str]:
    return {key: (value or "") for key, value in attrs}


def _looks_like_tlb_page_table(table: ElementNode) -> bool:
    rows = _table_rows(table)
    if len(rows) < 2:
        return False
    headers = [
        re.sub(r"\s+", " ", _text_content(cell)).strip().lower()
        for cell in _row_cells(rows[0])
    ]
    return headers == ["tlb", "page table"]


def _append_class(attrs: list[tuple[str, str | None]], class_name: str) -> list[tuple[str, str | None]]:
    updated: list[tuple[str, str | None]] = []
    found = False
    for key, value in attrs:
        if key.lower() == "class":
            classes = [part for part in (value or "").split() if part]
            if class_name not in classes:
                classes.append(class_name)
            updated.append((key, " ".join(classes)))
            found = True
        else:
            updated.append((key, value))
    if not found:
        updated.append(("class", class_name))
    return updated


def _rewrite_cache_cell_content(node: ElementNode) -> ElementNode:
    if node.tag != "td":
        return node
    raw = "".join(_render_node(child) for child in node.children).strip()
    if not raw or "<table" in raw.lower() or "class=\"cloze-input\"" in raw:
        return node

    if "Data =" in raw:
        parts = re.split(r'<div class="cloze-converted-break"></div>', raw, flags=re.IGNORECASE)
        parts = [part.strip() for part in parts if part.strip()]
        if len(parts) >= 2:
            meta = parts[0]
            data_lines = "\n".join(parts[1:])
            return ElementNode(
                "td",
                list(node.attrs),
                [
                    ElementNode("div", [("class", "cloze-cache-meta")], [meta]),
                    ElementNode(
                        "pre",
                        [("class", "cloze-converted-code cloze-cache-bytes")],
                        [data_lines],
                    ),
                ],
            )

    if "PPN=" in raw and 'cloze-converted-break' in raw:
        lines = re.split(r'<div class="cloze-converted-break"></div>', raw, flags=re.IGNORECASE)
        lines = [line.strip() for line in lines if line.strip()]
        if len(lines) >= 2:
            children: list[Node] = []
            for line in lines:
                children.append(ElementNode("div", [("class", "cloze-cache-meta")], [line]))
            return ElementNode("td", list(node.attrs), children)

    return node


def _transform_nodes(nodes: list[Node]) -> list[Node]:
    transformed: list[Node] = []
    for node in nodes:
        transformed.extend(_transform_node(node))
    return transformed


def _transform_node(node: Node) -> list[Node]:
    if isinstance(node, str):
        return [node]

    transformed_children = _transform_nodes(node.children)
    current = ElementNode(node.tag, list(node.attrs), transformed_children)

    if current.tag == "span":
        return current.children

    if current.tag == "table" and _looks_like_tlb_page_table(current):
        rows = _table_rows(current)
        content_cells = _row_cells(rows[1])
        if len(content_cells) == 2:
            return [
                ElementNode(
                    "div",
                    [("class", "cloze-comparison-sections")],
                    [
                        ElementNode(
                            "section",
                            [("class", "cloze-comparison-section")],
                            [
                                ElementNode("h4", [("class", "cloze-comparison-heading")], ["TLB"]),
                                ElementNode(
                                    "div",
                                    [("class", "cloze-comparison-body")],
                                    [_clone_node(child) for child in content_cells[0].children],
                                ),
                            ],
                        ),
                        ElementNode(
                            "section",
                            [("class", "cloze-comparison-section")],
                            [
                                ElementNode("h4", [("class", "cloze-comparison-heading")], ["Page Table"]),
                                ElementNode(
                                    "div",
                                    [("class", "cloze-comparison-body")],
                                    [_clone_node(child) for child in content_cells[1].children],
                                ),
                            ],
                        ),
                    ],
                )
            ]

    if current.tag in {"table", "pre"}:
        current.attrs = _append_class(current.attrs, "cloze-converted-table" if current.tag == "table" else "cloze-converted-code")

    if current.tag == "td":
        current = _rewrite_cache_cell_content(current)

    return [current]


def _cleanup_cache_html(text: str) -> str:
    cleaned = _sanitize_moodle_html(text)
    parser = _HtmlTreeBuilder()
    parser.feed(cleaned)
    parser.close()
    transformed = _transform_nodes(parser.root.children)
    rendered = "".join(_render_node(node) for node in transformed)

    rendered = re.sub(r"(<li>\s*(?:<p>)?)\s*\.\s*", r"\1", rendered, flags=re.IGNORECASE)
    rendered = re.sub(r"<p>\s*</p>", "", rendered, flags=re.IGNORECASE)
    rendered = re.sub(r"\s+\n", "\n", rendered)
    return rendered.strip()


def convert_moodle_cache_xml(path: Path, keep_names: bool = False) -> dict[str, list[dict[str, str]]]:
    root = _read_quiz_root(path)
    variants: list[dict[str, str]] = []

    cloze_index = 0
    for question in root.findall("question"):
        if question.get("type") != "cloze":
            continue

        cloze_index += 1
        name = (question.findtext("name/text") or "").strip() or f"Question {cloze_index}"
        text = question.findtext("questiontext/text")
        if text is None or not text.strip():
            raise ValueError(f"Question {cloze_index} ({name!r}) is missing questiontext/text.")

        variants.append(
            {
                "id": str(cloze_index - 1),
                "name": name if keep_names else "",
                "text": _cleanup_cache_html(text),
            }
        )

    return {"variants": variants}


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert cache/TLB Moodle quiz XML cloze questions into a cache-optimized cloze variants JSON format."
    )
    parser.add_argument("input", help="Path to the Moodle quiz XML file.")
    parser.add_argument(
        "-o",
        "--output",
        help="Path to the output JSON file. Defaults to the input filename with a .json suffix.",
    )
    parser.add_argument(
        "--keep-names",
        action="store_true",
        help="Keep Moodle question names as variant names instead of stripping them from student-facing output.",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    output_path = Path(args.output) if args.output else input_path.with_suffix(".json")
    payload = convert_moodle_cache_xml(input_path, keep_names=args.keep_names)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Wrote {len(payload['variants'])} variant(s) to {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
