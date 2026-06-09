import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime, time as dtime

# ===== 기본 설정 =====
SHEET_CSV = "https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/export?format=csv&gid=0"

st.set_page_config(page_title="교실 에너지 모니터링", page_icon="🌍", layout="wide")

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30 * 1000, key="refresh")
except ImportError:
    pass


# ========================================
# 일정 정의 (조회/교시/쉬는시간/점심/종례)
# ========================================
# 기본 일과 (월·수·금: 6교시 + 종례 15:00~15:10)
SCHEDULE_6 = [
    ("조회",     dtime(8, 10),  dtime(8, 20),  "homeroom"),
    ("1교시",   dtime(8, 20),  dtime(9, 10),  "class"),
    ("쉬는시간", dtime(9, 10),  dtime(9, 20),  "break"),
    ("2교시",   dtime(9, 20),  dtime(10, 10), "class"),
    ("쉬는시간", dtime(10, 10), dtime(10, 20), "break"),
    ("3교시",   dtime(10, 20), dtime(11, 10), "class"),
    ("쉬는시간", dtime(11, 10), dtime(11, 20), "break"),
    ("4교시",   dtime(11, 20), dtime(12, 10), "class"),
    ("점심시간", dtime(12, 10), dtime(13, 10), "lunch"),
    ("5교시",   dtime(13, 10), dtime(14, 0),  "class"),
    ("쉬는시간", dtime(14, 0),  dtime(14, 10), "break"),
    ("6교시",   dtime(14, 10), dtime(15, 0),  "class"),
    ("종례",     dtime(15, 0),  dtime(15, 10), "homeroom"),
]

# 화·목: 7교시 + 종례 15:40~15:50
SCHEDULE_7 = [
    ("조회",     dtime(8, 10),  dtime(8, 20),  "homeroom"),
    ("1교시",   dtime(8, 20),  dtime(9, 10),  "class"),
    ("쉬는시간", dtime(9, 10),  dtime(9, 20),  "break"),
    ("2교시",   dtime(9, 20),  dtime(10, 10), "class"),
    ("쉬는시간", dtime(10, 10), dtime(10, 20), "break"),
    ("3교시",   dtime(10, 20), dtime(11, 10), "class"),
    ("쉬는시간", dtime(11, 10), dtime(11, 20), "break"),
    ("4교시",   dtime(11, 20), dtime(12, 10), "class"),
    ("점심시간", dtime(12, 10), dtime(13, 10), "lunch"),
    ("5교시",   dtime(13, 10), dtime(14, 0),  "class"),
    ("쉬는시간", dtime(14, 0),  dtime(14, 10), "break"),
    ("6교시",   dtime(14, 10), dtime(15, 0),  "class"),
    ("쉬는시간", dtime(15, 0),  dtime(15, 10), "break"),
    ("7교시",   dtime(15, 10), dtime(16, 0),  "class"),
    ("종례",     dtime(16, 0),  dtime(16, 10), "homeroom"),
]

# 요일별 일과표 (월=0 ~ 금=4)
DAY_SCHEDULE = {0: SCHEDULE_6, 1: SCHEDULE_7, 2: SCHEDULE_6, 3: SCHEDULE_7, 4: SCHEDULE_6}

WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]


# ========================================
# 시간표 (2-3반)
# ========================================
TIMETABLE = {
    "2-3": {
        "월": {"1교시": "문학A", "2교시": "영어B", "3교시": "선택 과목", "4교시": "선택 과목",
               "5교시": "대수", "6교시": "음악 연주와 창작"},
        "화": {"1교시": "선택 과목", "2교시": "문학C", "3교시": "합주", "4교시": "선택 과목",
               "5교시": "대수", "6교시": "스포츠 생활B", "7교시": "선택 과목"},
        "수": {"1교시": "영어A", "2교시": "선택 과목", "3교시": "선택 과목", "4교시": "문학B",
               "5교시": "선택 과목", "6교시": "대수"},
        "목": {"1교시": "선택 과목", "2교시": "스포츠 생활A", "3교시": "선택 과목", "4교시": "선택 과목",
               "5교시": "영어A", "6교시": "선택 과목", "7교시": "대수"},
        "금": {"1교시": "선택 과목", "2교시": "선택 과목", "3교시": "영어C", "4교시": "문학D",
               "5교시": "자율", "6교시": "자율"},
    },
}

