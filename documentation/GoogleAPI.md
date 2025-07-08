To use CanterburyCommuto, it is necessary to have your API key ready from Google. 

0. You need a Google Account.
1. Go to Google Cloud Console.
2. Create a billing account. If the usage of API is below a certain threshold, no payment will be needed.
3. Click on the button next to the Google Cloud logo to make a new project.
4. From Quick access, find APIs&Services. Click on it.
5. Go to the API Library.
6. Type in Google Maps in the search bar.
7. Enable the Google Maps Routes API. (It is probably harmless to enable more APIs than needed.) You will be able to create an API key in this step.
8. Go to Credentials, where you will find your key stored.

*Caveat: Do not share your Google API key to the public. Your key is related to your billing account. If abused, high costs will be incurred.*

## Google Maps Routes API Pricing Summary

Google Maps Routes API is structured into three feature tiers—**Essentials**, **Advanced (Pro)**, and **Preferred (Enterprise)**—with pricing based on usage volume and feature complexity.

| Tier       | Free Monthly Quota | 1–100K Requests | 100K–500K | 500K–1M | 1M–5M | 5M+    |
|------------|--------------------|------------------|------------|----------|--------|--------|
| Essentials | 10,000 requests     | $5.00 / 1,000     | $4.00      | $3.00    | $1.50  | $0.38  |
| Advanced   | 5,000 requests      | $10.00 / 1,000    | $8.00      | $6.00    | $3.00  | $0.75  |
| Preferred  | 1,000 requests      | $15.00 / 1,000    | $12.00     | $9.00    | $4.50  | $1.14  |

- **Essentials**: Basic routing (up to 10 waypoints), no traffic awareness.
- **Advanced (Pro)**: Supports traffic-aware routing, more waypoints (11–25), and route modifiers.
- **Preferred (Enterprise)**: Includes premium features like two-wheel vehicle routing and fleet management.

All tiers offer automatic volume discounts beyond 100,000 monthly requests. Free quotas reset each month and are applied per SKU.

[View official pricing documentation](https://developers.google.com/maps/billing-and-pricing/pricing#routes)

This Python package uses the essential tier of the Google Maps Routes API, relying only on basic parameters and avoiding advanced features, thereby qualifying for standard usage rates.
