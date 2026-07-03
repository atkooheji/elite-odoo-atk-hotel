# Functional Definition — Booking Engine Block

## Module Objective
To provide a seamless, high-performance "Booking Engine" experience within the Odoo website, allowing end-users to search for, book, and review hotel rooms directly from any web page.

## Business Scope
- **Interactive Search Block**: A draggable website snippet for the Odoo editor.
- **Dynamic Availability**: Real-time checking of room availability via the `atk_hotel` ERP bridge.
- **Booking Journey**: Unified flow from landing page to confirmed reservation.
- **Post-Stay Feedback**: Integration of a review system to capture guest experiences.

## In-Scope
- Website Snippet (Booking Engine Block).
- Dynamic Results Page (Filtering by dates/guests).
- Booking confirmation flow.
- Review submission and display.

## Out-of-Scope
- Payment gateway integration (handled by standard Odoo payment).
- Flights or third-party activities.

## Process Owner
- Hotel General Manager / Web Administrator.

## Stakeholders
- Potential Guests (End Users).
- Hotel Staff (Front Desk/Sales).
- Management (for MIS/Reporting).

## Key Use Cases
1. **Quick Search**: A user lands on the homepage, enters dates in the block, and sees available suites.
2. **Room Discovery**: A user browses rooms, reads reviews, and makes an informed decision.
3. **Instant Booking**: A user confirms their stay and receives an immediate reference number.
4. **Feedback Loop**: A guest leaves a review after their stay, which populates the website for future users.

## Integration Points
- `atk_hotel`: Core room management, pricing, and booking history.
- `website`: For the editor and public pages.
- `res.partner`: Guest profile management.
