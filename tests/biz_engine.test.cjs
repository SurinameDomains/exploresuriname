// Business tools engine tests. Run: node --test tests/
// These run in CI (update.yml) BEFORE generate.py. A failure stops the deploy,
// so a wrong rule or engine change can never reach the live site.
'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const path = require('node:path');
const fs = require('node:fs');
const E = require(path.join(__dirname, '..', 'biz_engine.js'));
const R = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'business_rules.json'), 'utf8'));

// Holiday table exactly as business_pages.py builds it
function holidays() {
  const H = { dates: {}, complete: {}, incomplete: {} };
  const base = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'holidays.json'), 'utf8'));
  H.complete[String(base.year)] = true;
  for (const h of base.public) H.dates[h.date] = h.name_nl;
  const extra = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'data', 'biz_holidays_extra.json'), 'utf8'));
  for (const [y, v] of Object.entries(extra.years)) {
    if (H.complete[y]) continue;
    if (v.incomplete) H.incomplete[y] = v.missing_note; else H.complete[y] = true;
    for (const h of v.public) H.dates[h.date] = h.name_nl;
  }
  return H;
}
const c = (srd) => Math.round(srd * 100);

// ── Salary: vectors captured live from Celery and calculator.tax.sr (27 Sep 2026)
const VECTORS = [
  { src: 'Celery 2026', gross: 20000, apf: 8,   med: false, pens: 200.00, aov: 776.00, tax: 1862.00, fvo: 100.00, net: 17062.00 },
  { src: 'Celery 2024', gross: 20000, apf: 7.5, med: false, pens: 187.50, aov: 776.50, tax: 1865.50, fvo: 100.00, net: 17070.50 },
  { src: 'Celery 2026', gross: 3000,  apf: 8,   med: false, pens: 120.00, aov: 110.59, tax: 0.00,    fvo: 15.00,  net: 2754.41 },
  { src: 'Celery 2026', gross: 10616, apf: 8,   med: false, pens: 200.00, aov: 400.64, tax: 81.28,   fvo: 53.08,  net: 9881.00 },
  { src: 'Celery 2026', gross: 60000, apf: 8,   med: false, pens: 200.00, aov: 2376.00, tax: 17052.00, fvo: 300.00, net: 40072.00 },
  { src: 'tax.sr 2026', gross: 20000, apf: 8.5, med: true,  pens: 212.50, aov: 776.17, tax: 1863.17, fvo: 100.00, net: 17048.16 },
];
for (const v of VECTORS) {
  test(`salary ${v.src} gross ${v.gross}`, () => {
    const r = E.salary({ gross: c(v.gross), apfPct: v.apf, medical: v.med }, R, '2026-09-27');
    assert.equal(r.pensionEmp, c(v.pens), 'pension');
    assert.equal(r.aov, c(v.aov), 'aov');
    assert.equal(r.tax, c(v.tax), 'wage tax');
    assert.equal(r.fvoEmp, c(v.fvo), 'fvo');
    assert.equal(r.net, c(v.net), 'net');
  });
}
test('salary: tax.sr published example (no pension, medical on) tax = 1934.33', () => {
  const r = E.salary({ gross: c(20000), medical: true, noPension: true }, R, '2026-09-27');
  assert.equal(r.tax, c(1934.33));
});
test('salary: default APF is latest published (8% for 2025) on a 2026 date', () => {
  assert.equal(E.apfDefault(R, '2026-09-27').pct_total, 8.0);
  assert.equal(E.apfDefault(R, '2024-06-01').pct_total, 7.5);
});
test('salary: age 60+ pays no AOV', () => {
  assert.equal(E.salary({ gross: c(20000), apfPct: 8, age60: true }, R, '2026-09-27').aov, 0);
});
test('salary: pension base floor 500 and cap 5000', () => {
  assert.equal(E.salary({ gross: c(300), apfPct: 8 }, R, '2026-09-27').pensionBase, c(500));
  assert.equal(E.salary({ gross: c(9000), apfPct: 8 }, R, '2026-09-27').pensionBase, c(5000));
});
test('salary: overtime uses its own table (from 1 Jul 2025) and AOV applies', () => {
  const a = E.salary({ gross: c(20000), apfPct: 8 }, R, '2026-09-27');
  const b = E.salary({ gross: c(20000), apfPct: 8, overtime: c(3000) }, R, '2026-09-27');
  assert.equal(b.overtimeTax, c(2500 * 0.05 + 500 * 0.15));      // 125 + 75 = 200
  assert.equal(b.tax, a.tax);                                      // regular tax unchanged
  assert.equal(b.aov - a.aov, c(120));                             // 4% of 3000
  const old = E.salary({ gross: c(20000), apfPct: 8, overtime: c(3000) }, R, '2025-06-15');
  assert.equal(old.overtimeTax, c(500 * 0.05 + 600 * 0.15 + 1900 * 0.25)); // 25+90+475 = 590
});
test('salary: child allowance tax-free up to 125/child, max 500', () => {
  const r = E.salary({ gross: c(20000), apfPct: 8, childAllow: c(700), children: 5 }, R, '2026-09-27');
  assert.equal(r.childTaxable, c(200));
});
test('salary: bracket edges', () => {
  // zuiver exactly 9000 -> tax 0; +3500 -> 280
  for (const [z, t] of [[9000, 0], [12500, 280], [16000, 910], [19500, 1890], [20500, 2270]]) {
    assert.equal(E.bands(c(z - 9000), R.wage_tax[0].bands_month), c(t), 'zuiver ' + z);
  }
});
test('salary: net -> gross round trip', () => {
  for (const g of [3000, 10616, 15000.37, 20000, 47000, 60000]) {
    const net = E.salary({ gross: c(g), apfPct: 8 }, R, '2026-09-27').net;
    const back = E.grossForNet(net, { apfPct: 8 }, R, '2026-09-27');
    const again = E.salary({ gross: back, apfPct: 8 }, R, '2026-09-27').net;
    assert.ok(again >= net && again - net <= 2, `gross ${g}: ${back} gives ${again} vs ${net}`);
    assert.ok(back <= c(g), 'never above the original gross');
  }
});
test('salary: huge salaries do not overflow', () => {
  const r = E.salary({ gross: c(50000000), apfPct: 8 }, R, '2026-09-27');
  assert.ok(r.net > 0 && r.net < c(50000000));
});

