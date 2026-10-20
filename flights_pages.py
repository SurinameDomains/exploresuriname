#!/usr/bin/env python3
"""
Explore Suriname: flights board (flights.html) + one page per recurring flight
(flight-<number>.html). Data comes from flights.collect(); see flights.py.

generate.py calls build_flight_pages(ctx, c) and merges the returned dict into
its `pages` map. Everything it needs from generate.py (PAGE_HEAD, nav, footer,
SITE_URL, _ld_safe) arrives through ctx: no circular import.

House rules: no em dashes in visible copy, no emoji, no Tailwind classes here
(this file is not in tailwind.config.js content; all styling is FL_CSS).
i18n: static words are plain text nodes (translations.json, hand nl/es/zh/fr/pt);
sentences that carry values use data-l10n with baked translations (L10N below);
words written by the browser come from FL_I18N.
"""

import html
import json
import re
from datetime import datetime, timedelta

import flights as F

esc = html.escape
LANGS = ("nl", "es", "zh", "fr", "pt")

# ── weekday names per language (Mon=0) ───────────────────────────────────────
WD = {
    "en": ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"],
    "nl": ["ma", "di", "wo", "do", "vr", "za", "zo"],
    "es": ["lun", "mar", "mié", "jue", "vie", "sáb", "dom"],
    "zh": ["周一", "周二", "周三", "周四", "周五", "周六", "周日"],
    "fr": ["lun.", "mar.", "mer.", "jeu.", "ven.", "sam.", "dim."],
    "pt": ["seg", "ter", "qua", "qui", "sex", "sáb", "dom"],
}
DAILY = {"en": "Daily", "nl": "Dagelijks", "es": "Diario", "zh": "每天", "fr": "Tous les jours", "pt": "Diário"}
PMB = {"en": "Paramaribo", "nl": "Paramaribo", "es": "Paramaribo", "zh": "帕拉马里博", "fr": "Paramaribo", "pt": "Paramaribo"}

# Sentence templates with values (baked per language, never through MT).
L10N = {
    "route": {"en": "{a} to {b}", "nl": "{a} naar {b}", "es": "{a} a {b}", "zh": "{a}至{b}",
              "fr": "{a} à {b}", "pt": "{a} para {b}"},
    "and": {"en": " and ", "nl": " en ", "es": " y ", "zh": "及", "fr": " et ", "pt": " e "},
    "title": {"en": "{fn} {route}: Flight Status & On-Time Record",
              "nl": "{fn} {route}: vluchtstatus en stiptheid",
              "es": "{fn} {route}: estado del vuelo y puntualidad",
              "zh": "{fn} {route}：航班动态与准点记录",
              "fr": "{fn} {route}\u00a0: statut du vol et ponctualité",
              "pt": "{fn} {route}: status do voo e pontualidade"},
    "desc": {"en": "Live status of {al} flight {fn} {route} today, with delays, the weekly schedule, the aircraft and the on-time record of the last 30 days.",
             "nl": "Actuele status van {al}-vlucht {fn} {route} vandaag: vertragingen, weekschema, vliegtuig en stiptheid van de laatste 30 dagen.",
             "es": "Estado en vivo del vuelo {fn} de {al} {route} hoy, con retrasos, el horario semanal, el avión y la puntualidad de los últimos 30 días.",
             "zh": "{al} {fn} 航班（{route}）今日实时动态，含延误、每周时刻、机型及过去 30 天的准点记录。",
             "fr": "Statut en direct du vol {al} {fn} {route} aujourd’hui\u00a0: retards, horaires de la semaine, avion et ponctualité des 30 derniers jours.",
             "pt": "Status ao vivo do voo {fn} da {al} {route} hoje, com atrasos, horário semanal, aeronave e pontualidade dos últimos 30 dias."},
    "ontime_line": {"en": "{p}% of the last {n} flights arrived or left within 15 minutes of schedule.",
                    "nl": "{p}% van de laatste {n} vluchten vertrok of landde binnen 15 minuten na de geplande tijd.",
                    "es": "El {p}% de los últimos {n} vuelos salió o llegó dentro de los 15 minutos de lo previsto.",
                    "zh": "最近 {n} 个航班中有 {p}% 在计划时间 15 分钟内起飞或抵达。",
                    "fr": "{p} % des {n} derniers vols sont partis ou arrivés à moins de 15 minutes de l’horaire.",
                    "pt": "{p}% dos últimos {n} voos partiram ou chegaram em até 15 minutos do horário."},
    "faq_al": {"en": "Scheduled passenger flights at Johan Adolf Pengel (PBM) are currently operated by {list}. The live board on this page lists every flight with its status.",
               "nl": "Lijnvluchten met passagiers op Johan Adolf Pengel (PBM) worden op dit moment uitgevoerd door {list}. Het live bord op deze pagina toont elke vlucht met de status.",
               "es": "Los vuelos regulares de pasajeros en Johan Adolf Pengel (PBM) los operan actualmente {list}. El panel en vivo de esta página muestra cada vuelo con su estado.",
               "zh": "目前在约翰·阿道夫·彭格尔机场（PBM）运营定期客运航班的航空公司有：{list}。本页的实时航班表列出每个航班及其状态。",
               "fr": "Les vols réguliers de passagers à Johan Adolf Pengel (PBM) sont actuellement assurés par {list}. Le tableau en direct de cette page affiche chaque vol et son statut.",
               "pt": "Os voos regulares de passageiros em Johan Adolf Pengel (PBM) são operados atualmente por {list}. O painel ao vivo desta página mostra cada voo com seu status."},
    "faq_dest": {"en": "Direct destinations from Johan Adolf Pengel include {list}. The Destinations section on this page shows the airlines and how often each route flies.",
                 "nl": "Vanaf Johan Adolf Pengel vliegt u direct naar onder meer {list}. Het onderdeel met bestemmingen op deze pagina toont de maatschappijen en hoe vaak elke route vliegt.",
                 "es": "Los destinos directos desde Johan Adolf Pengel incluyen {list}. La sección de destinos de esta página muestra las aerolíneas y la frecuencia de cada ruta.",
                 "zh": "从约翰·阿道夫·彭格尔机场直飞的目的地包括：{list}。本页的目的地部分列出各航线的航空公司和航班频率。",
                 "fr": "Les destinations directes depuis Johan Adolf Pengel comprennent {list}. La section des destinations de cette page indique les compagnies et la fréquence de chaque ligne.",
                 "pt": "Os destinos diretos a partir de Johan Adolf Pengel incluem {list}. A seção de destinos desta página mostra as companhias e a frequência de cada rota."},
    "faq_days_q": {"en": "Which days does {fn} fly?", "nl": "Op welke dagen vliegt {fn}?",
                   "es": "¿Qué días vuela el {fn}?", "zh": "{fn} 每周哪几天执飞？",
                   "fr": "Quels jours le vol {fn} opère-t-il ?", "pt": "Em quais dias o {fn} voa?"},
    "faq_days_a": {"en": "{fn} {route} has flown on {days} in recent weeks, usually at {t} Suriname time. Schedules change, so check with {al} before you travel.",
                   "nl": "{fn} {route} vloog de afgelopen weken op {days}, meestal om {t} Surinaamse tijd. Schema's veranderen, dus controleer het bij {al} voordat u reist.",
                   "es": "El {fn} {route} ha volado los {days} en las últimas semanas, normalmente a las {t} hora de Surinam. Los horarios cambian: confírmelo con {al} antes de viajar.",
                   "zh": "近几周 {fn}（{route}）在{days}执飞，通常为苏里南时间 {t}。航班时刻可能调整，出行前请向 {al} 确认。",
                   "fr": "Ces dernières semaines, le vol {fn} {route} a opéré le {days}, généralement à {t} heure du Suriname. Les horaires changent : vérifiez auprès de {al} avant de partir.",
                   "pt": "Nas últimas semanas, o {fn} {route} voou {days}, geralmente às {t} no horário do Suriname. Horários mudam, então confirme com a {al} antes de viajar."},
    "faq_ot_q": {"en": "Is {fn} usually on time?", "nl": "Is {fn} meestal op tijd?",
                 "es": "¿El {fn} suele ser puntual?", "zh": "{fn} 通常准点吗？",
                 "fr": "Le vol {fn} est-il généralement à l’heure ?", "pt": "O {fn} costuma ser pontual?"},
    "faq_ot_a": {"en": "Over the last {d} days {p}% of {n} recorded {fn} flights were within 15 minutes of schedule, with an average delay of {avg} minutes.",
                 "nl": "In de afgelopen {d} dagen was {p}% van {n} geregistreerde {fn}-vluchten binnen 15 minuten op tijd, met een gemiddelde vertraging van {avg} minuten.",
                 "es": "En los últimos {d} días, el {p}% de {n} vuelos {fn} registrados estuvo dentro de los 15 minutos previstos, con un retraso medio de {avg} minutos.",
                 "zh": "过去 {d} 天记录的 {n} 个 {fn} 航班中，{p}% 在计划时间 15 分钟内，平均延误 {avg} 分钟。",
                 "fr": "Sur les {d} derniers jours, {p} % des {n} vols {fn} enregistrés étaient à moins de 15 minutes de l’horaire, avec un retard moyen de {avg} minutes.",
                 "pt": "Nos últimos {d} dias, {p}% de {n} voos {fn} registrados ficaram dentro de 15 minutos do horário, com atraso médio de {avg} minutos."},
    "faq_ac_q": {"en": "What aircraft flies {fn}?", "nl": "Met welk vliegtuig vliegt {fn}?",
                 "es": "¿Qué avión opera el {fn}?", "zh": "{fn} 使用什么机型？",
                 "fr": "Quel avion assure le vol {fn} ?", "pt": "Qual aeronave opera o {fn}?"},
    "faq_ac_a": {"en": "{fn} is usually flown with a {ac}.", "nl": "{fn} wordt meestal gevlogen met een {ac}.",
                 "es": "El {fn} suele operarse con un {ac}.", "zh": "{fn} 通常使用 {ac} 执飞。",
                 "fr": "Le vol {fn} est généralement assuré en {ac}.", "pt": "O {fn} costuma ser operado com um {ac}."},
    "faq_dur_q": {"en": "How long is flight {fn}?", "nl": "Hoe lang duurt vlucht {fn}?",
                  "es": "¿Cuánto dura el vuelo {fn}?", "zh": "{fn} 航班飞行多久？",
                  "fr": "Combien de temps dure le vol {fn} ?", "pt": "Quanto tempo dura o voo {fn}?"},
    "faq_dur_a": {"en": "The scheduled flying time of {fn} {route} is {dur}.",
                  "nl": "De geplande vliegtijd van {fn} {route} is {dur}.",
                  "es": "El tiempo de vuelo previsto del {fn} {route} es de {dur}.",
                  "zh": "{fn}（{route}）计划飞行时间为 {dur}。",
                  "fr": "La durée prévue du vol {fn} {route} est de {dur}.",
                  "pt": "O tempo de voo previsto do {fn} {route} é de {dur}."},
    "faq_live_q": {"en": "Where can I see if {fn} is delayed today?", "nl": "Waar zie ik of {fn} vandaag vertraagd is?",
                   "es": "¿Dónde puedo ver si el {fn} va retrasado hoy?", "zh": "在哪里查看 {fn} 今天是否延误？",
                   "fr": "Où voir si le vol {fn} est retardé aujourd’hui ?", "pt": "Onde vejo se o {fn} está atrasado hoje?"},
    "faq_live_a": {"en": "The status card at the top of this page updates by itself every few minutes. For check-in, gate and rebooking questions, {al} is the official source.",
                   "nl": "De statuskaart bovenaan deze pagina werkt zichzelf om de paar minuten bij. Voor inchecken, gate en omboeken is {al} de officiële bron.",
                   "es": "La tarjeta de estado en la parte superior de esta página se actualiza sola cada pocos minutos. Para facturación, puerta y cambios, {al} es la fuente oficial.",
                   "zh": "本页顶部的状态卡每隔几分钟自动更新。值机、登机口和改签问题请以 {al} 的官方信息为准。",
                   "fr": "La carte de statut en haut de cette page se met à jour toute seule toutes les quelques minutes. Pour l’enregistrement, la porte et les changements, {al} est la source officielle.",
                   "pt": "O cartão de status no topo desta página se atualiza sozinho a cada poucos minutos. Para check-in, portão e remarcação, a {al} é a fonte oficial."},
}

DUR_FMT = {"en": "{h} h {m} min", "nl": "{h} u {m} min", "es": "{h} h {m} min", "zh": "{h} 小时 {m} 分钟",
           "fr": "{h} h {m} min", "pt": "{h} h {m} min"}


def _join(items, lang):
    items = list(items)
    if lang == "zh":
        return "、".join(items)
    if len(items) < 2:
        return "".join(items)
    return ", ".join(items[:-1]) + L10N["and"][lang] + items[-1]


def _l(key, lang, **kw):
    t = L10N[key].get(lang) or L10N[key]["en"]
    return t.format(**kw)


def _l10n_attr(key_fn):
    """data-l10n JSON for the 5 languages from a function lang -> text."""
    return esc(json.dumps({lg: key_fn(lg) for lg in LANGS}, ensure_ascii=False), quote=True)


def _days_text(wd, lang):
    if not wd:
        return ""
    if len(wd) == 7:
        return DAILY[lang]
    names = WD[lang]
    sep = "、" if lang == "zh" else ", "
    return sep.join(names[i] for i in wd)


