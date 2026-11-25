"""Streamlit client. All inference requests go through FastAPI."""
import os
import pandas as pd
import requests
import streamlit as st

API = os.getenv('API_URL', 'http://127.0.0.1:8000').rstrip('/')
st.set_page_config(page_title='Dota Match Analyzer', layout='wide')
st.title('Dota Match Analyzer')
st.caption('Прогноз до матча и на пятой минуте. Два режима обучены на разных исторических наборах данных.')


@st.cache_data(ttl=30)
def metadata():
    response = requests.get(f'{API}/metadata', timeout=10)
    response.raise_for_status()
    return response.json()


try:
    meta = metadata()
except (requests.RequestException, ValueError):
    st.error('Не удалось подключиться к модели. Запустите обучение и API, затем повторите подключение.')
    if st.button('Повторить подключение'):
        st.cache_data.clear()
        st.rerun()
    st.stop()

hero_names = {h['id']: h['name'] for h in meta['heroes']}
ids = sorted(hero_names, key=hero_names.get)
early_tab, draft_tab, quality_tab, about_tab = st.tabs(['На пятой минуте', 'До матча', 'Качество драфта', 'О проекте'])

with early_tab:
    from early_ui import render
    render(API)

with draft_tab:
    st.write('Выберите по пять уникальных героев. Команда A соответствует значению +1 в исходных данных, команда B — значению −1.')
    example_a, example_b = [1, 2, 3, 4, 5], [6, 7, 8, 9, 10]
    if st.button('Загрузить пример'):
        for team, example in [('a', example_a), ('b', example_b)]:
            for i, value in enumerate(example):
                st.session_state[f'{team}_{i}'] = value
        st.session_state.pop('prediction', None)
    a_col, b_col = st.columns(2, gap='large')
    teams = []
    for col, key, title, example in [(a_col, 'a', 'Команда A', example_a), (b_col, 'b', 'Команда B', example_b)]:
        with col:
            st.subheader(title)
            teams.append([st.selectbox(f'Герой {i+1}', ids, index=ids.index(example[i]),
                                       format_func=hero_names.get, key=f'{key}_{i}') for i in range(5)])
    with st.expander('Контекст матча'):
        st.caption('Сохранены исходные коды датасета: без неподтверждённой привязки к современным названиям режимов.')
        game_mode = st.selectbox('Режим игры — код', meta['game_modes'], index=meta['game_modes'].index(2))
        game_type = st.selectbox('Тип игры — код', meta['game_types'], index=meta['game_types'].index(2))
    valid = len(set(teams[0] + teams[1])) == 10
    if not valid:
        st.warning('Один герой выбран несколько раз. Для прогноза нужны 10 разных героев.')
    payload = {'team_a': teams[0], 'team_b': teams[1], 'game_mode': game_mode, 'game_type': game_type}
    if st.button('Оценить составы', type='primary', disabled=not valid):
        try:
            with st.spinner('Сравниваем составы…'):
                response = requests.post(f'{API}/predict', json=payload, timeout=30)
                response.raise_for_status()
                st.session_state['prediction'] = (payload, response.json())
        except (requests.RequestException, ValueError):
            st.session_state.pop('prediction', None)
            st.error('Прогноз недоступен. Проверьте API и повторите запрос.')
    saved = st.session_state.get('prediction')
    if saved and saved[0] == payload:
        result = saved[1]
        st.divider()
        st.subheader('Оценка модели')
        left, right = st.columns(2)
        left.metric('Вероятность победы A', f"{result['team_a_probability']:.1%}")
        right.metric('Вероятность победы B', f"{result['team_b_probability']:.1%}")
        st.caption('Это оценка вероятности, а не гарантия. Навыки игроков, линии, предметы и ход матча в данных отсутствуют.')
        st.caption(f"Модель: {result['model_name']} · Версия {result['model_version']}")
    elif saved:
        st.info('Состав изменён. Нажмите «Оценить составы», чтобы обновить результат.')

with quality_tab:
    st.subheader('Проверка на отложенных матчах')
    st.write(f"Обучающая выборка: {meta['train_rows']:,} · Тестовая: {meta['test_rows']:,}")
    st.caption('Модель выбрана по ROC AUC на валидации внутри Train. Официальный Test используется для итоговой оценки.')
    st.dataframe(pd.DataFrame(meta['validation']).set_index('model').round(4), use_container_width=True)
    st.write('Итоговые метрики выбранной модели и простой baseline:')
    st.dataframe(pd.DataFrame({'Модель': meta['test_metrics'], 'Baseline': meta['baseline_test_metrics']}).round(4), use_container_width=True)
    st.write('Матрица ошибок: строки — реальный класс, столбцы — прогноз.')
    st.dataframe(pd.DataFrame(meta['confusion_matrix'], index=['Победа B', 'Победа A'], columns=['Прогноз B', 'Прогноз A']), use_container_width=True)

with about_tab:
    st.subheader('От драфта к прогнозу')
    st.write('Streamlit → FastAPI → сохранённая модель scikit-learn. Обучение и регистрация версий выполняются через MLflow.')
    st.write('Два независимых режима: прогноз до матча на UCI 2016 и прогноз на пятой минуте на YASP/Coursera 2015. Их исходные строки не объединяются.')
    st.write(meta['note'])
    st.markdown('[Источник: UCI Dota2 Games Results](https://archive.ics.uci.edu/dataset/367/dota2+games+results) · CC BY 4.0 · Stephen Tridgell, 2016')
    st.caption('Используем обозначения A/B: описание UCI определяет стороны как +1/−1 без явного подтверждения Radiant/Dire.')
