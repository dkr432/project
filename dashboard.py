import streamlit as st
import pandas as pd

# ===== 기본 설정 =====
SHEET_CSV = "https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/export?format=csv&gid=0"

st.set_page_config(page_title="교실 에너지 모니터링", page_icon="🏫", layout="wide")

# 자동 새로고침
try:
    from streamlit_autorefresh import st_autorefresh
    st_autorefresh(interval=30 * 1000, key="refresh")
except ImportError:
    pass


# ===== 데이터 로드 =====
@st.cache_data(ttl=20)
def load_data():
    df = pd.read_csv(SHEET_CSV)
    df.columns = ["시간", "반", "co2", "온도", "습도", "가스", "조도", "상태"]
    # 숫자형으로 변환 (오류나면 NaN)
    for col in ["co2", "온도", "습도", "가스"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    return df

df = load_data()


# ===== 에너지 상태 판단 =====
def check_status(temp, co2):
    if pd.isna(temp):
        return "❓ 측정실패", "데이터 없음", "gray"
    people = co2 >= 600
    if temp >= 29:
        return "⚪ 냉방 안 함", "온도 높음", "orange"
    elif temp < 22:
        if not people:
            return "🟡 빈 교실 냉방 의심", "사람 없는데 냉방 (이동수업?)", "gold"
        else:
            return "🔴 과냉방 (낭비!)", "온도 너무 낮음", "red"
    else:
        return "🟢 정상", "적정 온도", "green"


# ===== 사이드바 메뉴 =====
st.sidebar.title("🏫 에너지 모니터링")
page = st.sidebar.radio(
    "페이지 선택",
    ["🏠 전체 현황", "📊 반별 상세", "🏆 에너지 랭킹", "📋 전체 데이터"]
)
st.sidebar.divider()
st.sidebar.caption(f"총 데이터: {len(df)}개")
st.sidebar.caption(f"측정 반: {df['반'].nunique()}개")
st.sidebar.caption("30초마다 자동 갱신")


# ========================================
# 페이지 1: 전체 현황
# ========================================
if page == "🏠 전체 현황":
    st.title("🏠 전체 교실 현황")
    st.caption("모든 반의 최신 상태를 한눈에 확인하세요.")

    # 각 반 최신 데이터
    latest = df.groupby("반").last().reset_index()

    # 상단 요약 통계
    total = len(latest)
    waste = sum(1 for _, r in latest.iterrows()
                if check_status(r["온도"], r["co2"])[2] in ["red", "gold"])
    normal = sum(1 for _, r in latest.iterrows()
                 if check_status(r["온도"], r["co2"])[2] == "green")

    c1, c2, c3 = st.columns(3)
    c1.metric("📊 측정 중인 반", f"{total}개")
    c2.metric("🟢 정상", f"{normal}개")
    c3.metric("🔴 에너지 낭비 의심", f"{waste}개")

    st.divider()

    # 반별 카드
    st.subheader("⚡ 반별 상태")
    cards_per_row = 4
    rows = [latest[i:i+cards_per_row] for i in range(0, len(latest), cards_per_row)]
    for row_group in rows:
        cols = st.columns(cards_per_row)
        for idx, (_, row) in enumerate(row_group.iterrows()):
            status, reason, color = check_status(row["온도"], row["co2"])
            with cols[idx]:
                with st.container(border=True):
                    st.markdown(f"### {row['반']}")
                    st.markdown(f"**{status}**")
                    st.caption(reason)
                    st.text(f"🌡️ {row['온도']}도  🫁 {row['co2']}ppm")
                    st.text(f"💧 {row['습도']}%  🔥 가스 {row['가스']}")


# ========================================
# 페이지 2: 반별 상세
# ========================================
elif page == "📊 반별 상세":
    st.title("📊 반별 상세 그래프")

    class_list = sorted(df["반"].unique().tolist())
    selected = st.selectbox("반을 선택하세요", class_list)

    class_df = df[df["반"] == selected].copy()

    # 현재 상태 표시
    latest_row = class_df.iloc[-1]
    status, reason, color = check_status(latest_row["온도"], latest_row["co2"])
    st.markdown(f"## {selected}반 — {status}")
    st.caption(f"{reason} · 데이터 {len(class_df)}개")

    # 최신 값 메트릭
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("🫁 CO₂", f"{latest_row['co2']} ppm")
    c2.metric("🌡️ 온도", f"{latest_row['온도']} °C")
    c3.metric("💧 습도", f"{latest_row['습도']} %")
    c4.metric("🔥 가스", f"{latest_row['가스']}")

    st.divider()

    # 그래프들
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🫁 CO₂ 변화")
        st.line_chart(class_df.set_index("시간")["co2"], color="#FF6B6B")
        st.subheader("🌡️ 온도 변화")
        st.line_chart(class_df.set_index("시간")["온도"], color="#4ECDC4")
    with col2:
        st.subheader("💧 습도 변화")
        st.line_chart(class_df.set_index("시간")["습도"], color="#45B7D1")
        st.subheader("🔥 가스 변화")
        st.line_chart(class_df.set_index("시간")["가스"], color="#FFA07A")


# ========================================
# 페이지 3: 에너지 랭킹
# ========================================
elif page == "🏆 에너지 랭킹":
    st.title("🏆 에너지 절약 랭킹")
    st.caption("온도가 적정 범위(22~28도)에 가까울수록 에너지를 잘 쓰는 거예요.")

    latest = df.groupby("반").last().reset_index()

    # 점수 계산: 적정온도(25도)에서 멀수록 감점
    def score(temp):
        if pd.isna(temp):
            return 0
        # 25도에 가까울수록 100점
        return max(0, 100 - abs(temp - 25) * 10)

    latest["점수"] = latest["온도"].apply(score)
    ranked = latest.sort_values("점수", ascending=False).reset_index(drop=True)

    # 순위 표시
    for idx, row in ranked.iterrows():
        rank = idx + 1
        medal = ["🥇", "🥈", "🥉"][idx] if idx < 3 else f"{rank}위"
        status, reason, color = check_status(row["온도"], row["co2"])
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

    # 반 필터
    class_list = ["전체"] + sorted(df["반"].unique().tolist())
    selected = st.selectbox("반 필터", class_list)

    if selected == "전체":
        view_df = df
    else:
        view_df = df[df["반"] == selected]

    st.dataframe(view_df, use_container_width=True)
    st.caption(f"총 {len(view_df)}개의 데이터")

    # CSV 다운로드 버튼
    csv = view_df.to_csv(index=False).encode("utf-8-sig")
    st.download_button("📥 CSV 다운로드", csv, "교실데이터.csv", "text/csv")
