import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import re
import requests
from io import StringIO
import urllib.parse

# Use caching to prevent re-running the data download and processing on every interaction
@st.cache_data(ttl=600) # Cache data for 10 minutes
def load_and_process_data(sheet_url):
    """
    Loads data from the specified Google Sheet URL, processes each tab,
    and returns the analyzed data with enhanced error handling.
    """
    try:
        match = re.search(r'/d/([a-zA-Z0-9-_]+)', sheet_url)
        if not match:
            st.error("Invalid Google Sheet URL. Please check the hardcoded URL in the script.")
            return None, None
        sheet_id = match.group(1)

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
                # More robust URL encoding for sheet names with special characters
                encoded_sheet_name = urllib.parse.quote_plus(sheet_name)
                csv_export_url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/gviz/tq?tqx=out:csv&sheet={encoded_sheet_name}'
                
                # Use requests to fetch the data with a timeout
                response = requests.get(csv_export_url, timeout=10)
                
                # Raise an exception for bad status codes (like 403 Forbidden or 404 Not Found)
                response.raise_for_status()
                
                # If successful, read the content into pandas
                df = pd.read_csv(StringIO(response.text))
                total, statuses, processed_df = analyze_task_data(df)

                if processed_df is not None and total > 0:
                    department_data[sheet_name] = {'Total Tasks': total, **statuses}
                    department_dfs[sheet_name] = processed_df
            
            # *** NEW: SPECIFIC ERROR HANDLING ***
            except requests.exceptions.HTTPError as e:
                st.error(f"Failed to access '{sheet_name}': {e}. This strongly indicates a permissions issue. Please ensure the Google Sheet's sharing is set to 'Anyone with the link can view'.")
            except requests.exceptions.RequestException as e:
                st.error(f"A network error occurred for '{sheet_name}': {e}. This could be a firewall or connectivity issue.")
            except Exception as e:
                st.warning(f"Could not process sheet '{sheet_name}' after download. It might be empty or formatted incorrectly. Error: {e}")

            progress_bar.progress((i + 1) / len(sheet_names), text=f"Loading: {sheet_name}")

        progress_bar.empty()
        return department_data, department_dfs

    except Exception as e:
        st.error(f"A major failure occurred during the data loading process. Error: {e}")
        return None, None


def analyze_task_data(df):
    """
    Analyzes a DataFrame to count tasks and categorize them by completion status.
    """
    try:
        df.dropna(how='all', inplace=True)
        if df.empty:
            return 0, {}, None

        task_description_cols = ['Project/Task Name', 'KPI ID', 'Issue']
        primary_task_col = next((col for col in task_description_cols if col in df.columns), None)
        
        total_tasks = len(df) if not primary_task_col else df[primary_task_col].notna().sum()

        possible_status_cols = ['% Achievement', '% Achievement ', 'Achievement', 'Status']
        achievement_col = next((col for col in possible_status_cols if col in df.columns), None)

        statuses = {
            'Completed': 0,
            'Almost Complete': 0,
            'Half Done': 0,
            'Work in Progress': 0
        }

        if achievement_col:
            for status in df[achievement_col]:
                status_str = str(status).lower().strip()
                
                if status_str == 'complete':
                    statuses['Completed'] += 1
                    continue
                
                try:
                    numeric_val = float(re.findall(r"[-+]?\d*\.\d+|\d+", status_str)[0])
                    if numeric_val > 90:
                        statuses['Almost Complete'] += 1
                    elif numeric_val > 50:
                        statuses['Half Done'] += 1
                    else:
                        statuses['Work in Progress'] += 1
                except (ValueError, IndexError):
                    if status_str not in ['nan', '']:
                         statuses['Work in Progress'] += 1

        return total_tasks, statuses, df

    except Exception as e:
        st.warning(f"Could not process a DataFrame. Error: {e}")
        return 0, {}, None

def show_home_page(department_data):
    """
    Displays the main dashboard with a stacked bar chart for task statuses.
    """
    st.header("📈 Overall Task Analysis")
    st.markdown("This dashboard provides a summary of task completion across all departments.")

    results_df = pd.DataFrame.from_dict(department_data, orient='index')
    results_df = results_df.sort_values(by='Total Tasks', ascending=False)
    
    status_colors = {
        'Completed': '#2ca02c', 'Almost Complete': '#98df8a',
        'Half Done': '#ff7f0e', 'Work in Progress': '#d62728'
    }

    fig = go.Figure()
    for status in status_colors.keys():
        if status in results_df.columns:
            fig.add_trace(go.Bar(x=results_df.index, y=results_df[status], name=status,
                                marker_color=status_colors[status], text=results_df[status],
                                textposition='auto'))

    fig.update_layout(barmode='stack', title='<b>Task Completion Status by Department</b>',
                      xaxis_title='Department', yaxis_title='Number of Tasks',
                      legend_title='Status', font=dict(family="Arial, sans-serif", size=12),
                      plot_bgcolor='rgba(0,0,0,0)', yaxis=dict(gridcolor='lightgrey'),
                      xaxis={'categoryorder':'total descending'})
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Summary Data")
    st.dataframe(results_df, use_container_width=True)

def show_department_page(department_name, department_info, df):
    """
    Displays a detailed view for a single selected department with new metrics.
    """
    st.header(f"🔍 Analysis for: {department_name}")

    col1, col2, col3, col4, col5 = st.columns(5)
    col1.metric("Total Tasks", department_info.get('Total Tasks', 0))
    col2.metric("Completed", department_info.get('Completed', 0))
    col3.metric("Almost Complete (>90%)", department_info.get('Almost Complete', 0))
    col4.metric("Half Done (>50%)", department_info.get('Half Done', 0))
    col5.metric("Work in Progress (<=50%)", department_info.get('Work in Progress', 0))

    st.subheader("Task Details")
    st.dataframe(df, use_container_width=True)

def main():
    """
    Main function to run the Streamlit application.
    """
    st.set_page_config(page_title="Department Task Analysis", layout="wide")
    st.title("📊 Department Weekly Task Analysis from Google Sheets")

    sheet_url = "https://docs.google.com/spreadsheets/d/11ziSlsf3oDqffciCPvkreKg4Wz2VuY_sc4g-yTGnmMY/edit?usp=sharing"
    
    department_data, department_dfs = load_and_process_data(sheet_url)

    if department_data and department_dfs:
        st.sidebar.title("Navigation")
        page_options = ["Home"] + sorted(list(department_data.keys()))
        selected_page = st.sidebar.radio("Go to", page_options)

        if selected_page == "Home":
            show_home_page(department_data)
        elif selected_page in department_data:
            show_department_page(selected_page, department_data[selected_page], department_dfs[selected_page])
    else:
        st.warning("No valid data could be extracted from the Google Sheet. Please check the error messages above for details.")

if __name__ == "__main__":
    main()
