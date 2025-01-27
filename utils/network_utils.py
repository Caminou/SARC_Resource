
import pandas as pd
import matplotlib.pyplot as plt
from pyvis.network import Network

# Define a function to generate unique shades of green for each Data_Type
def get_data_type_color(data_type):
    # Define a list of green shades (from light to dark)
    green_shades = {
        "in-vitro_dosing": "#a8e6cf",  # Light Green
        "WES": "#5eae60",              # Medium Green
        "LongReadSeq": "#2d6a4f",      # Dark Green
        "RNAseq": "#276749",           # Darker Green
        "scRNAseq": "#9cc2a6",         # Light Green (choose a color)
        "WTA Probe Sequencing": "#4b8c6f" # Custom color for this type
    }
    # Default to a light green if the data_type is not listed
    return green_shades.get(data_type, "#a8e6cf")  # Default to light green

def create_network_graph(df):
    # Initialize a Pyvis network
    net = Network(height="750px", width="100%", directed=True)
    
    # Define colors for other node types
    patient_color = "skyblue"
    project_color = "orange"
    
    # Add nodes and edges to the network
    for _, row in df.iterrows():
        patient_id = str(row["Patient ID"])
        project_id = str(row["Project ID"])
        data_type = str(row["Data_type"])
        
        # Add Patient and Project nodes
        net.add_node(patient_id, label=patient_id, title=f"{patient_id}", color=patient_color)
        net.add_node(project_id, label=project_id, title=f"{project_id}", color=project_color)
        
        # Get the color for this Data_Type using the mapping function
        data_type_color = get_data_type_color(data_type)
        
        # Add Data_Type node for the patient with a unique color
        data_type_node = f"{patient_id}_{data_type}"  # Create a unique ID for each Data_Type per Patient
        net.add_node(data_type_node, label=data_type, title=f"{data_type}", color=data_type_color)
        
        # Create edges:
        # - Between Patient and Project
        net.add_edge(patient_id, project_id)
        
        # - Between Patient and Data_Type
        net.add_edge(patient_id, data_type_node)
   # Disable physics to stop nodes from shaking
          # Disable physics to stop nodes from shaking
    return net