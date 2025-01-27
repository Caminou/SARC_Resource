import streamlit as st
st._is_running_with_streamlit = True
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
from pyvis.network import Network

# Add the utils folder to the Python path
sys.path.append(str(Path(__file__).resolve().parent.parent / "utils"))

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
    inconsistencies = sanity_check(combined_df)
    # # Display the results in Streamlit
    if inconsistencies:
        st.error(f"Found {len(inconsistencies)} inconsistencies.")
        st.write("Details:")
        st.json(inconsistencies)  # Use a JSON viewer for better display
    else:
        st.success("No inconsistencies found in the data!")

# Run the Streamlit app
if __name__ == "__main__":
    main()