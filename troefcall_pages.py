"""Troefcall (Games > Troefcall), added 11 Nov 2026.

Suriname's card game for two pairs: practice against the computer in the browser, and online
tables (invite link, "Play now", chat) through the esr-troefcall Worker (source: ../troefcall-worker/).

Files (all in the repo root):
  troefcall_engine.js  rules + computer players + table flow. The SAME file is pasted into the Worker
                       (troefcall-worker/build.js), so after any change here: rebuild and redeploy the Worker.
  troefcall_ui.js      table UI; all words in its I18N block (en/nl/es/zh/fr/pt, hand-written).
  troefcall.css        styling for the app and this page (no Tailwind classes anywhere in this section).
Page: troefcall.html (clean URL /troefcall). All static words are baked in per language with
data-l10n / data-l10n-group (resolved by build_i18n.apply_l10n), nothing goes through translations.json.

Everything this module needs from generate.py comes in through `ctx`: PAGE_HEAD, nav_html, footer_html, SITE_URL.
A missing JS/CSS file raises, so the build keeps the previous page instead of publishing a broken one.
"""
import html as _html
import json as _json
import os as _os

LANGS = ("en", "nl", "es", "zh", "fr", "pt")
IN_LANG = {"en": "en", "nl": "nl", "es": "es", "zh": "zh-Hans", "fr": "fr", "pt": "pt-BR"}
API = "https://esr-troefcall.surinamedomains.workers.dev"
_HERE = _os.path.dirname(_os.path.abspath(__file__))
FILES = ("troefcall_engine.js", "troefcall_ui.js", "troefcall.css")


def esc(s):
    return _html.escape(str(s), quote=True)


def _nb(s):
    """French: no-break space before : ; ? !"""
    for ch in ":;?!":
        s = s.replace(" " + ch, " " + ch)
    return s


def _fr(d):
    if isinstance(d, dict) and "fr" in d and isinstance(d["fr"], str):
        d = dict(d)
        d["fr"] = _nb(d["fr"])
    return d


def _lj(d):
    return esc(_json.dumps({k: v for k, v in d.items() if k != "en" and v}, ensure_ascii=False))


def tx(d, tag="span", cls="", extra=""):
    d = _fr(d)
    c = f' class="{cls}"' if cls else ""
    return f'<{tag}{c}{extra} translate="no" data-l10n="{_lj(d)}">{esc(d["en"])}</{tag}>'


def group_block(per_lang, tag="div", cls=""):
    c = f' class="{cls}"' if cls else ""
    kids = "".join(
        f'<div data-l10n-lang="{lg}"{"" if lg == "en" else " hidden"}>{per_lang[lg]}</div>'
        for lg in LANGS if per_lang.get(lg))
    return f'<{tag}{c} translate="no" data-l10n-group>{kids}</{tag}>'


def _read(name):
    with open(_os.path.join(_HERE, name), encoding="utf-8") as f:
        return f.read()


# ── words ────────────────────────────────────────────────────────────────────
U = {
    "home": {"en": "Home", "nl": "Home", "es": "Inicio", "zh": "首页", "fr": "Accueil", "pt": "Início"},
    "title": {
        "en": "Troefcall Online: Play Suriname's Card Game Free",
        "nl": "Troefcall online spelen: gratis Surinaams kaartspel",
        "es": "Troefcall online: el juego de cartas de Surinam, gratis",
        "zh": "Troefcall 在线玩：免费的苏里南纸牌游戏",
        "fr": "Troefcall en ligne : le jeu de cartes du Suriname",
        "pt": "Troefcall online: o jogo de cartas do Suriname, grátis"},
    "desc": {
        "en": "Play Troefcall online, free and without an app. Invite friends with a WhatsApp link, join a table that is playing now, or practise against the computer.",
        "nl": "Speel Troefcall online, gratis en zonder app. Nodig vrienden uit met een WhatsApp-link, schuif aan bij een tafel of oefen tegen de computer.",
        "es": "Juega Troefcall en línea, gratis y sin app. Invita a tus amigos con un enlace de WhatsApp, únete a una mesa o practica contra la computadora.",
        "zh": "免费在线玩 Troefcall，无需下载应用。用 WhatsApp 链接邀请朋友，加入正在进行的牌桌，或与电脑练习。",
        "fr": "Jouez au Troefcall en ligne, gratuit et sans application. Invitez vos amis par WhatsApp, rejoignez une table ou entraînez-vous contre l’ordinateur.",
        "pt": "Jogue Troefcall online, grátis e sem aplicativo. Convide amigos com um link do WhatsApp, entre numa mesa ou treine contra o computador."},
    "eyebrow": {"en": "Surinamese card game", "nl": "Surinaams kaartspel", "es": "Juego de cartas de Surinam",
                "zh": "苏里南纸牌游戏", "fr": "Jeu de cartes du Suriname", "pt": "Jogo de cartas do Suriname"},
    "lede": {
        "en": "The Surinamese card game for two pairs, in your browser. Seven tricks win the game, and seven to nil is a kap. Play online with friends or practise against the computer.",
        "nl": "Het Surinaamse kaartspel voor twee koppels, in je browser. Zeven slagen winnen de game, en zeven tegen nul is een kap. Speel online met vrienden of oefen tegen de computer.",
        "es": "El juego de cartas surinamés para dos parejas, en tu navegador. Siete bazas ganan la mano, y siete a cero es un kap. Juega en línea con amigos o practica contra la computadora.",
        "zh": "苏里南的二对二纸牌游戏，打开浏览器就能玩。先拿七墩赢下一局，七比零就是 Kap。可以和朋友在线对战，也可以与电脑练习。",
        "fr": "Le jeu de cartes surinamais à deux contre deux, dans votre navigateur. Sept plis gagnent la manche, et sept à zéro, c’est un kap. Jouez en ligne entre amis ou entraînez-vous contre l’ordinateur.",
        "pt": "O jogo de cartas surinamês para duas duplas, no seu navegador. Sete vazas ganham a mão, e sete a zero é um kap. Jogue online com amigos ou treine contra o computador."},
    "h_rules": {"en": "How to play Troefcall", "nl": "Zo speel je Troefcall", "es": "Cómo se juega al Troefcall",
                "zh": "Troefcall 怎么玩", "fr": "Comment jouer au Troefcall", "pt": "Como jogar Troefcall"},
    "h_score": {"en": "Points", "nl": "Punten", "es": "Puntos", "zh": "计分", "fr": "Points", "pt": "Pontos"},
    "h_words": {"en": "Words at the table", "nl": "Woorden aan tafel", "es": "Palabras de la mesa",
                "zh": "牌桌用语", "fr": "Les mots de la table", "pt": "Palavras da mesa"},
    "h_ways": {"en": "Three ways to play", "nl": "Drie manieren om te spelen", "es": "Tres formas de jugar",
               "zh": "三种玩法", "fr": "Trois façons de jouer", "pt": "Três jeitos de jogar"},
    "h_about": {"en": "About Troefcall", "nl": "Over Troefcall", "es": "Sobre el Troefcall",
                "zh": "关于 Troefcall", "fr": "À propos du Troefcall", "pt": "Sobre o Troefcall"},
    "h_faq": {"en": "Common questions", "nl": "Veelgestelde vragen", "es": "Preguntas frecuentes",
              "zh": "常见问题", "fr": "Questions fréquentes", "pt": "Perguntas frequentes"},
    "more": {"en": "More games", "nl": "Meer spellen", "es": "Más juegos", "zh": "更多游戏", "fr": "Autres jeux", "pt": "Mais jogos"},
    "noscript": {"en": "Troefcall is a browser game and needs JavaScript.", "nl": "Troefcall is een browserspel en heeft JavaScript nodig.",
                 "es": "Troefcall es un juego de navegador y necesita JavaScript.", "zh": "Troefcall 是网页游戏，需要启用 JavaScript。",
                 "fr": "Troefcall est un jeu de navigateur et a besoin de JavaScript.", "pt": "Troefcall é um jogo de navegador e precisa de JavaScript."},
}

