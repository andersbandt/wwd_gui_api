
import csv
from pathlib import Path

class CSVHelper:
    def __init__(self, file_path):
        self.file_path = Path(file_path)

    def initialize_file(self, headers):
        """Initialize the CSV file with headers."""
        with open(self.file_path, mode='w', newline='') as file:
            writer = csv.writer(file)
            writer.writerow(headers)

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
        """Print data from the CSV file."""
        data = self.read_data()
        for row in data:
            print(row)

    def delete_file(self):
        """Delete the CSV file."""
        if self.file_path.exists():
            self.file_path.unlink()