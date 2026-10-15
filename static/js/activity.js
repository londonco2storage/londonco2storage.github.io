// Keep clicks made while GoatCounter loads, without storing visitor details.
(() => {
    'use strict';
    const pending = [];
    window.goatcounter = window.goatcounter || {};
    window.goatcounter.no_events = true;

    const flush = () => {
        if (typeof window.goatcounter.count !== 'function') return;
        while (pending.length) window.goatcounter.count(pending.shift());
    };

    document.addEventListener('click', event => {
        const element = event.target.closest('[data-goatcounter-click]');
        if (!element) return;
        pending.push({
            path: element.dataset.goatcounterClick,
            title: element.dataset.goatcounterTitle || element.textContent.trim(),
            event: true,
            no_session: element.dataset.goatcounterNoSession === '1',
        });
        flush();
    });

    document.addEventListener('load', event => {
        if (event.target.matches && event.target.matches('script[data-goatcounter]')) flush();
    }, true);
})();
