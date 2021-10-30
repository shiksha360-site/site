import sys
import os

if not os.environ.get("_DEV"):
    raise RuntimeError("This should only be run from shiksdk")
    sys.exit(-1)

sys.pycache_prefix = "data/pycache"
sys.path.append(".")

from sdk import internal
import uvicorn    


if __name__ == "__main__":
    uvicorn.run(internal.internal_site.app, host="0.0.0.0")