STEPS = {
    "en": [
        ("Four players, two pairs", "Partners sit opposite each other. All 52 cards are used. The ace is the highest card, the two the lowest."),
        ("The caller names troef", "The player on the dealer's left is the caller. The caller gets five cards first and picks the troef suit (the trump suit) from those five. After that everyone is dealt up to thirteen cards."),
        ("No picture, no game", "A caller with no king, queen or jack among the thirteen cards may ask for a new deal."),
        ("Follow suit", "The caller plays the first card. You must play a card of the same suit when you have one. If you have none, play any card: a troef to take the trick, or a card you can miss."),
        ("Who wins the trick", "The highest troef wins. If nobody played troef, the highest card of the suit that was led wins. The winner plays the first card of the next trick."),
        ("Seven tricks win", "The first pair to take seven of the thirteen tricks wins the game, and play stops there."),
    ],
    "nl": [
        ("Vier spelers, twee koppels", "Partners zitten tegenover elkaar. Er wordt gespeeld met alle 52 kaarten. De aas is de hoogste kaart, de twee de laagste."),
        ("De caller maakt troef", "De speler links van de deler is de caller. De caller krijgt eerst vijf kaarten en kiest daaruit de troefkleur. Daarna krijgt iedereen kaarten tot dertien."),
        ("No picture, no game", "Een caller die in zijn dertien kaarten geen heer, vrouw of boer heeft, mag opnieuw laten delen."),
        ("Kleur bekennen", "De caller speelt de eerste kaart. Je moet een kaart van dezelfde kleur spelen als je die hebt. Heb je die niet, dan mag je elke kaart spelen: een troef om de slag te pakken, of een kaart die je kunt missen."),
        ("Wie wint de slag", "De hoogste troef wint. Is er niet getroefd, dan wint de hoogste kaart van de gevraagde kleur. De winnaar speelt de eerste kaart van de volgende slag."),
        ("Zeven slagen winnen", "Het koppel dat als eerste zeven van de dertien slagen heeft, wint de game. Daarna stopt het spel."),
    ],
    "es": [
        ("Cuatro jugadores, dos parejas", "Los compañeros se sientan uno frente al otro. Se juega con las 52 cartas. El as es la carta más alta y el dos la más baja."),
        ("El caller elige el troef", "El jugador a la izquierda de quien reparte es el caller. Recibe primero cinco cartas y con ellas elige el palo de triunfo, el troef. Después todos reciben cartas hasta tener trece."),
        ("No picture, no game", "Un caller que no tiene rey, reina ni jota entre sus trece cartas puede pedir que se reparta de nuevo."),
        ("Seguir el palo", "El caller juega la primera carta. Debes jugar una carta del mismo palo si la tienes. Si no la tienes, juega cualquier carta: un troef para llevarte la baza o una carta que no necesites."),
        ("Quién gana la baza", "Gana el troef más alto. Si nadie jugó troef, gana la carta más alta del palo de salida. Quien gana juega la primera carta de la siguiente baza."),
        ("Siete bazas ganan", "La primera pareja que consigue siete de las trece bazas gana la mano, y ahí termina el juego."),
    ],
    "zh": [
        ("四人两队", "搭档面对面坐。使用全部 52 张牌，A 最大，2 最小。"),
        ("叫牌人定 Troef", "发牌人左手边的玩家是叫牌人（caller）。他先拿五张牌，并从这五张里选定将牌花色，也就是 Troef。之后每人发满十三张。"),
        ("No picture, no game", "叫牌人的十三张牌里如果没有 K、Q、J，可以要求重新发牌。"),
        ("必须跟牌", "叫牌人先出第一张牌。手里有同花色的牌就必须跟出。没有的话可以出任意一张：出 Troef 赢下这一墩，或者垫一张不要的牌。"),
        ("谁赢这一墩", "最大的 Troef 获胜。如果没人出 Troef，则首引花色中最大的牌获胜。赢家出下一墩的第一张牌。"),
        ("先拿七墩获胜", "十三墩里先拿到七墩的一方赢下这一局，本局随即结束。"),
    ],
    "fr": [
        ("Quatre joueurs, deux équipes", "Les partenaires sont assis face à face. On joue avec les 52 cartes. L’as est la carte la plus forte, le deux la plus faible."),
        ("Le caller annonce le troef", "Le joueur à gauche du donneur est le caller. Il reçoit d’abord cinq cartes et choisit parmi elles la couleur d’atout, le troef. Ensuite, chacun reçoit des cartes jusqu’à en avoir treize."),
        ("No picture, no game", "Un caller qui n’a ni roi, ni dame, ni valet parmi ses treize cartes peut demander une nouvelle donne."),
        ("Fournir la couleur", "Le caller joue la première carte. Vous devez jouer une carte de la même couleur si vous en avez une. Sinon, jouez n’importe quelle carte : un troef pour prendre le pli, ou une carte dont vous pouvez vous passer."),
        ("Qui remporte le pli", "Le troef le plus fort l’emporte. Si personne n’a joué troef, c’est la plus forte carte de la couleur demandée qui gagne. Le gagnant joue la première carte du pli suivant."),
        ("Sept plis pour gagner", "La première équipe qui fait sept des treize plis gagne la manche, et le jeu s’arrête là."),
    ],
    "pt": [
        ("Quatro jogadores, duas duplas", "Os parceiros sentam de frente um para o outro. Joga-se com as 52 cartas. O ás é a carta mais alta e o dois a mais baixa."),
        ("O caller escolhe o troef", "O jogador à esquerda de quem dá as cartas é o caller. Ele recebe cinco cartas primeiro e escolhe entre elas o naipe de trunfo, o troef. Depois todos recebem cartas até completar treze."),
        ("No picture, no game", "Um caller sem rei, dama ou valete entre as treze cartas pode pedir que as cartas sejam dadas de novo."),
        ("Seguir o naipe", "O caller joga a primeira carta. Você precisa jogar uma carta do mesmo naipe se tiver. Se não tiver, jogue qualquer carta: um troef para ganhar a vaza ou uma carta que não faça falta."),
        ("Quem ganha a vaza", "O troef mais alto ganha. Se ninguém jogou troef, ganha a carta mais alta do naipe de saída. Quem ganha joga a primeira carta da vaza seguinte."),
        ("Sete vazas ganham", "A primeira dupla a fazer sete das treze vazas ganha a mão, e o jogo para ali."),
    ],
}

