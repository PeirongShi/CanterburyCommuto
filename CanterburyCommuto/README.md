# CanterburyCommuto

The aim of CanterburyCommuto is to find commuting information including time and distance travelled before, during, and after the overlap, if it exists, between two routes. 

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

For Google Maps Routes APIs, the **essential services**—**Directions** and **Distance Matrix APIs**—each include a **free monthly usage cap of 10,000 requests**. Beyond that, usage from **10,001 to 100,000 requests** is billed at **\$5 per 1,000 requests**, and any usage **exceeding 100,000 requests** is billed at a reduced rate of **\$4 per 1,000 requests**. The **advanced versions**—**Directions Advanced** and **Distance Matrix Advanced**—offer enhanced features such as traffic-aware routing and waypoint optimization. These have a **lower free monthly cap of 5,000 requests**, with usage from **5,001 to 100,000 requests** charged at **\$10 per 1,000 requests**, and any requests **above 100,000** billed at **\$8 per 1,000 requests**.

This Python package uses the essential tier of the Google Maps Directions API, relying only on basic parameters and avoiding advanced features, thereby qualifying for standard usage rates.

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

Next, import the main function.

```bash
from canterburycommuto.CanterburyCommuto import Overlap_Function
```

Then, to use CanterburyCommuto, you can run the command in a way like the example illustrated below. This example chooses to create 150-meter buffers along the two routes to find the buffers' intersection ratios for each route. The output is "buffer_output.csv". 

```bash
python -m canterburycommuto origin_destination_coordinates.csv YOUR_GOOGLE_API_KEY \
    --threshold 60 \
    --width 120 \
    --buffer 150 \
    --approximation "yes with buffer" \
    --commuting_info "yes" \
    --colorna "home_A" \
    --coldesta "work_A" \
    --colorib "home_B" \
    --colfestb "work_B" \
    --output_overlap "overlap_output.csv" \
    --output_buffer "buffer_output.csv" \
    --skip_invalid True
```

You can run this package on as many route pairs as you wish, as long as these route pairs are stored in a csv file in a way similar to the output of Sample.py in the repository.
Don't worry if the order of the columns in your csv file is different from that of the Sample.py output, as you can manually fill in the column names corresponding to the origins and destinations of the route pairs in CanterburyCommuto. 
See example.ipynb for how to run all options of the package's major function. 

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
21. **aoverlapDist**: Distance of the overlapping segment on route A inside the buffer intersection with route B.  
22. **aoverlapTime**: Time to traverse the overlapping segment on route A.  
23. **boverlapDist**: Distance of the overlapping segment on route B inside the buffer intersection with route A.  
24. **boverlapTime**: Time to traverse the overlapping segment on route B.

### Overlap Function Options

This table summarizes the available options for the package's main function, including whether commuting information before and after the overlap can be considered, how realistic the results are, and a brief description.

| Option Name                 | Commuting Information (Pre/Post Overlap) Available? | Closeness to Reality (0 = Not Close, 10 = Very Close) | Description |
|----------------------------|---------------------------|--------------------------------------|-------------|
| Common Node                | Yes                       | 6                                    | This option finds the first and last common nodes along the two routes' polylines given by Google Maps. The overlapping information is obtained via these nodes. |
| Rectangle Approximation    | Yes                       | 5 to 7                                | As a modified variant of the Common Node Method, this option draws rectangles along the route segments before and after the first and last common nodes of the two routes. It may extend the overlapping range of the route pair if the overlapping area ratio of these rectangles exceeds certain thresholds, which is set to 50% by default, but adjustable by the users. |
| Buffer Area Ratio          | No                        | 8                                    | This option creates 100-meter (m) buffers along the two routes to find the ratios of the buffers' intersection area for each route separately. The buffer width is 100m by default, but it may be adjusted upon the users' wishes. |
| Buffer Route Node          | Yes                       | 6 to 8                                | This option considers the routes and buffers as lines and geometric shapes. It finds the closest nodes to the points of intersections among the buffer polygons and route lines. The overlapping information is determined based on these closest nodes. |
| Buffer Route Intersection  | Yes                       | 9                                    | As an improved version of the Buffer Route Node method, this option directly records the GPS coordinates corresponding to the points of intersections among the buffer polygons and the route lines and then proceeds to compute the overlapping distance and time information based on these GPS coordinates. |

## Acknowledgment

This Python package CanterburyCommuto is created under the instruction of Professor Florian Grosset and Professor Émilien Schultz. 

The **Specification on API Usage** section, located in doc, was written with assistance from OpenAI's ChatGPT, as its explanation on the details of API utilization is relatively clear. 

If you have any question, please open an issue.






