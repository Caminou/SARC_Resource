import pandas as pd
### DATA LOADING FUNCTIONS 

def load_data():
    """Load and return datasets."""
    patients = pd.read_csv("~/Database/patient_metadata.csv")
    data_metadata = pd.read_csv("~/Database/data_metadata.csv")
    redcap = pd.read_csv("~/Database/Redcap_metadata.csv", low_memory=False)
    return patients, data_metadata, redcap

# --- DATA PROCESSING FUNCTIONS ---
def process_redcap_data(redcap):
    """Clean and split the REDCap data."""
    patient_info = redcap[~redcap["Repeat Instrument"].isin(["Diagnosis Information at Study Site", "Treatment at Study Site"])]
    patient_info = patient_info.dropna(axis=1, how="all")

    diagnosis_treatment = redcap[
        (redcap["Repeat Instrument"] == "Diagnosis Information at Study Site") |
        (redcap["Repeat Instrument"] == "Treatment at Study Site")
    ]
    diagnosis_treatment = diagnosis_treatment.dropna(axis=1, how="all")

    merged = pd.merge(patient_info, diagnosis_treatment, on="REDCap Record ID")
    final_df = pd.concat([patient_info, merged], ignore_index=True)
    return final_df

def merge_all_data(patients, final_df, data_metadata):
    """Merge patient and metadata into a single DataFrame."""
    merged_df = pd.merge(patients, final_df, left_on="REDCAP ID", right_on="REDCap Record ID")
    merged_df = merged_df.drop(columns=["REDCap Record ID"])
    combined_df = pd.merge(merged_df, data_metadata, on="Patient ID")
    return combined_df
