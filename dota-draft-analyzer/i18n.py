"""UI strings in English (default) and Russian. Use t('key', **format_args)."""
import streamlit as st

LANGUAGES = {'en': 'English', 'ru': 'Русский'}
DEFAULT = 'en'

TEXT = {
    # Page
    'language': {'en': 'Language', 'ru': 'Язык'},
    'subtitle': {'en': 'Win probability before the match and at minute five. The two modes are trained on different historical datasets.',
                 'ru': 'Прогноз до матча и на пятой минуте. Два режима обучены на разных исторических наборах данных.'},
    'api_down': {'en': 'Cannot connect to the model. Train the models and start the API, then retry.',
                 'ru': 'Не удалось подключиться к модели. Запустите обучение и API, затем повторите подключение.'},
    'retry': {'en': 'Retry connection', 'ru': 'Повторить подключение'},
    'tab_early': {'en': 'At minute five', 'ru': 'На пятой минуте'},
    'tab_draft': {'en': 'Before the match', 'ru': 'До матча'},
    'tab_quality': {'en': 'Draft model quality', 'ru': 'Качество драфта'},
    'tab_about': {'en': 'About', 'ru': 'О проекте'},

    # Draft tab
    'draft_intro': {'en': 'Pick five unique heroes per team. Team A is the +1 side in the source data, team B is the −1 side.',
                    'ru': 'Выберите по пять уникальных героев. Команда A соответствует значению +1 в исходных данных, команда B — значению −1.'},
    'load_example': {'en': 'Load example', 'ru': 'Загрузить пример'},
    'team_a': {'en': 'Team A', 'ru': 'Команда A'},
    'team_b': {'en': 'Team B', 'ru': 'Команда B'},
    'hero_n': {'en': 'Hero {n}', 'ru': 'Герой {n}'},
    'match_context': {'en': 'Match context', 'ru': 'Контекст матча'},
    'context_note': {'en': 'Original dataset codes are kept: no unconfirmed mapping to modern game mode names.',
                     'ru': 'Сохранены исходные коды датасета: без неподтверждённой привязки к современным названиям режимов.'},
    'game_mode': {'en': 'Game mode — code', 'ru': 'Режим игры — код'},
    'game_type': {'en': 'Game type — code', 'ru': 'Тип игры — код'},
    'duplicate_draft': {'en': 'A hero is selected more than once. The prediction needs 10 different heroes.',
                        'ru': 'Один герой выбран несколько раз. Для прогноза нужны 10 разных героев.'},
    'predict_draft': {'en': 'Evaluate drafts', 'ru': 'Оценить составы'},
    'spinner_draft': {'en': 'Comparing drafts…', 'ru': 'Сравниваем составы…'},
    'predict_failed': {'en': 'Prediction unavailable. Check the API and try again.',
                       'ru': 'Прогноз недоступен. Проверьте API и повторите запрос.'},
    'model_estimate': {'en': 'Model estimate', 'ru': 'Оценка модели'},
    'win_a': {'en': 'Team A win probability', 'ru': 'Вероятность победы A'},
    'win_b': {'en': 'Team B win probability', 'ru': 'Вероятность победы B'},
    'draft_disclaimer': {'en': 'This is a probability estimate, not a guarantee. Player skill, lanes, items and match events are not in the data.',
                         'ru': 'Это оценка вероятности, а не гарантия. Навыки игроков, линии, предметы и ход матча в данных отсутствуют.'},
    'model_version': {'en': 'Model: {name} · Version {version}', 'ru': 'Модель: {name} · Версия {version}'},
    'draft_changed': {'en': 'The draft has changed. Press “Evaluate drafts” to update the result.',
                      'ru': 'Состав изменён. Нажмите «Оценить составы», чтобы обновить результат.'},
    'historical_note': {'en': 'Data from 13 August 2016. The estimate does not reflect the current meta and does not guarantee the outcome.',
                        'ru': 'Данные от 13 августа 2016 года. Оценка не отражает современную мету и не гарантирует исход матча.'},

    # Pick advisor tab
    'tab_advisor': {'en': 'Pick advisor', 'ru': 'Советник пиков'},
    'adv_intro': {'en': 'Enter the heroes picked so far (any number, even none) and choose the team that picks next. The draft model scores every free hero for that team.',
                  'ru': 'Укажите уже выбранных героев (любое количество, можно ни одного) и команду, которая пикает следующей. Модель драфта оценит каждого свободного героя для этой команды.'},
    'adv_picked': {'en': '{team} — picked so far', 'ru': '{team} — уже выбраны'},
    'adv_side': {'en': 'Who picks next?', 'ru': 'Кто пикает следующим?'},
    'adv_example': {'en': 'Load example draft', 'ru': 'Загрузить пример драфта'},
    'adv_clear': {'en': 'Clear', 'ru': 'Очистить'},
    'adv_full': {'en': 'This team already has five heroes. Choose the other team or remove a hero.',
                 'ru': 'У этой команды уже пять героев. Выберите другую команду или уберите героя.'},
    'adv_duplicate': {'en': 'A hero is picked by both teams. Each hero can be picked only once.',
                      'ru': 'Герой выбран обеими командами. Каждого героя можно выбрать только один раз.'},
    'adv_button': {'en': 'Suggest picks', 'ru': 'Подобрать героя'},
    'adv_spinner': {'en': 'Scoring every free hero…', 'ru': 'Оцениваем всех свободных героев…'},
    'adv_failed': {'en': 'Recommendations unavailable. Check the API and try again.',
                   'ru': 'Рекомендации недоступны. Проверьте API и повторите запрос.'},
    'adv_title': {'en': 'Best next picks for {team}', 'ru': 'Лучшие следующие пики: {team}'},
    'adv_random': {'en': 'Win chance if the next pick were random: {p:.1%}', 'ru': 'Шанс победы при случайном следующем пике: {p:.1%}'},
    'adv_exact': {'en': 'This pick completes the draft, so the estimate is exact.',
                  'ru': 'Этот пик завершает драфт, поэтому оценка точная.'},
    'adv_sampled': {'en': 'Empty slots are filled with random free heroes {n} times and the results are averaged (Monte Carlo).',
                    'ru': 'Пустые слоты {n} раз заполняются случайными свободными героями, результаты усредняются (метод Монте-Карло).'},
    'adv_col_hero': {'en': 'Hero', 'ru': 'Герой'},
    'adv_col_win': {'en': 'Win chance', 'ru': 'Шанс победы'},
    'adv_col_gain': {'en': 'vs random pick', 'ru': 'vs случайный пик'},
    'adv_col_why': {'en': 'Why (model weights)', 'ru': 'Почему (веса модели)'},
    'adv_pick': {'en': 'Pick', 'ru': 'Взять'},
    'adv_strength': {'en': 'strong hero {v:+.2f}', 'ru': 'сильный герой {v:+.2f}'},
    'adv_weak': {'en': 'hero on its own {v:+.2f}', 'ru': 'герой сам по себе {v:+.2f}'},
    'adv_ally': {'en': 'with {name} {v:+.2f}', 'ru': 'с {name} {v:+.2f}'},
    'adv_opponent': {'en': 'vs {name} {v:+.2f}', 'ru': 'против {name} {v:+.2f}'},
    'adv_note': {'en': 'Weights are log-odds from the logistic regression: positive values raise the chance of the picking team. The model learned from 2016 matches, so this is the model’s opinion, not advice for the current meta. Differences of 1–2 points are within noise.',
                 'ru': 'Веса — логарифм шансов из логистической регрессии: положительные значения повышают шанс команды, которая пикает. Модель обучена на матчах 2016 года, поэтому это мнение модели, а не совет для современной меты. Разница в 1–2 пункта — в пределах шума.'},

    # Quality tab
    'quality_title': {'en': 'Evaluation on held-out matches', 'ru': 'Проверка на отложенных матчах'},
    'rows': {'en': 'Training set: {train:,} · Test set: {test:,}', 'ru': 'Обучающая выборка: {train:,} · Тестовая: {test:,}'},
    'selection_note': {'en': 'The model is selected by validation ROC AUC inside Train. The official Test set is used only for the final evaluation.',
                       'ru': 'Модель выбрана по ROC AUC на валидации внутри Train. Официальный Test используется для итоговой оценки.'},
    'final_metrics': {'en': 'Final metrics of the selected model and a simple baseline:',
                      'ru': 'Итоговые метрики выбранной модели и простой baseline:'},
    'col_model': {'en': 'Model', 'ru': 'Модель'},
    'confusion': {'en': 'Confusion matrix: rows are the true class, columns are the prediction.',
                  'ru': 'Матрица ошибок: строки — реальный класс, столбцы — прогноз.'},
    'true_b': {'en': 'B won', 'ru': 'Победа B'},
    'true_a': {'en': 'A won', 'ru': 'Победа A'},
    'pred_b': {'en': 'Predicted B', 'ru': 'Прогноз B'},
    'pred_a': {'en': 'Predicted A', 'ru': 'Прогноз A'},

    # About tab
    'about_title': {'en': 'From draft to prediction', 'ru': 'От драфта к прогнозу'},
    'about_arch': {'en': 'Streamlit → FastAPI → saved scikit-learn model. Training and model versioning are done with MLflow.',
                   'ru': 'Streamlit → FastAPI → сохранённая модель scikit-learn. Обучение и регистрация версий выполняются через MLflow.'},
    'about_modes': {'en': 'Two independent modes: pre-match prediction on UCI 2016 and minute-five prediction on YASP/Coursera 2015. Their rows are never merged.',
                    'ru': 'Два независимых режима: прогноз до матча на UCI 2016 и прогноз на пятой минуте на YASP/Coursera 2015. Их исходные строки не объединяются.'},
    'about_source': {'en': '[Source: UCI Dota2 Games Results](https://archive.ics.uci.edu/dataset/367/dota2+games+results) · CC BY 4.0 · Stephen Tridgell, 2016',
                     'ru': '[Источник: UCI Dota2 Games Results](https://archive.ics.uci.edu/dataset/367/dota2+games+results) · CC BY 4.0 · Stephen Tridgell, 2016'},
    'about_sides': {'en': 'We use A/B labels: the UCI description defines sides as +1/−1 without confirming Radiant/Dire.',
                    'ru': 'Используем обозначения A/B: описание UCI определяет стороны как +1/−1 без явного подтверждения Radiant/Dire.'},

    # Minute-five tab
    'stat_gold': {'en': 'Hero value — total net worth', 'ru': 'Ценность героев — сумма net worth'},
    'stat_xp': {'en': 'Experience — total XP', 'ru': 'Полученный опыт — сумма XP'},
    'stat_lh': {'en': 'Creeps killed — total last hits', 'ru': 'Добитые крипы — сумма last hits'},
    'stat_kills': {'en': 'Kills', 'ru': 'Убийства'},
    'stat_deaths': {'en': 'Deaths', 'ru': 'Смерти'},
    'stat_level': {'en': 'Sum of the five heroes’ levels', 'ru': 'Сумма уровней пяти героев'},
    'stat_items': {'en': 'Items bought — total count', 'ru': 'Купленные предметы — суммарное количество'},
    'early_title': {'en': 'Game state at 5:00', 'ru': 'Состояние игры на 5:00'},
    'early_age': {'en': 'Trained on historical matches from 2015; quality on the current meta has not been checked.',
                  'ru': 'Модель обучена на исторических матчах 2015 года; качество на современной мете не проверялось.'},
    'early_intro': {'en': 'Enter each team’s totals exactly at minute five. Here the sides are known: Radiant and Dire.',
                    'ru': 'Введите суммарные показатели каждой команды ровно на пятой минуте. Здесь стороны известны: Radiant и Dire.'},
    'early_fields': {'en': 'Gold is the total value of heroes with items, not unspent gold. Items is the number of purchases in the first five minutes, not occupied inventory slots. Do not use end-of-match statistics.',
                     'ru': 'Gold — общая ценность героев с предметами, а не свободное золото. Items — число покупок за первые пять минут, а не занятые слоты инвентаря. Не используйте итоговую статистику матча.'},
    'early_unavailable': {'en': 'Minute-five mode is unavailable. Run python train_early.py and restart the API.',
                          'ru': 'Режим пятой минуты недоступен. Запустите python train_early.py и перезапустите API.'},
    'example_select': {'en': 'Real example from the training split', 'ru': 'Реальный пример из обучающей части'},
    'example_n': {'en': 'Example {n}', 'ru': 'Пример {n}'},
    'load_stats': {'en': 'Load example stats', 'ru': 'Загрузить показатели примера'},
    'example_note': {'en': 'Examples come from Train to demonstrate the input; model quality is measured on other, held-out matches.',
                     'ru': 'Примеры взяты из Train для демонстрации ввода; качество модели проверяется на других, отложенных матчах.'},
    'five_heroes': {'en': 'Five {team} heroes', 'ru': 'Пять героев {team}'},
    'value_placeholder': {'en': 'Value at 5:00', 'ru': 'Введите значение на 5:00'},
    'duplicate_early': {'en': 'A hero appears in both lineups. Each hero can be picked only once.',
                        'ru': 'Герой повторяется в составах. Каждый герой может участвовать только один раз.'},
    'incomplete_early': {'en': 'Pick five heroes per team and fill in every stat, or load a real example.',
                         'ru': 'Выберите по пять героев и заполните все показатели или загрузите реальный пример.'},
    'predict_early': {'en': 'Estimate outcome at 5:00', 'ru': 'Оценить исход на 5:00'},
    'spinner_early': {'en': 'Evaluating the game state…', 'ru': 'Оцениваем состояние матча…'},
    'early_failed': {'en': 'Could not get a prediction. Check the API and try again.',
                     'ru': 'Не удалось получить прогноз. Проверьте API и повторите запрос.'},
    'early_result': {'en': 'Win probability after five minutes', 'ru': 'Вероятность победы после пяти минут'},
    'early_note': {'en': 'Prediction at 5:00 based on historical matches from 2015. All stats must refer to the first five minutes only.',
                   'ru': 'Прогноз на отметке 5:00 по историческим матчам 2015 года. Все показатели должны относиться только к первым пяти минутам.'},
    'early_model': {'en': 'Model {name}, version {version}.', 'ru': 'Модель {name}, версия {version}.'},
    'early_changed': {'en': 'The stats have changed. Run the estimate again to update the prediction.',
                      'ru': 'Показатели изменились. Повторите расчёт, чтобы обновить прогноз.'},
    'early_gain_title': {'en': 'How much the first five minutes help', 'ru': 'Насколько помогают первые пять минут'},
    'early_gain_note': {'en': 'Both models are trained on the same 2015 dataset and tested on the same held-out matches. Comparing with the earlier 60.37% on UCI 2016 directly is not valid.',
                        'ru': 'Обе модели обучены на одном наборе 2015 года и проверены на одинаковых отложенных матчах. Сравнение с прежними 60.37% на UCI 2016 напрямую некорректно.'},
    'col_heroes_only': {'en': 'Heroes only', 'ru': 'Только герои'},
    'col_heroes_5min': {'en': 'Heroes + 5 minutes', 'ru': 'Герои + 5 минут'},
    'early_rows': {'en': 'Training with validation: {train:,} matches; final test: {test:,}.',
                   'ru': 'Обучение с валидацией: {train:,} матчей; итоговый тест: {test:,}.'},
    'early_split': {'en': 'Matches are split by the provided start time. In the original task the times are slightly shifted for anonymisation, so this is the order of the published timestamps.',
                    'ru': 'Матчи разделены по предоставленному времени начала. В исходном задании время слегка изменено для анонимизации; это порядок по опубликованным меткам времени.'},
    'sources_title': {'en': 'Sources and limitations', 'ru': 'Источники и ограничения'},
    'sources_links': {'en': '[Original description and the 300-second cut](https://github.com/romovpa/kaggle-dota2-contest) · [Public CSV mirror](https://github.com/nikkuper/coursera-dota-2) · YASP data, CC BY-SA 4.0.',
                      'ru': '[Исходное описание и срез 300 секунд](https://github.com/romovpa/kaggle-dota2-contest) · [Публичное зеркало CSV](https://github.com/nikkuper/coursera-dota-2) · данные YASP, CC BY-SA 4.0.'},
    'sources_text': {'en': 'This is a different set of historical matches. Its stats were not joined to UCI by row order. Duration and final tower and barracks states are excluded. The prediction applies to matches still running at minute five; the source sample contains matches lasting at least 15 minutes.',
                     'ru': 'Это другой набор исторических матчей. Статистика не присоединялась к UCI по случайному порядку строк. Длительность и итоговое состояние башен и бараков исключены. Прогноз относится к матчам, которые продолжаются на пятой минуте; исходная выборка содержит матчи длительностью не менее 15 минут.'},
}


