import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, time as dtime

# ===== 기본 설정 =====
SHEET_CSV = "https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/export?format=csv&gid=0"

st.set_page_config(page_title="교실 에너지 모니터링", page_icon="🌍", layout="wide")

# 자동 새로고침 (30초)
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30 * 1000, key="refresh")
except ImportError:
    pass


# ========================================
# 교시 시간 정의
# ========================================
PERIODS = [
    ("조회",   dtime(8, 10),  dtime(8, 20)),
    ("1교시", dtime(8, 20),  dtime(9, 10)),
    ("2교시", dtime(9, 10),  dtime(10, 0)),
    ("3교시", dtime(10, 0),  dtime(10, 50)),
    ("4교시", dtime(10, 50), dtime(11, 40)),
    ("점심",   dtime(11, 40), dtime(13, 10)),
    ("5교시", dtime(13, 10), dtime(14, 0)),
    ("6교시", dtime(14, 0),  dtime(14, 50)),
    ("7교시", dtime(14, 50), dtime(15, 40)),  # 화·목만
]

# 요일별 마지막 교시 (월=0 ~ 일=6)
LAST_PERIOD = {0: "6교시", 1: "7교시", 2: "6교시", 3: "7교시", 4: "6교시"}


# ========================================
# 시간표 (여기에 입력! 2-3반만 작성)
# 형식: TIMETABLE["반"]["요일"]["교시"] = "과목"
# 요일: 월/화/수/목/금
# ========================================
TIMETABLE = {
    "2-3": {
        "월": {"1교시": "국어", "2교시": "수학", "3교시": "영어", "4교시": "과학",
               "5교시": "체육", "6교시": "사회"},
        "화": {"1교시": "수학", "2교시": "국어", "3교시": "체육", "4교시": "영어",
               "5교시": "과학", "6교시": "음악", "7교시": "미술"},
        "수": {"1교시": "영어", "2교시": "과학", "3교시": "국어", "4교시": "수학",
               "5교시": "사회", "6교시": "체육"},
        "목": {"1교시": "과학", "2교시": "체육", "3교시": "수학", "4교시": "국어",
               "5교시": "영어", "6교시": "기술", "7교시": "한문"},
        "금": {"1교시": "사회", "2교시": "영어", "3교시": "과학", "4교시": "체육",
               "5교시": "국어", "6교시": "수학"},
    },
    # 다른 반은 나중에 추가!
}

# 이동수업으로 간주할 과목 (교실 비는 시간)
MOVING_SUBJECTS = ["체육", "음악", "미술", "기술", "과학"]  # 과학실/체육관 등 이동

WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]


# ========================================
# 현재 교시 / 과목 찾기
# ========================================
def get_current_period(now):
    """현재 시각에 해당하는 교시 이름 반환"""
    weekday = now.weekday()
    if weekday >= 5:  # 주말
        return None, "주말"
    now_t = now.time()
    last = LAST_PERIOD.get(weekday, "6교시")
    last_idx = [p[0] for p in PERIODS].index(last)

    for i, (name, start, end) in enumerate(PERIODS):
        if i > last_idx:
            break
        if start <= now_t < end:
            return name, None
    return None, "수업시간 아님"


def get_subject(class_id, now, period):
    """현재 교시의 과목 반환"""
    if period is None:
        return None
    weekday = now.weekday()
    if weekday >= 5:
        return None
    day = WEEKDAY_KR[weekday]
    return TIMETABLE.get(class_id, {}).get(day, {}).get(period, None)


