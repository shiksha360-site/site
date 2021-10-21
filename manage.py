import sys
sys.pycache_prefix = "data/pycache"

from sdk import internal
import uvicorn    


if __name__ == "__main__":
    uvicorn.run(internal.internal_site.app)