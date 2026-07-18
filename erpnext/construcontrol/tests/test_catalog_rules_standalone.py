from __future__ import annotations

import importlib.util
import unittest
from pathlib import Path

MODULE_PATH = Path(__file__).resolve().parents[1] / "migration" / "catalog_rules.py"
SPEC = importlib.util.spec_from_file_location("construcontrol_catalog_rules", MODULE_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError(f"Unable to load {MODULE_PATH}")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)

is_construction_record = MODULE.is_construction_record


class ConstructionCatalogRulesTest(unittest.TestCase):
    def test_accepts_explicit_construction_materials(self) -> None:
        self.assertTrue(is_construction_record({"name": "Cemento gris", "unit": "saco"}))
        self.assertTrue(is_construction_record({"name": "Varilla corrugada 3/8", "unit": "unidad"}))
        self.assertTrue(is_construction_record({"name": "Balastre", "category": "Arena y agregados"}))
        self.assertTrue(is_construction_record({"name": "Tubería PVC 1/2", "unit": "metro"}))

    def test_rejects_demo_and_retail_products(self) -> None:
        self.assertFalse(is_construction_record({"name": "Running Shoe", "unit": "Nos"}))
        self.assertFalse(is_construction_record({"name": "Coffee Mug", "unit": "Nos"}))
        self.assertFalse(is_construction_record({"name": "Television", "unit": "Nos"}))
        self.assertFalse(is_construction_record({"name": "Demo Item", "category": "Products"}))

    def test_accepts_short_historical_names_only_with_inventory_context(self) -> None:
        self.assertTrue(
            is_construction_record(
                {
                    "name": "Pegazulejo A1",
                    "unit": "saco",
                    "currentStock": 12,
                    "minimumStock": 3,
                }
            )
        )
        self.assertFalse(is_construction_record({"name": "Producto genérico"}))


if __name__ == "__main__":
    unittest.main()
