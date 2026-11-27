"""Streamlit client. All inference requests go through FastAPI."""
import os
import pandas as pd
import requests
import streamlit as st
from i18n import language_selector, t

API = os.getenv('API_URL', 'http://127.0.0.1:8000').rstrip('/')
st.set_page_config(page_title='Dota Match Analyzer', layout='wide')
title_col, lang_col = st.columns([5, 1], vertical_alignment='bottom')
with lang_col:
    language_selector()
title_col.title('Dota Match Analyzer')
st.caption(t('subtitle'))


@st.cache_data(ttl=30)
def metadata():
    response = requests.get(f'{API}/metadata', timeout=10)
    response.raise_for_status()
    return response.json()


try:
    meta = metadata()
except (requests.RequestException, ValueError):
    st.error(t('api_down'))
    if st.button(t('retry')):
        st.cache_data.clear()
        st.rerun()
    st.stop()

hero_names = {h['id']: h['name'] for h in meta['heroes']}
ids = sorted(hero_names, key=hero_names.get)
# A keyed radio instead of st.tabs: st.tabs jumps back to the first tab after every button press.
PAGES = ['early', 'draft', 'advisor', 'quality', 'about']
st.session_state.setdefault('page', 'early')
page = st.radio('Section', PAGES, format_func=lambda p: t('tab_' + p), horizontal=True,
                label_visibility='collapsed', key='page')
st.divider()

if page == 'early':
    from early_ui import render
    render(API)

if page == 'draft':
    st.write(t('draft_intro'))
    example_a, example_b = [1, 2, 3, 4, 5], [6, 7, 8, 9, 10]
    if st.button(t('load_example')):
        for team, example in [('a', example_a), ('b', example_b)]:
            for i, value in enumerate(example):
                st.session_state[f'{team}_{i}'] = value
        st.session_state.pop('prediction', None)
    # Defaults live in session state (not index=) so values survive a language switch without warnings.
    for team, example in [('a', example_a), ('b', example_b)]:
        for i, value in enumerate(example):
            st.session_state.setdefault(f'{team}_{i}', value)
    st.session_state.setdefault('game_mode', 2)
    st.session_state.setdefault('game_type', 2)
    a_col, b_col = st.columns(2, gap='large')
    teams = []
    for col, key, title in [(a_col, 'a', t('team_a')), (b_col, 'b', t('team_b'))]:
        with col:
            st.subheader(title)
            teams.append([st.selectbox(t('hero_n', n=i + 1), ids, format_func=hero_names.get, key=f'{key}_{i}') for i in range(5)])
    with st.expander(t('match_context')):
        st.caption(t('context_note'))
        game_mode = st.selectbox(t('game_mode'), meta['game_modes'], key='game_mode')
        game_type = st.selectbox(t('game_type'), meta['game_types'], key='game_type')
    valid = len(set(teams[0] + teams[1])) == 10
    if not valid:
        st.warning(t('duplicate_draft'))
    payload = {'team_a': teams[0], 'team_b': teams[1], 'game_mode': game_mode, 'game_type': game_type}
    if st.button(t('predict_draft'), type='primary', disabled=not valid):
        try:
            with st.spinner(t('spinner_draft')):
                response = requests.post(f'{API}/predict', json=payload, timeout=30)
                response.raise_for_status()
                st.session_state['prediction'] = (payload, response.json())
        except (requests.RequestException, ValueError):
            st.session_state.pop('prediction', None)
            st.error(t('predict_failed'))
    saved = st.session_state.get('prediction')
    if saved and saved[0] == payload:
        result = saved[1]
        st.divider()
        st.subheader(t('model_estimate'))
        left, right = st.columns(2)
        left.metric(t('win_a'), f"{result['team_a_probability']:.1%}")
        right.metric(t('win_b'), f"{result['team_b_probability']:.1%}")
        st.caption(t('draft_disclaimer'))
        st.caption(t('model_version', name=result['model_name'], version=result['model_version']))
    elif saved:
        st.info(t('draft_changed'))

if page == 'advisor':
    from advisor_ui import render as render_advisor
    render_advisor(API, hero_names, ids, st.session_state.get('game_mode', 2), st.session_state.get('game_type', 2))

if page == 'quality':
    st.subheader(t('quality_title'))
    st.write(t('rows', train=meta['train_rows'], test=meta['test_rows']))
    st.caption(t('selection_note'))
    st.dataframe(pd.DataFrame(meta['validation']).set_index('model').round(4), use_container_width=True)
    st.write(t('final_metrics'))
    st.dataframe(pd.DataFrame({t('col_model'): meta['test_metrics'], 'Baseline': meta['baseline_test_metrics']}).round(4), use_container_width=True)
    st.write(t('confusion'))
    st.dataframe(pd.DataFrame(meta['confusion_matrix'], index=[t('true_b'), t('true_a')], columns=[t('pred_b'), t('pred_a')]), use_container_width=True)

if page == 'about':
    st.subheader(t('about_title'))
    st.write(t('about_arch'))
    st.write(t('about_modes'))
    st.write(t('historical_note'))
    st.markdown(t('about_source'))
    st.caption(t('about_sides'))
