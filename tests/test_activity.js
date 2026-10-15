const assert = require('node:assert/strict');
const { test } = require('node:test');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function setup() {
    const listeners = {};
    const window = {};
    const document = { addEventListener: (name, fn) => { listeners[name] = fn; } };
    vm.runInNewContext(fs.readFileSync(path.join(__dirname, '../static/js/activity.js'), 'utf8'), { window, document });
    const click = () => listeners.click({ target: { closest: () => ({
        dataset: { goatcounterClick: 'download-table1-csv', goatcounterTitle: 'Table 1 CSV download', goatcounterNoSession: '1' },
    }) } });
    const loaded = () => listeners.load({ target: { matches: () => true } });
    return { window, click, loaded, listeners };
}

test('four CSV clicks emit four events without session deduplication', () => {
    const { window, click } = setup();
    const calls = [];
    window.goatcounter.count = event => calls.push(event);
    for (let i = 0; i < 4; i++) click();
    assert.equal(calls.length, 4);
    assert(calls.every(event => event.event && event.no_session && event.path === 'download-table1-csv'));
    assert.equal(window.goatcounter.no_events, true); // Built-in handlers cannot double-count.
    assert.equal(window.goatcounter.no_session, undefined); // Page visits retain deduplication.
});

test('clicks before the tracker loads flush once, then new clicks send immediately', () => {
    const { window, click, loaded } = setup();
    for (let i = 0; i < 4; i++) click();
    const calls = [];
    window.goatcounter.count = event => calls.push(event);
    loaded();
    loaded();
    assert.equal(calls.length, 4);
    click();
    assert.equal(calls.length, 5);
});

test('ordinary navigation is not also sent as a click event', () => {
    const { window, listeners } = setup();
    window.goatcounter.count = () => assert.fail('Unexpected tracking event');
    listeners.click({ target: { closest: () => null } });
});
