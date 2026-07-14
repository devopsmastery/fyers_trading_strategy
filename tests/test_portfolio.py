import unittest
import os
import json
import csv
from scripts.portfolio_db import parse_csv_to_db, add_trade, remove_trade, load_db, CSV_PATH, DB_PATH

class TestPortfolioManager(unittest.TestCase):
    def setUp(self):
        self.csv_path = 'test_portfolio.txt'
        self.db_path = 'test_db.json'
        
        # Create a mock Portfolio.txt
        with open(self.csv_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerow(['Instrument', 'Qty.', 'Avg. cost', 'LTP', 'Invested', 'Cur. val', 'P&L'])
            writer.writerow(['TESTA', '10', '100.5', '110.0', '1005', '1100', '95'])
            writer.writerow(['TESTB', '20', '50.0', '45.0', '1000', '900', '-100'])
            
        # Clear existing DB
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def tearDown(self):
        # Clean up
        if os.path.exists(self.csv_path):
            os.remove(self.csv_path)
        if os.path.exists(self.db_path):
            os.remove(self.db_path)

    def test_parse_csv_to_db(self):
        db = {}
        db = parse_csv_to_db(db, self.csv_path)
        self.assertIn('TESTA', db)
        self.assertEqual(db['TESTA']['qty'], 10)
        self.assertEqual(db['TESTA']['avg_cost'], 100.5)
        
        self.assertIn('TESTB', db)
        self.assertEqual(db['TESTB']['qty'], 20)

    def test_add_trade(self):
        # Add a brand new trade
        add_trade('TESTC', 5, 200.0, self.csv_path, self.db_path)
        db = load_db(self.db_path)
        self.assertIn('TESTC', db)
        self.assertEqual(db['TESTC']['qty'], 5)
        self.assertEqual(db['TESTC']['avg_cost'], 200.0)
        
        # Average down TESTC
        add_trade('TESTC', 5, 100.0, self.csv_path, self.db_path)
        db = load_db(self.db_path)
        self.assertEqual(db['TESTC']['qty'], 10)
        self.assertEqual(db['TESTC']['avg_cost'], 150.0)
        
    def test_remove_trade(self):
        # Need to parse CSV to DB first to simulate load
        db = {}
        db = parse_csv_to_db(db, self.csv_path)
        with open(self.db_path, 'w') as f:
            json.dump(db, f)
            
        remove_trade('TESTA', self.csv_path, self.db_path)
        db = load_db(self.db_path)
        self.assertNotIn('TESTA', db)
        self.assertIn('TESTB', db)

if __name__ == '__main__':
    unittest.main()
