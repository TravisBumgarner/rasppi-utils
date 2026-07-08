#!/usr/bin/env python3
"""Social Poster - caption generation from photo metadata.

Python port of the old Photography-Portfolio/social-tagging Node tool. Photos
exported from Lightroom (with metadata included) carry an embedded XMP packet
holding the title, description, and hierarchical keywords, plus EXIF gear
info. This module turns that into ready-to-review captions:

1. Parse the embedded XMP for ``dc:title``, ``dc:description`` and
   ``lr:hierarchicalSubject`` keywords (e.g.
   ``cameracoffeewander|Place|USA|California``).
2. Map each ``cameracoffeewander|...`` keyword through the tag tree in
   ``config/tags.json`` to per-platform hashtag/account lists. The JSON file
   is the single editable source of tags — edit it directly to add/change
   tags; it is re-read on every extraction, so no restart is needed.
3. Read EXIF for the gear/setup lines (camera, lens, shutter, aperture,
   focal length), with the same per-camera label overrides as the old tool.
4. Render the caption template per platform: Instagram gets priority+general
   tags (deduped, capped at 30); Bluesky gets its own tag set.

Bulk ingestion calls ``extract_captions`` once per uploaded image in a
background thread. A raised ValueError marks that ingest item's tagging as
failed with the message, which the review UI surfaces (captions can then be
written by hand).
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
from xml.etree import ElementTree

from PIL import Image

# The editable tag tree: nested categories whose leaves hold
# {"priority": [...], "general": [...], "bluesky": [...]} tag lists.
TAGS_PATH = Path(__file__).parent.parent / "config" / "tags.json"

# Only Lightroom keywords under this root are social tags; others (e.g.
# gallery organization) are ignored.
TAG_ROOT = "cameracoffeewander"

INSTAGRAM_TAG_LIMIT = 30

_XMP_RE = re.compile(rb"<x:xmpmeta[^>]*>.*?</x:xmpmeta>", re.DOTALL)

_NS = {
    "rdf": "http://www.w3.org/1999/02/22-rdf-syntax-ns#",
    "dc": "http://purl.org/dc/elements/1.1/",
    "lr": "http://ns.adobe.com/lightroom/1.0/",
}

# EXIF tag ids (IFD0 + Exif IFD).
_MAKE, _MODEL = 271, 272
_EXIF_IFD = 0x8769
_EXPOSURE_TIME, _F_NUMBER = 0x829A, 0x829D
_DATE_TIME_ORIGINAL = 0x9003
_FOCAL_LENGTH = 0x920A
_LENS_MODEL = 0xA434

# Friendly camera labels by EXIF "Make - Model". A value of None for lens
# means "keep the EXIF lens"; '' blanks it (phones/scans where the lens line
# is noise). Mirrors metadataOverride.ts from the old tool.
_CAMERA_OVERRIDES: Dict[str, Dict[str, Optional[str]]] = {
    "Apple - iPhone 13 mini": {"camera": "iPhone 13", "lens": ""},
    "Google - Pixel 3": {"lens": ""},
    "motorola - moto x4": {"lens": ""},
    "NIKON CORPORATION - NIKON D3400": {"camera": "Nikon D3400"},
    "NIKON CORPORATION - NIKON D5300": {"camera": "Nikon D5300"},
    "NIKON CORPORATION - NIKON D7500": {"camera": "Nikon D7500"},
    "NIKON CORPORATION - NIKON Z 5": {"camera": "Nikon Z5"},
    "SONY - DSC-RX100": {"camera": "Sony RX100"},
    "SONY - SLT-A55V": {"camera": "Sony A55"},
    "SONY - DSLR-A290": {"camera": "Sony A290"},
    "DJI - FC3582": {"camera": "DJI Mini 3 Pro"},
    # Film scanners: the scanner isn't the real camera and EXIF has no usable
    # model, so drop the gear info unless a film-camera keyword overrides it.
    "NORITSU KOKI - QSS-32_33": {"camera": "", "lens": ""},
    "NORITSU KOKI - EZ Controller": {"camera": "", "lens": ""},
    # Exports with stripped camera EXIF.
    "None - None": {"camera": "", "lens": ""},
}

# Film cameras are identified by keyword, not EXIF (the scan carries the
# scanner's EXIF). Keyword wins over the EXIF-derived label.
_FILM_CAMERA_TAGS: Dict[str, Dict[str, Optional[str]]] = {
    f"{TAG_ROOT}|Camera|PentaxK1000": {"camera": "Pentax K1000"},
    f"{TAG_ROOT}|Camera|YashicaC": {"camera": "Yashica C"},
    f"{TAG_ROOT}|Camera|OlympusPS": {"camera": "Olympus Stylus P&S"},
    f"{TAG_ROOT}|Camera|NikonSLR": {"camera": "Nikon SLR"},
    f"{TAG_ROOT}|Camera|UnknownFilmCamera": {
        "camera": "Unknown Film Camera",
        "lens": "",
    },
}


# ---------------------------------------------------------------------------
# XMP (title / description / hierarchical keywords)
# ---------------------------------------------------------------------------
def _read_xmp(image_path: str) -> Optional[ElementTree.Element]:
    """Find and parse the embedded XMP packet, or None if the file has none."""
    data = Path(image_path).read_bytes()
    match = _XMP_RE.search(data)
    if match is None:
        return None
    try:
        return ElementTree.fromstring(match.group(0).decode("utf-8", "replace"))
    except ElementTree.ParseError:
        return None


def _xmp_text(root: ElementTree.Element, path: str) -> str:
    """First rdf:li text under an XMP property (Alt/Bag), or ''."""
    node = root.find(f".//{path}//rdf:li", _NS)
    return (node.text or "").strip() if node is not None else ""


def _xmp_list(root: ElementTree.Element, path: str) -> List[str]:
    """All rdf:li texts under an XMP property (Bag/Seq)."""
    return [
        (node.text or "").strip()
        for node in root.findall(f".//{path}//rdf:li", _NS)
        if node.text
    ]


# ---------------------------------------------------------------------------
# EXIF (gear/setup lines)
# ---------------------------------------------------------------------------
def _format_shutter_speed(exposure_time: float) -> str:
    if exposure_time <= 0:
        return ""
    if exposure_time < 1:
        return f"1/{round(1 / exposure_time)}s"
    return f"{exposure_time:g}s"


def _format_date_taken(exif_datetime: str) -> str:
    """EXIF 'YYYY:MM:DD HH:MM:SS' -> 'January 2026' ('' if unparseable)."""
    from datetime import datetime

    try:
        return datetime.strptime(exif_datetime[:10], "%Y:%m:%d").strftime("%B %Y")
    except ValueError:
        return ""


def _read_exif(image_path: str) -> Dict[str, str]:
    """Extract the template's gear/setup fields from EXIF, applying the
    per-camera label overrides. Unreadable/absent EXIF yields empty fields
    (the template drops empty lines)."""
    try:
        with Image.open(image_path) as img:
            exif = img.getexif()
            ifd = exif.get_ifd(_EXIF_IFD)
    except Exception:  # noqa: BLE001 - formats without EXIF support
        return {
            "camera": "",
            "lens": "",
            "shutter_speed": "",
            "aperture": "",
            "focal_length": "",
            "date_taken": "",
        }

    def clean(value) -> str:
        return str(value).strip().strip("\x00").strip() if value is not None else ""

    camera = f"{clean(exif.get(_MAKE)) or None} - {clean(exif.get(_MODEL)) or None}"
    lens = clean(ifd.get(_LENS_MODEL))
    if lens == "----":  # Sony A55 with an unrecognized lens
        lens = ""

    exposure = ifd.get(_EXPOSURE_TIME)
    f_number = ifd.get(_F_NUMBER)
    focal = ifd.get(_FOCAL_LENGTH)

    fields = {
        "camera": camera,
        "lens": lens,
        "shutter_speed": _format_shutter_speed(float(exposure)) if exposure else "",
        "aperture": f"ƒ/{float(f_number):.1f}" if f_number else "",
        "focal_length": f"{float(focal):g}mm" if focal else "",
        "date_taken": _format_date_taken(clean(ifd.get(_DATE_TIME_ORIGINAL))),
    }

    override = _CAMERA_OVERRIDES.get(camera, {})
    for key, value in override.items():
        if value is not None:
            fields[key] = value
    return fields


def _apply_film_camera_tags(fields: Dict[str, str], keywords: List[str]) -> None:
    """Film-camera keywords name the real camera (scans carry scanner EXIF)."""
    for tag, override in _FILM_CAMERA_TAGS.items():
        if tag in keywords:
            for key, value in override.items():
                if value is not None:
                    fields[key] = value


# ---------------------------------------------------------------------------
# Tag tree lookup
# ---------------------------------------------------------------------------
def _load_tag_tree() -> Dict:
    with open(TAGS_PATH, encoding="utf-8") as f:
        return json.load(f)


def _lookup(tree: Dict, parts: List[str]) -> Optional[Dict]:
    """Walk the tag tree by hierarchy parts; return the leaf tag lists or None."""
    node = tree
    for part in parts:
        if not isinstance(node, dict) or part not in node:
            return None
        node = node[part]
    return node if isinstance(node, dict) and "general" in node else None


def _generate_social_tags(keywords: List[str]) -> Dict[str, List[str]]:
    """Map ``cameracoffeewander|...`` keywords to per-platform tag lists.

    Raises ValueError naming any keyword the tag tree doesn't know, so the
    tree and the Lightroom hierarchy stay in sync (same contract as the old
    tool).
    """
    tree = _load_tag_tree()
    errors: List[str] = []
    priority: List[str] = []
    general: List[str] = []
    bluesky: List[str] = []

    for keyword in keywords:
        if TAG_ROOT not in keyword:
            continue
        hierarchy = keyword.replace(f"{TAG_ROOT}|", "")
        leaf = _lookup(tree, hierarchy.split("|"))
        if leaf is None:
            errors.append(f"Unknown hierarchy tag: {hierarchy}")
            continue
        if not leaf["general"] and not leaf["priority"]:
            errors.append(f"No tags or accounts found for hierarchy tag: {hierarchy}")
            continue
        priority.extend(leaf["priority"])
        general.extend(leaf["general"])
        bluesky.extend(leaf.get("bluesky", []))

    if errors:
        raise ValueError("; ".join(errors))

    # Priority tags first (actively monitored), deduped, Instagram caps at 30.
    instagram = list(dict.fromkeys(priority + general))[:INSTAGRAM_TAG_LIMIT]
    malformed = [t for t in instagram if t[:2] in ("##", "@@", "#@", "@#")]
    if malformed:
        raise ValueError(f"Malformed tag(s) in tag tree: {malformed}")

    return {"instagram": instagram, "bluesky": list(dict.fromkeys(bluesky))}


# ---------------------------------------------------------------------------
# Caption template
# ---------------------------------------------------------------------------
def _render_caption(fields: Dict[str, str], title: str, description: str,
                    tags: List[str]) -> str:
    gear = ", ".join(x for x in (fields["camera"], fields["lens"]) if x)
    setup_parts = [
        fields["shutter_speed"],
        fields["aperture"],
        f"{fields['focal_length']} focal length" if fields["focal_length"] else "",
    ]
    lines = [
        f"{title.strip()} {fields['date_taken']}".strip(),
        description.strip(),
        f"The Gear - {gear}" if gear else "",
        f"The Setup - {', '.join(p for p in setup_parts if p)}"
        if any(setup_parts)
        else "",
        " ".join(tags),
    ]
    return "\n".join(line for line in lines if line)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------
def extract_captions(image_path: str) -> Dict[str, str]:
    """Build per-platform captions for a photo, e.g. ``{"instagram": ...,
    "bluesky": ...}``.

    Raises ValueError with a human-readable message when the photo lacks the
    Lightroom keywords the tag tree needs (the review UI shows it and the
    captions can be written by hand).
    """
    xmp = _read_xmp(image_path)
    if xmp is None:
        raise ValueError(
            "No XMP metadata found — export from Lightroom with metadata included"
        )

    keywords = _xmp_list(xmp, "lr:hierarchicalSubject")
    if not keywords:
        raise ValueError("No Lightroom hierarchical keywords (lr:hierarchicalSubject)")

    title = _xmp_text(xmp, "dc:title")
    description = _xmp_text(xmp, "dc:description")

    tags = _generate_social_tags(keywords)

    fields = _read_exif(image_path)
    _apply_film_camera_tags(fields, keywords)

    return {
        platform: _render_caption(fields, title, description, tags[platform])
        for platform in ("instagram", "bluesky")
    }
