"""Собирает страницу кейса index.html из report/case.md и расчётов scripts/model.py.

Места для инфографики отмечены в тексте комментариями <!-- fig:имя -->.
Запуск:  .venv/bin/python scripts/build_page.py
"""

import base64
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import model  # noqa: E402

MD = ROOT / "report" / "case.md"
OUT = ROOT / "index.html"
REPO = "https://github.com/massimo-pazzi/fastfood-assistant-case"


def esc(t):
    return str(t).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def num(x):
    return f"{x:,.0f}".replace(",", " ")


def figure(title, body, note=""):
    n = f'<p class="note">{note}</p>' if note else ""
    return f'<figure class="chart"><figcaption class="chart-title">{title}</figcaption>{body}{n}</figure>'


def table(head, rows, cls=""):
    return (f'<div class="table-wrap"><table class="{cls}"><thead><tr>' + "".join(f"<th>{h}</th>" for h in head) +
            "</tr></thead><tbody>" + "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows) +
            "</tbody></table></div>")


def link(text, url):
    return f'<a href="{url}" target="_blank" rel="noopener">{text}</a>'


# ---------------------------------------------------------------- инфографика

def fig_summary():
    steps = [("Гость в приложении", "пишет вопрос на своём языке в разделе поддержки"),
             ("ИИ-ассистент", "определяет язык и тему, берёт заказы и баллы гостя из CRM"),
             ("Ответ", "статус заказа, баллы, состав блюда, ближайший ресторан, возврат"),
             ("Оператор", "сложные случаи — с историей диалога и переводом на русский")]
    html = '<div class="flow">' + "".join(
        (f'<div class="arrow" aria-hidden="true">→</div>' if i else "") +
        f'<div class="flow-col{" core" if i == 1 else ""}"><div class="flow-h">{esc(h)}</div><p>{esc(t)}</p></div>'
        for i, (h, t) in enumerate(steps)) + "</div>"
    return figure("Что предлагалось: ассистент в приложении между гостем и контакт-центром", html)


def fig_sources():
    rows = [("Открытые жалобы, отзывы и FAQ сетей быстрого питания", "Темы обращений и их примерная частота, типовые формулировки",
             "Это оценка по отзывам, а не статистика контакт-центра"),
            ("Отзывы гостей и сотрудников о самом заказчике", "Местная специфика: неполные заказы, возвраты, акции, скорость поддержки",
             "Отдельные отзывы, а не репрезентативная выборка"),
            ("Решения конкурентов", "Что уже сделано на рынке и где технология ломается", "Компании почти не раскрывают эффект")]
    return figure("Три источника вместо данных заказчика", table(["Источник", "Что даёт", "Ограничение"], rows))


def fig_topics():
    mx = 40
    html = '<div class="ranges">'
    for name, lo, hi, _, _ in model.TOPICS:
        lab = f"{lo}–{hi}%" if lo != hi else f"{lo}%"
        if lo == 0:
            lab = f"до {hi}%"
        html += (f'<div class="rg"><div class="rg-l">{esc(name)}</div><div class="rg-bar">'
                 f'<div class="rg-lo" style="width:{lo / mx * 100:.1f}%"></div>'
                 f'<div class="rg-hi" style="width:{(hi - lo) / mx * 100:.1f}%"></div>'
                 f'<span>{lab}</span></div></div>')
    html += ('</div><div class="legend"><span><i class="sw s1"></i>нижняя граница оценки</span>'
             '<span><i class="sw s1l"></i>разброс оценки</span></div>')
    top = model.TOPICS[:3]
    return figure("Темы обращений гостей и их доля в потоке, оценка", html,
                  f"Оценка для предложения по открытым жалобам, отзывам и FAQ сетей быстрого питания; "
                  f"публичной статистики контакт-центров сети не раскрывают. Три верхние темы — "
                  f"{sum(t[1] for t in top)}–{sum(t[2] for t in top)}% потока. Данные — data/topics.csv.")