// ── amount parsing / formatting
test('parseAmount: money rule (3 digits = thousands, 1-2 digits = decimals)', () => {
  const cases = [
    ['1.234,56', 123456], ['1,234.56', 123456], ['1234,5', 123450], ['1234.5', 123450], ['1234,56', 123456],
    ['1.000.000', 100000000], ['SRD 20.000', 2000000], ['20000', 2000000], ['1 234', 123400], ['1.000', 100000],
    ['1,234', 123400], ['1.234', 123400], ['12.500', 1250000], ['12,50', 1250], ['0,50', 50], ['0,5', 50],
    ['12,345.678', 1234568], ['1.234.567,89', 123456789], ['1,234,567.89', 123456789],
    ['', null], ['abc', null], ['-50', -5000], ['1.2.3', null], ['1,23,456', null], ['0.005', 1],
  ];
  for (const [s, v] of cases) assert.equal(E.parseAmount(s), v, s);
});
test('parseNum: one separator is decimal', () => {
  assert.equal(E.parseNum('37,8525'), 37.8525); assert.equal(E.parseNum('37.8525'), 37.8525);
  assert.equal(E.parseNum('37,365'), 37.365); assert.equal(E.parseNum('8,5'), 8.5); assert.equal(E.parseNum('8.5'), 8.5);
  assert.equal(E.parseNum('1.000.000'), 1000000); assert.equal(E.parseNum('1.234,5'), 1234.5); assert.equal(E.parseNum('x'), null);
  assert.equal(E.parseNum('12'), 12);
});
test('fmt uses Surinamese/Dutch style for nl and es, US style for en', () => {
  assert.equal(E.fmt(123456789, 'nl'), '1.234.567,89');
  assert.equal(E.fmt(123456789, 'es'), '1.234.567,89');
  assert.equal(E.fmt(123456789, 'en'), '1,234,567.89');
});

// ── BTW
test('BTW excl/incl and round trip at every rate', () => {
  assert.deepEqual(E.btwFromExcl(c(1000), 10), { excl: c(1000), btw: c(100), incl: c(1100) });
  assert.deepEqual(E.btwFromIncl(c(1100), 10), { excl: c(1000), btw: c(100), incl: c(1100) });
  assert.equal(E.btwFromIncl(c(105), 5).excl, c(100));
  assert.equal(E.btwFromIncl(c(125), 25).excl, c(100));
  for (let x = 1; x < 5000; x += 37) for (const r of [0, 5, 10, 25]) {
    const f = E.btwFromExcl(x, r); assert.equal(f.incl, f.excl + f.btw);
    const b = E.btwFromIncl(f.incl, r); assert.ok(Math.abs(b.excl - x) <= 1);
  }
});
test('BTW lines group per rate', () => {
  const r = E.btwLines([{ amount: c(100), rate: 10, qty: 2 }, { amount: c(50), rate: 5 }, { amount: c(110), rate: 10, incl: true }]);
  assert.equal(r.excl, c(350)); assert.equal(r.btw, c(32.5)); assert.equal(r.incl, c(382.5));
  assert.equal(r.groups[0].rate, 10);
});
test('BTW penalty per S.B. 2025 no. 140', () => {
  assert.equal(E.monthsLate('2026-10-15', '2026-10-15'), 0);
  assert.equal(E.monthsLate('2026-10-15', '2026-10-16'), 1);   // one day late = one month
  assert.equal(E.monthsLate('2026-10-15', '2026-11-15'), 1);
  assert.equal(E.monthsLate('2026-10-15', '2026-11-16'), 2);
  assert.equal(E.monthsLate('2026-10-15', '2027-06-01'), 8);
  const p = E.btwPenalty('2026-10-15', '2026-12-20', c(4000), R);
  assert.equal(p.months, 3); assert.equal(p.filing, c(7500)); assert.equal(p.payment, c(2000));
  assert.equal(E.btwPenalty('2026-10-15', '2027-06-01', c(100000), R).filing, c(10000));
  assert.equal(E.btwPenalty('2026-10-15', '2027-06-01', c(100000), R).payment, c(10000)); // capped
});

