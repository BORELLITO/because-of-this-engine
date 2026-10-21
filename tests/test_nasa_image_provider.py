import tempfile
import unittest
import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGE_PATH = ROOT / "production" / "image_provider.py"
IMAGE_SPEC = importlib.util.spec_from_file_location("image_provider", IMAGE_PATH)
image_provider = importlib.util.module_from_spec(IMAGE_SPEC)
assert IMAGE_SPEC.loader is not None
sys.modules[IMAGE_SPEC.name] = image_provider
IMAGE_SPEC.loader.exec_module(image_provider)
NASA_PATH = ROOT / "production" / "nasa_image_provider.py"
NASA_SPEC = importlib.util.spec_from_file_location("nasa_image_provider", NASA_PATH)
nasa_image_provider = importlib.util.module_from_spec(NASA_SPEC)
assert NASA_SPEC.loader is not None
sys.modules[NASA_SPEC.name] = nasa_image_provider
NASA_SPEC.loader.exec_module(nasa_image_provider)

_asset_url = nasa_image_provider._asset_url
_score_item = nasa_image_provider._score_item
_vertical_crop = nasa_image_provider._vertical_crop


class NASAImageProviderTests(unittest.TestCase):
    def test_prefers_original_image_link(self):
        item = {
            "data": [{"nasa_id": "PIA02330", "title": "Mars"}],
            "links": [
                {"href": "https://images-assets.nasa.gov/image/PIA02330/PIA02330~thumb.jpg"},
                {"href": "https://images-assets.nasa.gov/image/PIA02330/PIA02330~orig.jpg"},
            ],
        }
        self.assertEqual(_asset_url(item), "https://images-assets.nasa.gov/image/PIA02330/PIA02330~orig.jpg")

    def test_exact_title_scores_above_description_only(self):
        exact = {"data": [{"title": "KSC-98pc1079", "description": "Mars Climate Orbiter"}]}
        broad = {"data": [{"title": "Mars landscape", "description": "A planet"}]}
        self.assertGreater(_score_item(exact, "KSC-98pc1079"), _score_item(broad, "KSC-98pc1079"))

    def test_vertical_crop_returns_short_format(self):
        from io import BytesIO
        from PIL import Image

        source = BytesIO()
        Image.new("RGB", (1600, 900), (12, 20, 30)).save(source, format="JPEG")
        cropped = _vertical_crop(source.getvalue())
        with Image.open(BytesIO(cropped)) as image:
            self.assertEqual(image.size, (1080, 1920))


if __name__ == "__main__":
    unittest.main()