SCORE = {
    "en": [("Seven tricks, the other pair has at least one", "2 points"),
           ("Kap: seven tricks to nil, and you stop", "5 points"),
           ("Baunie: you play on after a kap and take all thirteen tricks", "15 points"),
           ("Failed baunie: you play on and lose a trick", "2 points for the other pair")],
    "nl": [("Zeven slagen, de tegenpartij heeft er minstens één", "2 punten"),
           ("Kap: zeven slagen tegen nul, en je stopt", "5 punten"),
           ("Baunie: je speelt door na een kap en haalt alle dertien slagen", "15 punten"),
           ("Mislukte baunie: je speelt door en verliest een slag", "2 punten voor de tegenpartij")],
    "es": [("Siete bazas, la otra pareja tiene al menos una", "2 puntos"),
           ("Kap: siete bazas a cero, y paras", "5 puntos"),
           ("Baunie: sigues después de un kap y te llevas las trece bazas", "15 puntos"),
           ("Baunie fallido: sigues y pierdes una baza", "2 puntos para la otra pareja")],
    "zh": [("拿到七墩，对方至少有一墩", "2 分"),
           ("Kap：七比零，并且就此停下", "5 分"),
           ("Baunie：Kap 之后继续打，十三墩全拿", "15 分"),
           ("Baunie 失败：继续打却输了一墩", "对方得 2 分")],
    "fr": [("Sept plis, l’autre équipe en a au moins un", "2 points"),
           ("Kap : sept plis à zéro, et vous arrêtez", "5 points"),
           ("Baunie : vous continuez après un kap et faites les treize plis", "15 points"),
           ("Baunie manqué : vous continuez et perdez un pli", "2 points pour l’autre équipe")],
    "pt": [("Sete vazas, a outra dupla tem pelo menos uma", "2 pontos"),
           ("Kap: sete vazas a zero, e você para", "5 pontos"),
           ("Baunie: você segue depois de um kap e faz as treze vazas", "15 pontos"),
           ("Baunie falhou: você segue e perde uma vaza", "2 pontos para a outra dupla")],
}

AFTER = {
    "en": ["After a kap, the player who won the seventh trick decides: stop and take 5 points, or play on for baunie. When the caller's pair scores, the same player deals again and the same caller names troef. When the other pair scores, the caller becomes the dealer and the player on the caller's left is the new caller. The first pair to reach 15 points wins the match; the host of a table can also choose 10 or 20.",
           "One difference from a real table: there, the partner of the seventh-trick winner may also tap off a kap, which then counts for 2 points. Online only the winner of the seventh trick decides."],
    "nl": ["Na een kap beslist de speler die de zevende slag won: stoppen voor 5 punten of doorspelen voor baunie. Scoort het koppel van de caller, dan deelt dezelfde speler opnieuw en maakt dezelfde caller weer troef. Scoort de tegenpartij, dan wordt de caller de deler en is de speler links van hem de nieuwe caller. Het koppel dat als eerste 15 punten heeft, wint de wedstrijd. De host van een tafel kan ook 10 of 20 punten kiezen.",
           "Eén verschil met een echte tafel: daar mag ook de partner van de speler met de zevende slag een kap aftikken, en dan telt hij voor 2 punten. Online beslist alleen de speler die de zevende slag won."],
    "es": ["Después de un kap decide quien ganó la séptima baza: parar y sumar 5 puntos, o seguir por el baunie. Si puntúa la pareja del caller, reparte el mismo jugador y el mismo caller vuelve a elegir el troef. Si puntúa la otra pareja, el caller pasa a repartir y el jugador a su izquierda es el nuevo caller. La primera pareja que llega a 15 puntos gana la partida; el anfitrión de una mesa también puede elegir 10 o 20.",
           "Una diferencia con una mesa real: allí también el compañero de quien ganó la séptima baza puede cerrar un kap, y entonces vale 2 puntos. En línea solo decide quien ganó la séptima baza."],
    "zh": ["打出 Kap 之后，由赢下第七墩的玩家决定：停下拿 5 分，还是继续打 Baunie。叫牌方得分时，发牌人和叫牌人都不变。对方得分时，原叫牌人改为发牌，他左手边的玩家成为新的叫牌人。先到 15 分的一方赢得整场比赛；桌主也可以把比赛设为 10 分或 20 分。",
           "与线下牌桌有一点不同：线下时，赢下第七墩的玩家的搭档也可以叫停 Kap，那样只算 2 分。在线对局只由赢下第七墩的玩家决定。"],
    "fr": ["Après un kap, c’est le joueur qui a remporté le septième pli qui décide : arrêter et marquer 5 points, ou continuer pour le baunie. Si l’équipe du caller marque, le même joueur redonne et le même caller annonce de nouveau le troef. Si l’autre équipe marque, le caller devient donneur et le joueur à sa gauche est le nouveau caller. La première équipe à 15 points gagne le match ; l’hôte d’une table peut aussi choisir 10 ou 20.",
           "Une différence avec une vraie table : là, le partenaire du joueur qui a remporté le septième pli peut lui aussi arrêter un kap, qui ne vaut alors que 2 points. En ligne, seul le gagnant du septième pli décide."],
    "pt": ["Depois de um kap, quem ganhou a sétima vaza decide: parar e marcar 5 pontos, ou seguir para o baunie. Quando a dupla do caller pontua, o mesmo jogador dá as cartas de novo e o mesmo caller escolhe o troef outra vez. Quando a outra dupla pontua, o caller passa a dar as cartas e o jogador à esquerda dele vira o novo caller. A primeira dupla a chegar a 15 pontos vence a partida; o anfitrião de uma mesa também pode escolher 10 ou 20.",
           "Uma diferença em relação à mesa de verdade: lá, o parceiro de quem ganhou a sétima vaza também pode encerrar um kap, que então vale 2 pontos. Online só decide quem ganhou a sétima vaza."],
}

