# QMS Process Map — Guest Booking Journey

## Process Overview
The Guest Booking Journey ensures a consistent, high-quality interaction from the first search until the final review.

| Attribute | Detail |
| :--- | :--- |
| **Process Name** | Guest Booking & Feedback Cycle |
| **Purpose** | To convert web traffic into confirmed reservations and verify service quality through reviews. |
| **Trigger** | User interacts with the "Booking Engine Block" on the website. |
| **Inputs** | Check-in Date, Check-out Date, Guest Count, Room Type preference. |
| **Process Steps** | 1. Search (Frontend API call) <br/> 2. Filter available Room Types <br/> 3. View Room Details & Reviews <br/> 4. Initialize Booking <br/> 5. Confirm Reservation <br/> 6. (Post-Stay) Submit Review. |
| **Decision Points** | Availability (Yes/No), Partner exists (Yes/No), Confirmation (Yes/No). |
| **Outputs** | Confirmed Booking Record (`hotel.book.history`), Review Record (`hotel.room.review`). |
| **Responsible Roles** | Website Visitor (Customer), Reservation Desk (Verification). |
| **Risks** | Double booking, Invalid dates, Poor reviews affecting brand. |
| **Controls** | Real-time availability check, Mandatory fields, Review moderation. |
| **Documented Records** | `hotel.book.history` (Booking details), `res.partner` (Guest info). |

## Controls & Compliance
- **Submission Controls**: Dates must be in the future; checkout must be after check-in.
- **Validation Controls**: Room must be in "Available" state for the entire duration.
- **Audit Trail**: Every booking creates a chatter history in the backend for accountability.
- **Nonconformity Handling**: If a room becomes unavailable during the session, the user is redirected to the results page with a clear explanation.
