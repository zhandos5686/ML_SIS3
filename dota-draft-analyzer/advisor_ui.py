"""Pick advisor tab: partial draft in, ranked next picks out. Inference goes through FastAPI."""
import requests
import streamlit as st
from i18n import t

EXAMPLE = {'adv_a': [1, 2, 3], 'adv_b': [6, 7, 8, 9], 'adv_side': 'team_a'}


def _load_example():
    st.session_state.update(EXAMPLE)


def _clear():
    st.session_state.update(adv_a=[], adv_b=[], adv_side='team_a')


def _pick(hero, side):
    key = 'adv_a' if side == 'team_a' else 'adv_b'
    st.session_state[key] = [*st.session_state.get(key, []), hero]
    if len(st.session_state[key]) == 5:  # this team is done; the other one picks next
        st.session_state['adv_side'] = 'team_b' if side == 'team_a' else 'team_a'


def _reason_text(item):
    parts = []
    if item.get('hero_strength') is not None:
        v = item['hero_strength']
        parts.append(t('adv_strength' if v > 0 else 'adv_weak', v=v))
    for reason in item['reasons']:
        parts.append(t('adv_' + reason['kind'], name=reason['name'], v=reason['effect']))
    return ' · '.join(parts)


def render(api, hero_names, ids, game_mode=2, game_type=2):
    st.write(t('adv_intro'))
    st.session_state.setdefault('adv_a', [])
    st.session_state.setdefault('adv_b', [])
    st.session_state.setdefault('adv_side', 'team_a')
    left, right = st.columns(2)
    left.button(t('adv_example'), on_click=_load_example, key='adv_example_btn')
    right.button(t('adv_clear'), on_click=_clear, key='adv_clear_btn')
    a_col, b_col = st.columns(2, gap='large')
    team_a = a_col.multiselect(t('adv_picked', team=t('team_a')), ids, format_func=hero_names.get, max_selections=5, key='adv_a')
    team_b = b_col.multiselect(t('adv_picked', team=t('team_b')), ids, format_func=hero_names.get, max_selections=5, key='adv_b')
    side = st.radio(t('adv_side'), ['team_a', 'team_b'], format_func=lambda s: t(s), horizontal=True, key='adv_side')

    duplicate = bool(set(team_a) & set(team_b))
    full = len(team_a if side == 'team_a' else team_b) == 5
    if duplicate:
        st.warning(t('adv_duplicate'))
    elif full:
        st.info(t('adv_full'))
    payload = {'team_a': team_a, 'team_b': team_b, 'side': side, 'game_mode': game_mode, 'game_type': game_type, 'top': 5}
    if st.button(t('adv_button'), type='primary', disabled=duplicate or full, key='adv_go'):
        try:
            with st.spinner(t('adv_spinner')):
                response = requests.post(f'{api}/recommend', json=payload, timeout=30)
                response.raise_for_status()
                st.session_state['advice'] = (payload, response.json())
        except (requests.RequestException, ValueError):
            st.session_state.pop('advice', None)
            st.error(t('adv_failed'))

    saved = st.session_state.get('advice')
    if not saved or saved[0] != payload:
        return
    result = saved[1]
    st.divider()
    st.subheader(t('adv_title', team=t(result['side'])))
    st.caption(t('adv_random', p=result['random_pick_probability']))
    st.caption(t('adv_exact') if result['exact'] else t('adv_sampled', n=result['samples']))
    widths = [2.2, 1.3, 1.5, 4.5, 1]
    header = st.columns(widths)
    for col, key in zip(header, ['adv_col_hero', 'adv_col_win', 'adv_col_gain', 'adv_col_why']):
        col.markdown(f"**{t(key)}**")
    for item in result['recommendations']:
        hero, win, gain, why, act = st.columns(widths, vertical_alignment='center')
        hero.write(item['name'])
        win.write(f"{item['win_probability']:.1%}")
        gain.write(f"{100 * item['delta']:+.1f} pp")
        why.caption(_reason_text(item))
        act.button(t('adv_pick'), key=f"adv_pick_{item['hero_id']}", on_click=_pick, args=(item['hero_id'], result['side']))
    st.caption(t('adv_note'))
    st.caption(t('model_version', name=result['model_name'], version=result['model_version']))
