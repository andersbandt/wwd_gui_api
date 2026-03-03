"""CSV file read/write helper utilities."""

# import needed modules
import logging
import csv
from typing import Dict, Any, Optional
from pathlib import Path
import os

logger = logging.getLogger(__name__)


def init_csvh(data_dir: str, filename: str, headers):
    """
    Create CSVHelper and initialize file. Returns the CSVHelper instance.
    """
    full_path = os.path.join(data_dir, filename)
    csvh = CSVHelper(full_path, headers)
    return csvh


class CSVHelper:
    def __init__(self, file_path, headers):
        self.file_path = Path(file_path)
        self.headers = headers

    def initialize_file(self):
        """Initialize the CSV file with headers."""
        with open(self.file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(self.headers)

    def add_row(self, row):
        """Add a single row of data to the CSV file."""
        with open(self.file_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(row)

    def add_rows(self, rows):
        """Add multiple rows of data to the CSV file."""
        with open(self.file_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerows(rows)

    def add_row_from_dict(self, row_dict: Dict[str, Any], default: Optional[str] = "") -> None:
        """
        Add a row based on a dictionary keyed by your known headers.

        - Values are written in the same order as self.headers.
        - Keys in row_dict that are not in headers are ignored.
        - Missing header keys are filled with `default` (empty string by default).
        - None values are converted to empty strings (or `default` if provided).

        :param row_dict: Dict where keys correspond to CSV headers you control.
        :param default: Value used when a header is missing in row_dict or is None.
        """
        # Normalize values and ensure order
        ordered_row = []
        for h in self.headers:
            val = row_dict.get(h, default)
            if val is None:
                val = default
            ordered_row.append(val)

        # Now append the row
        with open(self.file_path, mode='a', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(ordered_row)

    def read_data(self):
        """Read data from the CSV file."""
        with open(self.file_path, mode='r', newline='') as file:
            reader = csv.reader(file)
            data = [row for row in reader]
        return data

    def read_data_as_dict(self):
        """Read data from the CSV file as a list of dictionaries."""
        with open(self.file_path, mode='r', newline='') as file:
            reader = csv.DictReader(file)
            data = [row for row in reader]
        return data

    def print_data(self):
        """Log data from the CSV file at DEBUG level."""
        data = self.read_data()
        for row in data:
            logger.debug(row)

    def delete_file(self):
        """Delete the CSV file."""
        if self.file_path.exists():
            self.file_path.unlink()