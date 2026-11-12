/* Troefcall table UI (Explore Suriname, Nov 2026). Needs TCEngine (troefcall_engine.js) and <div id="tc-app" data-api="...">.
   Practice against the computer runs in this page; online tables talk to the esr-troefcall Worker over a WebSocket.
   All words live in I18N below (en/nl/es/zh/fr/pt, hand-written). Names and chat are only ever written with textContent. */
(function () {
  "use strict";
  var E = window.TCEngine, root = document.getElementById("tc-app");
  if (!E || !root) return;

  var I18N = {
    en: {
      name_lbl: "Your name", name_ph: "Name at the table", online: "{n} playing online now",
      now: "Play now", now_sub: "Online with whoever is at the table. Computer players fill the empty seats.",
      friends: "Play with friends", friends_sub: "Open a table and send the link on WhatsApp.",
      code_lbl: "Got a table code?", code_ph: "Code", join: "Join",
      solo: "Practise against the computer", solo_sub: "Works without internet, at your own pace.",
      solo_resume: "Continue practice match ({a}–{b})", solo_new: "New practice match",
      invited: "You are invited to table {code}", join_table: "Sit down at the table", back_table: "Back to table {code}",
      record: "Your matches: {w} won of {p}", connecting: "Connecting…",
      e_notfound: "This table is closed. Open a new one or tap Play now.", e_full: "This table is full.",
      e_net: "The game server did not answer. Check your connection, or practise against the computer.",
      e_busy: "A lot of new tables right now. Try again in a minute.",
      e_replaced: "This table is open in another tab or on another device.",
      us: "We", them: "They", to_n: "to {n}", troef: "Troef", tricks: "Tricks", you: "You", partner: "partner", pc: "computer", host: "host",
      dealer: "Dealer", caller: "Caller", gone: "offline",
      your_turn: "Your turn", turn_of: "{name} is playing",
      pick_t: "Choose troef", pick_s: "You are the caller. Name troef from your first five cards.",
      picking: "{name} is choosing troef…", called: "{name} calls troef",
      S: "Spades", H: "Hearts", C: "Clubs", D: "Diamonds",
      follow: "Follow suit: play {suit}", again_tap: "Tap again to play",
      nopic_t: "No picture, no game", nopic_q: "You have no king, queen or jack. Ask for a new deal?", nopic_y: "New deal", nopic_n: "Play these cards",
      nopic_o: "{name} has no picture card. New deal.",
      kap_t: "Kap!", kap_q: "Seven tricks to nil. Stop here for 5 points, or play on for baunie: all 13 tricks for 15 points. Lose a single trick and the other side gets 2.",
      kap_stop: "Kap partij: 5 points", kap_go: "Play on for baunie", kap_w: "Kap! {name} decides: stop or baunie?", bau_go: "{name} plays on for baunie!",
      r_win_us: "We win the game", r_win_them: "They win the game", r_kap_us: "Kap! Seven tricks to nil", r_kap_them: "Kap against us",
      r_bau_us: "Baunie! All 13 tricks", r_bau_them: "Baunie against us", r_fail_us: "Their baunie failed", r_fail_them: "Our baunie failed",
      pts_us: "+{n} for us", pts_them: "+{n} for them", first: "{name} is the first caller",
      o_win: "You win the match!", o_lose: "Match lost", final: "Final score", again: "Play again", again_in: "New match in {n} s",
      share: "Share on WhatsApp", lobby: "Leave table",
      sh_win: "I won at Troefcall, {a}–{b}, on Explore Suriname. Come and play: {url}", sh_any: "Come and play Troefcall on Explore Suriname: {url}",
      w_code: "Table code", guest: "Guest", w_title: "Table {code}", w_inv: "Invite your friends", w_inv_s: "Send this link. Whoever opens it sits down at your table.",
      wa: "Send on WhatsApp", copy: "Copy link", copied: "Copied", inv_txt: "Come play Troefcall with me! Table {code}: {url}",
      w_seats: "Players opposite each other are partners. Tap an empty seat to move.", sit_here: "Sit here",
      len: "Match length", pts_n: "{n} points", start: "Start the game", start_s: "Computer players take the empty seats.", w_host: "Waiting for {name} to start…",
      n_lost: "Connection lost. Reconnecting…", n_fail: "Could not reconnect.", retry: "Try again",
      away_t: "Still there?", away_q: "The computer is playing your cards.", back: "I'm back",
      auto: "Time's up. The computer played for {name}.", joined: "{name} sat down", left: "{name} left. The computer takes over.",
      chat: "Chat", chat_ph: "Say something…", send: "Send", chat_rule: "Keep it friendly, and don't tell your partner your cards.",
      mute: "Mute", unmute: "Unmute", chat_empty: "No messages yet.",
      sound: "Sound", confirm: "Tap twice to play a card", rules: "Rules", leave: "Leave table", leave_q: "Leave this table?", yes: "Yes, leave", no: "Stay",
      practice: "Practice", close: "Close", menu: "Menu"
    },
    nl: {
      name_lbl: "Je naam", name_ph: "Naam aan tafel", online: "{n} spelers nu online",
      now: "Nu spelen", now_sub: "Online met wie er aan tafel zit. Computerspelers vullen de lege stoelen.",
      friends: "Met vrienden spelen", friends_sub: "Open een tafel en stuur de link via WhatsApp.",
      code_lbl: "Heb je een tafelcode?", code_ph: "Code", join: "Aanschuiven",
      solo: "Oefenen tegen de computer", solo_sub: "Werkt zonder internet, in je eigen tempo.",
      solo_resume: "Verder met je oefenwedstrijd ({a}–{b})", solo_new: "Nieuwe oefenwedstrijd",
      invited: "Je bent uitgenodigd aan tafel {code}", join_table: "Aanschuiven", back_table: "Terug naar tafel {code}",
      record: "Je wedstrijden: {w} gewonnen van {p}", connecting: "Verbinden…",
      e_notfound: "Deze tafel is gesloten. Open een nieuwe of tik op Nu spelen.", e_full: "Deze tafel is vol.",
      e_net: "De spelserver reageert niet. Controleer je verbinding, of oefen tegen de computer.",
      e_busy: "Er worden nu veel tafels geopend. Probeer het over een minuut opnieuw.",
      e_replaced: "Deze tafel is open in een ander tabblad of op een ander toestel.",
      us: "Wij", them: "Zij", to_n: "tot {n}", troef: "Troef", tricks: "Slagen", you: "Jij", partner: "partner", pc: "computer", host: "host",
      dealer: "Deler", caller: "Caller", gone: "offline",
      your_turn: "Jij bent aan de beurt", turn_of: "{name} speelt",
      pick_t: "Kies troef", pick_s: "Jij bent de caller. Maak troef uit je eerste vijf kaarten.",
      picking: "{name} kiest troef…", called: "{name} maakt troef",
      S: "Schoppen", H: "Harten", C: "Klaveren", D: "Ruiten",
      follow: "Je moet bekennen: speel {suit}", again_tap: "Tik nog een keer om te spelen",
      nopic_t: "No picture, no game", nopic_q: "Je hebt geen heer, vrouw of boer. Opnieuw laten delen?", nopic_y: "Opnieuw delen", nopic_n: "Met deze kaarten spelen",
      nopic_o: "{name} heeft geen prent. Er wordt opnieuw gedeeld.",
      kap_t: "Kap!", kap_q: "Zeven slagen tegen nul. Stop nu voor 5 punten, of speel door voor baunie: alle 13 slagen voor 15 punten. Verlies je één slag, dan krijgt de tegenpartij 2 punten.",
      kap_stop: "Kap partij: 5 punten", kap_go: "Doorspelen voor baunie", kap_w: "Kap! {name} beslist: stoppen of baunie?", bau_go: "{name} speelt door voor baunie!",
      r_win_us: "Wij winnen de game", r_win_them: "Zij winnen de game", r_kap_us: "Kap! Zeven slagen tegen nul", r_kap_them: "Kap tegen ons",
      r_bau_us: "Baunie! Alle 13 slagen", r_bau_them: "Baunie tegen ons", r_fail_us: "Hun baunie is mislukt", r_fail_them: "Onze baunie is mislukt",
      pts_us: "+{n} voor ons", pts_them: "+{n} voor hen", first: "{name} is de eerste caller",
      o_win: "Je wint de wedstrijd!", o_lose: "Wedstrijd verloren", final: "Eindstand", again: "Nog een wedstrijd", again_in: "Nieuwe wedstrijd over {n} s",
      share: "Delen via WhatsApp", lobby: "Tafel verlaten",
      sh_win: "Ik heb gewonnen met Troefcall, {a}–{b}, op Explore Suriname. Kom ook spelen: {url}", sh_any: "Kom Troefcall spelen op Explore Suriname: {url}",
      w_code: "Tafelcode", guest: "Gast", w_title: "Tafel {code}", w_inv: "Nodig je vrienden uit", w_inv_s: "Stuur deze link. Wie hem opent, schuift aan bij jouw tafel.",
      wa: "Stuur via WhatsApp", copy: "Link kopiëren", copied: "Gekopieerd", inv_txt: "Kom Troefcall met mij spelen! Tafel {code}: {url}",
      w_seats: "Wie tegenover elkaar zit, speelt samen. Tik op een lege stoel om te wisselen.", sit_here: "Hier zitten",
      len: "Lengte van de wedstrijd", pts_n: "{n} punten", start: "Start het spel", start_s: "Computerspelers nemen de lege stoelen.", w_host: "Wachten tot {name} start…",
      n_lost: "Verbinding verbroken. Opnieuw verbinden…", n_fail: "Opnieuw verbinden is niet gelukt.", retry: "Probeer opnieuw",
      away_t: "Ben je er nog?", away_q: "De computer speelt je kaarten.", back: "Ik ben er weer",
      auto: "De tijd is om. De computer speelde voor {name}.", joined: "{name} schuift aan", left: "{name} is weg. De computer neemt het over.",
      chat: "Chat", chat_ph: "Zeg iets…", send: "Stuur", chat_rule: "Houd het gezellig en verklap je kaarten niet aan je partner.",
      mute: "Dempen", unmute: "Weer tonen", chat_empty: "Nog geen berichten.",
      sound: "Geluid", confirm: "Twee keer tikken om een kaart te spelen", rules: "Spelregels", leave: "Tafel verlaten", leave_q: "Deze tafel verlaten?", yes: "Ja, verlaten", no: "Blijven",
      practice: "Oefenen", close: "Sluiten", menu: "Menu"
    },
    es: {
      name_lbl: "Tu nombre", name_ph: "Nombre en la mesa", online: "{n} jugando en línea ahora",
      now: "Jugar ahora", now_sub: "En línea con quien esté en la mesa. La computadora ocupa las sillas vacías.",
      friends: "Jugar con amigos", friends_sub: "Abre una mesa y envía el enlace por WhatsApp.",
      code_lbl: "¿Tienes un código de mesa?", code_ph: "Código", join: "Entrar",
      solo: "Practicar contra la computadora", solo_sub: "Funciona sin internet, a tu ritmo.",
      solo_resume: "Seguir la partida de práctica ({a}–{b})", solo_new: "Nueva partida de práctica",
      invited: "Te invitaron a la mesa {code}", join_table: "Sentarme en la mesa", back_table: "Volver a la mesa {code}",
      record: "Tus partidas: {w} ganadas de {p}", connecting: "Conectando…",
      e_notfound: "Esta mesa está cerrada. Abre una nueva o toca Jugar ahora.", e_full: "Esta mesa está llena.",
      e_net: "El servidor del juego no responde. Revisa tu conexión o practica contra la computadora.",
      e_busy: "Se están abriendo muchas mesas. Inténtalo de nuevo en un minuto.",
      e_replaced: "Esta mesa está abierta en otra pestaña o en otro dispositivo.",
      us: "Nosotros", them: "Ellos", to_n: "a {n}", troef: "Troef", tricks: "Bazas", you: "Tú", partner: "pareja", pc: "computadora", host: "anfitrión",
      dealer: "Reparte", caller: "Caller", gone: "sin conexión",
      your_turn: "Te toca", turn_of: "Juega {name}",
      pick_t: "Elige el troef", pick_s: "Eres el caller. Elige el palo de triunfo con tus cinco primeras cartas.",
      picking: "{name} está eligiendo el troef…", called: "{name} canta troef",
      S: "Picas", H: "Corazones", C: "Tréboles", D: "Diamantes",
      follow: "Debes seguir el palo: juega {suit}", again_tap: "Toca otra vez para jugar",
      nopic_t: "No picture, no game", nopic_q: "No tienes rey, reina ni jota. ¿Pedir un nuevo reparto?", nopic_y: "Repartir de nuevo", nopic_n: "Jugar con estas cartas",
      nopic_o: "{name} no tiene figuras. Se reparte de nuevo.",
      kap_t: "¡Kap!", kap_q: "Siete bazas a cero. Para aquí y gana 5 puntos, o sigue por el baunie: las 13 bazas valen 15 puntos. Si pierdes una sola baza, el otro equipo gana 2.",
      kap_stop: "Kap partij: 5 puntos", kap_go: "Seguir por el baunie", kap_w: "¡Kap! {name} decide: ¿parar o baunie?", bau_go: "¡{name} sigue por el baunie!",
      r_win_us: "Ganamos la mano", r_win_them: "Ellos ganan la mano", r_kap_us: "¡Kap! Siete bazas a cero", r_kap_them: "Kap en contra",
      r_bau_us: "¡Baunie! Las 13 bazas", r_bau_them: "Baunie en contra", r_fail_us: "Su baunie falló", r_fail_them: "Nuestro baunie falló",
      pts_us: "+{n} para nosotros", pts_them: "+{n} para ellos", first: "{name} es el primer caller",
      o_win: "¡Ganas la partida!", o_lose: "Partida perdida", final: "Resultado final", again: "Jugar otra", again_in: "Nueva partida en {n} s",
      share: "Compartir por WhatsApp", lobby: "Salir de la mesa",
      sh_win: "Gané al Troefcall, {a}–{b}, en Explore Suriname. Ven a jugar: {url}", sh_any: "Ven a jugar Troefcall en Explore Suriname: {url}",
      w_code: "Código de la mesa", guest: "Invitado", w_title: "Mesa {code}", w_inv: "Invita a tus amigos", w_inv_s: "Envía este enlace. Quien lo abra se sienta en tu mesa.",
      wa: "Enviar por WhatsApp", copy: "Copiar enlace", copied: "Copiado", inv_txt: "¡Ven a jugar Troefcall conmigo! Mesa {code}: {url}",
      w_seats: "Quienes se sientan enfrente son pareja. Toca una silla vacía para cambiarte.", sit_here: "Sentarme aquí",
      len: "Duración de la partida", pts_n: "{n} puntos", start: "Empezar el juego", start_s: "La computadora ocupa las sillas vacías.", w_host: "Esperando a que {name} empiece…",
      n_lost: "Se perdió la conexión. Reconectando…", n_fail: "No se pudo reconectar.", retry: "Intentar de nuevo",
      away_t: "¿Sigues ahí?", away_q: "La computadora está jugando tus cartas.", back: "Ya volví",
      auto: "Se acabó el tiempo. La computadora jugó por {name}.", joined: "{name} se sentó", left: "{name} se fue. La computadora toma su lugar.",
      chat: "Chat", chat_ph: "Di algo…", send: "Enviar", chat_rule: "Con buen ambiente, y sin decirle tus cartas a tu pareja.",
      mute: "Silenciar", unmute: "Volver a mostrar", chat_empty: "Aún no hay mensajes.",
      sound: "Sonido", confirm: "Tocar dos veces para jugar una carta", rules: "Reglas", leave: "Salir de la mesa", leave_q: "¿Salir de esta mesa?", yes: "Sí, salir", no: "Quedarme",
      practice: "Práctica", close: "Cerrar", menu: "Menú"
    },
    zh: {
      name_lbl: "你的名字", name_ph: "牌桌上的名字", online: "当前 {n} 人在线",
      now: "马上开打", now_sub: "在线与牌桌上的玩家对战，空位由电脑补上。",
      friends: "和朋友一起玩", friends_sub: "开一张牌桌，把链接通过 WhatsApp 发给朋友。",
      code_lbl: "有牌桌代码？", code_ph: "代码", join: "加入",
      solo: "与电脑练习", solo_sub: "不用联网，按自己的节奏玩。",
      solo_resume: "继续练习赛（{a}–{b}）", solo_new: "新的练习赛",
      invited: "你被邀请到牌桌 {code}", join_table: "入座", back_table: "回到牌桌 {code}",
      record: "你的战绩：{p} 场胜 {w} 场", connecting: "连接中…",
      e_notfound: "这张牌桌已关闭。请新开一桌，或点“马上开打”。", e_full: "这张牌桌已满。",
      e_net: "游戏服务器没有响应。请检查网络，或先与电脑练习。",
      e_busy: "现在新开的牌桌太多，请一分钟后再试。",
      e_replaced: "这张牌桌已在另一个标签页或另一台设备上打开。",
      us: "我方", them: "对方", to_n: "打到 {n} 分", troef: "Troef", tricks: "墩数", you: "你", partner: "搭档", pc: "电脑", host: "桌主",
      dealer: "发牌", caller: "叫牌", gone: "离线",
      your_turn: "轮到你了", turn_of: "{name} 出牌中",
      pick_t: "选择 Troef（将牌）", pick_s: "你是叫牌人，请根据最先拿到的五张牌定将牌花色。",
      picking: "{name} 正在选 Troef…", called: "{name} 叫 Troef",
      S: "黑桃", H: "红心", C: "梅花", D: "方块",
      follow: "必须跟同花色：请出{suit}", again_tap: "再点一次出牌",
      nopic_t: "No picture, no game", nopic_q: "你手里没有 K、Q、J。要求重新发牌吗？", nopic_y: "重新发牌", nopic_n: "就用这手牌",
      nopic_o: "{name} 没有人头牌，重新发牌。",
      kap_t: "Kap！", kap_q: "七比零。现在停下得 5 分，或继续打 Baunie：13 墩全拿得 15 分。只要输一墩，对方得 2 分。",
      kap_stop: "Kap partij：5 分", kap_go: "继续打 Baunie", kap_w: "Kap！{name} 决定：停下还是打 Baunie？", bau_go: "{name} 继续打 Baunie！",
      r_win_us: "我方赢下这一局", r_win_them: "对方赢下这一局", r_kap_us: "Kap！七比零", r_kap_them: "被 Kap 了",
      r_bau_us: "Baunie！13 墩全拿", r_bau_them: "被 Baunie 了", r_fail_us: "对方 Baunie 失败", r_fail_them: "我方 Baunie 失败",
      pts_us: "我方 +{n}", pts_them: "对方 +{n}", first: "{name} 先叫牌",
      o_win: "你赢了这场比赛！", o_lose: "比赛输了", final: "最终比分", again: "再来一场", again_in: "{n} 秒后开始新比赛",
      share: "分享到 WhatsApp", lobby: "离开牌桌",
      sh_win: "我在 Explore Suriname 玩 Troefcall 赢了，{a}–{b}。一起来玩：{url}", sh_any: "来 Explore Suriname 玩 Troefcall：{url}",
      w_code: "牌桌代码", guest: "访客", w_title: "牌桌 {code}", w_inv: "邀请朋友", w_inv_s: "把这个链接发出去，打开的人就会坐到你的牌桌。",
      wa: "用 WhatsApp 发送", copy: "复制链接", copied: "已复制", inv_txt: "来和我玩 Troefcall！牌桌 {code}：{url}",
      w_seats: "对面坐的是搭档。点空位可以换座位。", sit_here: "坐这里",
      len: "比赛长度", pts_n: "{n} 分", start: "开始游戏", start_s: "空位由电脑补上。", w_host: "等待 {name} 开始…",
      n_lost: "连接中断，正在重新连接…", n_fail: "重新连接失败。", retry: "重试",
      away_t: "你还在吗？", away_q: "电脑正在替你出牌。", back: "我回来了",
      auto: "时间到，电脑替 {name} 出了牌。", joined: "{name} 入座了", left: "{name} 离开了，由电脑接手。",
      chat: "聊天", chat_ph: "说点什么…", send: "发送", chat_rule: "友好交流，不要把手里的牌告诉搭档。",
      mute: "屏蔽", unmute: "取消屏蔽", chat_empty: "还没有消息。",
      sound: "声音", confirm: "点两次才出牌", rules: "规则", leave: "离开牌桌", leave_q: "要离开这张牌桌吗？", yes: "离开", no: "留下",
      practice: "练习", close: "关闭", menu: "菜单"
    },
    fr: {
      name_lbl: "Votre nom", name_ph: "Nom à la table", online: "{n} joueurs en ligne en ce moment",
      now: "Jouer maintenant", now_sub: "En ligne avec les joueurs présents. L’ordinateur occupe les places libres.",
      friends: "Jouer entre amis", friends_sub: "Ouvrez une table et envoyez le lien par WhatsApp.",
      code_lbl: "Vous avez un code de table ?", code_ph: "Code", join: "Rejoindre",
      solo: "S’entraîner contre l’ordinateur", solo_sub: "Fonctionne sans internet, à votre rythme.",
      solo_resume: "Reprendre le match d’entraînement ({a}–{b})", solo_new: "Nouveau match d’entraînement",
      invited: "Vous êtes invité à la table {code}", join_table: "S’asseoir à la table", back_table: "Retour à la table {code}",
      record: "Vos matchs : {w} gagnés sur {p}", connecting: "Connexion…",
      e_notfound: "Cette table est fermée. Ouvrez-en une nouvelle ou touchez Jouer maintenant.", e_full: "Cette table est complète.",
      e_net: "Le serveur du jeu ne répond pas. Vérifiez votre connexion ou entraînez-vous contre l’ordinateur.",
      e_busy: "Beaucoup de tables s’ouvrent en ce moment. Réessayez dans une minute.",
      e_replaced: "Cette table est ouverte dans un autre onglet ou sur un autre appareil.",
      us: "Nous", them: "Eux", to_n: "en {n}", troef: "Troef", tricks: "Plis", you: "Vous", partner: "partenaire", pc: "ordinateur", host: "hôte",
      dealer: "Donneur", caller: "Caller", gone: "hors ligne",
      your_turn: "À vous de jouer", turn_of: "{name} joue",
      pick_t: "Choisissez le troef", pick_s: "Vous êtes le caller. Annoncez l’atout avec vos cinq premières cartes.",
      picking: "{name} choisit le troef…", called: "{name} annonce le troef",
      S: "Pique", H: "Cœur", C: "Trèfle", D: "Carreau",
      follow: "Vous devez fournir : jouez {suit}", again_tap: "Touchez encore pour jouer",
      nopic_t: "No picture, no game", nopic_q: "Vous n’avez ni roi, ni dame, ni valet. Demander une nouvelle donne ?", nopic_y: "Nouvelle donne", nopic_n: "Jouer ces cartes",
      nopic_o: "{name} n’a aucune figure. Nouvelle donne.",
      kap_t: "Kap !", kap_q: "Sept plis à zéro. Arrêtez ici pour 5 points, ou continuez pour le baunie : les 13 plis pour 15 points. Un seul pli perdu et l’autre équipe marque 2.",
      kap_stop: "Kap partij : 5 points", kap_go: "Continuer pour le baunie", kap_w: "Kap ! {name} décide : arrêter ou baunie ?", bau_go: "{name} continue pour le baunie !",
      r_win_us: "Nous gagnons la manche", r_win_them: "Ils gagnent la manche", r_kap_us: "Kap ! Sept plis à zéro", r_kap_them: "Kap contre nous",
      r_bau_us: "Baunie ! Les 13 plis", r_bau_them: "Baunie contre nous", r_fail_us: "Leur baunie a échoué", r_fail_them: "Notre baunie a échoué",
      pts_us: "+{n} pour nous", pts_them: "+{n} pour eux", first: "{name} est le premier caller",
      o_win: "Vous gagnez le match !", o_lose: "Match perdu", final: "Score final", again: "Rejouer", again_in: "Nouveau match dans {n} s",
      share: "Partager sur WhatsApp", lobby: "Quitter la table",
      sh_win: "J’ai gagné au Troefcall, {a}–{b}, sur Explore Suriname. Venez jouer : {url}", sh_any: "Venez jouer au Troefcall sur Explore Suriname : {url}",
      w_code: "Code de la table", guest: "Invité", w_title: "Table {code}", w_inv: "Invitez vos amis", w_inv_s: "Envoyez ce lien. Ceux qui l’ouvrent s’assoient à votre table.",
      wa: "Envoyer par WhatsApp", copy: "Copier le lien", copied: "Copié", inv_txt: "Venez jouer au Troefcall avec moi ! Table {code} : {url}",
      w_seats: "Les joueurs face à face sont partenaires. Touchez une place libre pour changer.", sit_here: "S’asseoir ici",
      len: "Durée du match", pts_n: "{n} points", start: "Lancer la partie", start_s: "L’ordinateur prend les places libres.", w_host: "En attente de {name}…",
      n_lost: "Connexion perdue. Reconnexion…", n_fail: "Reconnexion impossible.", retry: "Réessayer",
      away_t: "Toujours là ?", away_q: "L’ordinateur joue vos cartes.", back: "Je suis de retour",
      auto: "Temps écoulé. L’ordinateur a joué pour {name}.", joined: "{name} s’assoit", left: "{name} est parti. L’ordinateur prend le relais.",
      chat: "Chat", chat_ph: "Dites quelque chose…", send: "Envoyer", chat_rule: "Restez courtois et ne dites pas vos cartes à votre partenaire.",
      mute: "Masquer", unmute: "Réafficher", chat_empty: "Aucun message pour l’instant.",
      sound: "Son", confirm: "Toucher deux fois pour jouer une carte", rules: "Règles", leave: "Quitter la table", leave_q: "Quitter cette table ?", yes: "Oui, quitter", no: "Rester",
      practice: "Entraînement", close: "Fermer", menu: "Menu"
    },
    pt: {
      name_lbl: "Seu nome", name_ph: "Nome na mesa", online: "{n} jogando online agora",
      now: "Jogar agora", now_sub: "Online com quem estiver na mesa. O computador ocupa as cadeiras vazias.",
      friends: "Jogar com amigos", friends_sub: "Abra uma mesa e mande o link pelo WhatsApp.",
      code_lbl: "Tem um código de mesa?", code_ph: "Código", join: "Entrar",
      solo: "Treinar contra o computador", solo_sub: "Funciona sem internet, no seu ritmo.",
      solo_resume: "Continuar a partida de treino ({a}–{b})", solo_new: "Nova partida de treino",
      invited: "Você foi convidado para a mesa {code}", join_table: "Sentar à mesa", back_table: "Voltar para a mesa {code}",
      record: "Suas partidas: {w} vitórias em {p}", connecting: "Conectando…",
      e_notfound: "Esta mesa foi fechada. Abra uma nova ou toque em Jogar agora.", e_full: "Esta mesa está cheia.",
      e_net: "O servidor do jogo não respondeu. Verifique sua conexão ou treine contra o computador.",
      e_busy: "Muitas mesas sendo abertas agora. Tente de novo em um minuto.",
      e_replaced: "Esta mesa está aberta em outra aba ou em outro aparelho.",
      us: "Nós", them: "Eles", to_n: "até {n}", troef: "Troef", tricks: "Vazas", you: "Você", partner: "parceiro", pc: "computador", host: "anfitrião",
      dealer: "Carteador", caller: "Caller", gone: "offline",
      your_turn: "Sua vez", turn_of: "{name} está jogando",
      pick_t: "Escolha o troef", pick_s: "Você é o caller. Escolha o naipe de trunfo com as suas cinco primeiras cartas.",
      picking: "{name} está escolhendo o troef…", called: "{name} canta o troef",
      S: "Espadas", H: "Copas", C: "Paus", D: "Ouros",
      follow: "Você precisa seguir o naipe: jogue {suit}", again_tap: "Toque de novo para jogar",
      nopic_t: "No picture, no game", nopic_q: "Você não tem rei, dama nem valete. Pedir nova distribuição?", nopic_y: "Dar as cartas de novo", nopic_n: "Jogar com estas cartas",
      nopic_o: "{name} não tem figuras. As cartas serão dadas de novo.",
      kap_t: "Kap!", kap_q: "Sete vazas a zero. Pare agora e ganhe 5 pontos, ou siga para o baunie: as 13 vazas valem 15 pontos. Se perder uma única vaza, o outro time ganha 2.",
      kap_stop: "Kap partij: 5 pontos", kap_go: "Seguir para o baunie", kap_w: "Kap! {name} decide: parar ou baunie?", bau_go: "{name} segue para o baunie!",
      r_win_us: "Ganhamos a mão", r_win_them: "Eles ganham a mão", r_kap_us: "Kap! Sete vazas a zero", r_kap_them: "Kap contra nós",
      r_bau_us: "Baunie! As 13 vazas", r_bau_them: "Baunie contra nós", r_fail_us: "O baunie deles falhou", r_fail_them: "Nosso baunie falhou",
      pts_us: "+{n} para nós", pts_them: "+{n} para eles", first: "{name} é o primeiro caller",
      o_win: "Você venceu a partida!", o_lose: "Partida perdida", final: "Placar final", again: "Jogar de novo", again_in: "Nova partida em {n} s",
      share: "Compartilhar no WhatsApp", lobby: "Sair da mesa",
      sh_win: "Ganhei no Troefcall, {a}–{b}, no Explore Suriname. Vem jogar: {url}", sh_any: "Vem jogar Troefcall no Explore Suriname: {url}",
      w_code: "Código da mesa", guest: "Convidado", w_title: "Mesa {code}", w_inv: "Convide seus amigos", w_inv_s: "Mande este link. Quem abrir senta na sua mesa.",
      wa: "Mandar pelo WhatsApp", copy: "Copiar link", copied: "Copiado", inv_txt: "Vem jogar Troefcall comigo! Mesa {code}: {url}",
      w_seats: "Quem senta de frente joga junto. Toque numa cadeira vazia para trocar de lugar.", sit_here: "Sentar aqui",
      len: "Duração da partida", pts_n: "{n} pontos", start: "Começar o jogo", start_s: "O computador ocupa as cadeiras vazias.", w_host: "Esperando {name} começar…",
      n_lost: "Conexão perdida. Reconectando…", n_fail: "Não foi possível reconectar.", retry: "Tentar de novo",
      away_t: "Ainda está aí?", away_q: "O computador está jogando as suas cartas.", back: "Voltei",
      auto: "O tempo acabou. O computador jogou por {name}.", joined: "{name} sentou à mesa", left: "{name} saiu. O computador assume.",
      chat: "Chat", chat_ph: "Diga alguma coisa…", send: "Enviar", chat_rule: "Mantenha o clima bom e não conte suas cartas ao parceiro.",
      mute: "Silenciar", unmute: "Reativar", chat_empty: "Nenhuma mensagem ainda.",
      sound: "Som", confirm: "Tocar duas vezes para jogar uma carta", rules: "Regras", leave: "Sair da mesa", leave_q: "Sair desta mesa?", yes: "Sim, sair", no: "Ficar",
      practice: "Treino", close: "Fechar", menu: "Menu"
    }
  };
  /* said in Sranan at every table, never translated */
  var QUICK = ["Fa waka?", "Bun wroko!", "Kap!", "Tjé!", "No span", "Grantangi", "Wakti pikinso", "Prei baka?"];

  var LANG = String(document.documentElement.lang || "en").slice(0, 2).toLowerCase();
  if (!I18N[LANG]) LANG = "en";
  var L = I18N[LANG];
  if (LANG === "fr") for (var fk in L) L[fk] = L[fk].replace(/ ([?!:;])/g, " $1");
  function t(k, v) {
    var s = L[k] != null ? L[k] : (I18N.en[k] != null ? I18N.en[k] : k);
    if (v) for (var x in v) s = s.split("{" + x + "}").join(v[x]);
    return s;
  }

  /* ── small helpers ── */
  var D = document, W = window;
  function lsGet(k, d) { try { var v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch (e) { return d; } }
  function lsSet(k, v) { try { localStorage.setItem(k, JSON.stringify(v)); } catch (e) {} }
  function lsDel(k) { try { localStorage.removeItem(k); } catch (e) {} }
  function ga(n, p) { try { if (typeof W.gtag === "function") W.gtag("event", n, p || {}); } catch (e) {} }
  function el(tag, cls, txt) { var e = D.createElement(tag); if (cls) e.className = cls; if (txt != null) e.textContent = txt; return e; }
  function add(p) { for (var i = 1; i < arguments.length; i++) if (arguments[i]) p.appendChild(arguments[i]); return p; }
  function btn(cls, txt, fn) { var b = el("button", cls, txt); b.type = "button"; if (fn) b.addEventListener("click", fn); return b; }
  function wait(ms) { return new Promise(function (r) { setTimeout(r, ms); }); }
  function clone(o) { return JSON.parse(JSON.stringify(o)); }
  var reduced = W.matchMedia && W.matchMedia("(prefers-reduced-motion: reduce)").matches;
  var touch = W.matchMedia && W.matchMedia("(pointer: coarse)").matches;
  var GLYPH = { S: "♠︎", H: "♥︎", C: "♣︎", D: "♦︎" };
  var API = (root.getAttribute("data-api") || "").replace(/\/+$/, "");
  var RULES = root.getAttribute("data-rules") || "#tc-rules";

  var SET = lsGet("tc-set", null) || { sound: 1, confirm: touch ? 1 : 0 };
  var NAME = E.cleanName(lsGet("tc-name", ""));
  var PID = lsGet("tc-pid", "");
  if (!/^[A-Za-z0-9_-]{16,40}$/.test(PID)) {
    var abc = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789", a = new Uint8Array(24);
    (W.crypto || W.msCrypto).getRandomValues(a);
    PID = "";
    for (var i0 = 0; i0 < 24; i0++) PID += abc[a[i0] % abc.length];
    lsSet("tc-pid", PID);
  }

  /* ── state ── */
  var conn = null;       /* LocalConn or NetConn */
  var V = null;          /* what the table looks like right now (a snapshot, moved along by events) */
  var mode = "";         /* solo | now | friends | join */
  var queue = [], busy = false, sel = null, optim = null, dlAt = 0, dlFor = -1;
  var chat = [], unread = 0, muted = {}, chatOpen = false, menuOpen = false, leaveAsk = false;
  var net = "ok", resultEv = null, countedOver = "", restartAt = 0, toastT = 0, noteT = 0;
  var R = {};            /* DOM refs of the table screen */

  /* ── sound: tiny synth, no files ── */
  var AC = null;
  function tone(freq, dur, type, vol, when) {
    if (!SET.sound) return;
    try {
      AC = AC || new (W.AudioContext || W.webkitAudioContext)();
      if (AC.state === "suspended") AC.resume();
      var o = AC.createOscillator(), g = AC.createGain(), t0 = AC.currentTime + (when || 0);
      o.type = type || "sine"; o.frequency.value = freq;
      g.gain.setValueAtTime(0.0001, t0);
      g.gain.exponentialRampToValueAtTime(vol || 0.08, t0 + 0.012);
      g.gain.exponentialRampToValueAtTime(0.0001, t0 + dur);
      o.connect(g); g.connect(AC.destination); o.start(t0); o.stop(t0 + dur + 0.02);
    } catch (e) {}
  }
  var SND = {
    card: function () { tone(190, 0.07, "triangle", 0.12); tone(95, 0.05, "square", 0.03, 0.01); },
    turn: function () { tone(660, 0.12, "sine", 0.07); tone(880, 0.16, "sine", 0.06, 0.1); },
    won: function () { tone(523, 0.1, "sine", 0.06); tone(784, 0.16, "sine", 0.06, 0.09); },
    lost: function () { tone(330, 0.14, "sine", 0.05); tone(262, 0.2, "sine", 0.05, 0.1); },
    kap: function () { [523, 659, 784, 1047].forEach(function (f, i) { tone(f, 0.2, "triangle", 0.09, i * 0.11); }); },
    deal: function () { for (var i = 0; i < 5; i++) tone(240 + i * 14, 0.05, "triangle", 0.06, i * 0.07); }
  };
  function buzz(ms) { try { if (navigator.vibrate) navigator.vibrate(ms); } catch (e) {} }
  /* keep the phone awake at the table, and mark the tab when it is your turn in another tab */
  var wakeLock = null, baseTitle = D.title, cueKey = "";
  function awake(on) {
    try {
      if (on && navigator.wakeLock && !wakeLock && !D.hidden) navigator.wakeLock.request("screen").then(function (l) { wakeLock = l; l.addEventListener("release", function () { wakeLock = null; }); }, function () {});
      if (!on && wakeLock) { wakeLock.release(); wakeLock = null; }
    } catch (e) {}
  }
  function turnCue() {
    var g = V && V.g, mine = !!(g && g.turn === V.you && !busy && (g.phase === "play" || g.phase === "trump" || g.phase === "kap" || g.phase === "redeal") && V.phase === "game");
    D.title = (mine && D.hidden ? "\u25CF " : "") + baseTitle;
    if (!mine) return;
    var key = V.seq + ":" + g.phase + ":" + g.hand.length;
    if (key === cueKey) return;
    cueKey = key;
    if (g.phase === "play") { tone(740, 0.09, "sine", 0.045); buzz(25); }
  }

  /* ───────────────────────── lobby ───────────────────────── */

  function hashCode() {
    var m = /[#&]t=([A-Za-z2-9]{5})\b/.exec(location.hash || "");
    return m ? m[1].toUpperCase() : "";
  }
  function setHash(code) {
    try { history.replaceState(null, "", location.pathname + location.search + (code ? "#t=" + code : "")); } catch (e) {}
  }
  function inviteUrl(code) { return location.origin + location.pathname + "#t=" + code; }
  function saveName(inp) {
    NAME = E.cleanName(inp.value);
    lsSet("tc-name", NAME);
    return NAME;
  }

  function showLobby(msg) {
    if (conn) { try { conn.close(); } catch (e) {} conn = null; }
    awake(false); D.title = baseTitle;
    V = null; queue = []; busy = false; chat = []; unread = 0; chatOpen = false; menuOpen = false; leaveAsk = false; net = "ok"; mode = "";
    root.className = "tc tc-in-lobby";
    root.textContent = "";
    var box = el("div", "tc-lobby");
    var code = hashCode();
    if (msg) add(box, el("p", "tc-msg", msg));

    var nameRow = el("label", "tc-field");
    var inp = el("input", "tc-inp");
    inp.type = "text"; inp.maxLength = 14; inp.value = NAME; inp.placeholder = t("name_ph");
    inp.setAttribute("autocomplete", "nickname"); inp.setAttribute("enterkeyhint", "done");
    inp.addEventListener("change", function () { saveName(inp); });
    add(nameRow, el("span", "tc-lbl", t("name_lbl")), inp);
    add(box, nameRow);

    function need() { saveName(inp); if (!NAME) NAME = E.cleanName(t("guest") + " " + (10 + Math.floor(Math.random() * 90))); return true; }

    if (code) {
      var inv = el("div", "tc-invite");
      add(inv, el("p", "tc-inv-t", t("invited", { code: code })),
        btn("tc-btn tc-btn-p", t("join_table"), function () { need(); goOnline("join", code); }));
      add(box, inv);
    }
    var last = lsGet("tc-last", null);
    if (!code && last && last.code && Date.now() - last.at < 2 * 3600000)
      add(box, btn("tc-btn tc-btn-g tc-wide", t("back_table", { code: last.code }), function () { need(); goOnline("join", last.code); }));

    var opts = el("div", "tc-opts");
    var bNow = btn("tc-opt" + (code ? "" : " tc-opt-p"), null, function () { need(); goOnline("now"); });
    add(bNow, el("b", null, t("now")), el("span", null, t("now_sub")));
    var bFr = btn("tc-opt", null, function () { need(); goOnline("friends"); });
    add(bFr, el("b", null, t("friends")), el("span", null, t("friends_sub")));
    var solo = lsGet("tc-solo", null), soloLive = solo && solo.g && solo.g.phase !== "over" && solo.seats && solo.seats.some(function (x) { return x.pid === PID; });
    var bSolo = btn("tc-opt", null, function () { need(); goSolo(!!soloLive); });
    add(bSolo, el("b", null, soloLive ? t("solo_resume", { a: solo.g.scores[0], b: solo.g.scores[1] }) : t("solo")), el("span", null, t("solo_sub")));
    if (soloLive) {
      var me = 0;
      solo.seats.forEach(function (x, i) { if (x.pid === PID) me = i; });
      bSolo.firstChild.textContent = t("solo_resume", { a: solo.g.scores[me % 2], b: solo.g.scores[1 - me % 2] });
    }
    add(opts, bNow, bFr, bSolo);
    if (soloLive) add(opts, btn("tc-link", t("solo_new"), function () { need(); lsDel("tc-solo"); goSolo(false); }));
    add(box, opts);

    var joinRow = el("form", "tc-join");
    var cin = el("input", "tc-inp tc-code");
    cin.type = "text"; cin.maxLength = 5; cin.placeholder = t("code_ph"); cin.setAttribute("autocapitalize", "characters"); cin.setAttribute("autocomplete", "off");
    cin.setAttribute("aria-label", t("code_lbl"));
    var jb = el("button", "tc-btn tc-btn-g", t("join")); jb.type = "submit";
    joinRow.addEventListener("submit", function (ev) {
      ev.preventDefault();
      var c = cin.value.toUpperCase().replace(/[^A-Z2-9]/g, "");
      if (c.length !== 5) { cin.focus(); return; }
      need(); goOnline("join", c);
    });
    add(joinRow, el("span", "tc-lbl", t("code_lbl")), cin, jb);
    add(box, joinRow);

    var foot = el("p", "tc-foot");
    var st = lsGet("tc-stats", null);
    if (st && st.p) foot.textContent = t("record", { w: st.w || 0, p: st.p });
    var on = el("span", "tc-online"); on.hidden = true;
    add(box, on, foot);
    add(root, box);

    if (API) {
      fetch(API + "/stats").then(function (r) { return r.json(); }).then(function (j) {
        if (j && j.players > 0 && on.isConnected) { on.textContent = t("online", { n: j.players }); on.hidden = false; }
      }).catch(function () {});
    }
  }

  function goSolo(resume) {
    mode = "solo";
    ga("tc_start", { tc_mode: "solo" });
    conn = new LocalConn(resume);
    conn.open();
  }
  function goOnline(kind, code) {
    mode = kind;
    ga("tc_start", { tc_mode: kind });
    if (!API) { showLobby(t("e_net")); return; }
    root.textContent = "";
    add(root, add(el("div", "tc-lobby tc-wait"), el("p", "tc-msg", t("connecting"))));
    if (code) { conn = new NetConn(code); conn.open(); return; }
    var tried = "";
    function ask() {
      fetch(API + (kind === "now" ? "/quick" : "/new") + (tried ? "?not=" + tried : ""), { method: "POST" })
        .then(function (r) { return r.json().then(function (j) { return { s: r.status, j: j }; }); })
        .then(function (x) {
          if (x.s === 429) { showLobby(t("e_busy")); return; }
          if (!x.j || !x.j.code) throw new Error("no code");
          conn = new NetConn(x.j.code);
          conn.onFull = kind === "now" && !tried ? function () { tried = x.j.code; ask(); } : null;
          conn.open();
        })
        .catch(function () { showLobby(t("e_net")); });
    }
    ask();
  }

  /* ───────────────────────── connections ───────────────────────── */

  function LocalConn(resume) { this.resume = resume; this.T = null; this.local = true; }
  LocalConn.prototype.open = function () {
    var st = this.resume ? lsGet("tc-solo", null) : null;
    try { this.T = st ? new E.Table({ state: st }) : null; } catch (e) { this.T = null; }
    if (!this.T || this.T.seatOf(PID) < 0) this.T = new E.Table({ solo: true, target: 15 });
    this.T.join(PID, NAME, Date.now());
    this.pump();
  };
  LocalConn.prototype.send = function (m) {
    if (m.t === "leave") return;
    this.T.handle(PID, m, Date.now());
    this.pump();
  };
  LocalConn.prototype.pump = function () {
    var out = this.T.flush();
    lsSet("tc-solo", this.T.s);
    out.forEach(function (o) { setTimeout(function () { onMsg(o.msg); }, 0); });
  };
  LocalConn.prototype.close = function () {};

  function NetConn(code) { this.code = code; this.ws = null; this.tries = 0; this.ever = false; this.done = false; this.ka = 0; this.onFull = null; }
  NetConn.prototype.open = function () {
    var self = this, ws;
    try { ws = this.ws = new WebSocket(API.replace(/^http/, "ws") + "/ws?t=" + this.code); }
    catch (e) { this.fail(); return; }
    ws.onopen = function () {
      ws.send(JSON.stringify({ t: "hello", pid: PID, name: NAME }));
      clearInterval(self.ka);
      self.ka = setInterval(function () { try { if (ws.readyState === 1) ws.send("ping"); } catch (e) {} }, 25000);
    };
    ws.onmessage = function (ev) {
      if (ev.data === "pong" || self.done) return;
      var m;
      try { m = JSON.parse(ev.data); } catch (e) { return; }
      if (m.t === "u") { self.ever = true; self.tries = 0; setNet("ok"); }
      if (m.t === "err") {
        self.done = true;
        try { ws.close(); } catch (e) {}
        if (m.code === "full" && self.onFull) { self.onFull(); return; }
        if (m.code === "notfound" || m.code === "full") { lsDel("tc-last"); setHash(""); }
        showLobby(t(m.code === "full" ? "e_full" : m.code === "replaced" ? "e_replaced" : "e_notfound"));
        return;
      }
      onMsg(m);
    };
    ws.onclose = function () {
      clearInterval(self.ka);
      if (self.done || self.ws !== ws) return;
      self.fail();
    };
    ws.onerror = function () {};
  };
  NetConn.prototype.fail = function () {
    var self = this;
    if (this.done) return;
    this.tries++;
    if (!this.ever && this.tries > 2) { this.done = true; showLobby(t("e_net")); return; }
    if (this.tries > 8) { setNet("fail"); return; }
    if (this.ever) setNet("lost");
    setTimeout(function () { if (!self.done) self.open(); }, Math.min(8000, 500 * Math.pow(1.7, this.tries)));
  };
  NetConn.prototype.send = function (m) { try { if (this.ws && this.ws.readyState === 1) this.ws.send(JSON.stringify(m)); } catch (e) {} };
  NetConn.prototype.close = function () { this.done = true; clearInterval(this.ka); try { this.ws.close(); } catch (e) {} };
  NetConn.prototype.retryNow = function () { this.tries = 0; setNet("lost"); this.open(); };

  function setNet(s) { if (net === s) return; net = s; if (V) render(); }
  D.addEventListener("visibilitychange", function () {
    if (!D.hidden) { D.title = baseTitle; if (V) awake(true); }
    if (!D.hidden && conn && !conn.local && !conn.done && conn.ws && conn.ws.readyState > 1 && net !== "fail") { conn.tries = 0; conn.open(); }
  });

  /* ───────────────────────── messages ───────────────────────── */

  function onMsg(m) {
    if (m.t === "chat") { gotChat(m); return; }
    if (m.t !== "u") return;
    m.at = Date.now();
    if (!V) {
      V = m.s;
      if (!V.solo) { lsSet("tc-last", { code: V.code, at: Date.now() }); if (!V.pub) setHash(V.code); }
      buildTable();
      /* a game already under way: show it as it is, then follow along */
      useSnapshot(m);
      render();
      try { root.scrollIntoView({ block: "start", behavior: reduced ? "auto" : "smooth" }); } catch (e) {}
      return;
    }
    queue.push(m);
    runQueue();
  }
  function useSnapshot(m) {
    V = m.s;
    dlAt = V.dl ? m.at + V.dl : 0;
    dlFor = V.g ? V.g.turn : -1;
    restartAt = V.g && V.g.restart ? m.at + V.g.restart : 0;
    optim = null; sel = null;
    if (V.g && V.g.phase === "over") countMatch();
  }
  function countMatch() {
    var g = V.g, key = V.code + ":" + g.scores.join("-") + ":" + g.handNo + ":" + (g.stats ? g.stats.hands : 0);
    if (countedOver === key) return;
    countedOver = key;
    var st = lsGet("tc-stats", null) || { p: 0, w: 0 };
    st.p++; if (g.winner === V.you % 2) st.w++;
    lsSet("tc-stats", st);
    ga("tc_match_end", { tc_mode: mode, tc_result: g.winner === V.you % 2 ? "win" : "loss" });
  }
  function runQueue() {
    if (busy) return;
    busy = true;
    (function next() {
      if (!V || !queue.length) { busy = false; if (V) render(); return; }
      var m = queue.shift();
      var fast = D.hidden || queue.length > 2;
      var i = 0;
      (function step() {
        if (!V) { busy = false; return; }
        if (i >= m.ev.length) { useSnapshot(m); render(); next(); return; }
        showEvent(m.ev[i++], fast).then(step, step);
      })();
    })();
  }
  function nameOf(seat) { return seat === V.you ? t("you") : V.seats[seat].name; }
  function nm(seat) { return V.seats[seat].name; }

  function showEvent(e, fast) {
    var g = V.g, A = E.ANIM, me = V.you, d = fast ? 0 : 1;
    switch (e.e) {
      case "first":
        if (g) { g.scores = [0, 0]; g.phase = "idle"; g.winner = null; g.trick = []; g.hand = []; g.counts = [0, 0, 0, 0]; g.trump = null; g.tricks = [0, 0]; }
        V.phase = "game"; resultEv = null;
        note(t("first", { name: nm(e.seat) }), 2600);
        render();
        return wait(A.first * d);
      case "deal1":
        V.phase = "game";
        V.g = g = { phase: "trump", handNo: e.n, dealer: e.dealer, caller: e.caller, trump: null, turn: e.caller, lead: e.caller, trick: [], tricks: [0, 0],
          scores: g ? g.scores : [0, 0], target: g ? g.target : V.target, baunie: null, winner: null, last: g ? g.last : null, stats: g ? g.stats : null,
          counts: [0, 0, 0, 0], hand: e.h ? E.sortHand(e.h, null) : [], legal: [], restart: 0 };
        g.counts[e.caller] = 5;
        resultEv = null; dlAt = 0;
        render(true);
        SND.deal();
        return wait(A.deal1 * d);
      case "trump":
        g.trump = e.suit; g.hand = E.sortHand(g.hand, g.trump);
        render();
        toast(t("called", { name: nm(e.seat) }), e.suit, A.trump - 150);
        return wait(A.trump * d);
      case "deal2":
        g.counts = [13, 13, 13, 13]; g.phase = "play"; g.turn = g.lead = g.caller;
        if (e.h) g.hand = E.sortHand(e.h, g.trump);
        render(true);
        SND.deal();
        return wait(A.deal2 * d);
      case "nopic":
        g.phase = "redeal"; g.turn = e.seat; render();
        return wait(A.nopic * d);
      case "redeal":
        note(t("nopic_o", { name: nm(e.seat) }), 2400);
        return wait(A.redeal * d);
      case "keep":
        g.phase = "play"; render();
        return wait(A.keep * d);
      case "play":
        if (e.seat === me && optim === e.card) { optim = null; return wait(260 * d); }
        var from = null;
        if (!fast) {
          var src = e.seat === me ? R.hand.querySelector('[data-c="' + e.card + '"]') : R.seat[rel(e.seat)];
          if (src) from = src.getBoundingClientRect();
        }
        if (e.seat === me) g.hand = g.hand.filter(function (c) { return c !== e.card; });
        g.counts[e.seat] = Math.max(0, g.counts[e.seat] - 1);
        g.trick.push({ s: e.seat, c: e.card });
        g.turn = g.trick.length < 4 ? (e.seat + 1) % 4 : -1;
        g.phase = "play"; g.legal = []; sel = null;
        render();
        if (from) fly(R.slot[rel(e.seat)].firstChild, from);
        SND.card();
        return wait(A.play * d);
      case "trick":
        return collect(e, fast);
      case "kapq":
        g.phase = "kap"; g.turn = e.seat; render();
        toast(t("kap_t"), null, 900, "tc-toast-kap");
        SND.kap(); buzz(60);
        return wait(A.kapq * d);
      case "baunie":
        g.baunie = e.seat % 2; g.phase = "play"; g.turn = e.seat; render();
        note(t("bau_go", { name: nm(e.seat) }), 2600);
        return wait(A.baunie * d);
      case "end":
        g.scores = e.scores; g.tricks = e.tricks; g.phase = "handend"; g.turn = -1;
        resultEv = e;
        render();
        if (e.kind === "kap" || e.kind === "baunie") { if (e.team === me % 2) SND.kap(); else SND.lost(); }
        else if (e.team === me % 2) SND.won(); else SND.lost();
        return wait(A.end * d).then(function () { resultEv = null; });
      case "over":
        return wait(A.over * d);
      case "auto":
        note(t("auto", { name: nm(e.seat) }), 2600);
        return Promise.resolve();
      case "join":
        if (e.seat !== me) note(t("joined", { name: e.name }), 2600);
        return Promise.resolve();
      case "left":
        note(t("left", { name: e.name }), 3000);
        return Promise.resolve();
    }
    return Promise.resolve();
  }
  function collect(e, fast) {
    var g = V.g, A = E.ANIM, pos = rel(e.w);
    if (fast) { g.tricks = e.tricks; g.trick = []; g.turn = e.w; render(); return Promise.resolve(); }
    var slot = R.slot[pos];
    if (slot.firstChild) slot.firstChild.classList.add("tc-win");
    return wait(A.trick - 420).then(function () {
      if (!V) return;
      var to = (pos === "b" ? R.me : R.seat[pos]).getBoundingClientRect();
      ["b", "l", "t", "r"].forEach(function (p) {
        var c = R.slot[p].firstChild;
        if (!c || reduced) return;
        var r = c.getBoundingClientRect();
        c.style.transition = "transform .34s ease-in, opacity .34s ease-in";
        c.style.transform = "translate(" + (to.left + to.width / 2 - r.left - r.width / 2) + "px," + (to.top + to.height / 2 - r.top - r.height / 2) + "px) scale(.35)";
        c.style.opacity = "0";
      });
      if (e.w % 2 === V.you % 2) tone(620, 0.08, "sine", 0.04);
      return wait(360);
    }).then(function () {
      if (!V) return;
      g.tricks = e.tricks; g.trick = []; g.turn = e.w;
      render();
      return wait(60);
    });
  }
  function fly(card, from) {
    if (!card || reduced) return;
    var to = card.getBoundingClientRect();
    var dx = from.left + from.width / 2 - to.left - to.width / 2, dy = from.top + from.height / 2 - to.top - to.height / 2;
    var rot = card.style.getPropertyValue("--rot") || "0deg";
    card.style.transition = "none";
    card.style.transform = "translate(" + dx + "px," + dy + "px) scale(" + Math.max(0.5, Math.min(1.2, from.width / to.width)) + ")";
    void card.offsetWidth;
    card.style.transition = "transform .26s cubic-bezier(.2,.8,.25,1)";
    card.style.transform = "rotate(" + rot + ")";
  }

  /* ───────────────────────── table screen ───────────────────────── */

  function rel(seat) { return ["b", "l", "t", "r"][(seat - V.you + 4) % 4]; }
  function seatAt(pos) { return (V.you + { b: 0, l: 1, t: 2, r: 3 }[pos]) % 4; }

  function cardEl(c, cls) {
    var red = c[1] === "H" || c[1] === "D", r = c[0] === "T" ? "10" : c[0], face = "KQJ".indexOf(c[0]) >= 0;
    var d = el("div", "tc-card " + (red ? "tc-red" : "tc-blk") + (face ? " tc-face" : "") + (c[0] === "A" ? " tc-ace" : "") + (cls ? " " + cls : ""));
    d.setAttribute("data-c", c);
    var ix = el("span", "tc-ix");
    add(ix, el("b", null, r), el("i", null, GLYPH[c[1]]));
    var mid = el("span", "tc-pip");
    if (face) add(mid, el("b", null, r), el("i", null, GLYPH[c[1]]));
    else mid.textContent = GLYPH[c[1]];
    add(d, ix, mid);
    d.setAttribute("aria-label", r + " " + t(c[1]));
    d.setAttribute("role", "img");
    return d;
  }
  function icon(name) {
    var P = {
      back: "M15 5l-7 7 7 7", chat: "M4 5h16v11H9l-5 4z", menu: "M5 12h.01M12 12h.01M19 12h.01", x: "M6 6l12 12M18 6L6 18",
      send: "M4 12l16-7-6 16-3-6z", pc: "M4 5h16v10H4zM9 19h6M12 15v4"
    };
    var s = D.createElementNS("http://www.w3.org/2000/svg", "svg");
    s.setAttribute("viewBox", "0 0 24 24"); s.setAttribute("width", "20"); s.setAttribute("height", "20");
    s.setAttribute("fill", "none"); s.setAttribute("stroke", "currentColor"); s.setAttribute("stroke-width", name === "menu" ? "3" : "1.9");
    s.setAttribute("stroke-linecap", "round"); s.setAttribute("stroke-linejoin", "round"); s.setAttribute("aria-hidden", "true");
    var p = D.createElementNS("http://www.w3.org/2000/svg", "path");
    p.setAttribute("d", P[name]); s.appendChild(p);
    return s;
  }
  function ibtn(cls, ic, label, fn) { var b = btn("tc-ib " + cls, null, fn); b.appendChild(icon(ic)); b.setAttribute("aria-label", label); return b; }

  function buildTable() {
    root.className = "tc tc-in-game" + (V.solo ? " tc-solo" : "");
    root.textContent = "";
    R = { seat: {}, slot: {} };
    var game = el("div", "tc-game"), main = el("div", "tc-main");
    var top = el("div", "tc-top");
    R.title = el("span", "tc-title");
    R.score = el("div", "tc-score");
    R.chatBtn = ibtn("tc-chatbtn", "chat", t("chat"), function () { chatOpen = !chatOpen; if (chatOpen) unread = 0; render(); if (chatOpen && R.chatIn && !touch) R.chatIn.focus(); });
    R.badge = el("i", "tc-badge"); R.chatBtn.appendChild(R.badge);
    add(top, ibtn("tc-leave", "back", t("leave"), function () { leaveAsk = true; menuOpen = false; render(); }), R.title, R.score, R.chatBtn,
      ibtn("tc-menubtn", "menu", t("menu"), function () { menuOpen = !menuOpen; render(); }));
    var felt = R.felt = el("div", "tc-felt");
    R.hudL = el("div", "tc-hud tc-hud-l"); R.hudR = el("div", "tc-hud tc-hud-r");
    ["l", "t", "r"].forEach(function (p) {
      var s = R.seat[p] = el("div", "tc-seat tc-s-" + p);
      s.addEventListener("click", function () { seatTap(p); });
      felt.appendChild(s);
    });
    R.mid = el("div", "tc-mid");
    ["t", "l", "r", "b"].forEach(function (p) { R.slot[p] = el("div", "tc-slot tc-sl-" + p); R.mid.appendChild(R.slot[p]); });
    R.toast = el("div", "tc-toast"); R.toast.hidden = true;
    R.note = el("div", "tc-note"); R.note.hidden = true;
    R.me = el("div", "tc-me");
    R.status = el("div", "tc-status");
    R.hand = el("div", "tc-hand");
    R.ov = el("div", "tc-ov"); R.ov.hidden = true;
    R.menu = el("div", "tc-menu"); R.menu.hidden = true;
    add(felt, R.hudL, R.hudR, R.mid, R.note, R.toast, R.status, R.me, R.hand, R.ov, R.menu);
    R.hand.addEventListener("click", handTap);
    R.hand.addEventListener("keydown", function (ev) { if (ev.key === "Enter" || ev.key === " ") { ev.preventDefault(); handTap(ev); } });
    add(main, top, felt);
    R.chat = el("aside", "tc-chat");
    buildChat();
    add(game, main, R.chat);
    add(root, game);
    awake(true);
    layout();
  }

  function layout() {
    if (!R.felt) return;
    var w = R.felt.clientWidth || root.clientWidth || 360, vh = W.innerHeight || 700;
    var wide = w >= 640;
    var cw = Math.round(Math.max(44, Math.min(wide ? 86 : 70, w / (wide ? 9.2 : 6.1))));
    var fh = wide ? Math.max(520, Math.min(640, vh - 110)) : Math.max(456, Math.min(610, vh - 58));
    root.style.setProperty("--cw", cw + "px");
    root.style.setProperty("--fh", Math.round(fh) + "px");
    R.cw = cw; R.w = w;
    if (V) layHand();
  }
  var rsT = 0;
  W.addEventListener("resize", function () { clearTimeout(rsT); rsT = setTimeout(function () { layout(); }, 80); });

  function layHand() {
    var cards = R.hand.children, n = cards.length, cw = R.cw, ch = cw * 1.42, pad = 13, w = R.w - pad * 2;
    var maxStep = cw * 0.74, minStep = touch ? 31 : 24;
    var one = n > 1 ? Math.min(maxStep, (w - cw) / (n - 1)) : 0;
    var rows = (n > 7 && one < minStep) ? 2 : 1;
    var perRow = rows === 2 ? Math.ceil(n / 2) : n;
    for (var i = 0; i < n; i++) {
      var row = i < perRow ? 0 : 1, k = row === 0 ? perRow : n - perRow, j = row === 0 ? i : i - perRow;
      var step = k > 1 ? Math.min(maxStep, (w - cw) / (k - 1)) : 0;
      var total = cw + step * (k - 1);
      cards[i].style.left = Math.round(pad + (w - total) / 2 + j * step) + "px";
      cards[i].style.top = Math.round(rows === 2 ? row * ch * 0.6 : 0) + "px";
      cards[i].style.zIndex = String(10 + i);
    }
    var hh = Math.round(rows === 2 ? ch * 1.6 : ch);
    R.hand.style.height = hh + "px";
    root.style.setProperty("--hh", hh + "px");
  }

  function seatTap(pos) {
    if (!V || V.phase !== "wait") return;
    var s = seatAt(pos);
    if (V.seats[s].bot) conn.send({ t: "sit", seat: s });
  }
  function handTap(ev) {
    var c = ev.target.closest ? ev.target.closest(".tc-card") : null;
    if (!c || !V || !V.g) return;
    var g = V.g, card = c.getAttribute("data-c");
    if (busy || g.phase !== "play" || g.turn !== V.you || optim) return;
    if (g.legal.indexOf(card) < 0) {
      c.classList.remove("tc-shake"); void c.offsetWidth; c.classList.add("tc-shake");
      if (g.trick.length) note(t("follow", { suit: t(g.trick[0].c[1]) + " " + GLYPH[g.trick[0].c[1]] }), 2200);
      return;
    }
    if (SET.confirm && sel !== card) { sel = card; render(); return; }
    /* show it at once, the table confirms a moment later */
    var from = c.getBoundingClientRect();
    optim = card; sel = null;
    g.hand = g.hand.filter(function (x) { return x !== card; });
    g.counts[V.you] = Math.max(0, g.counts[V.you] - 1);
    g.trick.push({ s: V.you, c: card });
    g.legal = []; g.turn = -1; dlAt = 0;
    render();
    fly(R.slot.b.firstChild, from);
    SND.card();
    conn.send({ t: "play", card: card });
  }

  function seatBox(pos) {
    var s = seatAt(pos), st = V.seats[s], g = V.g, box = R.seat[pos];
    box.textContent = "";
    var waiting = V.phase === "wait";
    box.className = "tc-seat tc-s-" + pos + (g && g.turn === s && g.phase !== "over" && g.phase !== "handend" ? " tc-turn" : "") +
      (st.bot ? " tc-bot" : "") + (!st.bot && !st.conn ? " tc-off" : "") + (waiting && st.bot ? " tc-free" : "");
    var av = el("div", "tc-av");
    if (st.bot) av.appendChild(icon("pc")); else av.textContent = (st.name || "?").charAt(0).toUpperCase();
    var meta = el("div", "tc-meta");
    add(meta, el("b", "tc-nm", waiting && st.bot ? t("sit_here") : st.name));
    var sub = [];
    if (pos === "t") sub.push(t("partner"));
    if (st.bot && !(waiting)) sub.push(t("pc"));
    if (waiting && st.bot) sub.push(t("pc"));
    if (!st.bot && !st.conn) sub.push(t("gone"));
    if (!st.bot && V.host === s && !V.pub && !V.solo) sub.push(t("host"));
    if (sub.length) add(meta, el("small", null, sub.join(" · ")));
    add(box, av, meta);
    if (g && !waiting) {
      var tags = el("div", "tc-tags");
      if (g.caller === s) add(tags, el("i", "tc-tag tc-tag-c", t("caller")));
      if (g.dealer === s) add(tags, el("i", "tc-tag", t("dealer")));
      if (g.counts[s]) add(tags, el("i", "tc-cnt", String(g.counts[s])));
      add(box, tags);
    }
    var b = lastBubble(s);
    if (b) add(box, el("div", "tc-bub", b));
  }
  function lastBubble(seat) {
    for (var i = chat.length - 1; i >= 0; i--) {
      var c = chat[i];
      if (c.seat === seat) return (Date.now() - c.at < 4500 && !muted[c.name]) ? c.m : null;
    }
    return null;
  }

  function render(dealt) {
    if (!V || !R.felt) return;
    var g = V.g, me = V.you, my = me % 2, i;
    var myTurn = g && g.turn === me && !busy;
    /* top bar */
    R.title.textContent = V.solo ? t("practice") : t("w_title", { code: V.code });
    R.score.textContent = "";
    if (g) {
      add(R.score, add(el("span", "tc-sc tc-sc-us"), el("small", null, t("us")), el("b", null, String(g.scores[my]))),
        add(el("span", "tc-sc tc-sc-them"), el("b", null, String(g.scores[1 - my])), el("small", null, t("them"))),
        el("span", "tc-to", t("to_n", { n: g.target })));
    }
    R.chatBtn.hidden = !!V.solo;
    R.badge.hidden = !unread; R.badge.textContent = unread > 9 ? "9+" : String(unread);
    root.classList.toggle("tc-chat-open", chatOpen && !V.solo);
    /* seats */
    ["l", "t", "r"].forEach(seatBox);
    /* hud */
    R.hudL.textContent = ""; R.hudR.textContent = "";
    if (g && V.phase === "game") {
      var chip = el("div", "tc-troef" + (g.trump ? " tc-" + (g.trump === "H" || g.trump === "D" ? "red" : "blk") : " tc-none"));
      add(chip, el("span", "tc-troef-g", g.trump ? GLYPH[g.trump] : "?"));
      add(R.hudL, chip, add(el("div", "tc-troef-l"), el("small", null, t("troef")), el("b", null, g.trump ? t(g.trump) : "…")));
      var tr = el("div", "tc-tricks");
      [[t("us"), g.tricks[my], "us"], [t("them"), g.tricks[1 - my], "them"]].forEach(function (x) {
        var row = el("div", "tc-trow tc-trow-" + x[2]);
        add(row, el("small", null, x[0]));
        var pips = el("span", "tc-pips");
        for (var k = 0; k < Math.max(7, x[1]); k++) pips.appendChild(el("i", k < x[1] ? "on" : ""));
        add(row, pips, el("b", null, String(x[1])));
        tr.appendChild(row);
      });
      R.hudR.appendChild(tr);
    }
    /* trick */
    ["b", "l", "t", "r"].forEach(function (p) { R.slot[p].textContent = ""; });
    if (g) g.trick.forEach(function (pl) {
      var c = cardEl(pl.c), p = rel(pl.s), rot = { b: "2deg", l: "-5deg", t: "-2deg", r: "5deg" }[p];
      c.style.setProperty("--rot", rot); c.style.transform = "rotate(" + rot + ")";
      R.slot[p].appendChild(c);
    });
    /* me + hand */
    R.me.textContent = "";
    var mst = V.seats[me];
    add(R.me, el("b", "tc-nm", mst.name));
    if (g && V.phase === "game") {
      if (g.caller === me) add(R.me, el("i", "tc-tag tc-tag-c", t("caller")));
      if (g.dealer === me) add(R.me, el("i", "tc-tag", t("dealer")));
    }
    R.me.className = "tc-me" + (g && g.turn === me && g.phase !== "over" && g.phase !== "handend" ? " tc-turn" : "");
    R.hand.textContent = "";
    R.hand.className = "tc-hand";
    if (g) {
      var canPlay = myTurn && g.phase === "play" && !optim;
      if (canPlay && g.legal.length < g.hand.length) R.hand.className = "tc-hand tc-some";
      g.hand.forEach(function (c, ix) {
        var cls = "";
        if (g.trump && c[1] === g.trump) cls += " tc-tr";
        if (canPlay) cls += g.legal.indexOf(c) >= 0 ? " tc-ok" : " tc-no";
        if (sel === c) cls += " tc-sel";
        var ce = cardEl(c, cls);
        if (canPlay && g.legal.indexOf(c) >= 0) { ce.setAttribute("role", "button"); ce.tabIndex = 0; }
        if (dealt && !reduced) { ce.classList.add("tc-dealt"); ce.style.animationDelay = (ix * 45) + "ms"; }
        R.hand.appendChild(ce);
      });
    }
    layHand();
    /* status line */
    var txt = "", cls = "";
    if (g && V.phase === "game" && g.phase !== "over" && g.phase !== "handend" && g.turn >= 0) {
      if (g.turn === me) {
        if (g.phase === "play" && !busy) { txt = sel ? t("again_tap") : t("your_turn"); cls = " tc-mine"; }
      } else if (g.phase === "trump") txt = t("picking", { name: nm(g.turn) });
      else if (g.phase === "kap") txt = t("kap_w", { name: nm(g.turn) });
      else if (g.phase === "play" && !busy) txt = t("turn_of", { name: nm(g.turn) });
    }
    R.status.className = "tc-status" + cls; R.status.textContent = txt;
    if (txt && cls) { var bar = el("i", "tc-bar"); R.status.appendChild(bar); }
    R.status.hidden = !txt;
    renderOverlay(myTurn);
    renderMenu();
    renderChat();
    turnCue();
    tick();
  }

  function panel(cls) { var p = el("div", "tc-panel " + (cls || "")); R.ov.appendChild(p); return p; }
  function renderOverlay(myTurn) {
    var g = V.g, me = V.you, my = me % 2, p;
    var keepSuit = R.ov.getAttribute("data-k");
    var key = "";
    R.ov.textContent = "";
    R.ov.className = "tc-ov";
    if (net !== "ok" && !V.solo) {
      key = "net";
      p = panel("tc-p-net");
      add(p, el("p", "tc-p-t", net === "fail" ? t("n_fail") : t("n_lost")));
      if (net === "fail") add(p, btn("tc-btn tc-btn-p", t("retry"), function () { conn.retryNow(); }), btn("tc-link", t("lobby"), leaveNow));
    } else if (leaveAsk) {
      key = "leave";
      p = panel();
      add(p, el("p", "tc-p-t", t("leave_q")),
        add(el("div", "tc-row"), btn("tc-btn tc-btn-g", t("no"), function () { leaveAsk = false; render(); }), btn("tc-btn tc-btn-p", t("yes"), leaveNow)));
    } else if (V.phase === "wait") {
      key = "wait"; waitPanel();
    } else if (g && V.seats[me].away && g.phase !== "over") {
      key = "away";
      p = panel();
      add(p, el("p", "tc-p-t", t("away_t")), el("p", "tc-p-s", t("away_q")), btn("tc-btn tc-btn-p", t("back"), function () { conn.send({ t: "back" }); }));
    } else if (resultEv) {
      key = "res"; resultPanel(resultEv);
      R.ov.className = "tc-ov tc-ov-soft";
    } else if (g && g.phase === "over" && !busy) {
      key = "over"; overPanel();
    } else if (g && myTurn && g.phase === "trump") {
      key = "trump";
      p = panel("tc-p-trump");
      add(p, el("p", "tc-p-t", t("pick_t")), el("p", "tc-p-s", t("pick_s")));
      var row = el("div", "tc-suits");
      E.SUITS.forEach(function (s) {
        var n = g.hand.filter(function (c) { return c[1] === s; }).length;
        var b = btn("tc-suit " + (s === "H" || s === "D" ? "tc-red" : "tc-blk"), null, function () { conn.send({ t: "trump", suit: s }); R.ov.hidden = true; });
        add(b, el("span", null, GLYPH[s]), el("b", null, t(s)), el("small", null, "× " + n));
        row.appendChild(b);
      });
      p.appendChild(row);
      R.ov.className = "tc-ov tc-ov-top";
    } else if (g && myTurn && g.phase === "redeal") {
      key = "redeal";
      p = panel();
      add(p, el("p", "tc-p-t", t("nopic_t")), el("p", "tc-p-s", t("nopic_q")),
        add(el("div", "tc-row"), btn("tc-btn tc-btn-g", t("nopic_n"), function () { conn.send({ t: "redeal", yes: 0 }); }),
          btn("tc-btn tc-btn-p", t("nopic_y"), function () { conn.send({ t: "redeal", yes: 1 }); })));
      R.ov.className = "tc-ov tc-ov-top";
    } else if (g && myTurn && g.phase === "kap") {
      key = "kap";
      p = panel("tc-p-kap");
      add(p, el("p", "tc-p-big", t("kap_t")), el("p", "tc-p-s", t("kap_q")),
        add(el("div", "tc-row tc-col"), btn("tc-btn tc-btn-p", t("kap_stop"), function () { ga("tc_kap", { tc_choice: "kap" }); conn.send({ t: "kap", go: 0 }); }),
          btn("tc-btn tc-btn-g", t("kap_go"), function () { ga("tc_kap", { tc_choice: "baunie" }); conn.send({ t: "kap", go: 1 }); })));
      R.ov.className = "tc-ov tc-ov-top";
    }
    R.ov.hidden = !key;
    R.ov.setAttribute("data-k", key);
    if (key && key !== keepSuit && (key === "trump" || key === "kap") && !D.hidden) { SND.turn(); buzz(40); }
  }
  function resultPanel(e) {
    var mine = e.team === V.you % 2, w = mine ? "us" : "them";
    var k = { win: "r_win_", kap: "r_kap_", baunie: "r_bau_", fail: "r_fail_" }[e.kind] + w;
    var p = panel("tc-p-res " + (mine ? "tc-good" : "tc-bad"));
    add(p, el("p", e.kind === "win" || e.kind === "fail" ? "tc-p-t" : "tc-p-big", t(k)),
      el("p", "tc-p-pts", t(mine ? "pts_us" : "pts_them", { n: e.pts })),
      scoreLine(e.scores));
  }
  function scoreLine(sc) {
    var my = V.you % 2, d = el("div", "tc-final");
    add(d, add(el("span", "tc-sc-us"), el("small", null, t("us")), el("b", null, String(sc[my]))), el("i", null, "–"),
      add(el("span", "tc-sc-them"), el("b", null, String(sc[1 - my])), el("small", null, t("them"))));
    return d;
  }
  function overPanel() {
    var g = V.g, won = g.winner === V.you % 2, my = V.you % 2;
    var p = panel("tc-p-over " + (won ? "tc-good" : "tc-bad"));
    add(p, el("p", "tc-p-big", t(won ? "o_win" : "o_lose")), el("small", "tc-p-k", t("final")), scoreLine(g.scores));
    var again = btn("tc-btn tc-btn-p", t("again"), function () { conn.send({ t: "again" }); });
    R.again = el("small", "tc-p-s"); R.again.hidden = true;
    var url = location.origin + location.pathname;
    var txt = won ? t("sh_win", { a: g.scores[my], b: g.scores[1 - my], url: url }) : t("sh_any", { url: url });
    var sh = el("a", "tc-btn tc-btn-wa", t("share"));
    sh.href = "https://wa.me/?text=" + encodeURIComponent(txt); sh.target = "_blank"; sh.rel = "noopener";
    sh.addEventListener("click", function () { ga("tc_share", { tc_result: won ? "win" : "loss" }); });
    add(p, add(el("div", "tc-row tc-col"), again, sh), R.again, btn("tc-link", t("lobby"), leaveNow));
  }
  function waitPanel() {
    var host = V.host === V.you, p = panel("tc-p-wait");
    var url = inviteUrl(V.code);
    add(p, el("p", "tc-p-t", t("w_inv")), el("p", "tc-p-s", t("w_inv_s")));
    var link = add(el("div", "tc-codebox"), el("small", null, t("w_code")), el("b", null, V.code));
    var wa = el("a", "tc-btn tc-btn-wa", t("wa"));
    wa.href = "https://wa.me/?text=" + encodeURIComponent(t("inv_txt", { code: V.code, url: url })); wa.target = "_blank"; wa.rel = "noopener";
    wa.addEventListener("click", function () { ga("tc_invite", { tc_via: "wa" }); });
    var cp = btn("tc-btn tc-btn-g", t("copy"), function () {
      ga("tc_invite", { tc_via: "copy" });
      var done = function () { cp.textContent = t("copied"); setTimeout(function () { cp.textContent = t("copy"); }, 1800); };
      if (navigator.clipboard && navigator.clipboard.writeText) navigator.clipboard.writeText(url).then(done, function () {});
      else { var ta = el("textarea"); ta.value = url; D.body.appendChild(ta); ta.select(); try { D.execCommand("copy"); done(); } catch (e) {} ta.remove(); }
    });
    /* the four seats as a small table: opposite seats share a colour */
    var mini = el("div", "tc-mini");
    ["t", "l", "r", "b"].forEach(function (pos) {
      var s = seatAt(pos), st = V.seats[s];
      var b = btn("tc-ms tc-ms-" + (s % 2 === V.you % 2 ? "a" : "b") + (st.bot ? " tc-ms-free" : "") + (pos === "b" ? " tc-ms-me" : ""), null,
        function () { if (st.bot) conn.send({ t: "sit", seat: s }); });
      b.style.gridArea = pos;
      if (!st.bot) b.disabled = true;
      add(b, el("b", null, st.bot ? t("sit_here") : st.name),
        el("small", null, st.bot ? t("pc") : (pos === "b" ? t("you") : (!st.conn ? t("gone") : (V.host === s ? t("host") : (pos === "t" ? t("partner") : "\u00a0"))))));
      mini.appendChild(b);
    });
    mini.appendChild(el("div", "tc-mc"));
    add(p, link, add(el("div", "tc-row tc-row2"), wa, cp), mini, el("p", "tc-p-hint", t("w_seats")));
    if (host) {
      var len = el("div", "tc-len");
      add(len, el("small", null, t("len")));
      [10, 15, 20].forEach(function (n) {
        len.appendChild(btn("tc-pill" + (V.target === n ? " on" : ""), t("pts_n", { n: n }), function () { conn.send({ t: "opt", target: n }); }));
      });
      add(p, len, btn("tc-btn tc-btn-p tc-wide", t("start"), function () { conn.send({ t: "start" }); }), el("small", "tc-p-s", t("start_s")));
    } else {
      add(p, el("p", "tc-p-s tc-pulse", t("w_host", { name: V.host >= 0 ? V.seats[V.host].name : "…" })),
        el("small", "tc-p-k", t("len") + ": " + t("pts_n", { n: V.target })));
    }
    R.ov.className = "tc-ov tc-ov-wait";
  }
  function leaveNow() {
    if (conn) conn.send({ t: "leave" });
    if (V && !V.solo) { lsDel("tc-last"); setHash(""); }
    showLobby();
  }

  function renderMenu() {
    R.menu.hidden = !menuOpen;
    if (!menuOpen) return;
    R.menu.textContent = "";
    function tog(key, label) {
      var b = btn("tc-mi", null, function () { SET[key] = SET[key] ? 0 : 1; lsSet("tc-set", SET); sel = null; render(); });
      add(b, el("span", null, label), el("i", "tc-sw" + (SET[key] ? " on" : "")));
      b.setAttribute("aria-pressed", SET[key] ? "true" : "false");
      return b;
    }
    var rl = el("a", "tc-mi", t("rules")); rl.href = RULES;
    rl.addEventListener("click", function () { menuOpen = false; render(); });
    add(R.menu, tog("sound", t("sound")), tog("confirm", t("confirm")), rl,
      btn("tc-mi tc-mi-x", t("leave"), function () { menuOpen = false; leaveAsk = true; render(); }));
  }

  function toast(text, suit, ms, cls) {
    clearTimeout(toastT);
    R.toast.textContent = "";
    R.toast.className = "tc-toast " + (cls || "");
    if (suit) add(R.toast, el("span", "tc-toast-g " + (suit === "H" || suit === "D" ? "tc-red" : "tc-blk"), GLYPH[suit]));
    add(R.toast, el("b", null, text));
    if (suit) add(R.toast, el("small", null, t(suit)));
    R.toast.hidden = false;
    toastT = setTimeout(function () { if (R.toast) R.toast.hidden = true; }, ms || 1200);
  }
  function note(text, ms) {
    if (!R.note) return;
    clearTimeout(noteT);
    R.note.textContent = text; R.note.hidden = false;
    noteT = setTimeout(function () { if (R.note) R.note.hidden = true; }, ms || 2200);
  }

  /* turn clock + countdown to the next online match */
  function tick() {
    if (!V || !R.felt) return;
    var g = V.g, now = Date.now(), frac = -1;
    if (g && dlAt && !busy && g.turn === dlFor && g.turn >= 0 && !V.solo) {
      var total = (V.pub ? E.TURN_MS.pub : E.TURN_MS.priv) + (g.phase === "trump" ? 8000 : 0);
      frac = Math.max(0, Math.min(1, (dlAt - now) / total));
    }
    ["l", "t", "r"].forEach(function (p) {
      var on = frac >= 0 && g.turn === seatAt(p);
      R.seat[p].style.setProperty("--p", on ? String(frac) : "1");
      R.seat[p].classList.toggle("tc-low", on && frac < 0.25);
    });
    var bar = R.status.querySelector(".tc-bar");
    if (bar) { bar.style.transform = "scaleX(" + (frac >= 0 && g.turn === V.you ? frac : 1) + ")"; bar.classList.toggle("tc-low", frac >= 0 && frac < 0.25); }
    if (R.again && R.again.isConnected) {
      var left = restartAt ? Math.ceil((restartAt - now) / 1000) : 0;
      R.again.hidden = !(left > 0);
      if (left > 0) R.again.textContent = t("again_in", { n: left });
    }
    /* chat bubbles fade by themselves */
    var bubs = R.felt.querySelectorAll(".tc-bub");
    if (bubs.length) for (var i = 0; i < 4; i++) { var b = i !== V.you && lastBubble(i); if (!b) { var q = R.seat[rel(i)] && R.seat[rel(i)].querySelector(".tc-bub"); if (q) q.remove(); } }
  }
  setInterval(tick, 250);

  /* ───────────────────────── chat ───────────────────────── */

  function buildChat() {
    R.chat.textContent = "";
    var head = el("div", "tc-chat-h");
    add(head, el("b", null, t("chat")), ibtn("tc-chat-x", "x", t("close"), function () { chatOpen = false; render(); }));
    R.chatList = el("div", "tc-chat-l");
    var quick = el("div", "tc-quick");
    QUICK.forEach(function (q) { quick.appendChild(btn("tc-q", q, function () { sendChat(q); })); });
    var form = el("form", "tc-chat-f");
    R.chatIn = el("input", "tc-inp");
    R.chatIn.type = "text"; R.chatIn.maxLength = 140; R.chatIn.placeholder = t("chat_ph"); R.chatIn.setAttribute("autocomplete", "off");
    R.chatIn.setAttribute("enterkeyhint", "send"); R.chatIn.setAttribute("aria-label", t("chat"));
    var sb = el("button", "tc-ib tc-send"); sb.type = "submit"; sb.appendChild(icon("send")); sb.setAttribute("aria-label", t("send"));
    form.addEventListener("submit", function (ev) { ev.preventDefault(); var v = R.chatIn.value; R.chatIn.value = ""; sendChat(v); });
    add(form, R.chatIn, sb);
    add(R.chat, head, R.chatList, quick, form);
  }
  var chatSent = 0, lastSend = 0;
  function sendChat(v) {
    v = E.cleanChat(v);
    if (!v || !conn || !V || V.solo) return;
    if (Date.now() - lastSend < 950) return;
    lastSend = Date.now();
    conn.send({ t: "chat", m: v });
    if (!chatSent++) ga("tc_chat", { tc_mode: mode });
  }
  function gotChat(m) {
    if (!V) return;
    chat.push({ seat: m.seat, name: String(m.name || ""), m: String(m.m || ""), at: Date.now() });
    if (chat.length > 80) chat.shift();
    if (m.seat !== V.you && !muted[m.name]) {
      var wideOpen = W.matchMedia && W.matchMedia("(min-width: 980px)").matches;
      if (!chatOpen && !wideOpen) unread++;
    }
    render();
  }
  function renderChat() {
    if (!R.chatList || V.solo) return;
    var L2 = R.chatList, atEnd = L2.scrollHeight - L2.scrollTop - L2.clientHeight < 40;
    L2.textContent = "";
    add(L2, el("p", "tc-chat-rule", t("chat_rule")));
    if (!chat.length) add(L2, el("p", "tc-chat-e", t("chat_empty")));
    chat.forEach(function (c) {
      var mine = c.seat === V.you, row = el("div", "tc-cm" + (mine ? " tc-cm-me" : "") + (c.seat % 2 === V.you % 2 ? " tc-cm-us" : " tc-cm-them"));
      var who = el("b", null, mine ? t("you") : c.name);
      if (muted[c.name] && !mine) { add(row, who, el("span", "tc-cm-muted", "···")); }
      else add(row, who, el("span", null, c.m));
      if (!mine) row.appendChild(btn("tc-cm-mute", muted[c.name] ? t("unmute") : t("mute"), function () { muted[c.name] = !muted[c.name]; render(); }));
      L2.appendChild(row);
    });
    if (atEnd) L2.scrollTop = L2.scrollHeight;
  }

  /* ───────────────────────── start ───────────────────────── */
  W.addEventListener("hashchange", function () { if (!V && !conn) showLobby(); });
  if (location.hostname === "localhost") W.__tc = { view: function () { return V; }, conn: function () { return conn; }, msg: onMsg, busy: function () { return busy; } };
  showLobby();
})();