def language():
    return st.session_state.get('lang', DEFAULT)


def t(key, **kwargs):
    text = TEXT[key].get(language(), TEXT[key][DEFAULT])
    return text.format(**kwargs) if kwargs else text


FORM_KEYS = ('a_', 'b_', 'game_mode', 'game_type', 'early_radiant_', 'early_dire_', 'early_example_choice',
             'adv_a', 'adv_b', 'adv_side', 'page')
BUTTON_SUFFIXES = ('_btn', '_go')


def keep_form_state():
    """Translated labels give widgets a new identity, which would reset their values.
    Re-assigning input values each run keeps heroes and stats when the language changes.
    Buttons are skipped: Streamlit does not allow setting their state."""
    for key in list(st.session_state.keys()):
        if key.startswith(FORM_KEYS) and not key.endswith(BUTTON_SUFFIXES) and not key.startswith('adv_pick_'):
            st.session_state[key] = st.session_state[key]


def language_selector(container=st):
    """Language picker; English by default, ?lang=ru in the URL opens Russian."""
    if 'lang' not in st.session_state:
        requested = st.query_params.get('lang', DEFAULT)
        st.session_state['lang'] = requested if requested in LANGUAGES else DEFAULT
    keep_form_state()
    # Constant label: the widget keeps its identity when the language changes.
    container.selectbox('Language / Язык', list(LANGUAGES), format_func=LANGUAGES.get, key='lang')
