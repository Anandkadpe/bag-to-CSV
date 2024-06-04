import os
import csv
import rosbag
import multiprocessing
import time
import psutil

# Define topics to skip
TOPICS_TO_SKIP = ['/camera/color/camera_info', '/camera/color/image_raw','/camera/depth/color/points','/camera/depth/image_rect_raw']  # Add the topics you want to skip

def find_rosbag_files(raw_data_folder_path):
    """
    Find all rosbag files in a folder and its subfolders
    """
    for root, dirs, files in os.walk(raw_data_folder_path):
        for file in files:
            if file.endswith(".bag"):
                yield os.path.join(root, file)

def extract_topics(rosbag_file):
    """
    Extract topics from a ROS bag file
    """
    try:
        bag = rosbag.Bag(rosbag_file)
        for topic, msg, t in bag.read_messages():
            if topic not in TOPICS_TO_SKIP:  # Skip topics in the skip list
                yield topic, t.to_sec(), msg
        bag.close()
    except rosbag.ROSBagException as e:
        print(f"Error processing {rosbag_file}: {str(e)}")

def extract_message_attributes(message, parent_field=None):
    """
    Extract attributes from the message and return as a dictionary
    """
    attributes = {}
    for field in message.__slots__:
        full_field_name = f"{parent_field}.{field}" if parent_field else field
        if hasattr(getattr(message, field), '__slots__'):
            attributes.update(extract_message_attributes(getattr(message, field), parent_field=full_field_name))
        else:
            attributes[full_field_name] = getattr(message, field)
    return attributes

def convert_to_csv(topic_generator, output_folder):
    """
    Convert topics from topic_generator to CSV files
    """
    for topic, timestamp, message in topic_generator:
        try:
            csv_file_path = os.path.join(output_folder, f"{topic.replace('/', '_')}.csv")
            with open(csv_file_path, 'a', newline='') as csv_file:
                writer = csv.DictWriter(csv_file, fieldnames=['Timestamp'] + list(extract_message_attributes(message).keys()))
                if csv_file.tell() == 0:
                    writer.writeheader()
                attributes = extract_message_attributes(message)
                attributes['Timestamp'] = timestamp
                writer.writerow(attributes)
        except Exception as e:
            print(f"Error processing {topic}: {e}. Skipping this topic.")

def process_bag_file(bag_file):
    """
    Process a single bag file
    """
    try:
        start_time = time.time()
        output_folder = os.path.splitext(bag_file)[0] + "_csv"
        os.makedirs(output_folder, exist_ok=True)
        topic_generator = extract_topics(bag_file)
        convert_to_csv(topic_generator, output_folder)
        end_time = time.time()
        elapsed_time = end_time - start_time
        print(f"Processed {bag_file} in {elapsed_time:.2f} seconds")
    except OSError as e:
        print(f"Error processing {bag_file}: {e}")

def process_bag_files(raw_data_folder_path):
    """
    Process all bag files in the given folder using multiprocessing
    """
    bag_files = list(find_rosbag_files(raw_data_folder_path))
    cpu_count = psutil.cpu_count()
    target_processes = int(cpu_count * 0.8)
    pool = multiprocessing.Pool(processes=target_processes)
    pool.map(process_bag_file, bag_files)
    pool.close()
    pool.join()

if __name__ == "__main__":
    raw_data_folder_path = r"G:\Data Analysis Sets\2023_05_13\Test1_10_03_C-R"
    process_bag_files(raw_data_folder_path)
    print("processing......" )
    print('Done converting')