// ── dates / deadlines
const H = holidays();
test('holidays: 2026 complete, 2027 flagged incomplete', () => {
  assert.equal(E.coverage('2026-05-01', H), 'complete');
  assert.equal(E.coverage('2027-03-01', H), 'incomplete');
  assert.equal(E.coverage('2028-03-01', H), 'unknown');
  assert.equal(E.isWorkingDay('2026-11-25', H), false);   // Independence Day
  assert.equal(E.isWorkingDay('2027-03-29', H), false);   // Easter Monday 2027
  assert.equal(E.isWorkingDay('2026-09-28', H), true);
});
test('deadlines: BTW before the 16th, wage tax 7th working day but never after the 10th, APF 15th', () => {
  const expect = [
    [2026, 9,  '2026-10-15', '2026-10-09'],
    [2026, 10, '2026-11-15', '2026-11-10'],
    [2026, 11, '2026-12-15', '2026-12-09'],
    [2026, 12, '2027-01-15', '2027-01-10'],   // 7th working day is 12 Jan (1 Jan holiday); portal window closes on the 10th
    [2026, 7,  '2026-08-15', '2026-08-10'],   // 7th working day would be 11 Aug
    [2027, 2,  '2027-03-15', '2027-03-09'],
  ];
  for (const [y, m, btw, lb] of expect) {
    const d = E.monthlyDeadlines(y, m, R, H);
    assert.equal(d.btw, btw, `btw ${y}-${m}`); assert.equal(d.wageTax, lb, `lb ${y}-${m}`);
    assert.equal(d.apf, btw.slice(0, 8) + '15');
  }
});
test('working days: add and count skip weekends and holidays', () => {
  assert.equal(E.addWorkingDays('2026-11-20', 3, H).date, '2026-11-26'); // skips 25 Nov
  assert.equal(E.countWorkingDays('2026-12-21', '2026-12-31', H).count, 8); // 21-24, 28-31 (25 Dec off, 26 = Sat)
  assert.equal(E.addWorkingDays('2026-12-30', 5, H).coverage, 'incomplete');
});

// ── vacation
test('vacation days per Vakantiewet art. 7', () => {
  assert.deepEqual([1, 2, 3, 4, 10].map(y => E.vacationDays(y, R)), [12, 14, 16, 18, 18]);
  assert.equal(E.vacationPartial(7, R), 7);
  assert.equal(E.vacationOnTermination(18, 6), 9);
  assert.equal(E.vacationAllowance(12, c(500), R), c(3000));
});

// ── income tax (persons)
test('income tax bands (Wet IB art. 34) and AOV', () => {
  const r = E.incomeTax(c(200000), false, R, '2026-09-27');
  // 0 on 108k, 8% of 42k = 3360, 18% of 42k = 7560, 28% of 8k = 2240 -> 13160
  assert.equal(r.tax, c(13160)); assert.equal(r.aov, c(8000));
  assert.equal(E.incomeTax(c(100000), true, R, '2026-09-27').total, 0);
});

