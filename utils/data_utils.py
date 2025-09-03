import pandas as pd
from pyvis.network import Network
import pandas as pd
import matplotlib.pyplot as plt
import re

  # return original if no match

### DATA LOADING FUNCTIONS =
def load_data():
    #### = Load data_metadata = ####
    import pandas as pd
    import glob
    import os
    import re

    def standardize_to_hSC(value):
        match = re.search(r'h(\d+)', str(value), re.IGNORECASE)
        if match:
            return f"hSC{match.group(1)}"
        return value

    # Get all CSV file paths
    csv_files = glob.glob(os.path.join("/mnt/c/Users/caminorsm/Desktop/Database/updated_after_holidays/data_metadata/", "*.csv"))
    # Read and concatenate all CSVs
    data_metadata = pd.concat((pd.read_csv(f) for f in csv_files), ignore_index=True)
    data_metadata = data_metadata.replace("NaN", "")

    # Some data modification for small mistakes
    data_metadata['Data Type'] = data_metadata['Data Type'].str.replace('in_vitro_dosing', 'in-vitro dosing', regex=False)
    data_metadata['Data Type'] = data_metadata['Data Type'].str.replace(' in-vitro dosing', 'in-vitro dosing', regex=False)
    data_metadata=data_metadata.drop(columns=["Lab ID"])
    # Read sample_metadata (Sample_type (PDSC, tumor_frozen, FFP...))
    sample_metadata = pd.read_csv("/mnt/c/Users/caminorsm/Desktop/Database/updated_after_holidays/sample_metadata.csv")
    sample_metadata = sample_metadata.replace("NaN", "")
    sample_metadata["Lab ID"] = sample_metadata["Lab ID"].apply(standardize_to_hSC)


 #### = CREATE REDCAP DATA FILE = ####
    # Read patient metadata (hSC number, REDCAP ID, NCCS, omics)
    patients = pd.read_csv("/mnt/c/Users/caminorsm/Desktop/Database/updated_after_holidays/mapper.csv")
    patients = patients.replace("NaN", "")

    ### = LOAD REDCAP DATA AND PARSE DATE AGAIN == ##
    
    # Read redcap data (Demographics, Diagnosis and Treatment)
    redcap = pd.read_csv("/mnt/c/Users/caminorsm/Desktop/Database/updated_after_holidays/20250807_redcap_corrected_dates.csv", low_memory=False)
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

    sarcoma_fixed_dates = sarcoma_fixed_dates.replace("NaN", "nan")

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
    # Reset index and merge back on all three keys
    # Step 1: Reset index and merge on all three keys
    redcap_updated = redcap.merge(
        sarcoma_fixed_dates[index_cols + shared_date_cols],
        on=index_cols,
        how="left",
        suffixes=("", "_new")
    )


    # Final dataset
    redcap = redcap_updated
    ## = PROCESS REDCAP dropping down the demographic info to each row

    def process_redcap_data(redcap):
        redcap_clean = redcap.dropna(axis=1, how='all')
        # Split demographics info (when Repeat Instrument is NaN)
        patient_info = redcap[redcap["Repeat Instrument"].isna()].copy()
        # Split diagnosis/treatment rows
        diagnosis_treatment = redcap_clean[
            redcap_clean["Repeat Instrument"].isin([
                "Diagnosis Information at Study Site",
                "Treatment at Study Site"
            ])
        ].copy()
        # Drop fully empty columns in diagnosis/treatment
        diagnosis_treatment = diagnosis_treatment.dropna(axis=1, how='all')
        # Merge to add patient_info to diagnosis/treatment rows
        # Only keep columns from redcap_clean (i.e., original set of 307 columns)
        merged = diagnosis_treatment.merge(
            patient_info.drop(columns=["Repeat Instrument"]),  # don't override 'Repeat Instrument'
            on="REDCAP ID",
            how="left",
            suffixes=("", "_demo")  # prevent _x/_y
        )
        # Fill missing demographic columns in diagnosis_treatment using patient_info 
        for col in patient_info.columns:
            if col != "REDCAP ID" and col in merged.columns and col + "_demo" in merged.columns:
                merged[col] = merged[col].combine_first(merged[col + "_demo"])
                merged = merged.drop(columns=[col + "_demo"])
        # Now combine all: demographics + enriched diagnosis/treatment
        final = pd.concat([patient_info, merged], ignore_index=True)
        # Keep only columns from redcap_clean (i.e., 307 columns)
        final = final[redcap_clean.columns]
        return final

    redcap = process_redcap_data(redcap)

    ### == Reorder columns == ###
    index_cols = ["REDCAP ID", "Repeat Instrument", "Repeat Instance"]

    # Get all columns except these index columns
    other_cols = [col for col in redcap.columns if col not in index_cols]

    # Reorder columns
    redcap = redcap[index_cols + other_cols]
    # drop empty redcap columns to reduce size of the table
    redcap = redcap.dropna(axis=1, how="all")
    ## Add Patient information using the matching patient_metadata sheet
    demographics = pd.merge(patients, redcap, on =["REDCAP ID"], how="outer")
    ## create a data df using the data_metadata and the sample_metadata
    data = pd.merge(data_metadata, sample_metadata, on=["Patient ID","Sample ID","Specimen ID"], how="outer")
    ## merge everything together based on the common Patient ID number
    all_data=pd.merge(demographics, data, on=["Patient ID"], how="outer")
    
 #### == FIX correct diagnosis and grade for the Lab ID == ##
    def get_final_diagnosis(path_diag, comp_path_diag):
        if path_diag == "Others":
            if pd.isna(comp_path_diag) or comp_path_diag.strip() == "":
                return "Others"
            else:
                return comp_path_diag
        return path_diag

