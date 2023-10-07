import time
import pendulum
import datetime

import pandas as pd
import streamlit as st
from utils import database_utils

timezone = "Asia/Bangkok"


def date_to_pendulum(date):
    return pendulum.datetime(
        date.year,
        date.month,
        date.day,
        tz=timezone
    )


def datetime_to_pendulum(_datetime):
    return pendulum.instance(_datetime, tz=timezone)


def pd_timestamp_to_pendulum(pd_timestamp):
    return pendulum.instance(pd_timestamp.to_pydatetime(), tz=timezone)


def get_latest_data(df, datapoint):

    value_map = {
        "presence_state": {
            '"unoccupied"': "Not Detected",
            '"occupied"': "Detected"
        }
    }

    filtered_df = df[df['datapoint'] == datapoint].sort_index(ascending=True)
    if not filtered_df.empty:
        if len(filtered_df) >= 2:
            latest_values = filtered_df.iloc[-3:-1]['value'].tolist()
        else:
            latest_values = ['N/A', filtered_df.iloc[-1]['value']]

        if datapoint in value_map:
            latest_values = [value_map[datapoint][v] if v in value_map[datapoint] else v for v in latest_values]
        if datapoint == 'occupancy':
            new_latest_values = []
            for v in latest_values:
                if v != 'N/A':
                    if float(v) > 0.5:
                        new_latest_values.append('Occupied')
                    else:
                        new_latest_values.append('Vacant')
                else:
                    new_latest_values.append('N/A')
            latest_values = new_latest_values
        if datapoint == 'delay_started_at':
            new_latest_values = []
            for v in latest_values:
                if v == '"None"':
                    new_latest_values.append('Online')
                else:
                    new_latest_values.append('Measuring CO2..')
            latest_values = new_latest_values
        return latest_values
    else:
        return ['N/A', 'N/A']


def get_data(_sensor_start_unix, _log_start_unix, _end_unix):
    t = time.time()
    filters = {
        'timestamp': {
            '>=': _sensor_start_unix,
            '<': _end_unix
        }
    }
    df = database_utils.query_data_from_database(filters=filters, table_name='raw_data',
                                                 pivot_datapoint_column=False)
    filters = {
        'timestamp': {
            '>=': _log_start_unix,
            '<': _end_unix
        }
    }
    df_oc = database_utils.query_data_from_database(filters=filters, table_name='occupancy_results',
                                                    pivot_datapoint_column=False)
    print(f"Data queried in {time.time() - t} seconds")

    if df.empty:
        df = pd.DataFrame(columns=['timestamp', 'device_id', 'datapoint', 'value'])
    else:
        df['value'] = df['value'].apply(transform_value)

    if df_oc.empty:
        df_oc = pd.DataFrame(columns=['timestamp', 'device_id', 'datapoint', 'value'])
    else:
        df_oc['value'] = df_oc['value'].apply(transform_value)

    df.drop('location', axis=1, inplace=True)

    return df


def update_metrics(df, datapoint_mapping):
    metrics = {}
    latest = df.index.max() if not df.empty else None
    for label, datapoint in datapoint_mapping.items():
        metrics[label] = get_latest_data(df, datapoint)
    latest_timestamp = pd_timestamp_to_pendulum(latest) if latest else pendulum.now()
    return metrics, latest_timestamp


# Transform value if the string can turn into float then do it, if not remain string
def transform_value(value):
    try:
        return float(value)
    except:
        return value


def calculate_delta(metrics, label):
    if metrics[label][-1] != 'N/A' and metrics[label][-2] != 'N/A':
        return float(metrics[label][-1]) - float(metrics[label][-2])
    else:
        return 'N/A'