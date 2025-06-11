#The purpose of this code is to create a sample of orginine and destination pairs for testing the Marco Polo package. 
#It includes 6 different combination pairs.
import csv

# Data to be written in the CSV file
data = [
    {
        "ID": "R1",
        "home_A_latitude": "5.373588", "home_A_longitude": "-3.998759",
        "work_A_latitude": "5.327810", "work_A_longitude": "-4.005012",
        "home_B_latitude": "5.373588", "home_B_longitude": "-3.998759",
        "work_B_latitude": "5.327810", "work_B_longitude": "-4.005012",
    },
    {
        "ID": "R2",
        "home_A_latitude": "5.373588", "home_A_longitude": "-3.998759",
        "work_A_latitude": "5.327810", "work_A_longitude": "-4.005012",
        "home_B_latitude": "5.361826", "home_B_longitude": "-3.990009",
        "work_B_latitude": "5.322763", "work_B_longitude": "-4.002270",
    },
    {
        "ID": "R3",
        "home_A_latitude": "5.373588", "home_A_longitude": "-3.998760",
        "work_A_latitude": "5.327810", "work_A_longitude": "-4.005013",
        "home_B_latitude": "5.368385", "home_B_longitude": "-4.006019",
        "work_B_latitude": "5.335087", "work_B_longitude": "-3.995491",
    },
    {
        "ID": "R4",
        "home_A_latitude": "5.373588", "home_A_longitude": "-3.998761",
        "work_A_latitude": "5.327810", "work_A_longitude": "-4.005014",
        "home_B_latitude": "5.355748", "home_B_longitude": "-3.969820",
        "work_B_latitude": "5.333238", "work_B_longitude": "-4.006999",
    },
    {
        "ID": "R5",
        "home_A_latitude": "5.373588", "home_A_longitude": "-3.998762",
        "work_A_latitude": "5.327810", "work_A_longitude": "-4.005015",
        "home_B_latitude": "5.392951", "home_B_longitude": "-3.975507",
        "work_B_latitude": "5.347369", "work_B_longitude": "-4.003102",
    },
    {
        "ID": "R6",
        "home_A_latitude": "5.361826", "home_A_longitude": "-3.990009",
        "work_A_latitude": "5.322763", "work_A_longitude": "-4.002270",
        "home_B_latitude": "5.368385", "home_B_longitude": "-4.006019",
        "work_B_latitude": "5.335087", "work_B_longitude": "-3.995491",
    },
    {
        "ID": "R7",
        "home_A_latitude": "5.355748", "home_A_longitude": "-3.969820",
        "work_A_latitude": "5.333238", "work_A_longitude": "-4.006999",
        "home_B_latitude": "5.392951", "home_B_longitude": "-3.975507",
        "work_B_latitude": "5.347369", "work_B_longitude": "-4.003102",
    },
]

# Path to save the CSV file
file_path = "origin_destination_coordinates.csv"

# Write the data to a CSV file
with open(file_path, mode='w', newline='') as file:
    writer = csv.DictWriter(
        file, fieldnames = ["ID", "home_A_latitude", "home_A_longitude", "work_A_latitude", "work_A_longitude", "home_B_latitude", "home_B_longitude", "work_B_latitude", "work_B_longitude"]
    )
    writer.writeheader()  # Write the header
    writer.writerows(data)  # Write the rows

print(f"CSV file saved as {file_path}")



