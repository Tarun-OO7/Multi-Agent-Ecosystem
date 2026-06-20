from .config import AgentConfig
from .models import Gemini25Flash

def Skill(name, description, model):
    """Mock Skill decorator for Google ADK."""
    def decorator(func):
        func.skill_name = name
        func.description = description
        return func
    return decorator

class Agent:
    """Mock Agent class for Google ADK."""
    def __init__(self, config, skills=None):
        self.config = config
        self.skills = skills or []

    def execute(self, **kwargs):
        agent_name = self.config.name.upper()
        file_path = kwargs.get('file_path')
        prompt = kwargs.get('prompt', '').lower()
        
        response_text = ""
        
        if file_path and prompt:
            try:
                import pandas as pd
                if file_path.endswith('.csv'):
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path)
                    
                # Clean potential currency/string columns to numeric
                for col in df.columns:
                    if df[col].dtype == 'object' or df[col].dtype == 'string':
                        first_valid = df[col].dropna().iloc[0] if not df[col].dropna().empty else ""
                        if isinstance(first_valid, str) and first_valid.startswith('$'):
                            df[col] = pd.to_numeric(df[col].astype(str).str.replace(r'[\$,]', '', regex=True), errors='coerce')
                            
                prompt_lower = prompt.lower()
                
                # Check for unique/different types
                if "different" in prompt_lower or "unique" in prompt_lower or "types" in prompt_lower:
                    cat_cols = df.select_dtypes(include=['object', 'string']).columns
                    res = []
                    for c in cat_cols:
                        uniques = df[c].dropna().unique().tolist()
                        if len(uniques) <= 20:
                            res.append(f"- **{c}**: {', '.join(map(str, uniques))}")
                    if res:
                        response_text = "Here are the different categories I found in the dataset:\n" + "\n".join(res)
                    else:
                        response_text = "I couldn't find any clear categorical types to list."
                        
                # Check for totals/sums
                elif "total" in prompt_lower or "sum" in prompt_lower or "how many" in prompt_lower or "quantity" in prompt_lower:
                    # Find which numeric column to sum
                    num_cols = df.select_dtypes(include=['number']).columns
                    target_num_col = None
                    for c in num_cols:
                        if c.lower() in prompt_lower:
                            target_num_col = c
                            break
                    if not target_num_col:
                        quant_candidates = [c for c in df.columns if 'quant' in c.lower() or 'unit' in c.lower() or 'sales' in c.lower()]
                        if quant_candidates:
                            target_num_col = quant_candidates[0]
                            
                    # Find which specific category value is mentioned
                    cat_cols = df.select_dtypes(include=['object', 'string']).columns
                    target_val = None
                    target_cat_col = None
                    for c in cat_cols:
                        for val in df[c].dropna().unique():
                            if str(val).lower() in prompt_lower:
                                target_val = val
                                target_cat_col = c
                                break
                        if target_val: break
                        
                    if target_num_col and target_val:
                        total_val = df[df[target_cat_col].astype(str).str.lower() == str(target_val).lower()][target_num_col].sum()
                        response_text = f"Based on my analysis, the total {target_num_col} for **'{target_val}'** is **{total_val:,.2f}**."
                    elif target_num_col:
                        total_val = df[target_num_col].sum()
                        response_text = f"The overall total for {target_num_col} is **{total_val:,.2f}**."
                    else:
                        response_text = f"I've analyzed the dataset. Here is a statistical summary:\n```json\n{df.describe().to_dict()}\n```"
                else:
                    # Generic fallback
                    summary = df.describe().to_dict()
                    response_text = f"I've analyzed the dataset. It has {len(df)} rows. Here is a statistical summary of the numeric columns:\n```json\n{summary}\n```"
            except Exception as e:
                response_text = f"I encountered an error reading the file dynamically: {e}"
        elif "report" in agent_name.lower():
            return f"### {agent_name} Final Report\n\n**Executive Summary:** Data processing successful.\n\n**Critical Risks:** Needs continuous monitoring.\n\n**30-Day Action Plan:** Review metrics weekly."
        
        return f"**[{agent_name}] Agent Insight:**\n\n{response_text}\n\n*Note: This response was generated dynamically by analyzing the uploaded dataset.*"