def fig_boundaries():
    cols = [("Отвечает сам", ["Статус и состав заказа, история последних заказов", "Баллы, списания и действующие акции",
                              "Состав блюд, калорийность, аллергены", "Ближайший ресторан и часы работы",
                              "Возврат или довоз при неполном заказе", "Рекомендации по истории заказов"]),
            ("Передаёт оператору", ["Жалобы на качество еды и обслуживание", "Чистота и гигиена в ресторане",
                                    "Спорные возвраты и компенсации", "Всё, что не распознал уверенно"]),
            ("Не делает", ["Не оформляет заказы и не принимает оплату", "Не сообщает о готовности заказа — это делает приложение",
                           "Не показывает данные других пользователей", "Не отвечает на темы вне сервиса"])]
    html = '<div class="cols3">' + "".join(
        f'<div class="c3{" core" if i == 0 else ""}"><div class="flow-h">{esc(h)}</div><ul>' +
        "".join(f"<li>{esc(x)}</li>" for x in items) + "</ul></div>" for i, (h, items) in enumerate(cols)) + "</div>"
    return figure("Границы продукта", html)


def fig_tree():
    b, v, t = model.scenarios()
    tiles = "".join(
        f'<div class="tile"><div class="tile-n">{1 + var}</div><div class="tile-h">{esc(name)}</div>'
        f'<div class="tile-s">{"1 базовый" + (f" + {var} вариаций" if var else "")}</div>'
        f'<div class="tile-e">{esc(ex)}</div></div>'
        for name, _, _, var, ex in model.TOPICS)
    return figure(f"Дерево сценариев: {b} базовых и {v} вариаций — всего {t}", f'<div class="tiles">{tiles}</div>',
                  "Мультиязычность не добавляет сценариев: меняется язык диалога, а не его ветки.")


def fig_load():
    L = model.load()
    rows = [("Обращений в день, верхняя граница", num(model.DIALOGS_PER_DAY_MAX), "оценка по установкам приложения"),
            ("Сообщений гостя в одном обращении", f"{model.STEPS[0]}–{model.STEPS[1]}", "вопрос, ответ, уточнение, передача оператору"),
            ("Сообщений в день", f"≈ {L['msgs_day'] / 1e6:.2f} млн".replace(".", ","), "при 5 сообщениях в обращении"),
            ("Сообщений в секунду, в среднем", f"≈ {L['avg_msgs_s']:.0f}", f"нагрузка распределена на {model.ACTIVE_HOURS} часов"),
            ("Новых обращений в секунду, в пик", num(model.PEAK_DIALOGS_PER_SEC), "обед, вечер, выходные"),
            ("<strong>Сообщений в минуту, в пик</strong>", f"<strong>≈ {num(L['peak_msgs_min'])}</strong>", "по этой цифре делается сайзинг серверов")]
    return figure("От обращений к сообщениям: какую нагрузку должен держать ассистент",
                  table(["Показатель", "Значение", "Откуда"], rows, "num txtlast"),
                  "Данных об активной аудитории заказчик не предоставил, поэтому нагрузка оценена сверху. Расчёт — scripts/model.py.")


