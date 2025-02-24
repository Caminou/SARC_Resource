import streamlit as st
st._is_running_with_streamlit = True
import sys
from pathlib import Path
import pandas as pd
import matplotlib.pyplot as plt
import plotly.express as px
from pyvis.network import Network
import altair as alt

# --- VISUALIZATION FUNCTIONS ---
def plot_unique_patients(df):
    """Interactive bar plot for unique patients."""
    st.header("Interactive Visualization")
    group_by_column = st.selectbox("Select a column to group by:", options=df.columns, index=0)
    try:
        unique_patients = df.groupby(group_by_column)["Patient ID"].nunique().reset_index()
        unique_patients.columns = [group_by_column, "Unique_Patient_Count"]

        fig, ax = plt.subplots()
        ax.bar(unique_patients[group_by_column], unique_patients["Unique_Patient_Count"])
        ax.set_xlabel(group_by_column)
        ax.set_ylabel("Unique Patient Count")
        ax.set_title(f"Unique Patients per {group_by_column}")
        st.pyplot(fig)
    except Exception as e:
        st.error(f"Error grouping by '{group_by_column}': {e}")


def plot_diagnosis_boxplot(df):
    """Plot an interactive boxplot of diagnoses vs. number of patients."""
    # Group data by Diagnosis and count the number of unique patients
    diagnosis_counts = df.groupby("Pathologic Diagnosis")["Patient ID"].nunique().reset_index()
    diagnosis_counts.columns = ["Diagnosis", "Number of Patients"]

    # Create a boxplot using Plotly
    fig = px.box(
        diagnosis_counts,
        y="Number of Patients",
        x="Diagnosis",
        title="Interactive Boxplot: Diagnoses vs. Number of Patients",
        labels={"Number of Patients": "Number of Patients", "Diagnosis": "Diagnosis"},
        template="plotly_white",
    )

    # Update layout for better appearance
    fig.update_layout(
        xaxis_tickangle=-45,
        xaxis_title="Diagnosis",
        yaxis_title="Number of Patients",
        height=600,
    )
    return fig


def plot_samples_per_patient_with_color(data_metadata):
    """
    Creates a bar chart to visualize the number of unique samples per patient,
    colored by a user-selected column (e.g., Sex, File Type, etc.).
    """
    if "Patient ID" in data_metadata.columns and "Sample ID" in data_metadata.columns:
        # Select the column to color by
        column_to_color = st.selectbox("Select a column to color by:", data_metadata.columns)

        if column_to_color not in data_metadata.columns:
            st.warning(f"Column '{column_to_color}' not found in the dataset.")
            return None

        # Group by Patient ID and count the number of unique Sample ID
        # Merge the selected column to color by
        grouped_data = (data_metadata.groupby("Patient ID")["Sample ID"].nunique().reset_index(name="Number of Samples"))
        grouped_data = grouped_data.merge(data_metadata[["Patient ID", column_to_color]].drop_duplicates(subset=["Patient ID"]),on="Patient ID",how="left")  # Ensures only one match per Patient ID

# Step 3: Check the final table
        # Create the bar chart with color based on the selected column
        fig = px.bar(
            grouped_data,
            x="Patient ID",
            y="Number of Samples",
            color=column_to_color,  # Color by the selected column
            title="*Number of Unique Samples per Patient (Colored by " + column_to_color + ")",
            labels={"Patient ID": "Patient ID", "Number of Samples": "Number of Samples"},
        )
        fig.update_layout(
            xaxis={'categoryorder': 'total descending'},  # Optional: Sort x-axis by number of samples
            xaxis_title="Patient ID",
            yaxis_title="Number of Unique Samples",
            bargap=0.2  # Adjust bar gap
        )
        return fig
    else:
        st.warning("Columns 'Patient ID' or 'Sample ID' are missing in the dataset.")
        return None


