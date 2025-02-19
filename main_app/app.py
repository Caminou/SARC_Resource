import streamlit as st
st._is_running_with_streamlit = True
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
import plotly.graph_objects as go
from pyvis.network import Network
import altair as alt
import tempfile 

### Authentification process


# Add the utils folder to the Python path
sys.path.append(str(Path(__file__).resolve().parent.parent / "utils"))

# Import the modules
import data_utils
import plot_utils
import network_utils

from data_utils import load_data, process_redcap_data, merge_all_data, sanity_check
from plot_utils import plot_unique_patients, plot_samples_per_patient_with_color, plot_diagnosis_boxplot, interactive_plot
from network_utils import create_network_graph, get_data_type_color

# --- STREAMLIT APP FUNCTIONS ---

# --- MAIN FUNCTION ---
# Streamlit App
def main():

    # Set header and description
    st.title("Sarcoma Resource")
    
    # Load your data
    # Step 1: Load Data
    patients, data_metadata, redcap, sample_metadata = load_data()

    # Check if data is loaded successfully
    if patients is None or data_metadata is None or redcap is None:
        st.error("Error loading data. Exiting...")
        return
    # Step 2: Process REDCap Data
    final_df = process_redcap_data(redcap)
    
    # Step 3: Merge All Data
    combined_df = merge_all_data(patients, final_df, data_metadata, sample_metadata)
    # Now you can use combined_df for further analysis
    unique_combinations = combined_df[["Patient ID", "Specimen ID", "Sample ID"]].drop_duplicates()
    cell_line_combinations = combined_df[combined_df["Sample type"] == "Cancer cell line"][["Patient ID", "Specimen ID", "Sample ID"]].drop_duplicates()
    patient_biopsy_combinations=combined_df[combined_df["Sample type"] != "Cancer cell line"][["Patient ID", "Specimen ID", "Sample ID"]].drop_duplicates()
    analyzed_samples = combined_df[combined_df['File type'] == 'Analysed Files']
    cell_line_samples =combined_df[combined_df['Sample type'] == "PDC"]
    raw_samples = combined_df[combined_df['File type'] != 'Analysed Files']  # All other entries are considered raw

    st.write("Resource is composed by Tumor biopsies:", len(patient_biopsy_combinations), "samples from ", patient_biopsy_combinations["Patient ID"].nunique(), 
             "patient and ",len(cell_line_combinations), "Cell line samples from ",cell_line_combinations["Patient ID"].nunique())
    st.write(len(analyzed_samples)," total analyzed sample combinations.")
    st.write(len(raw_samples)," total raw sample combinations.")
   
    st.header("Combined DataFrame:")
    st.dataframe(combined_df)  # Corrected this line (removed parentheses)

    # Set a Project-Patient Network
    st.header("Sarcoma Resource Network: Mapping Patient-Project Connections")

    # Create a DataFrame for the network
    df = pd.DataFrame(combined_df[["Patient ID", "Project ID", "Data_type","Sample type"]])
    # Create and render the network graph
    net = create_network_graph(df)
    # Save the network graph as an HTML file
    net.save_graph("mygraph.html")
        # Create a temporary file
    st.components.v1.html(net.generate_html(), width=900, height=750)  # Use iframe
# Create interactive
    st.header("Patients with RedCap information:")
    st.write("Current Resource Database is formed by ",combined_df[combined_df["Sample type"] != "Cancer cell line"][["Patient ID"]].nunique()["Patient ID"] ,"and ", combined_df[combined_df["Sample type"] != "Cancer cell line"][["REDCAP ID"]].nunique()["REDCAP ID"]," of them have REDCAP data associated ID")
    st.altair_chart(interactive_plot(combined_df))
# Run the Streamlit app
if __name__ == "__main__":
    main()