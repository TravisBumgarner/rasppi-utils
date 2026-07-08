"""Tests for caption generation from photo metadata (XMP + EXIF + tag tree)."""

import json
import sys
from pathlib import Path

import pytest
from PIL import Image

_SCRIPTS = Path(__file__).parent.parent / "scripts"
sys.path.insert(0, str(_SCRIPTS))

import tagging  # noqa: E402


def _xmp_packet(keywords, title="Golden Gate", description="Fog at sunrise."):
    lis = "".join(f"<rdf:li>{k}</rdf:li>" for k in keywords)
    return f"""<x:xmpmeta xmlns:x="adobe:ns:meta/">
 <rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">
  <rdf:Description xmlns:dc="http://purl.org/dc/elements/1.1/"
                   xmlns:lr="http://ns.adobe.com/lightroom/1.0/">
   <dc:title><rdf:Alt><rdf:li xml:lang="x-default">{title}</rdf:li></rdf:Alt></dc:title>
   <dc:description><rdf:Alt><rdf:li xml:lang="x-default">{description}</rdf:li></rdf:Alt></dc:description>
   <lr:hierarchicalSubject><rdf:Bag>{lis}</rdf:Bag></lr:hierarchicalSubject>
  </rdf:Description>
 </rdf:RDF>
</x:xmpmeta>""".encode("utf-8")


def _write_photo(path, keywords, with_exif=True, **xmp_kwargs):
    """Create a small JPEG, optionally with camera EXIF, and append an XMP
    packet (the extractor scans file bytes for the packet, so appending is
    equivalent to Lightroom embedding it)."""
    img = Image.new("RGB", (8, 8), "gray")
    if with_exif:
        exif = Image.Exif()
        exif[271] = "NIKON CORPORATION"  # Make
        exif[272] = "NIKON Z 5"  # Model
        ifd = exif.get_ifd(0x8769)
        ifd[0x829A] = 0.005  # ExposureTime -> 1/200s
        ifd[0x829D] = 2.8  # FNumber
        ifd[0x9003] = "2026:05:01 10:00:00"  # DateTimeOriginal
        ifd[0x920A] = 35.0  # FocalLength
        ifd[0xA434] = "NIKKOR Z 35mm f/1.8 S"  # LensModel
        img.save(path, exif=exif)
    else:
        img.save(path)
    with open(path, "ab") as f:
        f.write(_xmp_packet(keywords, **xmp_kwargs))


def test_extract_captions_end_to_end(tmp_path):
    photo = tmp_path / "photo.jpg"
    _write_photo(photo, ["cameracoffeewander|Camera|NikonZ5", "gallery|ignored"])

    captions = tagging.extract_captions(str(photo))

    instagram = captions["instagram"]
    assert instagram.splitlines()[0] == "Golden Gate May 2026"
    assert "Fog at sunrise." in instagram
    assert "The Gear - Nikon Z5, NIKKOR Z 35mm f/1.8 S" in instagram
    assert "The Setup - 1/200s, ƒ/2.8, 35mm focal length" in instagram
    assert "#nikonz5" in instagram and "#nikon" in instagram

    bluesky = captions["bluesky"]
    assert "#nikon" in bluesky
    assert "#nikonz5" not in bluesky  # bluesky uses its own tag set


def test_unknown_hierarchy_tag_raises(tmp_path):
    photo = tmp_path / "photo.jpg"
    _write_photo(photo, ["cameracoffeewander|Camera|NotACamera"])

    with pytest.raises(ValueError, match="Unknown hierarchy tag: Camera|NotACamera"):
        tagging.extract_captions(str(photo))


def test_photo_without_xmp_raises(tmp_path):
    photo = tmp_path / "photo.jpg"
    Image.new("RGB", (8, 8), "gray").save(photo)

    with pytest.raises(ValueError, match="No XMP metadata"):
        tagging.extract_captions(str(photo))


def test_photo_without_keywords_raises(tmp_path):
    photo = tmp_path / "photo.jpg"
    _write_photo(photo, [])

    with pytest.raises(ValueError, match="hierarchical keywords"):
        tagging.extract_captions(str(photo))


def test_film_camera_keyword_overrides_scanner_exif(tmp_path, monkeypatch):
    # A film scan: no useful EXIF, camera named by keyword instead.
    tree = {
        "Camera": {
            "PentaxK1000": {
                "general": ["#pentax"],
                "priority": ["#analogsunrise"],
                "bluesky": ["#pentaxK1000"],
            }
        }
    }
    tags_path = tmp_path / "tags.json"
    tags_path.write_text(json.dumps(tree))
    monkeypatch.setattr(tagging, "TAGS_PATH", tags_path)

    photo = tmp_path / "scan.jpg"
    _write_photo(photo, ["cameracoffeewander|Camera|PentaxK1000"], with_exif=False)

    captions = tagging.extract_captions(str(photo))
    assert "The Gear - Pentax K1000" in captions["instagram"]
    # Priority tags come before general ones.
    tag_line = captions["instagram"].splitlines()[-1]
    assert tag_line == "#analogsunrise #pentax"
    assert captions["bluesky"].splitlines()[-1] == "#pentaxK1000"


