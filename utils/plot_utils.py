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
    # Process the data for pie chart with percentage
    disease_counts = combined_df['Pathologic Diagnosis'].value_counts().reset_index()
    disease_counts.columns = ['Pathologic Diagnosis', 'Count']

    # Calculate percentage
    total_count = disease_counts['Count'].sum()
    disease_counts['Percentage'] = (disease_counts['Count'] / total_count) * 100
    disease_counts['Percentage'] = disease_counts['Percentage'].map('{:.1f}%'.format)
    # Selection filter
    disease_select = alt.selection_single(fields=["Pathologic Diagnosis"], empty="all")

    # Create an Altair Pie Chart with Percentage Display
    disease_pie = (
        alt.Chart(disease_counts)
        .mark_arc(innerRadius=50)
        .encode(
            theta=alt.Theta("Count:Q", title="Total Cases"),
            color=alt.Color(
                "Pathologic Diagnosis:N",
                scale=alt.Scale(scheme="category20"),
                legend=alt.Legend(title="Pathologic Diagnosis", orient="left")  # Custom legend title for Pathology
            ),
            opacity=alt.condition(disease_select, alt.value(1), alt.value(0.3)),
            tooltip=[
                "Pathologic Diagnosis:N",
                "Percentage",
                alt.Tooltip("Percentage:Q", format=".1f")]
        )
        .add_selection(disease_select)
        .properties(title="Pathologic Diagnosis Distribution", width=400, height=400)
    )
    project_patient_counts = (
        combined_df.groupby(["Pathologic Diagnosis", "Project ID", "Data_type"])["Patient ID"]
        .nunique()  # Count unique patients
        .reset_index()
    )
    # Rename columns for clarity
    project_patient_counts.columns = ["Pathologic Diagnosis", "Project ID", "Data_type", "Number of Patients"]

    # Summary Bar Chart (Filtered by Pie Selection)
    datatype_summary = (
        alt.Chart(project_patient_counts)
        .mark_bar()
        .encode(
            x=alt.X("Project ID:N", title="Project ID"),
            y=alt.Y("Number of Patients:Q", title="Number of Patients"),
            tooltip=["Project ID", "Number of Patients","Data_type"],
            color=alt.Color("Data_type:N",
                scale=alt.Scale(scheme="category20"),
                legend=alt.Legend(title="Data_type", orient="left") 
        ))
        .transform_filter(disease_select)  # Apply the filter from the pie chart
        .properties(title="Patients per Project (Filtered by Disease)", width=500)
    )

    treatment = (
        combined_df.groupby(["Pathologic Diagnosis", "Cancer treatment regimen 1"])["Patient ID"]
        .nunique()  # Count unique patients
        .reset_index()
    )
    # Rename columns for clarity
    treatment.columns = ["Pathologic Diagnosis", "Treatment", "Number of Patients"]

    # Summary Bar Chart (Filtered by Pie Selection)
    Diagnosis_summary = (
        alt.Chart(treatment)
        .mark_bar()
        .encode(
            x=alt.X("Treatment:N", title="Treatment"),
            y=alt.Y("Number of Patients:Q", title="Number of Patients"),
            tooltip=["Treatment", "Number of Patients"],
            color=alt.Color("Treatment:N",
                scale=alt.Scale(scheme="category20"),
                legend=alt.Legend(title="Treatment:N", orient="left"))
        )
        .transform_filter(disease_select)  # Apply the filter from the pie chart
        .properties(title="Patients per Project (Filtered by Disease)", width=500)
    )
    ## Merge all plots at the same time
    chart_row = (disease_pie | datatype_summary).resolve_scale(
        color='independent'  # Crucial: Make the color scales independent
    )
    chart_row = (chart_row & Diagnosis_summary).resolve_scale(
        color="independent"
        )

    return(chart_row)
