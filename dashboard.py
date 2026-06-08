import streamlit as st
import pandas as pd

# 구글 시트 CSV 주소
SHEET_CSV = "https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/export?format=csv&gid=0"

# 페이지 제목
st.title("🏫 교실 환경 모니터링 대시보드")
st.write("구글 시트의 데이터를 실시간으로 읽어옵니다.")

# 시트 읽어오기 (UTF-8로 자동 처리되어 한글 안 깨짐)
df = pd.read_csv(SHEET_CSV)

# 표로 보여주기
st.subheader("📋 수집된 데이터")
st.dataframe(df)

# 데이터가 몇 줄인지 표시
st.write("총", len(df), "개의 데이터가 있습니다.")
