import streamlit as st
import pandas as pd

# ===== 설정 =====
SHEET_CSV = "https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/export?format=csv&gid=0"

# 자동 새로고침 (30초마다). streamlit 최신 버전 기능 사용
st.set_page_config(page_title="교실 에너지 모니터링", layout="wide")

# 30초마다 자동 새로고침
st_autorefresh = st.empty()
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30 * 1000, key="refresh")
except ImportError:
    st.info("자동 새로고침 기능을 쓰려면: py -m pip install streamlit-autorefresh")


# ===== 데이터 읽기 =====
@st.cache_data(ttl=20)  # 20초간 캐시 (너무 자주 구글에 요청하지 않도록)
def load_data():
    df = pd.read_csv(SHEET_CSV)
    # 컬럼 이름 정리 (시트 첫 줄 헤더와 맞춰야 함!)
    df.columns = ["시간", "반", "co2", "온도", "습도", "가스", "조도", "상태"]
    return df

df = load_data()


# ===== 에너지 상태 판단 함수 =====
def check_status(row):
    temp = float(row["온도"])
    co2 = float(row["co2"])

    # 사람 있음 추정: CO2가 600 이상이면 사람 있다고 봄
    people = co2 >= 600

    if temp >= 29:
        return ("⚪ 냉방 안 함", "온도 높음")
    elif temp < 22:
        if not people:
            return ("🟡 빈 교실 냉방 의심", "사람 없는데 온도 낮음 (이동수업?)")
        else:
            return ("🔴 과냉방 (낭비!)", "온도 너무 낮음")
    else:
        return ("🟢 정상", "적정 온도")


# ===== 제목 =====
st.title("🏫 교실 에너지 모니터링 대시보드")


# ===== 상단: 반 선택 드롭다운 + 그래프 =====
st.header("📈 반별 상세 그래프")

class_list = sorted(df["반"].unique().tolist())
selected_class = st.selectbox("반을 선택하세요", class_list)

# 선택한 반 데이터만 추출
class_df = df[df["반"] == selected_class].copy()

st.subheader(f"{selected_class} 데이터 ({len(class_df)}개)")

# 그래프 (온도, CO2, 습도)
col1, col2 = st.columns(2)
with col1:
    st.write("🌡️ 온도 변화")
    st.line_chart(class_df.set_index("시간")["온도"])
    st.write("💧 습도 변화")
    st.line_chart(class_df.set_index("시간")["습도"])
with col2:
    st.write("🫁 CO₂ 변화")
    st.line_chart(class_df.set_index("시간")["co2"])
    st.write("💡 조도 변화")
    st.line_chart(class_df.set_index("시간")["조도"])


# ===== 하단: 모든 반 현재 상태 카드 =====
st.header("⚡ 전체 반 에너지 상태 (한눈에 보기)")
st.caption("각 반의 가장 최근 데이터를 기준으로 표시합니다.")

# 각 반의 가장 최근 데이터만 뽑기
latest = df.groupby("반").last().reset_index()

# 카드를 가로로 4개씩 배치
cards_per_row = 4
rows = [latest[i:i+cards_per_row] for i in range(0, len(latest), cards_per_row)]

for row_group in rows:
    cols = st.columns(cards_per_row)
    for idx, (_, row) in enumerate(row_group.iterrows()):
        status, reason = check_status(row)
        with cols[idx]:
            st.metric(
                label=f"{row['반']}",
                value=status,
            )
            st.caption(f"🌡️ {row['온도']}도 / 🫁 {row['co2']}")
            st.caption(reason)


# ===== 갱신 시각 표시 =====
st.divider()
st.caption("데이터는 약 20~30초마다 자동 갱신됩니다.")
