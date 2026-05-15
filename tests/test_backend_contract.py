import unittest
from pathlib import Path
from unittest.mock import patch

from backend import inference
from backend.main import PredictRequest, api_predict


class PredictionContractTests(unittest.TestCase):
    def test_label_thresholds_match_public_risk_thresholds(self):
        self.assertEqual(inference.get_label_and_confidence(0.50), ("DANGER", "MEDIUM"))
        self.assertEqual(inference.get_label_and_confidence(0.30), ("WARNING", "MEDIUM"))
        self.assertEqual(inference.get_label_and_confidence(0.2999)[0], "SAFE")

    def test_predict_response_keeps_frontend_contract(self):
        request = PredictRequest(
            station_id="BT_BinhDai",
            date="2020-03-15",
            features={
                "salinity_psu": 8.0,
                "salinity_7d_avg": 7.5,
                "ndvi": 0.35,
                "ndvi_tendency": -0.02,
                "distance_to_estuary_km": 8.3,
            },
        )

        with (
            patch("backend.main.predict", return_value={"probability": 0.50, "mock": False}),
            patch("backend.main.match_patterns", return_value=[]),
            patch("backend.main.build_spm_sequence_string", return_value=""),
            patch("backend.main.save_prediction") as save_prediction,
        ):
            response = api_predict(request)

        self.assertEqual(response["label"], "DANGER")
        self.assertEqual(response["threshold"], 0.30)
        self.assertEqual(response["risk_thresholds"], {"warning": 0.30, "danger": 0.50})
        self.assertIn("feature_top10", response)
        self.assertIn("explanation", response)
        self.assertIn("recommendations", response)
        save_prediction.assert_called_once()


class FrontendSyncTests(unittest.TestCase):
    def test_frontend_uses_inclusive_threshold_boundaries(self):
        files = [
            Path("frontend/js/ui/prediction.js"),
            Path("frontend/js/ui/map-panel.js"),
            Path("frontend/js/ui/pages.js"),
            Path("frontend/js/ui/recommendations-page.js"),
        ]
        for path in files:
            text = path.read_text(encoding="utf-8")
            self.assertNotIn("> 0.50", text, path.as_posix())
            self.assertNotIn(">0.50", text, path.as_posix())
            self.assertNotIn("> 0.30", text, path.as_posix())
            self.assertNotIn(">0.30", text, path.as_posix())


if __name__ == "__main__":
    unittest.main()
