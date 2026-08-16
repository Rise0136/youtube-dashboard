import streamlit as st
from googleapiclient.discovery import build
import pandas as pd
import plotly.express as px

st.set_page_config(page_title="YouTube 트렌드 분석기", layout="wide")

st.sidebar.title("⚙️ 설정")
api_key = st.sidebar.text_input("YouTube Data API Key 입력", type="password")

if not api_key:
    st.warning("👈 좌측 사이드바에 API 키를 입력해 주세요.")
    st.stop()

youtube = build('youtube', 'v3', developerKey=api_key)
st.sidebar.divider()

st.sidebar.subheader("🤖 특수 필터")
st.sidebar.info("유튜브 정책상 타인 영상의 '공식 AI 라벨'은 API로 수집이 차단되어 있습니다. 따라서 제목과 설명란의 텍스트를 정밀 분석하여 AI 영상을 추정합니다.")
ai_filter = st.sidebar.checkbox("AI 추정 콘텐츠만 보기")

st.sidebar.divider()
menu = st.sidebar.radio("기능 선택", ["🔥 카테고리별 인기 동영상", "🔍 특정 채널 모니터링", "📈 키워드 검색 분석"])

# --- AI 탐지 로직 강화 ---
# 키워드 대폭 확장 (프로그램 이름, AI 마크 관련 문구 등)
AI_KEYWORDS = [
    'ai', '인공지능', '생성형', '챗gpt', 'chatgpt', '합성', 'cover', '딥페이크',
    'suno', 'midjourney', 'vrew', 'elevenlabs', 'runway', 'sora', 
    'ai로 만든', 'ai 생성', 'ai generated', 'synthetic', '가상인간', '버추얼'
]

def is_ai_content(video_item):
    # 1. API가 만약 채널 주인 권한이라 값을 준다면 확인 (일반적으론 안 잡힘)
    has_ai_label = video_item.get('status', {}).get('containsSyntheticMedia', False)
    
    # 2. 제목과 '설명란(Description)' 동시 확인으로 탐지율 대폭 상승
    title = video_item['snippet'].get('title', '').lower()
    description = video_item['snippet'].get('description', '').lower()
    
    has_ai_keyword = any(kw in title or kw in description for kw in AI_KEYWORDS)
    return has_ai_label or has_ai_keyword
# -------------------------

if menu == "🔥 카테고리별 인기 동영상":
    st.title("🔥 카테고리별 실시간 인기 동영상")
    categories = {"전체 인기": "0", "음악": "10", "게임": "20", "엔터테인먼트": "24", "과학/기술": "28", "뉴스/정치": "25"}
    selected_cat = st.selectbox("카테고리 선택", list(categories.keys()))
    
    with st.spinner("데이터 수집 중..."):
        params = {'part': 'snippet,statistics,status', 'chart': 'mostPopular', 'regionCode': 'KR', 'maxResults': 50}
        if categories[selected_cat] != "0":
            params['videoCategoryId'] = categories[selected_cat]
            
        res = youtube.videos().list(**params).execute()
        
        items = []
        for v in res.get('items', []):
            if ai_filter and not is_ai_content(v):
                continue
                
            views = int(v['statistics'].get('viewCount', 0))
            likes = int(v['statistics'].get('likeCount', 0))
            ai_status = "🤖 AI/합성" if is_ai_content(v) else "일반"
            
            items.append({
                '분류': ai_status,
                '제목': v['snippet']['title'],
                '영상 링크': f"https://www.youtube.com/watch?v={v['id']}",
                '채널명': v['snippet']['channelTitle'],
                '조회수': views,
                '좋아요': likes
            })
        
        df = pd.DataFrame(items)
        if not df.empty:
            st.dataframe(df, column_config={"영상 링크": st.column_config.LinkColumn("바로가기", display_text="🔗 보러가기")}, use_container_width=True)
        else:
            st.warning("조건에 맞는 인기 영상이 없습니다.")

elif menu == "🔍 특정 채널 모니터링":
    st.title("🔍 특정 채널 상세 모니터링")
    channel_query = st.text_input("채널 이름 입력", "@Google")
    if st.button("분석 시작"):
        with st.spinner("데이터를 불러오는 중..."):
            search_res = youtube.search().list(part="snippet", q=channel_query, type="channel", maxResults=1).execute()
            if search_res.get('items'):
                channel_id = search_res['items'][0]['snippet']['channelId']
                
                recent_search = youtube.search().list(part="id", channelId=channel_id, order="date", maxResults=20, type="video").execute()
                video_ids = [item['id']['videoId'] for item in recent_search.get('items', [])]
                
                if video_ids:
                    videos_res = youtube.videos().list(part="snippet,statistics,status", id=','.join(video_ids)).execute()
                    
                    v_list = []
                    for v in videos_res.get('items', []):
                        if ai_filter and not is_ai_content(v):
                            continue
                            
                        views = int(v['statistics'].get('viewCount', 0))
                        likes = int(v['statistics'].get('likeCount', 0))
                        ai_status = "🤖 AI/합성" if is_ai_content(v) else "일반"
                        
                        v_list.append({
                            '분류': ai_status,
                            '영상 제목': v['snippet']['title'],
                            '영상 링크': f"https://www.youtube.com/watch?v={v['id']}",
                            '조회수': views,
                            '좋아요': likes
                        })
                        
                    if v_list:
                        st.dataframe(pd.DataFrame(v_list), column_config={"영상 링크": st.column_config.LinkColumn("바로가기", display_text="🔗 보러가기")}, use_container_width=True)
                    else:
                        st.warning("조건에 맞는 영상이 없습니다.")

elif menu == "📈 키워드 검색 분석":
    st.title("📈 키워드 기반 영상 분석")
    keyword = st.text_input("분석할 키워드를 입력하세요", "스마트폰 리뷰")
    if st.button("분석 시작"):
        with st.spinner("데이터를 수집 중..."):
            search_res = youtube.search().list(part="id", q=keyword, type="video", order="relevance", maxResults=30).execute()
            video_ids = [item['id']['videoId'] for item in search_res.get('items', [])]
            
            if video_ids:
                videos_res = youtube.videos().list(part="snippet,statistics,status", id=','.join(video_ids)).execute()
                
                results = []
                for v in videos_res.get('items', []):
                    if ai_filter and not is_ai_content(v):
                        continue
                        
                    views = int(v['statistics'].get('viewCount', 0))
                    likes = int(v['statistics'].get('likeCount', 0))
                    ai_status = "🤖 AI/합성" if is_ai_content(v) else "일반"
                    
                    results.append({
                        '분류': ai_status,
                        '제목': v['snippet']['title'],
                        '영상 링크': f"https://www.youtube.com/watch?v={v['id']}",
                        '채널명': v['snippet']['channelTitle'],
                        '조회수': views,
                        '좋아요': likes
                    })
                
                if results:
                    df_results = pd.DataFrame(results).sort_values(by="조회수", ascending=False)
                    st.dataframe(df_results.reset_index(drop=True), column_config={"영상 링크": st.column_config.LinkColumn("바로가기", display_text="🔗 보러가기")}, use_container_width=True)
                else:
                    st.warning("조건에 맞는 결과가 없습니다.")
