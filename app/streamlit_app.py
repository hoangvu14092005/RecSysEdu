"""LearnPath base: view an explicit snapshot; never train in a UI request."""

import os
from collections import defaultdict
from pathlib import Path

import streamlit as st

from recsysedu.demo.artifacts import MODEL_LABELS, PREREQUISITE_LABELS, load_bundle

st.set_page_config(page_title='LearnPath', page_icon='📚', layout='wide')
root = Path(__file__).resolve().parents[1]
path = Path(os.environ.get('RECSYSEDU_BUNDLE', str(root / 'tests/fixtures/demo_bundle.json')))
try:
    bundle = load_bundle(path)
except (OSError, ValueError) as exc:
    st.error(f'Không mở được dữ liệu giao diện: {exc}')
    st.stop()

meta = bundle['meta']
st.title('LearnPath')
st.caption('Gợi ý khóa học và xem kết quả mô hình')
if meta['data_mode'] == 'synthetic':
    st.warning('DỮ LIỆU MẪU — ranking và lý do minh họa để dựng UI; chưa huấn luyện mô hình thật.')
else:
    st.info('KẾT QUẢ THẬT — đọc từ snapshot được cung cấp, không huấn luyện khi bấm giao diện.')

users = {user['user_id']: user for user in bundle['users']}
courses = {course['course_id']: course for course in bundle['courses']}
if not users:
    st.info('Chưa có hồ sơ để xem.')
    st.stop()
user_id = st.sidebar.selectbox('Hồ sơ', list(users), key='user',
                               format_func=lambda value: users[value]['display_name'])
options = [rec for rec in bundle['recommendations'] if rec['user_id'] == user_id]
model_ids = list(dict.fromkeys(rec['model_id'] for rec in options))
if not model_ids:
    st.info('Hồ sơ này chưa có kết quả gợi ý.')
    st.stop()
if st.session_state.get('model') not in model_ids:
    st.session_state['model'] = model_ids[0]
model_id = st.sidebar.selectbox('Mô hình', model_ids, key='model',
                                format_func=lambda value: MODEL_LABELS[value])
user = users[user_id]
st.sidebar.subheader('Lịch sử đăng ký')
for course_id in user['observed_course_ids']:
    st.sidebar.text(courses[course_id]['name'] or course_id)
if not user['observed_course_ids']:
    st.sidebar.info('Người mới: chưa có lịch sử đăng ký.')

rec = next(rec for rec in options if rec['model_id'] == model_id)
portal, lab = st.tabs(['Gợi ý học tập', 'Model Lab'])
with portal:
    st.subheader('Dành cho bạn')
    if rec['fallback_status'] != 'none':
        st.info('Hồ sơ chưa đủ dữ liệu cho mô hình này; đang dùng gợi ý dự phòng.')
    if len(rec['items']) < 10:
        st.caption(f"Có {len(rec['items'])} khóa trong snapshot này; không thêm khóa để đủ 10.")
    for item in rec['items']:
        course = courses[item['course_id']]
        with st.container(border=True):
            st.text(f"#{item['rank']}  {course['name'] or item['course_id']}")
            st.text('Lĩnh vực: ' + (', '.join(course['fields']) or 'chưa có thông tin'))
            st.caption(PREREQUISITE_LABELS[item['prerequisite_status']])
            with st.expander(f"Giải thích khóa #{item['rank']}"):
                for evidence in item['evidence']:
                    st.text(evidence)
                st.caption(f"Điểm xếp hạng: {item['score']:.3f}; không phải xác suất học thành công.")
    if not rec['items']:
        st.info('Chưa có khóa phù hợp trong tập kết quả được cung cấp.')
    st.info('Lộ trình chưa được tích hợp trong base; cần graph đã kiểm tra ở giai đoạn P1.')

with lab:
    st.subheader('Kết quả chạy offline')
    st.caption('So sánh theo chỉ số đánh giá, không so điểm thô của các model.')
    grouped = defaultdict(list)
    for run in bundle['runs']:
        key = (run['evaluation_split'], run['cohort'], run['candidate_policy'], run['seen_policy'])
        grouped[key].append(run)
    for (split, cohort, candidate, seen), runs in grouped.items():
        st.text(f'Split: {split} | Nhóm: {cohort} | Candidate: {candidate} | Seen: {seen}')
        rows = []
        for run in runs:
            row = {
                'Mô hình': MODEL_LABELS[run['model_id']], 'Run ID': run['run_id'],
                'Dataset': meta['dataset_version'], 'Protocol': meta['protocol_id'],
                'Split': split, 'Cohort': cohort, 'Cỡ mẫu': run['cohort_size'],
                'Candidate': candidate, 'Seen policy': seen, 'Seed': run['seed'],
                'Config hash': run['config_hash'], 'Dataset hash': run['dataset_hash'],
                'Split hash': run['split_hash'], 'Data mode': meta['data_mode'],
                'Trạng thái': 'Đã đo' if run['metric_status'] == 'measured' else 'Chưa có metric',
            }
            row.update(run['metrics'] or {})
            rows.append(row)
        st.dataframe(rows, hide_index=True, width='stretch')
        if all(run['metric_status'] == 'not_available' for run in runs):
            st.info('Chưa có số liệu huấn luyện/đánh giá. Không điền metric giả hoặc số 0.')
        import pandas as pd
        st.download_button('Tải bảng cùng thông tin run', pd.DataFrame(rows).to_csv(index=False),
                           file_name=f'learnpath_{split}_runs.csv', mime='text/csv',
                           key=f'csv-{split}-{cohort}-{candidate}-{seen}')
