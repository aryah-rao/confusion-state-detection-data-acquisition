import json
import os
import argparse
from pathlib import Path
import pandas as pd

def read_json(json_path):
    """
    Reads a JSON file and returns its content.

    Parameters:
    - json_path (str): The path to the JSON file.

    Returns:
    - dict: The JSON content as a dictionary.
    """
    try:
        with open(json_path, 'r') as file:
            return json.load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"File not found: {json_path}")
    except json.JSONDecodeError:
        raise ValueError(f"Error decoding JSON from file: {json_path}")

def update_metadata(metadata_path, metadata):
    """
    Updates the metadata file with new information.

    Parameters:
    - metadata_path (str): The path to the metadata file.
    - metadata (dict): The updated metadata to be saved.
    """
    with open(metadata_path, 'w') as json_file:
        json.dump(metadata, json_file, indent=4)

def calculate_end_times(df):
    """
    Calculates the end times based on start timestamp and duration.

    Parameters:
    - df (DataFrame): The DataFrame containing start times and durations.

    Returns:
    - tuple: Two lists of tuples with start and end times in seconds.
    """
    confused_intervals = []
    rh_intervals = []
    for _, row in df.iterrows():
        start_time = pd.to_timedelta(row['Timestamp']).total_seconds()
        duration = pd.to_timedelta(row['Duration']).total_seconds()
        end_time = start_time + duration
        if row['Tags'] == 'RH':
            rh_intervals.append((start_time, end_time))
        else:
            confused_intervals.append((start_time, end_time))
    
    return confused_intervals, rh_intervals

def read_metadata(metadata_path):
    """
    Reads the metadata.json file and returns the parsed JSON data.

    Parameters:
    - metadata_path (str): The file path to the metadata.json file.

    Returns:
    - dict: The parsed JSON data from the metadata.json file.
    """
    return read_json(metadata_path)

def update_metadata_with_csv(metadata, csv_path):
    """
    Updates metadata with start and end times from the CSV file.

    Parameters:
    - metadata (dict): The metadata dictionary to update.
    - csv_path (str): The path to the CSV file with highlights.

    Returns:
    - dict: The updated metadata dictionary.
    """
    df = pd.read_csv(csv_path)
    confused_times, rh_times = calculate_end_times(df)

    metadata["confused_intervals"] = confused_times
    metadata["rh_intervals"] = rh_times

    average_frame_rate = metadata.get("average_frame_rate", 30.0)
    metadata["confused_frame_intervals"] = [
        (int(start * average_frame_rate), int(end * average_frame_rate))
        for start, end in confused_times
    ]
    metadata["rh_frame_intervals"] = [
        (int(start * average_frame_rate), int(end * average_frame_rate))
        for start, end in rh_times
    ]

    return metadata

def label_frames(body_tracking_data, intervals, label_key, average_frame_rate=30.0):
    """
    Labels each frame in the body_tracking data based on the given intervals.

    Parameters:
    - body_tracking_data (dict): The body tracking data.
    - intervals (list): A list of tuples with start and end times in seconds.
    - label_key (str): The key to use for labeling in the body_tracking_data.
    - average_frame_rate (float): The average frame rate used for the conversion.

    Returns:
    - dict: The updated body tracking data with labels.
    """
    intervals_in_frames = [
        (int(start * average_frame_rate), int(end * average_frame_rate))
        for start, end in intervals
    ]

    for frame_number_str, frame_data in body_tracking_data.items():
        frame_number = int(frame_number_str)
        label_value = any(start_frame <= frame_number <= end_frame for start_frame, end_frame in intervals_in_frames)
        frame_data[label_key] = 1 if label_value else 0

    return body_tracking_data

def flatten_json(json_data):
    """
    Flattens the nested JSON structure into a flat dictionary.

    Parameters:
    - json_data (dict): The JSON data to flatten.

    Returns:
    - tuple: A DataFrame of the flattened JSON data and a list of frames with errors.
    """
    records = []
    frames_with_errors = []
    for frame, frame_data in json_data.items():
        too_many_bodies = len(frame_data) > 3
        if too_many_bodies:
            frames_with_errors.append(frame)

        for inner_key, inner_data in frame_data.items():
            if isinstance(inner_data, dict):
                record = {'frame_number': frame, 'inner_key': inner_key, 'body_tracking_error': too_many_bodies}
                for key, value in inner_data.items():
                    if isinstance(value, list):
                        if all(isinstance(i, list) for i in value):
                            for i, sublist in enumerate(value):
                                for j, subvalue in enumerate(sublist):
                                    record[f'{key}_{i}_{j}'] = subvalue
                        else:
                            for i, subvalue in enumerate(value):
                                record[f'{key}_{i}'] = subvalue
                    else:
                        record[key] = value
                record["confused"] = frame_data.get("confused", False)
                record["help"] = frame_data.get("help", False)
                records.append(record)

    return pd.DataFrame(records), frames_with_errors

def save_to_csv(dataframe, output_path):
    """
    Saves the flattened DataFrame to a CSV file.

    Parameters:
    - dataframe (pd.DataFrame): The DataFrame to save.
    - output_path (str): The path to save the CSV file.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dataframe.to_csv(output_path, index=False)

def main(folder_path):
    """
    Main function to update metadata, label body tracking data, flatten the JSON, and save as CSV.

    Parameters:
    - folder_path (str): The directory path containing the JSON files.
    """
    folder_path = Path(folder_path)
    metadata_path = folder_path / 'metadata.json'
    csv_path = folder_path / 'reduct-highlights-export.csv'

    metadata = read_metadata(metadata_path)

    metadata = update_metadata_with_csv(metadata, csv_path)

    body_tracking_data = read_json(folder_path / 'body_tracking.json')

    for label_key, intervals_key in [("confused", "confused_intervals"), ("help", "rh_intervals")]:
        intervals = metadata.get(intervals_key, [])
        body_tracking_data = label_frames(body_tracking_data, intervals, label_key, metadata.get("average_frame_rate", 30.0))
        print(f"Labeling frames for {label_key}")

    flattened_df, frames_with_errors = flatten_json(body_tracking_data)
    metadata["body_tracking_errors"] = frames_with_errors

    metadata["confused_frame_intervals"] = metadata.get("confused_frame_intervals", [])
    metadata["rh_frame_intervals"] = metadata.get("rh_frame_intervals", [])

    update_metadata(metadata_path, metadata)

    folder_name = folder_path.name
    csv_output_path = Path('../../intermediate-data/zed-body-tracking') / f'{folder_name}.csv'
    save_to_csv(flattened_df, csv_output_path)
    print(f"Saved body tracking data to {csv_output_path}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process body_tracking.json with metadata and export to CSV.')
    parser.add_argument('--folder_path', type=str, required=True, help='Directory containing the metadata.json and reduct-highlights-export.csv files')
    args = parser.parse_args()

    main(args.folder_path)
