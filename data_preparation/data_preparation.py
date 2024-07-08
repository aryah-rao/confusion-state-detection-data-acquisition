import json
import os
import argparse
import pandas as pd
from collections import OrderedDict

def calculate_end_times_with_updated_csv(df):
    """
    Calculates the end times based on start timestamp and duration.
    
    Parameters:
    - df (DataFrame): The DataFrame containing start times and durations.
    
    Returns:
    - list: A list of tuples with start and end times in seconds.
    """
    times = []
    rh_intervals = []
    for _, row in df.iterrows():
        start_time = pd.to_timedelta(row['Timestamp']).total_seconds()
        duration = pd.to_timedelta(row['Duration']).total_seconds()
        end_time = start_time + duration
        times.append((start_time, end_time))
        if row['Tags'] == 'RH':
            rh_intervals.append((start_time, end_time))
    
    return times, rh_intervals

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


def seconds_to_frames(confused, seconds average_frame_rate):
    """
    Converts a list of seconds to a list of frame numbers using the average frame rate.
    
    Parameters:
    - seconds_list (list): A list of seconds to convert to frames.
    - average_frame_rate (float): The average frame rate used for the conversion.
    
    Returns:
    - list: A list of frame numbers corresponding to the given seconds.
    """
    return [int(confused * average_frame_rate for second in confused)]

def update_metadata_with_csv(metadata_path, csv_path):
    """
    Updates metadata.json with start and end times from the CSV file and converts them to frames.
    
    Parameters:
    - metadata_path (str): The path to the metadata.json file.
    - csv_path (str): The path to the CSV file with highlights.
    """
    # Load the metadata file
    with open(metadata_path, 'r') as f:
        metadata = json.load(f)
    
    # Load the CSV file and calculate the start and end times
    df = pd.read_csv(csv_path)
    confused_times, rh_times = calculate_end_times_with_updated_csv(df)

    # Add start and end times to the seconds list in metadata
    if "confused" not in metadata:
        metadata["confused"] = []
    for start_time, end_time in confused_times:
        metadata["confused"].append(start_time)
        metadata["confused"].append(end_time)
    
        # Add start and end times to the seconds list in metadata
    if "rh" not in metadata:
        metadata["rh"] = []
    for start_time, end_time in rh_times:
        metadata["rh"].append(start_time)
        metadata["rh"].append(end_time)

    # Convert the updated times to frames
    average_frame_rate = metadata.get("average_frame_rate", 30.0)  # Default to 30.0 if not found
    confused_frames_list = seconds_to_frames(metadata["confused"], average_frame_rate)
    rh_frames_list = seconds_to_frames(metadata["rh"], average_frame_rate)
    
    # Save the frames list to metadata
    metadata["confused_frames"] = confused_frames_list
    metadata["rh_frames"] = rh_frames_list
    
    # Save the updated metadata back to the JSON file
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=4)

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
    intervals_in_seconds = metadata.get("seconds", [])
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
            frame_data[inner_key]["confused"] = confused_value
    return body_tracking_data

def label_help(body_tracking_data, rh_intervals, average_frame_rate):
    """
    Labels each frame in the body_tracking data as 'help' (1) if it falls within RH intervals, else 0.
    
    Parameters:
    - body_tracking_data (dict): The body tracking data.
    - rh_intervals (list): A list of tuples with start and end times for RH intervals.
    - average_frame_rate (float): The average frame rate used for conversion.
    
    Returns:
    - dict: The updated body tracking data with 'help' labels.
    """
    rh_intervals_in_frames = []
    for start, end in rh_intervals:
        start_frame = int(start * average_frame_rate)
        end_frame = int(end * average_frame_rate)
        rh_intervals_in_frames.append((start_frame, end_frame))

    for frame_number_str, frame_data in body_tracking_data.items():
        frame_number = int(frame_number_str)
        help_value = 0
        for start_frame, end_frame in rh_intervals_in_frames:
            if start_frame <= frame_number <= end_frame:
                help_value = 1
                break
        for inner_key in frame_data.keys():
            frame_data[inner_key]["help"] = help_value
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
    
def check_outermost_keys(json_data):
    """
    Checks if the outermost keys' values are dictionaries with exactly one key.
    
    Parameters:
    - data (dict): The JSON data to check.
    
    Returns:
    - bool: True if all outermost keys' values are dictionaries with exactly one key, otherwise False.
    """
    for key, value in json_data.items():
        if isinstance(value, dict) and len(value) != 1:
            print(f'The frame {key} has more than one bodies')
            return False
    return True

def flatten_json(json_data):
    """
    Flattens the nested JSON structure into a flat dictionary.

    Parameters:
    - json_data (dict): The JSON data to flatten.

    Returns:
    - pd.DataFrame: The flattened JSON data as a pandas DataFrame.
    """
    records = []
    frames_with_errors = []
    for frame, frame_data in json_data.items():
        if len(frame_data) > 1:
            too_many_bodies = 1
            frames_with_errors.append(frame)
        else:
            too_many_bodies = 0
        for inner_key, inner_data in frame_data.items():
            if isinstance(inner_data, dict):
                record = {'frame_number': frame, 
                          'inner_key': inner_key, 
                          'body_tracking_error':too_many_bodies
                          }
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
    return pd.DataFrame(records), frames_with_errors


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
    csv_path = os.path.join(folder_path, 'reduct-highlights-export.csv' )
    
    body_tracking_data = read_body_tracking(body_tracking_path)
    # if not check_outermost_keys(body_tracking_data):
    #     print("Validation failed: An outermost key does not contain a dictionary with exactly one key.")
    #     return
    
    # Update metadata with CSV
    update_metadata_with_csv(metadata_path, csv_path)

    # Get average frame rate from metadata
    average_frame_rate, metadata = get_average_frame_rate_from_metadata(metadata_path)
    if average_frame_rate is None:
        print("Average frame rate not found in metadata.")
        return

    # Extract intervals from metadata
    intervals = extract_intervals_from_metadata(metadata, average_frame_rate)

    
    # Label the body tracking data with 'confused' based on the intervals
    labeled_body_tracking_data = label_confused(body_tracking_data, intervals)

    # Load the CSV file to calculate RH intervals
    df = pd.read_csv(csv_path)
    _, rh_intervals = calculate_end_times_with_updated_csv(df)

    # Label the body tracking data with 'help'
    labeled_body_tracking_data = label_help(labeled_body_tracking_data, rh_intervals, average_frame_rate)


    # Save the updated body tracking data back to the JSON file
    save_body_tracking(labeled_body_tracking_data, body_tracking_path)

    # Flatten the body tracking JSON data to a DataFrame
    flattened_df, frames_with_errors = flatten_json(body_tracking_data)
    metadata["body_tracking_errors"] = frames_with_errors
    update_metadata(metadata_path, metadata)
    
    # Define the output CSV path and save the DataFrame to CSV
    folder_name = os.path.basename(folder_path)
    csv_output_path = os.path.join('../../intermediate-data/zed-body-tracking', folder_name+'.csv')
    
    save_to_csv(flattened_df, csv_output_path)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process body_tracking.json with metadata and export to CSV.')
    parser.add_argument('--folder_path', type=str, required=True, help='Directory containing the body_tracking.json and metadata.json files')
    args = parser.parse_args()
    
    main(args.folder_path)