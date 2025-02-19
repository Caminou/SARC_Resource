import pandas as pd
### DATA LOADING FUNCTIONS 

def load_data():
    """Load and return datasets."""
    patients = pd.read_csv("~/Database/patient_metadata.csv")
    data_metadata = pd.read_csv("~/Database/data_metadata.csv")
    redcap = pd.read_csv("~/Database/Redcap_metadata.csv", low_memory=False)
    sample_metadata = pd.read_csv("~/Database/sample_metadata.csv")
    return patients, data_metadata, redcap, sample_metadata

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
    final_df = final_df.rename(columns={'REDCap Record ID': 'REDCAP ID'})
    return final_df

# Merge all columns by Patient_ID, Redcap_record
def merge_all_data(patients, final_df, data_metadata, sample_metadata):
    """Merge patient and metadata into a single DataFrame."""
    merged_df = pd.merge(patients, final_df, on="REDCAP ID", how="outer")
    combined_df = pd.merge(merged_df, data_metadata, on=["Patient ID"],how="outer")
    combined_df = pd.merge(combined_df, sample_metadata, on=["Patient ID","Specimen ID","Sample ID"],how="outer")
    combined_df = combined_df.dropna(subset=['Patient ID'])
    return combined_df

# Determine if Sex and Race in patient and Redcap is the same
def sanity_check(df, id_col="Patient ID"):
    """Check for inconsistencies in the patient data."""
    inconsistencies = []
    
    # Define the required mappings for Gender and Sex
    gender_sex_mapping = {"Female": "F", "Male": "M"}
    
    # Iterate through each row of the DataFrame
    for _, row in df.iterrows():
        # Extract the Patient ID for reference
        patient_id = row.get(id_col, "Unknown")
        
        # Safely handle Gender
        gender = row.get("Gender", "")
        gender = str(gender).strip() if not pd.isna(gender) else ""
        
        # Safely handle Sex
        sex = row.get("Sex", "")
        sex = str(sex).strip() if not pd.isna(sex) else ""
        
        # Safely handle Race_x
        race_x = row.get("Race_x", "")
        race_x = str(race_x).strip() if not pd.isna(race_x) else ""
        
        # Safely handle Race_y
        race_y = row.get("Race_y", "")
        race_y = str(race_y).strip() if not pd.isna(race_y) else ""
        
        # --- Perform Checks ---
        # Check Gender vs. Sex mismatch
        if gender and sex:
            expected_sex = gender_sex_mapping.get(gender, "")
            if expected_sex and sex != expected_sex:
                inconsistencies.append({
                    "Patient ID": patient_id,
                    "Issue": "Gender vs. Sex mismatch",
                    "Details": f"Gender: {gender}, Sex: {sex} (expected: {expected_sex})"
                })
        
        # Check Race_x vs. Race_y mismatch
        if race_x and race_y and race_x != race_y:
            inconsistencies.append({
                "Patient ID": patient_id,
                "Issue": "Race_x vs. Race_y mismatch",
                "Details": f"Race_x: {race_x}, Race_y: {race_y}"
            })
    
    # --- Log Results ---
    if inconsistencies:
        print(f"Found {len(inconsistencies)} inconsistencies:")
        for inc in inconsistencies:
            print(f"Patient ID: {inc['Patient ID']}, Issue: {inc['Issue']}, Details: {inc['Details']}")
    else:
        print("No inconsistencies found.")

    return inconsistencies
