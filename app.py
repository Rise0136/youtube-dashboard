import streamlit as st
from googleapiclient.discovery import build
import pandas as pd
import plotly.express as px

# 1. 페이지 설정
st.set_page_config(page_title="YouTube 트렌드 분석기", layout="wide")

# 2. 사이드바 - API 키 설정 (기간 설정 삭제됨)
st.sidebar.title("⚙️ 설정")
api_key = st.sidebar.text_input("YouTube Data API Key 입력", type="password")

if not api_key:
    st.warning("👈 좌측 사이드바에 발급받으신 YouTube API 키를 입력해 주세요.")
    st.stop()

# YouTube API 클라이언트 연결
youtube = build('youtube', 'v3', developerKey=api_key)

st.sidebar.divider()
menu = st.sidebar.radio(
    "기능 선택",
    ["🔥 카테고리별 인기 동영상", "🔍 특정 채널 모니터링", "📈 키워드 검색 분석"]
)

# ----------------- 기능 1: 카테고리별 인기 영상 -----------------
if menu == "🔥 카테고리별 인기 동영상":
    st.title("🔥 카테고리별 실시간 인기 동영상")
    
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
            views = int(v['statistics'].get('viewCount', 0))
            likes = int(v['statistics'].get('likeCount', 0))
            # 참여도(좋아요 비율) 계산
            engagement_rate = (likes / views * 100) if views > 0 else 0
            
            items.append({
                '제목': v['snippet']['title'],
                '채널명': v['snippet']['channelTitle'],
                '조회수': views,
                '좋아요': likes,
                '참여도(%)': round(engagement_rate, 2),
                '게시일': v['snippet']['publishedAt'][:10]
            })
        
        df = pd.DataFrame(items)
        
        if not df.empty:
            col1, col2, col3 = st.columns(3)
            col1.metric("TOP 20 평균 조회수", f"{int(df['조회수'].mean()):,}회")
            col2.metric("TOP 20 평균 좋아요", f"{int(df['좋아요'].mean()):,}개")
            col3.metric("최고 참여도(좋아요 비율)", f"{df['참여도(%)'].max()}%")
            
            st.divider()
            fig = px.bar(df.head(10), x='조회수', y='제목', orientation='h', 
                         color='참여도(%)', title="인기 동영상 TOP 10 (조회수 및 참여도)",
                         hover_data=['채널명', '좋아요'])
            fig.update_layout(yaxis={'autorange': 'reversed'})
            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df, use_container_width=True)

# ----------------- 기능 2: 채널 모니터링 -----------------
elif menu == "🔍 특정 채널 모니터링":
    st.title("🔍 특정 채널 상세 모니터링")
    channel_query = st.text_input("채널 이름 또는 핸들(@)을 입력하세요", "@Google")
    
    if st.button("채널 분석 시작"):
        with st.spinner("채널 및 최근 영상 상세 데이터를 불러오는 중..."):
            # 1. 채널 검색
            search_res = youtube.search().list(
                part="snippet", q=channel_query, type="channel", maxResults=1
            ).execute()
            
            if search_res.get('items'):
                channel_id = search_res['items'][0]['snippet']['channelId']
                
                # 2. 채널 기본 스탯
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
                
                # 3. 최근 영상 검색 (영상 ID만 먼저 추출)
                recent_search = youtube.search().list(
                    part="id", channelId=channel_id, order="date",
                    maxResults=10, type="video"
                ).execute()
                
                video_ids = [item['id']['videoId'] for item in recent_search.get('items', [])]
                
                # 4. 각 영상의 상세 지표(조회수, 좋아요 등) 수집
                if video_ids:
                    videos_res = youtube.videos().list(
                        part="snippet,statistics", id=','.join(video_ids)
                    ).execute()
                    
                    v_list = []
                    for v in videos_res.get('items', []):
                        views = int(v['statistics'].get('viewCount', 0))
                        likes = int(v['statistics'].get('likeCount', 0))
                        rate = (likes / views * 100) if views > 0 else 0
                        
                        v_list.append({
                            '영상 제목': v['snippet']['title'],
                            '조회수': views,
                            '좋아요': likes,
                            '참여도(%)': round(rate, 2),
                            '업로드 날짜': v['snippet']['publishedAt'][:10]
                        })
                        
                    st.markdown("### 📌 최근 업로드 10개 영상 상세 분석")
                    st.dataframe(pd.DataFrame(v_list), use_container_width=True)
                else:
                    st.warning("최근 업로드된 영상이 없습니다.")
            else:
                st.error("채널을 찾을 수 없습니다.")

# ----------------- 기능 3: 키워드 검색 분석 -----------------
elif menu == "📈 키워드 검색 분석":
    st.title("📈 키워드 기반 영상 상세 분석")
    keyword = st.text_input("분석할 키워드를 입력하세요", "생성형 AI")
    
    if st.button("키워드 분석"):
        with st.spinner("검색 결과 상세 데이터를 수집 중..."):
            
            # 1. 키워드로 영상 검색 (ID 추출)
            search_res = youtube.search().list(
                part="id", q=keyword, type="video", order="relevance", maxResults=15
            ).execute()
            
            video_ids = [item['id']['videoId'] for item in search_res.get('items', [])]
            
            # 2. 추출된 ID로 상세 지표 수집
            if video_ids:
                videos_res = youtube.videos().list(
                    part="snippet,statistics", id=','.join(video_ids)
                ).execute()
                
                results = []
                for v in videos_res.get('items', []):
                    views = int(v['statistics'].get('viewCount', 0))
                    likes = int(v['statistics'].get('likeCount', 0))
                    
                    results.append({
                        '제목': v['snippet']['title'],
                        '채널명': v['snippet']['channelTitle'],
                        '조회수': views,
                        '좋아요': likes,
                        '게시일': v['snippet']['publishedAt'][:10]
                    })
                
                # 조회수 기준으로 정렬하여 표시
                df_results = pd.DataFrame(results).sort_values(by="조회수", ascending=False)
                
                st.markdown(f"### 🔎 '{keyword}' 관련 상위 노출 영상 상세 지표")
                st.dataframe(df_results.reset_index(drop=True), use_container_width=True)
            else:
                st.warning("검색된 영상이 없습니다.")
