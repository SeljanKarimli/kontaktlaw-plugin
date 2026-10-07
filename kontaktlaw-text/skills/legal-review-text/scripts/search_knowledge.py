import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
from kontaktlaw_core import knowledge as core
from kontaktlaw_core.knowledge import *
if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"): sys.stdout.reconfigure(encoding="utf-8")
    core.main()
else:
    sys.modules[__name__] = core
