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
    ("조회", dtime(8,10), dtime(8,20), "homeroom"),
    ("1교시", dtime(8,20), dtime(9,10), "class"),
    ("쉬는시간", dtime(9,10), dtime(9,20), "break"),
    ("2교시", dtime(9,20), dtime(10,10), "class"),
    ("쉬는시간", dtime(10,10), dtime(10,20), "break"),
    ("3교시", dtime(10,20), dtime(11,10), "class"),
    ("쉬는시간", dtime(11,10), dtime(11,20), "break"),
    ("4교시", dtime(11,20), dtime(12,10), "class"),
    ("점심시간", dtime(12,10), dtime(13,10), "lunch"),
    ("5교시", dtime(13,10), dtime(14,0), "class"),
    ("쉬는시간", dtime(14,0), dtime(14,10), "break"),
    ("6교시", dtime(14,10), dtime(15,0), "class"),
    ("종례", dtime(15,0), dtime(15,10), "homeroom"),
]
SCHEDULE_7 = [
    ("조회", dtime(8,10), dtime(8,20), "homeroom"),
    ("1교시", dtime(8,20), dtime(9,10), "class"),
    ("쉬는시간", dtime(9,10), dtime(9,20), "break"),
    ("2교시", dtime(9,20), dtime(10,10), "class"),
    ("쉬는시간", dtime(10,10), dtime(10,20), "break"),
    ("3교시", dtime(10,20), dtime(11,10), "class"),
    ("쉬는시간", dtime(11,10), dtime(11,20), "break"),
    ("4교시", dtime(11,20), dtime(12,10), "class"),
    ("점심시간", dtime(12,10), dtime(13,10), "lunch"),
    ("5교시", dtime(13,10), dtime(14,0), "class"),
    ("쉬는시간", dtime(14,0), dtime(14,10), "break"),
    ("6교시", dtime(14,10), dtime(15,0), "class"),
    ("쉬는시간", dtime(15,0), dtime(15,10), "break"),
    ("7교시", dtime(15,10), dtime(16,0), "class"),
    ("종례", dtime(16,0), dtime(16,10), "homeroom"),
]
DAY_SCHEDULE = {0: SCHEDULE_6, 1: SCHEDULE_7, 2: SCHEDULE_6, 3: SCHEDULE_7, 4: SCHEDULE_6}
WEEKDAY_KR = ["월","화","수","목","금","토","일"]


TIMETABLE = {
    "2-3": {
        "월": {"1교시":"문학A","2교시":"영어B","3교시":"선택 과목","4교시":"선택 과목","5교시":"대수","6교시":"음악 연주와 창작"},
        "화": {"1교시":"선택 과목","2교시":"문학C","3교시":"합주","4교시":"선택 과목","5교시":"대수","6교시":"스포츠 생활B","7교시":"선택 과목"},
        "수": {"1교시":"영어A","2교시":"선택 과목","3교시":"선택 과목","4교시":"문학B","5교시":"선택 과목","6교시":"대수"},
        "목": {"1교시":"선택 과목","2교시":"스포츠 생활A","3교시":"선택 과목","4교시":"선택 과목","5교시":"영어A","6교시":"선택 과목","7교시":"대수"},
        "금": {"1교시":"선택 과목","2교시":"선택 과목","3교시":"영어C","4교시":"문학D","5교시":"자율","6교시":"자율"},
    },
}
MOVING_SUBJECTS = ["스포츠 생활A", "스포츠 생활B"]


# ========================================
# 시간 파싱 (★핵심: 2026. 6. 8 오전 11:10:26 형식)
# ========================================
def parse_time(t_str):
    if not isinstance(t_str, str):
        return None
    try:
        s = t_str.strip()
        # "2026. 6. 8 오전 11:10:26" -> 날짜 / 오전오후 / 시간
        date_part, ampm, time_part = None, None, None
        # 오전/오후 분리
        if "오전" in s:
            ampm = "AM"
            date_part, time_part = s.split("오전")
        elif "오후" in s:
            ampm = "PM"
            date_part, time_part = s.split("오후")
        else:
            return None
        # 날짜: "2026. 6. 8"
        y, mo, d = [int(x) for x in date_part.replace(".", " ").split()]
        # 시간: "11:10:26"
        hh, mm, ss = [int(x) for x in time_part.strip().split(":")]
        # 오전/오후 보정
        if ampm == "PM" and hh != 12:
            hh += 12
        if ampm == "AM" and hh == 12:
            hh = 0
        return datetime(y, mo, d, hh, mm, ss)
    except Exception:
        return None


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
    # 시간 파싱 컬럼 추가
    df["datetime"] = df["시간"].apply(parse_time)
    return df

