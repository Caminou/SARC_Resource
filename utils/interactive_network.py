import streamlit as st
import networkx as nx
from pyvis.network import Network
import pandas as pd

# Sample Data
data = pd.read_csv("~/Database/data_metadata.csv")
# Convert to DataFrame
df = pd.DataFrame(data)

# Create a graph
G = nx.Graph()

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

net = Network(height="750px", width="100%", directed=True)
for _, row in df.iterrows():
    patient_id = str(row["Patient ID"])
    project_id = str(row["Project ID"])
    data_type = str(row["Data_type"])
    patient_color="lightgrey"
    project_color="orange"
    # Add Patient and Project nodes
    G.add_node(patient_id, label=patient_id, title=f"{patient_id}", color=patient_color)
    G.add_node(project_id, label=project_id, title=f"{project_id}", color=project_color)
        
        # Get the color for this Data_Type using the mapping function
    data_type_color = get_data_type_color(data_type)
        
        # Add Data_Type node for the patient with a unique color
    data_type_node = f"{patient_id}_{data_type}"  # Create a unique ID for each Data_Type per Patient
    G.add_node(data_type_node, label=data_type, title=f"{data_type}", color=data_type_color)
        
        # Create edges:
        # - Between Patient and Project
    G.add_edge(patient_id, project_id)
        
        # - Between Patient and Data_Type
    G.add_edge(patient_id, data_type_node)

# Create a Pyvis network
net = Network(notebook=True, cdn_resources='in_line', height='500px', width='100%')
net.from_nx(G)

# Save the graph to an HTML file
net.save_graph('network.html')

# Display the graph in Streamlit
st.components.v1.html(open('network.html', 'r').read(), height=600)

# Function to get summary
def get_summary(project_name):
    patients = df[df['Project'] == project_name]['Patient'].nunique()
    return f"Project {project_name} has {patients} patients."

# Handle node click event
node_clicked = st.text_input("Enter the Project name to get summary:")
if node_clicked:
    st.write(get_summary(node_clicked))