def interactive_plot(combined_df): 
    combined_df["Patient_Sample_Specimen"] = (
        combined_df["Patient ID"].astype(str) + "_" +
        combined_df["Sample ID"].astype(str) + "_" +
        combined_df["Specimen ID"].astype(str) + "_" +
        combined_df["Sample type"].astype(str)
    )

    # Filter dataset where repeat_instance == 1
    filtered_df = combined_df[combined_df["Repeat Instance"] == 1]

    # Count unique patients per pathology
    disease_counts = (
        filtered_df.groupby("Pathologic Diagnosis")["Patient ID"]
        .nunique()
        .reset_index()
        .rename(columns={"Patient ID": "Unique Patients"})
    )

    # Calculate percentage and keep it numeric
    total_count = disease_counts["Unique Patients"].sum()
    disease_counts["Percentage"] = (disease_counts["Unique Patients"] / total_count) * 100  # Keep as float

    # Selection filters
    disease_select = alt.selection_single(fields=["Pathologic Diagnosis"], empty="all", name="DiagnosisFilter")
    data_type_select = alt.selection_single(fields=["Data_type"], empty="all", name="DataTypeFilter")
    sample_type_select = alt.selection_single(fields=["Sample type"], empty="all", name="SampleTypeFilter")
    # Corrected Filtering Logic
    filter_condition = (
        (alt.datum["Pathologic Diagnosis"] == disease_select) | (disease_select)
        ) & (
            (alt.datum["Data_type"] == data_type_select) | (data_type_select)
            )

    # **Pie Chart (Pathologic Diagnosis)**
    disease_pie = (
        alt.Chart(disease_counts)
        .mark_arc(innerRadius=50)
        .encode(
            theta=alt.Theta("Unique Patients:Q", title="Unique Patients"),
            color=alt.Color(
                "Pathologic Diagnosis:N",
                scale=alt.Scale(scheme="category20"),
                legend=alt.Legend(title="Pathologic Diagnosis (REDCAP)", orient="right"),
            ),
            opacity=alt.condition(
                disease_select, alt.value(1), alt.value(0.3)
            ),
            tooltip=[
                "Pathologic Diagnosis:N", 
                "Unique Patients:Q", 
                alt.Tooltip("Percentage:Q", format=".1f")  # Ensure numeric format
            ],
        )
        .add_selection(disease_select)
        .transform_filter(filter_condition)
        .properties(title="Unique Patients per Pathologic Diagnosis", width=400, height=400)
    )

    # **Bar Chart (Data Type)**
    project_patient_counts = (
        filtered_df.groupby(["Pathologic Diagnosis", "Sample type", "Data_type"])["Patient_Sample_Specimen"]
        .nunique()
        .reset_index(name="Unique Patient_Sample_Specimen (Biosample)")
    )

    datatype_summary = (
        alt.Chart(project_patient_counts)
        .mark_bar()
        .encode(
            x=alt.X("Sample type:N", title="Sample type"),
            y=alt.Y("Unique Patient_Sample_Specimen (Biosample):Q", title="Number of Samples"),
            color=alt.Color(
                "Data_type:N",
                scale=alt.Scale(scheme="category20"),
                legend=alt.Legend(title="Data Type", orient="right"),
            ),
            opacity=alt.condition(
                data_type_select & sample_type_select, alt.value(1), alt.value(0.3)
            ),
            tooltip=["Sample type", "Unique Patient_Sample_Specimen (Biosample)", "Data_type"],
        )
        .add_selection(data_type_select)
        .add_selection(sample_type_select)
        .transform_filter(disease_select)
        .properties(width=500, height=300)
    )

    # **Treatment Summary**
    # Define interactive selections for data type, sample type, and disease

    # **Treatment Summary (Diagnosis_summary)**
    treatment = (
        combined_df
        .groupby(["Pathologic Diagnosis", "Cancer treatment regimen 1","Data_type","Sample type"])["Patient_Sample_Specimen"]
        .size()
        .reset_index(name="Number of Patient_Sample_Specimen")
    )


    Diagnosis_summary = (
        alt.Chart(treatment)
        .mark_bar()
        .encode(
            x=alt.X("Cancer treatment regimen 1:N", title="Treatment (REDCAP)"),
            y=alt.Y("Number of Patient_Sample_Specimen:Q", title="Number of Patient_Sample_Specimen (Biosample)"),
            color=alt.Color("Cancer treatment regimen 1:N", scale=alt.Scale(scheme="category20")),
            tooltip=["Cancer treatment regimen 1", "Number of Patient_Sample_Specimen"],
        )
        .transform_filter(data_type_select & sample_type_select & disease_select)
        .properties(width=500)
    )

    # **Mismatch Data Plot**

    Mismatch_data = (
        combined_df
        .groupby(["Pathologic Diagnosis", "Diagnosis","Data_type","Sample type"])["Patient_Sample_Specimen"]
        .nunique()
        .reset_index(name="Unique Patient_Sample_Specimen (Biosample)")
    )

    Mismatch_plot = (
        alt.Chart(Mismatch_data)
        .mark_bar()
        .encode(
            x=alt.X("Pathologic Diagnosis:N", title="Pathologic Diagnosis (REDCAP)"),
            y=alt.Y("Diagnosis:N", title="Diagnosis (WXY lab)"),
            color=alt.Color("Diagnosis:N", scale=alt.Scale(scheme="category20")),
            tooltip=["Pathologic Diagnosis", "Diagnosis"],
        )
        .transform_filter(data_type_select & sample_type_select & disease_select)
        .properties(width=500)
    )
    # **Merge all plots**
    
    chart_row = (disease_pie | datatype_summary).resolve_scale(color='independent')
    chart_row1 = (Diagnosis_summary | Mismatch_plot).resolve_scale(color="independent")
    final_chart = (chart_row & chart_row1).resolve_scale(color="independent")

    return final_chart


