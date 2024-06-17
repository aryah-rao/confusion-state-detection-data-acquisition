import json
import os
import argparse
import pandas as pd
from collections import OrderedDict

def get_average_frame_rate_from_metadata(metadata_path):
    """
    Reads the metadata file and retrieves the average frame rate.

    Parameters:
    - metadata_path (str): The path to the metadata file.

    Returns:
    - average_frame_rate (float): The average frame rate.
    - metadata (dict): The entire metadata.
    """
    with open(metadata_path, "r") as json_file:
        metadata = json.load(json_file)
        average_frame_rate = metadata.get("average_frame_rate")
        if average_frame_rate is None:
            return None, None
        
        return average_frame_rate, metadata

def seconds_to_frames(seconds_list, average_frame_rate):
    """
    Converts a list of seconds to a list of frame numbers using the average frame rate.

    Parameters:
    - seconds_list (list): A list of seconds to convert to frames.
    - average_frame_rate (float): The average frame rate used for the conversion.

    Returns:
    - frames_list (list): A list of frames corresponding to the given seconds.
    """
    frames_list = []
    
    for second in seconds_list:
        frame = int(second * average_frame_rate)
        frames_list.append(frame)
    
    return frames_list

def update_metadata(metadata_path, metadata):
    """
    Updates the metadata file with new information.

    Parameters:
    - metadata_path (str): The path to the metadata file.
    - metadata (dict): The updated metadata to be saved.
    """
    with open(metadata_path, 'w') as json_file:
        json.dump(metadata, json_file, indent=4)

def read_metadata(metadata_path):
    """
    Reads the metadata.json file and returns the parsed JSON data.
    
    Parameters:
    - metadata_path (str): The file path to the metadata.json file.
        
    Returns:
    - dict: The parsed JSON data from the metadata.json file.
    """
    with open(metadata_path, 'r') as file:
        metadata = json.load(file)
    return metadata

def read_body_tracking(body_tracking_path):
    """
    Reads the body_tracking.json file and returns the parsed JSON data.
    
    Parameters:
    - body_tracking_path (str): The file path to the body_tracking.json file.
        
    Returns:
    - dict: The parsed JSON data from the body_tracking.json file.
    """
    with open(body_tracking_path, 'r') as file:
        body_tracking_data = json.load(file)
    return body_tracking_data

def extract_intervals_from_metadata(metadata, average_frame_rate):
    """
    Extracts intervals from metadata and converts them to frames.

    Parameters:
    - metadata (dict): The metadata containing intervals in seconds.
    - average_frame_rate (float): The average frame rate used for conversion.

    Returns:
    - intervals (set): A set of frame numbers within the specified intervals.
    """
    intervals_in_seconds = metadata.get("intervals", [])
    frames_list = seconds_to_frames(intervals_in_seconds, average_frame_rate)
    intervals = set()
    for i in range(0, len(frames_list), 2):
        start, end = frames_list[i], frames_list[i+1]
        intervals.update(range(start, end + 1))
    return intervals

def label_confused(body_tracking_data, intervals):
    """
    Labels each frame in the body_tracking data as 'confused' (True) or not confused (False).
    
    Parameters:
    - body_tracking_data (dict): The body tracking data.
    - intervals (set): A set of frame numbers within the specified intervals.
        
    Returns:
    - dict: The updated body tracking data with 'confused' labels.
    """
    for frame_number_str, frame_data in body_tracking_data.items():
        frame_number = int(frame_number_str)
        confused_value = frame_number in intervals
        for inner_key in frame_data.keys():
            inner_data = frame_data[inner_key]
            frame_data[inner_key] = OrderedDict([('confused', confused_value)] + list(inner_data.items()))
    return body_tracking_data

def save_body_tracking(body_tracking_data, output_path):
    """
    Saves the modified body_tracking data to a JSON file.
    
    Parameters:
    - body_tracking_data (dict): The modified body tracking data.
    - output_path (str): The file path to save the modified body_tracking.json file.
    """
    with open(output_path, 'w') as file:
        json.dump(body_tracking_data, file, indent=4)

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
    for frame, frame_data in json_data.items():
        for inner_key, inner_data in frame_data.items():
            if isinstance(inner_data, dict):
                record = {'frame_number': frame, 'inner_key': inner_key}
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


def save_to_csv(dataframe, output_path):
    """
    Saves the flattened DataFrame to a CSV file.

    Parameters:
    - dataframe (pd.DataFrame): The DataFrame to save.
    - output_path (str): The path to save the CSV file.
    """
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    dataframe.to_csv(output_path, index=False)

def main(folder_path):
    """
    Main function to update metadata, label body tracking data, flatten the JSON, and save as CSV.

    Parameters:
    - folder_path (str): The directory path containing the JSON files.
    """
    body_tracking_path = os.path.join(folder_path, 'body_tracking.json')
    metadata_path = os.path.join(folder_path, 'metadata.json')

    # Get average frame rate from metadata
    average_frame_rate, metadata = get_average_frame_rate_from_metadata(metadata_path)
    if average_frame_rate is None:
        print("Average frame rate not found in metadata.")
        return

    # Extract intervals from metadata
    intervals = extract_intervals_from_metadata(metadata, average_frame_rate)

    # Read body tracking data
    body_tracking_data = read_body_tracking(body_tracking_path)

    # Label the body tracking data with 'confused' based on the intervals
    labeled_body_tracking_data = label_confused(body_tracking_data, intervals)

    # Save the updated body tracking data back to the JSON file
    save_body_tracking(labeled_body_tracking_data, body_tracking_path)

    # Flatten the body tracking JSON data to a DataFrame
    flattened_df = flatten_json(body_tracking_data)

    # Define the output CSV path and save the DataFrame to CSV
    folder_name = os.path.basename(folder_path)
    csv_output_path = os.path.join('../../../../intermediate-data/zed-body-tracking', folder_name+'.csv')
    
    save_to_csv(flattened_df, csv_output_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process body_tracking.json with metadata and export to CSV.')
    parser.add_argument('--folder_path', type=str, required=True, help='Directory containing the body_tracking.json and metadata.json files')
    args = parser.parse_args()
    
    main(args.folder_path)