df = load_data()


def is_active(last_time_str, now, threshold_min=3):
    t = parse_time(last_time_str)
    if t is None:
        return None
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


COLOR_HEX = {"green":"#2e7d32","red":"#c62828","gold":"#f9a825","orange":"#ef6c00","gray":"#757575"}


# ========================================
# 에너지 점수 로직 (오늘 하루 데이터 기반, 정교화)
# ========================================
def energy_score_today(class_id, df_class_today, now):
    """
    오늘 하루 데이터 전체를 분석해 점수 계산.
    - 온도 적정성 (40점): 오늘 평균 온도가 24~26도에 가까울수록
    - 환기 관리 (25점): 오늘 평균 CO2가 낮을수록 (환기 잘함)
    - 이동수업 절약 (20점): 이동수업 시간에 냉방 껐으면 만점, 켰으면 감점
    - 온도 안정성 (15점): 하루 온도 변동이 적을수록 (적정 유지)
    """
    detail = {}
    if df_class_today["온도"].notna().sum() == 0:
        return 0, {"데이터없음": 0}

    temps = df_class_today["온도"].dropna()
    co2s = df_class_today["co2"].dropna()

    # 1) 온도 적정성 (40점)
    avg_temp = temps.mean()
    if 24 <= avg_temp <= 26:
        t_score = 40
    else:
        gap = (24 - avg_temp) if avg_temp < 24 else (avg_temp - 26)
        t_score = max(0, 40 - gap * 7)
    detail["🌡️온도적정"] = round(t_score, 1)

    # 2) 환기 관리 (25점)
    avg_co2 = co2s.mean() if len(co2s) else 9999
    if avg_co2 <= 800:
        v_score = 25
    elif avg_co2 <= 1200:
        v_score = 18
    elif avg_co2 <= 1800:
        v_score = 10
    else:
        v_score = 3
    detail["🫁환기"] = round(v_score, 1)

    # 3) 이동수업 절약 (20점) — 오늘 이동수업 시간대 데이터 검사
    move_score = 20
    move_checked = False
    weekday = now.weekday()
    if weekday < 5:
        day = WEEKDAY_KR[weekday]
        schedule = DAY_SCHEDULE[weekday]
        for _, drow in df_class_today.iterrows():
            dt = drow["datetime"]
            if dt is None or pd.isna(drow["온도"]):
                continue
            # 그 데이터 시각의 교시/과목 찾기
            for name, start, end, kind in schedule:
                if start <= dt.time() < end and "교시" in name:
                    subj = TIMETABLE.get(class_id, {}).get(day, {}).get(name)
                    if subj in MOVING_SUBJECTS:
                        move_checked = True
                        if drow["온도"] < 24:  # 이동수업인데 냉방 켜둠
                            move_score -= 4   # 데이터마다 감점
                    break
        move_score = max(0, move_score)
    detail["🚶이동수업절약"] = round(move_score, 1)

    # 4) 온도 안정성 (15점)
    if len(temps) >= 3:
        std = temps.std()
        if std <= 1:
            s_score = 15
        elif std <= 2:
            s_score = 10
        elif std <= 3:
            s_score = 5
        else:
            s_score = 0
    else:
        s_score = 15  # 데이터 적으면 만점 처리
    detail["📉안정성"] = round(s_score, 1)

    total = t_score + v_score + move_score + s_score
    return round(max(0, min(100, total)), 1), detail


# ========================================
# CSS
# ========================================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(180deg,#9fd9ff 0%,#bfe9ff 35%,#ddf4ff 65%,#eefaff 100%);
    background-attachment: fixed;
}

/* 모든 글씨: 흰색 + 검은 외곽선 */
h1,h2,h3,h4,h5,p,span,label,li,td,th,
.stMarkdown,.stCaption,
div[data-testid="stMetricValue"],div[data-testid="stMetricLabel"],
.stSelectbox label,.stRadio label {
    color:#fff !important;
    text-shadow:-1.5px -1.5px 0 #000,1.5px -1.5px 0 #000,-1.5px 1.5px 0 #000,1.5px 1.5px 0 #000,
        -1.5px 0 0 #000,1.5px 0 0 #000,0 -1.5px 0 #000,0 1.5px 0 #000 !important;
}

