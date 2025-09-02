### = LOAD LIBRARIES = ####
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
from data_utils import load_data
from plot_utils import plot_unique_patients
from network_utils import create_network_graph
from patient_history_plot import plot_lab_id_timeline
# --- STREAMLIT APP FUNCTIONS ---
# --- MAIN FUNCTION ---
# Streamlit App
def main():
    # Set header and description
    st.title("Sarcoma Resource")
    # Load your data
    # Step 1: Load Data
    patients, redcap, data_files, metadata = load_data()
    
    # Step 3: Merge All Data

    st.write("Current Resource Database is formed by ", data_files["Patient ID"].nunique(), "unique patients, ", redcap["Patient ID"].nunique(), "have REDCAP data associated")

    # Now you can use combined_df for further analysis
    st.header("Combined DataFrame:")
    st.dataframe(data_files.head())  # Corrected this line (removed parentheses)

    # Set a Project-Patient Network
    st.header("Project-Patient Network")

    # Create and render the network graph
    net = create_network_graph(data_files)
    
    # Save the network graph as an HTML file
    net.save_graph("network_graph.html")

    # Display the network in Streamlit
    st.components.v1.html(net.generate_html(), height=750)

    ## Show Data from specific patient
    pathology_ids = data_files["Pathologic Diagnosis"].unique()
    selected_pathology = st.selectbox("Select Pathology:", pathology_ids, key="patient_select")
    st.session_state.selected_pathology = selected_pathology
    # Filter data based on selected Patient ID
    patient_df = data_files[data_files["Pathologic Diagnosis"] == selected_pathology]
    patient_df = patient_df.dropna(axis=1, how="all")
    # Display Patient Data
    st.write(f"Data for the specific Pathology {selected_pathology}:")
    st.dataframe(patient_df)
    # Perform the sanity check on the filtered patient data
    # Perform the sanity check  

    # Set a Project-Patient Network
    st.header("Sarcoma Resource Network: Mapping Patient-Project Connections")
    data_files_plot = data_files[
    data_files["Data Type"].notna() & (data_files["Data Type"] != "nan")]
    data_files_plot = data_files_plot[
    data_files_plot["Project ID"].notna() & (data_files_plot["Project ID"] != "nan")]
    
    # Create a DataFrame for the network
    df = pd.DataFrame(data_files_plot[["Patient ID", "Project ID", "Data Type","Sample type"]])
    
    # Create and render the network graph
    net = create_network_graph(df)
    # Save the network graph as an HTML file
    net.save_graph("mygraph.html")
        # Create a temporary file
    st.components.v1.html(net.generate_html(), width=900, height=750)  # Use iframe
# Create interactive
    st.header("Patients with RedCap information:")
    st.write("Current Resource Database is formed by ",data_files[data_files["Sample type"] != "Cancer cell line"][["Patient ID"]].nunique()["Patient ID"] ,"and ", data_files[combined_df["Sample type"] != "Cancer cell line"][["REDCAP ID"]].nunique()["REDCAP ID"]," of them have REDCAP data associated ID")
    st.altair_chart(interactive_plot(data_files))

    data_files["Patient_Sample_Specimen"] = (
        data_files["Patient ID"].astype(str) + "_" +
        data_files["Sample ID"].astype(str) + "_" +
        data_files["Specimen ID"].astype(str) + "_" +
        data_files["Sample type"].astype(str))

    # Set up OpenAI API key --> Function generator
    openai.api_key = st.secrets["openai"]["api_key"]
    st.title("🧠 Clinical Metadata Plot Generator")
    # Load existing dataframe from session or app context (already called combined_df)
    # Assuming combined_df is defined globally before this script or imported
    def generate_plot_code(prompt, df_columns):
        column_list = ", ".join(df_columns)
        full_prompt = textwrap.dedent(f"""
        You are a data scientist. Given a dataframe named `combined_df` with the following columns:
        {column_list}
        Write Python code using Plotly Express and Streamlit to create a visualization as requested by the user below.
        Do NOT load or define a dataframe; assume `combined_df` is already available.
        Only return code. No explanations.

        User request: {prompt}
        """)

        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful Python and Plotly assistant."},
                {"role": "user", "content": full_prompt}
            ],
            temperature=0.3,
            max_tokens=500
        )
        return response.choices[0].message.content.strip()

    # --- User Input ---

    ### function generator
    st.header("Ask ChatGPT to Generate a Plot")
    user_prompt = st.text_input("What would you like to visualize?", placeholder="e.g., Bar chart of sex distribution")
    if user_prompt:
        with st.spinner("Generating visualization code with ChatGPT..."):
            try:
                code = generate_plot_code(user_prompt, data_files.columns)
                st.code(code, language="python")
                exec_globals = {"combined_df": data_files, "st": st, "px": px, "textwrap": textwrap}
                exec(code, exec_globals)
            except Exception as e:
                st.error(f"Error executing generated code: {e}")
# Run the Streamlit app
if __name__ == "__main__":
    main()