import streamlit as st
from googleapiclient.discovery import build
import pandas as pd
import plotly.express as px
from datetime import datetime, timedelta

# 1. 페이지 설정
st.set_page_config(page_title="YouTube 트렌드 분석기", layout="wide")

# 2. 사이드바 - API 키 및 기간 설정
st.sidebar.title("⚙️ 설정")
api_key = st.sidebar.text_input("YouTube Data API Key 입력", type="password")

if not api_key:
    st.warning("👈 좌측 사이드바에 발급받으신 YouTube API 키를 입력해 주세요.")
    st.stop()

# YouTube API 클라이언트 연결
youtube = build('youtube', 'v3', developerKey=api_key)

st.sidebar.divider()

# --- 기간 설정 로직 추가 ---
st.sidebar.subheader("📅 조회 기간 설정")
period_options = {
    "최근 1일": 1,
    "최근 1주일": 7,
    "최근 1개월": 30,
    "최근 3개월": 90,
    "최근 6개월": 180,
    "최근 1년": 365
}
selected_period = st.sidebar.selectbox("기간을 선택하세요", list(period_options.keys()))
days_to_subtract = period_options[selected_period]

# YouTube API 형식(RFC 3339)에 맞게 날짜 변환
published_after = (datetime.utcnow() - timedelta(days=days_to_subtract)).isoformat() + "Z"
# -----------------------------

# 3. 메뉴 선택
st.sidebar.divider()
menu = st.sidebar.radio(
    "기능 선택",
    ["🔥 카테고리별 인기 동영상", "🔍 특정 채널 모니터링", "📈 키워드 검색 분석"]
)

# ----------------- 기능 1: 카테고리별 인기 영상 -----------------
if menu == "🔥 카테고리별 인기 동영상":
    st.title("🔥 카테고리별 인기 동영상 트렌드")
    st.info("💡 유튜브 정책상 '인기 급상승 영상'은 실시간 기준으로만 제공되어 기간 설정이 적용되지 않습니다.")
    
    categories = {
        "전체 인기": "0", "음악": "10", "게임": "20",
        "엔터테인먼트": "24", "과학/기술": "28",
        "뉴스/정치": "25", "노하우/스타일": "26"
    }
    
    selected_cat = st.selectbox("카테고리 선택", list(categories.keys()))
    cat_id = categories[selected_cat]
    
    with st.spinner("데이터 수집 중..."):
        params = {
            'part': 'snippet,statistics',
            'chart': 'mostPopular',
            'regionCode': 'KR',
            'maxResults': 20
        }
        if cat_id != "0":
            params['videoCategoryId'] = cat_id
            
        res = youtube.videos().list(**params).execute()
        
        items = []
        for v in res.get('items', []):
            items.append({
                '제목': v['snippet']['title'],
                '채널명': v['snippet']['channelTitle'],
                '조회수': int(v['statistics'].get('viewCount', 0)),
                '좋아요': int(v['statistics'].get('likeCount', 0)),
                '댓글수': int(v['statistics'].get('commentCount', 0)),
                '게시일': v['snippet']['publishedAt'][:10]
            })
        
        df = pd.DataFrame(items)
        
        if not df.empty:
            col1, col2, col3 = st.columns(3)
            col1.metric("TOP 20 평균 조회수", f"{int(df['조회수'].mean()):,}회")
            col2.metric("TOP 20 평균 좋아요", f"{int(df['좋아요'].mean()):,}개")
            col3.metric("최고 조회수 영상", f"{df['조회수'].max():,}회")
            
            st.divider()
            fig = px.bar(df.head(10), x='조회수', y='제목', orientation='h', 
                         color='좋아요', title="인기 동영상 TOP 10 (조회수 기준)",
                         hover_data=['채널명', '댓글수'])
            fig.update_layout(yaxis={'autorange': 'reversed'})
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df, use_container_width=True)

# ----------------- 기능 2: 채널 모니터링 -----------------
elif menu == "🔍 특정 채널 모니터링":
    st.title("🔍 특정 채널 상세 모니터링")
    channel_query = st.text_input("채널 이름 또는 핸들(@)을 입력하세요", "@Google")
    
    if st.button("채널 분석 시작"):
        with st.spinner(f"{selected_period} 동안의 채널 정보를 불러오는 중..."):
            search_res = youtube.search().list(
                part="snippet", q=channel_query, type="channel", maxResults=1
            ).execute()
            
            if search_res.get('items'):
                channel_id = search_res['items'][0]['snippet']['channelId']
                
                ch_res = youtube.channels().list(
                    part="snippet,statistics", id=channel_id
                ).execute()['items'][0]
                
                stats = ch_res['statistics']
                snippet = ch_res['snippet']
                
                st.subheader(f"📺 {snippet['title']}")
                c1, c2, c3 = st.columns(3)
                c1.metric("구독자 수", f"{int(stats.get('subscriberCount', 0)):,}명")
                c2.metric("총 누적 조회수", f"{int(stats.get('viewCount', 0)):,}회")
                c3.metric("총 영상 수", f"{int(stats.get('videoCount', 0)):,}개")
                
                # --- 기간 필터(publishedAfter) 적용 ---
                videos_res = youtube.search().list(
                    part="snippet",
                    channelId=channel_id,
                    order="date",
                    publishedAfter=published_after, # 기간 필터 적용
                    maxResults=15,
                    type="video"
                ).execute()
                
                v_list = []
                for v in videos_res.get('items', []):
                    v_list.append({
                        '영상 제목': v['snippet']['title'],
                        '업로드 날짜': v['snippet']['publishedAt'][:10],
                    })
                    
                st.markdown(f"### 📌 {selected_period} 동안 업로드된 영상")
                if v_list:
                    st.dataframe(pd.DataFrame(v_list), use_container_width=True)
                else:
                    st.warning(f"선택하신 '{selected_period}' 동안 업로드된 영상이 없습니다.")
            else:
                st.error("채널을 찾을 수 없습니다.")

# ----------------- 기능 3: 키워드 검색 분석 -----------------
elif menu == "📈 키워드 검색 분석":
    st.title("📈 키워드 기반 영상 트렌드 탐색")
    keyword = st.text_input("분석할 키워드를 입력하세요", "생성형 AI")
    
    if st.button("키워드 분석"):
        with st.spinner(f"{selected_period} 동안의 검색 결과를 수집 중..."):
            
            # --- 기간 필터(publishedAfter) 적용 ---
            search_res = youtube.search().list(
                part="snippet",
                q=keyword,
                type="video",
                order="viewCount", # 조회수 높은 순으로 정렬
                publishedAfter=published_after, # 기간 필터 적용
                maxResults=15
            ).execute()
            
            results = []
            for item in search_res.get('items', []):
                results.append({
                    '제목': item['snippet']['title'],
                    '채널명': item['snippet']['channelTitle'],
                    '게시일': item['snippet']['publishedAt'][:10]
                })
            
            st.markdown(f"### 🔎 {selected_period} 동안 '{keyword}' 관련 조회수 높은 영상")
            if results:
                st.dataframe(pd.DataFrame(results), use_container_width=True)
            else:
                st.warning(f"선택하신 '{selected_period}' 동안 검색된 영상이 없습니다.")
