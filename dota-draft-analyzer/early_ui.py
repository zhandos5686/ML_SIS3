"""Minute-five workflow; totals are required, not silently invented."""
import pandas as pd
import requests
import streamlit as st
from early_features import STATS

LABELS = {'gold': 'Ценность героев — сумма net worth', 'xp': 'Полученный опыт — сумма XP',
          'lh': 'Добитые крипы — сумма last hits', 'kills': 'Убийства', 'deaths': 'Смерти',
          'level': 'Сумма уровней пяти героев', 'items': 'Купленные предметы — суммарное количество'}
MAXIMUM = {'gold': 2000000, 'xp': 2000000, 'lh': 10000, 'kills': 500, 'deaths': 500, 'level': 150, 'items': 2000}


@st.cache_data(ttl=30)
def get_metadata(api):
    response = requests.get(f'{api}/early/metadata', timeout=10)
    response.raise_for_status()
    return response.json()


def render(api):
    st.subheader('Состояние игры на 5:00')
    st.caption('Модель обучена на исторических матчах 2015 года; качество на современной мете не проверялось.')
    st.write('Введите суммарные показатели каждой команды ровно на пятой минуте. Здесь стороны известны: Radiant и Dire.')
    st.caption('Gold — общая ценность героев с предметами, а не свободное золото. Items — число покупок за первые пять минут, а не занятые слоты инвентаря. Не используйте итоговую статистику матча.')
    try:
        meta = get_metadata(api)
    except (requests.RequestException, ValueError):
        st.info('Режим пятой минуты недоступен. Запустите python train_early.py и перезапустите API.')
        return
    names = {h['id']: h['name'] for h in meta['heroes']}
    ids = sorted(names, key=names.get)
    selected_example = st.selectbox('Реальный пример из обучающей части', range(len(meta['examples'])),
                                    format_func=lambda i: f'Пример {i + 1}', key='early_example_choice')
    if st.button('Загрузить показатели примера', key='early_load'):
        example = meta['examples'][selected_example]
        for team in ['radiant', 'dire']:
            st.session_state[f'early_{team}_heroes'] = example[team]['heroes']
            for stat in STATS:
                st.session_state[f'early_{team}_{stat}'] = example[team][stat]
        st.session_state.pop('early_prediction', None)
    st.caption('Примеры взяты из Train для демонстрации ввода; качество модели проверяется на других, отложенных матчах.')
    payload = {'snapshot_seconds': 300}
    cols = st.columns(2, gap='large')
    for col, team, title in zip(cols, ['radiant', 'dire'], ['Radiant', 'Dire']):
        with col:
            st.markdown(f'### {title}')
            heroes = st.multiselect(f'Пять героев {title}', ids, format_func=names.get,
                                    max_selections=5, key=f'early_{team}_heroes')
            values = {stat: st.number_input(f'{LABELS[stat]} · {title}', min_value=0,
                max_value=MAXIMUM[stat], value=None, step=1, placeholder='Введите значение на 5:00',
                key=f'early_{team}_{stat}') for stat in STATS}
            payload[team] = {'heroes': heroes, **values}
    chosen = payload['radiant']['heroes'] + payload['dire']['heroes']
    complete = all(len(payload[t]['heroes']) == 5 and all(payload[t][s] is not None for s in STATS) for t in ['radiant', 'dire'])
    unique = len(chosen) == len(set(chosen))
    if not unique:
        st.warning('Герой повторяется в составах. Каждый герой может участвовать только один раз.')
    elif not complete:
        st.info('Выберите по пять героев и заполните все показатели или загрузите реальный пример.')
    if st.button('Оценить исход на 5:00', type='primary', disabled=not complete or not unique, key='early_predict'):
        try:
            with st.spinner('Оцениваем состояние матча…'):
                response = requests.post(f'{api}/predict/early', json=payload, timeout=30)
                response.raise_for_status()
                st.session_state['early_prediction'] = (payload, response.json())
        except (requests.RequestException, ValueError):
            st.session_state.pop('early_prediction', None)
            st.error('Не удалось получить прогноз. Проверьте API и повторите запрос.')
    saved = st.session_state.get('early_prediction')
    if saved and saved[0] == payload:
        result = saved[1]
        st.divider()
        st.subheader('Вероятность победы после пяти минут')
        left, right = st.columns(2)
        left.metric('Radiant', f"{result['radiant_probability']:.1%}")
        right.metric('Dire', f"{result['dire_probability']:.1%}")
        st.caption(f"{result['note']} Модель {result['model_name']}, версия {result['model_version']}.")
    elif saved:
        st.info('Показатели изменились. Повторите расчёт, чтобы обновить прогноз.')
    with st.expander('Насколько помогают первые пять минут'):
        st.caption('Обе модели обучены на одном наборе 2015 года и проверены на одинаковых отложенных матчах. Сравнение с прежними 60.37% на UCI 2016 напрямую некорректно.')
        st.dataframe(pd.DataFrame({'Только герои': meta['draft_test_metrics'], 'Герои + 5 минут': meta['test_metrics']}).round(4), use_container_width=True)
        st.write(f"Обучение с валидацией: {meta['train_rows']:,} матчей; итоговый тест: {meta['test_rows']:,}.")
        st.caption('Матчи разделены по предоставленному времени начала. В исходном задании время слегка изменено для анонимизации; это порядок по опубликованным меткам времени.')
    with st.expander('Источники и ограничения'):
        st.markdown('[Исходное описание и срез 300 секунд](https://github.com/romovpa/kaggle-dota2-contest) · [Публичное зеркало CSV](https://github.com/nikkuper/coursera-dota-2) · данные YASP, CC BY-SA 4.0.')
        st.write('Это другой набор исторических матчей. Статистика не присоединялась к UCI по случайному порядку строк. Длительность и итоговое состояние башен и бараков исключены. Прогноз относится к матчам, которые продолжаются на пятой минуте; исходная выборка содержит матчи длительностью не менее 15 минут.')
