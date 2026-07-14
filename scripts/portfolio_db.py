import os
import json
import csv

DB_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'portfolio_db.json')
CSV_PATH = os.path.join(os.path.dirname(__file__), '..', 'Portfolio.txt')

def load_db(db_path=DB_PATH):
    if os.path.exists(db_path):
        try:
            with open(db_path, 'r') as f:
                return json.load(f)
        except json.JSONDecodeError:
            return {}
    return {}

def save_db(db, db_path=DB_PATH):
    dir_name = os.path.dirname(db_path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(db_path, 'w') as f:
        json.dump(db, f, indent=4)

def parse_csv_to_db(db, csv_path=CSV_PATH):
    """Parses Portfolio.txt and updates the JSON DB."""
    if not os.path.exists(csv_path):
        return db
        
    with open(csv_path, 'r') as f:
        reader = csv.reader(f)
        for row in reader:
            if not row or row[0].startswith('#') or row[0] == 'Instrument':
                continue
            
            # Expected: Instrument, Qty., Avg. cost, ...
            symbol = row[0].strip()
            qty = 0
            avg_cost = 0.0
            
            if len(row) > 1:
                try:
                    qty = int(row[1].strip())
                except ValueError:
                    pass
            if len(row) > 2:
                try:
                    avg_cost = float(row[2].strip())
                except ValueError:
                    pass
                    
            db[symbol] = {
                "qty": qty,
                "avg_cost": avg_cost
            }
    return db

def sync_portfolio(csv_path=CSV_PATH, db_path=DB_PATH):
    """Syncs CSV into JSON, returns the dictionary."""
    db = load_db(db_path)
    db = parse_csv_to_db(db, csv_path)
    save_db(db, db_path)
    return db

def add_trade(symbol, qty, price, csv_path=CSV_PATH, db_path=DB_PATH):
    """Records a buy trade."""
    db = sync_portfolio(csv_path, db_path)
    
    if symbol in db:
        old_qty = db[symbol]['qty']
        old_cost = db[symbol]['avg_cost']
        new_qty = old_qty + qty
        if new_qty > 0:
            new_cost = ((old_qty * old_cost) + (qty * price)) / new_qty
        else:
            new_cost = 0
            
        db[symbol]['qty'] = new_qty
        db[symbol]['avg_cost'] = new_cost
    else:
        db[symbol] = {'qty': qty, 'avg_cost': price}
        
    save_db(db, db_path)
    _write_db_to_csv(db, csv_path)

def remove_trade(symbol, csv_path=CSV_PATH, db_path=DB_PATH):
    """Removes a stock from the portfolio."""
    db = sync_portfolio(csv_path, db_path)
    if symbol in db:
        del db[symbol]
        save_db(db, db_path)
        _write_db_to_csv(db, csv_path)

def _write_db_to_csv(db, csv_path=CSV_PATH):
    """Overwrites Portfolio.txt with the latest DB state."""
    with open(csv_path, 'w', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['# This file contains the stocks currently held in your active portfolio.'])
        writer.writerow(['Instrument', 'Qty.', 'Avg. cost'])
        for sym, data in db.items():
            writer.writerow([sym, data['qty'], round(data['avg_cost'], 2)])