MOVING_SUBJECTS = ["스포츠 생활A", "스포츠 생활B"]


# ========================================
# 현재 일정 찾기
# ========================================
def get_current_slot(now):
    """현재 (일정이름, 종류) 반환. 종류: class/break/lunch/homeroom/after/weekend"""
    weekday = now.weekday()
    if weekday >= 5:
        return "주말", "weekend"
    now_t = now.time()
    schedule = DAY_SCHEDULE[weekday]

    # 일과 시작 전
    if now_t < schedule[0][1]:
        return "등교 전", "before"

    for name, start, end, kind in schedule:
        if start <= now_t < end:
            return name, kind

    # 모든 일정 끝남
    return "방과후", "after"


def get_subject(class_id, now, slot_name):
    """현재 교시 과목 반환 (교시일 때만)"""
    if "교시" not in slot_name:
        return None
    weekday = now.weekday()
    if weekday >= 5:
        return None
    day = WEEKDAY_KR[weekday]
    return TIMETABLE.get(class_id, {}).get(day, {}).get(slot_name, None)


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
# 에너지 상태 판단
# ========================================
def check_status(temp, co2, class_id, now):
    if pd.isna(temp):
        return "❓ 측정실패", "데이터 없음", "gray"

    slot_name, kind = get_current_slot(now)
    subject = get_subject(class_id, now, slot_name)
    people = co2 >= 600

    # 이동수업인데 냉방 켜둠
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


# 카드 색상 매핑
COLOR_HEX = {
    "green":  "#2e7d32",
    "red":    "#c62828",
    "gold":   "#f9a825",
    "orange": "#ef6c00",
    "gray":   "#757575",
}


