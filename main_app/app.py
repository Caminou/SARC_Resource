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
def show_data_table(df):
    """Display the data table in the Streamlit UI."""
    st.write("Full Dataset:")
    st.dataframe(df)

def sanity_check(df):
    """Perform sanity checks and highlight inconsistencies."""
    st.header("Sanity Check")
    issues = df[(df["Gender"] == "Male") & (df["Sex"] == "F")]  # Example check
    if not issues.empty:
        st.warning("Found inconsistencies:")
        st.dataframe(issues)
    else:
        st.success("No inconsistencies found!")

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
    st.dataframe(combined_df)  # Corrected this line (removed parentheses)

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

# Run the Streamlit app
if __name__ == "__main__":
    main()