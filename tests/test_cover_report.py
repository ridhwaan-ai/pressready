from PIL import Image

from pressready.checklist import cover_image_report


def _img(tmp_path, size, fmt="PNG"):
    p = tmp_path / f"c.{fmt.lower()}"
    Image.new("RGB", size, (10, 20, 30)).save(p, fmt)
    return p


def test_good_cover(tmp_path):
    r = cover_image_report(_img(tmp_path, (1000, 1600)))
    assert r["warnings"] == [] and r["ratio"] == 1.6 and r["format"] == "PNG"


def test_small_cover(tmp_path):
    r = cover_image_report(_img(tmp_path, (400, 640)))
    assert any("1000px" in w for w in r["warnings"])


def test_landscape_and_ratio(tmp_path):
    assert any("portrait" in w for w in cover_image_report(_img(tmp_path, (1600, 1000)))["warnings"])
    assert any("ratio" in w for w in cover_image_report(_img(tmp_path, (1000, 1000 * 2)))["warnings"])


def test_jpeg_ok(tmp_path):
    assert cover_image_report(_img(tmp_path, (1000, 1600), "JPEG"))["warnings"] == []
