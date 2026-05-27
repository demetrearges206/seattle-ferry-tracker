#!/usr/bin/env python3
"""Fetches Figma node JSON + rendered PNGs and writes them to figma-specs/."""
import os
import re
import json
import urllib.request
import urllib.parse
from pathlib import Path

FIGMA_API_KEY = os.environ["FIGMA_API_KEY"]
FIGMA_URLS = os.environ["FIGMA_URLS"]


def figma_request(path):
    url = f"https://api.figma.com/v1{path}"
    req = urllib.request.Request(url, headers={"X-Figma-Token": FIGMA_API_KEY})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read())


def parse_urls(urls_str):
    """Returns dict of file_key -> [node_ids in colon format]."""
    file_nodes = {}
    for url in urls_str.split(","):
        url = url.strip()
        file_match = re.search(r"/design/([^/?]+)", url) or re.search(r"/file/([^/?]+)", url)
        node_match = re.search(r"node-id=([^&]+)", url)
        if not file_match or not node_match:
            print(f"WARNING: could not parse URL: {url}")
            continue
        file_key = file_match.group(1)
        node_id = urllib.parse.unquote(node_match.group(1)).replace("-", ":")
        file_nodes.setdefault(file_key, []).append(node_id)
    return file_nodes


def extract_color(paint):
    if paint.get("type") == "SOLID":
        c = paint["color"]
        a = paint.get("opacity", 1) * c.get("a", 1)
        r, g, b = int(c["r"] * 255), int(c["g"] * 255), int(c["b"] * 255)
        return f"rgba({r},{g},{b},{a:.2f})" if a < 1 else f"#{r:02x}{g:02x}{b:02x}"
    return paint.get("type", "unknown")


def node_summary_lines(node, depth=0):
    lines = []
    indent = "  " * depth
    name = node.get("name", "unnamed")
    ntype = node.get("type", "")
    bb = node.get("absoluteBoundingBox") or {}
    w, h = bb.get("width", 0), bb.get("height", 0)
    lines.append(f"{indent}{ntype}: \"{name}\" ({w:.0f}x{h:.0f})")

    # Auto-layout
    if node.get("layoutMode"):
        props = [f"direction={node['layoutMode']}"]
        if node.get("itemSpacing"):
            props.append(f"gap={node['itemSpacing']}")
        pad = [node.get(k, 0) for k in ["paddingTop", "paddingRight", "paddingBottom", "paddingLeft"]]
        if any(pad):
            props.append(f"padding={pad[0]}/{pad[1]}/{pad[2]}/{pad[3]}")
        if node.get("primaryAxisAlignItems"):
            props.append(f"justify={node['primaryAxisAlignItems']}")
        if node.get("counterAxisAlignItems"):
            props.append(f"align={node['counterAxisAlignItems']}")
        lines.append(f"{indent}  layout: {', '.join(props)}")

    # Fills
    fills = [f for f in node.get("fills", []) if f.get("visible", True)]
    if fills:
        lines.append(f"{indent}  fill: {', '.join(extract_color(f) for f in fills)}")

    # Corner radius
    if node.get("cornerRadius"):
        lines.append(f"{indent}  borderRadius: {node['cornerRadius']}")
    elif node.get("rectangleCornerRadii"):
        lines.append(f"{indent}  borderRadius: {node['rectangleCornerRadii']}")

    # Typography
    style = node.get("style")
    if style:
        typo = []
        for key, label in [("fontFamily", None), ("fontSize", "px"), ("fontWeight", "weight="),
                            ("lineHeightPx", "lineHeight="), ("letterSpacing", "letterSpacing="),
                            ("textAlignHorizontal", "align=")]:
            val = style.get(key)
            if val is None:
                continue
            if key == "fontFamily":
                typo.append(str(val))
            elif key == "fontSize":
                typo.append(f"{val}px")
            elif key == "lineHeightPx":
                typo.append(f"lineHeight={val:.0f}px")
            else:
                typo.append(f"{label}{val}")
        lines.append(f"{indent}  font: {', '.join(typo)}")

    # Text content
    chars = node.get("characters", "")
    if chars:
        preview = chars.replace("\n", "\\n")[:120]
        lines.append(f"{indent}  text: \"{preview}{'...' if len(chars) > 120 else ''}\"")

    # Strokes
    strokes = [s for s in node.get("strokes", []) if s.get("visible", True)]
    if strokes:
        lines.append(f"{indent}  stroke: {', '.join(extract_color(s) for s in strokes)} weight={node.get('strokeWeight', 1)}")

    # Drop shadows
    for e in node.get("effects", []):
        if e.get("visible", True) and e["type"] == "DROP_SHADOW":
            c = e.get("color", {})
            off = e.get("offset", {})
            lines.append(
                f"{indent}  shadow: offset=({off.get('x',0)},{off.get('y',0)}) "
                f"blur={e.get('radius',0)} "
                f"color=rgba({int(c.get('r',0)*255)},{int(c.get('g',0)*255)},{int(c.get('b',0)*255)},{c.get('a',1):.2f})"
            )

    # Recurse children (cap depth to keep summary readable)
    children = node.get("children", [])
    if depth < 5:
        for child in children:
            lines.extend(node_summary_lines(child, depth + 1))
    elif children:
        lines.append(f"{indent}  ... ({len(children)} children not shown)")

    return lines


def main():
    out_dir = Path("figma-specs")
    out_dir.mkdir(exist_ok=True)

    file_nodes = parse_urls(FIGMA_URLS)
    if not file_nodes:
        raise SystemExit("No valid Figma URLs parsed — aborting.")

    for file_key, node_ids in file_nodes.items():
        ids_api = ",".join(node_ids)
        print(f"\nFile {file_key}: fetching {len(node_ids)} node(s)...")

        # --- Node JSON ---
        # safe=':,' preserves colons (node ID separator) and commas (multi-ID separator)
        ids_encoded = urllib.parse.quote(ids_api, safe=":,")
        data = figma_request(f"/files/{file_key}/nodes?ids={ids_encoded}")
        raw_path = out_dir / f"{file_key}-nodes.json"
        with open(raw_path, "w") as f:
            json.dump(data, f, indent=2)
        print(f"  Saved raw JSON → {raw_path}")

        # --- Design summary markdown ---
        lines = [f"# Figma Specs — file `{file_key}`", ""]
        for node_id, node_data in data.get("nodes", {}).items():
            doc = node_data.get("document", {})
            lines += [f"## Node `{node_id}`: {doc.get('name', 'unnamed')}", ""]
            lines += node_summary_lines(doc)
            lines.append("")

        summary_path = out_dir / f"{file_key}-summary.md"
        with open(summary_path, "w") as f:
            f.write("\n".join(lines))
        print(f"  Saved summary  → {summary_path}")

        # --- Rendered PNGs ---
        print("  Fetching rendered images...")
        img_data = figma_request(
            f"/images/{file_key}?ids={ids_encoded}&format=png&scale=2"
        )
        for node_id, img_url in img_data.get("images", {}).items():
            if not img_url:
                print(f"  WARNING: no image URL returned for {node_id}")
                continue
            node_safe = node_id.replace(":", "-")
            with urllib.request.urlopen(img_url) as resp:
                img_bytes = resp.read()
            img_path = out_dir / f"{node_safe}.png"
            with open(img_path, "wb") as f:
                f.write(img_bytes)
            print(f"  Downloaded PNG  → {img_path} ({len(img_bytes):,} bytes)")


if __name__ == "__main__":
    main()
