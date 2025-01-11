#The purpose of this code is to create a sample of orginine and destination pairs for testing the Marco Polo package. 
#It includes 6 different combination pairs.
import csv

# Data to be written in the CSV file
data = [
    {
        "home_A": "5.373588,-3.998759",
        "work_A": "5.327810,-4.005012",
        "home_B": "5.361826,-3.990009",
        "work_B": "5.322763,-4.002270",
    },
    {
        "home_A": "5.373588,-3.998760",
        "work_A": "5.327810,-4.005013",
        "home_B": "5.368385,-4.006019",
        "work_B": "5.335087,-3.995491",
    },
    {
        "home_A": "5.373588,-3.998761",
        "work_A": "5.327810,-4.005014",
        "home_B": "5.355748,-3.969820",
        "work_B": "5.333238,-4.006999",
    },
    {
        "home_A": "5.373588,-3.998762",
        "work_A": "5.327810,-4.005015",
        "home_B": "5.392951,-3.975507",
        "work_B": "5.347369,-4.003102",
    },
    {
        "home_A": "5.361826,-3.990009",
        "work_A": "5.322763,-4.002270",
        "home_B": "5.368385,-4.006019",
        "work_B": "5.335087,-3.995491",
    },
    {
        "home_A": "5.355748,-3.969820",
        "work_A": "5.333238,-4.006999",
        "home_B": "5.392951,-3.975507",
        "work_B": "5.347369,-4.003102",
    },    
]

# Path to save the CSV file
file_path = "origin_destination_coordinates.csv"

# Write the data to a CSV file
with open(file_path, mode='w', newline='') as file:
    writer = csv.DictWriter(
        file, fieldnames=["home_A", "work_A", "home_B", "work_B"]
    )
    writer.writeheader()  # Write the header
    writer.writerows(data)  # Write the rows

print(f"CSV file saved as {file_path}")