# ========================================
# 디자인 CSS (밝은 지구/하늘 테마 + 애니메이션)
# ========================================
st.markdown("""
<style>
/* ===== 밝은 하늘 배경 (낮의 지구) ===== */
.stApp {
    background:
        radial-gradient(circle at 80% 15%, rgba(255,241,150,0.6) 0%, rgba(255,241,150,0) 12%),
        linear-gradient(180deg, #ade4ff 0%, #c9efff 35%, #e3f7ff 70%, #f0fbe5 100%);
    background-attachment: fixed;
}

/* 태양 */
.sun {
    position: fixed; top: 8%; right: 10%;
    width: 90px; height: 90px; border-radius: 50%;
    background: radial-gradient(circle, #fff7c2 0%, #ffe066 50%, #ffcc33 100%);
    box-shadow: 0 0 60px rgba(255,204,51,0.7), 0 0 120px rgba(255,224,102,0.5);
    z-index: 0; pointer-events: none;
    animation: sunPulse 5s ease-in-out infinite;
}
@keyframes sunPulse {
    0%,100% { box-shadow: 0 0 60px rgba(255,204,51,0.7), 0 0 120px rgba(255,224,102,0.5);}
    50% { box-shadow: 0 0 80px rgba(255,204,51,0.9), 0 0 160px rgba(255,224,102,0.7);}
}

/* 떠다니는 구름 */
.cloud {
    position: fixed; z-index: 0; pointer-events: none;
    background: #ffffff; border-radius: 100px; opacity: 0.85;
    box-shadow: 0 8px 20px rgba(0,0,0,0.06);
}
.cloud::before, .cloud::after {
    content:''; position:absolute; background:#fff; border-radius:50%;
}
.cloud1 { width:120px; height:40px; top:18%; left:-150px;
          animation: drift1 40s linear infinite; }
.cloud1::before { width:55px; height:55px; top:-25px; left:20px; }
.cloud1::after  { width:40px; height:40px; top:-15px; left:65px; }
.cloud2 { width:90px; height:30px; top:35%; left:-150px;
          animation: drift2 55s linear infinite; }
.cloud2::before { width:42px; height:42px; top:-20px; left:15px; }
.cloud2::after  { width:32px; height:32px; top:-12px; left:50px; }
.cloud3 { width:140px; height:45px; top:55%; left:-200px;
          animation: drift1 65s linear infinite; }
.cloud3::before { width:60px; height:60px; top:-28px; left:25px; }
.cloud3::after  { width:45px; height:45px; top:-18px; left:75px; }
@keyframes drift1 { from{transform:translateX(0);} to{transform:translateX(calc(100vw + 300px));} }
@keyframes drift2 { from{transform:translateX(0);} to{transform:translateX(calc(100vw + 300px));} }

/* 떠다니는 잎사귀/원형 도형 (지구 자연 느낌) */
.leaf {
    position: fixed; z-index: 0; pointer-events: none;
    font-size: 28px; opacity: 0.55;
    animation: floatLeaf 18s ease-in-out infinite;
}
.leaf1 { top:70%; left:8%;  animation-delay:0s; }
.leaf2 { top:25%; left:85%; animation-delay:4s; }
.leaf3 { top:80%; left:60%; animation-delay:8s; }
.leaf4 { top:45%; left:30%; animation-delay:12s; }
@keyframes floatLeaf {
    0%,100% { transform: translateY(0) rotate(0deg); }
    50% { transform: translateY(-40px) rotate(25deg); }
}

/* 콘텐츠는 항상 배경 위로 (가독성!) */
.main .block-container { position: relative; z-index: 1; }

/* 제목/텍스트 색 (밝은 배경이라 어둡게) */
h1, h2, h3 { color: #0d3b5e !important; text-shadow: 0 1px 2px rgba(255,255,255,0.6); }
.stMarkdown p, label { color: #1a4a6e !important; }

/* 사이드바 */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #1565c0 0%, #0d47a1 100%);
}
[data-testid="stSidebar"] * { color: #ffffff !important; }

/* ===== 멋진 시계 박스 ===== */
.clock-box {
    background: linear-gradient(135deg, #1976d2 0%, #42a5f5 60%, #29b6f6 100%);
    border-radius: 28px;
    padding: 28px 30px;
    margin-bottom: 24px;
    box-shadow: 0 10px 35px rgba(25,118,210,0.4), inset 0 2px 10px rgba(255,255,255,0.3);
    position: relative;
    overflow: hidden;
    border: 3px solid rgba(255,255,255,0.5);
}
.clock-box::before {
    content:''; position:absolute; top:-40px; right:-40px;
    width:160px; height:160px; border-radius:50%;
    background: rgba(255,255,255,0.15);
}
.clock-box::after {
    content:''; position:absolute; bottom:-50px; left:-30px;
    width:130px; height:130px; border-radius:50%;
    background: rgba(255,255,255,0.1);
}
.clock-time {
    font-size: 54px; font-weight: 900; color: #ffffff; margin:0;
    text-shadow: 0 2px 8px rgba(0,0,0,0.25); letter-spacing: 2px;
    position: relative; z-index: 2;
}
.clock-date { font-size: 18px; color: #e3f2fd; margin:4px 0 0 0; position: relative; z-index: 2; }
.clock-slot {
    display:inline-block; margin-top:14px; padding:8px 22px;
    background: rgba(255,255,255,0.95); border-radius: 30px;
    font-size: 20px; font-weight: 800; color: #0d47a1;
    box-shadow: 0 4px 12px rgba(0,0,0,0.15); position: relative; z-index: 2;
}

/* ===== 반별 상태 카드 (불투명!) ===== */
.class-card {
    border-radius: 22px;
    padding: 20px;
    margin-bottom: 8px;
    color: #ffffff;
    box-shadow: 0 8px 24px rgba(0,0,0,0.2);
    border: 3px solid rgba(255,255,255,0.6);
    position: relative;
    overflow: hidden;
}
.class-card::before {
    content:''; position:absolute; top:-30px; right:-30px;
    width:110px; height:110px; border-radius:50%;
    background: rgba(255,255,255,0.12);
}
.cc-name { font-size: 26px; font-weight: 900; margin:0; }
.cc-subject { font-size: 15px; opacity: 0.95; margin:2px 0 10px 0; }
.cc-status { font-size: 19px; font-weight: 800; margin:6px 0; }
.cc-reason { font-size: 13px; opacity: 0.92; margin-bottom:10px; }
.cc-data { font-size: 15px; font-weight: 600;
           background: rgba(255,255,255,0.18); border-radius: 12px; padding: 8px 10px; }

/* 일반 정보 박스 */
.info-card {
    background: #ffffff;
    border-radius: 20px;
    padding: 22px;
    box-shadow: 0 6px 20px rgba(0,0,0,0.1);
    border: 2px solid #e0f0ff;
    margin-bottom: 12px;
}
</style>

<div class="sun"></div>
<div class="cloud cloud1"></div>
<div class="cloud cloud2"></div>
<div class="cloud cloud3"></div>
<div class="leaf leaf1">🍃</div>
<div class="leaf leaf2">🌿</div>
<div class="leaf leaf3">🍃</div>
<div class="leaf leaf4">🌎</div>
""", unsafe_allow_html=True)


