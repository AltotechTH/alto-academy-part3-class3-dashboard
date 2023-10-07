import pandas as pd
import pendulum
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from config import DATAPOINT
from utils.dashboard_utils import *

timezone = "Asia/Bangkok"
tz = pendulum.timezone('Asia/Bangkok')


def bgLevels(fig, df, mode, fillcolor):
    _df = df.reset_index()
    y0 = 0
    y1 = 1

    if mode == 'presence':
        m = _df['value'] == '"occupied"'
        y0 = 0.5
        y1 = 1

    if mode == 'occupied':
        m = _df['value'].astype('float') >= 0.5
        y0 = 0
        y1 = 1

    if mode == 'vacant':
        m = _df['value'].astype('float') < 0.5
        y0 = 0
        y1 = 1

    df1 = _df[m].groupby((~m).cumsum())['datetime'].agg(['first', 'last'])
    del m
    for index, row in df1.iterrows():
        if row['first'] == row['last']:
            continue
        fig.add_shape(
            type="rect",
            xref="x",
            yref="paper",
            x0=row['first'],
            y0=y0,
            x1=row['last'],
            y1=y1,
            line=dict(color="rgba(0,0,0,0)", width=3, ),
            fillcolor=fillcolor,
            layer='below')
    return fig


def plot_co2_lifebeing_occupancy(df, df_oc, date, lag=None):
    fig = make_subplots(specs=[[{"secondary_y": True}]])

    # Get today and tomorrow at 12:00 in the given timezone
    today_12pm = date_to_pendulum(date).add(hours=12)
    tomorrow_12pm = today_12pm.add(days=1)

    # Convert pendulum DateTime to pandas datetime format
    today_12pm = pd.to_datetime(today_12pm.to_datetime_string())
    tomorrow_12pm = pd.to_datetime(tomorrow_12pm.to_datetime_string())

    # Filter DataFrame
    df = df[(df.index >= today_12pm) & (df.index < tomorrow_12pm)]
    df_oc = df_oc[(df_oc.index >= today_12pm) & (df_oc.index < tomorrow_12pm)]

    co2 = df[df['datapoint'] == 'co2'].sort_index()

    fig.add_trace(
        go.Scatter(x=co2.index, y=co2['value'], name='CO2', line=dict(color='green', width=4))
    )

    fig.update_yaxes(title_text=f"<b>CO₂ ppm<b>")
    fig.update_yaxes(title_text=f"<b>Life Being Status<b>", secondary_y=True)

    co2['value'] = co2['value'].astype(float)
    lb = df[df['datapoint'] == "presence_state"].sort_index()
    lb['numeric_value'] = lb['value'].apply(lambda x: 1 if x == '"occupied"' else 0)

    fig.add_trace(
        go.Scatter(
            x=lb.index,
            y=lb['numeric_value'],  # Use numerical values for plotting
            mode='lines',
            name='Lifebeing Status',
            line=dict(color='red', width=1)
        ),
        secondary_y=True,
    )
    fig.update_yaxes(
        tickvals=[0, 1],
        ticktext=['Not Detected', 'Detected'],
        secondary_y=True
    )

    # Add horizontal lines at y=642 and y=1000
    fig.add_shape(type="line",
                  x0=co2.index[0], y0=642,
                  x1=co2.index[-1], y1=642,
                  line=dict(color="grey", width=1.5, dash="dash"))

    fig.add_shape(type="line",
                  x0=co2.index[0], y0=1000,
                  x1=co2.index[-1], y1=1000,
                  line=dict(color="grey", width=1.5, dash="dash"))

    fig.update_layout(
        height=500,
        width=1500,
        colorway=px.colors.qualitative.D3,
        title_text=f"Occupancy Status and CO2 Levels on {date}"
    )

    fig.update_xaxes(showgrid=False)
    fig.update_yaxes(showgrid=False)
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10),
                      # plot_bgcolor="#F7F7F8",  # As per your background color preference
                      # paper_bgcolor="#F7F7F8"  # As per your background color preference
                      )

    oc = df_oc[df_oc['datapoint'] == "occupancy"].sort_index()
    fig = bgLevels(fig, oc, mode='occupied', fillcolor='rgba(54,174,124,0.4)')
    fig = bgLevels(fig, oc, mode='vacant', fillcolor='rgba(235,83,83,0.4)')

    # # Adding light gray background for the remaining area
    # fig.add_shape(
    #     type="rect",
    #     xref="x",
    #     yref="paper",
    #     x0=df_oc.index[0],
    #     y0=0,
    #     x1=df_oc.index[-1],
    #     y1=1,
    #     line=dict(color="rgba(0,0,0,0)", width=3),
    #     fillcolor='rgba(192,192,192,0.2)',
    #     layer='below'
    # )

    return fig


