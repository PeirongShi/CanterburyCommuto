# CanterburyCommuto

The aim of CanterburyCommuto is to find the percentages of time and distance travelled before, during, and after the overlap, if it exists, between two commuting routes. 

It relies on the Google Maps API. 

## How to use it

### Install the package

To use CanterburyCommuto, you need to clone the respository first. You can do this by running the following command in your terminal:

```bash
git clone https://github.com/PeirongShi/CanterburyCommuto.git
```

And then install the requirements

```bash
cd CanterburyCommuto
pip install -r requirements.txt
```

### Get Google API Key

To use CanterburyCommuto, it is necessary to have your API key ready from Google. 

0. You need a Google Account.
1. Go to Google Cloud Console.
2. Create a billing account. If the usage of API is below a certain threshold, no payment will be needed.
3. Click on the button next to the Google Cloud logo to make a new project.
4. From Quick access, find APIs&Services. Click on it.
5. Go to the API Library.
6. Type in Google Maps in the search bar.
7. Enable the Google Maps Directions API. (It is probably harmless to enable more APIs than needed.) You will be able to create an API key in this step.
8. Go to Credentials, where you will find your key stored.

*Caveat: Do not share your Google API key to the public. Your key is related to your billing account. If abused, high costs will be incurred.*

### Launch the computation

You can generate a test dataset with the script
  
```bash
python canterburycommuto/Sample.py
```

Otherwise, you need to create a csv file with the following columns:

1. **OriginA**: The GPS coordiantes of the starting location of route A in each route pair.
2. **DestinationA**: The GPS coordiantes of the ending location of route A in every route pair.
3. **OriginB**: The starting location of route B.
4. **DestinationB**: The ending location of route B.

Then, to use CanterburyCommuto, you need to run the following command in your terminal:

```bash
python -m canterburycommuto origin_destination_coordinates.csv YOUR_KEY
```

You can run this package on as many route pairs as you wish, as long as these route pairs are stored in a csv file in a way similar to the output of Sample.py in the repository.
Don't worry if the order of the columns in your csv file is different from that of the Sample.py output, as you can manually fill in the column names corresponding to the origins and destinations of the route pairs in CanterburyCommuto. 

For example, if you would like to find the intersection ratio of buffers created along two routes, you can type in the following command. 

```bash
python -m canterburycommuto origin_destination_coordinates.csv YOUR_GOOGLE_API_KEY \
    --threshold 60 \
    --width 120 \
    --buffer 150 \
    --approximation "yes with buffer" \
    --commuting_info "yes" \
    --colorna "Start_A" \
    --coldesta "End_A" \
    --colorib "Start_B" \
    --colfestb "End_B" \
    --output_overlap "overlap_output.csv" \
    --output_buffer "buffer_output.csv"
```
'threshold' has default 50, which is useful when approximations are made around the first and last common locations of the route pairs. rectangles are created for each segment before and after the overlap. If the ratio of the intersection area over the smaller area in the segment pair is above 50, then this segment pair is kept to extend the exact overlap.

'width' has a default of 100 meters. It is the width of the rectangle created around the segments before and after the overlap. 

'buffer' has a default of 100 meters as well. It specifies the width of the buffer created along the route.

### Results

The output will be a csv file including the GPS coordinates of the route pairs' origins and destinations and the values describing the overlaps of route pairs. Graphs are also produced to visualize the commuting paths on the **OpenStreetMap** background. By placing the mouse onto the markers, one is able to see the origins and destinations of route A and B marked as O1, D1, O2, and D2. O stands for origin and D represents destination. Distances are measured in kilometers and the time unit is minute. Users are able to calculate percentages of overlaps, for instance, with the values of the following variables. As shown below, the list explaining the meaning of the output variables:

1. **OriginA**: The starting location of route A.
2. **DestinationA**: The ending location of route A.
3. **OriginB**: The starting location of route B.
4. **DestinationB**: The ending location of route B.

5. **aDist**: Total distance of route A. 
6. **aTime**: Total time to traverse route A.
7. **bDist**: Total distance of route B.
8. **bTime**: Total time to traverse route B.

9. **overlapDist**: Distance of the overlapping segment between route A and route B.
10. **overlapTime**: Time to traverse the overlapping segment between route A and route B.

11. **aBeforeDist**: Distance covered on route A before the overlap begins.
12. **aBeforeTime**: Time spent on route A before the overlap begins.
13. **bBeforeDist**: Distance covered on route B before the overlap begins.
14. **bBeforeTime**: Time spent on route B before the overlap begins.

15. **aAfterDist**: Distance covered on route A after the overlap ends.
16. **aAfterTime**: Time spent on route A after the overlap ends.
17. **bAfterDist**: Distance covered on route B after the overlap ends.
18. **bAfterTime**: Time spent on route B after the overlap ends.
19. **aIntersecRatio**: The proportion of the buffer area of Route A that intersects with the buffer of Route B. It is calculated as:

    `aIntersecRatio = Intersection Area / Area of A`

20. **bIntersecRatio**: The proportion of the buffer area of Route B that intersects with the buffer of Route A.


## Acknowledgment

This Python package CanterburyCommuto is created under the instruction of Professor Florian Grosset and Professor Émilien Schultz. 

The **Specification on API Usage** section of this README.md was written with assistance from OpenAI's ChatGPT, as its explanation on the details of API utilization is relatively clear. 

If you have any question, please open a issue.






