"""Minute-five workflow; totals are required, not silently invented."""
import pandas as pd
import requests
import streamlit as st
from early_features import STATS
from i18n import t

MAXIMUM = {'gold': 2000000, 'xp': 2000000, 'lh': 10000, 'kills': 500, 'deaths': 500, 'level': 150, 'items': 2000}


@st.cache_data(ttl=30)
def get_metadata(api):
    response = requests.get(f'{api}/early/metadata', timeout=10)
    response.raise_for_status()
    return response.json()


def render(api):
    st.subheader(t('early_title'))
    st.caption(t('early_age'))
    st.write(t('early_intro'))
    st.caption(t('early_fields'))
    try:
        meta = get_metadata(api)
    except (requests.RequestException, ValueError):
        st.info(t('early_unavailable'))
        return
    names = {h['id']: h['name'] for h in meta['heroes']}
    ids = sorted(names, key=names.get)
    selected_example = st.selectbox(t('example_select'), range(len(meta['examples'])),
                                    format_func=lambda i: t('example_n', n=i + 1), key='early_example_choice')
    if st.button(t('load_stats'), key='early_load'):
        example = meta['examples'][selected_example]
        for team in ['radiant', 'dire']:
            st.session_state[f'early_{team}_heroes'] = example[team]['heroes']
            for stat in STATS:
                st.session_state[f'early_{team}_{stat}'] = example[team][stat]
        st.session_state.pop('early_prediction', None)
    st.caption(t('example_note'))
    payload = {'snapshot_seconds': 300}
    cols = st.columns(2, gap='large')
    for col, team, title in zip(cols, ['radiant', 'dire'], ['Radiant', 'Dire']):
        with col:
            st.markdown(f'### {title}')
            heroes = st.multiselect(t('five_heroes', team=title), ids, format_func=names.get,
                                    max_selections=5, key=f'early_{team}_heroes')
            values = {stat: st.number_input(f"{t('stat_' + stat)} · {title}", min_value=0,
                max_value=MAXIMUM[stat], value=None, step=1, placeholder=t('value_placeholder'),
                key=f'early_{team}_{stat}') for stat in STATS}
            payload[team] = {'heroes': heroes, **values}
    chosen = payload['radiant']['heroes'] + payload['dire']['heroes']
    complete = all(len(payload[side]['heroes']) == 5 and all(payload[side][s] is not None for s in STATS) for side in ['radiant', 'dire'])
    unique = len(chosen) == len(set(chosen))
    if not unique:
        st.warning(t('duplicate_early'))
    elif not complete:
        st.info(t('incomplete_early'))
    if st.button(t('predict_early'), type='primary', disabled=not complete or not unique, key='early_predict'):
        try:
            with st.spinner(t('spinner_early')):
                response = requests.post(f'{api}/predict/early', json=payload, timeout=30)
                response.raise_for_status()
                st.session_state['early_prediction'] = (payload, response.json())
        except (requests.RequestException, ValueError):
            st.session_state.pop('early_prediction', None)
            st.error(t('early_failed'))
    saved = st.session_state.get('early_prediction')
    if saved and saved[0] == payload:
        result = saved[1]
        st.divider()
        st.subheader(t('early_result'))
        left, right = st.columns(2)
        left.metric('Radiant', f"{result['radiant_probability']:.1%}")
        right.metric('Dire', f"{result['dire_probability']:.1%}")
        st.caption(f"{t('early_note')} {t('early_model', name=result['model_name'], version=result['model_version'])}")
    elif saved:
        st.info(t('early_changed'))
    with st.expander(t('early_gain_title')):
        st.caption(t('early_gain_note'))
        st.dataframe(pd.DataFrame({t('col_heroes_only'): meta['draft_test_metrics'], t('col_heroes_5min'): meta['test_metrics']}).round(4), use_container_width=True)
        st.write(t('early_rows', train=meta['train_rows'], test=meta['test_rows']))
        st.caption(t('early_split'))
    with st.expander(t('sources_title')):
        st.markdown(t('sources_links'))
        st.write(t('sources_text'))
