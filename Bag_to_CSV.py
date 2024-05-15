#import all the required python libraries
import os
import csv
import rosbag
import multiprocessing
import time
import psutil

def find_rosbag_files(raw_data_folder_path):
    """
    Find all rosbag files in a folder and its subfolders
    """
    for root, dirs, files in os.walk(raw_data_folder_path):  # Recursively walk through the folder structure
        for file in files:  # Iterate through files in the current directory
            if file.endswith(".bag"):  # Check if the file has a .bag extension
                yield os.path.join(root, file)  # Yield the full path of the bag file

def extract_topics(rosbag_file):
    """
    Extract topics from a ROS bag file
    """
    try:
        bag = rosbag.Bag(rosbag_file)  # Open the ROS bag file
        for topic, msg, t in bag.read_messages():  # Iterate through messages in the bag file
            yield topic, t.to_sec(), msg  # Yield topic, timestamp, and message
        bag.close()  # Close the bag file
    except rosbag.ROSBagException as e:  # Catch exceptions related to ROS bag processing
        print(f"Error processing {rosbag_file}: {str(e)}")  # Print an error message if an exception occurs


def extract_message_attributes(message, parent_field=None):
    """
    Extract attributes from the message and return as a dictionary
    """
    attributes = {}  # Initialize an empty dictionary to store attributes
    for field in message.__slots__:  # Iterate through slots of the message
        full_field_name = f"{parent_field}.{field}" if parent_field else field  # Construct the full field name
        if hasattr(getattr(message, field), '__slots__'):  # Check if the field is a nested message
            attributes.update(extract_message_attributes(getattr(message, field), parent_field=full_field_name))  # Recursively extract attributes
        else:
            attributes[full_field_name] = getattr(message, field)  # Extract attribute value
    return attributes  # Return the dictionary of attributes

def convert_to_csv(topic_generator, output_folder):
    """
    Convert topics from topic_generator to CSV files
    """
    for topic, timestamp, message in topic_generator:  # Iterate through topics, timestamps, and messages
        try:
            csv_file_path = os.path.join(output_folder, f"{topic.replace('/', '_')}.csv")  # Generate the CSV file path
            with open(csv_file_path, 'a', newline='') as csv_file:  # Open the CSV file in append mode
                writer = csv.DictWriter(csv_file, fieldnames=['Timestamp'] + list(extract_message_attributes(message).keys()))  # Create a CSV writer with headers
                if csv_file.tell() == 0:  # Check if the file is empty
                    writer.writeheader()  # Write header if the file is empty
                attributes = extract_message_attributes(message)  # Extract message attributes
                attributes['Timestamp'] = timestamp  # Add timestamp to attributes
                writer.writerow(attributes)  # Write attributes to CSV
        except Exception as e:
            print(f"Error processing {topic}: {e}. Skipping this topic.")


def process_bag_file(bag_file):
    """
    Process a single bag file
    """
    try:
        start_time = time.time()  # Record the start time
        output_folder = os.path.splitext(bag_file)[0] + "_csv"  # Generate the output folder path
        os.makedirs(output_folder, exist_ok=True)  # Create the output folder if it doesn't exist
        topic_generator = extract_topics(bag_file)  # Generate topics from the bag file
        convert_to_csv(topic_generator, output_folder)  # Convert topics to CSV files
        end_time = time.time()  # Record the end time
        elapsed_time = end_time - start_time  # Calculate the elapsed time
        print(f"Processed {bag_file} in {elapsed_time:.2f} seconds")  # Print the elapsed time
    except OSError as e:
        print(f"Error processing {bag_file}: {e}")

def process_bag_files(raw_data_folder_path):
    """
    Process all bag files in the given folder using multiprocessing
    """
    bag_files = list(find_rosbag_files(raw_data_folder_path))  # Get the list of ROS bag files
    cpu_count = psutil.cpu_count()  # Get the number of CPU cores
    target_processes = int(cpu_count * 0.8)  # Calculate the target number of processes (80% of CPU cores)
    pool = multiprocessing.Pool(processes=target_processes)  # Create a multiprocessing Pool with target number of processes
    pool.map(process_bag_file, bag_files)  # Map the bag processing function to the pool
    pool.close()  # Close the pool
    pool.join()  # Wait for all processes in the pool to finish


if __name__ == "__main__":
    raw_data_folder_path = r"F:\Data Analysis Sets\2023_05_13\Test1_10_03_C-R"  # Set the path to the raw data folder
    process_bag_files(raw_data_folder_path)  # Process bag files in the specified folder
    print('Done converting')  # Print a message indicating the conversion is complete
