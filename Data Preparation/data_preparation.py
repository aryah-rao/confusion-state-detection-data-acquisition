import json
import os
import argparse
import pandas as pd

def get_average_frame_rate_from_metadata(metadata_file):
    """
    Reads the metadata file and retrieves the average frame rate.

    Parameters:
    - metadata_file (str): The path to the metadata file.

    Returns:
    - average_frame_rate (float): The average frame rate.
    - metadata (dict): The entire metadata.
    """
    with open(metadata_file, "r") as json_file:
        metadata = json.load(json_file)
        average_frame_rate = metadata.get("average_frame_rate")
        return average_frame_rate, metadata

def seconds_to_frames(seconds, average_frame_rate):
    """
    Converts a list of seconds to a list of frame numbers using the average frame rate.

    Parameters:
    - seconds (list): A list of seconds to convert to frames.
    - average_frame_rate (float): The average frame rate used for the conversion.

    Returns:
    - frames (list): A list of frames corresponding to the given seconds.
    """
    return [int(sec * average_frame_rate) for sec in seconds]

def update_metadata(metadata_file, body_tracking_file):
    """
    Updates the metadata file with the average frame rate and saves it.

    Parameters:
    - metadata_file (str): The path to the metadata file.
    - body_tracking_file (str): The path to the body tracking file.

    Returns:
    - average_frame_rate (float): The average frame rate.
    - metadata (dict): The entire metadata.
    """
    average_frame_rate, metadata = get_average_frame_rate_from_metadata(metadata_file)
    if average_frame_rate is None:
        return None, None

    metadata_path = os.path.join(os.path.dirname(body_tracking_file), 'metadata.json')
    with open(metadata_path, 'w') as json_file:
        json.dump(metadata, json_file, indent=4)

    return average_frame_rate, metadata

def label_body_tracking(metadata_file, body_tracking_file):
    """
    Adds "confused" or "not confused" (0 or 1) label to each timeframe in body_tracking.json.

    Parameters:
    - metadata_file (str): The path to the metadata file.
    - body_tracking_file (str): The path to the body tracking file.
    """
    average_frame_rate, _ = get_average_frame_rate_from_metadata(metadata_file)

    with open(body_tracking_file, 'r') as json_file:
        body_data = json.load(json_file)

    for frame in body_data:
        if frame['frame_number'] < average_frame_rate:
            frame['label'] = 1
        else:
            frame['label'] = 0

    with open(body_tracking_file, 'w') as json_file:
        json.dump(body_data, json_file, indent=4)

def read_json(json_path):
    """
    Reads a JSON file and returns its content.

    Parameters:
    - json_path (str): The path to the JSON file.

    Returns:
    - dict: The JSON content as a dictionary.
    """
    with open(json_path, 'r') as file:
        return json.load(file)

def flatten_json(json_data):
    """
    Flattens the nested JSON structure into a flat dictionary.

    Parameters:
    - json_data (dict): The JSON data to flatten.

    Returns:
    - pd.DataFrame: The flattened JSON data as a pandas DataFrame.
    """
    records = []
    for frame in json_data:
        frame_number = frame.get('frame_number')
        for inner_key, inner_data in frame.items():
            if isinstance(inner_data, dict):
                record = {'frame_number': frame_number, 'inner_key': inner_key}
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
                records.append(record)
    return pd.DataFrame(records)

def save_to_csv(df, output_path):
    """
    Saves the flattened DataFrame to a CSV file.

    Parameters:
    - df (pd.DataFrame): The DataFrame to save.
    - output_path (str): The path to save the CSV file.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)

def main(folder_path):
    """
    Main function to update metadata, label body tracking data, flatten the JSON, and save as CSV.

    Parameters:
    - folder_path (str): The directory path containing the JSON files.
    """
    # Define paths for body_tracking.json and metadata.json
    body_tracking_file = os.path.join(folder_path, 'body_tracking.json')
    metadata_file = os.path.join(folder_path, 'metadata.json')

    # Update metadata and get average frame rate
    average_frame_rate, metadata = update_metadata(metadata_file, body_tracking_file)
    if average_frame_rate is None:
        print("Average frame rate not found in metadata.")
        return

    # Label body tracking data
    label_body_tracking(metadata_file, body_tracking_file)

    # Read and flatten body_tracking.json
    json_data = read_json(body_tracking_file)
    flattened_df = flatten_json(json_data)

    # Define output CSV path
    folder_name = os.path.basename(folder_path)
    csv_path = os.path.join('../../../../intermediate-data/zed-body-tracking', folder_name + '.csv')
    
    # Save the flattened DataFrame to CSV
    save_to_csv(flattened_df, csv_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process body_tracking.json with metadata and export to CSV.')
    parser.add_argument('--folder_path', type=str, required=True, help='Directory containing the body_tracking.json and metadata.json files')
    args = parser.parse_args()
    
    main(args.folder_path)
