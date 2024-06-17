import json
import os
import argparse
import pandas as pd
from collections import OrderedDict

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
        if average_frame_rate is None:
            return None, None
        
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
    frames = []
    
    # Iterate over each second in the seconds list
    for sec in seconds:
        # Calculate the frame number for the current second using the average frame rate
        frame = int(sec * average_frame_rate)
        
        # Append the frame to the frames list
        frames.append(frame)
    
    # Return the list of frames
    return frames

def update_metadata(metadata_file, metadata, body_tracking_file):
    """
    converts to seconds

    Parameters:
    - metadata_file (str): The path to the metadata file.
    - body_tracking_file (str): The path to the body tracking file.

    Returns:
    - average_frame_rate (float): The average frame rate.
    - metadata (dict): The entire metadata.
    """

    metadata_path = os.path.join(os.path.dirname(body_tracking_file), 'metadata.json')
    with open(metadata_path, 'w') as json_file:
        json.dump(metadata, json_file, indent=4)


def extract_intervals(body_tracking_file, frames):
    """
    Adds "confused" or "not confused" (0 or 1) label to each timeframe in body_tracking.json.

    Parameters:
    - metadata_file (str): The path to the metadata file.
    - body_tracking_file (str): The path to the body tracking file.
    """


    with open(body_tracking_file, 'r') as json_file:
        body_data = json.load(json_file)

    intervals = set()
    for i in range(0, len(frames), 2):
        start, end = frames[i], frames[i+1]
        intervals.update(range(start, end + 1))
    return intervals

    with open(body_tracking_file, 'w') as json_file:
        json.dump(body_data, json_file, indent=4)
        
def label_confused(body_tracking, intervals):
    """
    Labels each frame in the body_tracking data as 'confused' (True) or not confused (False).
    
    Args:
        body_tracking (dict): The body tracking data.
        intervals (set): A set of frame numbers within the specified intervals.
        
    Returns:
        dict: The updated body tracking data with 'confused' labels.
    """
    for frame_number_str, frame_data in body_tracking.items():
        frame_number = int(frame_number_str)  # Convert frame number to integer
        confused_value = True if frame_number in intervals else False
        for inner_key in frame_data.keys():
            inner_data = frame_data[inner_key]
            # Insert 'confused' at the start of the OrderedDict
            frame_data[inner_key] = OrderedDict([('confused', confused_value)] + list(inner_data.items()))
    return body_tracking

def save_body_tracking(body_tracking, output_path):
    """
    Saves the modified body_tracking data to a JSON file.
    
    Args:
        body_tracking (dict): The modified body tracking data.
        output_path (str): The file path to save the modified body_tracking.json file.
    """
    with open(output_path, 'w') as file:
        json.dump(body_tracking, file, indent=4)

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
    average_frame_rate = get_average_frame_rate_from_metadata(metadata_file)
    if average_frame_rate is None:
        print("Average frame rate not found in metadata.")
        return

    # Label body tracking data
    label_confused(metadata_file, body_tracking_file)

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
