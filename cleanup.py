import os
import shutil
import logging
import logger

def clear_folder(folder_path):
    try:
        # Check if the folder exists
        if os.path.exists(folder_path):
            # Iterate over the files and subdirectories in the folder
            for filename in os.listdir(folder_path):
                file_path = os.path.join(folder_path, filename)

                # Check if it's a file or directory
                if os.path.isfile(file_path):
                    # Remove file
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    # Remove directory and its contents
                    shutil.rmtree(file_path)

            logger.log_message(f"Contents of '{folder_path}' cleared successfully.")
            return (f"Contents of '{folder_path}' cleared successfully.")
        else:
            logger.log_message(f"The folder '{folder_path}' does not exist.", level=logging.WARNING)
            return(f"The folder '{folder_path}' does not exist.")
    except Exception as e:
        logger.log_message(e, level=logging.ERROR)
        return(f"An error occurred: {e}")
