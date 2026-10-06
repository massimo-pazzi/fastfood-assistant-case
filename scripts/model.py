"""Данные и расчёты кейса: темы обращений, очерёдность релизов, нагрузка, экономика.

Публичных данных о причинах обращений в контакт-центр не публикует ни одна крупная сеть
быстрого питания, а заказчик статистику не предоставил. Поэтому доли тем — оценка по
открытым жалобам, отзывам и FAQ сетей быстрого питания, сделанная для предложения.
Всё, что помечено «допущение», — оценка автора кейса, которую проверяет пилот.

Объёмы обращений из предложения уменьшены на 30% по соображениям конфиденциальности,
цена проекта — округлена. Результат — CSV в data/. Запуск:  python3 scripts/model.py
"""

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data"

# --- Темы обращений ------------------------------------------------------------------
# доля в потоке, % (от, до); вариаций в полном дереве предложения; релиз; вариаций после
# приоритизации; доля обращений темы, которую ассистент закрывает без оператора (допущение).
# Релиз 0 — тема без ветвления: один сценарий, который отвечает ссылкой или передаёт оператору.
TOPICS = [
    ("Статус и проблемы с заказом", 30, 40, 7, 1, 7, 0.7,
     "Где мой заказ, неполный заказ (возврат или довоз), не мой заказ, изменить, отменить, вернуть деньги"),
    ("Качество еды и обслуживания", 20, 25, 5, 1, 5, 0.2,
     "Холодная, слишком горячая, ошибка в составе, посторонний предмет, испорченная еда"),
    ("Программа лояльности и акции", 15, 15, 5, 1, 5, 0.7,
     "Баллы, активация акции, список акций, нет товара по акции, отказ в акции"),
    ("Меню и состав блюд", 10, 10, 7, 2, 7, 0.7,
     "Состав, калорийность, замена и добавка ингредиентов, что есть в меню, где купить, время завтраков"),
    ("Рестораны и часы работы", 8, 8, 6, 2, 6, 0.8,
     "Ближайший ресторан, часы работы, наличие позиции"),
    ("Доставка и оплата", 7, 7, 0, 2, 5, 0.5,
     "Статус доставки, задержка, оплата не прошла, двойное списание, возврат за отмену"),
    ("Технические проблемы с приложением", 5, 5, 6, 0, 0, 0.0,
     "Передача в поддержку приложения"),
    ("Чистота и гигиена", 3, 3, 6, 0, 0, 0.0,
     "Жалоба на ресторан — передача оператору"),
    ("Корпоративные вопросы", 2, 2, 6, 0, 0, 0.0,
     "Работа в сети, корпоративные заказы — ссылка"),
    ("Другое", 0, 5, 6, 0, 0, 0.0,
     "Франчайзинг, спонсорство, забытые вещи — передача оператору"),
]


def mid(t):
    return (t[1] + t[2]) / 2


def scenarios_full():
    base, variants = len(TOPICS), sum(t[3] for t in TOPICS)
    return base, variants, base + variants


def scenarios_by_release():
    out = {}
    for t in TOPICS:
        out[t[4]] = out.get(t[4], 0) + 1 + t[5]
    return out


def release_share(release):
    """Доля потока (по серединам оценок) в темах релиза, %."""
    return sum(mid(t) for t in TOPICS if t[4] == release) / sum(mid(t) for t in TOPICS) * 100


def containment(release_max):
    """Доля всего потока, закрытая без оператора, когда выпущены релизы 1..release_max, %."""
    total = sum(mid(t) for t in TOPICS)
    return sum(mid(t) * t[6] for t in TOPICS if 1 <= t[4] <= release_max) / total * 100


# --- Нагрузка ------------------------------------------------------------------------
STEPS = (4, 6)                  # сообщений гостя в одном обращении
ACTIVE_HOURS = 16               # часы основной нагрузки в сутки
CONF = 0.7                      # объёмы предложения уменьшены на 30% (конфиденциальность)

# Предельный сценарий — оценка предложения сверху, по установкам приложения.
LIMIT_DIALOGS_DAY = 750_000 * CONF
LIMIT_PEAK_DIALOGS_S = 50 * CONF

# Базовый сценарий — воронка от проблемного заказа (все доли — допущения).
GUESTS_DAY = 2_000_000          # порядок числа гостей в день у федеральной сети
APP_ORDER_SHARE = 0.20          # доля заказов через приложение
PROBLEM_SHARE = 0.03            # доля проблемных заказов (ориентир 2–5%)
CONTACT_SHARE = 0.50            # доля гостей с проблемным заказом, которые обращаются
PROBLEM_TOPICS = 0.60           # доля обращений, вызванных проблемой с заказом (по темам)
PEAK_FACTOR = 4                 # пиковый час к среднему (обед, вечер)
PROMO_MARGIN = 3                # запас на промо-кампании