/* 콘텐츠를 맨 앞으로 (z-index 높게) */
.main .block-container { position:relative; z-index:10; }

[data-testid="stSidebar"] { background:linear-gradient(180deg,#1565c0,#0d47a1); z-index:20; }

/* ===== 태양 (화면 안쪽, 얼굴 보임, 큼) ===== */
.sun-wrap { position:fixed; top:30px; right:40px;
    width:200px; height:200px; z-index:1; pointer-events:none; }
.sun-rays { position:absolute; top:50%; left:50%; width:200px; height:200px;
    margin:-100px 0 0 -100px; animation:spinRay 30s linear infinite; }
.ray { position:absolute; top:50%; left:50%;
    width:30px; height:55px; margin:-100px 0 0 -15px;
    background:#ffd23f; border:4px solid #1a1a1a; border-radius:50% 50% 0 0;
    transform-origin:50% 100%; }
.sun-core { position:absolute; top:50%; left:50%;
    width:130px; height:130px; margin:-65px 0 0 -65px; border-radius:50%;
    background:radial-gradient(circle at 38% 35%,#fff6a0 0%,#ffd23f 45%,#ffb300 100%);
    border:5px solid #1a1a1a; z-index:2; }
/* 눈 */
.sun-core::before { content:''; position:absolute; top:42px; left:34px;
    width:13px; height:19px; background:#1a1a1a; border-radius:50%;
    box-shadow:42px 0 0 #1a1a1a; }
/* 웃는 입 */
.sun-core::after { content:''; position:absolute; top:72px; left:44px;
    width:42px; height:22px; border:5px solid #1a1a1a; border-top:none;
    border-radius:0 0 50px 50px; }
@keyframes spinRay { from{transform:rotate(0);} to{transform:rotate(360deg);} }

/* ===== 지구 (하단 회전) ===== */
.earth-wrap { position:fixed; bottom:-400px; left:50%;
    width:760px; height:760px; margin-left:-380px; z-index:0; pointer-events:none; }
.earth { width:100%; height:100%; border-radius:50%;
    background:radial-gradient(circle at 38% 32%,#aee1ff 0%,#4ea8ec 45%,#1f78c4 100%);
    border:7px solid #0d3b66; position:relative; overflow:hidden;
    box-shadow:inset -40px -40px 90px rgba(0,0,30,0.35),0 0 70px rgba(78,168,236,0.6);
    animation:spinEarth 50s linear infinite; }
.continent { position:absolute; background:#5cc26b; border:5px solid #2e7d32; }
.c1 { top:14%; left:18%; width:160px; height:130px; border-radius:55% 45% 60% 40%/50% 55% 45% 50%; }
.c2 { top:42%; left:50%; width:200px; height:150px; border-radius:45% 55% 40% 60%/55% 45% 60% 40%; }
.c3 { top:60%; left:14%; width:130px; height:110px; border-radius:60% 40% 50% 50%; }
.c4 { top:8%; left:58%; width:110px; height:90px; border-radius:50% 50% 45% 55%; }
@keyframes spinEarth { from{transform:rotate(0);} to{transform:rotate(360deg);} }

/* ===== 구름 (배경 맨 뒤! z-index 0) ===== */
.cloud { position:fixed; z-index:0; pointer-events:none;
    background:#fff; border-radius:100px; opacity:0.85; border:3px solid #cfe8ff; }
.cloud::before,.cloud::after { content:''; position:absolute; background:#fff; border-radius:50%; }
.cloud::before { width:60%; height:160%; top:-55%; left:12%; }
.cloud::after { width:45%; height:130%; top:-35%; right:12%; }
@keyframes drift { from{transform:translateX(-220px);} to{transform:translateX(calc(100vw + 250px));} }
</style>

<div class="sun-wrap">
    <div class="sun-rays">
        <div class="ray" style="transform:rotate(0deg);"></div>
        <div class="ray" style="transform:rotate(45deg);"></div>
        <div class="ray" style="transform:rotate(90deg);"></div>
        <div class="ray" style="transform:rotate(135deg);"></div>
        <div class="ray" style="transform:rotate(180deg);"></div>
        <div class="ray" style="transform:rotate(225deg);"></div>
        <div class="ray" style="transform:rotate(270deg);"></div>
        <div class="ray" style="transform:rotate(315deg);"></div>
    </div>
    <div class="sun-core"></div>
</div>

<div class="earth-wrap">
    <div class="earth">
        <div class="continent c1"></div><div class="continent c2"></div>
        <div class="continent c3"></div><div class="continent c4"></div>
    </div>
</div>

<div class="cloud" style="width:130px;height:42px;top:10%;animation:drift 50s linear infinite;"></div>
<div class="cloud" style="width:90px;height:32px;top:20%;animation:drift 65s linear infinite;animation-delay:-10s;"></div>
<div class="cloud" style="width:150px;height:48px;top:30%;animation:drift 75s linear infinite;animation-delay:-25s;"></div>
<div class="cloud" style="width:100px;height:34px;top:42%;animation:drift 58s linear infinite;animation-delay:-5s;"></div>
<div class="cloud" style="width:120px;height:40px;top:55%;animation:drift 70s linear infinite;animation-delay:-35s;"></div>
<div class="cloud" style="width:80px;height:28px;top:15%;animation:drift 62s linear infinite;animation-delay:-45s;"></div>
<div class="cloud" style="width:140px;height:46px;top:65%;animation:drift 80s linear infinite;animation-delay:-15s;"></div>
""", unsafe_allow_html=True)


now = datetime.now()
slot_name, slot_kind = get_current_slot(now)


st.sidebar.title("🌍 에너지 모니터링")
page = st.sidebar.radio("페이지 선택",
    ["🏠 대시보드 홈","📊 반별 상세","🏆 에너지 랭킹","📅 오늘의 시간표","💡 에너지 리포트","🎯 프로젝트 목표"])


# 시계/카드/표 CSS
st.markdown("""
<style>
.clock-wrap{display:flex;align-items:center;gap:30px;
    background:linear-gradient(135deg,#42a5f5,#1976d2);border-radius:30px;
    padding:24px 36px;margin-bottom:24px;border:3px solid #0d3b66;
    box-shadow:0 12px 35px rgba(25,118,210,0.45);position:relative;z-index:10;}
.analog{width:110px;height:110px;border-radius:50%;
    background:radial-gradient(circle,#fff,#e3f2fd);border:6px solid #0d3b66;
    position:relative;flex-shrink:0;}
.analog .center{position:absolute;top:50%;left:50%;width:12px;height:12px;
    background:#0d47a1;border-radius:50%;transform:translate(-50%,-50%);z-index:5;border:2px solid #fff;}
.hand{position:absolute;bottom:50%;left:50%;transform-origin:bottom center;border-radius:10px;}
.hour{width:6px;height:28px;background:#0d47a1;margin-left:-3px;animation:spinH 43200s linear infinite;}
.minute{width:4px;height:40px;background:#1976d2;margin-left:-2px;animation:spinM 3600s linear infinite;}
.second{width:2px;height:45px;background:#e53935;margin-left:-1px;animation:spinS 60s linear infinite;}
@keyframes spinS{from{transform:rotate(0);}to{transform:rotate(360deg);}}
@keyframes spinM{from{transform:rotate(0);}to{transform:rotate(360deg);}}
@keyframes spinH{from{transform:rotate(0);}to{transform:rotate(360deg);}}
.tick{position:absolute;width:3px;height:9px;background:#90caf9;left:50%;top:5px;margin-left:-1.5px;transform-origin:50% 50px;}
.clock-time{font-size:48px;font-weight:900;margin:0;letter-spacing:2px;}
.clock-date{font-size:17px;margin:2px 0 0 0;}
.clock-slot{display:inline-block;margin-top:10px;padding:7px 20px;
    background:rgba(255,255,255,0.95);border-radius:30px;font-size:18px;font-weight:800;}
.clock-slot span{color:#0d47a1 !important;text-shadow:none !important;}

.class-card{border-radius:22px;padding:20px;margin-bottom:14px;
    box-shadow:0 8px 24px rgba(0,0,0,0.25);border:4px solid #0d3b66;
    position:relative;overflow:hidden;z-index:10;
    transition:transform 0.3s,box-shadow 0.3s;}
.class-card:hover{transform:translateY(-12px) scale(1.03);box-shadow:0 20px 45px rgba(0,0,0,0.4);}
.class-card::before{content:'';position:absolute;top:-30px;right:-30px;width:110px;height:110px;border-radius:50%;background:rgba(255,255,255,0.12);}
.cc-name{font-size:26px;font-weight:900;margin:0;}
.cc-subject{font-size:15px;margin:2px 0 8px 0;}
.cc-active{display:inline-block;padding:3px 12px;border-radius:20px;font-size:13px;font-weight:800;margin-bottom:8px;}
.cc-status{font-size:19px;font-weight:800;margin:6px 0;}
.cc-reason{font-size:13px;margin-bottom:10px;}
.cc-data{font-size:15px;font-weight:600;background:rgba(0,0,0,0.25);border-radius:12px;padding:8px 10px;}

.info-card{background:rgba(13,71,161,0.85);border-radius:20px;padding:22px;
    border:3px solid #0d3b66;margin-bottom:12px;z-index:10;transition:transform 0.3s;}
.info-card:hover{transform:translateY(-6px);}

.tt-table{width:100%;border-collapse:collapse;background:rgba(13,71,161,0.85);
    border-radius:14px;overflow:hidden;border:3px solid #0d3b66;}
.tt-table th{background:#0d47a1;padding:14px;border:1px solid #0d3b66;}
.tt-table td{padding:13px;text-align:center;font-weight:700;border:1px solid #2a5a9a;}
.tt-period{background:rgba(13,71,161,0.6);font-weight:900;}
.tt-now td{background:#ef6c00 !important;}
.tt-break td{background:rgba(0,0,0,0.3);font-size:13px;}
.tt-lunch td{background:rgba(245,127,23,0.6);font-weight:900;}
.tt-home td{background:rgba(46,125,50,0.6);font-weight:900;}
</style>
""", unsafe_allow_html=True)


def render_clock(now, slot_name, slot_kind):
    slot_icons={"class":"📚","break":"☕","lunch":"🍱","homeroom":"📢","after":"🏠","before":"🌅","weekend":"🌴"}
    icon=slot_icons.get(slot_kind,"🕐")
    wd=WEEKDAY_KR[now.weekday()]
    h=now.hour%12;m=now.minute;s=now.second
    sec_deg=s*6;min_deg=m*6+s*0.1;hour_deg=h*30+m*0.5
    ticks="".join(f'<div class="tick" style="transform:rotate({i*30}deg);"></div>' for i in range(12))
    return f"""<div class="clock-wrap"><div class="analog">{ticks}
        <div class="hand hour" style="animation-delay:-{hour_deg/360*43200}s;"></div>
        <div class="hand minute" style="animation-delay:-{min_deg/360*3600}s;"></div>
        <div class="hand second" style="animation-delay:-{sec_deg/360*60}s;"></div>
        <div class="center"></div></div>
        <div><p class="clock-time">{now.strftime('%H:%M:%S')}</p>
        <p class="clock-date">{now.strftime('%Y년 %m월 %d일')} ({wd}요일)</p>
        <span class="clock-slot"><span>{icon} {slot_name}</span></span></div></div>"""


# ========================================
# 페이지 1: 홈
# ========================================
if page == "🏠 대시보드 홈":
    st.markdown(render_clock(now, slot_name, slot_kind), unsafe_allow_html=True)
    st.title("🏠 전체 교실 현황")
    latest = df.groupby("반").last().reset_index()
    total = len(latest)
    waste = sum(1 for _,r in latest.iterrows() if check_status(r["온도"],r["co2"],r["반"],now)[2] in ["red","gold"])
    normal = sum(1 for _,r in latest.iterrows() if check_status(r["온도"],r["co2"],r["반"],now)[2]=="green")
    c1,c2,c3 = st.columns(3)
    c1.metric("📊 측정 중인 반", f"{total}개")
    c2.metric("🟢 정상", f"{normal}개")
    c3.metric("🔴 낭비 의심", f"{waste}개")
    st.divider()
    st.subheader("⚡ 반별 상태")
    rows=[latest[i:i+4] for i in range(0,len(latest),4)]
    for rg in rows:
        cols=st.columns(4)
        for idx,(_,row) in enumerate(rg.iterrows()):
            status,reason,color=check_status(row["온도"],row["co2"],row["반"],now)
            subject=get_subject(row["반"],now,slot_name)
            subject_text=f"📖 {subject} · {slot_name}" if subject else f"🕐 {slot_name}"
            bg=COLOR_HEX.get(color,"#757575")
            active=is_active(row["시간"],now)
            if active is True:
                ah='<span class="cc-active" style="background:#43a047;">🟢 작동함</span>'
            elif active is False:
                ah='<span class="cc-active" style="background:#c62828;">🔴 작동 안함</span>'
            else:
                ah='<span class="cc-active" style="background:#757575;">⚪ 알수없음</span>'
            with cols[idx]:
                st.markdown(f"""<div class="class-card" style="background:{bg};">
                <p class="cc-name">{row['반']}</p>
                <p class="cc-subject">{subject_text}</p>{ah}
                <p class="cc-status">{status}</p>
                <p class="cc-reason">{reason}</p>
                <div class="cc-data">🌡️ {row['온도']}°C &nbsp; 🫁 {row['co2']}ppm<br>
                💧 {row['습도']}% &nbsp; 🔥 가스 {row['가스']}</div></div>""", unsafe_allow_html=True)


# ========================================
# 페이지 2: 반별 상세 (시간축 + 범위 선택)
# ========================================
elif page == "📊 반별 상세":
    st.title("📊 반별 상세 그래프")
    cc1, cc2 = st.columns([2,1])
    with cc1:
        class_list=sorted(df["반"].unique().tolist())
        selected=st.selectbox("반을 선택하세요", class_list)
    with cc2:
        hours=st.selectbox("표시 범위", [1,3,6,12,24], index=1,
                           format_func=lambda x:f"최근 {x}시간")

    class_df=df[df["반"]==selected].copy()
    class_df=class_df[class_df["datetime"].notna()].sort_values("datetime")

    # 최근 N시간 필터 (데이터의 마지막 시각 기준)
    if len(class_df) > 0:
        last_dt = class_df["datetime"].max()
        cutoff = last_dt - timedelta(hours=hours)
        class_df = class_df[class_df["datetime"] >= cutoff]

    if len(class_df)==0:
        st.warning("해당 범위에 데이터가 없어요.")
    else:
        latest_row=class_df.iloc[-1]
        status,reason,color=check_status(latest_row["온도"],latest_row["co2"],selected,now)
        subject=get_subject(selected,now,slot_name)
        st.markdown(f"## {selected}반 — {status}")
        st.caption(f"{reason} · 현재: {subject or slot_name} · 최근 {hours}시간 / {len(class_df)}개")

        c1,c2,c3,c4=st.columns(4)
        c1.metric("🫁 CO₂", f"{latest_row['co2']} ppm")
        c2.metric("🌡️ 온도", f"{latest_row['온도']} °C")
        c3.metric("💧 습도", f"{latest_row['습도']} %")
        c4.metric("🔥 가스", f"{latest_row['가스']}")
        st.divider()

        def make_chart(y_col, title, color):
            fig=px.line(class_df, x="datetime", y=y_col, title=title, markers=True)
            fig.update_traces(line_color=color, line_width=3,
                marker=dict(size=7,color=color,line=dict(width=1.5,color="white")),
                hovertemplate="<b>%{x|%H:%M:%S}</b><br>"+y_col+": %{y}<extra></extra>")
            fig.update_layout(
                plot_bgcolor="rgba(255,255,255,0.95)",
                paper_bgcolor="rgba(13,71,161,0.55)",
                font_color="#fff", title_font_color="#fff", title_font_size=18,
                xaxis_title="시각", margin=dict(l=20,r=20,t=50,b=20), height=300,
                hoverlabel=dict(bgcolor="white", font_size=14))
            fig.update_xaxes(gridcolor="rgba(13,59,94,0.15)", color="#fff",
                tickformat="%H:%M", tickfont_color="#fff", title_font_color="#fff")
            fig.update_yaxes(gridcolor="rgba(13,59,94,0.15)", color="#fff",
                tickfont_color="#fff", title_font_color="#fff")
            return fig

        col1,col2=st.columns(2)
        with col1:
            st.plotly_chart(make_chart("co2","🫁 CO₂ 변화","#e53935"), use_container_width=True)
            st.plotly_chart(make_chart("온도","🌡️ 온도 변화","#00897b"), use_container_width=True)
        with col2:
            st.plotly_chart(make_chart("습도","💧 습도 변화","#1e88e5"), use_container_width=True)
            st.plotly_chart(make_chart("가스","🔥 가스 변화","#fb8c00"), use_container_width=True)


# ========================================
# 페이지 3: 에너지 랭킹 (오늘 하루)
# ========================================
elif page == "🏆 에너지 랭킹":
    st.title("🏆 오늘의 에너지 절약 랭킹")
    st.caption(f"📅 {now.strftime('%Y년 %m월 %d일')} 집계 (매일 0시 초기화)")
    st.caption("온도적정(40)+환기(25)+이동수업절약(20)+안정성(15) = 100점")

    # 오늘 데이터만 필터
    today = now.date()
    df_today = df[df["datetime"].notna()].copy()
    df_today = df_today[df_today["datetime"].apply(lambda d: d.date()==today)]

    if len(df_today)==0:
        st.warning("오늘 수집된 데이터가 아직 없어요.")
    else:
        results=[]
        for class_id in df_today["반"].unique():
            dc=df_today[df_today["반"]==class_id].reset_index(drop=True)
            sc,detail=energy_score_today(class_id, dc, now)
            latest=dc.iloc[-1]
            results.append((class_id,sc,detail,latest))
        results.sort(key=lambda x:x[1], reverse=True)

        for idx,(class_id,sc,detail,latest) in enumerate(results):
            medal=["🥇","🥈","🥉"][idx] if idx<3 else f"{idx+1}위"
            status,reason,color=check_status(latest["온도"],latest["co2"],class_id,now)
            bg=COLOR_HEX.get(color,"#757575")
            detail_str=" · ".join(f"{k} {v}" for k,v in detail.items())
            st.markdown(f"""<div class="class-card" style="background:{bg};">
                <div style="display:flex;align-items:center;">
                <div style="font-size:40px;margin-right:20px;">{medal}</div>
                <div style="flex:1;">
                <p class="cc-name">{class_id} — {sc}점</p>
                <p class="cc-status">{status}</p>
                <p class="cc-reason">🌡️ 현재 {latest['온도']}°C · 🫁 {latest['co2']}ppm</p>
                <div class="cc-data">{detail_str}</div>
                </div></div></div>""", unsafe_allow_html=True)


# ========================================
# 페이지 4: 시간표
# ========================================
elif page == "📅 오늘의 시간표":
    st.title("📅 오늘의 시간표")
    selected=st.selectbox("반 선택", sorted(TIMETABLE.keys()))
    weekday=now.weekday()
    if weekday>=5:
        st.info("🌴 주말입니다! 시간표가 없어요.")
    else:
        day=WEEKDAY_KR[weekday]
        st.subheader(f"{selected}반 · {day}요일")
        schedule=DAY_SCHEDULE[weekday]
        html='<table class="tt-table"><tr><th>구분</th><th>시간</th><th>과목/내용</th></tr>'
        for name,start,end,kind in schedule:
            subject=TIMETABLE.get(selected,{}).get(day,{}).get(name,"")
            time_str=f"{start.strftime('%H:%M')} ~ {end.strftime('%H:%M')}"
            is_now=(start<=now.time()<end)
            rc={"break":"tt-break","lunch":"tt-lunch","homeroom":"tt-home"}.get(kind,"")
            if is_now: rc+=" tt-now"
            tag=" 🔴" if is_now else ""
            disp=subject if subject else name
            html+=f'<tr class="{rc}"><td class="tt-period">{name}{tag}</td><td>{time_str}</td><td>{disp}</td></tr>'
        html+='</table>'
        st.markdown(html, unsafe_allow_html=True)


# ========================================
# 페이지 5: 에너지 리포트 (직관적)
# ========================================
elif page == "💡 에너지 리포트":
    st.title("💡 에너지 절약 리포트")

    df_valid = df[df["datetime"].notna() & df["온도"].notna()]
    if len(df_valid)==0:
        st.warning("아직 분석할 데이터가 부족해요.")
    else:
        c1,c2,c3=st.columns(3)
        c1.metric("🌡️ 평균 온도", f"{df_valid['온도'].mean():.1f} °C")
        c2.metric("🫁 평균 CO₂", f"{df_valid['co2'].mean():.0f} ppm")
        c3.metric("💧 평균 습도", f"{df_valid['습도'].mean():.1f} %")
        st.divider()

        layout=dict(plot_bgcolor="rgba(255,255,255,0.95)",
            paper_bgcolor="rgba(13,71,161,0.55)", font_color="#fff",
            title_font_color="#fff", margin=dict(l=20,r=20,t=60,b=20))

        # 1) 시간대별 평균 온도 (직관적: 언제 더웠나/추웠나)
        st.subheader("⏰ 시간대별 평균 온도 — 언제 냉방을 더 틀었나?")
        df_valid = df_valid.copy()
        df_valid["시각"] = df_valid["datetime"].dt.hour
        hourly = df_valid.groupby("시각")["온도"].mean().reset_index()
        fig=px.bar(hourly, x="시각", y="온도", text_auto=".1f",
            color="온도", color_continuous_scale="RdBu_r",
            labels={"시각":"시간 (시)","온도":"평균 온도(°C)"})
        fig.update_traces(marker_line_width=2, marker_line_color="#0d3b66",
            textposition="outside")
        # 적정 온도 기준선
        fig.add_hline(y=24, line_dash="dash", line_color="lime",
            annotation_text="적정 하한 24도", annotation_font_color="white")
        fig.add_hline(y=26, line_dash="dash", line_color="orange",
            annotation_text="적정 상한 26도", annotation_font_color="white")
        fig.update_layout(height=380, title="시간대별 평균 온도", **layout)
        fig.update_xaxes(color="#fff",tickfont_color="#fff",title_font_color="#fff",dtick=1)
        fig.update_yaxes(color="#fff",tickfont_color="#fff",title_font_color="#fff")
        st.plotly_chart(fig, use_container_width=True)

        col1,col2=st.columns(2)
        with col1:
            # 2) 온도 상태 비율 (도넛)
            st.subheader("🌡️ 온도 상태 비율")
            def temp_cat(t):
                if t<22: return "너무 추움(낭비)"
                elif t<=28: return "적정"
                else: return "너무 더움"
            df_valid["상태분류"]=df_valid["온도"].apply(temp_cat)
            cat=df_valid["상태분류"].value_counts().reset_index()
            cat.columns=["상태","개수"]
            fig2=px.pie(cat, names="상태", values="개수", hole=0.5,
                color="상태", color_discrete_map={
                    "적정":"#2e7d32","너무 추움(낭비)":"#1e88e5","너무 더움":"#e53935"})
            fig2.update_traces(textinfo="percent+label", textfont_color="white",
                marker=dict(line=dict(color="#0d3b66", width=3)))
            fig2.update_layout(height=350, **layout)
            st.plotly_chart(fig2, use_container_width=True)
        with col2:
            # 3) CO2 상태 비율 (환기 정도)
            st.subheader("🫁 환기 상태 비율")
            def co2_cat(c):
                if c<=1000: return "쾌적"
                elif c<=1500: return "보통"
                else: return "환기 필요"
            df_valid["환기분류"]=df_valid["co2"].apply(co2_cat)
            cat2=df_valid["환기분류"].value_counts().reset_index()
            cat2.columns=["상태","개수"]
            fig3=px.pie(cat2, names="상태", values="개수", hole=0.5,
                color="상태", color_discrete_map={
                    "쾌적":"#2e7d32","보통":"#f9a825","환기 필요":"#e53935"})
            fig3.update_traces(textinfo="percent+label", textfont_color="white",
                marker=dict(line=dict(color="#0d3b66", width=3)))
            fig3.update_layout(height=350, **layout)
            st.plotly_chart(fig3, use_container_width=True)


# ========================================
# 페이지 6: 프로젝트 목표
# ========================================
elif page == "🎯 프로젝트 목표":
    st.title("🎯 프로젝트 목표")
    st.markdown("""<div class="info-card"><h3>🌍 우리의 비전</h3>
    <p>학교 교실의 에너지 낭비를 실시간으로 감지하고, 모두가 한눈에 볼 수 있게 하여 에너지 절약 문화를 만든다!</p></div>""", unsafe_allow_html=True)
    goals=[("🔋","에너지 낭비 감지","이동수업·빈 교실에 냉방 켜둔 상황을 자동 감지해 낭비를 줄인다."),
        ("📊","데이터 기반 의사결정","감이 아닌 실제 센서 데이터로 냉난방을 관리한다."),
        ("🌡️","쾌적한 학습 환경","적정 온도·습도·CO₂를 유지해 집중도를 높인다."),
        ("🏆","절약 동기 부여","반별 에너지 점수와 랭킹으로 자발적 절약을 유도한다."),
        ("🌱","환경 보호 실천","작은 절약이 모여 탄소 배출을 줄이고 지구를 지킨다.")]
    for icon,title,desc in goals:
        st.markdown(f'<div class="info-card"><h3>{icon} {title}</h3><p>{desc}</p></div>', unsafe_allow_html=True)
    st.markdown("""<div class="info-card"><h3>📡 작동 원리</h3>
    <p>라즈베리파이 피코 + SCD30 + MQ-2 센서로 교실 환경 측정 → 구글 시트 저장 → 이 대시보드에서 실시간 분석! (30초마다 자동 갱신)</p></div>""", unsafe_allow_html=True)