COMP = [
    ("McDonald's", "ИИ-бот Olivia для найма персонала на платформе McHire. Ассистента для гостей в приложении нет",
     "Июнь–июль 2025: исследователи нашли тестовый доступ с паролем «123456» к данным до 64 млн кандидатов",
     "https://ian.sh/mcdonalds"),
    ("McDonald's и IBM", "Голосовой приём заказа в окне для автомобилистов, около 100 ресторанов в США",
     "Тест с 2021 года закрыт в июне 2024-го; точность — около 80% при цели 95% (оценка BTIG)",
     "https://www.nrn.com/quick-service/mcdonald-s-is-ending-its-ai-drive-thru-test-with-ibm"),
    ("Burger King", "Бот в Facebook Messenger: заказ из меню, ближайший ресторан, оплата",
     "Запущен в 2016 году", "https://fortune.com/2016/05/18/burger-king-bot/"),
    ("Burger King, Новая Зеландия", "ИИ-приём заказа в окне для автомобилистов, ассистент Patty",
     "Тест с марта 2024 года в 4 ресторанах Окленда; к июлю 2026-го — 40 ресторанов",
     "https://thespinoff.co.nz/kai/21-07-2026/just-useless-what-its-like-working-with-burger-kings-ai-assistant"),
    ("Burger King, США", "Patty — голосовой помощник в гарнитурах сотрудников: рецептуры, стоп-лист, разбор диалогов",
     "Объявлен в феврале 2026 года, пилот в 500 ресторанах",
     "https://www.nrn.com/quick-service/burger-king-is-launching-an-ai-powered-employee-assistant"),
    ("Taco Bell, KFC, Pizza Hut", "Голосовой ИИ в окне для автомобилистов вместе с NVIDIA",
     "500 ресторанов во втором квартале 2025 года; в августе 2025-го Taco Bell признал проблемы — "
     "например, троллинг заказом 18 000 стаканов воды",
     "https://techcrunch.com/2025/08/30/taco-bell-is-having-second-thoughts-about-relying-on-ai-at-the-drive-through/"),
    ("KFC, Тайвань", "Цифровой человек Kala на экранах в ресторанах: меню, вопросы, помощь с заказом",
     "Апрель 2024 года, более 70 ресторанов",
     "https://www.prnewswire.com/apac/news-releases/pantheon-lab-powers-kfc-taiwans-revolutionary-ai-intern-kala-302112715.html"),
    ("KFC и Baidu, Китай", "«Умные рестораны»: голосовой робот-ассистент, распознавание лиц и подсказка заказа",
     "Пилоты 2016 года", "https://www.nasdaq.com/articles/baidu-bidu-and-kfc-team-up-for-smart-restaurant-in-china-2016-12-29"),
]


def fig_competitors():
    rows = [(f"<strong>{esc(n)}</strong>", esc(w), f"{esc(r)} {link('↗', u)}") for n, w, r, u in COMP]
    return figure("ИИ в крупных сетях быстрого питания", table(["Сеть", "Что сделали", "Когда и чем закончилось"], rows))


def fig_metrics():
    rows = [("Доля обращений, закрытых без оператора", "Закрытые ассистентом обращения ко всем обращениям",
             "Главный эффект для контакт-центра"),
            ("Доля передач оператору по темам", "Передачи к обращениям — отдельно по каждой теме", "Показывает, каких сценариев не хватает"),
            ("Оценка гостя после диалога", "Короткий опрос в конце диалога", "Не даёт выдать «отфутболивание» за успех"),
            ("Повторные обращения по той же теме", "Гость вернулся с тем же вопросом в течение недели",
             "Проблема решена по-настоящему, а не формально"),
            ("Точность темы и языка", "Ручная разметка выборки диалогов", "Качество модели"),
            ("Обращения в контакт-центр по темам ассистента", "До и после запуска, по тем же темам",
             "Проверка гипотезы о снижении на 30–50%")]
    return figure("Как проверить, что ассистент работает", table(["Метрика", "Как считается", "Зачем"], rows))


def fig_refs():
    items = [f"{esc(n)}: {link(u.split('/')[2], u)}" for n, _, _, u in COMP]
    items.append("Видение продукта и коммерческое предложение (не публикуются): требования заказчика, функциональность, "
                 "сценарии, оценка нагрузки, сроки")
    return ('<ol class="sources">' + "".join(f"<li>{i}</li>" for i in items) + "</ol>"
            f'<p class="note">Расчёты и данные для графиков — {link("scripts/model.py", REPO + "/blob/main/scripts/model.py")} '
            f'и {link("data/", REPO + "/tree/main/data")}.</p>')


def author_block():
    img = base64.b64encode((ROOT / "assets/img/author.jpg").read_bytes()).decode()
    return (f'<div class="author"><img src="data:image/jpeg;base64,{img}" alt="Максим Поципух" width="64" height="64">'
            '<span>Максим Поципух</span></div>')