WORDS = {
    "en": [("Troef", "the trump suit: its cards beat every other suit."), ("Caller", "the player who names troef."),
           ("Kap", "seven tricks while the other pair has none."), ("Kap partij", "what you say, or a tap on the table, to stop after a kap."),
           ("Baunie", "all thirteen tricks. Also called bom."), ("Prent", "a picture card: king, queen or jack.")],
    "nl": [("Troef", "de troefkleur: die kaarten slaan elke andere kleur."), ("Caller", "de speler die troef maakt."),
           ("Kap", "zeven slagen terwijl de tegenpartij er geen heeft."), ("Kap partij", "wat je zegt, of een tik op tafel, om na een kap te stoppen."),
           ("Baunie", "alle dertien slagen. Ook wel bom genoemd."), ("Prent", "een plaatje: heer, vrouw of boer.")],
    "es": [("Troef", "el palo de triunfo: sus cartas ganan a todos los demás palos."), ("Caller", "el jugador que elige el troef."),
           ("Kap", "siete bazas mientras la otra pareja no tiene ninguna."), ("Kap partij", "lo que se dice, o un golpecito en la mesa, para parar después de un kap."),
           ("Baunie", "las trece bazas. También se le dice bom."), ("Prent", "una figura: rey, reina o jota.")],
    "zh": [("Troef", "将牌花色，这门花色的牌大过其他所有花色。"), ("Caller", "定 Troef 的玩家，即叫牌人。"),
           ("Kap", "一方拿到七墩而对方一墩未得。"), ("Kap partij", "打出 Kap 后叫停时说的话，也可以轻敲桌面表示。"),
           ("Baunie", "十三墩全拿，也叫 bom。"), ("Prent", "人头牌：K、Q、J。")],
    "fr": [("Troef", "la couleur d’atout : ses cartes battent toutes les autres couleurs."), ("Caller", "le joueur qui annonce le troef."),
           ("Kap", "sept plis alors que l’autre équipe n’en a aucun."), ("Kap partij", "ce que l’on dit, ou un petit coup sur la table, pour arrêter après un kap."),
           ("Baunie", "les treize plis. On dit aussi bom."), ("Prent", "une figure : roi, dame ou valet.")],
    "pt": [("Troef", "o naipe de trunfo: as cartas dele ganham de todos os outros naipes."), ("Caller", "o jogador que escolhe o troef."),
           ("Kap", "sete vazas enquanto a outra dupla não tem nenhuma."), ("Kap partij", "o que se diz, ou uma batidinha na mesa, para parar depois de um kap."),
           ("Baunie", "as treze vazas. Também chamado de bom."), ("Prent", "uma figura: rei, dama ou valete.")],
}