def funnel():
    app_orders = GUESTS_DAY * APP_ORDER_SHARE
    problems = app_orders * PROBLEM_SHARE
    contacts = problems * CONTACT_SHARE
    dialogs = contacts / PROBLEM_TOPICS
    return {"app_orders": app_orders, "problems": problems, "contacts": contacts, "dialogs": dialogs}


def sizing(dialogs_day, peak_dialogs_s=None, margin=1):
    steps = sum(STEPS) / 2
    avg = dialogs_day / (ACTIVE_HOURS * 3600)
    peak = peak_dialogs_s if peak_dialogs_s is not None else avg * PEAK_FACTOR
    return {"dialogs_day": dialogs_day, "msgs_day": dialogs_day * steps, "avg_dialogs_s": avg,
            "peak_dialogs_s": peak, "peak_msgs_min": peak * steps * 60 * margin}


def base_sizing():
    return sizing(funnel()["dialogs"], margin=PROMO_MARGIN)


def limit_sizing():
    return sizing(LIMIT_DIALOGS_DAY, LIMIT_PEAK_DIALOGS_S)


# --- Экономика -----------------------------------------------------------------------
PRICE = 8_000_000               # цена проекта, округлена (без эксплуатации и сопровождения)
COST_PER_DIALOG = 66            # ₽ за диалог чата на аутсорсинге: Kolocall, сверх пакета


def threshold_dialogs_day(months=12):
    """Сколько обращений в день ассистент должен закрывать без оператора, чтобы окупиться за months."""
    return PRICE / (COST_PER_DIALOG * 365 * months / 12)


def savings_year(dialogs_day, containment_pct):
    return dialogs_day * containment_pct / 100 * COST_PER_DIALOG * 365


def write(name, rows):
    DATA.mkdir(exist_ok=True)
    with open(DATA / name, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"data/{name}: {len(rows)} строк")


def main():
    names = {1: "Релиз 1", 2: "Релиз 2", 0: "Без ветвления"}
    write("topics.csv", [{"Тема обращения": t[0], "Доля в потоке от, %": t[1], "Доля в потоке до, %": t[2],
                          "Вариаций в полном дереве": t[3], "Релиз": names[t[4]], "Вариаций после приоритизации": t[5],
                          "Закрывается без оператора (допущение), %": round(t[6] * 100), "Примеры": t[7]}
                         for t in TOPICS])
    f, b, lim = funnel(), base_sizing(), limit_sizing()
    write("load.csv", [{"Сценарий": n, "Обращений в день": round(s["dialogs_day"]), "Сообщений в день": round(s["msgs_day"]),
                        "Обращений в секунду в пик": round(s["peak_dialogs_s"], 2),
                        "Сообщений в минуту в пик для сайзинга": round(s["peak_msgs_min"])}
                       for n, s in (("Базовый, с запасом на промо", b), ("Предельный", lim))])
    c1, c2 = containment(1), containment(2)
    th = threshold_dialogs_day()
    write("economics.csv", [
        {"Показатель": "Цена проекта, ₽", "Значение": PRICE},
        {"Показатель": "Стоимость диалога оператора на аутсорсинге, ₽", "Значение": COST_PER_DIALOG},
        {"Показатель": "Порог окупаемости за год, обращений в день без оператора", "Значение": round(th)},
        {"Показатель": "Обращений в день, базовый сценарий", "Значение": round(f["dialogs"])},
        {"Показатель": "Закрыто без оператора после релиза 1, % потока", "Значение": round(c1, 1)},
        {"Показатель": "Экономия в год после релиза 1, ₽", "Значение": round(savings_year(f["dialogs"], c1))},
        {"Показатель": "Закрыто без оператора после релиза 2, % потока", "Значение": round(c2, 1)},
    ])
    print("сценарии полного дерева:", scenarios_full(), "по релизам:", scenarios_by_release())
    print(f"доля потока: релиз 1 {release_share(1):.0f}%, релиз 2 {release_share(2):.0f}%, без ветвления {release_share(0):.0f}%")
    print(f"закрыто без оператора: после р1 {c1:.1f}%, после р2 {c2:.1f}%")
    print("воронка:", {k: round(v) for k, v in f.items()})
    print("базовый:", {k: round(v, 2) for k, v in b.items()})
    print("предельный:", {k: round(v, 2) for k, v in lim.items()})
    print(f"порог: {th:.0f} обращений/день = {th / f['dialogs'] * 100:.1f}% базового потока; "
          f"экономия р1 {savings_year(f['dialogs'], c1) / 1e6:.1f} млн ₽/год, окупаемость "
          f"{PRICE / savings_year(f['dialogs'], c1) * 12:.1f} мес.")


if __name__ == "__main__":
    main()