def test_instagram_hashtags_capped_at_5_priority_first(tmp_path, monkeypatch):
    tree = {
        "Special": {
            "Many": {
                "general": [f"#tag{i}" for i in range(40)],
                "priority": ["#first"],
                "bluesky": [],
            }
        }
    }
    tags_path = tmp_path / "tags.json"
    tags_path.write_text(json.dumps(tree))
    monkeypatch.setattr(tagging, "TAGS_PATH", tags_path)

    photo = tmp_path / "photo.jpg"
    _write_photo(photo, ["cameracoffeewander|Special|Many"])

    tag_line = tagging.extract_captions(str(photo))["instagram"].splitlines()[-1]
    tags = tag_line.split(" ")
    assert len(tags) == tagging.INSTAGRAM_HASHTAG_LIMIT
    assert tags[0] == "#first"
    assert all(t.startswith("#tag") for t in tags[1:])


def test_instagram_general_tags_are_shuffled(tmp_path, monkeypatch):
    tree = {
        "Special": {
            "Many": {
                "general": [f"#tag{i}" for i in range(40)],
                "priority": [],
                "bluesky": [],
            }
        }
    }
    tags_path = tmp_path / "tags.json"
    tags_path.write_text(json.dumps(tree))
    monkeypatch.setattr(tagging, "TAGS_PATH", tags_path)

    photo = tmp_path / "photo.jpg"
    _write_photo(photo, ["cameracoffeewander|Special|Many"])

    draws = {
        tagging.extract_captions(str(photo))["instagram"].splitlines()[-1]
        for _ in range(10)
    }
    assert len(draws) > 1  # 10 draws of 5-from-40 all identical ≈ impossible


def test_instagram_priority_never_dropped_and_mentions_uncounted(
        tmp_path, monkeypatch):
    # 6 priority hashtags exceed the budget on their own: all kept, no general
    # hashtags added. Mentions ride along without consuming the budget.
    tree = {
        "Special": {
            "Hubs": {
                "general": ["#extra1", "#extra2", "@generalmention"],
                "priority": [f"#hub{i}" for i in range(6)] + ["@bighub"],
                "bluesky": [],
            }
        }
    }
    tags_path = tmp_path / "tags.json"
    tags_path.write_text(json.dumps(tree))
    monkeypatch.setattr(tagging, "TAGS_PATH", tags_path)

    photo = tmp_path / "photo.jpg"
    _write_photo(photo, ["cameracoffeewander|Special|Hubs"])

    tag_line = tagging.extract_captions(str(photo))["instagram"].splitlines()[-1]
    tags = tag_line.split(" ")
    assert tags[:7] == [f"#hub{i}" for i in range(6)] + ["@bighub"]
    hashtags = [t for t in tags if t.startswith("#")]
    assert hashtags == [f"#hub{i}" for i in range(6)]  # no general hashtags
    assert "@generalmention" in tags  # mentions don't consume the budget


def test_bluesky_caption_fits_300_chars(tmp_path, monkeypatch):
    tree = {
        "Special": {
            "Wordy": {
                "general": ["#a"],
                "priority": [],
                "bluesky": ["#keepme"] + [f"#verylongblueskytag{i}" for i in range(20)],
            }
        }
    }
    tags_path = tmp_path / "tags.json"
    tags_path.write_text(json.dumps(tree))
    monkeypatch.setattr(tagging, "TAGS_PATH", tags_path)

    photo = tmp_path / "photo.jpg"
    _write_photo(photo, ["cameracoffeewander|Special|Wordy"],
                 description="An evening on the water. " * 6)

    caption = tagging.extract_captions(str(photo))["bluesky"]
    assert len(caption) <= tagging.BLUESKY_CHAR_LIMIT
    # Trimmed from the end: the first (most important) tag survives.
    assert "#keepme" in caption


def test_real_tags_json_is_valid():
    """The shipped tag tree parses and every leaf has the expected lists."""

    def walk(node):
        if "general" in node:
            assert isinstance(node["general"], list)
            assert isinstance(node["priority"], list)
            assert isinstance(node["bluesky"], list)
            return
        for child in node.values():
            walk(child)

    tree = json.loads(tagging.TAGS_PATH.read_text())
    assert set(tree.keys()) >= {"Camera", "Place", "PhotoType"}
    walk(tree)
