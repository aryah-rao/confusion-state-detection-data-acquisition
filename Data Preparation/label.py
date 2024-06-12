import json
from collections import OrderedDict

def read_metadata(metadata_path):
    """
    Reads the metadata.json file and returns the parsed JSON data.
    
    Args:
        metadata_path (str): The file path to the metadata.json file.
        
    Returns:
        dict: The parsed JSON data from the metadata.json file.
    """
    with open(metadata_path, 'r') as file:
        metadata = json.load(file)
    return metadata

def read_body_tracking(body_tracking_path):
    """
    Reads the body_tracking.json file and returns the parsed JSON data.
    
    Args:
        body_tracking_path (str): The file path to the body_tracking.json file.
        
    Returns:
        dict: The parsed JSON data from the body_tracking.json file.
    """
    with open(body_tracking_path, 'r') as file:
        body_tracking = json.load(file)
    return body_tracking

def extract_intervals(frames):
    """
    Extracts start and end frame intervals from the frames list and creates a set of intervals.
    
    Args:
        frames (list): The list of frame numbers.
        
    Returns:
        set: A set of frame numbers within the specified intervals.
    """
    intervals = set()
    for i in range(0, len(frames), 2):
        start, end = frames[i], frames[i+1]
        intervals.update(range(start, end + 1))
    return intervals

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
            # Insert 'confused' at the start
            frame_data[inner_key] = OrderedDict([('confused', confused_value)] + list(inner_data.items()))
    return body_tracking

def save_body_tracking(body_tracking, output_path):
    """
    Saves the modified body_tracking data to a JSON file.
    
    Args:
        body_tracking (dict): The modified body tracking data.
        output_path (str): The file path to save the modified body_tracking.json file.
    """
    with open (output_path, 'w') as file:
        json.dump(body_tracking, file, indent=4)

def main(metadata_path, body_tracking_path, output_path):
    """
    Main function to execute the workflow of reading metadata, processing body tracking data,
    labeling frames as 'confused', and saving the modified data.
    
    Args:
        metadata_path (str): The file path to the metadata.json file.
        body_tracking_path (str): The file path to the body_tracking.json file.
        output_path (str): The file path to save the modified body_tracking.json file.
    """
    metadata = read_metadata(metadata_path)
    body_tracking = read_body_tracking(body_tracking_path)
    intervals = extract_intervals(metadata['frames'])
    updated_body_tracking = label_confused(body_tracking, intervals)
    save_body_tracking(updated_body_tracking, output_path)

if __name__ == "__main__":
    main('path_to_metadata.json', 'path_to_extracted/body_tracking.json', 'path_to_extracted/body_tracking.json')
