import os, logging
logging.disable(logging.CRITICAL)
import warnings; warnings.filterwarnings("ignore")
from dotenv import load_dotenv
load_dotenv()

import anthropic
key = os.getenv("CLAUDE_API_KEY","")
print("Key prefix:", key[:20] if key else "MISSING")
try:
    c = anthropic.Anthropic(api_key=key)
    msg = c.messages.create(
        model="claude-3-5-sonnet-20241022",
        max_tokens=5,
        messages=[{"role":"user","content":"ping"}]
    )
    print("CLAUDE LIVE:", msg.stop_reason)
except anthropic.AuthenticationError as e:
    print("AUTH ERROR - Key is INVALID:", str(e)[:200])
except anthropic.PermissionDeniedError as e:
    print("PERMISSION DENIED:", str(e)[:200])
except Exception as e:
    print("ERROR:", type(e).__name__, str(e)[:300])
