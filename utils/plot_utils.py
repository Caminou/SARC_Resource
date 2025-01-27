import pandas as pd
import matplotlib.pyplot as plt

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
