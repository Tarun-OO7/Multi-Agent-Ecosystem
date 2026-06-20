import pandas as pd
import numpy as np
import json
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'sales.csv')

def process_sales_data(file_path: str = None) -> str:
    path_to_use = file_path if file_path else DATA_PATH
    try:
        if not os.path.exists(path_to_use):
            return json.dumps({"error": "sales.csv not found"})
        
        df = pd.read_csv(path_to_use)
        
        # Robust column mapping
        col_map = {}
        for c in df.columns:
            if c.lower() == 'date': col_map[c] = 'Date'
            elif c.lower() in ('revenue', 'sales'): col_map[c] = 'Revenue'
            elif c.lower() in ('units_sold', 'quantity'): col_map[c] = 'Units_Sold'
            elif c.lower() in ('product_name', 'product', 'item'): col_map[c] = 'Product_Name'
            elif c.lower() == 'region': col_map[c] = 'Region'
        df.rename(columns=col_map, inplace=True)
        
        if 'Date' in df.columns:
            df['Date'] = pd.to_datetime(df['Date'])
        if 'Revenue' in df.columns:
            df['Revenue'] = pd.to_numeric(df['Revenue'], errors='coerce').fillna(0)
        else:
            df['Revenue'] = 0.0
            
        if 'Units_Sold' in df.columns:
            df['Units_Sold'] = pd.to_numeric(df['Units_Sold'], errors='coerce').fillna(0)
        else:
            df['Units_Sold'] = 0.0
            
        if 'Product_Name' not in df.columns:
            df['Product_Name'] = 'Unknown'
        
        # MoM Growth
        df['Month'] = df['Date'].dt.to_period('M')
        monthly_revenue = df.groupby('Month')['Revenue'].sum()
        mom_growth = monthly_revenue.pct_change().dropna().to_dict()
        mom_growth_str_keys = {str(k): v for k, v in mom_growth.items()}
        
        # Top and Bottom Performing Products
        product_revenue = df.groupby('Product_Name')['Revenue'].sum().sort_values(ascending=False)
        top_products = product_revenue.head(3).to_dict()
        bottom_products = product_revenue.tail(3).to_dict()
        
        # Trend (Moving Average for last 30 days overall)
        daily_sales = df.groupby('Date')['Units_Sold'].sum().reset_index()
        daily_sales = daily_sales.sort_values('Date')
        daily_sales['7_day_MA'] = daily_sales['Units_Sold'].rolling(window=7).mean()
        recent_trend = daily_sales.tail(14)[['Date', '7_day_MA']].dropna()
        recent_trend['Date'] = recent_trend['Date'].dt.strftime('%Y-%m-%d')
        trend_data = recent_trend.set_index('Date')['7_day_MA'].to_dict()
        
        metrics = {
            "mom_growth": mom_growth_str_keys,
            "top_products_revenue": top_products,
            "bottom_products_revenue": bottom_products,
            "recent_units_sold_trend_7d_ma": trend_data
        }
        
        return json.dumps(metrics)
    except Exception as e:
        logger.error(f"Error processing sales data: {e}")
        return json.dumps({"error": str(e)})

if __name__ == "__main__":
    print(process_sales_data())
