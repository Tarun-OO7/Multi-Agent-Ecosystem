import os
from pathlib import Path
from mcp.server.fastmcp import FastMCP

# Import the calculation functions cleanly from Phase 1 architecture
from tools.sales_tools import process_sales_data
from tools.inventory_tools import process_inventory_data
from tools.customer_tools import process_customer_data

# Initialize a fast, lightweight MCP server instance
mcp = FastMCP("sme-bi-server")

# Define sandbox directory relative to this script
SANDBOX_DIR = Path(os.path.join(os.path.dirname(__file__), '..', 'data')).resolve()

def validate_file_path(file_path: str) -> Path:
    """
    Validates that the file exists, has a valid extension,
    and is strictly inside the sandbox directory to prevent path traversal.
    """
    valid_extensions = {".csv", ".xlsx", ".xls"}
    path = Path(file_path).resolve()
    
    if path.suffix.lower() not in valid_extensions:
        raise ValueError(f"Invalid file extension: {path.suffix}. Must be one of {valid_extensions}")
        
    try:
        path.relative_to(SANDBOX_DIR)
    except ValueError:
        raise ValueError("Path traversal detected! File must be within the ./data/ directory.")
        
    if not path.is_file():
        raise FileNotFoundError(f"File not found: {file_path}")
        
    return path

@mcp.tool()
def get_sales_metrics(file_path: str) -> str:
    """
    Calls the sales analysis functions and returns the JSON payload.
    """
    valid_path = validate_file_path(file_path)
    return process_sales_data(str(valid_path))

@mcp.tool()
def get_inventory_metrics(file_path: str) -> str:
    """
    Calls the inventory analysis functions and returns the JSON payload.
    """
    valid_path = validate_file_path(file_path)
    return process_inventory_data(str(valid_path))

@mcp.tool()
def get_customer_feedback_metrics(file_path: str) -> str:
    """
    Calls the customer insight functions and returns the preprocessed JSON payload.
    """
    valid_path = validate_file_path(file_path)
    return process_customer_data(str(valid_path))

if __name__ == "__main__":
    import logging
    
    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)
    
    logger.info("Starting Business Intelligence MCP Server...")
    mcp.run(transport='stdio')
