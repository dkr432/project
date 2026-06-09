import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, time as dtime

SHEET_CSV = "https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/export?format=csv&gid=0"

st.set_page_config(page_title="교실 에너지 모니터링", page_icon="🌍", layout="wide")

try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30 * 1000, key="refresh")
except ImportError:
    pass


# ========================================
# 일정 정의
# ========================================
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
DAY_SCHEDULE = {0: SCHEDULE_6, 1: SCHEDULE_7, 2: SCHEDULE_6, 3: SCHEDULE_7, 4: SCHEDULE_6}
WEEKDAY_KR = ["월", "화", "수", "목", "금", "토", "일"]


# ========================================
# 시간표
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


def get_current_slot(now):
    weekday = now.weekday()
    if weekday >= 5:
        return "주말", "weekend"
    now_t = now.time()
    schedule = DAY_SCHEDULE[weekday]
    if now_t < schedule[0][1]:
        return "등교 전", "before"
    for name, start, end, kind in schedule:
        if start <= now_t < end:
            return name, kind
    return "방과후", "after"


def get_subject(class_id, now, slot_name):
    if "교시" not in slot_name:
        return None
    weekday = now.weekday()
    if weekday >= 5:
        return None
    day = WEEKDAY_KR[weekday]
    return TIMETABLE.get(class_id, {}).get(day, {}).get(slot_name, None)


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


COLOR_HEX = {
    "green": "#2e7d32", "red": "#c62828", "gold": "#f9a825",
    "orange": "#ef6c00", "gray": "#757575",
}


# ========================================
# 에너지 점수 로직 (정교화)
# ========================================
def energy_score(class_id, df_class, now):
    """
    여러 요소를 종합해 0~100점 계산.
    - 온도 적정성 (50점): 24~26도가 만점, 멀어질수록 감점
    - 환기 적정성 (20점): CO2가 너무 높으면(환기 안함) 감점
    - 이동수업 낭비 (30점 감점): 이동수업인데 냉방 켜둠
    - 안정성: 온도 변동이 심하면 약간 감점
    """
    if df_class["온도"].notna().sum() == 0:
        return 0, {}

    latest = df_class.iloc[-1]
    temp = latest["온도"]
    co2 = latest["co2"]

    detail = {}

    # 1) 온도 점수 (50점 만점) — 24~26도 적정
    if 24 <= temp <= 26:
        temp_score = 50
    else:
        # 적정 범위에서 벗어난 만큼 감점 (1도당 8점)
        if temp < 24:
            gap = 24 - temp
        else:
            gap = temp - 26
        temp_score = max(0, 50 - gap * 8)
    detail["온도"] = round(temp_score, 1)

    # 2) 환기 점수 (20점 만점) — CO2 적정
    if co2 <= 1000:
        vent_score = 20
    elif co2 <= 1500:
        vent_score = 12
    elif co2 <= 2000:
        vent_score = 6
    else:
        vent_score = 0
    detail["환기"] = vent_score

    # 3) 기본 점수 (20점) - 측정 정상 작동
    base_score = 20
    detail["측정"] = base_score

    # 4) 이동수업 낭비 감점 (최대 -30)
    slot_name, _ = get_current_slot(now)
    subject = get_subject(class_id, now, slot_name)
    penalty = 0
    if subject in MOVING_SUBJECTS and temp < 24:
        penalty = 30
        detail["이동수업 낭비"] = -penalty

    # 5) 온도 안정성 (최대 -10) - 최근 데이터 변동성
    recent = df_class["온도"].dropna().tail(10)
    if len(recent) >= 3:
        volatility = recent.std()
        if volatility > 2:
            stab_penalty = min(10, (volatility - 2) * 5)
            detail["변동성"] = -round(stab_penalty, 1)
            penalty += stab_penalty

    total = temp_score + vent_score + base_score - penalty
    total = max(0, min(100, total))
    return round(total, 1), detail


