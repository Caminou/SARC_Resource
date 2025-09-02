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
    csv_files = glob.glob(os.path.join("/mnt/c/Users/caminorsm/Desktop/Database/updated/data_metadata/data_metadata", "*.csv"))
    # Read and concatenate all CSVs
    data_metadata = pd.concat((pd.read_csv(f) for f in csv_files), ignore_index=True)
    data_metadata = data_metadata.replace("NaN", "")

    # Some data modification for small mistakes
    data_metadata['Data Type'] = data_metadata['Data Type'].str.replace('in_vitro_dosing', 'in-vitro dosing', regex=False)
    data_metadata['Data Type'] = data_metadata['Data Type'].str.replace(' in-vitro dosing', 'in-vitro dosing', regex=False)
    data_metadata["Lab ID"] = data_metadata["Lab ID"].apply(standardize_to_hSC)
    
    # Read sample_metadata (Sample_type (PDSC, tumor_frozen, FFP...))
    sample_metadata = pd.read_csv("/mnt/c/Users/caminorsm/Desktop/Database/updated/sample_metadata.csv")
    sample_metadata = sample_metadata.replace("NaN", "")
    sample_metadata["Lab ID"] = sample_metadata["Lab ID"].apply(standardize_to_hSC)


 #### = CREATE REDCAP DATA FILE = ####
    # Read patient metadata (hSC number, REDCAP ID, NCCS, omics)
    patients = pd.read_csv("/mnt/c/Users/caminorsm/Desktop/Database/updated/mapper.csv")
    patients = patients.replace("NaN", "")
    # Matching sheet (sample_ID, Redcap, hSC number + establishment of PDSC + biopsy date)
    PDSC = pd.read_csv("/mnt/c/Users/caminorsm/Desktop/Database/Patient_Metadata_Matching_Sheet.csv")
    # Rename column names to match redcap column names
    PDSC = PDSC.rename(columns={'Redcap Number': 'REDCAP ID'})
    PDSC = PDSC.rename(columns={'NCCS number/ID': 'Patient ID'})
    PDSC = PDSC.replace("NaN", "")
    ## Get only the samples which model has been generated

    PDSC['REDCAP ID'] = PDSC['REDCAP ID'].astype(str)

    # Read redcap data (Demographics, Diagnosis and Treatment)
    metadata = pd.read_csv("/mnt/c/Users/caminorsm/Desktop/Database/updated/20250807_redcap_corrected_dates.csv",low_memory=False, parse_dates=True, dayfirst=True)

    def process_redcap_data(redcap):
        # Drop fully empty columns
        redcap_clean = redcap.dropna(axis=1, how='all')
        # Split demographics info (when Repeat Instrument is NaN)
        patient_info = redcap_clean[redcap_clean["Repeat Instrument"] == "nan"].copy()
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

    redcap = process_redcap_data(metadata)

    ### == Reorder columns == ###
    index_cols = ["REDCAP ID", "Repeat Instrument", "Repeat Instance"]

    # Get all columns except these index columns
    other_cols = [col for col in redcap.columns if col not in index_cols]

    # Reorder columns
    redcap = redcap[index_cols + other_cols]

    patients = PDSC.merge(patients,left_on=["Patient ID"], 
                                    right_on=["Patient ID"],
                                    how="left")

    patients = patients.drop(columns=["REDCAP ID_x"])

    # Rename 'REDCAP ID_y' to 'REDCAP ID'
    patients = patients.rename(columns={"REDCAP ID_y": "REDCAP ID"})
    redcap = patients.merge(redcap,left_on=["REDCAP ID"], 
                                    right_on=["REDCAP ID"],
                                    how="left")

    # drop empty redcap columns to reduce size of the table
    redcap = redcap.dropna(axis=1, how="all")

 #### == FIX correct diagnosis and grade for the Lab ID == ##
    def get_final_diagnosis(path_diag, comp_path_diag):
        if path_diag == "Others":
            if pd.isna(comp_path_diag) or comp_path_diag.strip() == "":
                return "Others"
            else:
                return comp_path_diag
        return path_diag

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
    
    diagnosis_rows = redcap[redcap["Repeat Instrument"] == "Diagnosis Information at Study Site"].copy()

    ## FIX Diagnosis information
    diagnosis_rows = diagnosis_rows.dropna(axis=1, how="all")
    diagnosis_fix = assign_final_diagnosis(diagnosis_rows)
    diagnosis_fix = assign_final_grade(diagnosis_fix)
    final_diagnosis_df = diagnosis_fix[['Lab ID', 'Diagnosis_final','Grade_final']].drop_duplicates()
    # Merge into redcap_df on Lab ID
    redcap = redcap.merge(final_diagnosis_df, on='Lab ID', how='left')

    # Convert date columns if not already done
    redcap['Resection Date'] = pd.to_datetime(redcap['Resection Date'], errors='coerce', dayfirst=True)
    redcap['Chemotherapy Start Date'] = pd.to_datetime(redcap['Chemotherapy Start Date'], errors='coerce', dayfirst=True)
    redcap['Radiotherapy Start Date'] = pd.to_datetime(redcap['Radiotherapy Start Date'], errors='coerce')

    # Group by Lab ID and identify treated patients
    treated_lab_ids = []

    for lab_id, group in redcap.groupby("Lab ID"):
        resect_dates = group['Resection Date'].dropna().unique()
        chemo_dates = group['Chemotherapy Start Date'].dropna().unique()
        radio_dates = group['Radiotherapy Start Date'].dropna().unique()

        if len(resect_dates) == 0 or len(chemo_dates) == 0 or len(radio_dates) == 0:
            continue  # skip if any of the key dates are missing

        # Check if any chemo or radio date is before any resection date
        if any(c < r for r in resect_dates for c in chemo_dates) or any(c < r for r in resect_dates for c in radio_dates):
            treated_lab_ids.append(lab_id)

    # Append ' TREATED' to Diagnosis_final where Lab ID is in treated list
    redcap['Diagnosis_final_long'] = redcap.apply(
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
    diagnosis_rows = redcap[redcap["Repeat Instrument"] == "Diagnosis Information at Study Site"].copy()
    diagnosis_rows = diagnosis_rows.dropna(axis=1, how="all")
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
    redcap = redcap.merge(diagnosis_info, on="Lab ID", how="left")
    data = pd.merge(data_metadata, sample_metadata, on=["Patient ID","Sample ID","Specimen ID"], how="outer")
    all_data=pd.merge(data, patients, on=["Patient ID"], how="outer")

    data_files = pd.merge(redcap, all_data, on=["Patient ID","Lab ID"], how="outer")

    return patients, redcap, data_files, all_data

    