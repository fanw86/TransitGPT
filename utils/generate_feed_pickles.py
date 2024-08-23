import warnings

warnings.filterwarnings("ignore")

import os
import sys 

# Get the directory of the current script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Add the parent directory to sys.path
parent_dir = os.path.dirname(current_dir)
sys.path.append(parent_dir)

from utils.constants import file_mapping
from utils.gtfs_loader import pickle_gtfs_loaders, GTFSLoader

pickle_gtfs_loaders(
    file_mapping,
    os.path.join(current_dir, "../gtfs_data/feed_pickles"),
    os.path.join(current_dir, "../gtfs_data/file_mapping.json"),
)
