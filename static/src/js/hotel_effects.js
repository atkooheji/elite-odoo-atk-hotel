/** @odoo-module **/

import publicWidget from "@web/legacy/js/public/public_widget";

publicWidget.registry.AlFarisEffects = publicWidget.Widget.extend({
    selector: '#wrap',

    start: function () {
        this._initScrollReveal();
        return this._super.apply(this, arguments);
    },

    _initScrollReveal: function () {
        const revealElements = this.el.querySelectorAll('.reveal-up');

        const observerOptions = {
            threshold: 0.1,
            rootMargin: '0px 0px -50px 0px'
        };

        const revealObserver = new IntersectionObserver((entries, observer) => {
            entries.forEach((entry) => {
                if (entry.isIntersecting) {
                    entry.target.classList.add('active');
                    observer.unobserve(entry.target);
                }
            });
        }, observerOptions);

        revealElements.forEach((el) => {
            revealObserver.observe(el);
        });
    },
});
