#The purpose of this code is to create a sample of orginine and destination pairs for testing the Marco Polo package. 
#It includes 6 different combination pairs.
import csv

# Data to be written in the CSV file
data = [
    {
        "Origin of A": "5.373588,-3.998759",
        "Destination of A": "5.327810,-4.005012",
        "Origin of B": "5.361826,-3.990009",
        "Destination of B": "5.322763,-4.002270",
    },
    {
        "Origin of A": "5.373588,-3.998760",
        "Destination of A": "5.327810,-4.005013",
        "Origin of B": "5.368385,-4.006019",
        "Destination of B": "5.335087,-3.995491",
    },
    {
        "Origin of A": "5.373588,-3.998761",
        "Destination of A": "5.327810,-4.005014",
        "Origin of B": "5.355748,-3.969820",
        "Destination of B": "5.333238,-4.006999",
    },
    {
        "Origin of A": "5.373588,-3.998762",
        "Destination of A": "5.327810,-4.005015",
        "Origin of B": "5.392951,-3.975507",
        "Destination of B": "5.347369,-4.003102",
    },
    {
        "Origin of A": "5.361826,-3.990009",
        "Destination of A": "5.322763,-4.002270",
        "Origin of B": "5.368385,-4.006019",
        "Destination of B": "5.335087,-3.995491",
    },
    {
        "Origin of A": "5.355748,-3.969820",
        "Destination of A": "5.333238,-4.006999",
        "Origin of B": "5.392951,-3.975507",
        "Destination of B": "5.347369,-4.003102",
    },    
]

# Path to save the CSV file
file_path = "origin_destination_coordinates.csv"

# Write the data to a CSV file
with open(file_path, mode='w', newline='') as file:
    writer = csv.DictWriter(
        file, fieldnames=["Origin of A", "Destination of A", "Origin of B", "Destination of B"]
    )
    writer.writeheader()  # Write the header
    writer.writerows(data)  # Write the rows

print(f"CSV file saved as {file_path}")
