import pandas as pd
import glob
import os
import re

def standardize_to_hSC(value):
    match = re.search(r'h(\d+)', str(value), re.IGNORECASE)
    if match:
        return f"hSC{match.group(1)}"
    return value

def load_csvs_from_folder(path):
    return pd.concat((pd.read_csv(f) for f in glob.glob(os.path.join(path, "*.csv"))), ignore_index=True)

def clean_column_suffixes(df, column, suffixes=("TREATED", "POST")):
    for suffix in suffixes:
        df[column] = df[column].str.replace(fr"(\s*[-–]?\s*{suffix})$", "", regex=True).str.strip()
    return df

def custom_date_parser(x):
    try:
        return pd.to_datetime(x, format="%d/%m/%Y", errors="coerce")
    except Exception:
        return pd.NaT

def process_redcap_blocks(redcap):
    redcap = redcap.dropna(axis=1, how='all')
    demo = redcap[redcap["Repeat Instrument"] == "nan"].copy()
    diag_treat = redcap[redcap["Repeat Instrument"].isin(["Diagnosis Information at Study Site", "Treatment at Study Site"])].copy()
    diag_treat = diag_treat.dropna(axis=1, how="all")

    merged = diag_treat.merge(demo.drop(columns=["Repeat Instrument"]), on="REDCAP ID", how="left", suffixes=("", "_demo"))

    for col in demo.columns:
        if col != "REDCAP ID" and col in merged and f"{col}_demo" in merged:
            merged[col] = merged[col].combine_first(merged[f"{col}_demo"])
            merged.drop(columns=[f"{col}_demo"], inplace=True)

    return pd.concat([demo, merged], ignore_index=True)[redcap.columns]

def get_final_diagnosis(row):
    if row["Pathologic Diagnosis"] == "Others":
        return row["Composite Pathologic Diagnosis"] if pd.notna(row["Composite Pathologic Diagnosis"]) else "Others"
    return row["Pathologic Diagnosis"]

def assign_final_diagnosis_and_grade(df):
    diag_df = df[df['Repeat Instrument'] == 'Diagnosis Information at Study Site'].copy()
    custom_date_parser(diag_df, ['Date of Final Pathologic Diagnosis', 'Resection Date'])

    results = {}
    for lab_id, group in diag_df.groupby('Lab ID'):
        group["TimeDiff"] = (group["Date of Final Pathologic Diagnosis"] - group["Resection Date"]).dt.days
        after = group[group["TimeDiff"] >= 0]
        before = group[group["TimeDiff"] < 0]

        def get_closest(g, post_flag=False):
            row = g.loc[g["TimeDiff"].abs().idxmin()]
            diag = get_final_diagnosis(row)
            grade = row["Pathologic Grade (FNCLCC)"]
            if post_flag: diag += " POST"; grade = str(grade) + " POST"
            return diag, grade

        if len(group.drop_duplicates(subset=["Pathologic Diagnosis", "Composite Pathologic Diagnosis"])) == 1:
            row = group.iloc[0]
            diag = get_final_diagnosis(row)
            grade = row["Pathologic Grade (FNCLCC)"]
        elif not after.empty:
            diag, grade = get_closest(after, False)
        elif not before.empty:
            diag, grade = get_closest(before, True)
        else:
            diag, grade = None, None

        results[lab_id] = (diag, grade)

    final_df = pd.DataFrame.from_dict(results, orient="index", columns=["Diagnosis_final", "Grade_final"]).reset_index()
    final_df = final_df.rename(columns={"index": "Lab ID"})
    return df.merge(final_df, on="Lab ID", how="left")

def flag_treated_samples(df):
    treated_ids = []
    for lab_id, group in df.groupby("Lab ID"):
        res = group['Resection Date'].dropna().unique()
        chemo = group['Chemotherapy Start Date'].dropna().unique()
        radio = group['Radiotherapy Start Date'].dropna().unique()
        if res.any() and (any(c < r for r in res for c in chemo) or any(r < r2 for r in res for r2 in radio)):
            treated_ids.append(lab_id)
    return treated_ids