# ========================================
# 현재 시각 / 일정
# ========================================
now = datetime.now()
slot_name, slot_kind = get_current_slot(now)


# ========================================
# 사이드바
# ========================================
st.sidebar.title("🌍 에너지 모니터링")
page = st.sidebar.radio(
    "페이지 선택",
    ["🏠 대시보드 홈", "📊 반별 상세", "🏆 에너지 랭킹",
     "📅 오늘의 시간표", "💡 에너지 리포트", "ℹ️ 시스템 정보"]
)
st.sidebar.divider()
st.sidebar.caption(f"총 데이터: {len(df)}개")
st.sidebar.caption(f"측정 반: {df['반'].nunique()}개")
st.sidebar.caption("⏱️ 30초마다 자동 갱신")


# ========================================
# 페이지 1: 대시보드 홈
# ========================================
if page == "🏠 대시보드 홈":
    weekday_name = WEEKDAY_KR[now.weekday()]

    # 일정 종류별 아이콘
    slot_icons = {
        "class": "📚", "break": "☕", "lunch": "🍱",
        "homeroom": "📢", "after": "🏠", "before": "🌅",
        "weekend": "🌴",
    }
    icon = slot_icons.get(slot_kind, "🕐")

    st.markdown(f"""
    <div class="clock-box">
        <p class="clock-time">{now.strftime('%H:%M:%S')}</p>
        <p class="clock-date">{now.strftime('%Y년 %m월 %d일')} ({weekday_name}요일)</p>
        <span class="clock-slot">{icon} {slot_name}</span>
    </div>
    """, unsafe_allow_html=True)

    st.title("🏠 전체 교실 현황")

    latest = df.groupby("반").last().reset_index()

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
    st.subheader("⚡ 반별 상태")

    cards_per_row = 4
    rows = [latest[i:i+cards_per_row] for i in range(0, len(latest), cards_per_row)]
    for row_group in rows:
        cols = st.columns(cards_per_row)
        for idx, (_, row) in enumerate(row_group.iterrows()):
            status, reason, color = check_status(row["온도"], row["co2"], row["반"], now)
            subject = get_subject(row["반"], now, slot_name)
            subject_text = f"📖 {subject} · {slot_name}" if subject else f"🕐 {slot_name}"
            bg = COLOR_HEX.get(color, "#757575")
            with cols[idx]:
                st.markdown(f"""
                <div class="class-card" style="background:{bg};">
                    <p class="cc-name">{row['반']}</p>
                    <p class="cc-subject">{subject_text}</p>
                    <p class="cc-status">{status}</p>
                    <p class="cc-reason">{reason}</p>
                    <div class="cc-data">🌡️ {row['온도']}°C &nbsp; 🫁 {row['co2']}ppm<br>
                    💧 {row['습도']}% &nbsp; 🔥 가스 {row['가스']}</div>
                </div>
                """, unsafe_allow_html=True)


