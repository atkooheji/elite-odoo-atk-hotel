# MIS KPI Matrix — Hotel Management Intelligence

Management monitoring of operational efficiency and revenue quality.

| KPI Name | Business Meaning | Source Model/Field | Alert Threshold | Dashboard |
| :--- | :--- | :--- | :--- | :--- |
| **Occupancy Rate %** | Capacity utilization | `hotel.room.state` | < 60% | Management |
| **RevPAR** | Revenue per available room | `hotel.book.history` | < 50 BHD | Revenue Hub |
| **Check-in Efficiency** | Avg time to check-in after arrival | Audit log (Draft -> Checked-in) | > 15 mins | Ops Dashboard |
| **Room Turnaround Time** | Time from check-out to "Clean" | `cleaning.request` duration | > 120 mins | Housekeeping |
| **NPS / Guest Satisfaction** | Overall guest sentiment | `hotel.room.review.rating` | < 4.0 Stars | Quality |
| **Billing Accuracy** | % of folios corrected after check-out | `account.move` adjustments | > 5% | Finance |

## MIS Dashboard Layout
- **Executive Summary Card**: Revenue MTD vs Target.
- **Trend Chart**: Monthly Occupancy vs ADR.
- **Bottleneck Chart**: Average cleaning time by room type.
- **Quality Table**: Top 5 rooms with most maintenance issues.
