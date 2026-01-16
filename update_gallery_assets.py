#!/usr/bin/env python3
"""
Обновляет gallery.json:
- добавляет width/height для изображений
- генерирует уменьшенные версии (srcset) в w/rs
- добавляет preview/srcset поля
"""
from __future__ import annotations

import argparse
import json
import os
from typing import Iterable, List, Tuple

from PIL import Image

DEFAULT_SIZES = [800, 1200]
DEFAULT_OUTPUT_DIR = os.path.join("w", "rs")


def is_video(src: str, item: dict) -> bool:
    return item.get("type") == "video" or src.lower().endswith((".mp4", ".webm"))


def is_image(src: str) -> bool:
    return src.lower().endswith((".webp", ".jpg", ".jpeg", ".png", ".gif"))


def load_gallery(path: str) -> List[dict]:
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def save_gallery(path: str, items: List[dict]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
        f.write("\n")


def resized_dimensions(width: int, height: int, target: int) -> Tuple[int, int]:
    if width >= height:
        new_w = target
        new_h = round(height * (target / width))
    else:
        new_h = target
        new_w = round(width * (target / height))
    return new_w, new_h


def build_srcset(
    src: str,
    sizes: Iterable[int],
    output_dir: str,
) -> Tuple[str, str, int]:
    """
    Возвращает (srcset, preview_path, created_count).
    """
    created = 0
    srcset_entries: List[Tuple[int, str]] = []

    with Image.open(src) as img:
        orig_w, orig_h = img.size

        for target in sizes:
            if max(orig_w, orig_h) <= target:
                continue

            new_w, new_h = resized_dimensions(orig_w, orig_h, target)
            stem, _ = os.path.splitext(os.path.basename(src))
            out_name = f"{stem}-{target}.webp"
            out_path = os.path.join(output_dir, out_name)

            if not os.path.exists(out_path):
                resized = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                resized.save(out_path, "WEBP", lossless=True)
                created += 1

            srcset_entries.append((new_w, out_path))

    srcset_entries.append((orig_w, src))
    srcset_entries = sorted(set(srcset_entries), key=lambda x: x[0])
    srcset_str = ", ".join([f"{path} {width}w" for width, path in srcset_entries])
    preview_path = srcset_entries[0][1] if srcset_entries else src

    return srcset_str, preview_path, created


def update_gallery(
    gallery_path: str,
    sizes: Iterable[int],
    output_dir: str,
) -> None:
    items = load_gallery(gallery_path)
    os.makedirs(output_dir, exist_ok=True)

    updated = 0
    created = 0
    missing = 0

    for item in items:
        src = item.get("src", "")
        if not src or is_video(src, item):
            item.pop("preview", None)
            item.pop("srcset", None)
            continue

        if not is_image(src):
            continue

        if not os.path.exists(src):
            missing += 1
            continue

        try:
            with Image.open(src) as img:
                width, height = img.size
            if item.get("width") != width or item.get("height") != height:
                item["width"] = width
                item["height"] = height

            srcset, preview, created_count = build_srcset(src, sizes, output_dir)
            created += created_count

            if item.get("srcset") != srcset or item.get("preview") != preview:
                item["srcset"] = srcset
                item["preview"] = preview
                updated += 1
        except Exception:
            missing += 1

    save_gallery(gallery_path, items)

    print(f"Updated items: {updated}")
    print(f"Created resized files: {created}")
    print(f"Missing/failed: {missing}")
    print(f"Total items: {len(items)}")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Update gallery assets and srcset.")
    parser.add_argument(
        "--gallery",
        default="gallery.json",
        help="Path to gallery.json (default: gallery.json)",
    )
    parser.add_argument(
        "--sizes",
        default=",".join(str(s) for s in DEFAULT_SIZES),
        help="Comma-separated target sizes (default: 800,1200)",
    )
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help="Directory for resized images (default: w/rs)",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    sizes = [int(s.strip()) for s in args.sizes.split(",") if s.strip()]
    update_gallery(args.gallery, sizes, args.output_dir)


if __name__ == "__main__":
    main()
