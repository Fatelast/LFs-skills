#!/usr/bin/env python3
"""Validate SVG and wrap it as React or Vue icon components."""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

JSX_ATTRS = {
    "stroke-width": "strokeWidth",
    "stroke-linecap": "strokeLinecap",
    "stroke-linejoin": "strokeLinejoin",
    "stroke-miterlimit": "strokeMiterlimit",
    "fill-rule": "fillRule",
    "clip-rule": "clipRule",
    "clip-path": "clipPath",
    "class": "className",
    "tabindex": "tabIndex",
    "aria-hidden": "aria-hidden",
}


def read_svg(path: Path) -> str:
    svg = path.read_text(encoding="utf-8").strip()
    try:
        ET.fromstring(svg)
    except ET.ParseError as exc:
        raise SystemExit(f"Invalid SVG XML: {exc}") from exc
    if not re.search(r"<svg[\s>]", svg):
        raise SystemExit("Input does not contain a root <svg> element.")
    return svg


def to_pascal_case(name: str) -> str:
    parts = re.split(r"[^a-zA-Z0-9]+", name)
    result = "".join(part[:1].upper() + part[1:] for part in parts if part)
    if not result:
        raise SystemExit("Component name cannot be empty.")
    if result[0].isdigit():
        result = "Icon" + result
    return result


def svg_to_jsx(svg: str) -> str:
    for source, target in JSX_ATTRS.items():
        svg = re.sub(rf"\b{re.escape(source)}=", f"{target}=", svg)
    svg = re.sub(r'width="24"', 'width={24}', svg, count=1)
    svg = re.sub(r'height="24"', 'height={24}', svg, count=1)
    svg = re.sub(r'strokeWidth="([0-9.]+)"', r'strokeWidth={\1}', svg)
    svg = re.sub(r'<svg\b([^>]*)>', lambda m: '<svg' + m.group(1) + ' {...props}>', svg, count=1)
    return svg


def indent(text: str, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line if line.strip() else line for line in text.splitlines())


def react_component(svg: str, name: str) -> str:
    component_name = to_pascal_case(name)
    jsx = indent(svg_to_jsx(svg), 4)
    return f'''import type {{ SVGProps }} from "react";

export function {component_name}(props: SVGProps<SVGSVGElement>) {{
  return (
{jsx}
  );
}}
'''


def vue_component(svg: str, name: str) -> str:
    component_name = to_pascal_case(name)
    body = indent(svg, 2)
    return f'''<script setup lang="ts">
defineOptions({{ name: "{component_name}" }});
</script>

<template>
{body}
</template>
'''


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("svg", type=Path, help="Path to an SVG file")
    parser.add_argument("--name", default="GeneratedIcon", help="Component name")
    parser.add_argument("--format", choices=("react", "vue", "svg"), default="react")
    parser.add_argument("--validate-only", action="store_true")
    args = parser.parse_args()

    svg = read_svg(args.svg)
    if args.validate_only:
        print("SVG is valid.")
        return 0
    if args.format == "react":
        print(react_component(svg, args.name))
    elif args.format == "vue":
        print(vue_component(svg, args.name))
    else:
        print(svg)
    return 0


if __name__ == "__main__":
    sys.exit(main())