# ========================================
# 데이터 로드
# ========================================
@st.cache_data(ttl=20)
def load_data():
    df = pd.read_csv(SHEET_CSV)
    df.columns = ["시간", "반", "co2", "온도", "습도", "가스", "조도", "상태"]
    for col in ["co2", "온도", "습도", "가스"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

df = load_data()


# ========================================
# 에너지 상태 판단 (시간표 반영!)
# ========================================
def check_status(temp, co2, class_id, now):
    if pd.isna(temp):
        return "❓ 측정실패", "데이터 없음", "gray"

    period, _ = get_current_period(now)
    subject = get_subject(class_id, now, period)
    people = co2 >= 600

    # 이동수업인데 냉방 켜둠 = 낭비!
    if subject in MOVING_SUBJECTS and temp < 24:
        return "🔴 이동수업 냉방 낭비!", f"{subject} 시간인데 냉방 켜둠", "red"

    if temp >= 29:
        return "⚪ 냉방 안 함", "온도 높음", "orange"
    elif temp < 22:
        if not people:
            return "🟡 빈 교실 냉방 의심", "사람 없는데 냉방", "gold"
        else:
            return "🔴 과냉방 (낭비!)", "온도 너무 낮음", "red"
    else:
        return "🟢 정상", "적정 온도", "green"


# ========================================
# 디자인: CSS 주입 (지구 배경 + 움직이는 도형)
# ========================================
st.markdown("""
<style>
/* 전체 배경: 우주/지구 느낌 그라데이션 */
.stApp {
    background: linear-gradient(-45deg, #0a1128, #1c3a5e, #0a2342, #15396b);
    background-size: 400% 400%;
    animation: gradientMove 18s ease infinite;
}
@keyframes gradientMove {
    0% {background-position: 0% 50%;}
    50% {background-position: 100% 50%;}
    100% {background-position: 0% 50%;}
}

/* 움직이는 도형들 (배경 뒤에 깔림, 기능 안 가림) */
.shape {
    position: fixed;
    border-radius: 50%;
    opacity: 0.12;
    z-index: 0;
    pointer-events: none;
}
.shape1 {width:300px;height:300px;background:#4ECDC4;top:10%;left:5%;
         animation: floatA 20s ease-in-out infinite;}
.shape2 {width:200px;height:200px;background:#FF6B6B;top:60%;right:8%;
         animation: floatB 25s ease-in-out infinite;}
.shape3 {width:150px;height:150px;background:#FFD93D;bottom:10%;left:15%;
         animation: floatA 30s ease-in-out infinite;}
@keyframes floatA {
    0%,100% {transform: translate(0,0) rotate(0deg);}
    50% {transform: translate(40px,-60px) rotate(180deg);}
}
@keyframes floatB {
    0%,100% {transform: translate(0,0) rotate(0deg);}
    50% {transform: translate(-50px,40px) rotate(-180deg);}
}

/* 콘텐츠는 도형 위로 (안 가려지게!) */
.main .block-container {position: relative; z-index: 1;}

/* 카드/텍스트 가독성 위해 살짝 밝게 */
[data-testid="stMetricValue"] {color: #ffffff;}
h1, h2, h3, p, .stMarkdown {color: #f0f4f8;}

/* 실시간 시계 박스 */
.clock-box {
    background: rgba(255,255,255,0.1);
    backdrop-filter: blur(10px);
    border: 1px solid rgba(255,255,255,0.2);
    border-radius: 20px;
    padding: 20px;
    text-align: center;
    margin-bottom: 20px;
}
.clock-time {font-size: 42px; font-weight: 800; color: #4ECDC4; margin:0;}
.clock-date {font-size: 16px; color: #b0c4de; margin:0;}
.clock-period {font-size: 20px; color: #FFD93D; margin-top:8px;}
</style>

<div class="shape shape1"></div>
<div class="shape shape2"></div>
<div class="shape shape3"></div>
""", unsafe_allow_html=True)


# ========================================
# 현재 시각
# ========================================
now = datetime.now()
period, period_msg = get_current_period(now)


# ========================================
# 사이드바
# ========================================
st.sidebar.title("🌍 에너지 모니터링")
page = st.sidebar.radio(
    "페이지 선택",
    ["🏠 대시보드 홈", "📊 반별 상세", "🏆 에너지 랭킹", "📋 전체 데이터"]
)
st.sidebar.divider()
st.sidebar.caption(f"총 데이터: {len(df)}개")
st.sidebar.caption(f"측정 반: {df['반'].nunique()}개")
st.sidebar.caption("⏱️ 30초마다 자동 갱신")


# ========================================
# 페이지 1: 대시보드 홈
# ========================================
if page == "🏠 대시보드 홈":
    # 실시간 시계
    weekday_name = WEEKDAY_KR[now.weekday()]
    if period:
        period_text = f"📚 현재: {period}"
    else:
        period_text = f"☕ {period_msg}"

    st.markdown(f"""
    <div class="clock-box">
        <p class="clock-time">{now.strftime('%H:%M:%S')}</p>
        <p class="clock-date">{now.strftime('%Y년 %m월 %d일')} ({weekday_name}요일)</p>
        <p class="clock-period">{period_text}</p>
    </div>
    """, unsafe_allow_html=True)

    st.title("🏠 전체 교실 현황")

    latest = df.groupby("반").last().reset_index()

    # 요약 통계
    total = len(latest)
    waste = sum(1 for _, r in latest.iterrows()
                if check_status(r["온도"], r["co2"], r["반"], now)[2] in ["red", "gold"])
    normal = sum(1 for _, r in latest.iterrows()
                 if check_status(r["온도"], r["co2"], r["반"], now)[2] == "green")

    c1, c2, c3 = st.columns(3)
    c1.metric("📊 측정 중인 반", f"{total}개")
    c2.metric("🟢 정상", f"{normal}개")
    c3.metric("🔴 낭비 의심", f"{waste}개")

    st.divider()
    st.subheader("⚡ 반별 상태 (현재 교시 과목 표시)")

    cards_per_row = 4
    rows = [latest[i:i+cards_per_row] for i in range(0, len(latest), cards_per_row)]
    for row_group in rows:
        cols = st.columns(cards_per_row)
        for idx, (_, row) in enumerate(row_group.iterrows()):
            status, reason, color = check_status(row["온도"], row["co2"], row["반"], now)
            subject = get_subject(row["반"], now, period)
            subject_text = f"📖 {subject}" if subject else "—"
            with cols[idx]:
                with st.container(border=True):
                    st.markdown(f"### {row['반']}")
                    st.markdown(f"**{subject_text}** ({period or '쉬는시간'})")
                    st.markdown(f"**{status}**")
                    st.caption(reason)
                    st.text(f"🌡️ {row['온도']}도  🫁 {row['co2']}ppm")


# ========================================
# 페이지 2: 반별 상세 (plotly)
# ========================================
elif page == "📊 반별 상세":
    st.title("📊 반별 상세 그래프")

    class_list = sorted(df["반"].unique().tolist())
    selected = st.selectbox("반을 선택하세요", class_list)
    class_df = df[df["반"] == selected].copy().reset_index(drop=True)

    # 측정 순번 (x축 글자 길이 문제 해결!)
    class_df["측정순번"] = range(1, len(class_df) + 1)

    latest_row = class_df.iloc[-1]
    status, reason, color = check_status(latest_row["온도"], latest_row["co2"], selected, now)
    subject = get_subject(selected, now, period)

    st.markdown(f"## {selected}반 — {status}")
    st.caption(f"{reason} · 현재 과목: {subject or '없음'} · 데이터 {len(class_df)}개")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🫁 CO₂", f"{latest_row['co2']} ppm")
    c2.metric("🌡️ 온도", f"{latest_row['온도']} °C")
    c3.metric("💧 습도", f"{latest_row['습도']} %")
    c4.metric("🔥 가스", f"{latest_row['가스']}")

    st.divider()

    # plotly 그래프 함수
    def make_chart(y_col, title, color):
        fig = px.line(class_df, x="측정순번", y=y_col, title=title, markers=True)
        fig.update_traces(line_color=color, line_width=3)
        fig.update_layout(
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            font_color="#f0f4f8",
            title_font_size=18,
            xaxis_title="측정 순번",
            margin=dict(l=20, r=20, t=50, b=20),
            height=300,
        )
        fig.update_xaxes(showgrid=True, gridcolor="rgba(255,255,255,0.1)")
        fig.update_yaxes(showgrid=True, gridcolor="rgba(255,255,255,0.1)")
        return fig

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(make_chart("co2", "🫁 CO₂ 변화", "#FF6B6B"), use_container_width=True)
        st.plotly_chart(make_chart("온도", "🌡️ 온도 변화", "#4ECDC4"), use_container_width=True)
    with col2:
        st.plotly_chart(make_chart("습도", "💧 습도 변화", "#45B7D1"), use_container_width=True)
        st.plotly_chart(make_chart("가스", "🔥 가스 변화", "#FFD93D"), use_container_width=True)


# ========================================
# 페이지 3: 에너지 랭킹
# ========================================
elif page == "🏆 에너지 랭킹":
    st.title("🏆 에너지 절약 랭킹")
    st.caption("적정 온도(25도)에 가까울수록 높은 점수!")

    latest = df.groupby("반").last().reset_index()

    def score(temp):
        if pd.isna(temp):
            return 0
        return max(0, 100 - abs(temp - 25) * 10)

    latest["점수"] = latest["온도"].apply(score)
    ranked = latest.sort_values("점수", ascending=False).reset_index(drop=True)

    for idx, row in ranked.iterrows():
        medal = ["🥇", "🥈", "🥉"][idx] if idx < 3 else f"{idx+1}위"
        status, reason, color = check_status(row["온도"], row["co2"], row["반"], now)
        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 2, 3])
            c1.markdown(f"## {medal}")
            c2.markdown(f"### {row['반']}")
            c2.caption(f"{int(row['점수'])}점")
            c3.markdown(f"**{status}**")
            c3.caption(f"🌡️ {row['온도']}도 · {reason}")


# ========================================
# 페이지 4: 전체 데이터
# ========================================
elif page == "📋 전체 데이터":
    st.title("📋 전체 데이터")

    class_list = ["전체"] + sorted(df["반"].unique().tolist())
    selected = st.selectbox("반 필터", class_list)
    view_df = df if selected == "전체" else df[df["반"] == selected]

    st.dataframe(view_df, use_container_width=True)
    st.caption(f"총 {len(view_df)}개의 데이터")

    csv = view_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 CSV 다운로드", csv, "교실데이터.csv", "text/csv")
