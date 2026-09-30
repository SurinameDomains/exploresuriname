/* Explore Suriname — Business tools engine.
 *
 * Pure calculation functions, no DOM. Inlined into every Business tool page by
 * business_pages.py and unit-tested by tests/biz_engine.test.cjs (run in CI
 * before generate.py; a failing test stops the deploy).
 *
 * Money is handled in INTEGER CENTS and percentages in BASIS POINTS so there is
 * no floating-point drift. Rounding is half-up per line item, which is what the
 * Surinamese payroll engines we validated against (Celery, tax.sr) do.
 *
 * All legal parameters come from data/business_rules.json (passed in as `R`).
 * Nothing legal is hard-coded here.
 */
(function (root) {
  'use strict';

  // ── integer money helpers ────────────────────────────────────────────────
  function bp(pct) { return Math.round(Number(pct) * 100); }          // 8.5 -> 850
  // round(num/den) half-up (away from zero for negatives), integers in, integer out
  function divRound(num, den) {
    if (den === 0) return 0;
    var neg = (num < 0) !== (den < 0);
    var n = Math.abs(num), d = Math.abs(den);
    var q = Math.floor((2 * n + d) / (2 * d));
    return neg ? -q : q;
  }
  function pctOf(cents, pct) { return divRound(cents * bp(pct), 10000); }
  function toCents(n) { return Math.round(Number(n) * 100); }          // only for trusted JSON numbers
  function min(a, b) { return a < b ? a : b; }
  function int(x) { var n = Number(x); return isFinite(n) ? Math.trunc(n) : 0; }
  function max(a, b) { return a > b ? a : b; }

  // Parse a user-typed MONEY amount into cents. Accepts "1.234,56", "1,234.56",
  // "1234,5", "1234.5", "1 234", "SRD 1.000", "1.000.000", "12.500".
  // Money rule (same in every language, because amounts never have 3 decimals):
  // a separator followed by exactly 3 digits is a thousands separator, a
  // separator followed by 1-2 digits is the decimal separator. With both "."
  // and "," present, the last one is the decimal separator.
  function parseAmount(str) {
    if (str === null || str === undefined) return null;
    var s = String(str).replace(/[^\d.,\-]/g, '');
    if (!s || !/\d/.test(s)) return null;
    var neg = s.charAt(0) === '-';
    s = s.replace(/-/g, '');
    var lastDot = s.lastIndexOf('.'), lastComma = s.lastIndexOf(',');
    var intPart, fracPart = '';
    function isGroups(t, sep) {
      var parts = t.split(sep);
      if (parts.length < 2 || !/^[1-9]\d{0,2}$/.test(parts[0])) return false;
      for (var i = 1; i < parts.length; i++) if (!/^\d{3}$/.test(parts[i])) return false;
      return true;
    }
    if (lastDot >= 0 && lastComma >= 0) {
      var dec = lastDot > lastComma ? '.' : ',';
      var thou = dec === '.' ? ',' : '.';
      var cut = s.lastIndexOf(dec);
      intPart = s.slice(0, cut);
      if (intPart.indexOf(dec) >= 0) return null;
      if (!isGroups(intPart, thou) && intPart.indexOf(thou) >= 0) return null;
      intPart = intPart.split(thou).join('');
      fracPart = s.slice(cut + 1);
    } else if (lastDot >= 0 || lastComma >= 0) {
      var sep = lastDot >= 0 ? '.' : ',';
      if (isGroups(s, sep)) {
        intPart = s.split(sep).join('');
      } else if (s.split(sep).length === 2) {
        var c = s.lastIndexOf(sep);
        intPart = s.slice(0, c);
        fracPart = s.slice(c + 1);
      } else {
        return null;
      }
    } else {
      intPart = s;
    }
    if (intPart === '') intPart = '0';
    if (!/^\d+$/.test(intPart) || (fracPart && !/^\d+$/.test(fracPart))) return null;
    var frac3 = (fracPart + '000').slice(0, 3);
    var cents = parseInt(intPart, 10) * 100 + parseInt(frac3.slice(0, 2), 10) + (parseInt(frac3.charAt(2), 10) >= 5 ? 1 : 0);
    if (!isFinite(cents) || cents > 1e13) return null;
    return neg ? -cents : cents;
  }

  // Parse a plain decimal number (exchange rates, hours, percentages, quantities).
  // One separator = decimal ("37,365" and "37.365" are both 37.365); several
  // identical separators = thousands grouping ("1.000.000"); with both, the last
  // one is the decimal separator.
  function parseNum(str) {
    if (str === null || str === undefined) return null;
    var s = String(str).replace(/[^\d.,\-]/g, '');
    if (!s || !/\d/.test(s)) return null;
    var lastDot = s.lastIndexOf('.'), lastComma = s.lastIndexOf(',');
    var t;
    if (lastDot >= 0 && lastComma >= 0) {
      var dec = lastDot > lastComma ? '.' : ',';
      var thou = dec === '.' ? ',' : '.';
      t = s.split(thou).join('').replace(dec, '.');
    } else if (lastDot >= 0 || lastComma >= 0) {
      var sep = lastDot >= 0 ? '.' : ',';
      var n = s.split(sep).length - 1;
      t = n === 1 ? s.replace(sep, '.') : s.split(sep).join('');
    } else t = s;
    if (!/^-?\d*\.?\d+$/.test(t) && !/^-?\d+\.?$/.test(t)) return null;
    var v = Number(t);
    return isFinite(v) ? v : null;
  }

  // Chinese uses the same 1,234.56 grouping as English; NL/ES use 1.234,56.
  function locale(lang) { return (lang === 'en' || lang === 'zh') ? 'en-US' : 'nl-NL'; }
  function fmt(cents, lang) {
    if (cents === null || cents === undefined || isNaN(cents)) return '–';
    return new Intl.NumberFormat(locale(lang), { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(cents / 100);
  }
  function fmtNum(n, lang, dec) {
    if (n === null || n === undefined || isNaN(n)) return '–';
    var d = dec === undefined ? 2 : dec;
    return new Intl.NumberFormat(locale(lang), { minimumFractionDigits: 0, maximumFractionDigits: d }).format(n);
  }

  // ── rules lookup ──────────────────────────────────────────────────────────
  // Pick the entry of an effective-dated list that applies on `iso` (YYYY-MM-DD).
  function pick(list, iso) {
    var best = null;
    for (var i = 0; i < list.length; i++) {
      if (list[i].from <= iso && (!best || list[i].from >= best.from)) best = list[i];
    }
    return best;
  }

  // Progressive bands: bands = [[width, pct], ..., [null, pct]] (width null = rest)
  // returns tax in cents, computed exactly then rounded once.
  function bands(amountCents, bandList) {
    if (amountCents <= 0) return 0;
    var rest = amountCents, acc = 0;
    for (var i = 0; i < bandList.length && rest > 0; i++) {
      var w = bandList[i][0] === null ? rest : min(rest, toCents(bandList[i][0]));
      acc += w * bp(bandList[i][1]);
      rest -= w;
    }
    return divRound(acc, 10000);
  }

  // ── salary ────────────────────────────────────────────────────────────────
  function apfDefault(R, iso) { return pick(R.apf, iso); }

  /* inp: {gross, overtime, taxableAllow, untaxedAllow, childAllow, children,
           medical(bool), age60(bool), apfPct, apfEmployerPct, bzv, bzvEmployerPct}
     all money in cents. */
  function salary(inp, R, iso) {
    var wt = pick(R.wage_tax, iso), ot = pick(R.overtime_tax, iso), tf = pick(R.tax_free, iso);
    var aovR = pick(R.aov, iso), fvoR = pick(R.fvo, iso), ac = R.apf_common;
    var gross = max(0, int(inp.gross));
    var overtime = max(0, int(inp.overtime));
    var taxAllow = max(0, int(inp.taxableAllow));
    var freeAllow = max(0, int(inp.untaxedAllow));
    var childAllow = max(0, int(inp.childAllow));
    var children = max(0, int(inp.children));
    var apfPct = (inp.apfPct === null || inp.apfPct === undefined) ? apfDefault(R, iso).pct_total : inp.apfPct;
    var erShare = (inp.apfEmployerPct === null || inp.apfEmployerPct === undefined) ? ac.employer_min_share_pct : inp.apfEmployerPct;

    var base = min(max(gross, toCents(ac.base_min_month)), toCents(ac.base_max_month));
    if (inp.noPension) base = 0;
    var pensTotal = pctOf(base, apfPct);
    // employee part rounded half-up first (matches Celery / tax.sr), employer pays the rest
    var pensEmp = divRound(pensTotal * (10000 - bp(erShare)), 10000);
    var pensEr = pensTotal - pensEmp;

    var childFree = min(children * toCents(tf.child_allowance_per_child_month), toCents(tf.child_allowance_max_month));
    var childTaxable = max(0, childAllow - childFree);

    var medical = 0;
    if (inp.medical) {
      var medYear = min(pctOf(gross * 12, tf.medical_pct_of_year_wage), toCents(tf.medical_max_year));
      medical = divRound(medYear, 12);
    }

    var loon = gross + taxAllow + childTaxable + medical - pensEmp;
    var forfait = min(pctOf(max(0, loon), wt.forfait_pct), toCents(wt.forfait_max_month));
    var zuiver = loon - forfait;
    var aov = inp.age60 ? 0 : pctOf(max(0, zuiver + overtime), aovR.pct);
    var taxable = max(0, zuiver - toCents(wt.tax_free_month));
    var tax = bands(taxable, wt.bands_month);
    var otTax = bands(overtime, ot.bands_month);
    var fvoEmp = pctOf(gross, fvoR.employee_max_pct);
    var fvoEr = pctOf(gross, fvoR.pct_total) - fvoEmp;
    var bzv = max(0, int(inp.bzv));
    var bzvEmp = divRound(bzv * (10000 - bp(inp.bzvEmployerPct === undefined || inp.bzvEmployerPct === null ? 50 : inp.bzvEmployerPct)), 10000);
    var bzvEr = bzv - bzvEmp;

    var cashIn = gross + taxAllow + freeAllow + childAllow + overtime;
    var deductions = pensEmp + aov + tax + otTax + fvoEmp + bzvEmp;
    var net = cashIn - deductions;
    var employerCost = cashIn + pensEr + fvoEr + bzvEr;

    return {
      gross: gross, overtime: overtime, taxableAllow: taxAllow, untaxedAllow: freeAllow,
      childAllow: childAllow, childTaxable: childTaxable, medical: medical,
      apfPct: apfPct, apfEmployerPct: erShare, pensionBase: base,
      pensionTotal: pensTotal, pensionEmp: pensEmp, pensionEr: pensEr,
      loon: loon, forfait: forfait, zuiver: zuiver, taxable: taxable,
      aov: aov, tax: tax, overtimeTax: otTax, fvoEmp: fvoEmp, fvoEr: fvoEr,
      bzvEmp: bzvEmp, bzvEr: bzvEr, cashIn: cashIn, deductions: deductions,
      net: net, employerCost: employerCost,
      flags: {
        overtimeForfaitNote: overtime > 0 && loon < toCents(wt.forfait_max_month) * 100 / wt.forfait_pct,
        pensionCapped: gross > toCents(ac.base_max_month),
        belowMinBase: gross > 0 && gross < toCents(ac.base_min_month)
      }
    };
  }

  // Find the smallest gross that yields at least `targetNet` (all else equal).
  function grossForNet(targetNet, inp, R, iso) {
    var lo = 0, hi = max(targetNet * 3, 100000), guard = 0;
    function netAt(g) { var o = {}; for (var k in inp) o[k] = inp[k]; o.gross = g; return salary(o, R, iso).net; }
    while (netAt(hi) < targetNet && guard++ < 40) hi *= 2;
    while (lo < hi) {
      var mid = Math.floor((lo + hi) / 2);
      if (netAt(mid) >= targetNet) hi = mid; else lo = mid + 1;
    }
    return lo;
  }

  // ── BTW ───────────────────────────────────────────────────────────────────
  function btwFromExcl(excl, rate) { var b = pctOf(excl, rate); return { excl: excl, btw: b, incl: excl + b }; }
  function btwFromIncl(incl, rate) {
    var excl = divRound(incl * 10000, 10000 + bp(rate));
    return { excl: excl, btw: incl - excl, incl: incl };
  }
  // lines: [{amount(cents), rate, qty(number, default 1), incl(bool)}]
  // BTW is calculated per rate over the summed excl amounts (one BTW line per rate).
  function btwLines(lines) {
    var byRate = {}, order = [];
    for (var i = 0; i < lines.length; i++) {
      var l = lines[i];
      if (l.amount === null || l.amount === undefined || isNaN(l.amount)) continue;
      var q = (l.qty === undefined || l.qty === null || isNaN(l.qty)) ? 1 : l.qty;
      var gross = Math.round(l.amount * q);
      var excl = l.incl ? btwFromIncl(gross, l.rate).excl : gross;
      if (!(l.rate in byRate)) { byRate[l.rate] = 0; order.push(l.rate); }
      byRate[l.rate] += excl;
    }
    var groups = [], tE = 0, tB = 0;
    order.sort(function (a, b) { return b - a; });
    for (var j = 0; j < order.length; j++) {
      var r = order[j], e = byRate[r], b = pctOf(e, r);
      groups.push({ rate: r, excl: e, btw: b, incl: e + b });
      tE += e; tB += b;
    }
    return { groups: groups, excl: tE, btw: tB, incl: tE + tB };
  }

  // ── dates ─────────────────────────────────────────────────────────────────
  function isoToUTC(iso) { var p = iso.split('-'); return Date.UTC(+p[0], +p[1] - 1, +p[2]); }
  function utcToIso(t) { var d = new Date(t); return d.getUTCFullYear() + '-' + pad2(d.getUTCMonth() + 1) + '-' + pad2(d.getUTCDate()); }
  function pad2(n) { return (n < 10 ? '0' : '') + n; }
  function addDays(iso, n) { return utcToIso(isoToUTC(iso) + n * 86400000); }
  function weekday(iso) { return new Date(isoToUTC(iso)).getUTCDay(); } // 0 Sun .. 6 Sat
  function daysBetween(a, b) { return Math.round((isoToUTC(b) - isoToUTC(a)) / 86400000); }

  // H = {dates: {"2026-01-01": "Nieuwjaarsdag", ...}, complete: {"2026": true}, incomplete: {"2027": "note"}}
  function isWorkingDay(iso, H) { var w = weekday(iso); return w !== 0 && w !== 6 && !(H.dates && H.dates[iso]); }
  function coverage(iso, H) {
    var y = iso.slice(0, 4);
    if (H.complete && H.complete[y]) return 'complete';
    if (H.incomplete && H.incomplete[y]) return 'incomplete';
    return 'unknown';
  }
  // n working days AFTER start (start itself not counted); n may be 0
  function addWorkingDays(startIso, n, H) {
    var d = startIso, c = 0, touched = {};
    touched[coverage(d, H)] = true;
    while (c < n) { d = addDays(d, 1); touched[coverage(d, H)] = true; if (isWorkingDay(d, H)) c++; }
    return { date: d, coverage: touched.unknown ? 'unknown' : (touched.incomplete ? 'incomplete' : 'complete') };
  }
  // working days in [a, b] inclusive
  function countWorkingDays(a, b, H) {
    if (b < a) { var t = a; a = b; b = t; }
    var d = a, c = 0, touched = {};
    for (var i = 0; i < 4000; i++) {
      touched[coverage(d, H)] = true;
      if (isWorkingDay(d, H)) c++;
      if (d === b) break;
      d = addDays(d, 1);
    }
    return { count: c, coverage: touched.unknown ? 'unknown' : (touched.incomplete ? 'incomplete' : 'complete') };
  }
  function nthWorkingDayOfMonth(year, month, n, H) {
    var d = year + '-' + pad2(month) + '-01', c = 0;
    for (var i = 0; i < 40; i++) {
      if (isWorkingDay(d, H)) { c++; if (c === n) return d; }
      d = addDays(d, 1);
    }
    return null;
  }

  // Deadlines for obligations that concern `month` (1-12) of `year` (the period).
  function monthlyDeadlines(year, month, R, H) {
    var ny = month === 12 ? year + 1 : year, nm = month === 12 ? 1 : month + 1;
    var dl = R.deadlines;
    var btwDay = ny + '-' + pad2(nm) + '-' + pad2(dl.btw.day - 1);
    // Earliest of the nth working day (Wet LB art. 20) and the end of the portal window (the 10th).
    var lb = nthWorkingDayOfMonth(ny, nm, dl.wage_tax.n, H);
    if (dl.wage_tax.portal_last_day) { var cap = ny + '-' + pad2(nm) + '-' + pad2(dl.wage_tax.portal_last_day); if (!lb || cap < lb) lb = cap; }
    var apf = ny + '-' + pad2(nm) + '-' + pad2(dl.apf.day);
    return {
      btw: btwDay,
      wageTax: lb,
      wageTaxCoverage: coverage(ny + '-' + pad2(nm) + '-01', H),
      apf: apf
    };
  }

  // BTW late-filing penalty (S.B. 2025 no. 140). dueIso = last allowed day.
  function monthsLate(dueIso, filedIso) {
    if (filedIso <= dueIso) return 0;
    var a = dueIso.split('-').map(Number), b = filedIso.split('-').map(Number);
    var m = (b[0] - a[0]) * 12 + (b[1] - a[1]) + (b[2] > a[2] ? 1 : 0);
    return max(1, m);
  }
  function btwPenalty(dueIso, filedIso, unpaidCents, R, iso) {
    var P = pick(R.btw_penalties, iso || filedIso);
    if (!P) return null;
    var m = monthsLate(dueIso, filedIso);
    var list = P.late_filing_by_month;
    var filing = m === 0 ? 0 : toCents(list[min(m, list.length) - 1]);
    var payment = unpaidCents > 0 && m > 0 ? min(pctOf(unpaidCents, P.late_payment_pct), toCents(P.late_payment_max)) : 0;
    return { months: m, filing: filing, payment: payment, total: filing + payment };
  }

  // ── vacation (Vakantiewet 1975) ───────────────────────────────────────────
  function vacationDays(fullYears, R) {
    var V = R.vacation[R.vacation.length - 1];
    if (fullYears < 1) return 0;
    return min(V.first_year_days + V.increase_per_year * (fullYears - 1), V.max_days);
  }
  function vacationPartial(fullMonths, R) {
    var V = R.vacation[R.vacation.length - 1];
    return max(0, min(12, fullMonths | 0)) * V.partial_year_days_per_full_month;
  }
  // termination (art. 12): twelfths of the year's entitlement for full months served this year
  function vacationOnTermination(entitlementDays, fullMonthsThisYear) {
    return entitlementDays * max(0, min(12, fullMonthsThisYear)) / 12;
  }
  function vacationAllowance(days, dailyWageCents, R) {
    var V = R.vacation[R.vacation.length - 1];
    return Math.round(days * dailyWageCents * V.allowance_fraction_of_daily_wage);
  }

  // ── income tax (self-employed, persons) ───────────────────────────────────
  function incomeTax(profitYearCents, age60, R, iso) {
    var IB = pick(R.income_tax, iso), A = pick(R.aov, iso);
    var tax = bands(max(0, profitYearCents), IB.bands_year);
    var aov = age60 ? 0 : pctOf(max(0, profitYearCents), A.pct);
    return { tax: tax, aov: aov, total: tax + aov, perMonth: divRound(tax + aov, 12), perInstallment: divRound(tax, 4) };
  }

  // ── import landed cost ────────────────────────────────────────────────────
  // rate = SRD per 1 foreign unit (Number, up to 4 decimals)
  function importCost(p) {
    var r10k = Math.round(p.rate * 10000);
    var cif = divRound(p.cifForeign * r10k, 10000);
    var duty = pctOf(cif, p.dutyPct || 0);
    var stat = pctOf(cif, p.statPct || 0);
    var consent = pctOf(cif, p.consentPct || 0);
    var excise = p.excise || 0;
    var btwBase = cif + duty + excise + stat + consent;
    var btw = pctOf(btwBase, p.btwPct || 0);
    var other = p.other || 0;
    var total = btwBase + btw + other;
    var qty = p.qty && p.qty > 0 ? p.qty : 1;
    return { cif: cif, duty: duty, stat: stat, consent: consent, excise: excise, btwBase: btwBase, btw: btw,
             other: other, total: total, taxes: total - cif - other, perUnit: Math.round(total / qty),
             perUnitExBtw: Math.round((total - btw) / qty) };
  }

  // ── pricing ───────────────────────────────────────────────────────────────
  // costForeign (cents of foreign currency), rate (SRD per unit), bufferPct, mode 'markup'|'margin', pct, btwPct
  function price(p) {
    var r10k = Math.round((p.rate || 1) * 10000);
    var costSrd = divRound(p.cost * r10k, 10000);
    var costBuf = costSrd + pctOf(costSrd, p.bufferPct || 0);
    var excl;
    if (p.mode === 'margin') {
      if (p.pct >= 100) return null;
      excl = divRound(costBuf * 10000, 10000 - bp(p.pct));
    } else {
      excl = costBuf + pctOf(costBuf, p.pct || 0);
    }
    var btw = pctOf(excl, p.btwPct || 0);
    var profit = excl - costBuf;
    return { costSrd: costSrd, cost: costBuf, excl: excl, btw: btw, incl: excl + btw, profit: profit,
             marginPct: excl > 0 ? profit * 100 / excl : 0, markupPct: costBuf > 0 ? profit * 100 / costBuf : 0 };
  }

  // ── loan (annuity) ────────────────────────────────────────────────────────
  function loan(principalCents, annualPct, months) {
    if (months <= 0) return null;
    var r = annualPct / 100 / 12, pay;
    if (r === 0) pay = principalCents / months;
    else pay = principalCents * r / (1 - Math.pow(1 + r, -months));
    var payment = Math.round(pay);
    // schedule with the rounded payment; last payment absorbs the rounding
    var bal = principalCents, interest = 0, rows = [];
    for (var i = 1; i <= months; i++) {
      var it = Math.round(bal * r);
      var pr = i === months ? bal : payment - it;
      var pmt = pr + it;
      bal -= pr; interest += it;
      rows.push({ n: i, payment: pmt, interest: it, principal: pr, balance: bal });
    }
    return { payment: payment, totalInterest: interest, totalPaid: principalCents + interest, rows: rows };
  }

  // ── cash counter ──────────────────────────────────────────────────────────
  function cashTotal(counts, denominations) { // counts: {"500": 3, "2.5": 4}
    var t = 0;
    for (var i = 0; i < denominations.length; i++) {
      var d = denominations[i], c = parseInt(counts[String(d)], 10) || 0;
      t += toCents(d) * c;
    }
    return t;
  }

  // ── timesheet ─────────────────────────────────────────────────────────────
  function hm(s) { var m = /^(\d{1,2})[:.h](\d{2})$/.exec(String(s).trim()); if (!m) return null; var h = +m[1], mi = +m[2]; if (h > 24 || mi > 59) return null; return h * 60 + mi; }
  function shiftMinutes(start, end, breakMin) {
    var a = hm(start), b = hm(end);
    if (a === null || b === null) return null;
    var d = b - a; if (d < 0) d += 1440; // past midnight
    return max(0, d - (breakMin || 0));
  }

  // ── amount in words ───────────────────────────────────────────────────────
  var NL_U = ['nul', 'een', 'twee', 'drie', 'vier', 'vijf', 'zes', 'zeven', 'acht', 'negen', 'tien', 'elf', 'twaalf', 'dertien', 'veertien', 'vijftien', 'zestien', 'zeventien', 'achttien', 'negentien'];
  var NL_T = ['', '', 'twintig', 'dertig', 'veertig', 'vijftig', 'zestig', 'zeventig', 'tachtig', 'negentig'];
  function nlBelow100(n) {
    if (n < 20) return NL_U[n];
    var t = Math.floor(n / 10), u = n % 10;
    if (u === 0) return NL_T[t];
    var uw = NL_U[u];
    var join = /e$/.test(uw) ? 'ën' : 'en';   // tweeëntwintig, drieëntwintig
    return uw + join + NL_T[t];
  }
  function nlBelow1000(n) {
    var h = Math.floor(n / 100), r = n % 100, s = '';
    if (h > 0) s = (h === 1 ? '' : NL_U[h]) + 'honderd';
    if (r > 0) s += nlBelow100(r);
    return s;
  }
  // Taalunie: write together up to 'duizend'; space after 'duizend', around 'miljoen'/'miljard'.
  function nlNumber(n) {
    if (n === 0) return 'nul';
    var parts = [];
    var bil = Math.floor(n / 1e9), mil = Math.floor((n % 1e9) / 1e6), th = Math.floor((n % 1e6) / 1000), rest = n % 1000;
    if (bil) parts.push(nlBelow1000(bil) + ' miljard');
    if (mil) parts.push(nlBelow1000(mil) + ' miljoen');
    if (th) parts.push((th === 1 ? '' : nlBelow1000(th)) + 'duizend');
    if (rest) parts.push(nlBelow1000(rest));
    return parts.join(' ');
  }
  var EN_U = ['zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten', 'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen'];
  var EN_T = ['', '', 'twenty', 'thirty', 'forty', 'fifty', 'sixty', 'seventy', 'eighty', 'ninety'];
  function enBelow1000(n) {
    var h = Math.floor(n / 100), r = n % 100, s = [];
    if (h) s.push(EN_U[h] + ' hundred');
    if (r) {
      var w = r < 20 ? EN_U[r] : EN_T[Math.floor(r / 10)] + (r % 10 ? '-' + EN_U[r % 10] : '');
      s.push(h ? 'and ' + w : w);
    }
    return s.join(' ');
  }
  function enNumber(n) {
    if (n === 0) return 'zero';
    var out = [], units = [[1e9, 'billion'], [1e6, 'million'], [1000, 'thousand']];
    for (var i = 0; i < units.length; i++) {
      var q = Math.floor(n / units[i][0]);
      if (q) { out.push(enBelow1000(q) + ' ' + units[i][1]); n = n % units[i][0]; }
    }
    if (n) out.push((out.length && n < 100 ? 'and ' : '') + enBelow1000(n).replace(/^and /, ''));
    return out.join(' ');
  }
  var CUR_WORDS = {
    SRD: { nl: 'Surinaamse dollar', en1: 'Surinamese dollar', en: 'Surinamese dollars' },
    USD: { nl: 'Amerikaanse dollar', en1: 'US dollar', en: 'US dollars' },
    EUR: { nl: 'euro', en1: 'euro', en: 'euros' }
  };
  function amountInWords(cents, lang, cur) {
    if (cents === null || cents === undefined || cents < 0) return '';
    var W = CUR_WORDS[cur || 'SRD'] || CUR_WORDS.SRD;
    var whole = Math.floor(cents / 100), c = cents % 100;
    if (lang === 'en') {
      var e = enNumber(whole) + ' ' + (whole === 1 ? W.en1 : W.en);
      if (c) e += ' and ' + enNumber(c) + ' cent' + (c === 1 ? '' : 's');
      return e.charAt(0).toUpperCase() + e.slice(1);
    }
    var w = whole === 1 ? 'één' : nlNumber(whole);
    var s = w + ' ' + W.nl;
    if (c) s += ' en ' + (c === 1 ? 'één' : nlNumber(c)) + ' cent';
    return s.charAt(0).toUpperCase() + s.slice(1);
  }

  // ── EAN-13 check digit ────────────────────────────────────────────────────
  function ean13Check(d12) {
    if (!/^\d{12}$/.test(d12)) return null;
    var s = 0;
    for (var i = 0; i < 12; i++) s += (+d12[i]) * (i % 2 ? 3 : 1);
    return (10 - (s % 10)) % 10;
  }

  // ── WiFi / vCard payloads for QR ──────────────────────────────────────────
  function wifiEsc(s) { return String(s).replace(/([\\;,:"])/g, '\\$1'); }
  function wifiPayload(ssid, pass, auth, hidden) {
    var t = auth === 'nopass' ? 'nopass' : (auth || 'WPA');
    return 'WIFI:T:' + t + ';S:' + wifiEsc(ssid) + ';' + (t === 'nopass' ? '' : 'P:' + wifiEsc(pass) + ';') + (hidden ? 'H:true;' : '') + ';';
  }
  function vcEsc(s) { return String(s || '').replace(/\\/g, '\\\\').replace(/\n/g, '\\n').replace(/([,;])/g, '\\$1'); }
  function vcardPayload(v) {
    var L = ['BEGIN:VCARD', 'VERSION:3.0'];
    var fn = [v.first, v.last].filter(Boolean).join(' ') || v.org || '';
    L.push('N:' + vcEsc(v.last) + ';' + vcEsc(v.first) + ';;;');
    L.push('FN:' + vcEsc(fn));
    if (v.org) L.push('ORG:' + vcEsc(v.org));
    if (v.title) L.push('TITLE:' + vcEsc(v.title));
    if (v.tel) L.push('TEL;TYPE=CELL:' + String(v.tel).replace(/[^\d+]/g, ''));
    if (v.email) L.push('EMAIL:' + vcEsc(v.email));
    if (v.url) L.push('URL:' + vcEsc(v.url));
    if (v.adr) L.push('ADR:;;' + vcEsc(v.adr) + ';;;;');
    L.push('END:VCARD');
    return L.join('\r\n');
  }
  // wa.me expects the number in international format without + or spaces
  function waNumber(s) {
    var d = String(s || '').replace(/[^\d+]/g, '');
    if (d.charAt(0) === '+') return d.slice(1);
    if (d.indexOf('00') === 0) return d.slice(2);
    if (/^[5-8]\d{6}$/.test(d) || /^[2-4]\d{5}$/.test(d)) return '597' + d; // local Suriname number
    return d;
  }

  var API = {
    bp: bp, divRound: divRound, pctOf: pctOf, toCents: toCents, parseAmount: parseAmount, parseNum: parseNum,
    fmt: fmt, fmtNum: fmtNum, pick: pick, bands: bands,
    salary: salary, grossForNet: grossForNet, apfDefault: apfDefault,
    btwFromExcl: btwFromExcl, btwFromIncl: btwFromIncl, btwLines: btwLines,
    addDays: addDays, weekday: weekday, daysBetween: daysBetween, isWorkingDay: isWorkingDay, coverage: coverage,
    addWorkingDays: addWorkingDays, countWorkingDays: countWorkingDays, nthWorkingDayOfMonth: nthWorkingDayOfMonth,
    monthlyDeadlines: monthlyDeadlines, monthsLate: monthsLate, btwPenalty: btwPenalty,
    vacationDays: vacationDays, vacationPartial: vacationPartial, vacationOnTermination: vacationOnTermination,
    vacationAllowance: vacationAllowance, incomeTax: incomeTax, importCost: importCost, price: price, loan: loan,
    cashTotal: cashTotal, hm: hm, shiftMinutes: shiftMinutes, amountInWords: amountInWords,
    nlNumber: nlNumber, enNumber: enNumber, ean13Check: ean13Check,
    wifiPayload: wifiPayload, vcardPayload: vcardPayload, waNumber: waNumber, pad2: pad2
  };
  if (typeof module !== 'undefined' && module.exports) module.exports = API;
  else root.BizEngine = API;
})(typeof window !== 'undefined' ? window : this);
