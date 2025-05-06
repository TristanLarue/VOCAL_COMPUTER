from dotenv import load_dotenv
import os
import pvporcupine

# 1) Load your .env
load_dotenv()

# 2) Grab the raw value
raw = os.getenv("PORCUPINE_ACCESS_KEY")

# 3) Guard & clean
if not raw:
    raise RuntimeError("PORCUPINE_ACCESS_KEY is missing in .env")
# strip any leading/trailing whitespace, plus any accidental quotes
key = raw.strip().strip('"\'')  

# 4) Debug print (remove after confirming)
print("Loaded key:", repr(key))

# 5) Create Porcupine with your cleaned key
porcupine = pvporcupine.create(
    access_key=key,
    keywords=["computer"],
    sensitivities=[0.6]
)
