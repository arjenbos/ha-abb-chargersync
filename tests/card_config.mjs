/** Verify the custom-card picker API without a browser or HA account. */
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const registrations = new Map();
globalThis.HTMLElement = class {};
globalThis.customElements = {get: key => registrations.get(key), define: (key,value) => registrations.set(key,value)};
globalThis.window = {};
const source = await readFile(new URL('../custom_components/abb_chargersync/www/chargersync-card.js',import.meta.url),'utf8');
const {ChargerSyncCard} = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
assert.equal(registrations.get('chargersync-card'),ChargerSyncCard);
assert.equal(window.customCards.length,1);
assert.equal(window.customCards[0].type,'chargersync-card');
const form = ChargerSyncCard.getConfigForm();
assert.equal(form.schema.find(field => field.name === 'entity').selector.entity.integration,'abb_chargersync');
assert.equal(form.schema.find(field => field.name === 'tab').selector.select.options.length,8);
assert.equal(ChargerSyncCard.getStubConfig({states:{'sensor.garage_charging_status':{}}}).entity,'sensor.garage_charging_status');
assert.equal(ChargerSyncCard.getStubConfig().entity,'sensor.charger_charging_status');
assert.equal(ChargerSyncCard.getStubConfig({states:{'sensor.other_charging_status':{},'sensor.garage_charging_status':{}},entities:{'sensor.garage_charging_status':{platform:'abb_chargersync'}}}).entity,'sensor.garage_charging_status');
// Reimporting the module with a different resource URL cannot duplicate registration.
await import(`data:text/javascript;base64,${Buffer.from(source+'\n// reimport').toString('base64')}`);
assert.equal(window.customCards.length,1);
console.log('Card registration, visual configuration, default selection and duplicate-loading checks passed.');