# ========================================
# 페이지 2: 반별 상세
# ========================================
elif page == "📊 반별 상세":
    st.title("📊 반별 상세 그래프")

    class_list = sorted(df["반"].unique().tolist())
    selected = st.selectbox("반을 선택하세요", class_list)
    class_df = df[df["반"] == selected].copy().reset_index(drop=True)
    class_df["측정순번"] = range(1, len(class_df) + 1)

    latest_row = class_df.iloc[-1]
    status, reason, color = check_status(latest_row["온도"], latest_row["co2"], selected, now)
    subject = get_subject(selected, now, slot_name)

    st.markdown(f"## {selected}반 — {status}")
    st.caption(f"{reason} · 현재: {subject or slot_name} · 데이터 {len(class_df)}개")

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🫁 CO₂", f"{latest_row['co2']} ppm")
    c2.metric("🌡️ 온도", f"{latest_row['온도']} °C")
    c3.metric("💧 습도", f"{latest_row['습도']} %")
    c4.metric("🔥 가스", f"{latest_row['가스']}")

    st.divider()

    def make_chart(y_col, title, color):
        fig = px.line(class_df, x="측정순번", y=y_col, title=title, markers=True)
        fig.update_traces(line_color=color, line_width=3,
                          marker=dict(size=7, color=color))
        fig.update_layout(
            plot_bgcolor="rgba(255,255,255,0.85)",
            paper_bgcolor="rgba(255,255,255,0)",
            font_color="#0d3b5e",
            title_font_size=18,
            xaxis_title="측정 순번",
            margin=dict(l=20, r=20, t=50, b=20),
            height=300,
        )
        fig.update_xaxes(showgrid=True, gridcolor="rgba(13,59,94,0.1)")
        fig.update_yaxes(showgrid=True, gridcolor="rgba(13,59,94,0.1)")
        return fig

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(make_chart("co2", "🫁 CO₂ 변화", "#e53935"), use_container_width=True)
        st.plotly_chart(make_chart("온도", "🌡️ 온도 변화", "#00897b"), use_container_width=True)
    with col2:
        st.plotly_chart(make_chart("습도", "💧 습도 변화", "#1e88e5"), use_container_width=True)
        st.plotly_chart(make_chart("가스", "🔥 가스 변화", "#fb8c00"), use_container_width=True)


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
        bg = COLOR_HEX.get(color, "#757575")
        st.markdown(f"""
        <div class="class-card" style="background:{bg}; display:flex; align-items:center;">
            <div style="font-size:38px; margin-right:20px;">{medal}</div>
            <div style="flex:2;">
                <p class="cc-name">{row['반']}</p>
                <p class="cc-subject">{int(row['점수'])}점</p>
            </div>
            <div style="flex:3;">
                <p class="cc-status">{status}</p>
                <p class="cc-reason">🌡️ {row['온도']}°C · {reason}</p>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ========================================
# 페이지 4: 오늘의 시간표
# ========================================
elif page == "📅 오늘의 시간표":
    st.title("📅 오늘의 시간표")

    class_list = sorted(TIMETABLE.keys())
    selected = st.selectbox("반 선택", class_list)

    weekday = now.weekday()
    if weekday >= 5:
        st.info("🌴 주말입니다! 시간표가 없어요.")
    else:
        day = WEEKDAY_KR[weekday]
        st.subheader(f"{selected}반 · {day}요일")
        schedule = DAY_SCHEDULE[weekday]

        for name, start, end, kind in schedule:
            subject = TIMETABLE.get(selected, {}).get(day, {}).get(name, "")
            time_str = f"{start.strftime('%H:%M')} ~ {end.strftime('%H:%M')}"

            # 현재 진행 중인 시간 강조
            is_now = (start <= now.time() < end)
            highlight = "border:3px solid #ff5722; box-shadow:0 0 15px rgba(255,87,34,0.4);" if is_now else ""

            label = name
            if subject:
                label = f"{name} · {subject}"
            now_tag = " 🔴 진행중" if is_now else ""

            st.markdown(f"""
            <div class="info-card" style="{highlight}">
                <b style="color:#0d3b5e; font-size:18px;">{label}{now_tag}</b><br>
                <span style="color:#1a4a6e;">🕐 {time_str}</span>
            </div>
            """, unsafe_allow_html=True)


# ========================================
# 페이지 5: 에너지 리포트
# ========================================
elif page == "💡 에너지 리포트":
    st.title("💡 에너지 절약 리포트")
    st.caption("전체 데이터를 분석한 통계입니다.")

    if df["온도"].notna().sum() == 0:
        st.warning("아직 분석할 데이터가 부족해요.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("🌡️ 평균 온도", f"{df['온도'].mean():.1f} °C")
        c2.metric("🫁 평균 CO₂", f"{df['co2'].mean():.0f} ppm")
        c3.metric("💧 평균 습도", f"{df['습도'].mean():.1f} %")

        st.divider()

        # 반별 평균 온도 막대그래프
        st.subheader("📊 반별 평균 온도")
        avg_temp = df.groupby("반")["온도"].mean().reset_index()
        fig = px.bar(avg_temp, x="반", y="온도", color="온도",
                     color_continuous_scale="RdYlBu_r")
        fig.update_layout(
            plot_bgcolor="rgba(255,255,255,0.85)",
            paper_bgcolor="rgba(255,255,255,0)",
            font_color="#0d3b5e", height=350,
            margin=dict(l=20, r=20, t=30, b=20),
        )
        st.plotly_chart(fig, use_container_width=True)

        # 온도 분포
        st.subheader("🌡️ 온도 분포")
        fig2 = px.histogram(df, x="온도", nbins=20, color_discrete_sequence=["#42a5f5"])
        fig2.update_layout(
            plot_bgcolor="rgba(255,255,255,0.85)",
            paper_bgcolor="rgba(255,255,255,0)",
            font_color="#0d3b5e", height=300,
            margin=dict(l=20, r=20, t=30, b=20),
        )
        st.plotly_chart(fig2, use_container_width=True)


# ========================================
# 페이지 6: 시스템 정보
# ========================================
elif page == "ℹ️ 시스템 정보":
    st.title("ℹ️ 시스템 정보")

    st.markdown("""
    <div class="info-card">
    <h3>🌍 교실 에너지 모니터링 시스템</h3>
    <p>라즈베리파이 피코 + 센서로 각 교실의 환경을 실시간 측정하고,
    에너지 낭비를 감지하는 시스템입니다.</p>
    </div>
    """, unsafe_allow_html=True)

    st.subheader("📡 측정 항목")
    st.markdown("""
    - 🫁 **CO₂ 농도** (SCD30 센서) — 사람 유무 추정
    - 🌡️ **온도 / 습도** (SCD30 센서) — 냉난방 상태
    - 🔥 **가스 농도** (MQ-2 센서) — 공기질
    """)

    st.subheader("⚡ 에너지 낭비 판단 기준")
    st.markdown("""
    - 🔴 **과냉방**: 온도 22도 미만 + 사람 있음
    - 🟡 **빈 교실 냉방**: 온도 낮은데 사람 없음
    - 🔴 **이동수업 낭비**: 체육 등 이동수업인데 냉방 켜둠
    - ⚪ **냉방 안 함**: 온도 29도 이상
    - 🟢 **정상**: 22~28도
    """)

    st.subheader("🔄 데이터 흐름")
    st.markdown("""
    `피코(센서)` → `구글 시트` → `이 대시보드`
    (30초마다 자동 갱신)
    """)
