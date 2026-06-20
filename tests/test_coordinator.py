import unittest
from agents.coordinator import classify_capability

class TestCoordinatorRouting(unittest.TestCase):
    def test_classify_capability_sales(self):
        dataset_context = {
            "columns": ["Date", "Region", "Product", "Sales", "Quantity"],
            "dtypes": {"Date": "datetime", "Region": "object", "Product": "object", "Sales": "float64", "Quantity": "int64"},
            "row_count": 1000,
            "sample_rows": [{"Date": "2023-01-01", "Region": "North", "Product": "Widget", "Sales": 100.0, "Quantity": 5}]
        }
        
        # Test DataQuery
        cap, conf = classify_capability("What is the total sales for the North region?", dataset_context)
        self.assertEqual(cap, "DataQueryAgent")
        self.assertEqual(conf, "high")
        
        # Test Forecast
        cap, conf = classify_capability("Forecast next month's sales.", dataset_context)
        self.assertEqual(cap, "ForecastAgent")
        self.assertEqual(conf, "high")
        
        # Test Report
        cap, conf = classify_capability("Generate a comprehensive report.", dataset_context)
        self.assertEqual(cap, "ReportAgent")
        self.assertEqual(conf, "high")

    def test_classify_capability_healthcare(self):
        dataset_context = {
            "columns": ["patient_id", "admission_date", "length_of_stay", "diagnosis_code"],
            "dtypes": {"patient_id": "object", "admission_date": "datetime", "length_of_stay": "int64", "diagnosis_code": "object"},
            "row_count": 500,
            "sample_rows": [{"patient_id": "P001", "admission_date": "2023-01-01", "length_of_stay": 3, "diagnosis_code": "J01"}]
        }
        
        # Test Analytics
        cap, conf = classify_capability("Analyze trends in length of stay over time.", dataset_context)
        self.assertEqual(cap, "AnalyticsAgent")
        self.assertEqual(conf, "high")
        
        # Test Visualization
        cap, conf = classify_capability("Plot the admission rates by month.", dataset_context)
        self.assertEqual(cap, "VisualizationAgent")
        self.assertEqual(conf, "high")
        
        # Test Default
        cap, conf = classify_capability("What is the name of the hospital?", dataset_context)
        self.assertEqual(cap, "DataQueryAgent")
        self.assertEqual(conf, "low")

if __name__ == "__main__":
    unittest.main()
