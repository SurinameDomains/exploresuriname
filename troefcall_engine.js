/* Troefcall engine (Explore Suriname, Nov 2026).
   One file, three homes: the browser (practice against the computer runs entirely here),
   the esr-troefcall Worker (online tables; the Worker build pastes this file in) and node (tests).
   Rules: official bond rules (STcB / TSBN) as also described on pagat.com:
     - 4 players, fixed partners opposite each other (seats 0+2 against 1+3), 52 cards, ace high.
     - The caller sits left of the dealer, gets 5 cards and names troef from those 5.
       Then 5 cards to the other three, then 4 and 4 to everyone.
     - "No picture, no game": a caller without king, queen or jack in 13 cards may ask for a new deal.
     - Caller leads. Follow suit when you can, otherwise any card. Highest troef wins, else highest of the led suit.
     - First team to 7 tricks wins the game: 2 points. 7 tricks to 0 is a kap: the winner of the 7th trick
       stops (5 points) or plays on for baunie (all 13 tricks, 15 points); losing one trick then gives the
       other team 2 points.
     - Caller's team scores: same dealer and caller. Other team scores: the caller becomes dealer and the
       player on his left the new caller.
   Everything in a table's state is plain JSON, so the Worker can store it between messages. */
var TCEngine = (function () {
  "use strict";

  var SUITS = ["S", "H", "C", "D"];
  var RANKS = "23456789TJQKA";
  var TURN_MS = { pub: 25000, priv: 45000 };
  /* How long the client takes to show each event. The server adds this to a turn's deadline. */
  var ANIM = { first: 1500, deal1: 1300, trump: 1300, deal2: 1500, nopic: 500, redeal: 1500, keep: 300,
               play: 620, trick: 1150, kapq: 500, baunie: 1300, end: 3600, over: 600, auto: 0, join: 0, left: 0 };

  function rv(c) { return RANKS.indexOf(c[0]); }
  function su(c) { return c[1]; }
  function isCard(c) { return typeof c === "string" && c.length === 2 && rv(c) >= 0 && SUITS.indexOf(c[1]) >= 0; }

  function defaultRnd() {
    var c = (typeof crypto !== "undefined" && crypto.getRandomValues) ? crypto : null;
    if (!c) return Math.random();
    var a = new Uint32Array(1);
    c.getRandomValues(a);
    return a[0] / 4294967296;
  }
  /* small seeded generator for tests */
  function seeded(seed) {
    var s = seed >>> 0;
    return function () {
      s = (s + 0x6D2B79F5) >>> 0;
      var t = Math.imul(s ^ (s >>> 15), 1 | s);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function newDeck() {
    var d = [];
    for (var s = 0; s < 4; s++) for (var r = 0; r < 13; r++) d.push(RANKS[r] + SUITS[s]);
    return d;
  }
  function shuffle(a, rnd) {
    for (var i = a.length - 1; i > 0; i--) {
      var j = Math.floor(rnd() * (i + 1));
      var t = a[i]; a[i] = a[j]; a[j] = t;
    }
    return a;
  }
  function sortHand(hand, trump) {
    /* troef first, then alternating colours; high to low inside a suit */
    var order = ["S", "H", "C", "D"];
    if (trump) {
      var alt = { S: ["S", "H", "C", "D"], H: ["H", "S", "D", "C"], C: ["C", "H", "S", "D"], D: ["D", "S", "H", "C"] };
      order = alt[trump];
    }
    return hand.slice().sort(function (a, b) {
      var d = order.indexOf(su(a)) - order.indexOf(su(b));
      return d || rv(b) - rv(a);
    });
  }

  /* ───────────────────────── game (one match) ───────────────────────── */

  function newMatch(target, rnd) {
    rnd = rnd || defaultRnd;
    var caller = Math.floor(rnd() * 4);
    return {
      target: target || 15, scores: [0, 0], handNo: 0,
      caller: caller, dealer: (caller + 3) % 4,
      phase: "idle", hands: [[], [], [], []], stock: [], trump: null,
      lead: caller, turn: caller, trick: [], tricks: [0, 0], trickNo: 0,
      baunie: null, seen: [], voids: emptyVoids(), redeals: 0, last: null, winner: null,
      stats: { hands: 0, kap: [0, 0], baunie: [0, 0] }
    };
  }
  function emptyVoids() {
    var v = [];
    for (var i = 0; i < 4; i++) v.push({ S: 0, H: 0, C: 0, D: 0 });
    return v;
  }
  function startHand(g, rnd, ev, isRedeal) {
    rnd = rnd || defaultRnd;
    var d = shuffle(newDeck(), rnd);
    g.hands = [[], [], [], []];
    g.hands[g.caller] = d.slice(0, 5);
    g.stock = d.slice(5);
    g.trump = null; g.trick = []; g.tricks = [0, 0]; g.trickNo = 0; g.baunie = null;
    g.seen = []; g.voids = emptyVoids();
    g.phase = "trump"; g.turn = g.caller; g.lead = g.caller;
    if (!isRedeal) { g.handNo++; g.redeals = 0; }
    ev.push({ e: "deal1", n: g.handNo, dealer: g.dealer, caller: g.caller, priv: mapOne(g.caller, g.hands[g.caller].slice()) });
  }
  function mapOne(seat, cards) { var m = {}; m[seat] = cards; return m; }

  function hasPicture(hand) {
    for (var i = 0; i < hand.length; i++) if ("KQJ".indexOf(hand[i][0]) >= 0) return true;
    return false;
  }
  function callTrump(g, seat, suit, ev) {
    if (g.phase !== "trump" || seat !== g.caller || SUITS.indexOf(suit) < 0) return false;
    g.trump = suit;
    ev.push({ e: "trump", seat: seat, suit: suit });
    /* 5 to the other three (clockwise from the caller's left), then 4 and 4 to everyone */
    var st = g.stock, p = 0, i, k;
    for (i = 1; i <= 3; i++) { k = (g.caller + i) % 4; g.hands[k] = g.hands[k].concat(st.slice(p, p + 5)); p += 5; }
    for (var round = 0; round < 2; round++)
      for (i = 0; i < 4; i++) { k = (g.caller + i) % 4; g.hands[k] = g.hands[k].concat(st.slice(p, p + 4)); p += 4; }
    g.stock = [];
    var priv = {};
    for (i = 0; i < 4; i++) priv[i] = g.hands[i].slice();
    ev.push({ e: "deal2", priv: priv });
    if (!hasPicture(g.hands[g.caller]) && g.redeals < 3) {
      g.phase = "redeal"; g.turn = g.caller;
      ev.push({ e: "nopic", seat: g.caller });
    } else {
      g.phase = "play"; g.turn = g.lead = g.caller;
    }
    return true;
  }
  function answerRedeal(g, seat, yes, rnd, ev) {
    if (g.phase !== "redeal" || seat !== g.caller) return false;
    if (yes) {
      g.redeals++;
      ev.push({ e: "redeal", seat: seat, cards: g.hands[seat].slice() });
      startHand(g, rnd, ev, true);
    } else {
      ev.push({ e: "keep", seat: seat });
      g.phase = "play"; g.turn = g.lead = g.caller;
    }
    return true;
  }
  function legalCards(g, seat) {
    if (g.phase !== "play" || g.turn !== seat) return [];
    var hand = g.hands[seat];
    if (!g.trick.length) return hand.slice();
    var led = su(g.trick[0].c);
    var f = hand.filter(function (c) { return su(c) === led; });
    return f.length ? f : hand.slice();
  }
  function trickWinner(trick, trump) {
    var best = trick[0];
    for (var i = 1; i < trick.length; i++) {
      var p = trick[i];
      if (su(p.c) === su(best.c)) { if (rv(p.c) > rv(best.c)) best = p; }
      else if (su(p.c) === trump) best = p;
    }
    return best;
  }
  function playCard(g, seat, card, ev) {
    if (g.phase !== "play" || g.turn !== seat) return false;
    var hand = g.hands[seat], ix = hand.indexOf(card);
    if (ix < 0) return false;
    if (g.trick.length) {
      var led = su(g.trick[0].c);
      if (su(card) !== led) {
        if (hand.some(function (c) { return su(c) === led; })) return false;
        g.voids[seat][led] = 1;
      }
    }
    hand.splice(ix, 1);
    g.trick.push({ s: seat, c: card });
    ev.push({ e: "play", seat: seat, card: card });
    if (g.trick.length < 4) { g.turn = (seat + 1) % 4; return true; }

    var w = trickWinner(g.trick, g.trump).s, t = w % 2;
    for (var i = 0; i < 4; i++) g.seen.push(g.trick[i].c);
    g.trick = []; g.trickNo++; g.tricks[t]++;
    ev.push({ e: "trick", w: w, tricks: g.tricks.slice() });
    if (g.baunie !== null) {
      if (t !== g.baunie) endHand(g, t, 2, "fail", ev);
      else if (g.tricks[t] === 13) endHand(g, t, 15, "baunie", ev);
      else g.turn = g.lead = w;
    } else if (g.tricks[t] === 7) {
      if (g.tricks[1 - t] === 0) { g.phase = "kap"; g.turn = w; ev.push({ e: "kapq", seat: w }); }
      else endHand(g, t, 2, "win", ev);
    } else g.turn = g.lead = w;
    return true;
  }
  function decideKap(g, seat, goOn, ev) {
    if (g.phase !== "kap" || g.turn !== seat) return false;
    if (goOn) {
      g.baunie = seat % 2; g.phase = "play"; g.lead = g.turn = seat;
      ev.push({ e: "baunie", seat: seat });
    } else endHand(g, seat % 2, 5, "kap", ev);
    return true;
  }
  function endHand(g, team, pts, kind, ev) {
    g.scores[team] += pts;
    g.stats.hands++;
    if (kind === "kap") g.stats.kap[team]++;
    if (kind === "baunie") g.stats.baunie[team]++;
    g.last = { kind: kind, team: team, pts: pts, tricks: g.tricks.slice(), caller: g.caller, trump: g.trump };
    ev.push({ e: "end", kind: kind, team: team, pts: pts, scores: g.scores.slice(), tricks: g.tricks.slice() });
    /* caller's team scored: nothing moves. Otherwise the caller deals and the player on his left calls. */
    if (team !== g.caller % 2) { g.dealer = g.caller; g.caller = (g.caller + 1) % 4; }
    g.hands = [[], [], [], []]; g.trick = [];
    if (g.scores[team] >= g.target) {
      g.phase = "over"; g.winner = team;
      ev.push({ e: "over", team: team, scores: g.scores.slice() });
    } else g.phase = "handend";
  }

  /* ───────────────────────── computer player ───────────────────────── */
  /* A bot only uses what its seat can know: its own cards, the cards played so far and who failed to follow suit. */

  function botTrump(hand) {
    var best = null, bs = -1;
    SUITS.forEach(function (s) {
      var cs = hand.filter(function (c) { return su(c) === s; });
      if (!cs.length) return;
      var sc = cs.length * 10;
      cs.forEach(function (c) { var r = rv(c); sc += r >= 12 ? 7 : r === 11 ? 5 : r === 10 ? 3.5 : r === 9 ? 2.5 : r === 8 ? 1 : r / 20; });
      if (sc > bs) { bs = sc; best = s; }
    });
    return best || "S";
  }
  function botRedeal(hand) {
    var aces = hand.filter(function (c) { return c[0] === "A"; }).length;
    return aces < 2;
  }
  function knowledge(g, seat) {
    var hand = g.hands[seat], gone = {}, i;
    for (i = 0; i < g.seen.length; i++) gone[g.seen[i]] = 1;
    for (i = 0; i < g.trick.length; i++) gone[g.trick[i].c] = 1;
    var mine = {};
    for (i = 0; i < hand.length; i++) mine[hand[i]] = 1;
    /* boss = no higher card of that suit is still with another player */
    function boss(c) {
      for (var r = rv(c) + 1; r < 13; r++) { var x = RANKS[r] + su(c); if (!gone[x] && !mine[x]) return false; }
      return true;
    }
    var T = g.trump, tOut = 0;
    for (i = 0; i < 13; i++) { var x = RANKS[i] + T; if (!gone[x] && !mine[x]) tOut++; }
    var opp = [(seat + 1) % 4, (seat + 3) % 4], mate = (seat + 2) % 4;
    function oppCanRuff(suit) {
      if (suit === T || !tOut) return false;
      return opp.some(function (o) { return g.voids[o][suit] && !g.voids[o][T]; });
    }
    function outIn(suit) { /* cards of the suit still with other players */
      var n = 0;
      for (var r = 0; r < 13; r++) { var x = RANKS[r] + suit; if (!gone[x] && !mine[x]) n++; }
      return n;
    }
    return { boss: boss, tOut: tOut, opp: opp, mate: mate, oppCanRuff: oppCanRuff, outIn: outIn, T: T };
  }
  function lowest(cards) { return cards.reduce(function (a, b) { return rv(b) < rv(a) ? b : a; }); }
  function highest(cards) { return cards.reduce(function (a, b) { return rv(b) > rv(a) ? b : a; }); }

  function botPlay(g, seat, rnd) {
    var legal = legalCards(g, seat);
    if (legal.length === 1) return legal[0];
    var K = knowledge(g, seat), T = K.T, hand = g.hands[seat];
    var trumps = hand.filter(function (c) { return su(c) === T; });
    var side = hand.filter(function (c) { return su(c) !== T; });
    function bySuit(s) { return hand.filter(function (c) { return su(c) === s; }); }
    function discard(pool) {
      /* throw the least useful card: low, not a boss, from a short suit; troef only when nothing else */
      var nt = pool.filter(function (c) { return su(c) !== T; });
      var p = nt.length ? nt : pool;
      var best = p[0], bs = 1e9;
      p.forEach(function (c) {
        var s = rv(c) + (K.boss(c) ? 30 : 0) + bySuit(su(c)).length * 0.3;
        if (s < bs) { bs = s; best = c; }
      });
      return best;
    }

    if (!g.trick.length) {
      /* ── leading ── */
      var myTeamCalled = g.caller % 2 === seat % 2;
      if (trumps.length && K.tOut > 0) {
        var topT = highest(trumps);
        if (K.boss(topT) && (myTeamCalled || trumps.length >= 3 || g.baunie === seat % 2)) return topT;
      }
      var bosses = side.filter(function (c) { return K.boss(c) && !K.oppCanRuff(su(c)); });
      if (bosses.length) {
        /* cash the one from the suit the others still hold most of (least likely to be ruffed) */
        bosses.sort(function (a, b) { return K.outIn(su(b)) - K.outIn(su(a)) || rv(b) - rv(a); });
        return bosses[0];
      }
      if (trumps.length && K.tOut > 0 && myTeamCalled && trumps.length >= 4) return lowest(trumps);
      /* give partner a ruff */
      var forMate = side.filter(function (c) { return g.voids[K.mate][su(c)] && !g.voids[K.mate][T] && K.tOut > 0 && !K.oppCanRuff(su(c)); });
      if (forMate.length) return lowest(forMate);
      var safe = side.filter(function (c) { return !K.oppCanRuff(su(c)); });
      var pool = safe.length ? safe : side;
      if (pool.length) {
        /* a single low card when I can ruff the suit later, else low from my longest suit */
        if (trumps.length) {
          var single = pool.filter(function (c) { return bySuit(su(c)).length === 1 && rv(c) < 10; });
          if (single.length) return lowest(single);
        }
        var longest = pool.slice().sort(function (a, b) { return bySuit(su(b)).length - bySuit(su(a)).length || rv(a) - rv(b); });
        return longest[0];
      }
      return K.boss(highest(trumps)) ? highest(trumps) : lowest(trumps);
    }

    /* ── following ── */
    var n = g.trick.length, last = n === 3;
    var led = su(g.trick[0].c);
    var cur = trickWinner(g.trick, T);
    var mateWins = cur.s % 2 === seat % 2;
    var curIsRuff = su(cur.c) === T && led !== T;
    var follow = su(legal[0]) === led && bySuit(led).length > 0;

    if (follow) {
      var win = curIsRuff ? [] : legal.filter(function (c) { return rv(c) > rv(cur.c); });
      if (mateWins) {
        if (last || curIsRuff || K.boss(cur.c) || rv(cur.c) >= 9) return lowest(legal);
        var hi = highest(legal);
        return (win.length && (K.boss(hi) || rv(hi) >= 10)) ? hi : lowest(legal);
      }
      if (!win.length) return lowest(legal);
      if (last) return lowest(win);
      var top = highest(win);
      if (K.boss(top)) return top;
      if (n === 2) return top;            /* third hand high */
      return lowest(legal);               /* second hand low */
    }
    /* cannot follow suit */
    if (mateWins) {
      if (last || curIsRuff || K.boss(cur.c)) return discard(legal);
      if (trumps.length && rv(cur.c) < 9) return lowest(trumps);
      return discard(legal);
    }
    if (trumps.length) {
      if (curIsRuff) {
        var over = trumps.filter(function (c) { return rv(c) > rv(cur.c); });
        if (over.length) return lowest(over);
        return discard(legal);
      }
      return lowest(trumps);
    }
    return discard(legal);
  }
  function botKap(g, seat) {
    /* play on for baunie only with a hand that cannot lose a trick */
    var K = knowledge(g, seat), T = K.T, hand = g.hands[seat];
    var trumps = hand.filter(function (c) { return su(c) === T; }).sort(function (a, b) { return rv(b) - rv(a); });
    var run = 0;
    /* my top troefs in sequence: after the ace is played the king is boss, and so on */
    var gone = {};
    g.seen.forEach(function (c) { gone[c] = 1; });
    var mine = {};
    hand.forEach(function (c) { mine[c] = 1; });
    function topRun(suit) {
      var k = 0;
      for (var r = 12; r >= 0; r--) {
        var x = RANKS[r] + suit;
        if (gone[x]) continue;
        if (mine[x]) k++; else break;
      }
      return k;
    }
    run = topRun(T);
    if (K.tOut > 0 && run < K.tOut) return false;
    if (K.tOut > 0 && trumps.length < K.tOut) return false;
    for (var i = 0; i < 4; i++) {
      var s = SUITS[i];
      if (s === T) continue;
      var n = hand.filter(function (c) { return su(c) === s; }).length;
      if (n && topRun(s) < n) return false;
    }
    return true;
  }

  /* ───────────────────────── table (seats, people, flow) ───────────────────────── */

  var BOT_NAMES = ["Anansi", "Kodjo", "Ba Tigri", "Sisa", "Oom Rudi", "Tante Es", "Mati", "Tia", "Kofi", "Amba", "Baas Jopie", "Swagri"];

  function cleanName(s) {
    s = String(s == null ? "" : s).replace(/[\u0000-\u001f\u007f<>&"'`\\]/g, "").replace(/\s+/g, " ").trim();
    if (s.length > 14) s = s.slice(0, 14).trim();
    return s;
  }
  function cleanChat(s) {
    s = String(s == null ? "" : s).replace(/[\u0000-\u001f\u007f]/g, " ").replace(/\s+/g, " ").trim();
    if (s.length > 140) s = s.slice(0, 140);
    return s;
  }

  function Table(opts) {
    opts = opts || {};
    this.rnd = opts.rnd || defaultRnd;
    this.out = [];              /* [{pid, msg}] for the transport to deliver */
    if (opts.state) { this.s = opts.state; return; }
    var now = opts.now || Date.now();
    this.s = {
      v: 1, code: opts.code || "", pub: !!opts.pub, solo: !!opts.solo,
      target: opts.target || 15, phase: opts.pub || opts.solo ? "game" : "wait", host: null,
      seats: [], g: null, deadline: 0, restartAt: 0, created: now, emptySince: now, seq: 0, chatAt: {}
    };
    var names = shuffle(BOT_NAMES.slice(), this.rnd);
    for (var i = 0; i < 4; i++) this.s.seats.push({ pid: null, name: "", bot: names[i], conn: 0, away: 0, strikes: 0, gone: 0 });
  }

  Table.prototype.seatOf = function (pid) {
    if (!pid) return -1;
    for (var i = 0; i < 4; i++) if (this.s.seats[i].pid === pid) return i;
    return -1;
  };
  Table.prototype.humans = function () { return this.s.seats.filter(function (x) { return x.pid; }).length; };
  Table.prototype.connected = function () { return this.s.seats.filter(function (x) { return x.pid && x.conn; }).length; };
  Table.prototype.active = function () { return this.s.seats.filter(function (x) { return x.pid && x.conn && !x.away; }).length; };
  Table.prototype.label = function (i) { var x = this.s.seats[i]; return x.pid ? x.name : x.bot; };

  /* join or come back. Returns seat number, or -1 when the table is full. */
  Table.prototype.join = function (pid, name, now) {
    var s = this.s, i = this.seatOf(pid), ev = [];
    name = cleanName(name) || "Speler";
    if (i >= 0) {
      var st = s.seats[i];
      st.conn = 1; st.away = 0; st.strikes = 0; st.gone = 0; st.name = name;
    } else {
      var free = [];
      for (var k = 0; k < 4; k++) if (!s.seats[k].pid) free.push(k);
      if (!free.length) return -1;
      if (s.phase === "wait") i = free[0];
      else {
        /* online table already playing: take over a computer seat, on the side with fewer people */
        var cnt = [0, 0];
        s.seats.forEach(function (x, k2) { if (x.pid) cnt[k2 % 2]++; });
        free.sort(function (a, b) { return cnt[a % 2] - cnt[b % 2]; });
        var bestSide = cnt[free[0] % 2];
        var cands = free.filter(function (k3) { return cnt[k3 % 2] === bestSide; });
        i = cands[Math.floor(this.rnd() * cands.length)];
      }
      /* two people with the same name at one table: number the newcomer */
      var taken = s.seats.filter(function (x) { return x.pid; }).map(function (x) { return x.name.toLowerCase(); });
      if (taken.indexOf(name.toLowerCase()) >= 0) name = cleanName(name.slice(0, 12) + " 2");
      s.seats[i] = { pid: pid, name: name, bot: s.seats[i].bot, conn: 1, away: 0, strikes: 0, gone: 0 };
      if (s.host === null || this.seatOf(s.host) < 0) s.host = pid;
      ev.push({ e: "join", seat: i, name: name });
    }
    s.emptySince = 0;
    if (s.phase === "game" && !s.g) this.newGame(ev);
    this.advance(now, ev);
    this.broadcast(ev, now);
    return i;
  };
  /* socket closed: keep the seat for a while, the computer plays meanwhile */
  Table.prototype.drop = function (pid, now) {
    var i = this.seatOf(pid);
    if (i < 0) return;
    var st = this.s.seats[i];
    st.conn = 0; st.gone = now;
    if (!this.connected()) this.s.emptySince = now;
    var ev = [];
    this.advance(now, ev);
    this.broadcast(ev, now);
  };
  Table.prototype.leave = function (pid, now) {
    var s = this.s, i = this.seatOf(pid);
    if (i < 0) return;
    var nm = s.seats[i].name;
    s.seats[i] = { pid: null, name: "", bot: s.seats[i].bot, conn: 0, away: 0, strikes: 0, gone: 0 };
    if (s.host === pid) {
      s.host = null;
      for (var k = 0; k < 4; k++) if (s.seats[k].pid && s.seats[k].conn) { s.host = s.seats[k].pid; break; }
      if (s.host === null) for (k = 0; k < 4; k++) if (s.seats[k].pid) { s.host = s.seats[k].pid; break; }
    }
    if (!this.connected()) s.emptySince = now;
    var ev = [{ e: "left", seat: i, name: nm }];
    this.advance(now, ev);
    this.broadcast(ev, now);
  };
  Table.prototype.newGame = function (ev) {
    var s = this.s;
    s.g = newMatch(s.target, this.rnd);
    s.restartAt = 0;
    ev.push({ e: "first", seat: s.g.caller });
    startHand(s.g, this.rnd, ev);
  };

  /* A message from a person. Returns false when it was not allowed (the transport may ignore that). */
  Table.prototype.handle = function (pid, m, now) {
    var s = this.s, i = this.seatOf(pid), g = s.g, ev = [], ok = false;
    if (i < 0 || !m || typeof m.t !== "string") return false;
    var st = s.seats[i];
    switch (m.t) {
      case "sit":
        if (s.phase !== "wait") return false;
        var to = m.seat | 0;
        if (to < 0 || to > 3 || to === i || s.seats[to].pid) return false;
        var bFrom = s.seats[i].bot, bTo = s.seats[to].bot;
        s.seats[to] = st; st.bot = bTo;
        s.seats[i] = { pid: null, name: "", bot: bFrom, conn: 0, away: 0, strikes: 0, gone: 0 };
        ok = true; break;
      case "opt":
        if (s.phase !== "wait" || s.host !== pid) return false;
        if ([10, 15, 20].indexOf(m.target | 0) < 0) return false;
        s.target = m.target | 0; ok = true; break;
      case "start":
        if (s.phase !== "wait" || s.host !== pid) return false;
        s.phase = "game"; this.newGame(ev); ok = true; break;
      case "again":
        if (s.phase !== "game" || !g || g.phase !== "over") return false;
        this.newGame(ev); ok = true; break;
      case "back":
        st.away = 0; st.strikes = 0; ok = true; break;
      case "trump":
        if (!g) return false;
        ok = callTrump(g, i, m.suit, ev); break;
      case "redeal":
        if (!g) return false;
        ok = answerRedeal(g, i, !!m.yes, this.rnd, ev); break;
      case "play":
        if (!g || !isCard(m.card)) return false;
        ok = playCard(g, i, m.card, ev); break;
      case "kap":
        if (!g) return false;
        ok = decideKap(g, i, !!m.go, ev); break;
      case "chat":
        var txt = cleanChat(m.m);
        if (!txt) return false;
        var last = s.chatAt[i] || 0;
        if (now - last < 900) return false;
        s.chatAt[i] = now;
        for (var k = 0; k < 4; k++) if (s.seats[k].pid && s.seats[k].conn) this.out.push({ pid: s.seats[k].pid, msg: { t: "chat", seat: i, name: st.name, m: txt } });
        return true;
      default: return false;
    }
    if (!ok) return false;
    if (m.t === "trump" || m.t === "play" || m.t === "kap" || m.t === "redeal") { st.away = 0; st.strikes = 0; }
    this.advance(now, ev);
    this.broadcast(ev, now);
    return true;
  };

  /* Let the computer act for its own seats and for people who are away, until a person has to decide. */
  Table.prototype.advance = function (now, ev) {
    var s = this.s, g = s.g;
    s.deadline = 0;
    if (s.phase !== "game" || !g) return;
    var guard = 0;
    while (guard++ < 400) {
      if (g.phase === "handend") {
        if (!this.active()) return;           /* nobody is watching: wait */
        startHand(g, this.rnd, ev);
        continue;
      }
      if (g.phase === "over") {
        if (s.pub && !s.restartAt) s.restartAt = now + animMs(ev) + 15000;
        return;
      }
      if (g.phase === "idle") return;
      var seat = g.turn, st = s.seats[seat];
      var person = st.pid && st.conn && !st.away;
      if (person) {
        if (!s.solo) s.deadline = now + animMs(ev) + (s.pub ? TURN_MS.pub : TURN_MS.priv) + (g.phase === "trump" ? 8000 : 0);
        return;
      }
      if (!this.active()) return;             /* only computers and absent people left: pause */
      this.botAct(seat, ev);
    }
  };
  Table.prototype.botAct = function (seat, ev) {
    var g = this.s.g;
    if (g.phase === "trump") callTrump(g, seat, botTrump(g.hands[seat]), ev);
    else if (g.phase === "redeal") answerRedeal(g, seat, botRedeal(g.hands[seat]), this.rnd, ev);
    else if (g.phase === "kap") decideKap(g, seat, botKap(g, seat), ev);
    else if (g.phase === "play") playCard(g, seat, botPlay(g, seat, this.rnd), ev);
  };

  /* Clock: turn ran out, absent seats are given back, a finished online match starts again.
     Returns "dead" when the table can be thrown away. */
  Table.prototype.tick = function (now) {
    var s = this.s, g = s.g, ev = [], changed = false, self = this;
    var grace = s.pub ? 90000 : 600000;
    s.seats.forEach(function (st, i) {
      if (st.pid && !st.conn && st.gone && now - st.gone > grace) {
        var nm = st.name;
        s.seats[i] = { pid: null, name: "", bot: st.bot, conn: 0, away: 0, strikes: 0, gone: 0 };
        if (s.host === st.pid) {
          s.host = null;
          for (var k = 0; k < 4; k++) if (s.seats[k].pid) { s.host = s.seats[k].pid; break; }
        }
        ev.push({ e: "left", seat: i, name: nm });
        changed = true;
      }
    });
    if (!this.connected()) {
      if (!s.emptySince) s.emptySince = now;
      if (now - s.emptySince > (s.pub ? 120000 : 1800000)) return "dead";
    }
    if (s.phase === "game" && g) {
      if (g.phase === "over" && s.restartAt && now >= s.restartAt && this.active()) {
        this.newGame(ev); changed = true;
      } else if (s.deadline && now >= s.deadline && g.phase !== "over" && g.phase !== "handend") {
        var seat = g.turn, st = s.seats[seat];
        st.strikes++;
        if (st.strikes >= 2) st.away = 1;
        ev.push({ e: "auto", seat: seat });
        self.botAct(seat, ev);
        changed = true;
      }
    }
    if (changed) { this.advance(now, ev); this.broadcast(ev, now); }
    return "ok";
  };
  /* when the transport should call tick() next (0 = no need) */
  Table.prototype.nextWake = function (now) {
    var s = this.s, t = 0;
    function want(x) { if (x && (!t || x < t)) t = x; }
    want(s.deadline);
    if (s.g && s.g.phase === "over") want(s.restartAt);
    var grace = s.pub ? 90000 : 600000;
    s.seats.forEach(function (st) { if (st.pid && !st.conn && st.gone) want(st.gone + grace + 500); });
    if (!this.connected()) want((s.emptySince || now) + (s.pub ? 120000 : 1800000) + 500);
    return t ? Math.max(t, now + 200) : 0;
  };

  function animMs(ev) {
    var t = 0;
    for (var i = 0; i < ev.length; i++) t += ANIM[ev[i].e] || 0;
    return t;
  }
  function personalize(ev, seat) {
    return ev.map(function (e) {
      if (!e.priv) return e;
      var c = {};
      for (var k in e) if (k !== "priv") c[k] = e[k];
      c.h = e.priv[seat] || null;
      return c;
    });
  }
  Table.prototype.snapshot = function (seat, now) {
    var s = this.s, g = s.g;
    var o = {
      code: s.code, pub: s.pub ? 1 : 0, solo: s.solo ? 1 : 0, phase: s.phase, target: s.target, you: seat,
      host: this.seatOf(s.host), seq: s.seq,
      seats: s.seats.map(function (x) { return { name: x.pid ? x.name : x.bot, bot: x.pid ? 0 : 1, conn: x.pid ? (x.conn ? 1 : 0) : 1, away: x.away ? 1 : 0 }; }),
      dl: s.deadline ? Math.max(0, s.deadline - now) : 0, g: null
    };
    if (g) {
      o.g = {
        phase: g.phase, handNo: g.handNo, dealer: g.dealer, caller: g.caller, trump: g.trump, turn: g.turn, lead: g.lead,
        trick: g.trick, tricks: g.tricks, scores: g.scores, target: g.target, baunie: g.baunie, winner: g.winner, last: g.last,
        stats: g.stats, counts: g.hands.map(function (h) { return h.length; }),
        hand: seat >= 0 ? sortHand(g.hands[seat], g.trump) : [],
        legal: seat >= 0 ? legalCards(g, seat) : [],
        restart: g.phase === "over" && s.restartAt ? Math.max(0, s.restartAt - now) : 0
      };
    }
    return o;
  };
  Table.prototype.broadcast = function (ev, now) {
    var s = this.s;
    now = now || Date.now();
    s.seq++;
    for (var i = 0; i < 4; i++) {
      var st = s.seats[i];
      if (st.pid && st.conn) this.out.push({ pid: st.pid, msg: { t: "u", ev: personalize(ev || [], i), s: this.snapshot(i, now) } });
    }
  };
  Table.prototype.flush = function () { var o = this.out; this.out = []; return o; };

  var api = {
    SUITS: SUITS, RANKS: RANKS, ANIM: ANIM, TURN_MS: TURN_MS, BOT_NAMES: BOT_NAMES,
    rv: rv, su: su, isCard: isCard, newDeck: newDeck, shuffle: shuffle, seeded: seeded, sortHand: sortHand,
    newMatch: newMatch, startHand: startHand, callTrump: callTrump, answerRedeal: answerRedeal, legalCards: legalCards,
    trickWinner: trickWinner, playCard: playCard, decideKap: decideKap, hasPicture: hasPicture,
    botTrump: botTrump, botRedeal: botRedeal, botPlay: botPlay, botKap: botKap,
    cleanName: cleanName, cleanChat: cleanChat, animMs: animMs, personalize: personalize, Table: Table
  };
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  return api;
})();