WAYS = {
    "en": [("Play now", "You sit down at a table that is open. Computer players hold the empty seats until more people arrive, so you never wait."),
           ("With friends", "Open a table and send the link on WhatsApp. Choose who sits opposite whom and how long the match is: 10, 15 or 20 points."),
           ("Against the computer", "Three computer players at your table. It keeps working without internet once the page is open, and your match is saved on your phone.")],
    "nl": [("Nu spelen", "Je schuift aan bij een open tafel. Computerspelers houden de lege stoelen bezet tot er meer mensen komen, dus je hoeft nooit te wachten."),
           ("Met vrienden", "Open een tafel en stuur de link via WhatsApp. Kies wie tegenover wie zit en hoe lang de wedstrijd duurt: 10, 15 of 20 punten."),
           ("Tegen de computer", "Drie computerspelers aan je tafel. Het werkt ook zonder internet zodra de pagina open is, en je wedstrijd wordt op je telefoon bewaard.")],
    "es": [("Jugar ahora", "Te sientas en una mesa abierta. La computadora ocupa las sillas vacías hasta que llegue más gente, así que nunca esperas."),
           ("Con amigos", "Abre una mesa y envía el enlace por WhatsApp. Elige quién se sienta frente a quién y cuánto dura la partida: 10, 15 o 20 puntos."),
           ("Contra la computadora", "Tres jugadores de la computadora en tu mesa. Sigue funcionando sin internet una vez abierta la página, y tu partida se guarda en tu teléfono.")],
    "zh": [("马上开打", "直接坐到一张开放的牌桌。空位先由电脑顶上，有人来了再让座，所以不用等待。"),
           ("和朋友一起", "开一张牌桌，把链接用 WhatsApp 发出去。可以安排谁和谁做搭档，并选择比赛长度：10、15 或 20 分。"),
           ("与电脑对战", "和三位电脑玩家同桌。页面打开后不联网也能玩，比赛进度保存在你的手机上。")],
    "fr": [("Jouer maintenant", "Vous vous asseyez à une table ouverte. L’ordinateur garde les places libres jusqu’à l’arrivée d’autres joueurs : vous n’attendez jamais."),
           ("Entre amis", "Ouvrez une table et envoyez le lien par WhatsApp. Choisissez qui s’assoit en face de qui et la durée du match : 10, 15 ou 20 points."),
           ("Contre l’ordinateur", "Trois joueurs ordinateur à votre table. Cela fonctionne sans internet une fois la page ouverte, et votre match est enregistré sur votre téléphone.")],
    "pt": [("Jogar agora", "Você senta numa mesa aberta. O computador segura as cadeiras vazias até chegar mais gente, então você nunca espera."),
           ("Com amigos", "Abra uma mesa e mande o link pelo WhatsApp. Escolha quem senta de frente para quem e a duração da partida: 10, 15 ou 20 pontos."),
           ("Contra o computador", "Três jogadores do computador na sua mesa. Funciona sem internet depois que a página abre, e a sua partida fica salva no seu celular.")],
}
WAYS_NOTE = {
    "en": "If someone leaves, a computer player takes over at once. If your connection drops, your seat and your cards are kept while you reconnect.",
    "nl": "Gaat iemand weg, dan neemt een computerspeler het meteen over. Valt je verbinding weg, dan blijven je stoel en je kaarten bewaard terwijl je opnieuw verbindt.",
    "es": "Si alguien se va, la computadora toma su lugar al instante. Si se cae tu conexión, tu silla y tus cartas se guardan mientras te reconectas.",
    "zh": "有人离开时，电脑会立刻接手。如果你掉线了，座位和手牌会为你保留，重新连上即可继续。",
    "fr": "Si quelqu’un part, l’ordinateur prend aussitôt le relais. Si votre connexion tombe, votre place et vos cartes sont conservées pendant la reconnexion.",
    "pt": "Se alguém sai, o computador assume na hora. Se a sua conexão cair, a sua cadeira e as suas cartas ficam guardadas enquanto você reconecta.",
}

ABOUT = {
    "en": "Troefcall is played all over Suriname and by Surinamese families in the Netherlands: at birthdays, on the veranda and in clubs. It is also known as troeftjaal and is closely related to Court Piece, a card game from India. Clubs play league matches under the Surinaamse Troefcall Bond in Suriname and the Troefcall Sport Bond Nederland (TSBN), founded in 1996. This table follows the TSBN competition rules.",
    "nl": "Troefcall wordt in heel Suriname gespeeld en door Surinaamse families in Nederland: op verjaardagen, op het balkon en in verenigingen. Het spel heet ook wel troeftjaal en is nauw verwant aan Court Piece, een kaartspel uit India. Verenigingen spelen competitie bij de Surinaamse Troefcall Bond in Suriname en de Troefcall Sport Bond Nederland (TSBN), opgericht in 1996. Deze tafel volgt de wedstrijdregels van de TSBN.",
    "es": "El Troefcall se juega en todo Surinam y entre las familias surinamesas de los Países Bajos: en cumpleaños, en el balcón y en clubes. También se conoce como troeftjaal y está muy emparentado con el Court Piece, un juego de cartas de la India. Los clubes compiten en la Surinaamse Troefcall Bond en Surinam y en la Troefcall Sport Bond Nederland (TSBN), fundada en 1996. Esta mesa sigue las reglas de competición de la TSBN.",
    "zh": "Troefcall 在苏里南各地以及荷兰的苏里南家庭中都很流行，生日聚会、阳台上、俱乐部里都能见到。它也叫 troeftjaal，与源自印度的纸牌游戏 Court Piece 关系很近。苏里南的 Surinaamse Troefcall Bond 和 1996 年成立的荷兰 Troefcall Sport Bond Nederland（TSBN）都组织俱乐部联赛。本牌桌采用 TSBN 的比赛规则。",
    "fr": "Le Troefcall se joue partout au Suriname et dans les familles surinamaises des Pays-Bas : aux anniversaires, sur la véranda et en club. On l’appelle aussi troeftjaal, et il est très proche du Court Piece, un jeu de cartes venu d’Inde. Les clubs disputent un championnat au sein de la Surinaamse Troefcall Bond au Suriname et de la Troefcall Sport Bond Nederland (TSBN), fondée en 1996. Cette table suit les règles de compétition de la TSBN.",
    "pt": "O Troefcall é jogado em todo o Suriname e pelas famílias surinamesas na Holanda: em aniversários, na varanda e em clubes. Também é conhecido como troeftjaal e é parente próximo do Court Piece, um jogo de cartas da Índia. Os clubes disputam campeonatos na Surinaamse Troefcall Bond, no Suriname, e na Troefcall Sport Bond Nederland (TSBN), fundada em 1996. Esta mesa segue as regras de competição da TSBN.",
}

