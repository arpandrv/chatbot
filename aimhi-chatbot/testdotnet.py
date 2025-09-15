from dotenv import load_dotenv
import os 
from typing import Dict, Any, List, Optional

load_dotenv()


print(os.getenv("LLM_SYSTEM_PROMPT_RISK"))