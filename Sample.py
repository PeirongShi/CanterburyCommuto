#The purpose of this code is to create a sample of orginine and destination pairs for testing the Marco Polo package. 
#It includes 6 different combination pairs.
import csv

import csv

# Data to be written in the CSV file
data = [
    {
        "OriginA": "5.373588,-3.998759",
        "DestinationA": "5.327810,-4.005012",
        "OriginB": "5.361826,-3.990009",
        "DestinationB": "5.322763,-4.002270",
    },
    {
        "OriginA": "5.373588,-3.998760",
        "DestinationA": "5.327810,-4.005013",
        "OriginB": "5.368385,-4.006019",
        "DestinationB": "5.335087,-3.995491",
    },
    {
        "OriginA": "5.373588,-3.998761",
        "DestinationA": "5.327810,-4.005014",
        "OriginB": "5.355748,-3.969820",
        "DestinationB": "5.333238,-4.006999",
    },
    {
        "OriginA": "5.373588,-3.998762",
        "DestinationA": "5.327810,-4.005015",
        "OriginB": "5.392951,-3.975507",
        "DestinationB": "5.347369,-4.003102",
    },
    {
        "OriginA": "5.361826,-3.990009",
        "DestinationA": "5.322763,-4.002270",
        "OriginB": "5.368385,-4.006019",
        "DestinationB": "5.335087,-3.995491",
    },
    {
        "OriginA": "5.355748,-3.969820",
        "DestinationA": "5.333238,-4.006999",
        "OriginB": "5.392951,-3.975507",
        "DestinationB": "5.347369,-4.003102",
    },    
]

# Path to save the CSV file
file_path = "origin_destination_coordinates.csv"

# Write the data to a CSV file
with open(file_path, mode='w', newline='') as file:
    writer = csv.DictWriter(
        file, fieldnames=["OriginA", "DestinationA", "OriginB", "DestinationB"]
    )
    writer.writeheader()  # Write the header
    writer.writerows(data)  # Write the rows

print(f"CSV file saved as {file_path}")