FAQ = {
    "en": [
        ("Is Troefcall on Explore Suriname free?", "Yes. There is no app to install and no account to make. Type a name and sit down."),
        ("How do I play Troefcall online with friends?", "Tap Play with friends. You get a table with its own link and a five-letter code. Send the link on WhatsApp and whoever opens it sits down at your table. Choose who sits opposite whom, then start. The computer plays the empty seats."),
        ("Can I play Troefcall alone?", "Yes. Practise against the computer puts three computer players at your table. Or tap Play now to sit down with people who are online at that moment."),
        ("What is a kap?", "A kap is seven tricks while the other pair has none. It is worth 5 points instead of 2. After a kap you may play on for baunie, all thirteen tricks, for 15 points. If you then lose a single trick, the other pair gets 2 points."),
        ("Who chooses troef?", "The caller, the player on the dealer's left. The caller has seen only five cards when naming troef."),
        ("What happens when a player leaves?", "A computer player takes over at once, so the game goes on. If your own connection drops, your seat is kept for a while and you get your cards back when you return."),
    ],
    "nl": [
        ("Is Troefcall op Explore Suriname gratis?", "Ja. Je hoeft geen app te installeren en geen account te maken. Typ een naam en schuif aan."),
        ("Hoe speel ik Troefcall online met vrienden?", "Tik op Met vrienden spelen. Je krijgt een tafel met een eigen link en een code van vijf tekens. Stuur de link via WhatsApp en wie hem opent, schuift aan bij jouw tafel. Kies wie tegenover wie zit en start het spel. De computer speelt op de lege stoelen."),
        ("Kan ik Troefcall alleen spelen?", "Ja. Met Oefenen tegen de computer zitten er drie computerspelers aan je tafel. Of tik op Nu spelen en schuif aan bij mensen die op dat moment online zijn."),
        ("Wat is een kap?", "Een kap is zeven slagen terwijl de tegenpartij er geen heeft. Een kap is 5 punten waard in plaats van 2. Na een kap mag je doorspelen voor baunie, alle dertien slagen, voor 15 punten. Verlies je dan één slag, dan krijgt de tegenpartij 2 punten."),
        ("Wie maakt troef?", "De caller, de speler links van de deler. De caller heeft pas vijf kaarten gezien als hij troef maakt."),
        ("Wat gebeurt er als een speler weggaat?", "Een computerspeler neemt het meteen over, zodat het spel doorgaat. Valt je eigen verbinding weg, dan blijft je stoel een tijdje bewaard en krijg je je kaarten terug als je terugkomt."),
    ],
    "es": [
        ("¿Es gratis el Troefcall en Explore Suriname?", "Sí. No hay que instalar ninguna app ni crear una cuenta. Escribe un nombre y siéntate."),
        ("¿Cómo juego Troefcall en línea con amigos?", "Toca Jugar con amigos. Recibes una mesa con su propio enlace y un código de cinco caracteres. Envía el enlace por WhatsApp y quien lo abra se sienta en tu mesa. Elige quién se sienta frente a quién y empieza. La computadora juega en las sillas vacías."),
        ("¿Puedo jugar Troefcall yo solo?", "Sí. Con Practicar contra la computadora se sientan tres jugadores de la computadora en tu mesa. O toca Jugar ahora para sentarte con quienes estén en línea en ese momento."),
        ("¿Qué es un kap?", "Un kap son siete bazas mientras la otra pareja no tiene ninguna. Vale 5 puntos en lugar de 2. Después de un kap puedes seguir por el baunie, las trece bazas, por 15 puntos. Si entonces pierdes una sola baza, la otra pareja gana 2 puntos."),
        ("¿Quién elige el troef?", "El caller, el jugador a la izquierda de quien reparte. El caller solo ha visto cinco cartas cuando elige el troef."),
        ("¿Qué pasa si un jugador se va?", "La computadora toma su lugar al instante y el juego sigue. Si se cae tu propia conexión, tu silla se guarda un rato y recuperas tus cartas al volver."),
    ],
    "zh": [
        ("Explore Suriname 上的 Troefcall 免费吗？", "免费。不用安装应用，也不用注册账号。输入一个名字就可以入座。"),
        ("怎样和朋友在线玩 Troefcall？", "点“和朋友一起玩”。你会得到一张牌桌，它有自己的链接和五位代码。把链接用 WhatsApp 发出去，打开的人就会坐到你的牌桌。安排好谁坐谁对面，然后开始。空位由电脑来打。"),
        ("可以一个人玩吗？", "可以。选“与电脑练习”，会有三位电脑玩家和你同桌。也可以点“马上开打”，和当时在线的玩家坐到一桌。"),
        ("什么是 Kap？", "一方拿到七墩而对方一墩未得，就是 Kap，得 5 分而不是 2 分。打出 Kap 后可以继续打 Baunie，也就是十三墩全拿，得 15 分。但只要输掉一墩，对方就得 2 分。"),
        ("谁来选 Troef？", "叫牌人，也就是发牌人左手边的玩家。他定 Troef 时只看到自己的五张牌。"),
        ("有玩家离开会怎样？", "电脑会立刻接手，牌局继续。如果是你自己掉线，座位会保留一段时间，回来后手牌还在。"),
    ],
    "fr": [
        ("Le Troefcall sur Explore Suriname est-il gratuit ?", "Oui. Aucune application à installer, aucun compte à créer. Saisissez un nom et asseyez-vous."),
        ("Comment jouer au Troefcall en ligne avec des amis ?", "Touchez Jouer entre amis. Vous obtenez une table avec son propre lien et un code de cinq caractères. Envoyez le lien par WhatsApp : ceux qui l’ouvrent s’assoient à votre table. Choisissez qui s’assoit en face de qui, puis lancez la partie. L’ordinateur joue aux places libres."),
        ("Peut-on jouer seul au Troefcall ?", "Oui. S’entraîner contre l’ordinateur installe trois joueurs ordinateur à votre table. Vous pouvez aussi toucher Jouer maintenant pour vous asseoir avec les joueurs en ligne à ce moment-là."),
        ("Qu’est-ce qu’un kap ?", "Un kap, c’est sept plis alors que l’autre équipe n’en a aucun. Il vaut 5 points au lieu de 2. Après un kap, vous pouvez continuer pour le baunie, les treize plis, pour 15 points. Si vous perdez alors un seul pli, l’autre équipe marque 2 points."),
        ("Qui choisit le troef ?", "Le caller, le joueur à gauche du donneur. Il n’a vu que cinq cartes au moment d’annoncer le troef."),
        ("Que se passe-t-il si un joueur quitte la table ?", "L’ordinateur prend aussitôt le relais et la partie continue. Si votre propre connexion tombe, votre place est gardée un moment et vous retrouvez vos cartes à votre retour."),
    ],
    "pt": [
        ("O Troefcall no Explore Suriname é grátis?", "Sim. Não precisa instalar aplicativo nem criar conta. Digite um nome e sente à mesa."),
        ("Como jogo Troefcall online com amigos?", "Toque em Jogar com amigos. Você recebe uma mesa com link próprio e um código de cinco caracteres. Mande o link pelo WhatsApp e quem abrir senta na sua mesa. Escolha quem senta de frente para quem e comece. O computador joga nas cadeiras vazias."),
        ("Dá para jogar Troefcall sozinho?", "Sim. Em Treinar contra o computador, três jogadores do computador sentam à sua mesa. Ou toque em Jogar agora para sentar com quem estiver online naquele momento."),
        ("O que é um kap?", "Um kap são sete vazas enquanto a outra dupla não tem nenhuma. Vale 5 pontos em vez de 2. Depois de um kap você pode seguir para o baunie, as treze vazas, por 15 pontos. Se perder uma única vaza, a outra dupla ganha 2 pontos."),
        ("Quem escolhe o troef?", "O caller, o jogador à esquerda de quem dá as cartas. Ele só viu cinco cartas quando escolhe o troef."),
        ("O que acontece quando um jogador sai?", "O computador assume na hora e o jogo continua. Se a sua conexão cair, a sua cadeira fica guardada por um tempo e você recupera as suas cartas ao voltar."),
    ],
}