def _dur_text(sec, lang):
    if not sec:
        return ""
    h, m = int(sec // 3600), int(round((sec % 3600) / 60))
    if m == 60:
        h, m = h + 1, 0
    if m == 0:
        return {"en": f"{h} h", "nl": f"{h} u", "es": f"{h} h", "zh": f"{h} 小时", "fr": f"{h} h", "pt": f"{h} h"}[lang]
    if h == 0:
        return {"en": f"{m} min", "nl": f"{m} min", "es": f"{m} min", "zh": f"{m} 分钟", "fr": f"{m} min", "pt": f"{m} min"}[lang]
    return DUR_FMT[lang].format(h=h, m=m)


MON = {
    "en": ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"],
    "nl": ["jan", "feb", "mrt", "apr", "mei", "jun", "jul", "aug", "sep", "okt", "nov", "dec"],
    "es": ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sept", "oct", "nov", "dic"],
    "fr": ["janv.", "févr.", "mars", "avr.", "mai", "juin", "juil.", "août", "sept.", "oct.", "nov.", "déc."],
    "pt": ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov", "dez"],
}


def _short_date(dt, lang):
    if lang == "zh":
        return f"{dt.month}月{dt.day}日"
    return f"{dt.day} {MON[lang][dt.month - 1]}"


def _hm(ts):
    return F._sr(ts).strftime("%H:%M") if ts else ""


def _city(name, lang):
    if lang == "zh" and name.startswith("Paramaribo"):
        return name.replace("Paramaribo", "帕拉马里博")
    return name


# ── CSS ───────────────────────────────────────────────────────────────────────
FL_CSS = r"""<style>
.fl-hero{background:#142A1E;color:#FCF7EC;padding:2.2rem 1.25rem 1.6rem;border-bottom:1px solid rgba(252,247,236,.13)}
.fl-hero .in{max-width:64rem;margin:0 auto}
.fl-hero .k{font-size:.72rem;font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:var(--gold);margin:0 0 .5rem}
.fl-hero h1{font-family:'Newsreader',Georgia,serif;font-weight:400;font-size:clamp(2rem,5.4vw,3.1rem);line-height:1.05;letter-spacing:-.02em;margin:0}
.fl-hero .sub{color:rgba(252,247,236,.72);font-size:1rem;line-height:1.5;margin:.6rem 0 0;max-width:44rem}
.fl-hero .back{display:inline-block;color:rgba(252,247,236,.6);font-size:.85rem;margin-bottom:1rem;text-decoration:none}
.fl-hero .back:hover{color:#fff}
.fl-live{display:flex;flex-wrap:wrap;align-items:center;gap:.35rem .5rem;font-size:.78rem;color:rgba(252,247,236,.75);margin-top:.9rem}
.fl-live .dot{width:8px;height:8px;border-radius:50%;background:#7BD389;box-shadow:0 0 0 0 rgba(123,211,137,.6);animation:flp 2s infinite}
.fl-live.off .dot{background:var(--gold);animation:none}
.fl-live b{color:#fff;font-weight:600}
@keyframes flp{0%{box-shadow:0 0 0 0 rgba(123,211,137,.55)}70%{box-shadow:0 0 0 7px rgba(123,211,137,0)}100%{box-shadow:0 0 0 0 rgba(123,211,137,0)}}
@media (prefers-reduced-motion:reduce){.fl-live .dot{animation:none}}
.fl-main{max-width:64rem;margin:0 auto;padding:1.25rem 1rem 5rem}
.fl-card{background:var(--card);border:1px solid var(--bd-card);border-radius:var(--r-card);box-shadow:var(--sh-card)}
.fl-next{display:grid;grid-template-columns:repeat(auto-fit,minmax(15rem,1fr));gap:.75rem;margin:0 0 1.1rem}
.fl-nc{padding:.95rem 1.05rem;display:flex;flex-direction:column;gap:.15rem;min-width:0;cursor:pointer;text-align:left;font:inherit;color:inherit}
.fl-nc:hover{box-shadow:var(--sh-lift)}
.fl-nc .l{font-size:.7rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-soft)}
.fl-nc .big{font-family:'Newsreader',Georgia,serif;font-size:2rem;line-height:1.05;color:var(--forest);font-variant-numeric:tabular-nums}
.fl-nc .big small{font-family:inherit;font-size:1rem;color:var(--ink-soft);margin-left:.35rem}
.fl-nc .r{font-size:.9rem;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fl-nc .c{font-size:.8rem;color:var(--ink-soft)}
.fl-nc.trk{border-left:3px solid var(--gold)}
@media(max-width:639px){.fl-next{grid-template-columns:repeat(2,minmax(0,1fr));gap:.55rem}.fl-nc{padding:.75rem .8rem}.fl-nc .r{font-size:.8rem}.fl-nc .c .pill{font-size:.7rem}.fl-nc .c{font-size:.72rem}}
.fl-bar{display:flex;flex-wrap:wrap;gap:.5rem .6rem;align-items:center;margin:0 0 .75rem;position:sticky;top:58px;z-index:30;background:linear-gradient(var(--paper) 88%,rgba(251,245,233,0));padding:.55rem 0 .7rem}
@media(max-width:379px){.fl-main .fl-sec{padding:.95rem .7rem}.fl-main{padding-left:.75rem;padding-right:.75rem}.fl-tbl .wdx{display:none}.fl-tbl td,.fl-tbl th{padding:.5rem .3rem}.fl-tbl th{font-size:.6rem;letter-spacing:.03em}.fl-tbl .pill{font-size:.68rem;padding:.2rem .4rem}}
@media(max-width:639px){.fl-seg[data-seg="ap"] .n{display:none}.fl-seg button{padding:.4rem .7rem}.fl-tbl .hs{display:none}.fl-tbl{font-size:.84rem}}
.fl-seg{display:inline-flex;background:var(--paper-2);border:1px solid var(--line);border-radius:999px;padding:3px}
.fl-seg button{border:0;background:transparent;font:inherit;font-size:.86rem;font-weight:600;color:var(--ink-soft);padding:.42rem .85rem;border-radius:999px;cursor:pointer;white-space:nowrap}
.fl-seg button[aria-pressed="true"]{background:var(--forest);color:#fff}
.fl-seg button .n{font-weight:400;opacity:.75;margin-left:.25rem;font-size:.78rem}
.fl-q{flex:1 1 11rem;min-width:0;position:relative}
.fl-q input{width:100%;font:inherit;font-size:.9rem;padding:.5rem .8rem .5rem 2rem;border:1px solid var(--line);border-radius:999px;background:var(--card);color:var(--ink)}
.fl-q svg{position:absolute;left:.7rem;top:50%;transform:translateY(-50%);width:14px;height:14px;color:var(--ink-soft)}
.fl-cg{display:inline-flex;align-items:center;gap:.35rem;font-size:.82rem;color:var(--ink-soft);cursor:pointer;white-space:nowrap}
.fl-board{padding:0;overflow:hidden}
.fl-day{font-size:.72rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-soft);padding:.8rem 1.05rem .35rem;background:var(--paper-2);border-bottom:1px solid var(--line);margin:0}
.fl-list{list-style:none;margin:0;padding:0}
.fr{border-bottom:1px solid var(--line)}
.fr:last-child{border-bottom:0}
.fr-main{display:grid;grid-template-columns:4.6rem minmax(0,1fr) auto;gap:.75rem;align-items:center;width:100%;padding:.8rem 1.05rem;background:none;border:0;text-align:left;font:inherit;color:inherit;cursor:pointer}
.fr-main:hover{background:rgba(0,0,0,.018)}
.fr-time b{display:block;font-size:1.15rem;font-weight:600;font-variant-numeric:tabular-nums;color:var(--ink);line-height:1.15}
.fr-time s{display:block;font-size:.78rem;color:var(--ink-soft);font-variant-numeric:tabular-nums}
.fr-time .p1{font-size:.68rem;color:var(--ink-soft);vertical-align:super;margin-left:1px}
.fr-mid{min-width:0}
.fr-city{display:block;font-weight:600;font-size:1rem;color:var(--ink);white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.fr-city small{font-weight:400;font-size:.78rem;color:var(--ink-soft);margin-left:.3rem}
.fr-fn{display:block;font-size:.8rem;color:var(--ink-soft);white-space:nowrap;overflow:hidden;text-overflow:ellipsis;margin-top:.1rem}
.fr-fn .tk{color:#B07A12}
.fr-st{text-align:right}
.pill{display:inline-block;font-size:.76rem;font-weight:600;padding:.25rem .55rem;border-radius:999px;white-space:nowrap;background:#EFEADF;color:#5C6657}
.pill.p-ontime{background:#E3F1E6;color:#22663F}
.pill.p-delayed{background:#FBEBD3;color:#8A4B12}
.pill.p-enroute{background:#E2ECF7;color:#1C5D99}
.pill.p-landed,.pill.p-departed{background:#DDEEE2;color:#1B4332}
.pill.p-cancelled,.pill.p-diverted{background:#F8E1DA;color:#A23A22}
.pill.p-unknown{background:#EFEADF;color:#7A7466}
.pill.p-boarding{background:#E2ECF7;color:#1C5D99}
.fd-why{margin:.2rem 0 .5rem;font-size:.84rem;color:var(--ink);line-height:1.45}
.fr-sub{display:block;font-size:.74rem;color:var(--ink-soft);margin-top:.2rem;white-space:nowrap}
.fr.past .fr-main{opacity:.62}
.fr-det{padding:0 1.05rem 1rem;border-top:1px dashed var(--line);background:rgba(244,236,218,.35)}
.fr-det[hidden]{display:none}
.fd-grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(10.5rem,1fr));gap:.6rem 1rem;padding:.85rem 0 .4rem;font-size:.85rem}
.fd-grid dt{font-size:.68rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-soft)}
.fd-grid dd{margin:.1rem 0 0;color:var(--ink);font-variant-numeric:tabular-nums}
.fd-acts{display:flex;flex-wrap:wrap;gap:.45rem;margin-top:.55rem}
.fbtn{display:inline-flex;align-items:center;gap:.35rem;font:inherit;font-size:.82rem;font-weight:600;padding:.45rem .8rem;border-radius:999px;border:1px solid var(--line);background:var(--card);color:var(--forest2);cursor:pointer;text-decoration:none;white-space:nowrap}
.fbtn:hover{border-color:var(--forest2)}
.fbtn.on{background:#FFF4DC;border-color:#E7AE4D;color:#8A5A00}
.fbtn svg{width:14px;height:14px}
.fbtn.wa{color:#1B7F3B}
.pk{margin-top:.8rem;padding:.8rem .9rem;border-radius:6px;background:var(--card);border:1px solid var(--line)}
.pk h4{margin:0 0 .45rem;font-size:.9rem;font-weight:700;color:var(--ink)}
.pk label{font-size:.8rem;color:var(--ink-soft);display:inline-flex;align-items:center;gap:.4rem;flex-wrap:wrap}
.pk select{font:inherit;font-size:.85rem;padding:.3rem .5rem;border:1px solid var(--line);border-radius:6px;background:#fff;color:var(--ink);max-width:100%}
.pk .res{margin:.55rem 0 0;font-size:.9rem;line-height:1.55;color:var(--ink)}
.pk .res b{font-variant-numeric:tabular-nums}
.pk .note{margin:.35rem 0 0;font-size:.74rem;color:var(--ink-soft);line-height:1.45}
.fl-more{display:block;width:100%;padding:.75rem;border:0;border-bottom:1px solid var(--line);background:var(--paper-2);font:inherit;font-size:.84rem;font-weight:600;color:var(--forest2);cursor:pointer}
.fl-empty{padding:1.6rem 1.05rem;text-align:center;color:var(--ink-soft);font-size:.9rem}
.fl-src{font-size:.75rem;color:var(--ink-soft);line-height:1.55;margin:.6rem .2rem 0}
.fl-src a{color:var(--forest2)}
.fl-sec{margin-top:1.75rem;padding:1.3rem 1.4rem 1.2rem}
@media(max-width:639px){.fd-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.fl-sec{padding:1.05rem 1rem 1rem}.fr-main{grid-template-columns:3.9rem minmax(0,1fr) auto;gap:.55rem;padding:.75rem .85rem}.fl-day{padding:.75rem .85rem .3rem}.fr-det{padding:0 .85rem .9rem}.fl-nc .big{font-size:1.7rem}}
.fl-h2{font-family:'Newsreader',Georgia,serif;font-weight:400;font-size:1.45rem;line-height:1.15;color:var(--forest);margin:0}
.fl-h2s{font-size:.85rem;color:var(--ink-soft);margin:.3rem 0 0;line-height:1.5}
.fl-tbl{width:100%;border-collapse:collapse;font-size:.88rem;margin-top:.85rem}
.fl-tbl th{font-size:.68rem;font-weight:700;letter-spacing:.08em;text-transform:uppercase;color:var(--ink-soft);text-align:left;padding:.5rem .5rem;border-bottom:1px solid var(--line)}
.fl-tbl td{padding:.6rem .5rem;border-bottom:1px solid var(--line);font-variant-numeric:tabular-nums;vertical-align:top}
.fl-tbl tr:last-child td{border-bottom:0}
.fl-tbl .num{text-align:right}
.fl-tbl a{color:var(--forest2);font-weight:600;text-decoration:none}
.fl-bar-ot{display:inline-block;height:6px;border-radius:3px;background:#2E7D4F;vertical-align:middle;margin-left:.4rem}
.fl-dest{display:grid;grid-template-columns:repeat(auto-fill,minmax(14rem,1fr));gap:.7rem;margin-top:.9rem}
.fl-dc{padding:.8rem .9rem;border:1px solid var(--line);border-radius:6px;background:#fff}
.fl-dc h3{margin:0;font-size:1rem;font-weight:700;color:var(--ink)}
.fl-dc h3 small{font-weight:400;color:var(--ink-soft);font-size:.78rem;margin-left:.3rem}
.fl-dc p{margin:.25rem 0 0;font-size:.82rem;color:var(--ink-soft);line-height:1.45}
.fl-dc a{color:var(--forest2);font-weight:600;text-decoration:none}
.fl-guide{display:grid;grid-template-columns:repeat(auto-fit,minmax(16rem,1fr));gap:1rem 1.4rem;margin-top:.9rem}
.fl-guide h3{margin:0 0 .3rem;font-size:.95rem;font-weight:700;color:var(--ink)}
.fl-guide p,.fl-guide li{font-size:.86rem;line-height:1.55;color:var(--ink-soft);margin:0}
.fl-guide ul{margin:0;padding-left:1.1rem}
.fl-guide a{color:var(--forest2)}
.fl-faq details{border-bottom:1px solid var(--line);padding:.75rem 0}
.fl-faq details:last-child{border-bottom:0}
.fl-faq summary{cursor:pointer;font-weight:600;color:var(--ink);font-size:.95rem;list-style:none}
.fl-faq summary::-webkit-details-marker{display:none}
.fl-faq summary::after{content:"+";float:right;color:var(--ink-soft);font-weight:400}
.fl-faq details[open] summary::after{content:"\2212"}
.fl-faq p{margin:.5rem 0 0;font-size:.88rem;line-height:1.6;color:var(--ink-soft)}
.fl-toast{position:fixed;left:50%;bottom:1.2rem;transform:translateX(-50%);background:#142A1E;color:#fff;padding:.65rem 1rem;border-radius:8px;font-size:.88rem;box-shadow:var(--sh-pop);z-index:60;max-width:calc(100vw - 2rem)}
.fl-toast[hidden]{display:none}
.fp-status{padding:1.15rem 1.25rem}
.fp-status .row{display:flex;flex-wrap:wrap;align-items:baseline;justify-content:space-between;gap:.4rem 1rem}
.fp-status .when{font-size:.75rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-soft)}
.fp-status .big{font-family:'Newsreader',Georgia,serif;font-size:2.4rem;line-height:1.05;color:var(--forest);font-variant-numeric:tabular-nums}
.fp-status .big s{font-size:1.1rem;color:var(--ink-soft);margin-left:.4rem}
.fp-status .lbl{font-size:.88rem;color:var(--ink-soft);margin-top:.2rem}
.fp-grid{display:grid;grid-template-columns:minmax(0,1fr);gap:.9rem;margin-top:.9rem}
@media(min-width:720px){.fp-grid{grid-template-columns:repeat(2,minmax(0,1fr))}#fp-status{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,26rem),1fr));gap:.9rem}}
#fp-status .fp-status{margin-bottom:.9rem}@media(min-width:720px){#fp-status .fp-status{margin-bottom:0}}
.fp-grid .fl-card{padding:1.05rem 1.15rem}
.fp-k{font-size:.7rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-soft);margin:0 0 .5rem}
.wdc{display:flex;gap:.3rem;flex-wrap:wrap;margin:.1rem 0 .6rem}
.wdc span{display:inline-flex;align-items:center;justify-content:center;min-width:2.3rem;height:1.9rem;padding:0 .3rem;border-radius:6px;font-size:.78rem;font-weight:600;background:var(--paper-2);color:#A39B88}
.wdc span.on{background:var(--forest);color:#fff}
.fp-kv{display:grid;grid-template-columns:auto 1fr;gap:.3rem .9rem;font-size:.88rem;margin:0}
.fp-kv dt{color:var(--ink-soft)}
.fp-kv dd{margin:0;color:var(--ink);font-variant-numeric:tabular-nums}
.fp-pct{font-family:'Newsreader',Georgia,serif;font-size:2.6rem;line-height:1;color:var(--forest)}
.fp-pct small{font-size:1rem;color:var(--ink-soft);margin-left:.3rem;font-family:inherit}
.fp-meter{height:8px;border-radius:4px;background:var(--paper-2);overflow:hidden;margin:.55rem 0 .5rem}
.fp-meter i{display:block;height:100%;background:#2E7D4F}
.fp-note{font-size:.8rem;color:var(--ink-soft);line-height:1.5;margin:.3rem 0 0}
.fp-links{display:flex;flex-wrap:wrap;gap:.45rem;margin-top:.6rem}
</style>"""


# ── SVG icons ─────────────────────────────────────────────────────────────────
_PH = esc(json.dumps({"nl": "Vlucht, maatschappij of stad", "es": "Vuelo, aerolínea o ciudad", "zh": "航班、航空公司或城市", "fr": "Vol, compagnie ou ville", "pt": "Voo, companhia ou cidade"}, ensure_ascii=False), quote=True)
IC_SEARCH = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>'


# ── server-side row rendering (same markup as the JS) ────────────────────────
STATE_EN = {"scheduled": "Scheduled", "ontime": "On time", "delayed": "Delayed", "enroute": "En route",
            "landed": "Landed", "departed": "Departed", "cancelled": "Cancelled", "diverted": "Diverted",
            "unknown": "No update", "boarding": "Boarding"}


def _shown_state(r, now):
    st = r.get("st") or "scheduled"
    if r.get("d") == "D" and r.get("brd") == "Open" and st in ("scheduled", "delayed"):
        return "boarding"
    if st == "scheduled" and r.get("e"):
        return "ontime"
    t = r.get("a") or r.get("e") or r["s"]
    if st == "scheduled" and t < now - 20 * 60:
        return "unknown"
    return st


def _row_html(r, now):
    st = _shown_state(r, now)
    t = r.get("a") or r.get("e") or r["s"]
    big = _hm(t)
    small = _hm(r["s"]) if abs(t - r["s"]) >= 300 else ""
    pill = STATE_EN[st]
    if st == "delayed" and r.get("dl"):
        pill += " +" + str(r["dl"]) + " min"
    cs = (" · " + ", ".join(r["cs"])) if r.get("cs") else ""
    q = " ".join([r["fn"], r.get("al") or "", r.get("on") or "", r.get("oi") or ""] + (r.get("cs") or []) + (r.get("via") or [])).lower()
    city = esc(r.get("on") or r.get("oi") or "")
    via = ""
    if r.get("via"):
        via = '<span class="fr-sub"><span>' + ("Continues to" if not r.get("vfirst") else "Also from") + '</span> <span translate="no">' + esc(", ".join(r["via"])) + "</span></span>"
    return (
        f'<li class="fr{" past" if st in ("landed", "departed", "cancelled") and t < now - 30 * 60 else ""}" '
        f'data-k="{esc(F.rec_key(r))}" data-ap="{r["ap"]}" data-d="{r["d"]}" data-cg="{r.get("cg", 0)}" data-q="{esc(q)}">'
        f'<button class="fr-main" type="button" aria-expanded="false">'
        f'<span class="fr-time" translate="no"><b>{big}</b>' + (f'<s>{small}</s>' if small else '') + '</span>'
        f'<span class="fr-mid"><span class="fr-city" translate="no">{city}<small>{esc(r.get("oi") or "")}</small></span>'
        f'<span class="fr-fn" translate="no">{esc(r["fn"])} · {esc(r.get("al") or "")}{esc(cs)}</span>{via}</span>'
        f'<span class="fr-st"><span class="pill p-{st}">{esc(pill)}</span></span></button>'
        f'<div class="fr-det" hidden><a class="fbtn" href="{F.slug_of(r["fn"])}.html" translate="no">{esc(r["fn"])}</a></div></li>'
    )


def _board_html(boards, now):
    """Initial board: every airport + direction, grouped by day; JS re-renders."""
    out = []
    for iata in ("PBM", "EAX"):
        rows = [r for r in boards.get(iata, []) if (r.get("a") or r.get("e") or r["s"]) >= now - 12 * 3600]
        for d in ("A", "D"):
            sel = [r for r in rows if r["d"] == d]
            sel.sort(key=lambda r: r.get("a") or r.get("e") or r["s"])
            last_day = None
            items = []
            for r in sel:
                day = F._sr(r.get("a") or r.get("e") or r["s"]).date()
                if day != last_day:
                    if items:
                        items.append('</ul>')
                    rel = (day - F._sr(now).date()).days
                    label = {0: "Today", 1: "Tomorrow", -1: "Yesterday"}.get(rel, F._sr(r["s"]).strftime("%A"))
                    items.append(f'<h3 class="fl-day"><span>{label}</span></h3><ul class="fl-list">')
                    last_day = day
                items.append(_row_html(r, now))
            if items:
                items.append('</ul>')
            out.append(f'<div class="fl-pane" data-ap="{iata}" data-d="{d}"' + ('' if (iata, d) == ("PBM", "A") else ' hidden') + '>'
                       + ("".join(items) or '<p class="fl-empty">No flights listed for the next two days.</p>') + '</div>')
    return "".join(out)


# ── aggregates for the board page ────────────────────────────────────────────

def _airline_stats(groups, now, days=30):
    agg = {}
    for (fn, d, ap), L in groups.items():
        if any(r.get("cg") for r in L):
            continue
        for r in L:
            if not (now - days * 86400 <= r["s"] <= now - 1800):
                continue
            key = (ap, r.get("al") or fn[:2])
            a = agg.setdefault(key, {"n": 0, "ok": 0, "dl": 0, "canc": 0})
            if r.get("st") == "cancelled":
                a["canc"] += 1
            elif r.get("st") in ("landed", "departed") and r.get("dl") is not None:
                a["n"] += 1
                a["ok"] += 1 if r["dl"] <= F.ON_TIME_MIN else 0
                a["dl"] += max(r["dl"], 0)
    return agg


def _destinations(groups, boards, now):
    dest = {}
    for (fn, d, ap), L in groups.items():
        if any(r.get("cg") for r in L) or ap != "PBM":
            continue
        recent = [r for r in L if now - 28 * 86400 <= r["s"] <= now + 3 * 86400]
        if not recent:
            continue
        last = recent[-1]
        k = last.get("oi") or "?"
        x = dest.setdefault(k, {"city": last.get("on") or k, "country": last.get("occ") or "", "airlines": set(),
                                "fns": set(), "dep_n": 0, "durs": [], "first": now})
        x["airlines"].add(last.get("al") or fn[:2])
        x["fns"].add(fn)
        x["first"] = min(x["first"], min(r["s"] for r in recent))
        if d == "D":
            x["dep_n"] += len([r for r in recent if r["s"] <= now + 86400 and r.get("st") != "cancelled"])
        for r in recent:
            if r.get("sa") and r.get("sd") and 600 < r["sa"] - r["sd"] < 20 * 3600:
                x["durs"].append(r["sa"] - r["sd"])
    out = []
    for k, x in dest.items():
        span = max(1, min(28, (now - x["first"]) / 86400))
        x["per_week"] = round(x["dep_n"] * 7 / span) if span >= 7 else None
        x["dur"] = sorted(x["durs"])[len(x["durs"]) // 2] if x["durs"] else None
        x["iata"] = k
        out.append(x)
    out.sort(key=lambda x: (-(x["per_week"] or 0), x["city"]))
    return out


def _flight_page_set(groups, boards, now):
    """Flight numbers that deserve a page: passenger, seen on >= 2 distinct days
    in the last 28 days (history incl. the current board)."""
    days = {}
    for (fn, d, ap), L in groups.items():
        if any(r.get("cg") for r in L):
            continue
        for r in L:
            if now - 28 * 86400 <= r["s"] <= now + 3 * 86400:
                days.setdefault(fn, set()).add(F._sr(r["s"]).date())
    return {fn for fn, ds in days.items() if len(ds) >= 2}


# ── JS i18n ───────────────────────────────────────────────────────────────────
FL_I18N = {
 "en": {"scheduled": "Scheduled", "ontime": "On time", "delayed": "Delayed", "enroute": "En route", "landed": "Landed",
        "departed": "Departed", "cancelled": "Cancelled", "diverted": "Diverted", "unknown": "No update",
        "min": "min", "today": "Today", "tomorrow": "Tomorrow", "yesterday": "Yesterday", "earlier": "Show {n} earlier flights",
        "hideEarlier": "Hide earlier flights", "none": "No flights match.", "noneDay": "No flights listed for the next two days.",
        "nextArr": "Next arrival", "nextDep": "Next departure", "yours": "Your flight", "from": "from", "to": "to", "via": "via",
        "in": "in {t}", "ago": "{t} ago", "h": "h", "m": "min", "now": "now",
        "sched": "Scheduled", "exp": "Expected", "act": "Actual", "dep": "Departure", "arr": "Arrival",
        "aircraft": "Aircraft", "reg": "Registration", "dur": "Flight time", "codeshare": "Also sold as", "gate": "Gate",
        "track": "Track", "tracking": "Tracking", "notify": "Alert me", "notifyOn": "Alerts on", "share": "Share",
        "cal": "Calendar", "page": "Flight page", "airline": "Airline website",
        "pkH": "Picking someone up?", "pkFrom": "Leaving from", "pkLeave": "Leave by", "pkLeaveNow": "Leave now",
        "pkLands": "Lands", "pkOut": "Usually out of the arrivals hall", "pkNote": "Drive times are typical, not live. Check Waze before you go.",
        "pkWaze": "Open in Waze", "pkHere": "At the airport", "pkWait": "Usually out", "pkLanded": "Landed",
        "ciH": "Flying out?", "ciWin": "Check-in", "ciBe": "Be at the airport by", "ciNote": "Check-in times as published by the airport. Your airline has the final word.",
        "liveOk": "Live", "liveOld": "Last known", "upd": "updated {t}", "alertTitle": "{fn} update", "landedAt": "Landed {t}",
        "departedAt": "Departed {t}", "early": "{n} min early", "late": "{n} min late", "ontimeWord": "on time",
        "trackedToast": "Tracking {fn}. It stays at the top of this page.", "untrackedToast": "Stopped tracking {fn}.",
        "alertsToast": "Alerts on. They work while this page is open.", "alertsDenied": "Alerts are blocked in your browser settings.",
        "copied": "Link copied", "shareText": "{fn} {route}: {status}", "seeLive": "Live status", "ot30": "On time last 30 days",
        "avgDelay": "avg delay", "lands": "lands", "leaves": "leaves", "cargo": "Cargo"},
 "nl": {"scheduled": "Gepland", "ontime": "Op tijd", "delayed": "Vertraagd", "enroute": "Onderweg", "landed": "Geland",
        "departed": "Vertrokken", "cancelled": "Geannuleerd", "diverted": "Uitgeweken", "unknown": "Geen update",
        "min": "min", "today": "Vandaag", "tomorrow": "Morgen", "yesterday": "Gisteren", "earlier": "Toon {n} eerdere vluchten",
        "hideEarlier": "Verberg eerdere vluchten", "none": "Geen vluchten gevonden.", "noneDay": "Geen vluchten voor de komende twee dagen.",
        "nextArr": "Volgende aankomst", "nextDep": "Volgend vertrek", "yours": "Uw vlucht", "from": "uit", "to": "naar", "via": "via",
        "in": "over {t}", "ago": "{t} geleden", "h": "u", "m": "min", "now": "nu",
        "sched": "Gepland", "exp": "Verwacht", "act": "Werkelijk", "dep": "Vertrek", "arr": "Aankomst",
        "aircraft": "Vliegtuig", "reg": "Registratie", "dur": "Vliegtijd", "codeshare": "Ook verkocht als", "gate": "Gate",
        "track": "Volgen", "tracking": "Gevolgd", "notify": "Meldingen", "notifyOn": "Meldingen aan", "share": "Delen",
        "cal": "Agenda", "page": "Vluchtpagina", "airline": "Website maatschappij",
        "pkH": "Iemand ophalen?", "pkFrom": "Vertrek vanaf", "pkLeave": "Vertrek om", "pkLeaveNow": "Vertrek nu",
        "pkLands": "Landt", "pkOut": "Meestal uit de aankomsthal", "pkNote": "Rijtijden zijn gemiddeld, niet live. Kijk op Waze voordat u gaat.",
        "pkWaze": "Open in Waze", "pkHere": "Op de luchthaven", "pkWait": "Meestal buiten", "pkLanded": "Geland",
        "ciH": "Gaat u vliegen?", "ciWin": "Inchecken", "ciBe": "Wees op de luchthaven om", "ciNote": "Incheck-tijden zoals gepubliceerd door de luchthaven. Uw maatschappij beslist.",
        "liveOk": "Live", "liveOld": "Laatst bekend", "upd": "bijgewerkt {t}", "alertTitle": "Update {fn}", "landedAt": "Geland {t}",
        "departedAt": "Vertrokken {t}", "early": "{n} min te vroeg", "late": "{n} min te laat", "ontimeWord": "op tijd",
        "trackedToast": "U volgt {fn}. De vlucht blijft bovenaan deze pagina.", "untrackedToast": "U volgt {fn} niet meer.",
        "alertsToast": "Meldingen aan. Ze werken zolang deze pagina open is.", "alertsDenied": "Meldingen zijn geblokkeerd in uw browser.",
        "copied": "Link gekopieerd", "shareText": "{fn} {route}: {status}", "seeLive": "Live status", "ot30": "Op tijd, laatste 30 dagen",
        "avgDelay": "gem. vertraging", "lands": "landt", "leaves": "vertrekt", "cargo": "Vracht"},
 "es": {"scheduled": "Programado", "ontime": "A tiempo", "delayed": "Retrasado", "enroute": "En vuelo", "landed": "Aterrizó",
        "departed": "Despegó", "cancelled": "Cancelado", "diverted": "Desviado", "unknown": "Sin novedades",
        "min": "min", "today": "Hoy", "tomorrow": "Mañana", "yesterday": "Ayer", "earlier": "Ver {n} vuelos anteriores",
        "hideEarlier": "Ocultar vuelos anteriores", "none": "Ningún vuelo coincide.", "noneDay": "No hay vuelos en los próximos dos días.",
        "nextArr": "Próxima llegada", "nextDep": "Próxima salida", "yours": "Su vuelo", "from": "desde", "to": "a", "via": "vía",
        "in": "en {t}", "ago": "hace {t}", "h": "h", "m": "min", "now": "ahora",
        "sched": "Previsto", "exp": "Estimado", "act": "Real", "dep": "Salida", "arr": "Llegada",
        "aircraft": "Avión", "reg": "Matrícula", "dur": "Duración", "codeshare": "También como", "gate": "Puerta",
        "track": "Seguir", "tracking": "Siguiendo", "notify": "Avisarme", "notifyOn": "Avisos activos", "share": "Compartir",
        "cal": "Calendario", "page": "Página del vuelo", "airline": "Web de la aerolínea",
        "pkH": "¿Va a recoger a alguien?", "pkFrom": "Sale desde", "pkLeave": "Salga a las", "pkLeaveNow": "Salga ya",
        "pkLands": "Aterriza", "pkOut": "Suelen salir de llegadas", "pkNote": "Tiempos de viaje típicos, no en vivo. Consulte Waze antes de salir.",
        "pkWaze": "Abrir en Waze", "pkHere": "En el aeropuerto", "pkWait": "Suelen salir", "pkLanded": "Aterrizó",
        "ciH": "¿Va a volar?", "ciWin": "Facturación", "ciBe": "Esté en el aeropuerto a las", "ciNote": "Horarios de facturación publicados por el aeropuerto. Su aerolínea tiene la última palabra.",
        "liveOk": "En vivo", "liveOld": "Último dato", "upd": "actualizado {t}", "alertTitle": "Novedad {fn}", "landedAt": "Aterrizó {t}",
        "departedAt": "Despegó {t}", "early": "{n} min antes", "late": "{n} min tarde", "ontimeWord": "a tiempo",
        "trackedToast": "Siguiendo {fn}. Queda arriba en esta página.", "untrackedToast": "Ya no sigue {fn}.",
        "alertsToast": "Avisos activos mientras esta página esté abierta.", "alertsDenied": "Los avisos están bloqueados en su navegador.",
        "copied": "Enlace copiado", "shareText": "{fn} {route}: {status}", "seeLive": "Estado en vivo", "ot30": "A tiempo, últimos 30 días",
        "avgDelay": "retraso medio", "lands": "aterriza", "leaves": "sale", "cargo": "Carga"},
 "zh": {"scheduled": "计划", "ontime": "准点", "delayed": "延误", "enroute": "飞行中", "landed": "已降落",
        "departed": "已起飞", "cancelled": "已取消", "diverted": "备降", "unknown": "暂无更新",
        "min": "分钟", "today": "今天", "tomorrow": "明天", "yesterday": "昨天", "earlier": "显示较早的 {n} 个航班",
        "hideEarlier": "隐藏较早的航班", "none": "没有符合条件的航班。", "noneDay": "未来两天没有航班。",
        "nextArr": "下一个到达", "nextDep": "下一个出发", "yours": "您的航班", "from": "来自", "to": "前往", "via": "经停",
        "in": "{t}后", "ago": "{t}前", "h": "小时", "m": "分钟", "now": "现在",
        "sched": "计划", "exp": "预计", "act": "实际", "dep": "出发", "arr": "到达",
        "aircraft": "机型", "reg": "注册号", "dur": "飞行时间", "codeshare": "共享航班号", "gate": "登机口",
        "track": "关注", "tracking": "已关注", "notify": "提醒我", "notifyOn": "提醒已开启", "share": "分享",
        "cal": "日历", "page": "航班页面", "airline": "航空公司网站",
        "pkH": "要去接机吗？", "pkFrom": "出发地", "pkLeave": "建议出发", "pkLeaveNow": "现在出发",
        "pkLands": "降落", "pkOut": "旅客通常走出到达大厅", "pkNote": "车程为常规估计，非实时。出发前请查看 Waze。",
        "pkWaze": "在 Waze 中打开", "pkHere": "已在机场", "pkWait": "通常出来", "pkLanded": "已降落",
        "ciH": "要乘机出发？", "ciWin": "值机", "ciBe": "建议到达机场", "ciNote": "值机时间以机场公布为准，最终以航空公司为准。",
        "liveOk": "实时", "liveOld": "最近数据", "upd": "更新于{t}", "alertTitle": "{fn} 动态", "landedAt": "{t} 已降落",
        "departedAt": "{t} 已起飞", "early": "提前 {n} 分钟", "late": "晚 {n} 分钟", "ontimeWord": "准点",
        "trackedToast": "已关注 {fn}，它会固定在本页顶部。", "untrackedToast": "已取消关注 {fn}。",
        "alertsToast": "提醒已开启，仅在本页打开时有效。", "alertsDenied": "浏览器设置已阻止提醒。",
        "copied": "链接已复制", "shareText": "{fn} {route}：{status}", "seeLive": "实时动态", "ot30": "过去 30 天准点率",
        "avgDelay": "平均延误", "lands": "降落", "leaves": "出发", "cargo": "货运"},
 "fr": {"scheduled": "Prévu", "ontime": "À l’heure", "delayed": "Retardé", "enroute": "En vol", "landed": "Atterri",
        "departed": "Décollé", "cancelled": "Annulé", "diverted": "Dérouté", "unknown": "Pas de mise à jour",
        "min": "min", "today": "Aujourd’hui", "tomorrow": "Demain", "yesterday": "Hier", "earlier": "Voir {n} vols précédents",
        "hideEarlier": "Masquer les vols précédents", "none": "Aucun vol ne correspond.", "noneDay": "Aucun vol prévu pour les deux prochains jours.",
        "nextArr": "Prochaine arrivée", "nextDep": "Prochain départ", "yours": "Votre vol", "from": "de", "to": "vers", "via": "via",
        "in": "dans {t}", "ago": "il y a {t}", "h": " h", "m": " min", "now": "maintenant",
        "sched": "Prévu", "exp": "Estimé", "act": "Réel", "dep": "Départ", "arr": "Arrivée",
        "aircraft": "Avion", "reg": "Immatriculation", "dur": "Durée du vol", "codeshare": "Aussi vendu sous", "gate": "Porte",
        "track": "Suivre", "tracking": "Suivi", "notify": "M’alerter", "notifyOn": "Alertes activées", "share": "Partager",
        "cal": "Agenda", "page": "Page du vol", "airline": "Site de la compagnie",
        "pkH": "Vous venez chercher quelqu’un ?", "pkFrom": "Départ de", "pkLeave": "Partez à", "pkLeaveNow": "Partez maintenant",
        "pkLands": "Atterrit", "pkOut": "Sortie du hall d’arrivée en général", "pkNote": "Temps de trajet habituels, pas en direct. Consultez Waze avant de partir.",
        "pkWaze": "Ouvrir dans Waze", "pkHere": "À l’aéroport", "pkWait": "Sortie en général", "pkLanded": "Atterri",
        "ciH": "Vous partez ?", "ciWin": "Enregistrement", "ciBe": "Soyez à l’aéroport à", "ciNote": "Horaires d’enregistrement publiés par l’aéroport. Votre compagnie a le dernier mot.",
        "liveOk": "En direct", "liveOld": "Dernières données", "upd": "mis à jour {t}", "alertTitle": "Mise à jour {fn}", "landedAt": "Atterri à {t}",
        "departedAt": "Décollé à {t}", "early": "{n} min d’avance", "late": "{n} min de retard", "ontimeWord": "à l’heure",
        "trackedToast": "Vous suivez {fn}. Il reste en haut de cette page.", "untrackedToast": "Vous ne suivez plus {fn}.",
        "alertsToast": "Alertes activées tant que cette page est ouverte.", "alertsDenied": "Les alertes sont bloquées dans votre navigateur.",
        "copied": "Lien copié", "shareText": "{fn} {route} : {status}", "seeLive": "Statut en direct", "ot30": "À l’heure, 30 derniers jours",
        "avgDelay": "retard moyen", "lands": "atterrit", "leaves": "part", "cargo": "Fret"},
 "pt": {"scheduled": "Previsto", "ontime": "No horário", "delayed": "Atrasado", "enroute": "Em voo", "landed": "Pousou",
        "departed": "Decolou", "cancelled": "Cancelado", "diverted": "Desviado", "unknown": "Sem atualização",
        "min": "min", "today": "Hoje", "tomorrow": "Amanhã", "yesterday": "Ontem", "earlier": "Ver {n} voos anteriores",
        "hideEarlier": "Ocultar voos anteriores", "none": "Nenhum voo encontrado.", "noneDay": "Nenhum voo nos próximos dois dias.",
        "nextArr": "Próxima chegada", "nextDep": "Próxima partida", "yours": "Seu voo", "from": "de", "to": "para", "via": "via",
        "in": "em {t}", "ago": "há {t}", "h": "h", "m": "min", "now": "agora",
        "sched": "Previsto", "exp": "Estimado", "act": "Real", "dep": "Partida", "arr": "Chegada",
        "aircraft": "Aeronave", "reg": "Matrícula", "dur": "Tempo de voo", "codeshare": "Também vendido como", "gate": "Portão",
        "track": "Acompanhar", "tracking": "Acompanhando", "notify": "Avisar", "notifyOn": "Avisos ligados", "share": "Compartilhar",
        "cal": "Agenda", "page": "Página do voo", "airline": "Site da companhia",
        "pkH": "Vai buscar alguém?", "pkFrom": "Saindo de", "pkLeave": "Saia às", "pkLeaveNow": "Saia agora",
        "pkLands": "Pousa", "pkOut": "Costumam sair do desembarque", "pkNote": "Tempos de viagem típicos, não ao vivo. Confira o Waze antes de sair.",
        "pkWaze": "Abrir no Waze", "pkHere": "No aeroporto", "pkWait": "Costumam sair", "pkLanded": "Pousou",
        "ciH": "Vai embarcar?", "ciWin": "Check-in", "ciBe": "Esteja no aeroporto às", "ciNote": "Horários de check-in publicados pelo aeroporto. A companhia aérea tem a palavra final.",
        "liveOk": "Ao vivo", "liveOld": "Último dado", "upd": "atualizado {t}", "alertTitle": "Atualização {fn}", "landedAt": "Pousou às {t}",
        "departedAt": "Decolou às {t}", "early": "{n} min adiantado", "late": "{n} min atrasado", "ontimeWord": "no horário",
        "trackedToast": "Acompanhando {fn}. Ele fica no topo desta página.", "untrackedToast": "Você parou de acompanhar {fn}.",
        "alertsToast": "Avisos ligados enquanto esta página estiver aberta.", "alertsDenied": "Os avisos estão bloqueados no seu navegador.",
        "copied": "Link copiado", "shareText": "{fn} {route}: {status}", "seeLive": "Status ao vivo", "ot30": "No horário, últimos 30 dias",
        "avgDelay": "atraso médio", "lands": "pousa", "leaves": "sai", "cargo": "Carga"},
}

_DRIVE_I18N = {
    "en": {"d_pmb": "Paramaribo centre", "d_noord": "Paramaribo Noord", "d_lely": "Lelydorp", "d_meer": "Meerzorg / Commewijne", "d_here": "At the airport"},
    "nl": {"d_pmb": "Paramaribo centrum", "d_noord": "Paramaribo Noord", "d_lely": "Lelydorp", "d_meer": "Meerzorg / Commewijne", "d_here": "Op de luchthaven"},
    "es": {"d_pmb": "Centro de Paramaribo", "d_noord": "Paramaribo Norte", "d_lely": "Lelydorp", "d_meer": "Meerzorg / Commewijne", "d_here": "En el aeropuerto"},
    "zh": {"d_pmb": "帕拉马里博市中心", "d_noord": "帕拉马里博北区", "d_lely": "Lelydorp", "d_meer": "Meerzorg / Commewijne", "d_here": "已在机场"},
    "fr": {"d_pmb": "Centre de Paramaribo", "d_noord": "Paramaribo Nord", "d_lely": "Lelydorp", "d_meer": "Meerzorg / Commewijne", "d_here": "À l’aéroport"},
    "pt": {"d_pmb": "Centro de Paramaribo", "d_noord": "Paramaribo Norte", "d_lely": "Lelydorp", "d_meer": "Meerzorg / Commewijne", "d_here": "No aeroporto"},
}
for _lg, _d in _DRIVE_I18N.items():
    FL_I18N[_lg].update(_d)
_AFKL_I18N = {'en': {'boarding': 'Boarding', 'boardingL': 'Boarding', 'checkin': 'Check-in', 'reason': 'Reason', 'cs_open': 'Open', 'cs_notopen': 'Not open yet', 'cs_closed': 'Closed', 'cs_finalised': 'Closed'}, 'nl': {'boarding': 'Boarding', 'boardingL': 'Boarding', 'checkin': 'Inchecken', 'reason': 'Reden', 'cs_open': 'Open', 'cs_notopen': 'Nog niet open', 'cs_closed': 'Gesloten', 'cs_finalised': 'Gesloten'}, 'es': {'boarding': 'Embarcando', 'boardingL': 'Embarque', 'checkin': 'Facturación', 'reason': 'Motivo', 'cs_open': 'Abierto', 'cs_notopen': 'Aún no abierto', 'cs_closed': 'Cerrado', 'cs_finalised': 'Cerrado'}, 'zh': {'boarding': '正在登机', 'boardingL': '登机', 'checkin': '值机', 'reason': '原因', 'cs_open': '已开放', 'cs_notopen': '尚未开放', 'cs_closed': '已关闭', 'cs_finalised': '已关闭'}, 'fr': {'boarding': 'Embarquement', 'boardingL': 'Embarquement', 'checkin': 'Enregistrement', 'reason': 'Motif', 'cs_open': 'Ouvert', 'cs_notopen': 'Pas encore ouvert', 'cs_closed': 'Fermé', 'cs_finalised': 'Fermé'}, 'pt': {'boarding': 'Embarcando', 'boardingL': 'Embarque', 'checkin': 'Check-in', 'reason': 'Motivo', 'cs_open': 'Aberto', 'cs_notopen': 'Ainda não aberto', 'cs_closed': 'Encerrado', 'cs_finalised': 'Encerrado'}}
for _lg, _v in _AFKL_I18N.items():
    FL_I18N[_lg].update(_v)
_DOWN_I18N = {'en': 'Flight data is not available right now. It usually returns within half an hour.', 'nl': 'Vluchtgegevens zijn nu niet beschikbaar. Meestal zijn ze binnen een half uur terug.', 'es': 'Los datos de vuelos no están disponibles ahora. Suelen volver en media hora.', 'zh': '航班数据暂时无法获取，通常半小时内恢复。', 'fr': 'Les données de vol ne sont pas disponibles pour le moment. Elles reviennent en général dans la demi-heure.', 'pt': 'Os dados dos voos não estão disponíveis agora. Costumam voltar em meia hora.'}
for _lg, _v in _DOWN_I18N.items():
    FL_I18N[_lg]['down'] = _v
_LOCAL_I18N = {'en': 'local time', 'nl': 'lokale tijd', 'es': 'hora local', 'zh': '当地时间', 'fr': 'heure locale', 'pt': 'hora local'}
for _lg, _v in _LOCAL_I18N.items():
    FL_I18N[_lg]['local'] = _v
_VIA_I18N = {'en': ('Also from', 'Continues to'), 'nl': ('Ook uit', 'Vliegt door naar'), 'es': ('También desde', 'Continúa a'), 'zh': ('也来自', '继续飞往'), 'fr': ('Également de', 'Continue vers'), 'pt': ('Também de', 'Continua para')}
for _lg, (_a, _c) in _VIA_I18N.items():
    FL_I18N[_lg].update({'alsoFrom': _a, 'cont': _c})


FL_JS = r"""<script>
(function(){
'use strict';
var D=document,W=window;
var LANG=(D.documentElement.lang||'en').slice(0,2).toLowerCase();
var I=W.FL_I18N||{},T=Object.assign({},I.en||{},I[LANG]||{});
var LOC={en:'en-GB',nl:'nl-NL',es:'es-ES',zh:'zh-CN',fr:'fr-FR',pt:'pt-BR'}[LANG]||'en-GB';
var CFG=W.FL_CFG||{},DATA=W.FL_DATA||{flights:[]};
var PFX=(LANG==='en'?'':'/'+LANG);
function tr(k,o){var s=(T[k]!=null?T[k]:k);if(o){for(var x in o){s=s.split('{'+x+'}').join(o[x]);}}return s;}
function esc(s){return String(s==null?'':s).replace(/[&<>"]/g,function(c){return{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c];});}
function now(){return Math.floor(Date.now()/1000);}
function pad(n){return(n<10?'0':'')+n;}
function hm(ts){if(!ts)return'';var d=new Date((ts-10800)*1000);return pad(d.getUTCHours())+':'+pad(d.getUTCMinutes());}
function hmz(ts,oz){if(oz==null)return hm(ts);var d=new Date((ts+oz)*1000);return pad(d.getUTCHours())+':'+pad(d.getUTCMinutes());}
function srDay(ts){return Math.floor((ts-10800)/86400);}
function lsGet(k,d){try{var v=localStorage.getItem(k);return v==null?d:JSON.parse(v);}catch(e){return d;}}
function lsSet(k,v){try{localStorage.setItem(k,JSON.stringify(v));}catch(e){}}
function tval(r){return r.a||r.e||r.s;}
function shown(r,n){var st=r.st||'scheduled';if(r.d==='D'&&r.brd==='Open'&&(st==='scheduled'||st==='delayed'))return'boarding';if(st==='scheduled'&&r.e)return'ontime';if(st==='scheduled'&&tval(r)<n-1200)return'unknown';return st;}
function dur(sec){sec=Math.abs(sec);var h=Math.floor(sec/3600),m=Math.round((sec%3600)/60);if(m===60){h++;m=0;}
  if(h&&m)return h+tr('h')+' '+m+' '+tr('m');if(h)return h+tr('h');return Math.max(1,m)+' '+tr('m');}
function relT(ts,n){var d=ts-n;if(Math.abs(d)<60)return tr('now');return d>0?tr('in',{t:dur(d)}):tr('ago',{t:dur(d)});}
function dayLabel(ts,n){var d=srDay(ts)-srDay(n);if(d===0)return tr('today');if(d===1)return tr('tomorrow');if(d===-1)return tr('yesterday');
  try{return new Intl.DateTimeFormat(LOC,{weekday:'long',day:'numeric',month:'long',timeZone:'America/Paramaribo'}).format(new Date(ts*1000));}catch(e){return'';}}
function route(r){var me=(r.ap==='EAX'?'Paramaribo':'Paramaribo');return r.d==='A'?(r.on+' → '+me):(me+' → '+r.on);}
function pillTxt(r,n){var st=shown(r,n),t=tr(st);if(st==='delayed'&&r.dl)t+=' +'+r.dl+' '+tr('min');return t;}
function isFinal(r){return r.st==='landed'||r.st==='departed'||r.st==='cancelled'||r.st==='diverted';}
function pageUrl(r){return (CFG.pages||DATA.pages||[]).indexOf(r.sl)>=0?(PFX+'/'+r.sl):(PFX+'/flights#f='+encodeURIComponent(r.k));}
var tracked=lsGet('fl-track',[]);if(!Array.isArray(tracked))tracked=[];
var notifyOn=lsGet('fl-notify',false);
function isTracked(k){return tracked.indexOf(k)>=0;}
var toastT;function toast(msg){var t=D.getElementById('fl-toast');if(!t)return;t.textContent=msg;t.hidden=false;clearTimeout(toastT);toastT=setTimeout(function(){t.hidden=true;},3600);}
function ga(ev,p){try{if(W.gtag)W.gtag('event',ev,p||{});}catch(e){}}

/* ── row + details markup ── */
function rowHtml(r,n,open){var st=shown(r,n),t=tval(r),big=hm(t),small=Math.abs(t-r.s)>=300?hm(r.s):'';
  var p1=srDay(t)>srDay(n)+1?'':'';var cs=r.cs&&r.cs.length?' · '+r.cs.join(', '):'';
  var via=r.via&&r.via.length?'<span class="fr-sub">'+esc((r.vfirst?tr('alsoFrom'):tr('cont'))+' '+r.via.join(', '))+'</span>':'';
  var past=(isFinal(r)&&t<n-1800)?' past':'';
  return '<li class="fr'+past+'" data-k="'+esc(r.k)+'"><button class="fr-main" type="button" aria-expanded="'+(open?'true':'false')+'">'+
   '<span class="fr-time" translate="no"><b>'+big+p1+'</b>'+(small?'<s>'+small+'</s>':'')+'</span>'+
   '<span class="fr-mid"><span class="fr-city" translate="no">'+esc(r.on||r.oi)+'<small>'+esc(r.oi||'')+'</small></span>'+
   '<span class="fr-fn" translate="no">'+(isTracked(r.k)?'<span class="tk">★</span> ':'')+esc(r.fn)+' · '+esc(r.al||'')+esc(cs)+'</span>'+via+'</span>'+
   '<span class="fr-st"><span class="pill p-'+st+'">'+esc(pillTxt(r,n))+'</span>'+subLine(r,n)+'</span></button>'+
   '<div class="fr-det"'+(open?'':' hidden')+'>'+(open?detHtml(r,n):'')+'</div></li>';}
function subLine(r,n){var st=shown(r,n),t=tval(r);
  if(st==='landed'||st==='departed'){if(r.dl!=null&&Math.abs(r.dl)>=5)return'<span class="fr-sub">'+esc(r.dl>0?tr('late',{n:r.dl}):tr('early',{n:-r.dl}))+'</span>';return'';}
  if(st==='cancelled'||st==='unknown')return'';
  if(t>n&&t-n<6*3600)return'<span class="fr-sub">'+esc(relT(t,n))+'</span>';return'';}
function fact(k,v){return v?'<div><dt>'+esc(tr(k))+'</dt><dd translate="no">'+v+'</dd></div>':'';}
function detHtml(r,n){var me=r.ap, oth=r.oi;
  var depS=r.d==='D'?r.s:r.sd, arrS=r.d==='A'?r.s:r.sa;
  var g='<dl class="fd-grid">';
  g+=fact('sched',esc(hm(r.s)));
  if(r.e&&!r.a&&Math.abs(r.e-r.s)>=60)g+=fact('exp',esc(hm(r.e)));
  if(r.a)g+=fact('act',esc(hm(r.a)));
  if(r.sd&&r.sa&&r.sa>r.sd)g+=fact('dur',esc(dur(r.sa-r.sd)));
  if(r.d==='A'&&r.sd)g+=fact('dep',esc(oth+' '+hmz(r.sd,r.oz))+' <small>'+esc(r.oz!=null?tr('local'):'SR')+'</small>');
  if(r.d==='D'&&r.sa)g+=fact('arr',esc(oth+' '+hmz(r.sa,r.oz))+' <small>'+esc(r.oz!=null?tr('local'):'SR')+'</small>');
  g+=fact('aircraft',esc(r.ac||''));g+=fact('reg',esc(r.rg||''));
  if(r.gate)g+=fact('gate',esc(r.gate));
  if(r.d==='D'&&r.chk&&!isFinal(r))g+=fact('checkin',esc(tr('cs_'+r.chk.toLowerCase().replace(/\s+/g,''))));
  if(r.d==='D'&&r.brd&&!isFinal(r))g+=fact('boardingL',esc(tr('cs_'+r.brd.toLowerCase().replace(/\s+/g,''))));
  if(r.cs&&r.cs.length)g+=fact('codeshare',esc(r.cs.join(', ')));
  g+='</dl>';
  if(r.why&&((r.dl||0)>=5||r.st==='cancelled'))g+='<p class="fd-why"><b>'+esc(tr('reason'))+(LANG==='fr'?'\u00a0:':':')+'</b> <span lang="en">'+esc(r.why)+'</span></p>';
  var on=isTracked(r.k);
  var a='<div class="fd-acts">'+
   '<button class="fbtn'+(on?' on':'')+'" data-act="track" type="button">★ '+esc(tr(on?'tracking':'track'))+'</button>'+
   (('Notification' in W)?'<button class="fbtn'+(notifyOn&&W.Notification.permission==='granted'?' on':'')+'" data-act="notify" type="button">'+esc(tr(notifyOn&&W.Notification.permission==='granted'?'notifyOn':'notify'))+'</button>':'')+
   '<button class="fbtn wa" data-act="share" type="button">'+esc(tr('share'))+'</button>'+
   '<a class="fbtn" data-act="cal" target="_blank" rel="noopener" href="'+esc(calUrl(r))+'">'+esc(tr('cal'))+'</a>'+
   (CFG.mode!=='flight'?'<a class="fbtn" href="'+esc(pageUrl(r))+'">'+esc(tr('page'))+' →</a>':'')+
   (r.site?'<a class="fbtn" target="_blank" rel="noopener" href="'+esc(r.site)+'">'+esc(tr('airline'))+' ↗</a>':'')+
   '</div>';
  return g+a+(r.d==='A'?pickupHtml(r,n):checkinHtml(r,n));}
function driveList(ap){return (CFG.drive||{})[ap]||[];}
function placeSel(ap,cls){var L=driveList(ap),cur=lsGet('fl-from-'+ap,L.length?L[0][0]:'');
  return '<select class="'+cls+'">'+L.map(function(x){return'<option value="'+x[0]+'"'+(x[0]===cur?' selected':'')+'>'+esc(tr('d_'+x[0]))+'</option>';}).join('')+'</select>';}
function driveMin(ap,id){var L=driveList(ap);for(var i=0;i<L.length;i++)if(L[i][0]===id)return L[i][2];return L.length?L[0][2]:50;}
function exitWin(r){var big=r.oi==='AMS'||/777|787|A330|A350|747|767|A340/.test(r.ac||'');if(r.ap==='EAX')return[10,25];return big?[30,60]:[20,40];}
function pickupHtml(r,n){if(r.st==='cancelled')return'';var L=driveList(r.ap);if(!L.length)return'';
  return '<div class="pk" data-pk="1"><h4>'+esc(tr('pkH'))+'</h4><label>'+esc(tr('pkFrom'))+' '+placeSel(r.ap,'pk-from')+'</label><p class="res" aria-live="polite">'+pickupRes(r,n)+'</p>'+
   '<p class="note">'+esc(tr('pkNote'))+'</p><p style="margin:.5rem 0 0"><a class="fbtn" target="_blank" rel="noopener" href="https://waze.com/ul?ll='+(CFG.coords||{})[r.ap]+'&navigate=yes">'+esc(tr('pkWaze'))+' ↗</a></p></div>';}
function pickupRes(r,n,from){var cur=from||lsGet('fl-from-'+r.ap,(driveList(r.ap)[0]||[''])[0]);var land=r.a||r.e||r.s,w=exitWin(r),dm=driveMin(r.ap,cur);
  var outA=land+w[0]*60,outB=land+w[1]*60,leave=outA-dm*60;
  var s='<span>'+esc(r.a?tr('pkLanded'):tr('pkLands'))+'</span> <b translate="no">'+hm(land)+'</b> · <span>'+esc(tr('pkOut'))+'</span> <b translate="no">'+hm(outA)+'–'+hm(outB)+'</b>';
  if(dm>0&&outB>n){s+='<br><span>'+esc(leave<=n?tr('pkLeaveNow'):tr('pkLeave'))+'</span>'+(leave<=n?'':' <b translate="no">'+hm(leave)+'</b>');}
  return s;}
function checkinHtml(r,n){if(r.st==='cancelled'||r.st==='departed'||r.ap!=='PBM')return'';
  var ci=(CFG.checkin||{})[r.oi]||(CFG.checkin||{})._||[3,2],open=r.s-ci[0]*3600,close=r.s-ci[1]*3600,be=close-1800;
  if(close<n)return'';
  return '<div class="pk" data-ci="1"><h4>'+esc(tr('ciH'))+'</h4><p class="res"><span>'+esc(tr('ciWin'))+'</span> <b translate="no">'+hm(open)+'–'+hm(close)+'</b> · <span>'+esc(tr('ciBe'))+'</span> <b translate="no">'+hm(be)+'</b></p>'+
   '<label>'+esc(tr('pkFrom'))+' '+placeSel(r.ap,'ci-from')+'</label><p class="res ci-leave">'+ciLeave(r,n,be)+'</p><p class="note">'+esc(tr('ciNote'))+'</p></div>';}
function ciLeave(r,n,be,from){var cur=from||lsGet('fl-from-'+r.ap,(driveList(r.ap)[0]||[''])[0]),dm=driveMin(r.ap,cur);if(dm<=0)return'';var lv=be-dm*60;
  return '<span>'+esc(lv<=n?tr('pkLeaveNow'):tr('pkLeave'))+'</span>'+(lv<=n?'':' <b translate="no">'+hm(lv)+'</b>');}
function gcal(ts){var d=new Date(ts*1000);return d.getUTCFullYear()+pad(d.getUTCMonth()+1)+pad(d.getUTCDate())+'T'+pad(d.getUTCHours())+pad(d.getUTCMinutes())+'00Z';}
function calUrl(r){var t=r.d==='A'?(r.e||r.s):r.s;var title=r.fn+' '+route(r);
  return 'https://calendar.google.com/calendar/render?action=TEMPLATE&text='+encodeURIComponent(title)+'&dates='+gcal(t-(r.d==='D'?3*3600:0))+'/'+gcal(t+(r.d==='A'?3600:0))+'&details='+encodeURIComponent(tr('seeLive')+': '+location.origin+pageUrl(r));}
function shareText(r,n){var st=shown(r,n),s=pillTxt(r,n);if(st==='landed')s=tr('landedAt',{t:hm(r.a||r.e||r.s)});else if(st==='departed')s=tr('departedAt',{t:hm(r.a||r.e||r.s)});else if(st!=='cancelled')s+=' · '+hm(tval(r))+' SR';
  return tr('shareText',{fn:r.fn,route:route(r),status:s});}

/* ── data helpers ── */
var SITES=CFG.sites||{};
function rows(){var L=(DATA.flights||[]);L.forEach(function(r){if(!r.site&&SITES[r.ai])r.site=SITES[r.ai];});return L;}
function byKey(k){var L=rows();for(var i=0;i<L.length;i++)if(L[i].k===k)return L[i];return null;}

/* ── live line ── */
function liveLine(){var el=D.getElementById('fl-live');if(!el)return;var n=now(),ap=CFG.mode==='flight'?(CFG.ap||'PBM'):state.ap;var a=(DATA.airports||{})[ap]||{};
  var asof=a.as_of||DATA.built,stale=!asof||(n-asof)>(DATA.stale_after_min||75)*60;
  el.className='fl-live'+(stale?' off':'');
  el.innerHTML='<span class="dot" aria-hidden="true"></span><b>'+esc(stale?tr('liveOld'):tr('liveOk'))+'</b><span>'+esc(tr('upd',{t:relT(asof||n,n)}))+'</span>';}

/* ── BOARD ── */
var state={ap:'PBM',d:'A',q:'',cg:false,earlier:false,open:null};
function initState(){var u=new URLSearchParams(location.search);var ap=(u.get('ap')||lsGet('fl-ap','PBM')+'').toUpperCase(),d=(u.get('d')||lsGet('fl-d','A')+'').toUpperCase();
  state.ap=(ap==='EAX'?'EAX':'PBM');state.d=(d==='D'||d==='DEP'?'D':'A');state.cg=!!lsGet('fl-cg',false);
  var h=/#f=([^&]+)/.exec(location.hash);if(h){var k=decodeURIComponent(h[1]),r=byKey(k);if(r){state.ap=r.ap;state.d=r.d;state.open=k;state.earlier=true;}}}
function filtered(){var n=now(),q=state.q.trim().toLowerCase();
  return rows().filter(function(r){if(r.ap!==state.ap||r.d!==state.d)return false;if(r.cg&&!state.cg&&!isTracked(r.k))return false;
    if(q){var hay=(r.fn+' '+(r.al||'')+' '+(r.on||'')+' '+(r.oi||'')+' '+(r.cs||[]).join(' ')+' '+(r.via||[]).join(' ')).toLowerCase();if(hay.indexOf(q)<0)return false;}
    return tval(r)>=n-12*3600;}).sort(function(a,b){return tval(a)-tval(b);});}
function renderBoard(){var box=D.getElementById('fl-board');if(!box)return;var n=now(),L=filtered();
  var early=L.filter(function(r){return (isFinal(r)||shown(r,n)==='unknown')&&tval(r)<n-1800&&r.k!==state.open;});
  var rest=L.filter(function(r){return early.indexOf(r)<0;});
  var h='';
  if(early.length){h+='<button class="fl-more" type="button" data-act="earlier">'+esc(state.earlier?tr('hideEarlier'):tr('earlier',{n:early.length}))+'</button>';
    if(state.earlier)h+=group(early,n);}
  h+=group(rest,n);
  if(!L.length){var apo=(DATA.airports||{})[state.ap]||{};h='<p class="fl-empty">'+esc(state.q?tr('none'):(apo.ok===false&&!rows().some(function(r){return r.ap===state.ap;})?tr('down'):tr('noneDay')))+'</p>';}
  box.innerHTML=h;
  D.querySelectorAll('[data-seg] button').forEach(function(b){var on=(b.getAttribute('data-v')===state.ap||b.getAttribute('data-v')===state.d);b.setAttribute('aria-pressed',on?'true':'false');});
  counts();}
function group(L,n){var h='',last=null;L.forEach(function(r){var dd=srDay(tval(r));if(dd!==last){if(last!==null)h+='</ul>';h+='<h3 class="fl-day">'+esc(dayLabel(tval(r),n))+'</h3><ul class="fl-list">';last=dd;}h+=rowHtml(r,n,r.k===state.open);});if(last!==null)h+='</ul>';return h;}
function counts(){var n=now();['A','D'].forEach(function(d){var c=rows().filter(function(r){return r.ap===state.ap&&r.d===d&&(!r.cg||state.cg)&&tval(r)>=n-1800&&srDay(tval(r))<=srDay(n)+1;}).length;
  var el=D.querySelector('[data-v="'+d+'"] .n');if(el)el.textContent=c?String(c):'';});}
function renderNext(){var box=D.getElementById('fl-next');if(!box)return;var n=now(),h='';
  tracked.forEach(function(k){var r=byKey(k);if(r&&tval(r)>=n-6*3600)h+=card(r,n,tr('yours'),true);});
  if(CFG.mode!=='flight'){['A','D'].forEach(function(d){var c=rows().filter(function(r){return r.ap===state.ap&&r.d===d&&!r.cg&&r.st!=='cancelled'&&!isFinal(r)&&tval(r)>=n-600&&!isTracked(r.k);}).sort(function(a,b){return tval(a)-tval(b);})[0];
    if(c)h+=card(c,n,tr(d==='A'?'nextArr':'nextDep'),false);});}
  box.innerHTML=h;box.hidden=!h;}
function card(r,n,label,trk){var t=tval(r);return '<button class="fl-card fl-nc'+(trk?' trk':'')+'" type="button" data-open="'+esc(r.k)+'"><span class="l">'+esc(label)+'</span>'+
  '<span class="big" translate="no">'+hm(t)+(Math.abs(t-r.s)>=300?'<small><s>'+hm(r.s)+'</s></small>':'')+'</span>'+
  '<span class="r" translate="no">'+esc(r.fn+' · '+(r.d==='A'?(r.on+' → '+r.ap):(r.ap+' → '+r.on)))+'</span>'+
  '<span class="c"><span class="pill p-'+shown(r,n)+'">'+esc(pillTxt(r,n))+'</span> '+esc(isFinal(r)?'':(Math.abs(t-n)>12*3600?dayLabel(t,n):relT(t,n)))+'</span></button>';}
function openRow(k){var r=byKey(k);if(!r)return;if(CFG.mode==='flight'){var el=D.getElementById('fp-status');if(el)el.scrollIntoView({behavior:'smooth',block:'start'});return;}
  state.ap=r.ap;state.d=r.d;state.open=k;state.earlier=true;renderAll();var li=D.querySelector('li[data-k="'+CSS.escape(k)+'"]');if(li)li.scrollIntoView({behavior:'smooth',block:'center'});}

/* ── FLIGHT PAGE ── */
function legsFor(){var fn=CFG.fn,n=now();var L=rows().filter(function(r){return r.fn===fn;});var out={};
  L.forEach(function(r){var key=r.d+r.ap;var cur=out[key];var score=function(x){var t=tval(x);return (isFinal(x)&&t<n-3*3600)?1e9+Math.abs(t-n):Math.abs(t-n);};if(!cur||score(r)<score(cur))out[key]=r;});
  return Object.keys(out).map(function(k){return out[k];}).sort(function(a,b){return a.s-b.s;});}
function renderFlight(){var box=D.getElementById('fp-status');if(!box)return;var n=now(),L=legsFor();if(!L.length)return;
  var h='';L.forEach(function(r){var t=tval(r),st=shown(r,n);
    h+='<div class="fl-card fp-status" data-k="'+esc(r.k)+'"><div class="row"><span class="when">'+esc(dayLabel(r.s,n))+' · '+esc(tr(r.d==='A'?'arr':'dep'))+' '+esc(r.ap)+'</span><span class="pill p-'+st+'">'+esc(pillTxt(r,n))+'</span></div>'+
      '<div class="big" translate="no">'+hm(t)+(Math.abs(t-r.s)>=300?'<s>'+hm(r.s)+'</s>':'')+'</div>'+
      '<p class="lbl" translate="no">'+esc(route(r))+(isFinal(r)||Math.abs(t-n)>12*3600?'':' · '+esc(relT(t,n)))+'</p>'+
      '<div class="fr-det">'+detHtml(r,n)+'</div></div>';});
  box.innerHTML=h;}

/* ── events ── */
D.addEventListener('click',function(e){var t=e.target.closest('[data-act],[data-open],.fr-main,[data-seg] button');if(!t)return;
  if(t.matches('[data-seg] button')){var v=t.getAttribute('data-v');if(v==='PBM'||v==='EAX'){state.ap=v;lsSet('fl-ap',v);}else{state.d=v;lsSet('fl-d',v);}state.open=null;state.earlier=false;renderAll();ga('fl_filter',{v:v});return;}
  if(t.hasAttribute('data-open')){openRow(t.getAttribute('data-open'));return;}
  if(t.classList.contains('fr-main')){var li=t.closest('li'),k=li.getAttribute('data-k');state.open=(state.open===k?null:k);
    var det=li.querySelector('.fr-det'),open=state.open===k;t.setAttribute('aria-expanded',open?'true':'false');
    if(open){D.querySelectorAll('.fr-det:not([hidden])').forEach(function(x){if(x!==det){x.hidden=true;var b=x.parentNode.querySelector('.fr-main');if(b)b.setAttribute('aria-expanded','false');}});det.innerHTML=detHtml(byKey(k),now());det.hidden=false;ga('fl_open',{fn:(byKey(k)||{}).fn});}
    else det.hidden=true;return;}
  var act=t.getAttribute('data-act'),host=t.closest('[data-k]'),r=host?byKey(host.getAttribute('data-k')):null;
  if(act==='earlier'){state.earlier=!state.earlier;renderBoard();return;}
  if(!r)return;
  if(act==='track'){var i=tracked.indexOf(r.k);if(i>=0){tracked.splice(i,1);toast(tr('untrackedToast',{fn:r.fn}));}else{tracked.push(r.k);toast(tr('trackedToast',{fn:r.fn}));snap[r.k]=sig(r);}
    tracked=tracked.slice(-8);lsSet('fl-track',tracked);ga('fl_track',{fn:r.fn});renderAll();return;}
  if(act==='notify'){if(!('Notification' in W))return;W.Notification.requestPermission().then(function(p){notifyOn=(p==='granted');lsSet('fl-notify',notifyOn);
      if(notifyOn){if(!isTracked(r.k)){tracked.push(r.k);lsSet('fl-track',tracked);snap[r.k]=sig(r);}toast(tr('alertsToast'));}else toast(tr('alertsDenied'));ga('fl_notify',{fn:r.fn,ok:notifyOn});renderAll();});return;}
  if(act==='share'){var txt=shareText(r,now()),url=location.origin+pageUrl(r);ga('fl_share',{fn:r.fn});
    if(navigator.share){navigator.share({text:txt,url:url}).catch(function(){});}else{W.open('https://wa.me/?text='+encodeURIComponent(txt+' '+url),'_blank','noopener');}return;}
  if(act==='cal'){ga('fl_cal',{fn:r.fn});return;}
});
D.addEventListener('change',function(e){var s=e.target;if(!s.matches('.pk-from,.ci-from'))return;var host=s.closest('[data-k]'),r=host?byKey(host.getAttribute('data-k')):null;if(!r)return;
  lsSet('fl-from-'+r.ap,s.value);var n=now();
  if(s.classList.contains('pk-from')){s.closest('.pk').querySelector('.res').innerHTML=pickupRes(r,n,s.value);}
  else{var ci=(CFG.checkin||{})[r.oi]||(CFG.checkin||{})._||[3,2];s.closest('.pk').querySelector('.ci-leave').innerHTML=ciLeave(r,n,r.s-ci[1]*3600-1800,s.value);}});
var qi=D.getElementById('fl-q');if(qi)qi.addEventListener('input',function(){state.q=qi.value;renderBoard();});
var cgi=D.getElementById('fl-cg');if(cgi){cgi.checked=state.cg;cgi.addEventListener('change',function(){state.cg=cgi.checked;lsSet('fl-cg',state.cg);renderBoard();});}

/* ── refresh + alerts ── */
var snap={};function sig(r){return (r.st||'')+'|'+Math.round(tval(r)/300);}
function snapAll(){tracked.forEach(function(k){var r=byKey(k);if(r)snap[k]=sig(r);});}
function alerts(){var n=now();tracked.forEach(function(k){var r=byKey(k);if(!r)return;var s=sig(r);if(snap[k]&&snap[k]!==s){var msg=shareText(r,n);toast(msg);
    if(notifyOn&&('Notification' in W)&&W.Notification.permission==='granted'){try{new W.Notification(tr('alertTitle',{fn:r.fn}),{body:msg,tag:r.k});}catch(e){}}}snap[k]=s;});}
function refresh(){if(D.hidden)return;fetch('/data/flights_live.json?t='+Math.floor(Date.now()/60000),{cache:'no-store'}).then(function(x){return x.ok?x.json():null;}).then(function(j){
  if(!j||!j.flights)return;if(j.built&&DATA.built&&j.built<DATA.built)return;DATA=j;alerts();renderAll();}).catch(function(){});}
function renderAll(){if(CFG.mode==='flight')renderFlight();else renderBoard();renderNext();liveLine();}
if(CFG.mode!=='flight')initState();
snapAll();renderAll();
setInterval(function(){if(!D.hidden){renderAll();}},45000);
setInterval(refresh,120000);
D.addEventListener('visibilitychange',function(){if(!D.hidden)refresh();});
setTimeout(refresh,4000);
})();
</script>"""


# ── page assembly ─────────────────────────────────────────────────────────────

def _head(ctx, title, desc, fname, ld_blocks, title_l10n=None, desc_l10n=None, og_image=None):
    SITE = ctx["SITE_URL"]
    url = f"{SITE}/{fname}"
    ld = "".join('\n  <script type="application/ld+json">\n  ' + ctx["_ld_safe"](json.dumps(b, ensure_ascii=False)) + '\n  </script>'
                 for b in ld_blocks)
    full = title + " | Explore Suriname"
    tl = f' translate="no" data-l10n="{title_l10n}"' if title_l10n else ""
    dl = f' data-l10n-content="{desc_l10n}"' if desc_l10n else ""
    img = og_image or f"{SITE}/og-image.jpg"
    return (ctx["PAGE_HEAD"]
            + f'\n  <title{tl}>{esc(full)}</title>'
            + f'\n  <meta name="description" content="{esc(desc)}"{dl}>'
            + f'\n  <link rel="canonical" href="{url}">'
            + '\n  <meta property="og:type" content="website">'
            + '\n  <meta property="og:site_name" content="Explore Suriname">'
            + f'\n  <meta property="og:url" content="{url}">'
            + f'\n  <meta property="og:title" content="{esc(full)}"' + (f' data-l10n-content="{title_l10n}"' if title_l10n else '') + '>'
            + f'\n  <meta property="og:description" content="{esc(desc)}"{dl}>'
            + f'\n  <meta property="og:image" content="{img}">'
            + '\n  <meta name="twitter:card" content="summary_large_image">'
            + '\n  <meta name="twitter:site" content="@exploringsuriname">'
            + f'\n  <meta name="twitter:title" content="{esc(full)}"' + (f' data-l10n-content="{title_l10n}"' if title_l10n else '') + '>'
            + f'\n  <meta name="twitter:description" content="{esc(desc)}"{dl}>'
            + f'\n  <meta name="twitter:image" content="{img}">'
            + ld + "\n" + FL_CSS + "\n</head>")


def _bc(SITE, items):
    return {"@context": "https://schema.org", "@type": "BreadcrumbList",
            "itemListElement": [{"@type": "ListItem", "position": i + 1, "name": n, "item": u}
                                for i, (n, u) in enumerate(items)]}


def _airport_ld():
    out = []
    for a in F.AIRPORTS:
        out.append({"@context": "https://schema.org", "@type": "Airport", "name": a["name"],
                    "iataCode": a["iata"], "icaoCode": a["icao"],
                    "address": {"@type": "PostalAddress", "addressCountry": "SR",
                                "addressLocality": a["place"]},
                    "geo": {"@type": "GeoCoordinates", "latitude": a["lat"], "longitude": a["lon"]}})
    out[0]["url"] = "https://www.japi-airport.com/"
    return out


def _cfg(extra=None):
    cfg = {"drive": {ap: [[i, lbl, m] for (i, lbl, m) in L] for ap, L in F.DRIVE.items()},
           "checkin": {k: list(v) for k, v in F.CHECKIN.items()},
           "coords": {a["iata"]: f'{a["lat"]},{a["lon"]}' for a in F.AIRPORTS},
           "sites": {k: v["site"] for k, v in F.AIRLINES.items() if v.get("site")},
           "pages": sorted(F.PAGE_SLUGS)}
    for k, v in F.AIRLINES_ICAO.items():
        if v.get("site"):
            cfg["sites"][k] = v["site"]
    cfg.update(extra or {})
    return cfg


def _scripts(live, cfg):
    j = lambda o: json.dumps(o, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
    return ('<div class="fl-toast" id="fl-toast" role="status" aria-live="polite" hidden></div>'
            '<script>window.FL_I18N=' + j(FL_I18N) + ';window.FL_CFG=' + j(cfg) + ';window.FL_DATA=' + j(live) + ';</script>'
            + FL_JS)


def _live_payload(c):
    now = c["now"]
    return {"built": now, "airports": {a["iata"]: {"ok": c["ok"].get(a["iata"], False),
                                                   "as_of": c["fetched"].get(a["iata"]) or None} for a in F.AIRPORTS},
            "stale_after_min": 75, "pages": sorted(F.PAGE_SLUGS), "flights": F.live_rows(c["boards"], now)}


def _hero(kicker, h1, sub, back_href="./", back_txt="Back to Home"):
    return ('<header class="fl-hero"><div class="in">'
            f'<a class="back" href="{back_href}">&#8592; {back_txt}</a>'
            f'<p class="k">{kicker}</p><h1>{h1}</h1>'
            + (f'<p class="sub">{sub}</p>' if sub else '')
            + '<p class="fl-live" id="fl-live"><span class="dot" aria-hidden="true"></span><b>Live</b></p>'
            '</div></header>')


def _dur_span(sec):
    if not sec:
        return ""
    return (f'<span translate="no" data-l10n="{_l10n_attr(lambda lg: _dur_text(sec, lg))}">'
            f'{esc(_dur_text(sec, "en"))}</span>')


def _fmt_dur(sec):
    if not sec:
        return ""
    h, m = int(sec // 3600), int(round((sec % 3600) / 60))
    return f"{h} h {m:02d} min" if h else f"{m} min"


# ── the board page ────────────────────────────────────────────────────────────

def build_board(ctx, c):
    SITE = ctx["SITE_URL"]
    now = c["now"]
    boards, groups = c["boards"], c["groups"]
    dests = _destinations(groups, boards, now)
    agg = _airline_stats(groups, now)
    hist_since = min((v["s"] for v in (c["hist"].get("f") or {}).values()), default=now)

    # FAQ, generated from the data where possible
    al_names = sorted({d for x in dests for d in x["airlines"]})
    dest_names = [x["city"] for x in dests[:10]]
    faq_l10n = {}
    _al_list = al_names or ["KLM", "Surinam Airways", "Copa Airlines", "Caribbean Airlines"]
    faq_l10n[0] = _l10n_attr(lambda lg: _l("faq_al", lg, list=_join(_al_list, lg)))
    if dest_names:
        faq_l10n[1] = _l10n_attr(lambda lg: _l("faq_dest", lg, list=_join(dest_names, lg)))
    faq = [
        ("Which airlines fly to Suriname?",
         _l("faq_al", "en", list=_join(_al_list, "en"))),
        ("Where can I fly direct from Suriname?",
         _l("faq_dest", "en", list=_join(dest_names, "en")) if dest_names else
         "Direct flights from Johan Adolf Pengel go to Amsterdam, Panama City, Port of Spain, Curaçao, Aruba, Georgetown, Belém and Miami."),
        ("How do I know if a flight to Suriname is delayed?",
         "The board on this page refreshes by itself every two minutes. A delayed flight shows its expected time, the original "
         "time crossed out and the number of minutes late. Tap a flight to track it; it then stays at the top of the page and "
         "your browser can alert you when its status changes while the page is open."),
        ("What time should I leave to pick someone up at Johan Adolf Pengel airport?",
         "Open the arriving flight on this page and choose where you leave from. The pickup helper adds the usual time it takes "
         "to get through immigration and baggage claim and the typical drive to the airport, and tells you when to leave. "
         "Check Waze for the live traffic picture before you go."),
        ("When does check-in open at Johan Adolf Pengel airport?",
         "According to the airport, check-in for flights to Amsterdam opens five hours and closes two hours before departure. "
         "For all regional flights it opens three hours and closes two hours before departure. Your airline has the final word."),
        ("What is the main airport in Suriname?",
         "Johan Adolf Pengel International Airport (PBM), also called Zanderij, about 45 km south of Paramaribo. Eduard Alexander "
         "Gummels Airport (EAX) at Zorg en Hoop in Paramaribo handles domestic flights, interior charters and short regional "
         "flights to Guyana."),
        ("How far is Johan Adolf Pengel Airport from Paramaribo?",
         "About 45 km. The drive from central Paramaribo usually takes 45 to 60 minutes depending on traffic."),
        ("How long is a flight from Amsterdam to Suriname?",
         "A direct flight from Amsterdam Schiphol to Johan Adolf Pengel takes about 9 to 10 hours."),
    ]
    faq_ld = {"@context": "https://schema.org", "@type": "FAQPage",
              "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a in faq]}
    title = "Suriname Flights Today: Live Arrivals &amp; Departures"
    desc = "Live arrivals and departures at PBM and Zorg en Hoop (EAX): delays, landing times, a pickup helper, check-in times and each airline&#8217;s on-time record."
    ld = [{"@context": "https://schema.org", "@type": "WebPage", "name": "Suriname Flights Today: Live Arrivals & Departures",
           "url": f"{SITE}/flights", "description": html.unescape(desc),
           "dateModified": F._sr(now).strftime("%Y-%m-%d"),
           "about": {"@type": "Place", "name": "Suriname", "addressCountry": "SR"},
           "isPartOf": {"@type": "WebSite", "name": "Explore Suriname", "url": SITE + "/"}},
          faq_ld, _bc(SITE, [("Home", SITE + "/"), ("Flights", SITE + "/flights")])] + _airport_ld()
    head = _head(ctx, html.unescape(title), desc, "flights.html", ld)

    hero = _hero("Flights", "Suriname Flights Today",
                 "Live arrivals and departures at Johan Adolf Pengel (PBM) and Zorg en Hoop (EAX), with delays, pickup times and on-time records.")

    bar = ('<div class="fl-bar">'
           '<div class="fl-seg" data-seg="ap" role="group" aria-label="Airport">'
           '<button type="button" data-v="PBM" aria-pressed="true"><span translate="no">PBM</span> <span class="n" translate="no">Zanderij</span></button>'
           '<button type="button" data-v="EAX" aria-pressed="false"><span translate="no">EAX</span> <span class="n" translate="no">Zorg en Hoop</span></button></div>'
           '<div class="fl-seg" data-seg="d" role="group" aria-label="Direction">'
           '<button type="button" data-v="A" aria-pressed="true"><span>Arrivals</span><span class="n" translate="no"></span></button>'
           '<button type="button" data-v="D" aria-pressed="false"><span>Departures</span><span class="n" translate="no"></span></button></div>'
           f'<label class="fl-q">{IC_SEARCH}<input id="fl-q" type="search" placeholder="Flight, airline or city" data-l10n-placeholder="{_PH}" aria-label="Search flights" autocomplete="off"></label>'
           '<label class="fl-cg"><input type="checkbox" id="fl-cg"> <span>Cargo</span></label>'
           '</div>')
    board = f'<section class="fl-card fl-board" id="fl-board" data-sec="board">{_board_html(boards, now)}</section>'
    src = ('<p class="fl-src">All times are Suriname time (UTC&minus;3). Flight data: Flightradar24 schedules, plus the airlines&#8217; own '
           'data where available: Air France-KLM Open Data for KLM, Copa and Surinam Airways flights, and Caribbean Airlines for its flights. '
           'The board refreshes every two minutes. For information only: always confirm with your airline. '
           '<a href="https://www.flightradar24.com/airport/pbm/arrivals" target="_blank" rel="noopener">Track planes on Flightradar24</a>.</p>')

    # on-time section
    rows = []
    for (ap, al), a in sorted(agg.items(), key=lambda kv: (kv[0][0], -kv[1]["n"])):
        if a["n"] < 5:
            continue
        p = round(100 * a["ok"] / a["n"])
        rows.append(f'<tr><td translate="no">{esc(al)}</td><td class="hs" translate="no">{ap}</td><td class="num" translate="no">{a["n"]}</td>'
                    f'<td class="num" translate="no">{p}%<span class="fl-bar-ot" style="width:{max(4, p // 3)}px"></span></td>'
                    f'<td class="num" translate="no">{round(a["dl"] / a["n"])} min</td><td class="num hs" translate="no">{a["canc"]}</td></tr>')
    since_txt = F._sr(hist_since).strftime("%Y-%m-%d")
    if rows:
        ot = ('<table class="fl-tbl"><thead><tr><th>Airline</th><th class="hs">Airport</th><th class="num">Flights</th><th class="num">On time</th>'
              '<th class="num">Avg delay</th><th class="num hs">Cancelled</th></tr></thead><tbody>' + "".join(rows) + '</tbody></table>'
              '<p class="fl-src">Last 30 days, passenger flights with a recorded take-off or landing time. On time means within 15 minutes of '
              'the schedule (departures by take-off time, arrivals by landing time). Average delay counts early flights as zero.</p>')
    else:
        ot = ('<p class="fl-h2s">We record every flight at PBM and EAX since <span translate="no" data-srdate="' + since_txt + '">'
              + since_txt + '</span>. The on-time table appears here once each airline has at least five recorded flights.</p>')
    ontime = ('<section class="fl-card fl-sec" id="on-time" data-sec="ontime"><h2 class="fl-h2">On-time record</h2>'
              '<p class="fl-h2s">How punctual each airline has been at Suriname&#8217;s airports.</p>' + ot + '</section>')

    # destinations
    dc = []
    for x in dests:
        fns = sorted(x["fns"])
        links = " ".join(
            (f'<a href="{F.slug_of(fn)}.html" translate="no">{esc(fn)}</a>' if F.slug_of(fn) in F.PAGE_SLUGS else f'<span translate="no">{esc(fn)}</span>')
            for fn in fns)
        meta = []
        if x.get("per_week"):
            meta.append(f'<span translate="no">{x["per_week"]}&#215;</span> <span>per week</span>')
        if x.get("dur"):
            meta.append(_dur_span(x["dur"]))
        dc.append(f'<div class="fl-dc"><h3 translate="no">{esc(x["city"])}<small>{esc(x["iata"])}</small></h3>'
                  f'<p translate="no">{esc(", ".join(sorted(x["airlines"])))}</p>'
                  + (f'<p>{" &#183; ".join(meta)}</p>' if meta else '') + f'<p>{links}</p></div>')
    dest_html = ('<section class="fl-card fl-sec" id="destinations" data-sec="dest"><h2 class="fl-h2">Where you can fly direct</h2>'
                 '<p class="fl-h2s">Passenger routes from Johan Adolf Pengel seen in the last four weeks.</p>'
                 f'<div class="fl-dest">{"".join(dc)}</div></section>') if dc else ""

    # airport guide (facts from japi-airport.com and the site's own pages)
    phones = []
    for code in ("PY", "KL", "CM", "BW", "8W", "G3"):
        a = F.AIRLINES[code]
        lk = f'<a href="/listing/{a["listing"]}/" translate="no">{esc(a["name"])}</a>' if a.get("listing") else f'<span translate="no">{esc(a["name"])}</span>'
        phones.append(f'<li>{lk}: <span translate="no">{esc(a["phone"])}</span></li>')
    guide = ('<section class="fl-card fl-sec" id="airport-guide" data-sec="guide"><h2 class="fl-h2">Airport guide</h2>'
             '<p class="fl-h2s">The practical bits for flying in and out of Suriname.</p><div class="fl-guide">'
             '<div><h3>Check-in at PBM</h3><p>Flights to Amsterdam: check-in opens 5 hours and closes 2 hours before departure. '
             'All regional flights: opens 3 hours and closes 2 hours before departure. Source: Johan Adolf Pengel Airport.</p></div>'
             '<div><h3>Getting to the airport</h3><p>Johan Adolf Pengel is about 45 km south of Paramaribo, usually a 45 to 60 minute drive. '
             'Ride-hailing apps do not operate at the airport: book a taxi or shuttle, or rent a car. '
             '<a href="/services?sub=travel-transport">Taxis, shuttles and transport</a>.</p></div>'
             '<div><h3>Arriving in Suriname</h3><p>Most visitors arrange an e-visa or tourist card and pay the entry fee online before they fly. '
             '<a href="/visitor-resources">Arrival, visa and money tips</a> &#183; <a href="/currency">Exchange rates</a> &#183; '
             '<a href="/atms">ATMs</a>.</p></div>'
             '<div><h3>Parking at PBM</h3><p>The airport offers overnight Park &amp; Fly in covered garage boxes and a secured area. '
             'Reserve through Commercial Affairs, NV Luchthavenbeheer: <span translate="no">+597 325113</span>.</p></div>'
             '<div><h3>Airline phone numbers</h3><ul>' + "".join(phones) + '</ul>'
             '<p>As listed by the airport. For bookings and rebooking, contact the airline.</p></div>'
             '<div><h3 translate="no">Zorg en Hoop (EAX)</h3><p>Paramaribo&#8217;s city airport for domestic flights, interior charters and short hops to '
             'Georgetown (Ogle) with Gum Air and Trans Guyana Airways.</p></div>'
             '</div></section>')

    faq_html = ('<section class="fl-card fl-sec fl-faq" id="faq"><h2 class="fl-h2">Questions</h2>'
                + "".join(f'<details><summary>{esc(q)}</summary>'
                          + (f'<p translate="no" data-l10n="{faq_l10n[i]}">{esc(a)}</p>' if i in faq_l10n else f'<p>{esc(a)}</p>')
                          + '</details>' for i, (q, a) in enumerate(faq)) + '</section>')

    cfg = _cfg({"mode": "board"})
    body = ('\n<body class="overflow-x-hidden">\n' + ctx["nav_html"]("flights") + hero
            + '<main class="fl-main"><div class="fl-next" id="fl-next" hidden></div>' + bar + board + src
            + ontime + dest_html + guide + faq_html + '</main>'
            + _scripts(_live_payload(c), cfg) + ctx["footer_html"]() + '\n</body>\n</html>')
    return head + body


# ── one page per flight ──────────────────────────────────────────────────────

def _route_text(legs, lang):
    """legs: list of (d, ap, on) sorted. PBM/EAX side = Paramaribo."""
    parts = []
    for d, ap, on in legs:
        a, b = (_city(on, lang), PMB[lang]) if d == "A" else (PMB[lang], _city(on, lang))
        parts.append(_l("route", lang, a=a, b=b))
    return L10N["and"][lang].join(parts)


def build_flight_page(ctx, c, fn):
    SITE = ctx["SITE_URL"]
    now = c["now"]
    groups = c["groups"]
    keys = sorted([k for k in groups if k[0] == fn], key=lambda k: (k[1] != "D", k[2]))
    if not keys:
        return None
    legs = []
    for k in keys:
        L = groups[k]
        last = [r for r in L if r["s"] <= now + 3 * 86400][-1] if any(r["s"] <= now + 3 * 86400 for r in L) else L[-1]
        legs.append({"key": k, "d": k[1], "ap": k[2], "on": last.get("on") or last.get("oi") or "", "oi": last.get("oi") or "",
                     "al": last.get("al") or "", "ai": last.get("ai") or "", "hist": L,
                     "pat": F.schedule_pattern(L, now), "stats": F.flight_stats(L, now)})
    al = next((l["al"] for l in legs if l["al"]), fn[:2])
    ai = next((l["ai"] for l in legs if l["ai"]), "")
    alinfo = F.airline_info(ai, ai, al)
    slug = F.slug_of(fn)
    rt = [(l["d"], l["ap"], l["on"]) for l in legs]
    route_en = _route_text(rt, "en")
    title = _l("title", "en", fn=fn, route=route_en)
    desc = _l("desc", "en", fn=fn, route=route_en, al=al)
    title_l = _l10n_attr(lambda lg: _l("title", lg, fn=fn, route=_route_text(rt, lg)) + " | Explore Suriname")
    desc_l = _l10n_attr(lambda lg: _l("desc", lg, fn=fn, route=_route_text(rt, lg), al=al))

    # FAQ from data
    faq = []
    main = legs[0]
    pat, st = main["pat"], main["stats"]
    def add(qk, ak, **kw):
        q_en = _l(qk, "en", **kw)
        a_en = _l(ak, "en", **kw)
        q_l = _l10n_attr(lambda lg: _l(qk, lg, **{**kw, **({"route": _route_text(rt, lg)} if "route" in kw else {}),
                                                     **({"days": _days_text(pat.get("wd"), lg)} if "days" in kw else {}),
                                                     **({"dur": _dur_text(pat.get("dur"), lg)} if "dur" in kw else {})}))
        a_l = _l10n_attr(lambda lg: _l(ak, lg, **{**kw, **({"route": _route_text(rt, lg)} if "route" in kw else {}),
                                                     **({"days": _days_text(pat.get("wd"), lg)} if "days" in kw else {}),
                                                     **({"dur": _dur_text(pat.get("dur"), lg)} if "dur" in kw else {})}))
        faq.append((q_en, a_en, q_l, a_l))
    add("faq_live_q", "faq_live_a", fn=fn, al=al)
    if pat.get("wd"):
        add("faq_days_q", "faq_days_a", fn=fn, route=route_en, days=_days_text(pat["wd"], "en"), t=pat.get("time", ""), al=al)
    if st.get("n", 0) >= 5:
        add("faq_ot_q", "faq_ot_a", fn=fn, d=st["days"], p=st["ontime"], n=st["n"], avg=st["avg"])
    if pat.get("dur"):
        add("faq_dur_q", "faq_dur_a", fn=fn, route=route_en, dur=_dur_text(pat["dur"], "en"))
    if pat.get("ac"):
        add("faq_ac_q", "faq_ac_a", fn=fn, ac=pat["ac"])

    ld = [{"@context": "https://schema.org", "@type": "WebPage", "name": title, "url": f"{SITE}/{slug}",
           "description": desc, "dateModified": F._sr(now).strftime("%Y-%m-%d"),
           "isPartOf": {"@type": "WebSite", "name": "Explore Suriname", "url": SITE + "/"}},
          {"@context": "https://schema.org", "@type": "FAQPage",
           "mainEntity": [{"@type": "Question", "name": q, "acceptedAnswer": {"@type": "Answer", "text": a}} for q, a, _, _ in faq]},
          _bc(SITE, [("Home", SITE + "/"), ("Flights", SITE + "/flights"), (fn, f"{SITE}/{slug}")])]
    head = _head(ctx, title, desc, slug + ".html", ld, title_l10n=title_l, desc_l10n=desc_l)

    h1_l = _l10n_attr(lambda lg: fn + " " + _route_text(rt, lg))
    hero = ('<header class="fl-hero"><div class="in">'
            '<a class="back" href="flights.html">&#8592; <span>All flights</span></a>'
            '<p class="k">Flight status</p>'
            f'<h1 translate="no" data-l10n="{h1_l}">{esc(fn)} {esc(route_en)}</h1>'
            f'<p class="sub" translate="no">{esc(al)}' + (f' &#183; {esc(", ".join(sorted({x for l in legs for x in (l["hist"][-1].get("cs") or [])})))}' if any(l["hist"][-1].get("cs") for l in legs) else '') + '</p>'
            '<p class="fl-live" id="fl-live"><span class="dot" aria-hidden="true"></span><b>Live</b></p></div></header>')

    # status cards: server snapshot (JS replaces with live data)
    stat_html = ""
    for l in legs:
        L = [r for r in c["boards"].get(l["ap"], []) if r["fn"] == fn and r["d"] == l["d"]]
        if not L:
            continue
        r = min(L, key=lambda x: abs((x.get("a") or x.get("e") or x["s"]) - now) + (10 ** 9 if x.get("st") in ("landed", "departed") and (x.get("a") or x["s"]) < now - 3 * 3600 else 0))
        stt = _shown_state(r, now)
        t = r.get("a") or r.get("e") or r["s"]
        stat_html += (f'<div class="fl-card fp-status"><div class="row"><span class="when"><span translate="no" data-l10n="{_l10n_attr(lambda lg: WD[lg][F._sr(r["s"]).weekday()] + " " + _short_date(F._sr(r["s"]), lg))}">'
                      f'{WD["en"][F._sr(r["s"]).weekday()]} {_short_date(F._sr(r["s"]), "en")}</span></span><span class="pill p-{stt}">{STATE_EN[stt]}</span></div>'
                      f'<div class="big" translate="no">{_hm(t)}' + (f'<s>{_hm(r["s"])}</s>' if abs(t - r["s"]) >= 300 else '') + '</div></div>')
    status = f'<section id="fp-status" data-sec="status">{stat_html}</section>'

    # schedule + on-time cards per leg
    cards = []
    for l in legs:
        p, s = l["pat"], l["stats"]
        dir_lbl = "Departs" if l["d"] == "D" else "Arrives"
        wd = p.get("wd") or []
        chips = "".join(f'<span class="{"on" if i in wd else ""}" data-l10n="{_l10n_attr(lambda lg, i=i: WD[lg][i])}" translate="no">{WD["en"][i]}</span>' for i in range(7))
        kv = []
        if p.get("time"):
            kv.append(f'<dt>{dir_lbl} <span translate="no">{l["ap"]}</span></dt><dd translate="no">{p["time"]}</dd>')
        hist_last = l["hist"][-1]
        other_t = hist_last.get("sa") if l["d"] == "D" else hist_last.get("sd")
        if other_t:
            oz = hist_last.get("oz")
            ot = F._sr(other_t + (oz + 10800 if oz is not None else 0)).strftime("%H:%M")
            kv.append(f'<dt>{"Arrives" if l["d"] == "D" else "Departs"} <span translate="no">{esc(l["oi"])}</span></dt><dd><span translate="no">{ot}</span> <small>' + ("local time" if oz is not None else "SR") + '</small></dd>')
        if p.get("dur"):
            kv.append(f'<dt>Flight time</dt><dd>{_dur_span(p["dur"])}</dd>')
        if p.get("ac"):
            kv.append(f'<dt>Aircraft</dt><dd translate="no">{esc(p["ac"])}</dd>')
        if p.get("per_week"):
            kv.append(f'<dt>Flights per week</dt><dd translate="no">{p["per_week"]}</dd>')
        rl = _route_text([(l["d"], l["ap"], l["on"])], "en")
        rl_l = _l10n_attr(lambda lg, l=l: _route_text([(l["d"], l["ap"], l["on"])], lg))
        cards.append('<div class="fl-card"><p class="fp-k">Schedule</p>'
                     f'<p style="margin:0 0 .5rem;font-weight:600" translate="no" data-l10n="{rl_l}">{esc(rl)}</p>'
                     f'<div class="wdc">{chips}</div><dl class="fp-kv">{"".join(kv)}</dl>'
                     '<p class="fp-note">From the flights we recorded in the last four weeks. Times in Suriname time unless marked local time.</p></div>')
        if s.get("n", 0) >= 3:
            line_l = _l10n_attr(lambda lg, s=s: _l("ontime_line", lg, p=s["ontime"], n=s["n"]))
            cards.append('<div class="fl-card"><p class="fp-k">On-time record</p>'
                         f'<p class="fp-pct"><span translate="no">{s["ontime"]}%</span><small>on time</small></p>'
                         f'<div class="fp-meter"><i style="width:{s["ontime"]}%"></i></div>'
                         f'<p class="fp-note" translate="no" data-l10n="{line_l}">{esc(_l("ontime_line", "en", p=s["ontime"], n=s["n"]))}</p>'
                         '<dl class="fp-kv" style="margin-top:.6rem">'
                         f'<dt>Average delay</dt><dd translate="no">{s["avg"]} min</dd>'
                         f'<dt>Worst delay</dt><dd translate="no">{s["worst"]} min</dd>'
                         f'<dt>Cancelled</dt><dd translate="no">{s["cancelled"]}</dd></dl></div>')
        else:
            cards.append('<div class="fl-card"><p class="fp-k">On-time record</p>'
                         '<p class="fp-note">Not enough recorded flights yet. The record fills in automatically as this flight operates.</p></div>')

    # recent flights table
    recent_rows = []
    allpast = sorted([r for l in legs for r in l["hist"] if r["s"] <= now - 1800], key=lambda r: -r["s"])[:14]
    for r in allpast:
        stt = r.get("st") or "unknown"
        if stt == "scheduled":
            stt = "unknown"
        dl = r.get("dl")
        dl_txt = ("+" + str(dl) if dl and dl > 0 else str(dl)) + " min" if dl is not None and stt in ("landed", "departed") else ""
        _dt = F._sr(r["s"])
        recent_rows.append(f'<tr><td style="white-space:nowrap"><span class="wdx" translate="no" data-l10n="{_l10n_attr(lambda lg, _dt=_dt: WD[lg][_dt.weekday()])}">{WD["en"][_dt.weekday()]}</span> '
                           f'<span translate="no" data-l10n="{_l10n_attr(lambda lg, _dt=_dt: _short_date(_dt, lg))}">{_short_date(_dt, "en")}</span></td>'
                           + (f'<td class="hs" translate="no" style="white-space:nowrap">{r["ap"]} {"&#8592;" if r["d"] == "A" else "&#8594;"} {esc(r.get("oi") or "")}</td>' if len(legs) > 1 else '') +
                           f'<td class="num" translate="no">{_hm(r["s"])}</td><td class="num" translate="no">{_hm(r.get("a")) or "&#8211;"}</td>'
                           f'<td class="num"><span class="pill p-{stt}">{STATE_EN.get(stt, "No update")}</span>' + (f'<span class="fr-sub" translate="no">{dl_txt}</span>' if dl_txt else '') + '</td></tr>')
    recent = ('<section class="fl-card fl-sec" id="recent"><h2 class="fl-h2">Recent flights</h2>'
              + ('<table class="fl-tbl"><thead><tr><th>Date</th>' + ('<th class="hs">Route</th>' if len(legs) > 1 else '') + '<th class="num">Scheduled</th><th class="num">Actual</th><th class="num">Status</th></tr></thead><tbody>'
                 + "".join(recent_rows) + '</tbody></table><p class="fl-src">Departures by take-off time, arrivals by landing time. On time means within 15 minutes of schedule.</p>'
                 if recent_rows else '<p class="fl-h2s">No completed flights recorded yet.</p>') + '</section>')

    # related flights: return flight + same route
    rel = set()
    for l in legs:
        for (fn2, d2, ap2), L2 in groups.items():
            if fn2 == fn or F.slug_of(fn2) not in F.PAGE_SLUGS:
                continue
            if L2[-1].get("oi") == l["oi"] and ap2 == l["ap"]:
                rel.add(fn2)
    rel_html = ""
    if rel:
        rel_html = ('<section class="fl-card fl-sec"><h2 class="fl-h2">Related flights</h2><div class="fp-links">'
                    + "".join(f'<a class="fbtn" href="{F.slug_of(x)}.html" translate="no">{esc(x)} &#183; {esc(groups[[k for k in groups if k[0] == x][0]][-1].get("on") or "")}</a>' for x in sorted(rel))
                    + '</div></section>')

    # airline card
    al_links = []
    if alinfo.get("listing"):
        al_links.append(f'<a class="fbtn" href="/listing/{alinfo["listing"]}/"><span translate="no">{esc(al)}</span>&nbsp;<span>on Explore Suriname</span></a>')
    if alinfo.get("site"):
        al_links.append(f'<a class="fbtn" href="{alinfo["site"]}" target="_blank" rel="noopener"><span>Airline website</span> &#8599;</a>')
    al_card = ('<section class="fl-card fl-sec"><h2 class="fl-h2" translate="no">' + esc(al) + '</h2>'
               + (f'<p class="fl-h2s"><span>Phone</span>: <span translate="no">{esc(alinfo["phone"])}</span></p>' if alinfo.get("phone") else '')
               + (f'<div class="fp-links">{"".join(al_links)}</div>' if al_links else '')
               + '<p class="fl-src">For check-in, baggage, gates and rebooking, the airline is the official source.</p></section>')

    faq_html = ('<section class="fl-card fl-sec fl-faq"><h2 class="fl-h2">Questions</h2>'
                + "".join(f'<details><summary translate="no" data-l10n="{ql}">{esc(q)}</summary><p translate="no" data-l10n="{alx}">{esc(a)}</p></details>' for q, a, ql, alx in faq)
                + '</section>')

    main_ap = legs[0]["ap"]
    cfg = _cfg({"mode": "flight", "fn": fn, "ap": main_ap})
    body = ('\n<body class="overflow-x-hidden">\n' + ctx["nav_html"]("flights") + hero
            + '<main class="fl-main"><div class="fl-next" id="fl-next" hidden></div>' + status
            + f'<div class="fp-grid">{"".join(cards)}</div>' + recent + rel_html + al_card + faq_html
            + '<p class="fl-src"><a href="flights.html">All arrivals and departures in Suriname</a></p></main>'
            + _scripts(_live_payload(c), cfg) + ctx["footer_html"]() + '\n</body>\n</html>')
    return head + body


def _stub(SITE):
    return ('<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
            '<meta name="viewport" content="width=device-width, initial-scale=1">'
            '<meta name="robots" content="noindex,follow">'
            '<meta name="esr-stub" content="/flights.html">'
            '<meta http-equiv="refresh" content="0;url=/flights.html">'
            f'<link rel="canonical" href="{SITE}/flights.html">'
            '<title>This flight no longer operates | Explore Suriname</title></head><body>'
            '<p>This flight is no longer listed. <a href="/flights.html">See all flights in Suriname</a>.</p>'
            '</body></html>')


def build_flight_pages(ctx, c, existing_files=()):
    """Returns {filename: html}. existing_files: names of flight-*.html already in
    the repo (become redirect stubs when their flight is gone)."""
    now = c["now"]
    fns = _flight_page_set(c["groups"], c["boards"], now)
    F.PAGE_SLUGS.clear()
    F.PAGE_SLUGS.update(F.slug_of(fn) for fn in fns)
    pages = {}
    for fn in sorted(fns):
        try:
            h = build_flight_page(ctx, c, fn)
            if h:
                pages[F.slug_of(fn) + ".html"] = h
        except Exception as e:
            print(f"  !! flight page {fn}: {e}")
            F.PAGE_SLUGS.discard(F.slug_of(fn))
    built = set(pages)
    for name in existing_files:
        if name not in built and name.startswith("flight-") and name.endswith(".html"):
            pages[name] = _stub(ctx["SITE_URL"])
    pages["flights.html"] = build_board(ctx, c)
    try:
        F.write_live(c)      # now with the final page list
    except Exception as e:
        print(f"  !! flights_live.json: {e}")
    return pages


# French typography: no-break space before ? : ; ! (house rule for /fr/).
def _fr_nbsp(s):
    return re.sub(r" ([?:;!])", " \\1", s)


for _k in L10N:
    if "fr" in L10N[_k]:
        L10N[_k]["fr"] = _fr_nbsp(L10N[_k]["fr"])
for _k in list(FL_I18N["fr"]):
    FL_I18N["fr"][_k] = _fr_nbsp(FL_I18N["fr"][_k])
