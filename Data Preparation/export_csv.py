import json
import pandas as pd
import argparse
import os

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
    Flattens the nested JSON structure into a tabular format.
    
    Args:
        json_data (dict): The nested JSON data.
        
    Returns:
        pd.DataFrame: The flattened data in a pandas DataFrame.
    """
    records = []
    
    for frame_number_str, frame_data in json_data.items():
        frame_number = int(frame_number_str)
        for inner_key, inner_data in frame_data.items():
            record = {'frame_number': frame_number, 'inner_key': inner_key}
            
            # Flatten inner_data dictionary
            for key, value in inner_data.items():
                if isinstance(value, list):
                    if all(isinstance(i, list) for i in value):  # Check if it's a list of lists
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
    
    Args:
        df (pd.DataFrame): The DataFrame to save.
        output_path (str): The path to save the CSV file.
    """
    df.to_csv(output_path, index=False)

def main(input_dir):
    """
    Main function to read the JSON file, flatten it, and save it as a CSV.
    
    Args:
        input_dir (str): The directory path containing the JSON file.
    """
    json_path = os.path.join(input_dir, 'body_tracking.json')
    csv_path = os.path.join(input_dir, 'labelled.csv')
    
    json_data = read_json(json_path)
    flattened_df = flatten_json(json_data)
    save_to_csv(flattened_df, csv_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Convert body_tracking.json to a CSV file.')
    parser.add_argument('input_dir', type=str, help='Directory containing the body_tracking.json file')
    args = parser.parse_args()
    
    main(args.input_dir)
    

