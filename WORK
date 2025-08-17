import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from io import StringIO

def process_file(uploaded_file):
    """
    Processes a single uploaded CSV file to count tasks and return the DataFrame.

    Args:
        uploaded_file: The file-like object from Streamlit's file_uploader.

    Returns:
        A tuple containing (total_tasks, completed_tasks, DataFrame).
        Returns (0, 0, None) if the file cannot be processed.
    """
    try:
        # Read the content of the file into a DataFrame
        string_data = StringIO(uploaded_file.getvalue().decode('utf-8'))
        df = pd.read_csv(string_data)

        # --- Data Cleaning: Remove rows where all values are NaN ---
        df.dropna(how='all', inplace=True)
        if df.empty:
            return 0, 0, None

        # --- Identify Key Columns ---
        # Find the column for task descriptions
        task_description_cols = ['Project/Task Name', 'KPI ID', 'Issue']
        primary_task_col = next((col for col in task_description_cols if col in df.columns), None)

        # Find the column for achievement/status
        achievement_col = None
        possible_status_cols = ['% Achievement', '% Achievement ', 'Achievement', 'Status']
        achievement_col = next((col for col in possible_status_cols if col in df.columns), None)

        # --- Calculate Total and Completed Tasks ---
        total_tasks = 0
        completed_tasks = 0

        if primary_task_col:
            # Count rows with a valid task description
            total_tasks = df[primary_task_col].notna().sum()
        else:
            # Fallback: if no task column, count all non-empty rows
            total_tasks = len(df)

        if achievement_col:
            # A task is "completed" if the status column contains 'complete' or '100'.
            # Ensure the column is treated as a string for searching.
            df[achievement_col] = df[achievement_col].astype(str).str.lower()
            completed_tasks = df[achievement_col].str.contains('complete|100', na=False).sum()

        return total_tasks, completed_tasks, df

    except Exception as e:
        st.warning(f"Could not process file: {uploaded_file.name}. Error: {e}")
        return 0, 0, None

def show_home_page(department_data):
    """
    Displays the main dashboard with an aggregated view of all departments.
    """
    st.header("📈 Overall Task Analysis")
    st.markdown("This dashboard provides a summary of task completion across all departments.")

    # Convert the analysis data into a DataFrame for visualization
    results_df = pd.DataFrame.from_dict(department_data, orient='index')
    results_df = results_df.sort_values(by='Total Tasks', ascending=False)

    # --- Create the Bar Chart using Plotly ---
    fig = go.Figure()

    # Bar for Total Tasks
    fig.add_trace(go.Bar(
        x=results_df.index,
        y=results_df['Total Tasks'],
        name='Total Tasks',
        marker_color='#636EFA',
        text=results_df['Total Tasks'],
        textposition='auto'
    ))

    # Bar for Completed Tasks
    fig.add_trace(go.Bar(
        x=results_df.index,
        y=results_df['Completed Tasks'],
        name='Completed Tasks',
        marker_color='#00CC96',
        text=results_df['Completed Tasks'],
        textposition='auto'
    ))

    # Customize chart layout for better readability
    fig.update_layout(
        barmode='group',
        title='<b>Task Completion Status by Department</b>',
        xaxis_title='Department',
        yaxis_title='Number of Tasks',
        legend_title='Status',
        font=dict(family="Arial, sans-serif", size=12),
        plot_bgcolor='rgba(0,0,0,0)',
        yaxis=dict(gridcolor='lightgrey'),
        xaxis={'categoryorder':'total descending'}
    )

    # Display the chart and the summary data table
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Summary Data")
    st.dataframe(results_df, use_container_width=True)

def show_department_page(department_name, department_info, df):
    """
    Displays a detailed view for a single selected department.
    """
    st.header(f"🔍 Analysis for: {department_name}")

    total_tasks = department_info['Total Tasks']
    completed_tasks = department_info['Completed Tasks']
    pending_tasks = total_tasks - completed_tasks
    completion_rate = (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0

    # --- Display Key Metrics ---
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tasks", f"{total_tasks}")
    col2.metric("Completed Tasks", f"{completed_tasks}")
    col3.metric("Pending Tasks", f"{pending_tasks}")
    col4.metric("Completion Rate", f"{completion_rate:.2f}%")

    # --- Display Raw Data Table ---
    st.subheader("Task Details")
    st.markdown("Here is the full list of tasks from the uploaded file for this department.")
    st.dataframe(df, use_container_width=True)


def main():
    """
    Main function to run the Streamlit application.
    """
    st.set_page_config(page_title="Department Task Analysis", layout="wide")

    st.title("📊 Department Weekly Task Analysis")
    st.markdown("""
    Upload your department's weekly CSV files to analyze task progress.
    The **Home** page shows an overview of all departments, and you can select a specific department from the sidebar to see its detailed task list.
    """)

    # --- File Uploader ---
    uploaded_files = st.file_uploader(
        "Upload Department CSV Files",
        type=['csv'],
        accept_multiple_files=True,
        help="You can drag and drop multiple files here."
    )

    if uploaded_files:
        department_data = {}
        department_dfs = {}
        excluded_files = ['read me.csv', 'master sheet.csv']

        # --- Process each uploaded file ---
        for uploaded_file in uploaded_files:
            file_name_lower = uploaded_file.name.lower()
            if any(excluded in file_name_lower for excluded in excluded_files):
                continue

            # Clean up the filename to use as the department name
            clean_name = uploaded_file.name.replace("Saturday Review- DC Ludhiana.xlsx - ", "").replace(".csv", "")
            
            total, completed, df = process_file(uploaded_file)
            if df is not None and total > 0:
                department_data[clean_name] = {'Total Tasks': total, 'Completed Tasks': completed}
                department_dfs[clean_name] = df

        if department_data:
            # --- Sidebar Navigation ---
            st.sidebar.title("Navigation")
            page_options = ["Home"] + sorted(list(department_data.keys()))
            selected_page = st.sidebar.radio("Go to", page_options)

            # --- Page Routing ---
            if selected_page == "Home":
                show_home_page(department_data)
            elif selected_page in department_data:
                show_department_page(selected_page, department_data[selected_page], department_dfs[selected_page])
        else:
            st.warning("No valid data could be extracted. Please check the files and ensure they are not empty.")

    else:
        st.info("Upload your CSV files to begin the analysis.")

if __name__ == "__main__":
    main()
