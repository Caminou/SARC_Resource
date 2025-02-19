import streamlit as st
st._is_running_with_streamlit = True
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from pyvis.network import Network

# Add the utils folder to the Python path
sys.path.append(str(Path(__file__).resolve().parent / "utils"))

# Import the modules
import data_utils
import plot_utils
import network_utils

from data_utils import load_data, process_redcap_data, merge_all_data

from plot_utils import plot_unique_patients
from network_utils import create_network_graph

# --- STREAMLIT APP FUNCTIONS ---
# --- MAIN FUNCTION ---
# Streamlit App
def main():

    # Set header and description
    st.title("Sarcoma Resource")
    
    # Load your data
    # Step 1: Load Data
    patients, data_metadata, redcap = load_data()

    # Check if data is loaded successfully
    if patients is None or data_metadata is None or redcap is None:
        st.error("Error loading data. Exiting...")
        return
    
    # Step 2: Process REDCap Data
    final_df = process_redcap_data(redcap)
    
    # Step 3: Merge All Data
    combined_df = merge_all_data(patients, final_df, data_metadata)
    st.write("Current Resource Database is formed by ", patients["Patient ID"].nunique(), "unique patients, ", combined_df["Patient ID"].nunique(), "have REDCAP data associated")

    # Now you can use combined_df for further analysis
    st.header("Combined DataFrame:")
    st.dataframe(combined_df.head())  # Corrected this line (removed parentheses)

    # Set a Project-Patient Network
    st.header("Project-Patient Network")

    # Create a DataFrame for the network
    df = pd.DataFrame(data_metadata[["Patient ID", "Project ID", "Data_type"]])

    # Create and render the network graph
    net = create_network_graph(df)
    
    # Save the network graph as an HTML file
    net.save_graph("network_graph.html")

    # Display the network in Streamlit
    st.components.v1.html(net.generate_html(), height=750)

    ## Show Data from specific patient
    pathology_ids = combined_df["Pathologic Diagnosis"].unique()
    selected_pathology = st.selectbox("Select Pathology:", pathology_ids, key="patient_select")
    st.session_state.selected_pathology = selected_pathology
    # Filter data based on selected Patient ID
    patient_df = combined_df[combined_df["Pathologic Diagnosis"] == selected_pathology]
    patient_df = patient_df.dropna(axis=1, how="all")
    # Display Patient Data
    st.write(f"Data for the specific Pathology {selected_pathology}:")
    st.dataframe(patient_df)
    from data_utils import sanity_check
    # Perform the sanity check on the filtered patient data
    # Perform the sanity check  

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

# Run the Streamlit app
if __name__ == "__main__":
    main()