/** Browser regression tests with a simulated HA connection; never call the cloud. */
const {chromium} = require('playwright');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const root = path.resolve(__dirname, '..');
(async () => {
  const browser = await chromium.launch({headless:true, ...(process.env.CHARGERSYNC_CHROMIUM ? {executablePath:process.env.CHARGERSYNC_CHROMIUM} : {})});
  const page = await browser.newPage({viewport:{width:1100,height:1000}});
  const errors = []; page.on('pageerror', error => errors.push(error.message));
  await page.route('**/*', async route => {
    if (route.request().url().endsWith('/card.js')) return route.fulfill({contentType:'application/javascript', body:fs.readFileSync(path.join(root,'custom_components/abb_chargersync/www/chargersync-card.js'),'utf8')});
    if (route.request().url() === 'http://chargersync.test/') return route.fulfill({contentType:'text/html', body:`<!doctype html><html><head><style>body{font:15px system-ui;background:#f5f7fa;margin:24px;--primary-color:#007c91;--primary-text-color:#172d38;--secondary-text-color:#596b74;--secondary-background-color:#edf2f5;--divider-color:#dce3e7;--error-color:#c62828;--text-primary-color:white}ha-card{display:block;background:white;border:1px solid #dce3e7;border-radius:16px;max-width:1100px;margin:auto}</style></head><body><script type="module" src="/card.js"></script></body></html>`});
    return route.abort();
  });
  await page.goto('http://chargersync.test/');
  await page.evaluate(async () => {
    await customElements.whenDefined('chargersync-card');
    window.calls = [];
    window.fixtures = {
      schedules:[{id:1,startTime:'22:00',endTime:'06:00',open:1}],
      sessions:{data:[{orderId:'session-1',startTime:'2026-10-24 20:00:00',stopTime:'2026-10-24 22:00:00',energy:12500,solarEnergy:5000,cost:3.75,currencyType:1,duration:7200,isCompanyCarSession:0,chargeFinishReason:'Vehicle finished'}]},
      currencies:[{currencyType:1,tag:'EUR',name:'Euro'}],
      load_limits:{enabled:true,ranges:[{weekdays:127,from:0,to:21600,limit:10}]},
      solar_offsets:{solar_start_current:1,solar_start_wait:30,solar_charging_current:2,solar_charging_wait:60,eco_start_current:3,eco_start_wait:90,eco_charging_current:4,eco_charging_wait:120},
      price:{averagePrice:'0.3',currencyType:1,offPeakSt:'22:00',offPeakEt:'06:00',offPeakPrice:'0.2'},
      auto_export:{enabled:true,email:'example@example.com',cycle:3,format:'csv',isCompanyCarSession:0},
      diagnostics:{cloud_online:1,remote_available:true,model:'Terra AC',firmware:'1.8.37',unsupported:['cable'],settings_failures:{active_mode:{error:'ConfigurationUnavailableError',result_code:1}}},
      firmware:[],log_info:{first:10,last:11,count:2},logs:[{serial:10,timestamp:100,type:1,code:2,detail:3}],
      trends:{currencyType:1,trends:[{date:'2026-10-24',energy:12500,cost:3.75,duration:7200,trans:1}]},
    };
    const card = document.createElement('chargersync-card');
    card.setConfig({entity:'sensor.driveway_charging_status',title:'Driveway charger'});
    document.body.append(card);
    card.hass = {callWS:async message => {
      window.calls.push(message);
      if (message.type === 'config/entity_registry/list') return [{entity_id:'sensor.driveway_charging_status',platform:'abb_chargersync',device_id:'ha-device'}];
      if (window.failResource === message.service_data.resource) throw new Error('Resource temporarily unavailable');
      return {response:{result:window.fixtures[message.service_data.resource] ?? null}};
    }};
    window.card = card;
  });
  const idle = () => page.waitForFunction(() => window.card.loaded && !window.card.busy);
  const tab = async label => { await page.getByRole('button',{name:label,exact:true}).click(); await idle(); };
  const section = title => page.locator('section').filter({has:page.getByRole('heading',{name:title,exact:true})});
  await idle();
  assert.equal(await page.evaluate(() => calls.filter(c => c.service && c.service !== 'get_data').length),0);
  await page.getByRole('button',{name:'Edit',exact:true}).click();
  await section('Edit schedule').locator('[name=start_time]').fill('21:30');
  await section('Edit schedule').getByRole('button',{name:'Save',exact:true}).click(); await idle();
  assert.equal(await page.evaluate(() => calls.find(c => c.service === 'update_schedule').service_data.start_time),'21:30');
  assert.equal(await page.evaluate(() => calls.find(c => c.service === 'update_schedule').service_data.schedule_id),1);
  const dismiss = dialog => dialog.dismiss(); page.once('dialog',dismiss);
  await page.getByRole('button',{name:'Delete',exact:true}).click();
  assert.equal(await page.evaluate(() => calls.filter(c => c.service === 'delete_schedule').length),0);
  const newForm = section('New schedule');
  await newForm.getByRole('button',{name:'Save',exact:true}).click(); await idle();
  page.once('dialog',d => d.accept()); await page.getByRole('button',{name:'Delete',exact:true}).click(); await idle();
  await tab('History & costs');
  assert.match(await page.locator('.stats').innerText(),/12\.50 kWh/);
  assert.match(await page.locator('.content').innerText(),/40\.0%/);
  await page.getByRole('button',{name:'Mark company',exact:true}).click(); await idle();
  const stats = section('Cloud statistics');
  await stats.locator('[name=start_time]').fill('2026-10-01'); await stats.locator('[name=end_time]').fill('2026-10-25');
  await stats.getByRole('button',{name:'Load statistics'}).click(); await idle();
  assert.equal(await page.locator('svg rect').count(),1);
  await tab('Current limits');
  await section('Add time window to draft').locator('[name=from]').fill('06:00');
  await section('Add time window to draft').getByRole('button',{name:'Add window'}).click();
  page.once('dialog',d => d.accept()); await section('Apply draft').getByRole('button',{name:'Save',exact:true}).click(); await idle();
  assert.equal(await page.evaluate(() => calls.find(c => c.service === 'replace_load_limits').service_data.ranges.length),2);
  await tab('Solar settings'); await section('Solar and Eco mix thresholds').getByRole('button',{name:'Save',exact:true}).click(); await idle();
  await tab('Tariffs'); await section('Charging tariffs').getByRole('button',{name:'Save',exact:true}).click(); await idle();
  await tab('Reports'); await section('Automatic reports').getByRole('button',{name:'Save',exact:true}).click(); await idle();
  assert.equal(await page.evaluate(() => typeof calls.find(c => c.service === 'set_auto_export').service_data.settings.cycle),'number');
  const exportForm = section('Export sessions by email');
  await exportForm.locator('[name=email]').fill('example@example.com');
  await exportForm.locator('[name=start_time]').fill('2026-10-01T00:00'); await exportForm.locator('[name=end_time]').fill('2026-10-25T23:59');
  page.once('dialog',d => d.accept()); await exportForm.getByRole('button',{name:'Send export'}).click(); await idle();
  await tab('Diagnostics'); await section('Read charger logs').getByRole('button',{name:'Read logs'}).click(); await idle();
  assert.equal(await page.evaluate(() => calls.find(c => c.service_data?.resource === 'logs').service_data.log_from),10);
  await tab('Charger'); await section('Charger name').locator('[name=name]').fill('Driveway'); await section('Charger name').getByRole('button',{name:'Save',exact:true}).click(); await idle();
  // Untrusted server content must be rendered as text, never HTML.
  await page.evaluate(() => { fixtures.sessions.data[0].chargeFinishReason = '<img src=x onerror="window.injected=1">'; });
  await tab('History & costs'); assert.equal(await page.locator('chargersync-card img').count(),0);
  assert.equal(await page.evaluate(() => window.injected),undefined);
  // An optional currency failure must preserve history and usable controls.
  await page.evaluate(() => { window.failResource = 'currencies'; });
  await page.getByRole('button',{name:'Refresh',exact:true}).click(); await idle();
  assert.match(await page.locator('.stats').innerText(),/12\.50 kWh/);
  assert.match(await page.locator('[role=alert]').innerText(),/temporarily unavailable/);
  await page.evaluate(() => { window.failResource = undefined; });
  await tab('Schedules');
  if (process.env.CHARGERSYNC_SCREENSHOT) await page.screenshot({path:process.env.CHARGERSYNC_SCREENSHOT,fullPage:true});
  await page.setViewportSize({width:390,height:844});
  assert.equal(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth),true);
  if (process.env.CHARGERSYNC_CALLS) fs.writeFileSync(process.env.CHARGERSYNC_CALLS,JSON.stringify(await page.evaluate(() => calls.filter(c => c.service)),null,2));
  assert.deepEqual(errors,[]);
  await browser.close();
  console.log('Browser checks passed: all 8 sections, forms, service payloads, cancellation, partial failures, XSS and mobile layout.');
})().catch(error => { console.error(error); process.exit(1); });
