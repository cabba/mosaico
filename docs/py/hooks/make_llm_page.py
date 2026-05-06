import os
import re
from pathlib import Path
from markdownify import markdownify as md

# Dynamic containers
categories = {
    "INDEX": [],
    "SDK_HOWTO": [],
    "SDK_EXAMPLES": [],
    "SDK_API_REFERENCE": [],
    "INDEPTH": [],
}
content_map = {}     # src_path -> full markdown content (for llms-full.txt)
metadata_map = {}    # src_path -> {"title": ..., "description": ..., "url": ...}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_title(markdown_text: str, fallback: str) -> str:
    """Return the first H1/H2 heading found in the markdown, or the fallback."""
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if stripped.startswith("# "):
            return stripped[2:].strip()
        if stripped.startswith("## ") and not stripped.startswith("## SOURCE:"):
            return stripped[3:].strip()
    return fallback


def _extract_description(markdown_text: str, max_chars: int = 160) -> str:
    """Return the first non-empty, non-heading paragraph as a brief description."""
    for line in markdown_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if stripped.startswith("#"):
            continue
        if stripped.startswith(">"):
            continue
        if stripped.startswith("|"):
            continue
        # Looks like real prose — use it
        desc = re.sub(r"\s+", " ", stripped)
        if len(desc) > max_chars:
            desc = desc[:max_chars].rsplit(" ", 1)[0] + "..."
        return desc
    return "No description available."


def _src_to_url(src_path: str, base_url: str) -> str:
    """Convert a source .md path to its published URL."""
    base_url = base_url.rstrip("/")
    url_path = src_path
    if url_path.endswith("/index.md"):
        url_path = url_path[: -len("index.md")]
    elif url_path.endswith(".md"):
        url_path = url_path[:-3] + "/"
    return f"{base_url}/{url_path}".rstrip("/") + "/"


# ---------------------------------------------------------------------------
# MkDocs event hooks
# ---------------------------------------------------------------------------

def on_page_content(html, page, config, files):
    src_path = page.file.src_path.replace(os.sep, "/")

    # Convert HTML → clean Markdown (strip links, scripts, images)
    clean_markdown = md(html, heading_style="ATX", strip=["a", "script", "img"])

    # Full content block used by llms-full.txt
    content_with_header = f"## SOURCE: {src_path}\n\n{clean_markdown}"
    content_map[src_path] = content_with_header

    # Lightweight metadata used by llms.txt
    title = page.title or _extract_title(clean_markdown, Path(src_path).stem)
    description = _extract_description(clean_markdown)
    base_url = config.get("site_url", "")
    url = _src_to_url(src_path, base_url) if base_url else src_path
    metadata_map[src_path] = {"title": title, "description": description, "url": url}

    # --- AUTOMATIC CATEGORIZATION ---
    if src_path in ["index.md", "SDK/index.md"]:
        categories["INDEX"].append(src_path)
    elif "SDK/API_reference/" in src_path:
        categories["SDK_API_REFERENCE"].append(src_path)
    elif "SDK/howto/" in src_path:
        categories["SDK_HOWTO"].append(src_path)
    elif "SDK/examples/" in src_path:
        categories["SDK_EXAMPLES"].append(src_path)
    elif src_path.endswith(".md"):
        categories["INDEPTH"].append(src_path)

    return html


def _collect_paths(path_lists: list[str]) -> list[str]:
    """Flatten the requested category lists into an ordered, deduplicated list."""
    seen = set()
    result = []
    for cat in path_lists:
        for p in categories.get(cat, []):
            if p not in seen:
                seen.add(p)
                result.append(p)
    return result


def _generate_full_file(filename, title, path_lists, config):
    """Generate an llms-full.txt style file with complete page content."""
    output_dir = Path(config["site_dir"]) / "llms"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    all_paths = _collect_paths(path_lists)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"> The Data Platform for Robotics and Physical AI\n\n")
        f.write(f"This file contains all documentation content in a single document following the llmstxt.org standard.\n\n")
        
        for path in all_paths:
            if path in content_map:
                f.write(content_map[path])
                f.write("\n\n---\n\n")

    print(f"INFO    -  AI-Doc: {filename} generated with {len(all_paths)} pages.")


def _generate_index_file(filename, title, path_lists, config):
    output_dir = Path(config["site_dir"]) / "llms"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    all_paths = _collect_paths(path_lists)

    with open(output_path, "w", encoding="utf-8") as f:
        f.write(f"# {title}\n\n")
        f.write(f"> The Data Platform for Robotics and Physical AI\n\n")
        f.write(f"This file contains links to documentation sections following the llmstxt.org standard.\n\n")
        f.write("## Table of Contents\n\n")

        for path in all_paths:
            meta = metadata_map.get(path)
            if meta:
                f.write(f"- [{meta['title']}]({meta['url']}): {meta['description']}\n")

    print(f"INFO    -  AI-Doc: {filename} generated with {len(all_paths)} entries.")


# ---------------------------------------------------------------------------
# Post-build: write all output files
# ---------------------------------------------------------------------------

def on_post_build(config):
    ALL_CATS = ["INDEX", "SDK_HOWTO", "SDK_EXAMPLES", "INDEPTH", "SDK_API_REFERENCE"]

    # 1. Full documentation dump (all content)
    _generate_full_file(
        "llms-full.txt",
        "Mosaico Python SDK Documentation",
        ALL_CATS,
        config,
    )

    # 2. Lightweight index with titles, descriptions, and links
    _generate_index_file(
        "llms.txt",
        "Mosaico Python SDK Documentation",
        ALL_CATS,
        config,
    )