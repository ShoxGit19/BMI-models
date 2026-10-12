"""Map API cache regressions without importing secret/data bootstrap."""
import ast
import logging
from pathlib import Path
import unittest
from unittest.mock import Mock

import pandas as pd
from flask import Flask, jsonify, request
from flask_caching import Cache


class MapCacheTests(unittest.TestCase):
    def setUp(self):
        self.app = Flask(__name__)
        self.app.config["TESTING"] = True
        cache = Cache(self.app, config={"CACHE_TYPE": "SimpleCache"})
        data = pd.DataFrame([
            {"SensorID": "S0001", "District": "Chilonzor", "Latitude": 41.3, "Longitude": 69.2, "Fault": 0},
            {"SensorID": "S0002", "District": "Bektemir", "Latitude": 41.25, "Longitude": 69.35, "Fault": 2},
        ])
        source = Path(__file__).resolve().parents[1].joinpath("app.py").read_text(encoding="utf-8")
        node = next(n for n in ast.parse(source).body if isinstance(n, ast.FunctionDef) and n.name == "map_data")
        namespace = {"app": self.app, "cache": cache, "df": data, "get_latest": Mock(return_value=data),
                     "request": request, "jsonify": jsonify, "logger": logging.getLogger(__name__)}
        exec(compile(ast.Module(body=[node], type_ignores=[]), "app.py", "exec"), namespace)
        self.client = self.app.test_client()

    def test_district_filter_has_its_own_cache(self):
        self.assertEqual(len(self.client.get("/api/map-data").json), 2)
        for district in ("Chilonzor", "Bektemir"):
            result = self.client.get("/api/map-data", query_string={"district": district})
            self.assertEqual(result.status_code, 200)
            self.assertEqual([row["District"] for row in result.json], [district])
        self.assertEqual(len(self.client.get("/api/map-data").json), 2)

    def test_unknown_district_does_not_poison_unfiltered_cache(self):
        self.assertEqual(self.client.get("/api/map-data?district=Missing").json, [])
        self.assertEqual(len(self.client.get("/api/map-data").json), 2)

    def test_markers_keep_required_coordinates_and_fields(self):
        result = self.client.get("/api/map-data").json
        for item in result:
            self.assertTrue({"SensorID", "District", "Latitude", "Longitude", "Fault", "Color"} <= item.keys())
            self.assertTrue(41 < item["Latitude"] < 42)
            self.assertTrue(69 < item["Longitude"] < 70)


if __name__ == "__main__":
    unittest.main()
