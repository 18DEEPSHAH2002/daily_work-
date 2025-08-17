import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
from io import StringIO

# Use caching to prevent re-running the data download and processing on every interaction
@st.cache_data(ttl=600) # Cache data for 10 minutes
def load_and_process_data(sheet_url):
    """
    Loads data from the specified Google Sheet URL, processes each tab,
    and returns the analyzed data.
    """
    try:
        # Extract the sheet ID from the URL using regex
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', sheet_url)
        if not match:
            st.error("Invalid Google Sheet URL. Please check the hardcoded URL in the script.")
            return None, None
        sheet_id = match.group(1)

        # List of sheet names (tabs) to process.
        sheet_names = [
            "ADC G", "ADC RD", "ADC UD", "ADC Khanna", "ADC Jagraon", "DRO",
            "SDM RaikotHQ", "CMFO", "AC G", "EAC(UT)", "SDM-Khanna", "SDM-Jagraon",
            "SDM-Samrala", "SDM-East", "SDM-West", "AC(UT)", "Political Non Political Works",
            "DC Meeting Actionables", "SDM-Political Non Political Wor", "Extra", "Back Sheet"
        ]

        department_data = {}
        department_dfs = {}
        
        progress_bar = st.progress(0, text="Initializing data load...")
        
        for i, sheet_name in enumerate(sheet_names):
            try:
                # Construct the URL to download the sheet as a CSV
                csv_export_url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={sheet_name.replace(" ", "%20")}'
                df = pd.read_csv(csv_export_url)

                # Analyze the data from the sheet
                total, completed, processed_df = analyze_task_data(df)

                if processed_df is not None and total > 0:
                    department_data[sheet_name] = {'Total Tasks': total, 'Completed Tasks': completed}
                    department_dfs[sheet_name] = processed_df
            
            except Exception as e:
                # This allows the app to continue even if some sheets are missing or fail
                st.warning(f"Could not read or process sheet: '{sheet_name}'. It might not exist or be formatted incorrectly. Skipping.")

            progress_bar.progress((i + 1) / len(sheet_names), text=f"Loading: {sheet_name}")

        progress_bar.empty()
        return department_data, department_dfs

    except Exception as e:
        st.error(f"Major failure loading from Google Sheet. Please ensure the link is correct and the sheet is publicly accessible. Error: {e}")
        return None, None


def analyze_task_data(df):
    """
    Analyzes a DataFrame to count total and completed tasks.
    """
    try:
        df.dropna(how='all', inplace=True)
        if df.empty:
            return 0, 0, None

        task_description_cols = ['Project/Task Name', 'KPI ID', 'Issue']
        primary_task_col = next((col for col in task_description_cols if col in df.columns), None)

        possible_status_cols = ['% Achievement', '% Achievement ', 'Achievement', 'Status']
        achievement_col = next((col for col in possible_status_cols if col in df.columns), None)

        total_tasks = len(df) if not primary_task_col else df[primary_task_col].notna().sum()
        completed_tasks = 0

        if achievement_col:
            df[achievement_col] = df[achievement_col].astype(str).str.lower()
            completed_tasks = df[achievement_col].str.contains('complete|100', na=False).sum()

        return total_tasks, completed_tasks, df

    except Exception as e:
        st.warning(f"Could not process a DataFrame. Error: {e}")
        return 0, 0, None

def show_home_page(department_data):
    """
    Displays the main dashboard with an aggregated view of all departments.
    """
    st.header("📈 Overall Task Analysis")
    st.markdown("This dashboard provides a summary of task completion across all departments, pulled directly from the Google Sheet.")

    results_df = pd.DataFrame.from_dict(department_data, orient='index')
    results_df = results_df.sort_values(by='Total Tasks', ascending=False)

    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=results_df.index, y=results_df['Total Tasks'], name='Total Tasks',
        marker_color='#636EFA', text=results_df['Total Tasks'], textposition='auto'
    ))
    fig.add_trace(go.Bar(
        x=results_df.index, y=results_df['Completed Tasks'], name='Completed Tasks',
        marker_color='#00CC96', text=results_df['Completed Tasks'], textposition='auto'
    ))
    fig.update_layout(
        barmode='group', title='<b>Task Completion Status by Department</b>',
        xaxis_title='Department', yaxis_title='Number of Tasks',
        legend_title='Status', font=dict(family="Arial, sans-serif", size=12),
        plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(gridcolor='lightgrey'),
        xaxis={'categoryorder':'total descending'}
    )
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

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Tasks", f"{total_tasks}")
    col2.metric("Completed Tasks", f"{completed_tasks}")
    col3.metric("Pending Tasks", f"{pending_tasks}")
    col4.metric("Completion Rate", f"{completion_rate:.2f}%")

    st.subheader("Task Details")
    st.dataframe(df, use_container_width=True)

def main():
    """
    Main function to run the Streamlit application.
    """
    st.set_page_config(page_title="Department Task Analysis", layout="wide")
    st.title("📊 Department Weekly Task Analysis from Google Sheets")

    # The URL is now hardcoded and data loading is triggered automatically
    sheet_url = "https://docs.google.com/spreadsheets/d/11ziSlsf3oDqffciCPvkreKg4Wz2VuY_sc4g-yTGnmMY/edit?usp=sharing"
    
    department_data, department_dfs = load_and_process_data(sheet_url)

    # --- Display content after data is loaded ---
    if department_data and department_dfs:
        st.sidebar.title("Navigation")
        page_options = ["Home"] + sorted(list(department_data.keys()))
        selected_page = st.sidebar.radio("Go to", page_options)

        if selected_page == "Home":
            show_home_page(department_data)
        elif selected_page in department_data:
            show_department_page(selected_page, department_data[selected_page], department_dfs[selected_page])
    else:
        st.warning("No valid data could be extracted from the Google Sheet. Please check the sheet's sharing settings and content.")

if __name__ == "__main__":
    main()