GAMES = [("quiz.html", "Sabi Suriname"), ("crossword.html", "Switi Mini"), ("map-game.html", "Pe A De?"),
         ("heiligenweg-jam.html", "Heiligenweg Jam"), ("korjaal.html", "Korjaal Run"), ("anaconda.html", "Aboma"),
         ("muskieto.html", "Muskieto Survivor")]

PAGE_CSS = """
.tcp-hero{text-align:center;color:#fff;padding:2.6rem 1rem 2.4rem}
.tcp-hero .tcp-crumb{font-size:.66rem;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:rgba(255,255,255,.6);margin:0 0 1.1rem}
.tcp-hero .tcp-crumb a{color:inherit}
.tcp-eye{font-size:.66rem;font-weight:700;letter-spacing:.16em;text-transform:uppercase;color:var(--gold,#E7AE4D);margin:0 0 .5rem}
.tcp-hero h1{font-size:clamp(2.4rem,7vw,3.4rem);margin:0 0 .6rem}
.tcp-lede{max-width:36rem;margin:0 auto;color:rgba(255,255,255,.76);font-size:1rem;line-height:1.55}
.tcp-main{padding:1.1rem .6rem 0}
.tcp-sec{max-width:46rem;margin:3.2rem auto 0;padding:0 .5rem;color:var(--ink,#233028)}
.tcp-sec h2{font-family:Newsreader,Georgia,serif;font-weight:500;font-size:1.75rem;line-height:1.15;margin:0 0 1rem;color:var(--forest,#1B4332)}
.tcp-sec h3{font-family:Newsreader,Georgia,serif;font-weight:600;font-size:1.25rem;margin:2rem 0 .7rem;color:var(--forest,#1B4332)}
.tcp-sec p{font-size:.95rem;line-height:1.65;margin:0 0 .9rem;color:#3b463d}
.tcp-steps{list-style:none;margin:0;padding:0;display:grid;gap:.6rem;counter-reset:s}
.tcp-steps li{counter-increment:s;position:relative;background:var(--card,#FFFDF6);border:1px solid var(--line,#EBE0CB);border-radius:10px;padding:.85rem 1rem .85rem 3.3rem}
.tcp-steps li::before{content:counter(s);position:absolute;left:.9rem;top:.8rem;width:1.75rem;height:1.75rem;border-radius:50%;background:var(--forest,#1B4332);color:#fff;font-weight:700;font-size:.85rem;display:grid;place-items:center}
.tcp-steps b{display:block;font-size:1rem;margin-bottom:.15rem;color:var(--ink,#233028)}
.tcp-steps span{display:block;font-size:.9rem;line-height:1.55;color:#4a554b}
.tcp-score{width:100%;border-collapse:collapse;background:var(--card,#FFFDF6);border:1px solid var(--line,#EBE0CB);border-radius:10px;overflow:hidden;font-size:.9rem;margin-bottom:1rem}
.tcp-score td{padding:.7rem .9rem;border-top:1px solid var(--line,#EBE0CB);vertical-align:top;line-height:1.45}
.tcp-score tr:first-child td{border-top:0}
.tcp-score td:last-child{text-align:right;font-weight:700;white-space:nowrap;color:var(--forest,#1B4332)}
.tcp-words{margin:0;display:grid;gap:.45rem}
.tcp-words div{display:grid;grid-template-columns:6.4rem 1fr;gap:.8rem;font-size:.9rem;line-height:1.5;padding:.45rem 0;border-top:1px solid var(--line,#EBE0CB)}
.tcp-words dt{font-weight:700;color:var(--forest,#1B4332)}
.tcp-words dd{margin:0;color:#4a554b}
.tcp-ways{display:grid;gap:.7rem;grid-template-columns:repeat(auto-fit,minmax(13rem,1fr));margin-bottom:1rem}
.tcp-ways div{background:var(--card,#FFFDF6);border:1px solid var(--line,#EBE0CB);border-radius:10px;padding:1rem}
.tcp-ways b{display:block;font-family:Newsreader,Georgia,serif;font-size:1.15rem;font-weight:600;color:var(--forest,#1B4332);margin-bottom:.3rem}
.tcp-ways span{display:block;font-size:.88rem;line-height:1.55;color:#4a554b}
.tcp-faq details{background:var(--card,#FFFDF6);border:1px solid var(--line,#EBE0CB);border-radius:10px;padding:.8rem 1rem;margin-bottom:.5rem}
.tcp-faq summary{font-weight:700;font-size:.93rem;cursor:pointer;color:var(--ink,#233028)}
.tcp-faq details p{margin:.55rem 0 0;font-size:.9rem}
.tcp-more{font-size:.9rem;line-height:2;margin:0 0 3rem}
.tcp-more a{color:var(--forest2,#2D6A4F);font-weight:600;margin-right:.9rem;white-space:nowrap}
.tcp-more a:hover{text-decoration:underline}
@media (max-width:420px){.tcp-score td:last-child{white-space:normal}.tcp-words div{grid-template-columns:5.2rem 1fr}}
"""


