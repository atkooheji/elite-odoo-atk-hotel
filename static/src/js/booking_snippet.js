/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.HotelBookingSnippet = publicWidget.Widget.extend({
    selector: '.s_booking_engine',
    
    start: function () {
        console.log("Hotel Editor: Initializing Booking Engine Widget...");
        this._initDates();
        return this._super.apply(this, arguments);
    },
    
    _initDates: function () {
        const today = new Date().toISOString().split('T')[0];
        const checkIn = this.$el.find('input[name="check_in"]');
        const checkOut = this.$el.find('input[name="check_out"]');
        
        if (checkIn.length && !checkIn.val()) {
            checkIn.val(today);
            checkIn.attr('min', today);
        }
        
        checkIn.on('change', () => {
            if (checkOut.length) {
                checkOut.attr('min', checkIn.val());
            }
        });
    }
});

export default publicWidget.registry.HotelBookingSnippet;