### Function to determine the diagnosis observed right after the time of Biopsy/Resection of the specific Patient ID _Lab ID sample
    def assign_final_diagnosis(df):
        diag_df = df[df['Repeat Instrument'] == 'Diagnosis Information at Study Site'].copy()
        
        # Convert dates
        diag_df['Date of Final Pathologic Diagnosis'] = pd.to_datetime(
            diag_df['Date of Final Pathologic Diagnosis'], errors='coerce', dayfirst=True
        )
        diag_df['Resection Date'] = pd.to_datetime(
            diag_df['Resection Date'], errors='coerce', dayfirst=True
        )

        # Fix possibly flipped dates
        diag_df['Date of Final Pathologic Diagnosis'] = [
            patho_date
            for patho_date, resection_date in zip(
                diag_df['Date of Final Pathologic Diagnosis'], diag_df['Resection Date']
            )
        ]
        final_diagnosis = {}

        for lab_id, group in diag_df.groupby('Lab ID'):
            unique_diag = group[['Pathologic Diagnosis', 'Composite Pathologic Diagnosis']].drop_duplicates()

            # Case 1: Only one diagnosis — use it
            if len(unique_diag) == 1:
                row = unique_diag.iloc[0]
                diagnosis = get_final_diagnosis(row['Pathologic Diagnosis'], row['Composite Pathologic Diagnosis'])
                final_diagnosis[lab_id] = diagnosis
                continue

            # Case 2: Multiple diagnoses
            group = group.copy()
            group['TimeDiff'] = (group['Date of Final Pathologic Diagnosis'] - group['Resection Date']).dt.days

            after_resection = group[group['TimeDiff'] >= 0]
            before_resection = group[group['TimeDiff'] < 0]

            if not after_resection.empty:
                # Get closest after or on the same day
                closest_row = after_resection.loc[after_resection['TimeDiff'].idxmin()]
                post_flag = False
            elif not before_resection.empty:
                # Get closest before and flag as "POST"
                closest_row = before_resection.loc[before_resection['TimeDiff'].idxmax()]
                post_flag = True
            else:
                final_diagnosis[lab_id] = None
                continue

            diagnosis = get_final_diagnosis(
                closest_row['Pathologic Diagnosis'],
                closest_row['Composite Pathologic Diagnosis']
            )

            if post_flag:
                diagnosis += " POST"

            final_diagnosis[lab_id] = diagnosis
        # Assign the results back
        df['Diagnosis_final'] = df['Lab ID'].map(final_diagnosis)
        return df
    
    def assign_final_grade(df):
        diag_df = df[df['Repeat Instrument'] == 'Diagnosis Information at Study Site'].copy()

        # Convert dates
        diag_df['Date of Final Pathologic Diagnosis'] = pd.to_datetime(
            diag_df['Date of Final Pathologic Diagnosis'], errors='coerce', dayfirst=True
        )
        diag_df['Resection Date'] = pd.to_datetime(
            diag_df['Resection Date'], errors='coerce', dayfirst=True
        )

        # Fix possibly flipped dates
        diag_df['Date of Final Pathologic Diagnosis'] = [
            patho_date
            for patho_date, resection_date in zip(
                diag_df['Date of Final Pathologic Diagnosis'], diag_df['Resection Date']
            )
        ]
        final_diagnosis = {}

        for lab_id, group in diag_df.groupby('Lab ID'):
            unique_diag = group[['Pathologic Grade (FNCLCC)']].drop_duplicates()

            # Case 1: Only one diagnosis — use it
            if len(unique_diag) == 1:
                row = unique_diag.iloc[0]
                diagnosis =row["Pathologic Grade (FNCLCC)"]
                final_diagnosis[lab_id] = diagnosis
                continue

            # Case 2: Multiple diagnoses
            group = group.copy()
            group['TimeDiff'] = (group['Date of Final Pathologic Diagnosis'] - group['Resection Date']).dt.days

            after_resection = group[group['TimeDiff'] >= 0]
            before_resection = group[group['TimeDiff'] < 0]
            if not after_resection.empty:
                # Get closest after or on the same day
                closest_row = after_resection.loc[after_resection['TimeDiff'].idxmin()]
                post_flag = False
            elif not before_resection.empty:
                # Get closest before and flag as "POST"
                closest_row = before_resection.loc[before_resection['TimeDiff'].idxmax()]
                post_flag = True
            else:
                final_diagnosis[lab_id] = None
                continue

            diagnosis = closest_row['Pathologic Grade (FNCLCC)']
            if post_flag:
                diagnosis += " POST"

            final_diagnosis[lab_id] = diagnosis
        # Assign the results back
        df['Grade_final'] = df['Lab ID'].map(final_diagnosis)
        return df
    
    diagnosis_rows = all_data[all_data["Repeat Instrument"] == "Diagnosis Information at Study Site"].copy()

    ## FIX Diagnosis information
    
    diagnosis_fix = assign_final_diagnosis(diagnosis_rows)
    diagnosis_fix = assign_final_grade(diagnosis_fix)
    final_diagnosis_df = diagnosis_fix[['Lab ID', 'Diagnosis_final','Grade_final']].drop_duplicates()
    # Merge into redcap_df on Lab ID
    all_data = all_data.merge(final_diagnosis_df, on='Lab ID', how='left')

    # Convert date columns if not already done
    all_data['Resection Date'] = pd.to_datetime(all_data['Resection Date'], errors='coerce', dayfirst=True)
    all_data['Chemotherapy Start Date'] = pd.to_datetime(all_data['Chemotherapy Start Date'], errors='coerce', dayfirst=True)
    all_data['Radiotherapy Start Date'] = pd.to_datetime(all_data['Radiotherapy Start Date'], errors='coerce')

    # Group by Lab ID and identify treated patients
    treated_lab_ids = []

    for lab_id, group in all_data.groupby("Lab ID"):
        resect_dates = group['Resection Date'].dropna().unique()
        chemo_dates = group['Chemotherapy Start Date'].dropna().unique()
        radio_dates = group['Radiotherapy Start Date'].dropna().unique()

        if len(resect_dates) == 0 or len(chemo_dates) == 0 or len(radio_dates) == 0:
            continue  # skip if any of the key dates are missing

        # Check if any chemo or radio date is before any resection date
        if any(c < r for r in resect_dates for c in chemo_dates) or any(c < r for r in resect_dates for c in radio_dates):
            treated_lab_ids.append(lab_id)

    # Append ' TREATED' to Diagnosis_final where Lab ID is in treated list
    all_data['Diagnosis_final_long'] = all_data.apply(
        lambda row: f"{row['Diagnosis_final']} TREATED" if row['Lab ID'] in treated_lab_ids and pd.notna(row['Diagnosis_final']) else row['Diagnosis_final'],
        axis=1
    )
    # Define a mapping dictionary for replacements
    replacement_map = {
        "Dedifferentiated Liposarcoma": "DDLPS",
        "Undifferentiated Pleomorphic Sarcoma": "UPS",
        "Leiomyosarcoma (excluding Skin)": "LMS",
        "Solitary Fibrous Tumour, Malignant": "SFT",
        "Well-Differentiated Liposarcoma / Atypical Lipomatous Tumour": "WDLPS/ALT",
        "Malignant Granular Cell Tumour": "Others",
        "Endometrial Stromal Sarcoma (Low Grade, High Grade), Undifferentiated Uterine Sarcoma": "ESS",
        "Myxofibrosarcoma (formerly Myxoid Malignant Fibrous Histiocytoma [Myxoid MFH])": "MFS",
        "Low-Grade Fibromyxoid Sarcoma": "MFS",
        "Myxoid/Round Cell Liposarcoma": "Others",
        "Undifferentiated Round Cell Sarcoma":"Others",
        "Liposarcoma, NOS": "LPS",
        "Pleomorphic Liposarcoma":"Others",
        "Synovial Sarcoma, NOS":"Others",
        "Solitary Fibrous Tumour, Malignant":"SFT",
        "Phyllodes Tumour":"Others",
        "Malignant Peripheral Nerve Sheath Tumour":"Others",
        "Pleomorphic Rhabdomyosarcoma":"Others",
        "Desmoid Fibromatosis":"Others",
        "Atypical Lipomatous Tumour":"WDLPS/ALT",
        "Well-Differentiated Liposarcoma":"WDLPS",
        "Well-Differentiated Liposarcoma and Dedifferentiated Liposarcoma":"WDLPS/DDLPS",
        "Pleomorphic Liposarcoma":"Others",
        "Malignant Peripheral Nerve Sheath Tumour":"Others"}
    diagnosis_rows = all_data[all_data["Repeat Instrument"] == "Diagnosis Information at Study Site"].copy()
    
    # Sort by REDCAP ID and Repeat Instance ascending
    diagnosis_plot = diagnosis_rows.copy()
    # Replace in-place
    diagnosis_plot["Diagnosis_original"] = diagnosis_plot["Diagnosis_final"]
    # Create a cleaned version to use for mapping (remove " - POST" or " - TREATED")

    # Clean suffixes like " TREATED" or " POST" (with or without dash or space)
    # Strip off 'POST' or 'TREATED' suffixes robustly
    diagnosis_plot["Diagnosis_final"] = diagnosis_plot["Diagnosis_original"].str.replace( r"(\s*[-–]?\s*(TREATED))$", "", regex=True
    ).str.strip()
    diagnosis_plot["Diagnosis_final"] = diagnosis_plot["Diagnosis_final"].str.replace( r"(\s*[-–]?\s*(POST))$", "", regex=True
    ).str.strip()
    # Apply replacement mapping
    diagnosis_plot["Diagnosis_final"] = diagnosis_plot["Diagnosis_final"].replace(replacement_map)
    # Override GIST assignments
    diagnosis_plot.loc[diagnosis_plot['Lab ID'].isin(['hSC68', 'hSC11', 'hSC07','hSC77']), 'Diagnosis_final'] = 'GIST'
    # Fill any remaining NaNs
    diagnosis_plot["Diagnosis_final_short"] = diagnosis_plot["Diagnosis_final"].fillna("Others")
    # 1. Create a DataFrame with the values you want to merge
    diagnosis_info = diagnosis_plot[["Lab ID", "Diagnosis_final_short"]].copy()
    # 2. Drop duplicates to ensure one row per Lab ID
    diagnosis_info = diagnosis_info.drop_duplicates(subset=["Lab ID"])
    # 3. Merge into redcap
    all_data = all_data.merge(diagnosis_info, on="Lab ID", how="left")

    return patients, redcap, all_data