# Load packages
from pyvis.network import Network
import pandas as pd
import matplotlib.pyplot as plt

# Read redcap data (Demographics, Diagnosis and Treatment)
redcap = pd.read_csv("/mnt/c/Users/caminorsm/Desktop/Database/updated/20250807_redcap_corrected_dates.csv", low_memory=False)
redcap = redcap.replace("NaN", "")
# Map Redcap_ID with the hSC
redcap = redcap.rename(columns={'REDCap Record ID': 'REDCAP ID'})

### REDCAP WITH FIXED DATES
temp = pd.read_csv("/mnt/c/Users/caminorsm/Desktop/Database/updated/NCCSDMOSarcomaMelano-SarcomaUpdatedRecord_DATA_LABELS_2025-04-02_1334_unlocked.csv", nrows=0)
date_cols = [col for col in temp.columns if "date" in col.lower()]

# Function to apply uniform parsing
def custom_date_parser(x):
    try:
        return pd.to_datetime(x, format="%d/%m/%Y", errors="coerce")
    except Exception:
        return pd.NaT

# Load full file
sarcoma_fixed_dates = pd.read_csv(
    "/mnt/c/Users/caminorsm/Desktop/Database/updated/NCCSDMOSarcomaMelano-SarcomaUpdatedRecord_DATA_LABELS_2025-04-02_1334_unlocked.csv",
    low_memory=False
)

# Rename for consistency
sarcoma_fixed_dates = sarcoma_fixed_dates.rename(columns={"REDCap Record ID": "REDCAP ID"})

# Parse all detected date columns with consistent format
for col in date_cols:
    sarcoma_fixed_dates[col] = sarcoma_fixed_dates[col].apply(custom_date_parser)
sarcoma_fixed_dates = sarcoma_fixed_dates.replace("NaN", "")

# Harmonize index types in both dataframes
for df in [redcap, sarcoma_fixed_dates]:
    df["REDCAP ID"] = df["REDCAP ID"].astype(str).str.strip()
    # DO NOT fill NaNs yet; preserve them for logic
    df["Repeat Instrument"] = df["Repeat Instrument"].astype(str).str.strip()
    # Keep Repeat Instance as-is, maybe cast to float to support NaN + ints
    df["Repeat Instance"] = pd.to_numeric(df["Repeat Instance"], errors="coerce")

### === UPDATE CORRECT DATES === ###
# Step 1: Set multi-index on both DataFrames
index_cols = ["REDCAP ID", "Repeat Instrument", "Repeat Instance"]
redcap_indexed = redcap.set_index(index_cols)
dates_indexed = sarcoma_fixed_dates.set_index(index_cols)

# Step 2: Identify shared date-related columns
date_cols = [col for col in redcap.columns if "date" in col.lower()]
date_cols_sarcoma = [col for col in sarcoma_fixed_dates.columns if "date" in col.lower()]
shared_date_cols = list(set(date_cols).intersection(date_cols_sarcoma))
shared_date_cols
# Step 3: Find overlapping row indices
shared_index = redcap_indexed.index.intersection(dates_indexed.index)

# Step 4: Update only those rows and columns
redcap_indexed.loc[shared_index, shared_date_cols] = dates_indexed.loc[shared_index, shared_date_cols]
redcap_indexed=redcap_indexed.reset_index()
# Step 5: Reset index if needed
redcap = redcap_indexed


redcap.to_csv("/mnt/c/Users/caminorsm/Desktop/Database/updated/20250807_redcap_corrected_dates.csv",low_memory=False, parse_dates=True, dayfirst=True)