// ── import / pricing / loan / cash
test('import landed cost: BTW over CIF + duty + excise + stat + consent', () => {
  const r = E.importCost({ cifForeign: c(1000), rate: 37.5, dutyPct: 20, statPct: 0.5, consentPct: 1.5, btwPct: 10, qty: 10 });
  assert.equal(r.cif, c(37500)); assert.equal(r.duty, c(7500)); assert.equal(r.stat, c(187.5)); assert.equal(r.consent, c(562.5));
  assert.equal(r.btw, c(4575)); assert.equal(r.total, c(50325)); assert.equal(r.perUnit, c(5032.5));
});
test('pricing: markup vs margin', () => {
  const m = E.price({ cost: c(100), rate: 1, mode: 'markup', pct: 25, btwPct: 10 });
  assert.equal(m.excl, c(125)); assert.equal(m.incl, c(137.5));
  const g = E.price({ cost: c(100), rate: 1, mode: 'margin', pct: 20, btwPct: 0 });
  assert.equal(g.excl, c(125)); assert.equal(E.price({ cost: c(1), rate: 1, mode: 'margin', pct: 100 }), null);
});
test('loan annuity: 100.000 at 12% over 12 months', () => {
  const l = E.loan(c(100000), 12, 12);
  assert.equal(l.payment, c(8884.88));
  assert.equal(l.rows[11].balance, 0);
  assert.ok(Math.abs(l.totalInterest - c(6618.55)) <= 2);
});
test('cash counter with official denominations', () => {
  const d = [...R.cash[0].notes, ...R.cash[0].coins];
  assert.equal(E.cashTotal({ '500': 2, '20': 3, '2.5': 4, '0.25': 3, '0.01': 7 }, d), c(1000 + 60 + 10 + 0.75 + 0.07));
});

// ── words / codes / QR payloads
test('amount in words (Dutch, Taalunie spelling)', () => {
  const t = [
    [c(1250.50), 'Duizend tweehonderdvijftig Surinaamse dollar en vijftig cent'],
    [c(22), 'Tweeëntwintig Surinaamse dollar'],
    [c(33), 'Drieëndertig Surinaamse dollar'],
    [c(101), 'Honderdeen Surinaamse dollar'],
    [c(1), 'Één Surinaamse dollar'],
    [c(2001), 'Tweeduizend een Surinaamse dollar'],
    [c(19500), 'Negentienduizend vijfhonderd Surinaamse dollar'],
    [c(1000000), 'Een miljoen Surinaamse dollar'],
    [c(2345678.01), 'Twee miljoen driehonderdvijfenveertigduizend zeshonderdachtenzeventig Surinaamse dollar en één cent'],
    [0, 'Nul Surinaamse dollar'],
  ];
  for (const [v, w] of t) assert.equal(E.amountInWords(v, 'nl'), w);
  assert.equal(E.amountInWords(c(1250.5), 'en'), 'One thousand two hundred and fifty Surinamese dollars and fifty cents');
  assert.equal(E.amountInWords(c(1), 'en'), 'One Surinamese dollar');
  assert.equal(E.amountInWords(c(250.05), 'nl', 'USD'), 'Tweehonderdvijftig Amerikaanse dollar en vijf cent');
  assert.equal(E.amountInWords(c(3), 'en', 'EUR'), 'Three euros');
  assert.equal(E.amountInWords(c(115), 'en'), 'One hundred and fifteen Surinamese dollars');
  assert.equal(E.amountInWords(c(1005), 'en'), 'One thousand and five Surinamese dollars');
});
test('EAN-13 check digit', () => {
  assert.equal(E.ean13Check('400638133393'), 1);
  assert.equal(E.ean13Check('871125300120'), 2);
  assert.equal(E.ean13Check('12345'), null);
});
test('QR payloads', () => {
  assert.equal(E.wifiPayload('Winkel;Wifi', 'ab:c"1', 'WPA', false), 'WIFI:T:WPA;S:Winkel\\;Wifi;P:ab\\:c\\"1;;');
  assert.equal(E.wifiPayload('Gast', '', 'nopass', false), 'WIFI:T:nopass;S:Gast;;');
  assert.equal(E.waNumber('+597 812-3456'), '5978123456');
  assert.equal(E.waNumber('8123456'), '5978123456');
  assert.ok(E.vcardPayload({ first: 'Anna', last: 'Doe', tel: '+597 8123456' }).includes('TEL;TYPE=CELL:+5978123456'));
});
test('timesheet shift minutes', () => {
  assert.equal(E.shiftMinutes('07:30', '16:00', 30), 480);
  assert.equal(E.shiftMinutes('22:00', '06:00', 0), 480);
  assert.equal(E.shiftMinutes('7', '16:00', 0), null);
});

// ── rules file integrity
test('rules file: every dated rule has from/source/url/verified and lists are sorted', () => {
  for (const [k, v] of Object.entries(R)) {
    if (!Array.isArray(v) || !v.length || typeof v[0] !== 'object' || !('from' in v[0])) continue;
    let prev = '';
    for (const e of v) {
      assert.match(e.from, /^\d{4}-\d{2}-\d{2}$/, k);
      assert.ok(e.from > prev, `${k} sorted`); prev = e.from;
      for (const f of ['source', 'url', 'verified', 'tier']) assert.ok(e[f], `${k}.${f}`);
    }
  }
});
