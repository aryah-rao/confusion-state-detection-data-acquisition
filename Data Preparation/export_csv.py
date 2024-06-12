import json
import pandas as pd
from  pandas import json_normalize


def read_json(file_path):
    """
    Reads a JSON file and returns the parsed JSON data.
    
    Args:
        file_path (str): The path to the JSON file.
        
    Returns:
        dict: The parsed JSON data.
    """
    with open(file_path, 'r') as file:
        data = json.load(file)
    return data

def flatten_json(json_data):
    """
    Flattens the nested JSON structure into a tabular format using json_normalize.
    
    Args:
        json_data (dict): The nested JSON data.
        
    Returns:
        pd.DataFrame: The flattened data in a pandas DataFrame.
    """
    # Convert the outermost dictionary to a list of records
    records = []
    for frame_number_str, frame_data in json_data.items():
        frame_number = int(frame_number_str)
        for inner_key, inner_data in frame_data.items():
            record = {
                'frame_number': frame_number,
                'inner_key': inner_key,
                'id': inner_data.get('id'),
                'confused': inner_data.get('confused'),
                'ts': inner_data.get('ts'),
                'confidence': inner_data.get('confidence')
            }
            if 'velocity' in inner_data:
                record['velocity_x'] = inner_data['velocity'][0]
                record['velocity_y'] = inner_data['velocity'][1]
                record['velocity_z'] = inner_data['velocity'][2]
            keypoints = inner_data.get('keypoint', [])
            for i, keypoint in enumerate(keypoints):
                record[f'keypoint_{i}_x'] = keypoint[0]
                record[f'keypoint_{i}_y'] = keypoint[1]
                record[f'keypoint_{i}_z'] = keypoint[2]
            keypoint_confidences = inner_data.get('keypoint_confidence', [])
            for i, kp_conf in enumerate(keypoint_confidences):
                record[f'keypoint_confidence_{i}'] = kp_conf
            records.append(record)
    
    return pd.DataFrame(records)

def save_to_csv(df, output_path):
    """
    Saves the flattened DataFrame to a CSV file.
    
    Args:
        df (pd.DataFrame): The DataFrame to save.
        output_path (str): The path to save the CSV file.
    """
    df.to_csv(output_path, index=False)

def main(json_path, csv_path):
    """
    Main function to read the JSON file, flatten it, and save it as a CSV.
    
    Args:
        json_path (str): The path to the JSON file.
        csv_path (str): The path to save the CSV file.
    """
    json_data = read_json(json_path)
    flattened_df = flatten_json(json_data)
    save_to_csv(flattened_df, csv_path)

if __name__ == "__main__":
    json_path = 'path_to_extracted/body_tracking.json'
    csv_path = 'output_path/body_tracking.csv'
    main(json_path, csv_path)