def simplify_diagnoses(df, treated_ids, replacement_map):
    df['Diagnosis_final_long'] = df.apply(
        lambda row: f"{row['Diagnosis_final']} TREATED" if row['Lab ID'] in treated_ids and pd.notna(row['Diagnosis_final']) else row['Diagnosis_final'],
        axis=1
    )

    diag_plot = df[df["Repeat Instrument"] == "Diagnosis Information at Study Site"].copy()
    diag_plot["Diagnosis_original"] = diag_plot["Diagnosis_final"]
    diag_plot = clean_column_suffixes(diag_plot, "Diagnosis_final")
    diag_plot["Diagnosis_final"] = diag_plot["Diagnosis_final"].replace(replacement_map)
    diag_plot.loc[diag_plot['Lab ID'].isin(['hSC68', 'hSC11', 'hSC07','hSC77']), 'Diagnosis_final'] = 'GIST'
    diag_plot["Diagnosis_final_short"] = diag_plot["Diagnosis_final"].fillna("Others")
    short_diag = diag_plot[["Lab ID", "Diagnosis_final_short"]].drop_duplicates()
    return df.merge(short_diag, on="Lab ID", how="left")

def load_data():
    ### Load and clean metadata
    data_metadata = load_csvs_from_folder("/mnt/c/Users/caminorsm/Desktop/Database/updated/data_metadata/data_metadata")
    data_metadata["Lab ID"] = data_metadata["Lab ID"].apply(standardize_to_hSC)
    sample_metadata = pd.read_csv("/mnt/c/Users/caminorsm/Desktop/Database/updated/sample_metadata.csv")
    sample_metadata["Lab ID"] = sample_metadata["Lab ID"].apply(standardize_to_hSC)

    data_metadata["Data Type"] = data_metadata["Data Type"].replace({
        "in_vitro_dosing": "in-vitro dosing",
        " in-vitro dosing": "in-vitro dosing"
    })

    ### Load patient linkage tables
    patients = pd.read_csv("/mnt/c/Users/caminorsm/Desktop/Database/updated/mapper.csv")
    PDSC = pd.read_csv("/mnt/c/Users/caminorsm/Desktop/Database/Patient_Metadata_Matching_Sheet.csv").rename(columns={
        'Redcap Number': 'REDCAP ID',
        'NCCS number/ID': 'Patient ID'
    })

    ### Merge patient info
    patients = PDSC.merge(patients, on="Patient ID", how="left").drop(columns=["REDCAP ID_x"]).rename(columns={"REDCAP ID_y": "REDCAP ID"})

    ### Load REDCap & clean dates
    redcap = pd.read_csv("/mnt/c/Users/caminorsm/Desktop/Database/updated/20250807_redcap_corrected_dates.csv",low_memory=False, parse_dates=True, dayfirst=True)
    date_cols = [col for col in redcap.columns if "date" in col.lower()]
    for col in date_cols:
        redcap[col] = pd.to_datetime(redcap[col], errors="coerce", dayfirst=True)

    ### Merge REDCap with patient map
    redcap = patients.merge(redcap, on="REDCAP ID", how="left").dropna(axis=1, how="all")

    ### Assign final diagnosis and grade
    redcap = assign_final_diagnosis_and_grade(redcap)

    ### Treated patients
    treated_ids = flag_treated_samples(redcap)

    ### Short diagnosis label
    replacement_map ={
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
        "Atypical Lipomatous Tumour":"WDLPS",
        "Well-Differentiated Liposarcoma":"WDLPS",
        "Well-Differentiated Liposarcoma and Dedifferentiated Liposarcoma":"WDLPS/DDLPS",
        "Pleomorphic Liposarcoma":"Others",
        "Malignant Peripheral Nerve Sheath Tumour":"Others"}  # your original replacement dict
    redcap = simplify_diagnoses(redcap, treated_ids, replacement_map)

    ### Merge metadata
    data = pd.merge(data_metadata, sample_metadata, on=["Patient ID", "Sample ID", "Specimen ID"], how="outer")
    data = pd.merge(data, patients, on=["Patient ID"],how="outer")
    data_files = pd.merge(redcap, data, on=["Patient ID", "Lab ID"], how="outer")
    date_cols = [col for col in redcap.columns if "date" in col.lower()]
    for col in date_cols:
        redcap[col] = pd.to_datetime(redcap[col], errors="coerce", dayfirst=True)
        
    return patients, redcap, data_files, data