FIGS = {"summary": fig_summary, "sources": fig_sources, "topics": fig_topics, "boundaries": fig_boundaries,
        "tree": fig_tree, "load": fig_load, "competitors": fig_competitors, "metrics": fig_metrics, "refs": fig_refs}

CSS = """
:root{
  --bg:#f5f6f7; --surface:#ffffff; --ink:#18202a; --ink-2:#4b5662; --muted:#6c7782;
  --rule:#d9dee3; --accent:#1f5fae; --accent-soft:#e6eef8; --neutral:#aab2bb;
  --s1:#2a78d6; --s2:#eb6834; --s3:#1baf7a; --s4:#a07800; --ok:#1b8a5a; --warn:#a36b00; --no:#8a929b;
}
@media (prefers-color-scheme: dark){
  :root:not([data-theme="light"]){ color-scheme:dark;
    --bg:#11161c; --surface:#171d24; --ink:#e7ebef; --ink-2:#b5bec7; --muted:#8c96a0;
    --rule:#2c343d; --accent:#79a9e8; --accent-soft:#1c2632; --neutral:#5d6670;
    --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --ok:#3fbf86; --warn:#e0a640; --no:#7d8791; }
}
:root[data-theme="dark"]{ color-scheme:dark;
  --bg:#11161c; --surface:#171d24; --ink:#e7ebef; --ink-2:#b5bec7; --muted:#8c96a0;
  --rule:#2c343d; --accent:#79a9e8; --accent-soft:#1c2632; --neutral:#5d6670;
  --s1:#3987e5; --s2:#d95926; --s3:#199e70; --s4:#c98500; --ok:#3fbf86; --warn:#e0a640; --no:#7d8791; }
body{margin:0; background:var(--bg); color:var(--ink); font-family:"Golos Text",system-ui,-apple-system,"Segoe UI",sans-serif;
  font-size:17px; line-height:1.62; padding-inline:16px; padding-block:40px 64px;}
.page{max-width:48rem; margin:0 auto;} a{color:var(--accent);}
.eyebrow{font-family:"IBM Plex Mono",ui-monospace,monospace; font-size:12.5px; letter-spacing:.06em; text-transform:uppercase; color:var(--accent); margin:0 0 14px;}
h1{font-size:clamp(1.7rem,4.2vw,2.3rem); line-height:1.18; font-weight:700; letter-spacing:-.01em; text-wrap:balance; margin:0 0 16px;}
h2{font-size:1.28rem; line-height:1.3; font-weight:650; text-wrap:balance; margin:46px 0 12px; padding-top:22px; border-top:1px solid var(--rule);}
.author{display:flex; align-items:center; gap:12px; margin:4px 0 16px; font-weight:600; font-size:15px;}
.author img{width:64px; height:64px; border-radius:50%; object-fit:cover; border:1px solid var(--rule);}
.author + p em{color:var(--ink-2); font-size:15px;}
p{margin:0 0 14px;} strong{font-weight:620;} hr{display:none;}
.chart{margin:16px 0 22px; background:var(--surface); border:1px solid var(--rule); border-radius:6px; padding:14px 16px 12px;}
.chart-title{font-weight:600; font-size:14.5px; margin-bottom:10px; line-height:1.4;}
.note{font-size:12.5px; color:var(--muted); margin:10px 0 0; line-height:1.5;}
.flow{display:grid; grid-template-columns:1fr auto 1fr auto 1fr auto 1fr; gap:8px; align-items:stretch;}
.flow-col{border:1px solid var(--rule); border-radius:6px; padding:10px 12px; font-size:13px; line-height:1.45;} .flow-col p{margin:0;}
.flow-h{font-weight:650; font-size:12.5px; text-transform:uppercase; letter-spacing:.04em; color:var(--ink-2); margin-bottom:6px;}
.flow-col.core{background:var(--accent-soft); border-color:var(--accent);} .flow-col.core .flow-h{color:var(--accent);}
.arrow{align-self:center; color:var(--muted); font-size:20px;}
@media (max-width:700px){ .flow{grid-template-columns:1fr;} .arrow{transform:rotate(90deg); justify-self:center;} }
.funnel{display:grid; gap:8px;}
.fn-row{display:grid; grid-template-columns:1fr 1fr; gap:12px; align-items:center;}
.fn-bar{box-sizing:border-box; max-width:100%; background:var(--s1); color:#fff; border-radius:4px; padding:7px 10px; font-weight:600; font-size:14px; min-width:9em; justify-self:end;}
.fn-row:last-child .fn-bar{background:var(--s2);}
.fn-l{font-size:13.5px; line-height:1.35;} .fn-l span{display:block; color:var(--muted); font-size:12.5px;}
.table-wrap{overflow-x:auto;}
table{border-collapse:collapse; width:100%; font-size:14px;}
th,td{text-align:left; padding:8px 10px 8px 0; border-bottom:1px solid var(--rule); vertical-align:top;}
th{font-weight:600; color:var(--ink-2); font-size:12.5px;}
.matrix td:first-child{font-weight:550; min-width:11em;} .matrix th:last-child,.matrix td:last-child{background:var(--accent-soft); padding-left:8px;}
.price td:last-child{text-align:right; font-variant-numeric:tabular-nums; white-space:nowrap;}
.y{color:var(--ok); font-weight:600;} .p{color:var(--warn); font-weight:600;} .n{color:var(--no);}
.steps{margin:0; padding-left:1.4em; columns:2; column-gap:28px; font-size:14px;} .steps li{margin-bottom:6px; break-inside:avoid;}
@media (max-width:640px){ .steps{columns:1;} }
.pairs{display:grid; gap:12px;}
.pair{display:grid; grid-template-columns:minmax(9em,13em) 1fr; gap:12px; align-items:center; font-size:13.5px;}
.pr-l span{display:block; color:var(--muted); font-size:12px;}
.pr-bars{display:grid; gap:4px;}
.pb{display:flex; align-items:center; gap:8px; font-size:12.5px; font-variant-numeric:tabular-nums;} .pb span{white-space:nowrap;}
.bar{height:14px; border-radius:3px; min-width:3px;} .bar.s1{background:var(--s1);} .bar.s2{background:var(--s2);}
.legend{display:flex; flex-wrap:wrap; gap:6px 16px; font-size:12.5px; color:var(--ink-2); margin-top:12px;}
.legend span{display:inline-flex; align-items:center; gap:6px;} .sw{display:inline-block; width:11px; height:11px; border-radius:2px;}
.sw.s1{background:var(--s1);} .sw.s2{background:var(--s2);}
.chart-scroll{overflow-x:auto;} .chart svg{display:block; width:100%; min-width:560px; height:auto;}
.grid{stroke:var(--rule); stroke-width:1;} .tick{fill:var(--muted); font-size:11px; font-family:"IBM Plex Mono",ui-monospace,monospace;}
.target{stroke:var(--ink-2); stroke-width:1.2; stroke-dasharray:5 4;} .median{stroke:var(--muted); stroke-width:1; stroke-dasharray:2 3;}
.band-label{fill:var(--muted); font-size:11px;} .label{fill:var(--ink); font-size:12px;}
.line{fill:none; stroke-width:2.2;} .line.s1{stroke:var(--s1);} .line.s2{stroke:var(--s2);} .line.s3{stroke:var(--s3);} .line.s4{stroke:var(--s4);}
.dot{stroke:var(--surface); stroke-width:2;} .dot.s1{fill:var(--s1);} .dot.s2{fill:var(--s2);} .dot.s3{fill:var(--s3);} .dot.s4{fill:var(--s4);}
.kpis{display:grid; grid-template-columns:repeat(auto-fit,minmax(150px,1fr)); gap:10px; margin-bottom:12px;}
.kpi{border:1px solid var(--rule); border-radius:6px; padding:12px 14px;}
.kpi-v{font-size:1.4rem; font-weight:700; font-variant-numeric:tabular-nums;} .kpi-l{font-size:13px; color:var(--ink-2); margin-top:4px; line-height:1.4;}
.num td:not(:first-child),.num th:not(:first-child){text-align:right; font-variant-numeric:tabular-nums;}
.txtlast td:last-child,.txtlast th:last-child{text-align:left;}
.dl-link{margin:-12px 0 22px; font-size:13.5px;}
.chart.live iframe{display:block; width:100%; border:0; border-radius:4px; background:#fff;}
.sources{font-size:14.5px; line-height:1.55; padding-left:1.5em;}
@media (max-width:520px){ body{font-size:16px; padding-block:24px 48px;} .pair,.fn-row{grid-template-columns:1fr;} .fn-bar{justify-self:start;} }
.ranges{display:grid; gap:7px;}
.rg{display:grid; grid-template-columns:minmax(10em,16em) 1fr; gap:12px; align-items:center; font-size:13.5px;}
.rg-bar{display:flex; align-items:center; gap:0; font-size:12.5px; font-variant-numeric:tabular-nums;}
.rg-lo{height:14px; background:var(--s1); border-radius:3px 0 0 3px;} .rg-hi{height:14px; background:var(--s1); opacity:.35; border-radius:0 3px 3px 0;}
.rg-bar span{margin-left:8px; white-space:nowrap;} .sw.s1l{background:var(--s1); opacity:.35;}
.cols3{display:grid; grid-template-columns:repeat(3,1fr); gap:10px;}
.c3{border:1px solid var(--rule); border-radius:6px; padding:10px 12px; font-size:13.5px; line-height:1.45;}
.c3 ul{margin:0; padding-left:1.1em;} .c3 li{margin-bottom:4px;}
.c3.core{background:var(--accent-soft); border-color:var(--accent);} .c3.core .flow-h{color:var(--accent);}
.tiles{display:grid; grid-template-columns:repeat(auto-fill,minmax(200px,1fr)); gap:10px;}
.tile{border:1px solid var(--rule); border-radius:6px; padding:10px 12px; font-size:13px; line-height:1.4;}
.tile-n{font-size:1.5rem; font-weight:700; color:var(--accent); font-variant-numeric:tabular-nums;}
.tile-h{font-weight:620; margin:2px 0;} .tile-s{color:var(--ink-2); font-size:12.5px;} .tile-e{color:var(--muted); font-size:12px; margin-top:4px;}
.num td:not(:first-child),.num th:not(:first-child){text-align:right; font-variant-numeric:tabular-nums;}
.txtlast td:last-child,.txtlast th:last-child{text-align:left;}
@media (max-width:640px){ .cols3{grid-template-columns:1fr;} .rg{grid-template-columns:1fr; gap:4px;} }
"""


def main():
    html = markdown.markdown(MD.read_text(encoding="utf-8"), extensions=["tables"])
    title, rest = html.split("</h1>", 1)
    html = title + "</h1>\n" + author_block() + rest
    for name, fn in FIGS.items():
        marker = f"<!-- fig:{name} -->"
        assert marker in html, f"нет места для блока {name}"
        html = html.replace(marker, fn())
    page = f"""<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>ИИ-ассистент без данных</title>
<meta name="description" content="Портфолио-кейс менеджера продукта с ИИ: как спроектировать ИИ-ассистента для приложения сети быстрого питания, когда заказчик не дал ни сценариев, ни статистики обращений">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Golos+Text:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap">
<style>{CSS}</style>
</head>
<body>
<main class="page">
<p class="eyebrow">Портфолио-кейс: продукт с ИИ · Максим Поципух · Сентябрь 2025</p>
{html}
</main>
</body>
</html>
"""
    OUT.write_text(page, encoding="utf-8")
    print(f"{OUT.relative_to(ROOT)}: {len(page) // 1024} КБ, блоков: {len(FIGS)}")


if __name__ == "__main__":
    main()
