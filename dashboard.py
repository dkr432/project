import streamlit as st
import pandas as pd

# 구글 시트 CSV 주소
SHEET_CSV = "https://docs.google.com/spreadsheets/d/1upDHGAi-83NMU4Mo_BuE3E6MeeBoonaemNNWhLZ0i8E/export?format=csv&gid=0"

st.title("교실 환경 모니터링 대시보드")

# 시트 읽어오기 (UTF-8로 읽어서 한글 안 깨짐)
df = pd.read_csv(SHEET_CSV)

# 표로 보여주기
st.dataframe(df)