def plot_short_line_chart(df, datapoint, minutes=None):
    def _limit_ticks(n, _tickvals, _ticktexts):
        if len(_tickvals) > n:
            step = len(_tickvals) // n
            _tickvals = _tickvals[::step]
            _ticktexts = _ticktexts[::step]
        return _tickvals, _ticktexts

    if minutes:
        end_time = df.index.max()
        start_time = end_time - pd.Timedelta(minutes=minutes)
        df = df[(df['datapoint'] == datapoint) & (df.index >= start_time) & (df.index <= end_time)].sort_index()
    else:
        df = df[df['datapoint'] == datapoint].sort_index()

    # Mapping value similar to the logic used below
    value_map = {
        "presence_state": {
            '"unoccupied"': "Not Detected",
            '"occupied"': "Detected"
        }
    }

    # Mapping values based on the datapoint
    if datapoint in value_map:
        df['value'] = df['value'].map(value_map[datapoint]).fillna(df['value'])

    if datapoint == 'occupancy':
        df['value'] = df['value'].apply(lambda x: 'Occupied' if float(x) > 0.5 else 'Vacant')

    if datapoint == 'delay_started_at':
        df['value'] = df['value'].apply(lambda x: 'Online' if x == '"None"' else 'Measuring CO2..')

    # If the 'value' column contains non-numeric data, map them to numbers
    mapping = {}
    try:
        # Try converting the entire column to float
        df['value'] = df['value'].astype(float)
    except ValueError:
        unique_values = df['value'].unique()
        value_mapping = {value: index for index, value in enumerate(unique_values)}
        mapping = {index: value for value, index in value_mapping.items()}
        df['value'] = df['value'].map(value_mapping)

    # Create a scatter plot with line connecting the points
    fig = go.Figure(data=go.Scatter(x=df.index, y=df['value'], mode='lines', line=dict(color='black', width=2)))

    # Update y-axis tickvals and ticktext to show original string values
    if mapping:
        tickvals, ticktexts = _limit_ticks(5, list(mapping.keys()),
                                              list(mapping.values()))  # Limit the number of ticks to 5
        fig.update_yaxes(tickvals=tickvals, ticktext=ticktexts)

    # Size small
    fig.update_layout(
        height=150,
        width=300,
        colorway=px.colors.qualitative.D3,
    )
    min_value = df['value'].min()
    max_value = df['value'].max()
    padding = (max_value - min_value) * 0.1  # Adjust the multiplier as needed
    min_value -= padding
    max_value += padding
    fig.update_yaxes(range=[min_value, max_value], showgrid=True)
    fig.update_xaxes(showgrid=True, tickformat="%H:%M:%S")
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))

    return fig


def plot_long_line_chart(df, datapoint):
    def _limit_ticks(n, _tickvals, _ticktexts):
        if len(_tickvals) > n:
            step = len(_tickvals) // n
            _tickvals = _tickvals[::step]
            _ticktexts = _ticktexts[::step]
        return _tickvals, _ticktexts

    df = df.sort_index()

    # Mapping value similar to the logic used below
    value_map = {
        "presence_state": {
            '"unoccupied"': "Not Detected",
            '"occupied"': "Detected"
        }
    }

    # Mapping values based on the datapoint
    if datapoint in value_map:
        df['value'] = df['value'].map(value_map[datapoint]).fillna(df['value'])

    if datapoint == 'occupancy':
        df['value'] = df['value'].apply(lambda x: 'Occupied' if float(x) > 0.5 else 'Vacant')

    if datapoint == 'delay_started_at':
        df['value'] = df['value'].apply(lambda x: 'Online' if x == '"None"' else 'Measuring CO2..')

    # If the 'value' column contains non-numeric data, map them to numbers
    mapping = {}
    try:
        # Try converting the entire column to float
        df['value'] = df['value'].astype(float)
    except ValueError:
        unique_values = df['value'].unique()
        value_mapping = {value: index for index, value in enumerate(unique_values)}
        mapping = {index: value for value, index in value_mapping.items()}
        df['value'] = df['value'].map(value_mapping)

    # Create a scatter plot with line connecting the points
    fig = go.Figure(data=go.Scatter(x=df.index, y=df['value'], mode='lines', line=dict(color='black', width=2)))

    # Update y-axis tickvals and ticktext to show original string values
    if mapping:
        tickvals, ticktexts = _limit_ticks(5, list(mapping.keys()),
                                              list(mapping.values()))  # Limit the number of ticks to 5
        fig.update_yaxes(tickvals=tickvals, ticktext=ticktexts)

    # Size small
    fig.update_layout(
        height=150,
        width=300,
        colorway=px.colors.qualitative.D3,
    )
    min_value = df['value'].min()
    max_value = df['value'].max()
    padding = (max_value - min_value) * 0.1  # Adjust the multiplier as needed
    min_value -= padding
    max_value += padding
    fig.update_yaxes(range=[min_value, max_value], showgrid=True)
    fig.update_xaxes(showgrid=True, tickformat="%H:%M:%S")
    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0))

    return fig


def plot_reason_distribution(df):

    data = df[df['datapoint'] == 'reason']
    data.rename(columns={'value': 'reason'}, inplace=True)

    # Calculate the distribution of reasons for final occupancy status
    reason_distribution = data['reason'].value_counts()

    # Calculate the percentages for Occupied and Unoccupied statuses
    total_count = len(data)
    occupied_count = len(data[data['reason'] == 'occupied'])
    unoccupied_count = len(data[data['reason'] == 'unoccupied'])

    occupied_percentage = (occupied_count / total_count) * 100
    unoccupied_percentage = (unoccupied_count / total_count) * 100

    # Corrected labels and values for the pie chart
    corrected_labels = reason_distribution.index.tolist()
    values = reason_distribution.values.tolist()

    # Create the corrected pie chart using Plotly with the corrected labels
    fig = go.Figure(data=[go.Pie(labels=corrected_labels, values=values, textinfo='label+percent', insidetextorientation='radial')])

    # Add title including the Occupied and Unoccupied percentages
    fig.update_layout(
        title=f'Distribution of Reasons for Final Occupancy Status<br>Occupied: {occupied_percentage:.2f}% | Unoccupied: {unoccupied_percentage:.2f}%',
        font=dict(family="Arial", size=14, color="gray"),
    )
    # Show the pie chart
    return fig