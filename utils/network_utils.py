import pandas as pd
from pyvis.network import Network

def get_data_type_color(data_type):
    color_map = {
        "in_vitro_dosing": "#aec7e1",
        " in-vitro dosing": "#1f77b4",
        "WES": "#f7b6d2",
        "LongReadSeq": "#2ca02c",
        "RNAseq": "#d62728",
        "scRNAseq": "#9467bd",
        "WTA Probe Sequencing": "#8c564b",
        "WGS": "#e377c2",
        "Oncomine Report": "#7f7f7f",
        "CutandRun": "#bcbd22",
    }
    return color_map.get(data_type, "#E0F2F7")

def get_sample_type_color(sample_type):
    color_map = {
        "PDSC": "#aec7e1",
        "Patient tumor": "#1f77b4",
        "DTC": "#f7b6d2",
        "blood": "#d62728",
    }
    return color_map.get(sample_type, "#E0F2F7")

def create_network_graph(df):
    net = Network(height="750px", width="100%", directed=True)

    patient_color = "lightgrey"
    project_color = "orange"
    no_sample_color = "lightblue"

    # Make sure we include ALL unique Patient IDs even if Sample type is missing
    unique_patients = df[["Project ID", "Patient ID"]].drop_duplicates()

    for _, row in unique_patients.iterrows():
        project_id = str(row["Project ID"])
        patient_id = str(row["Patient ID"])

        # Add Project and Patient nodes
        net.add_node(patient_id, label=patient_id, title=patient_id, color=patient_color)
        net.add_node(project_id, label=project_id, title=project_id, color=project_color, size=40)
        net.add_edge(patient_id, project_id, color=patient_color)  # Patient → Project

    # Grouping by Patient-Sample combination to reduce redundant edges
    grouped_df = df.groupby(["Project ID", "Patient ID", "Sample type"])["Data_type"].unique().reset_index()

    for _, row in grouped_df.iterrows():
        patient_id = str(row["Patient ID"])
        project_id = str(row["Project ID"])
        sample_type = str(row["Sample type"]) if pd.notna(row["Sample type"]) else "No Sample Info"
        data_types = row["Data_type"]

        # If Sample type is missing, create a placeholder node
        if sample_type == "No Sample Info":
            no_sample_node = f"{patient_id}_NoSample"
            net.add_node(no_sample_node, label="No Sample Info", title=f"{patient_id} (No Sample)", color=no_sample_color)
            net.add_edge(patient_id, no_sample_node, color=no_sample_color)

            # If there are data types, connect them to "No Sample Info"
            for data_type in data_types:
                data_type_color = get_data_type_color(data_type)
                data_type_node = f"{no_sample_node}_{data_type}"
                net.add_node(data_type_node, label=data_type, title=f"{patient_id} - {data_type}", color=data_type_color)
                net.add_edge(no_sample_node, data_type_node, color=data_type_color)

        else:
            # Normal case: Patient → Sample type → Data type
            patient_sample_node = f"{patient_id}_{sample_type}"
            sample_type_color = get_sample_type_color(sample_type)
            net.add_node(patient_sample_node, label=sample_type, title=f"{patient_id} - {sample_type}", color=sample_type_color)
            net.add_edge(patient_id, patient_sample_node, color=sample_type_color)

            for data_type in data_types:
                data_type_color = get_data_type_color(data_type)
                data_type_node = f"{patient_sample_node}_{data_type}"
                net.add_node(data_type_node, label=data_type, title=f"{patient_id} - {sample_type} - {data_type}", color=data_type_color)
                net.add_edge(patient_sample_node, data_type_node, color=data_type_color)

    return net
