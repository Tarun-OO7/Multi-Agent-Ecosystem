import pandas as pd
import json
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'inventory.csv')

def process_inventory_data(file_path: str = None) -> str:
    path_to_use = file_path if file_path else DATA_PATH
    try:
        if not os.path.exists(path_to_use):
            return json.dumps({"error": "inventory.csv not found"})
            
        df = pd.read_csv(path_to_use)
        df['Stock_Level'] = pd.to_numeric(df['Stock_Level'], errors='coerce').fillna(0)
        df['Reorder_Point'] = pd.to_numeric(df['Reorder_Point'], errors='coerce').fillna(0)
        
        stockouts = df[df['Stock_Level'] == 0][['Product_ID', 'Product_Name']].to_dict('records')
        needs_reorder = df[df['Stock_Level'] <= df['Reorder_Point']][['Product_ID', 'Product_Name', 'Stock_Level', 'Reorder_Point']].to_dict('records')
        excess_inventory = df[df['Stock_Level'] > (df['Reorder_Point'] * 3)][['Product_ID', 'Product_Name', 'Stock_Level']].to_dict('records')
        
        metrics = {
            "stockout_risks": stockouts,
            "needs_immediate_reorder": needs_reorder,
            "excess_inventory": excess_inventory
        }
        
        return json.dumps(metrics)
    except Exception as e:
        logger.error(f"Error processing inventory data: {e}")
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    print(process_inventory_data())
