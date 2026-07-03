# MIS KPI Matrix — Booking Engine Performance

Management monitoring of the web booking experience and conversion efficiency.

| KPI Name | Business Meaning | Source Model/Field | Alert Threshold | Dashboard |
| :--- | :--- | :--- | :--- | :--- |
| **Web Conversion Rate** | % of visitors who book after searching | `hotel.book.history` / Website Logs | < 2% | Hotel Dashboard |
| **Average Revenue Per Stay** | Revenue performance of web bookings | `hotel.book.history.total_amount` | < 100 BHD | Revenue Dashboard |
| **Search-to-Booking Time** | Average time from first search to confirmation | Calculated | > 10 mins | Ops Dashboard |
| **Average Guest Rating** | Overall satisfaction score from reviews | `hotel.room.review.rating` | < 3.5 Stars | Quality Dashboard |
| **Occupancy Forecast** | Future bookings vs capacity | `hotel.room` availability | < 60% | Management Hub |

## MIS Dashboard Design (Blueprint)
- **Top Card**: Total Web Revenue (MTD).
- **Trend Chart**: Bookings by Source (Website vs Manual).
- **Quality Chart**: Review Distribution (1-5 stars).
- **Demand Heatmap**: Most searched dates vs Actual bookings.