def _ld(site, lg):
    url = f"{site}/troefcall"
    graph = [
        {"@type": "WebPage", "@id": url + "#webpage", "url": url, "name": U["title"][lg], "description": U["desc"][lg],
         "inLanguage": IN_LANG[lg], "isPartOf": {"@type": "WebSite", "name": "Explore Suriname", "url": site + "/"},
         "breadcrumb": {"@id": url + "#breadcrumb"}, "mainEntity": {"@id": url + "#game"},
         "datePublished": "2026-11-11", "isAccessibleForFree": True},
        {"@type": "BreadcrumbList", "@id": url + "#breadcrumb", "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": U["home"][lg], "item": site + "/"},
            {"@type": "ListItem", "position": 2, "name": "Troefcall", "item": url}]},
        {"@type": "VideoGame", "@id": url + "#game", "name": "Troefcall", "url": url, "description": U["lede"][lg],
         "genre": "Card game", "gamePlatform": "Web browser", "playMode": ["SinglePlayer", "MultiPlayer"],
         "numberOfPlayers": {"@type": "QuantitativeValue", "minValue": 1, "maxValue": 4},
         "inLanguage": [IN_LANG[x] for x in LANGS], "isAccessibleForFree": True,
         "offers": {"@type": "Offer", "price": "0", "priceCurrency": "USD"},
         "publisher": {"@type": "Organization", "name": "Explore Suriname", "url": site + "/"}},
        {"@type": "FAQPage", "@id": url + "#faq", "mainEntity": [
            {"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in FAQ[lg]]},
    ]
    return ('<script type="application/ld+json">'
            + _json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False,
                          separators=(",", ":")).replace("</", "<\\/") + "</script>")


def _rules(lg):
    f = _nb if lg == "fr" else (lambda s: s)
    steps = "".join(f"<li><b>{esc(f(t))}</b><span>{esc(f(b))}</span></li>" for t, b in STEPS[lg])
    score = "".join(f"<tr><td>{esc(f(a))}</td><td>{esc(f(b))}</td></tr>" for a, b in SCORE[lg])
    after = "".join(f"<p>{esc(f(p))}</p>" for p in AFTER[lg])
    words = "".join(f"<div><dt>{esc(w)}</dt><dd>{esc(f(d))}</dd></div>" for w, d in WORDS[lg])
    return (f'<ol class="tcp-steps">{steps}</ol>'
            f'<h3>{esc(U["h_score"][lg])}</h3><table class="tcp-score"><tbody>{score}</tbody></table>{after}'
            f'<h3>{esc(f(U["h_words"][lg]))}</h3><dl class="tcp-words">{words}</dl>')


def _ways(lg):
    f = _nb if lg == "fr" else (lambda s: s)
    cards = "".join(f"<div><b>{esc(f(t))}</b><span>{esc(f(b))}</span></div>" for t, b in WAYS[lg])
    return f'<div class="tcp-ways">{cards}</div><p>{esc(f(WAYS_NOTE[lg]))}</p>'


def _faq(lg):
    f = _nb if lg == "fr" else (lambda s: s)
    return "".join(f"<details><summary>{esc(f(q))}</summary><p>{esc(f(a))}</p></details>" for q, a in FAQ[lg])


def build_troefcall_pages(ctx):
    site = ctx["SITE_URL"]
    url = f"{site}/troefcall"
    engine, ui, css = (_read(n) for n in FILES)
    for name, src in (("troefcall_engine.js", engine), ("troefcall_ui.js", ui)):
        if "</script" in src.lower():
            raise ValueError(name + " contains a closing script tag")
    title, desc = _fr(U["title"]), _fr(U["desc"])
    og = f"{site}/og-image.jpg"          # swapped for images/og-pages/troefcall.jpg by _og_swap
    head = (ctx["PAGE_HEAD"]
            + f'\n  <title translate="no" data-l10n="{_lj(title)}">{esc(title["en"])}</title>'
            + f'\n  <meta name="description" content="{esc(desc["en"])}" data-l10n-content="{_lj(desc)}">'
            + f'\n  <link rel="canonical" href="{url}">'
            + '\n  <meta property="og:type" content="website">'
            + '\n  <meta property="og:site_name" content="Explore Suriname">'
            + f'\n  <meta property="og:url" content="{url}">'
            + f'\n  <meta property="og:title" content="{esc(title["en"])}" data-l10n-content="{_lj(title)}">'
            + f'\n  <meta property="og:description" content="{esc(desc["en"])}" data-l10n-content="{_lj(desc)}">'
            + f'\n  <meta property="og:image" content="{og}">'
            + '\n  <meta name="twitter:card" content="summary_large_image">'
            + f'\n  <meta name="twitter:title" content="{esc(title["en"])}" data-l10n-content="{_lj(title)}">'
            + f'\n  <meta name="twitter:description" content="{esc(desc["en"])}" data-l10n-content="{_lj(desc)}">'
            + f'\n  <meta name="twitter:image" content="{og}">'
            + '\n  <link rel="preconnect" href="' + API + '" crossorigin>'
            + "\n  <style>" + css + PAGE_CSS + "</style>"
            + "\n</head>")
    hero = ('<div class="pg-hero tcp-hero">'
            f'<p class="tcp-crumb"><a href="./">{tx(U["home"])}</a> &#8250; <span translate="no">Troefcall</span></p>'
            f'{tx(U["eyebrow"], "p", "tcp-eye")}<h1 class="serif" translate="no">Troefcall</h1>'
            f'{tx(U["lede"], "p", "tcp-lede")}</div>')
    app = (f'<div id="tc-app" class="tc" data-api="{API}" data-rules="#tc-rules">'
           f'<noscript>{tx(U["noscript"], "p")}</noscript></div>')
    more = ('<p class="tcp-more">' + tx(U["more"], "b") + ": "
            + "".join(f'<a href="{h}" translate="no">{esc(n)}</a>' for h, n in GAMES) + "</p>")
    body = ('<main class="tcp-main">' + app
            + f'<section class="tcp-sec" id="tc-rules">{tx(U["h_rules"], "h2")}'
            + group_block({lg: _rules(lg) for lg in LANGS}) + "</section>"
            + f'<section class="tcp-sec">{tx(U["h_ways"], "h2")}'
            + group_block({lg: _ways(lg) for lg in LANGS}) + "</section>"
            + f'<section class="tcp-sec">{tx(U["h_about"], "h2")}{tx(ABOUT, "p")}</section>'
            + f'<section class="tcp-sec tcp-faq">{tx(U["h_faq"], "h2")}'
            + group_block({lg: _faq(lg) + _ld(site, lg) for lg in LANGS}) + more + "</section>"
            + "</main>")
    page = (head + '\n<body class="bg-gray-50 overflow-x-hidden">\n' + ctx["nav_html"]("troefcall") + hero + body + "\n"
            + ctx["footer_html"]() + "\n<script>\n" + engine + "\n</script>\n<script>\n" + ui + "\n</script>\n</body>\n</html>")
    return {"troefcall.html": page}
