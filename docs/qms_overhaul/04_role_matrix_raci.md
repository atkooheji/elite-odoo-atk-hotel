# Role & Security Design — ATK Hotel

## User Roles (Groups)

| Role | Responsibility | Access Level |
| :--- | :--- | :--- |
| **Hotel Receptionist** | Daily operations, bookings, check-in/out. | CRUD Bookings, Read Rooms. |
| **Hotel Manager** | Approvals, pricing, full MIS visibility. | Full CRUD + Approvals. |
| **Housekeeping Lead** | Room status, cleaning teams. | CRUD Cleaning/Maintenance. |
| **Auditor / Finance** | Revenue verification, reporting. | Read-Only all + Finance CRUD. |

## RACI Matrix

| Task | Receptionist | Manager | Housekeeping | Finance |
| :--- | :--- | :--- | :--- | :--- |
| Create Booking | **R/A** | S | I | I |
| Confirm Complimentary | C | **A** | I | I |
| Room Inspection | I | C | **R/A** | I |
| Finalize Folio | **R** | S | I | **A** |
| Configure Pricing | I | **R/A** | I | C |

## Record Rule Design
- **Multi-Company**: Users only see bookings and rooms for their allowed companies.
- **Privacy**: Receptionists only see guest contact info for active/upcoming bookings (optional enhancement).
