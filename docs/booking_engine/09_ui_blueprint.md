# UI/UX Blueprint — Booking Engine Experience

## 1. Website Snippet: "Booking Engine Block"
- **Location**: Website Editor -> Dynamic Blocks.
- **Design**:
    - Clean, modern layout (can be horizontal or vertical).
    - Floating labels for "Check-In" and "Check-Out".
    - Guest count dropdown (1-10).
    - "Check Availability" button with loading state.
- **Behavior**:
    - Client-side validation of dates.
    - On click: Redirects to `/hotel/rooms` with parameters.

## 2. Dynamic Results Page (`/hotel/rooms`)
- **Header**: Sticky filter bar to allow updating search without leaving the page.
- **Body**: Grid of Room Types.
- **Card Features**:
    - Primary Image.
    - Name & Rating (Star display).
    - Price / Night (Monetary widget).
    - Key Amenities (Icons).
    - "Book Now" Button.

## 3. Review System Integration
- **Room Details Page**:
    - "Guest Stories" section showing the latest verified reviews.
    - Rating summary (Average score).
- **Review Submission Page**:
    - Clean form: Stars (1-5), Comment text area.
    - Verified badge if the user has a completed booking.

## 4. Modern UX Enhancements
- **Skeleton Loaders**: While checking availability.
- **Smooth Transitions**: Between search results and details.
- **Mobile Optimized**: Responsive layout for all blocks and pages.
