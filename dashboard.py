import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime, time as dtime, timedelta

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
# 데이터 작동 여부 판단 (마지막 데이터가 최근인지)
# ========================================
def parse_time(t_str):
    """시트 시간 문자열을 datetime으로 (실패하면 None)"""
    if not isinstance(t_str, str):
        return None
    for fmt in ["%Y. %m. %d %p %I:%M:%S", "%Y-%m-%d %H:%M:%S",
                "%Y. %m. %d %H:%M:%S", "%Y/%m/%d %H:%M:%S"]:
        try:
            return datetime.strptime(t_str.strip(), fmt)
        except (ValueError, TypeError):
            continue
    return None


def is_active(last_time_str, now, threshold_min=3):
    """마지막 측정이 threshold_min분 이내면 작동 중"""
    t = parse_time(last_time_str)
    if t is None:
        return None  # 시간 파싱 실패 → 알 수 없음
    diff = abs((now - t).total_seconds()) / 60
    return diff <= threshold_min


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


def energy_score(class_id, df_class, now):
    if df_class["온도"].notna().sum() == 0:
        return 0, {}
    latest = df_class.iloc[-1]
    temp = latest["온도"]
    co2 = latest["co2"]
    detail = {}
    if 24 <= temp <= 26:
        temp_score = 50
    else:
        gap = (24 - temp) if temp < 24 else (temp - 26)
        temp_score = max(0, 50 - gap * 8)
    detail["온도"] = round(temp_score, 1)
    if co2 <= 1000:
        vent_score = 20
    elif co2 <= 1500:
        vent_score = 12
    elif co2 <= 2000:
        vent_score = 6
    else:
        vent_score = 0
    detail["환기"] = vent_score
    base_score = 20
    detail["측정"] = base_score
    slot_name, _ = get_current_slot(now)
    subject = get_subject(class_id, now, slot_name)
    penalty = 0
    if subject in MOVING_SUBJECTS and temp < 24:
        penalty = 30
        detail["이동수업 낭비"] = -penalty
    recent = df_class["온도"].dropna().tail(10)
    if len(recent) >= 3:
        volatility = recent.std()
        if volatility > 2:
            stab_penalty = min(10, (volatility - 2) * 5)
            detail["변동성"] = -round(stab_penalty, 1)
            penalty += stab_penalty
    total = temp_score + vent_score + base_score - penalty
    return round(max(0, min(100, total)), 1), detail


# ========================================
# CSS
# ========================================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg, #9fd9ff 0%, #bfe9ff 35%, #ddf4ff 65%, #eefaff 100%);
    background-attachment: fixed;
}

/* ===== 모든 글씨: 흰 글씨 + 검은 외곽선 (그림자 X) ===== */
h1,h2,h3,h4,h5,p,span,label,li,td,th,
.stMarkdown, .stCaption,
div[data-testid="stMetricValue"], div[data-testid="stMetricLabel"],
.stSelectbox label, .stRadio label {
    color: #ffffff !important;
    text-shadow:
        -1.5px -1.5px 0 #000, 1.5px -1.5px 0 #000,
        -1.5px  1.5px 0 #000, 1.5px  1.5px 0 #000,
        -1.5px 0 0 #000, 1.5px 0 0 #000,
        0 -1.5px 0 #000, 0 1.5px 0 #000 !important;
}

.main .block-container { position: relative; z-index: 2; }