# ========================================
# CSS (글씨 외곽선 + 회전 지구 + hover + 애니메이션 시계)
# ========================================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg, #aee2ff 0%, #cdeeff 40%, #e6f7ff 70%, #f2fbff 100%);
    background-attachment: fixed;
}

/* ===== 모든 글씨에 외곽선 (가독성!) ===== */
h1, h2, h3, h4, p, span, label, .stMarkdown, div[data-testid="stMetricValue"],
div[data-testid="stMetricLabel"], .stCaption, .stSelectbox label {
    text-shadow:
        -1px -1px 0 #ffffff, 1px -1px 0 #ffffff,
        -1px  1px 0 #ffffff, 1px  1px 0 #ffffff,
         0px  0px 4px rgba(255,255,255,0.9) !important;
}
h1, h2, h3 { color: #0a2e4d !important; }
.stMarkdown p, label { color: #103a5e !important; font-weight: 600; }

/* ===== 화면 하단 회전하는 반쪽 지구 (스크롤 고정) ===== */
.earth {
    position: fixed;
    bottom: -360px;          /* 절반만 보이게 아래로 내림 */
    left: 50%;
    transform: translateX(-50%);
    width: 700px; height: 700px;
    border-radius: 50%;
    background:
        radial-gradient(circle at 35% 30%, rgba(255,255,255,0.5) 0%, transparent 35%),
        linear-gradient(180deg, #2196f3 0%, #1976d2 100%);
    box-shadow: 0 0 80px rgba(33,150,243,0.5), inset -30px -30px 80px rgba(0,0,0,0.25);
    z-index: 0;
    pointer-events: none;
    overflow: hidden;
    animation: spinEarth 40s linear infinite;
}
/* 대륙 무늬 */
.earth::before {
    content: '';
    position: absolute; top: 18%; left: 12%;
    width: 180px; height: 120px;
    background: #43a047; border-radius: 45% 55% 60% 40%;
    box-shadow: 220px 90px 0 -10px #66bb6a,
                120px 260px 0 -5px #43a047,
                360px 200px 0 -20px #66bb6a,
                40px 380px 0 -15px #4caf50;
    opacity: 0.85;
}
.earth::after {
    content: '';
    position: absolute; bottom: 15%; right: 15%;
    width: 140px; height: 100px;
    background: #4caf50; border-radius: 50% 40% 55% 45%;
    box-shadow: -260px -40px 0 -15px #66bb6a, -100px 120px 0 -10px #43a047;
    opacity: 0.8;
}
@keyframes spinEarth {
    from { transform: translateX(-50%) rotate(0deg); }
    to   { transform: translateX(-50%) rotate(360deg); }
}

/* 구름 */
.cloud { position: fixed; z-index: 0; pointer-events: none;
         background:#fff; border-radius:100px; opacity:0.85; }
.cloud::before, .cloud::after { content:''; position:absolute; background:#fff; border-radius:50%; }
.cloud1 { width:120px;height:40px;top:12%;left:-150px; animation:drift 45s linear infinite; }
.cloud1::before{width:55px;height:55px;top:-25px;left:20px;}
.cloud1::after{width:40px;height:40px;top:-15px;left:65px;}
.cloud2 { width:90px;height:30px;top:28%;left:-150px; animation:drift 60s linear infinite; }
.cloud2::before{width:42px;height:42px;top:-20px;left:15px;}
.cloud2::after{width:32px;height:32px;top:-12px;left:50px;}
@keyframes drift { from{transform:translateX(0);} to{transform:translateX(calc(100vw + 300px));} }

.main .block-container { position: relative; z-index: 1; }

/* 사이드바 */
[data-testid="stSidebar"] { background: linear-gradient(180deg, #1565c0 0%, #0d47a1 100%); }
[data-testid="stSidebar"] * { color:#fff !important;
    text-shadow: 1px 1px 2px rgba(0,0,0,0.4) !important; }

/* ===== 애니메이션 시계 ===== */
.clock-wrap {
    display:flex; align-items:center; gap:30px;
    background: linear-gradient(135deg,#42a5f5,#1976d2);
    border-radius:30px; padding:24px 36px; margin-bottom:24px;
    box-shadow:0 12px 35px rgba(25,118,210,0.45), inset 0 2px 12px rgba(255,255,255,0.3);
    border:3px solid rgba(255,255,255,0.6);
}
.analog {
    width:110px; height:110px; border-radius:50%;
    background: radial-gradient(circle,#fff 0%,#e3f2fd 100%);
    border:6px solid #fff; position:relative; flex-shrink:0;
    box-shadow:0 4px 15px rgba(0,0,0,0.25), inset 0 0 10px rgba(0,0,0,0.1);
}
.analog .center { position:absolute; top:50%; left:50%;
    width:10px; height:10px; background:#0d47a1; border-radius:50%;
    transform:translate(-50%,-50%); z-index:5; }
.hand { position:absolute; bottom:50%; left:50%; transform-origin:bottom center;
    border-radius:10px; }
.hour { width:5px; height:28px; background:#0d47a1; margin-left:-2.5px;
    animation:spinH 43200s linear infinite; }
.minute { width:4px; height:40px; background:#1976d2; margin-left:-2px;
    animation:spinM 3600s linear infinite; }
.second { width:2px; height:45px; background:#e53935; margin-left:-1px;
    animation:spinS 60s linear infinite; }
@keyframes spinS { from{transform:rotate(0);} to{transform:rotate(360deg);} }
@keyframes spinM { from{transform:rotate(0);} to{transform:rotate(360deg);} }
@keyframes spinH { from{transform:rotate(0);} to{transform:rotate(360deg);} }
/* 시계 눈금 */
.tick { position:absolute; width:2px; height:8px; background:#90caf9; left:50%; top:4px;
    margin-left:-1px; transform-origin:50% 51px; }

.clock-digital { color:#fff; }
.clock-time { font-size:48px; font-weight:900; margin:0; letter-spacing:2px;
    text-shadow:0 2px 6px rgba(0,0,0,0.3) !important; }
.clock-date { font-size:17px; margin:2px 0 0 0; color:#e3f2fd; }
.clock-slot { display:inline-block; margin-top:10px; padding:7px 20px;
    background:rgba(255,255,255,0.95); border-radius:30px;
    font-size:18px; font-weight:800; color:#0d47a1;
    text-shadow:none !important; }

/* ===== 반별 카드 (불투명 + hover 붕) ===== */
.class-card {
    border-radius:22px; padding:20px; margin-bottom:14px; color:#fff;
    box-shadow:0 8px 24px rgba(0,0,0,0.2);
    border:3px solid rgba(255,255,255,0.6); position:relative; overflow:hidden;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.class-card:hover {
    transform: translateY(-12px) scale(1.03);
    box-shadow:0 20px 40px rgba(0,0,0,0.35);
}
.class-card::before { content:''; position:absolute; top:-30px; right:-30px;
    width:110px; height:110px; border-radius:50%; background:rgba(255,255,255,0.12); }
.class-card p { text-shadow: 1px 1px 2px rgba(0,0,0,0.4) !important; }
.cc-name { font-size:26px; font-weight:900; margin:0; }
.cc-subject { font-size:15px; opacity:0.95; margin:2px 0 10px 0; }
.cc-status { font-size:19px; font-weight:800; margin:6px 0; }
.cc-reason { font-size:13px; opacity:0.92; margin-bottom:10px; }
.cc-data { font-size:15px; font-weight:600;
    background:rgba(0,0,0,0.18); border-radius:12px; padding:8px 10px; }

.info-card {
    background:#ffffff; border-radius:20px; padding:22px;
    box-shadow:0 6px 20px rgba(0,0,0,0.1); border:2px solid #e0f0ff; margin-bottom:12px;
    transition: transform 0.3s ease, box-shadow 0.3s ease;
}
.info-card:hover { transform: translateY(-6px); box-shadow:0 14px 30px rgba(0,0,0,0.18); }
.info-card p, .info-card b, .info-card span { text-shadow:none !important; }

/* 시간표 */
.tt-table { width:100%; border-collapse:separate; border-spacing:0;
    background:#fff; border-radius:18px; overflow:hidden;
    box-shadow:0 8px 24px rgba(0,0,0,0.15); }
.tt-table th { background:linear-gradient(135deg,#1976d2,#42a5f5); color:#fff;
    padding:14px; font-size:16px; text-shadow:1px 1px 2px rgba(0,0,0,0.3) !important; }
.tt-table td { padding:14px; text-align:center; border-bottom:1px solid #e3f2fd;
    color:#0d3b5e; font-weight:600; text-shadow:none !important; }
.tt-period { background:#e3f2fd; font-weight:800; color:#0d47a1; }
.tt-now { background:#fff3e0 !important; box-shadow:inset 0 0 0 3px #ff5722; }
.tt-break td { background:#f5f5f5; color:#999; font-size:13px; }
.tt-lunch td { background:#fff8e1; color:#f57f17; font-weight:800; }
.tt-home td { background:#e8f5e9; color:#2e7d32; font-weight:800; }
</style>

<div class="earth"></div>
<div class="cloud cloud1"></div>
<div class="cloud cloud2"></div>
""", unsafe_allow_html=True)


now = datetime.now()
slot_name, slot_kind = get_current_slot(now)


# 사이드바
st.sidebar.title("🌍 에너지 모니터링")
page = st.sidebar.radio(
    "페이지 선택",
    ["🏠 대시보드 홈", "📊 반별 상세", "🏆 에너지 랭킹",
     "📅 오늘의 시간표", "💡 에너지 리포트", "🎯 프로젝트 목표"]
)
st.sidebar.divider()
st.sidebar.caption(f"총 데이터: {len(df)}개")
st.sidebar.caption(f"측정 반: {df['반'].nunique()}개")
st.sidebar.caption("⏱️ 30초마다 자동 갱신")


# ========================================
# 애니메이션 시계 HTML 생성 함수
# ========================================
def render_clock(now, slot_name, slot_kind):
    slot_icons = {"class":"📚","break":"☕","lunch":"🍱","homeroom":"📢",
                  "after":"🏠","before":"🌅","weekend":"🌴"}
    icon = slot_icons.get(slot_kind, "🕐")
    weekday_name = WEEKDAY_KR[now.weekday()]

    # 현재 시각에 맞춰 시계바늘 시작 각도 계산
    h = now.hour % 12
    m = now.minute
    s = now.second
    sec_deg = s * 6
    min_deg = m * 6 + s * 0.1
    hour_deg = h * 30 + m * 0.5

    # 눈금 12개
    ticks = "".join(
        f'<div class="tick" style="transform:rotate({i*30}deg);"></div>'
        for i in range(12)
    )

    return f"""
    <div class="clock-wrap">
        <div class="analog">
            {ticks}
            <div class="hand hour" style="animation-delay:-{hour_deg/360*43200}s;"></div>
            <div class="hand minute" style="animation-delay:-{min_deg/360*3600}s;"></div>
            <div class="hand second" style="animation-delay:-{sec_deg/360*60}s;"></div>
            <div class="center"></div>
        </div>
        <div class="clock-digital">
            <p class="clock-time">{now.strftime('%H:%M:%S')}</p>
            <p class="clock-date">{now.strftime('%Y년 %m월 %d일')} ({weekday_name}요일)</p>
            <span class="clock-slot">{icon} {slot_name}</span>
        </div>
    </div>
    """


# ========================================
# 페이지 1: 홈
# ========================================
if page == "🏠 대시보드 홈":
    st.markdown(render_clock(now, slot_name, slot_kind), unsafe_allow_html=True)
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
        fig.update_traces(line_color=color, line_width=3, marker=dict(size=7, color=color))
        fig.update_layout(
            plot_bgcolor="rgba(255,255,255,0.95)",
            paper_bgcolor="rgba(255,255,255,0.6)",
            font_color="#0a2e4d", font_size=13,
            title_font_size=18, title_font_color="#0a2e4d",
            xaxis_title="측정 순번",
            margin=dict(l=20, r=20, t=50, b=20), height=300,
        )
        fig.update_xaxes(showgrid=True, gridcolor="rgba(13,59,94,0.12)", color="#0a2e4d")
        fig.update_yaxes(showgrid=True, gridcolor="rgba(13,59,94,0.12)", color="#0a2e4d")
        return fig

    col1, col2 = st.columns(2)
    with col1:
        st.plotly_chart(make_chart("co2", "🫁 CO₂ 변화", "#e53935"), use_container_width=True)
        st.plotly_chart(make_chart("온도", "🌡️ 온도 변화", "#00897b"), use_container_width=True)
    with col2:
        st.plotly_chart(make_chart("습도", "💧 습도 변화", "#1e88e5"), use_container_width=True)
        st.plotly_chart(make_chart("가스", "🔥 가스 변화", "#fb8c00"), use_container_width=True)


# ========================================
# 페이지 3: 에너지 랭킹 (정교한 로직)
# ========================================
elif page == "🏆 에너지 랭킹":
    st.title("🏆 에너지 절약 랭킹")
    st.caption("온도 적정성(50) + 환기(20) + 측정(20) − 이동수업낭비/변동성 penalty")

    results = []
    for class_id in df["반"].unique():
        df_class = df[df["반"] == class_id].reset_index(drop=True)
        sc, detail = energy_score(class_id, df_class, now)
        latest = df_class.iloc[-1]
        results.append((class_id, sc, detail, latest))

    results.sort(key=lambda x: x[1], reverse=True)

    for idx, (class_id, sc, detail, latest) in enumerate(results):
        medal = ["🥇", "🥈", "🥉"][idx] if idx < 3 else f"{idx+1}위"
        status, reason, color = check_status(latest["온도"], latest["co2"], class_id, now)
        bg = COLOR_HEX.get(color, "#757575")

        # 점수 상세 문자열
        detail_str = " · ".join(f"{k} {v}" for k, v in detail.items())

        st.markdown(f"""
        <div class="class-card" style="background:{bg};">
            <div style="display:flex; align-items:center;">
                <div style="font-size:40px; margin-right:20px;">{medal}</div>
                <div style="flex:1;">
                    <p class="cc-name">{class_id} <span style="font-size:22px;">— {sc}점</span></p>
                    <p class="cc-status">{status}</p>
                    <p class="cc-reason">🌡️ {latest['온도']}°C · 🫁 {latest['co2']}ppm · {reason}</p>
                    <div class="cc-data">📊 {detail_str}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ========================================
# 페이지 4: 오늘의 시간표 (진짜 표)
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

        rows_html = ""
        for name, start, end, kind in schedule:
            subject = TIMETABLE.get(selected, {}).get(day, {}).get(name, "")
            time_str = f"{start.strftime('%H:%M')} ~ {end.strftime('%H:%M')}"
            is_now = (start <= now.time() < end)

            row_class = ""
            if kind == "break":
                row_class = "tt-break"
            elif kind == "lunch":
                row_class = "tt-lunch"
            elif kind == "homeroom":
                row_class = "tt-home"
            if is_now:
                row_class += " tt-now"

            now_tag = " 🔴" if is_now else ""
            display = subject if subject else name

            rows_html += f"""
            <tr class="{row_class}">
                <td class="tt-period">{name}{now_tag}</td>
                <td>{time_str}</td>
                <td>{display}</td>
            </tr>
            """

        st.markdown(f"""
        <table class="tt-table">
            <tr><th>구분</th><th>시간</th><th>과목/내용</th></tr>
            {rows_html}
        </table>
        """, unsafe_allow_html=True)


# ========================================
# 페이지 5: 에너지 리포트 (예쁜 그래프)
# ========================================
elif page == "💡 에너지 리포트":
    st.title("💡 에너지 절약 리포트")

    if df["온도"].notna().sum() == 0:
        st.warning("아직 분석할 데이터가 부족해요.")
    else:
        c1, c2, c3 = st.columns(3)
        c1.metric("🌡️ 평균 온도", f"{df['온도'].mean():.1f} °C")
        c2.metric("🫁 평균 CO₂", f"{df['co2'].mean():.0f} ppm")
        c3.metric("💧 평균 습도", f"{df['습도'].mean():.1f} %")
        st.divider()

        common_layout = dict(
            plot_bgcolor="rgba(255,255,255,0.95)",
            paper_bgcolor="rgba(255,255,255,0.6)",
            font_color="#0a2e4d", font_size=13,
            margin=dict(l=20, r=20, t=50, b=20),
        )

        st.subheader("📊 반별 평균 온도")
        avg_temp = df.groupby("반")["온도"].mean().reset_index()
        fig = px.bar(avg_temp, x="반", y="온도", color="온도",
                     color_continuous_scale="Tealrose", text_auto=".1f")
        fig.update_traces(marker_line_width=2, marker_line_color="white",
                          textfont_size=14, textposition="outside")
        fig.update_layout(height=350, title="반별 평균 온도 (°C)", **common_layout)
        fig.update_xaxes(color="#0a2e4d"); fig.update_yaxes(color="#0a2e4d")
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🌡️ 온도 분포")
            fig2 = px.histogram(df, x="온도", nbins=15,
                                color_discrete_sequence=["#42a5f5"])
            fig2.update_traces(marker_line_width=1, marker_line_color="white")
            fig2.update_layout(height=320, **common_layout)
            fig2.update_xaxes(color="#0a2e4d"); fig2.update_yaxes(color="#0a2e4d")
            st.plotly_chart(fig2, use_container_width=True)
        with col2:
            st.subheader("🫁 반별 평균 CO₂")
            avg_co2 = df.groupby("반")["co2"].mean().reset_index()
            fig3 = px.bar(avg_co2, x="반", y="co2", color="co2",
                          color_continuous_scale="Sunsetdark", text_auto=".0f")
            fig3.update_traces(marker_line_width=2, marker_line_color="white",
                               textposition="outside")
            fig3.update_layout(height=320, **common_layout)
            fig3.update_xaxes(color="#0a2e4d"); fig3.update_yaxes(color="#0a2e4d")
            st.plotly_chart(fig3, use_container_width=True)


# ========================================
# 페이지 6: 프로젝트 목표
# ========================================
elif page == "🎯 프로젝트 목표":
    st.title("🎯 프로젝트 목표")

    st.markdown("""
    <div class="info-card">
        <h3>🌍 우리의 비전</h3>
        <p>학교 교실의 에너지 낭비를 <b>실시간으로 감지</b>하고,
        모두가 한눈에 볼 수 있게 하여 <b>에너지 절약 문화</b>를 만든다!</p>
    </div>
    """, unsafe_allow_html=True)

    goals = [
        ("🔋", "에너지 낭비 감지", "이동수업·빈 교실에 냉방 켜둔 상황을 자동 감지해 낭비를 줄인다."),
        ("📊", "데이터 기반 의사결정", "감(感)이 아닌 실제 센서 데이터로 냉난방을 관리한다."),
        ("🌡️", "쾌적한 학습 환경", "적정 온도·습도·CO₂를 유지해 집중도를 높인다."),
        ("🏆", "절약 동기 부여", "반별 에너지 점수와 랭킹으로 자발적 절약을 유도한다."),
        ("🌱", "환경 보호 실천", "작은 절약이 모여 탄소 배출을 줄이고 지구를 지킨다."),
    ]
    for icon, title, desc in goals:
        st.markdown(f"""
        <div class="info-card">
            <h3>{icon} {title}</h3>
            <p>{desc}</p>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-card">
        <h3>📡 작동 원리</h3>
        <p><b>라즈베리파이 피코 + SCD30 + MQ-2 센서</b>로 교실 환경을 측정 →
        <b>구글 시트</b>에 저장 → <b>이 대시보드</b>에서 실시간 분석!
        (30초마다 자동 갱신)</p>
    </div>
    """, unsafe_allow_html=True)
