Dear users,

This Python package CanterburyCommuto is created under the instruction of Professor Florian Grosset and Professor Emilien Schultz. 

# Overview
The aim of CanterburyCommuto is to find the percentages of time and distance travelled before, during, and after the overlap, if it exists, between two commuting routes. 

However, you can run this package on as many route pairs as you wish, as long as these route pairs are stored in a csv file in a way similar to the output of Sample.py in the repository.
Don't worry if the order of the columns in your csv file is different from that of the Sample.py output, as CanterburyCommuto will ask you to manually fill in the column names corresponding to 
the origins and destinations of the route pairs. 

# Google API Key
To use CanterburyCommuto, it is necessary to have your API key ready from Google. How to find this key?

1. Go to Google Cloud Console.
2. Create a billing account. If the usage of API is below a certain threshold, no payment will be needed.
3. Click on the button next to the Google Cloud logo to make a new project.
4. From Quick access, find APIs&Services. Click on it.
5. Go to the API Library.
6. Type in Google Maps in the search bar.
7. Enable the relevant APIs. (It is probably harmless to enable more APIs than needed.) You will be able to create an API key in this step.
8. Go to Credentials, where you will find your key stored.

Caveat: Do not share your Google API key to the public. Your key is related to your billing account. If abused, high costs will be incurred. 

# Function Implementation

Once imported from CanterburyCommuto, the Overlap_Function will implement the main goal of this package. 

This function takes the csv file containing the GPS coordinates of route pairs and the API key as the necessary inputs. 
Other optional inputs are a threshold, a width, and a buffer distance, which are used for approximations. 
The function will first ask the user about his/her willingness to have approximations in the overlaps. 

If you answer 'no', then the function will consider that an overlap starts from the first common point of a route pair and ends at the last common point.

Otherwise, there are two types of approximation. 

The first type uses route segments before the first common point and after the last common point, since humans are free entities that can move around and decide to meet early or part later from the common points. Rectangles are created around the route segments before and after the common points. The intersection of the rectangles of the given width is evaluated. If the value of the intersection area over the smaller rectangle area is larger than a certain threshold, the route segment pairs will be kept. The first and last overlapping nodes will be redetermined through these route pairs kept by the rectangle approximation.

After selecting any of the two methods mentioned above, you will receive a follow-up question asking if you would like to obtain the information before and after the overlap, but this will lead to higher costs, as your API is called for more times. You may answer 'no', if you are operating on a tight budget. 

The second type of approximation uses a buffer, whose distance can be chosen by the user optionally. The intersection area of the buffers created along the two routes within a pair will be recorded. The ratios of the intersection over the two buffers will then be calculated. 

The output will be a csv file including the GPS coordinates of the route pairs and the corresponding percentages or values describing the overlaps of route pairs. 

If you have any question, feel free to write in the comment section.

Thank you!

Best regards,

Peirong Shi






