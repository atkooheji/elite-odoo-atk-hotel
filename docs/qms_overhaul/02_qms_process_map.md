# QMS Process Map — Hotel Operations

## Process: Guest Booking & Stay Management

| Attribute | Detail |
| :--- | :--- |
| **Process Name** | Guest Stay Lifecycle |
| **Purpose** | To ensure high-quality service delivery and record integrity throughout the guest's stay. |
| **Trigger** | Booking inquiry (Website or Manual). |
| **Inputs** | Guest identity, Dates, Room selection, Payment info. |
| **Process Steps** | 1. **Booking**: Create record (Draft). <br/> 2. **Confirmation**: Validate availability & ID (Confirmed). <br/> 3. **Check-in**: Verify signature & activate room (Checked-in). <br/> 4. **Service**: Daily cleaning & maintenance (In-Progress). <br/> 5. **Check-out**: Finalize folio & release room (Checked-out). <br/> 6. **Feedback**: Collect guest review. |
| **Decision Points** | Availability check, ID verification, Payment status. |
| **Outputs** | Confirmed Folio, Clean Room, Guest Review. |
| **Responsible Roles** | Receptionist (Booking/Check-in), Cleaning Team (Service), Manager (Approvals). |

## Controls & Compliance
- **Submission Controls**: Mandatory Passport/Visa fields for international guests.
- **Validation Controls**: Automated double-booking prevention at the ORM level.
- **Approval Checkpoints**: Manager approval required for complimentary/house-use stays.
- **Nonconformity Handling**: Room complaints must be logged as "Internal Incidents" linked to the booking for quality tracking.
- **Escalation Rules**: Unresolved cleaning requests (> 4 hours) escalated to Operations Manager.

## Documented Records
- `hotel.book.history`: The master record of stay.
- `hotel.room.inspection`: Evidence of room quality before check-in.
- `hotel.room.review`: Evidence of customer satisfaction.