/* ===== 사이드바 ===== */
[data-testid="stSidebar"] { background: linear-gradient(180deg,#1565c0 0%,#0d47a1 100%); }

/* ========== 태양 (우상단, 갈퀴 회전) ========== */
.sun-wrap {
    position: fixed; top: -70px; right: -70px;
    width: 260px; height: 260px; z-index: 0; pointer-events: none;
}
.sun-rays {
    position: absolute; top:50%; left:50%; width:240px; height:240px;
    margin:-120px 0 0 -120px;
    animation: spinRay 30s linear infinite;
}
.ray {
    position:absolute; top:50%; left:50%;
    width:34px; height:90px; margin:-90px 0 0 -17px;
    background:#ffd23f;
    border:4px solid #1a1a1a;
    border-radius:50% 50% 0 0;
    transform-origin:50% 100%;
}
.sun-core {
    position:absolute; top:50%; left:50%;
    width:140px; height:140px; margin:-70px 0 0 -70px;
    border-radius:50%;
    background: radial-gradient(circle at 38% 35%, #fff6a0 0%, #ffd23f 45%, #ffb300 100%);
    border:5px solid #1a1a1a;
    z-index:2;
}
/* 태양 얼굴(데포르메) */
.sun-core::before {
    content:''; position:absolute; top:42px; left:34px;
    width:14px; height:20px; background:#1a1a1a; border-radius:50%;
    box-shadow:44px 0 0 #1a1a1a;
}
.sun-core::after {
    content:''; position:absolute; top:78px; left:46px;
    width:48px; height:24px;
    border:5px solid #1a1a1a; border-top:none;
    border-radius:0 0 50px 50px;
}
@keyframes spinRay { from{transform:rotate(0);} to{transform:rotate(360deg);} }

/* ========== 지구 (하단, 회전) ========== */
.earth-wrap {
    position: fixed; bottom: -380px; left:50%;
    width: 720px; height: 720px; margin-left:-360px;
    z-index: 0; pointer-events: none;
}
.earth {
    width:100%; height:100%; border-radius:50%;
    background: radial-gradient(circle at 38% 32%, #aee1ff 0%, #4ea8ec 45%, #1f78c4 100%);
    border:7px solid #0d3b66;
    position:relative; overflow:hidden;
    box-shadow: inset -40px -40px 90px rgba(0,0,30,0.35),
                0 0 70px rgba(78,168,236,0.6);
    animation: spinEarth 50s linear infinite;
}
/* 대륙들 (여러 덩어리) */
.continent {
    position:absolute; background:#5cc26b; border:5px solid #2e7d32;
}
.c1 { top:14%; left:18%; width:160px; height:130px;
      border-radius:55% 45% 60% 40%/50% 55% 45% 50%;
      box-shadow: inset -8px -8px 0 rgba(0,80,0,0.15); }
.c2 { top:42%; left:50%; width:200px; height:150px;
      border-radius:45% 55% 40% 60%/55% 45% 60% 40%;
      box-shadow: inset -8px -8px 0 rgba(0,80,0,0.15); }
.c3 { top:60%; left:14%; width:130px; height:110px;
      border-radius:60% 40% 50% 50%;
      box-shadow: inset -8px -8px 0 rgba(0,80,0,0.15); }
.c4 { top:8%; left:58%; width:110px; height:90px;
      border-radius:50% 50% 45% 55%;
      box-shadow: inset -8px -8px 0 rgba(0,80,0,0.15); }
@keyframes spinEarth { from{transform:rotate(0);} to{transform:rotate(360deg);} }

/* ========== 구름 (많이!) ========== */
.cloud { position: fixed; z-index: 1; pointer-events: none;
         background:#fff; border-radius:100px; opacity:0.9;
         border:3px solid #cfe8ff; }
.cloud::before, .cloud::after { content:''; position:absolute;
         background:#fff; border-radius:50%; }
.cloud::before { width:60%; height:160%; top:-55%; left:12%; }
.cloud::after  { width:45%; height:130%; top:-35%; right:12%; }
@keyframes drift { from{transform:translateX(-200px);} to{transform:translateX(calc(100vw + 250px));} }
</style>

<!-- 태양 -->
<div class="sun-wrap">
    <div class="sun-rays">
        <div class="ray" style="transform:rotate(0deg) translateY(-30px);"></div>
        <div class="ray" style="transform:rotate(45deg) translateY(-30px);"></div>
        <div class="ray" style="transform:rotate(90deg) translateY(-30px);"></div>
        <div class="ray" style="transform:rotate(135deg) translateY(-30px);"></div>
        <div class="ray" style="transform:rotate(180deg) translateY(-30px);"></div>
        <div class="ray" style="transform:rotate(225deg) translateY(-30px);"></div>
        <div class="ray" style="transform:rotate(270deg) translateY(-30px);"></div>
        <div class="ray" style="transform:rotate(315deg) translateY(-30px);"></div>
    </div>
    <div class="sun-core"></div>
</div>

<!-- 지구 -->
<div class="earth-wrap">
    <div class="earth">
        <div class="continent c1"></div>
        <div class="continent c2"></div>
        <div class="continent c3"></div>
        <div class="continent c4"></div>
    </div>
</div>

<!-- 구름 많이 -->
<div class="cloud" style="width:130px;height:42px;top:10%;animation:drift 50s linear infinite;animation-delay:0s;"></div>
<div class="cloud" style="width:90px;height:32px;top:18%;animation:drift 65s linear infinite;animation-delay:-10s;"></div>
<div class="cloud" style="width:150px;height:48px;top:26%;animation:drift 75s linear infinite;animation-delay:-25s;"></div>
<div class="cloud" style="width:100px;height:34px;top:34%;animation:drift 58s linear infinite;animation-delay:-5s;"></div>
<div class="cloud" style="width:120px;height:40px;top:44%;animation:drift 70s linear infinite;animation-delay:-35s;"></div>
<div class="cloud" style="width:80px;height:28px;top:14%;animation:drift 62s linear infinite;animation-delay:-45s;"></div>
<div class="cloud" style="width:140px;height:46px;top:52%;animation:drift 80s linear infinite;animation-delay:-15s;"></div>
<div class="cloud" style="width:95px;height:32px;top:8%;animation:drift 55s linear infinite;animation-delay:-30s;"></div>
<div class="cloud" style="width:110px;height:38px;top:38%;animation:drift 68s linear infinite;animation-delay:-50s;"></div>
""", unsafe_allow_html=True)


now = datetime.now()
slot_name, slot_kind = get_current_slot(now)


# 사이드바 (문구 삭제)
st.sidebar.title("🌍 에너지 모니터링")
page = st.sidebar.radio(
    "페이지 선택",
    ["🏠 대시보드 홈", "📊 반별 상세", "🏆 에너지 랭킹",
     "📅 오늘의 시간표", "💡 에너지 리포트", "🎯 프로젝트 목표"]
)


# 시계 (CSS는 위 블록과 분리해서 여기 추가)
st.markdown("""
<style>
.clock-wrap { display:flex; align-items:center; gap:30px;
    background: linear-gradient(135deg,#42a5f5,#1976d2);
    border-radius:30px; padding:24px 36px; margin-bottom:24px;
    box-shadow:0 12px 35px rgba(25,118,210,0.45), inset 0 2px 12px rgba(255,255,255,0.3);
    border:3px solid #0d3b66; position:relative; z-index:2; }
.analog { width:110px; height:110px; border-radius:50%;
    background: radial-gradient(circle,#fff 0%,#e3f2fd 100%);
    border:6px solid #0d3b66; position:relative; flex-shrink:0;
    box-shadow:0 4px 15px rgba(0,0,0,0.25); }
.analog .center { position:absolute; top:50%; left:50%; width:12px; height:12px;
    background:#0d47a1; border-radius:50%; transform:translate(-50%,-50%);
    z-index:5; border:2px solid #fff; }
.hand { position:absolute; bottom:50%; left:50%; transform-origin:bottom center; border-radius:10px; }
.hour { width:6px; height:28px; background:#0d47a1; margin-left:-3px; animation:spinH 43200s linear infinite; }
.minute { width:4px; height:40px; background:#1976d2; margin-left:-2px; animation:spinM 3600s linear infinite; }
.second { width:2px; height:45px; background:#e53935; margin-left:-1px; animation:spinS 60s linear infinite; }
@keyframes spinS { from{transform:rotate(0);} to{transform:rotate(360deg);} }
@keyframes spinM { from{transform:rotate(0);} to{transform:rotate(360deg);} }
@keyframes spinH { from{transform:rotate(0);} to{transform:rotate(360deg);} }
.tick { position:absolute; width:3px; height:9px; background:#90caf9; left:50%; top:5px;
    margin-left:-1.5px; transform-origin:50% 50px; }
.clock-time { font-size:48px; font-weight:900; margin:0; letter-spacing:2px; }
.clock-date { font-size:17px; margin:2px 0 0 0; }
.clock-slot { display:inline-block; margin-top:10px; padding:7px 20px;
    background:rgba(255,255,255,0.95); border-radius:30px;
    font-size:18px; font-weight:800; }
.clock-slot span { color:#0d47a1 !important; text-shadow:none !important; }

/* 카드 */
.class-card { border-radius:22px; padding:20px; margin-bottom:14px;
    box-shadow:0 8px 24px rgba(0,0,0,0.25); border:4px solid #0d3b66;
    position:relative; overflow:hidden; z-index:2;
    transition: transform 0.3s ease, box-shadow 0.3s ease; }
.class-card:hover { transform: translateY(-12px) scale(1.03);
    box-shadow:0 20px 45px rgba(0,0,0,0.4); }
.class-card::before { content:''; position:absolute; top:-30px; right:-30px;
    width:110px; height:110px; border-radius:50%; background:rgba(255,255,255,0.12); }
.cc-name { font-size:26px; font-weight:900; margin:0; }
.cc-subject { font-size:15px; margin:2px 0 8px 0; }
.cc-active { display:inline-block; padding:3px 12px; border-radius:20px;
    font-size:13px; font-weight:800; margin-bottom:8px; }
.cc-status { font-size:19px; font-weight:800; margin:6px 0; }
.cc-reason { font-size:13px; margin-bottom:10px; }
.cc-data { font-size:15px; font-weight:600;
    background:rgba(0,0,0,0.25); border-radius:12px; padding:8px 10px; }

.info-card { background:rgba(13,71,161,0.85); border-radius:20px; padding:22px;
    box-shadow:0 6px 20px rgba(0,0,0,0.2); border:3px solid #0d3b66; margin-bottom:12px; z-index:2;
    transition: transform 0.3s ease; }
.info-card:hover { transform: translateY(-6px); }

/* 시간표 */
.tt-table { width:100%; border-collapse:collapse;
    background:rgba(13,71,161,0.8); border-radius:14px; overflow:hidden;
    box-shadow:0 8px 24px rgba(0,0,0,0.25); border:3px solid #0d3b66; }
.tt-table th { background:#0d47a1; padding:14px; font-size:16px; border:1px solid #0d3b66; }
.tt-table td { padding:13px; text-align:center; font-weight:700; border:1px solid #2a5a9a; }
.tt-period { background:rgba(13,71,161,0.6); font-weight:900; }
.tt-now td { background:#ef6c00 !important; }
.tt-break td { background:rgba(0,0,0,0.25); font-size:13px; }
.tt-lunch td { background:rgba(245,127,23,0.6); font-weight:900; }
.tt-home td { background:rgba(46,125,50,0.6); font-weight:900; }
</style>
""", unsafe_allow_html=True)


def render_clock(now, slot_name, slot_kind):
    slot_icons = {"class":"📚","break":"☕","lunch":"🍱","homeroom":"📢",
                  "after":"🏠","before":"🌅","weekend":"🌴"}
    icon = slot_icons.get(slot_kind, "🕐")
    weekday_name = WEEKDAY_KR[now.weekday()]
    h = now.hour % 12; m = now.minute; s = now.second
    sec_deg = s * 6
    min_deg = m * 6 + s * 0.1
    hour_deg = h * 30 + m * 0.5
    ticks = "".join(f'<div class="tick" style="transform:rotate({i*30}deg);"></div>' for i in range(12))
    return f"""
    <div class="clock-wrap">
        <div class="analog">
            {ticks}
            <div class="hand hour" style="animation-delay:-{hour_deg/360*43200}s;"></div>
            <div class="hand minute" style="animation-delay:-{min_deg/360*3600}s;"></div>
            <div class="hand second" style="animation-delay:-{sec_deg/360*60}s;"></div>
            <div class="center"></div>
        </div>
        <div>
            <p class="clock-time">{now.strftime('%H:%M:%S')}</p>
            <p class="clock-date">{now.strftime('%Y년 %m월 %d일')} ({weekday_name}요일)</p>
            <span class="clock-slot"><span>{icon} {slot_name}</span></span>
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

            # 작동 여부
            active = is_active(row["시간"], now)
            if active is True:
                active_html = '<span class="cc-active" style="background:#43a047;">🟢 작동함</span>'
            elif active is False:
                active_html = '<span class="cc-active" style="background:#c62828;">🔴 작동 안함</span>'
            else:
                active_html = '<span class="cc-active" style="background:#757575;">⚪ 알수없음</span>'

            with cols[idx]:
                st.markdown(f"""
                <div class="class-card" style="background:{bg};">
                    <p class="cc-name">{row['반']}</p>
                    <p class="cc-subject">{subject_text}</p>
                    {active_html}
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
        fig.update_traces(line_color=color, line_width=4, marker=dict(size=8, color=color,
                          line=dict(width=2, color="white")))
        fig.update_layout(
            plot_bgcolor="rgba(255,255,255,0.92)",
            paper_bgcolor="rgba(13,71,161,0.55)",
            font_color="#ffffff", font_size=14,
            title_font_size=18, title_font_color="#ffffff",
            xaxis_title="측정 순번",
            margin=dict(l=20, r=20, t=50, b=20), height=300,
        )
        fig.update_xaxes(showgrid=True, gridcolor="rgba(13,59,94,0.15)",
                         color="#ffffff", title_font_color="#ffffff", tickfont_color="#ffffff")
        fig.update_yaxes(showgrid=True, gridcolor="rgba(13,59,94,0.15)",
                         color="#ffffff", title_font_color="#ffffff", tickfont_color="#ffffff")
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
    st.caption("온도 적정성(50) + 환기(20) + 측정(20) − 이동수업낭비/변동성")

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
        detail_str = " · ".join(f"{k} {v}" for k, v in detail.items())
        st.markdown(f"""
        <div class="class-card" style="background:{bg};">
            <div style="display:flex; align-items:center;">
                <div style="font-size:40px; margin-right:20px;">{medal}</div>
                <div style="flex:1;">
                    <p class="cc-name">{class_id} — {sc}점</p>
                    <p class="cc-status">{status}</p>
                    <p class="cc-reason">🌡️ {latest['온도']}°C · 🫁 {latest['co2']}ppm · {reason}</p>
                    <div class="cc-data">📊 {detail_str}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ========================================
# 페이지 4: 오늘의 시간표 (오류 수정 - 줄별 출력)
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

        # HTML을 한 문자열로 완성 (줄바꿈/공백 최소화가 핵심)
        html = '<table class="tt-table"><tr><th>구분</th><th>시간</th><th>과목/내용</th></tr>'
        for name, start, end, kind in schedule:
            subject = TIMETABLE.get(selected, {}).get(day, {}).get(name, "")
            time_str = f"{start.strftime('%H:%M')} ~ {end.strftime('%H:%M')}"
            is_now = (start <= now.time() < end)
            row_class = {"break":"tt-break","lunch":"tt-lunch","homeroom":"tt-home"}.get(kind, "")
            if is_now:
                row_class += " tt-now"
            now_tag = " 🔴" if is_now else ""
            display = subject if subject else name
            html += f'<tr class="{row_class}"><td class="tt-period">{name}{now_tag}</td><td>{time_str}</td><td>{display}</td></tr>'
        html += '</table>'

        st.markdown(html, unsafe_allow_html=True)


# ========================================
# 페이지 5: 에너지 리포트
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

        layout = dict(
            plot_bgcolor="rgba(255,255,255,0.92)",
            paper_bgcolor="rgba(13,71,161,0.55)",
            font_color="#ffffff", font_size=13,
            title_font_color="#ffffff",
            margin=dict(l=20, r=20, t=50, b=20),
        )

        st.subheader("📊 반별 평균 온도")
        avg_temp = df.groupby("반")["온도"].mean().reset_index()
        fig = px.bar(avg_temp, x="반", y="온도", color="온도",
                     color_continuous_scale="Tealrose", text_auto=".1f")
        fig.update_traces(marker_line_width=3, marker_line_color="#0d3b66",
                          textfont_size=15, textposition="outside")
        fig.update_layout(height=350, title="반별 평균 온도 (°C)", **layout)
        fig.update_xaxes(color="#fff", tickfont_color="#fff", title_font_color="#fff")
        fig.update_yaxes(color="#fff", tickfont_color="#fff", title_font_color="#fff")
        st.plotly_chart(fig, use_container_width=True)

        col1, col2 = st.columns(2)
        with col1:
            st.subheader("🌡️ 온도 분포")
            fig2 = px.histogram(df, x="온도", nbins=15, color_discrete_sequence=["#42a5f5"])
            fig2.update_traces(marker_line_width=2, marker_line_color="#0d3b66")
            fig2.update_layout(height=320, **layout)
            fig2.update_xaxes(color="#fff", tickfont_color="#fff", title_font_color="#fff")
            fig2.update_yaxes(color="#fff", tickfont_color="#fff", title_font_color="#fff")
            st.plotly_chart(fig2, use_container_width=True)
        with col2:
            st.subheader("🫁 반별 평균 CO₂")
            avg_co2 = df.groupby("반")["co2"].mean().reset_index()
            fig3 = px.bar(avg_co2, x="반", y="co2", color="co2",
                          color_continuous_scale="Sunsetdark", text_auto=".0f")
            fig3.update_traces(marker_line_width=3, marker_line_color="#0d3b66",
                               textposition="outside")
            fig3.update_layout(height=320, **layout)
            fig3.update_xaxes(color="#fff", tickfont_color="#fff", title_font_color="#fff")
            fig3.update_yaxes(color="#fff", tickfont_color="#fff", title_font_color="#fff")
            st.plotly_chart(fig3, use_container_width=True)


# ========================================
# 페이지 6: 프로젝트 목표
# ========================================
elif page == "🎯 프로젝트 목표":
    st.title("🎯 프로젝트 목표")
    st.markdown("""
    <div class="info-card"><h3>🌍 우리의 비전</h3>
    <p>학교 교실의 에너지 낭비를 실시간으로 감지하고, 모두가 한눈에 볼 수 있게 하여 에너지 절약 문화를 만든다!</p></div>
    """, unsafe_allow_html=True)

    goals = [
        ("🔋", "에너지 낭비 감지", "이동수업·빈 교실에 냉방 켜둔 상황을 자동 감지해 낭비를 줄인다."),
        ("📊", "데이터 기반 의사결정", "감이 아닌 실제 센서 데이터로 냉난방을 관리한다."),
        ("🌡️", "쾌적한 학습 환경", "적정 온도·습도·CO₂를 유지해 집중도를 높인다."),
        ("🏆", "절약 동기 부여", "반별 에너지 점수와 랭킹으로 자발적 절약을 유도한다."),
        ("🌱", "환경 보호 실천", "작은 절약이 모여 탄소 배출을 줄이고 지구를 지킨다."),
    ]
    for icon, title, desc in goals:
        st.markdown(f"""
        <div class="info-card"><h3>{icon} {title}</h3><p>{desc}</p></div>
        """, unsafe_allow_html=True)

    st.markdown("""
    <div class="info-card"><h3>📡 작동 원리</h3>
    <p>라즈베리파이 피코 + SCD30 + MQ-2 센서로 교실 환경 측정 → 구글 시트 저장 → 이 대시보드에서 실시간 분석! (30초마다 자동 갱신)</p></div>
    """, unsafe_allow_html=True)
