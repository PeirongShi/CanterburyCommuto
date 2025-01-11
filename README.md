This Python package CanterburyCommuto is created under the instruction of Professor Florian Grosset and Professor Emilien Schultz. 

Dear users, 

The aim of CanterburyCommuto is to find the percentages of time and distance travelled before, during, and after the overlap, if it exists, between two commuting routes. 
However, you can run this package on as many route pairs as you wish, as long as these route pairs are stored in a csv file in a way similar to the output of Sample.py in the repository.
Don't worry if the order of the columns in your csv file is different from that of the Sample.py output, as CanterburyCommuto will ask you to manually fill in the column names corresponding to 
the origins and destinations of the route pairs. 

To use CanterburyCommuto, it is necessary to have your API key from Google. How to find this key?

1. Go to Google Cloud Console.
2. Create a billing account. If the usage of API is below certain threshold, no payment will be needed.
3. Click on the button next to the Google Cloud logo to make a new project.
4. From Quick access, find APIs&Services. Click on it.
5. Go to the API Library.
6. Type in Google Maps in the search bar.
7. Enable the relevant APIs. (It is probably harmless to enable more APIs than needed.) You will be able to create an API key in this step.
8. Go to Credentials, where you will find your key stored.

Caveat: Do not share your Google API key to the public. Your key is related to your billing account. If abused, high cost will be incurred. 
