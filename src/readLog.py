from config import get_config
cfg = get_config()

def readLogFiles(logFileName):
    DATA_DIR = cfg.paths.DATA_DIR
    p = DATA_DIR / logFileName
    if p.exists():
        with p.open("r", encoding="utf-8") as f:
            return next((line.strip() for line in reversed(f.read().splitlines()) if line.strip()), None)
    else:
        return "N/A"