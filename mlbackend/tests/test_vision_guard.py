import io
import unittest

import numpy as np
from PIL import Image

from mlbackend.vision_ai_model import LocalVisionAIModel, validate_leaf_image


class VisionGuardTests(unittest.TestCase):
    def _jpeg(self, array: np.ndarray) -> bytes:
        buf = io.BytesIO()
        Image.fromarray(array.astype(np.uint8), mode="RGB").save(buf, format="JPEG", quality=90)
        return buf.getvalue()

    def test_blank_neutral_image_is_not_a_leaf(self):
        image = np.full((400, 600, 3), 220, dtype=np.uint8)
        result = validate_leaf_image(self._jpeg(image))
        self.assertFalse(result["valid"])
        self.assertEqual(result["status"], "NOT_A_LEAF")

    def test_dark_screen_like_image_is_not_a_leaf(self):
        image = np.full((400, 700, 3), 25, dtype=np.uint8)
        image[40:360, 80:620] = [35, 35, 35]
        image[80:120, 120:580] = [15, 100, 65]
        image[160:180, 200:500] = [230, 230, 230]
        result = validate_leaf_image(self._jpeg(image))
        self.assertFalse(result["valid"])
        self.assertEqual(result["status"], "NOT_A_LEAF")

    def test_missing_model_never_returns_diagnosis(self):
        image = np.zeros((400, 400, 3), dtype=np.uint8)
        image[:, :, 1] = 180
        result = LocalVisionAIModel().diagnose(image_bytes=self._jpeg(image))
        if result["status"] == "MODEL_UNAVAILABLE":
            self.assertIsNone(result["diagnosis"])
            self.assertIsNone(result["confidence_pct"])


if __name__ == "__main__":
    unittest.main()
