import streamlit as st 
import os
import pandas as pd 
from datetime import datetime, time, timedelta
from streamlit_echarts import st_echarts
import altair as alt

# Import config_streamlit 
from config_streamlit import random_color
# Import path configuration
from config.path_config import lakefs_s3_path, lakefs_s3_path_ml

st.set_page_config(layout="wide")


st.markdown("""
<style>
.xtitle {
    display: flex;
    flex-direction: row;
    align-items: center;
    gap: 1.2em; 
.xtitle h1 {
    margin: 0;
    font-size: 1.8rem; 
    font-weight: 700;
}
</style>
<div class="xtitle">
<svg width="40" height="40" viewBox="0 0 1200 1227" fill="none" xmlns="http://www.w3.org/2000/svg">
    <path d="M714.163 519.284L1160.89 0H1055.03L667.137 450.887L357.328 0H0L468.492 681.821L0 1226.37H105.866L515.491 750.218L842.672 1226.37H1200L714.137 519.284H714.163ZM569.165 687.828L521.697 619.934L144.011 79.6944H306.615L611.412 515.685L658.88 583.579L1055.08 1150.3H892.476L569.165 687.854V687.828Z" fill="black"/>
</svg>
<h1>Tweet Analysis</h1>
</div>
""", unsafe_allow_html=True)

if 'submitted' not in st.session_state:
    st.session_state.submitted = False
if "refresh_key" not in st.session_state:
    st.session_state.refresh_key = 0

status_topic_ml = False
status_subtopic_ml = False

def event_handler():
    st.session_state.submitted = True
    st.session_state.refresh_key += 1

@st.cache_data
def load_css(file_name):
    with open(file_name) as f:
        st.markdown(f'<style>{f.read()}</style>', unsafe_allow_html=True)

def wordcloud_generate(df: pd.DataFrame):
    def generate_options(df: pd.DataFrame) -> list[dict]:
        def remove_stopwords(word_list, stopwords):
            return [word for word in word_list if word not in stopwords]
        stop_word = list(
            set(
                word
                for tags in df['tag'].dropna()
                for word in tags.split("#")
                if word.strip() 
            )
        )
        all_filtered_df_wordcloud = filtered_df_wordcloud['subtopic'].explode().values.tolist()
        filtered_faq_all = remove_stopwords(all_filtered_df_wordcloud, stop_word)
        result = [
            {
                "name": topic, 
                "value": filtered_faq_all.count(topic),
                "textStyle": {
                    "color": random_color() 
                }
            }
            for topic in set(filtered_faq_all)
        ]
        return result
        
    all_result = generate_options(filtered_df_wordcloud)

    options_all = {
        "title": {
            "text": "Word Cloud",
            "left": "center",
            "top": "3%",  # ขยับลงเล็กน้อยจากเดิม
            "textStyle": {
                "fontSize": 26,  # ลดขนาดลงเล็กน้อยเพื่อไม่ให้แน่น
                "fontWeight": "bold"
            }
        },
        "height": "400px",
        "width": "100%",
        "tooltip": {
            "show": True,
            "formatter": "{b}: {c}"
        },
        "series": [{
            "type": 'wordCloud',
            "shape": 'circle',
            "keepAspect": False,
            "left": 'center',
            "top": '15%',  # เว้นห่างจาก title ให้มากขึ้น
            "width": '80%',
            "height": '75%',  # ไม่ให้ชนขอบล่าง
            "right": None,
            "bottom": None,
            "sizeRange": [12, 60],
            "rotationRange": [0, 0],
            "rotationStep": 0,
            "gridSize": 8,
            "drawOutOfBound": False,
            "shrinkToFit": False,
            "layoutAnimation": True,
            "textStyle": {
                "fontFamily": 'sans-serif',
                "fontWeight": 'bold',
            },
            "emphasis": {
                "focus": 'self',
            },
            "data": all_result
        }]
    }
    
    event_word_cloud_all = st_echarts(
        options=options_all,
        height="400px", 
        width="100%",
        key="word_cloud_all",
        events={"click": "function(params) { console.log(params.name); return params.name }"}
    )

    return event_word_cloud_all

def barchart_generate(df: pd.DataFrame):
    all_faq_subtopics_list = df['subtopic'].explode().values.tolist()

    all_faq_subtopics_count =pd.DataFrame(all_faq_subtopics_list)\
                .value_counts().to_frame()\
                .sort_values(by='count', ascending=False)\
                .reset_index()\
                [:10]
    all_faq_subtopics_count.columns = ['subtopic', 'count']
    chart = alt.Chart(all_faq_subtopics_count).mark_bar().encode(
        x=alt.X('count', title='Count'),
        y=alt.Y('subtopic', sort='-x', title='Topic'),
        color=alt.value('#367bbd')
    ).properties(
        width=300,
        height=400
    )

    st.altair_chart(chart)

@st.cache_data(ttl=600)
def data_from_lakefs(refresh_key: int = None, lakefs_endpoint: str = "http://lakefsdb:8000/", columns: list[str] = None):
    storage_options = {
        "key": os.getenv("ACCESS_KEY"),
        "secret": os.getenv("SECRET_KEY"),
        "client_kwargs": {
            "endpoint_url": lakefs_endpoint
        }
    }
    df = pd.read_parquet(
        lakefs_s3_path,
        columns=columns,
        storage_options=storage_options,
        engine='pyarrow',
    )
    return df

@st.cache_data(ttl=600)
def wordcloud_from_lakefs(lakefs_endpoint: str = "http://lakefsdb:8000/", columns: list[str] = None):
    storage_options = {
        "key": os.getenv("ACCESS_KEY"),
        "secret": os.getenv("SECRET_KEY"),
        "client_kwargs": {
            "endpoint_url": lakefs_endpoint
        }
    }
    df = pd.read_parquet(
        lakefs_s3_path_ml,
        columns=columns,
        storage_options=storage_options,
        engine='pyarrow',
    )
    return df

def convert_df_to_echart_option(df: pd.DataFrame):
    df = df.reset_index()
    df_sorted = df.sort_values('postTimeRaw')
    x_data = df_sorted['postTimeRaw'].dt.strftime('%Y-%m-%d %H:%M:%S').tolist()
    
    series = []
    for col in df.columns:
        if col == 'postTimeRaw':
            continue
        series.append({
            'name': col,
            'type': 'line',
            'stack': 'Total',
            'data': df_sorted[col].tolist()
        })

    option = {
        # 'title': {'text': 'Stacked Line'},
        'tooltip': {'trigger': 'axis'},
        'legend': {'data': [col for col in df.columns if col != 'postTimeRaw']},
        'grid': {
            'left': '3%',
            'right': '4%',
            'bottom': '3%',
            'containLabel': True
        },
        'toolbox': {
            'feature': {'saveAsImage': {}}
        },
        'xAxis': {
            'type': 'category',
            'boundaryGap': False,
            'data': x_data
        },
        'yAxis': {'type': 'value'},
        'series': series
    }

    return option

load_css("./src/frontend/styles/style.css")


df_tag_time = data_from_lakefs(columns=['tag', 'postTimeRaw'])
min_date = df_tag_time["postTimeRaw"].min().date()
max_date = df_tag_time["postTimeRaw"].max().date()
unique_tags = df_tag_time["tag"].unique().tolist()

with st.form("my_form"):
    selected_tags = st.multiselect("เลือก hashtag (tag):", unique_tags, default=unique_tags[0])

    start_date, end_date = st.date_input("เลือกช่วงเวลา:", [max_date, max_date], min_value=min_date, max_value=max_date)
    b1, b2 = st.columns(2)
    with b1:
        start_time = st.time_input("เลือกเวลาเริ่มต้น:", time(0, 0))
    with b2:
        end_time = st.time_input("เลือกเวลาสิ้นสุด:", time(23, 59))
    time_group = st.selectbox("เลือกช่วงเวลา Grouping", ["15min","1H", "3H", "6H", "12H", "1D", "3D"], index=3)

    submitted = st.form_submit_button("Submit", on_click=event_handler)

if st.session_state.submitted:
    # st.write(f"Selected tags: {selected_tags}")
    # st.write(f"Start date: {start_date} - End date: {end_date}")
    # st.write(f"Start time: {start_time} - End time: {end_time}")

    df = data_from_lakefs(refresh_key=st.session_state.refresh_key)

    start_datetime = datetime.combine(start_date, start_time)
    end_datetime = datetime.combine(end_date, end_time)

    filtered_df = df[
        (df["tag"].isin(selected_tags)) & 
        (df["postTimeRaw"] >= start_datetime) & 
        (df["postTimeRaw"] <= end_datetime)
    ]
    if len(filtered_df) != 0:
        df_filtered = filtered_df.set_index("postTimeRaw")
        df_grouped = df_filtered.groupby([pd.Grouper(freq=time_group), "tag"]).size().reset_index(name="count")

        df_pivot = df_grouped.pivot(index="postTimeRaw", columns="tag", values="count").fillna(0)
        dataframe_display = df_filtered.drop(columns=['index', 'year', 'month', 'day', 'scrapeTime'])
        st.dataframe(
            dataframe_display,
            column_config={
                "postTimeRaw": "Post Time",
                "category": "Category",
                "tag": "Hashtag",
                "username": "Username",
                "tweetText": "Tweet",
                "tweet_link": st.column_config.LinkColumn(label="Link")
            },
        )

        st.subheader("จำนวน Hashtag ต่อช่วงเวลา")

        option = convert_df_to_echart_option(df_pivot)
        st_echarts(options=option, height="400px")
        # st.line_chart(df_pivot)
        # a1, a2 = st.columns((6,4))
        # with a1:
        #     st.subheader("จำนวน Hashtag ต่อช่วงเวลา")
        #     st.line_chart(df_pivot)
        # with a2:
        #     st.subheader("จำนวน Hashtag ทั้งหมด")
        #     st.write(df_grouped)

        df_wordcloud = wordcloud_from_lakefs()
        # main
        filtered_df_wordcloud = df_wordcloud[
            (df_wordcloud["tag"].isin(selected_tags)) & 
            (df_wordcloud["postTimeRaw"] >= start_datetime) & 
            (df_wordcloud["postTimeRaw"] <= end_datetime)
        ]  

        if len(filtered_df_wordcloud) > 0:
            # Barchart
            barchart_generate(df=filtered_df_wordcloud)

            st.write('')
            st.write('')

            # Word Cloud
            event_word_cloud_all = wordcloud_generate(df=filtered_df_wordcloud)

            if event_word_cloud_all:

                st.subheader(f"ผลลัพธ์สำหรับ: {event_word_cloud_all}")
                
                filtered = filtered_df_wordcloud[
                    filtered_df_wordcloud['subtopic'].apply(lambda x: event_word_cloud_all in x)
                ]
                filtered = filtered[['tweetText', 'tag', 'postTimeRaw']]
                if not filtered.empty:
                    # st.write(filtered)
                    nb_columns = 3
                    cols_info = st.columns(nb_columns)
                    filtered = filtered.reset_index(drop=True)
                    df_filtered_m = df_filtered.reset_index()[['tweetText', 'tag', 'postTimeRaw', 'tweet_link']]
                    merged_df_tweet = pd.merge(
                        filtered,
                        df_filtered_m[['tweetText', 'tag', 'postTimeRaw', 'tweet_link']],
                        on=['tweetText', 'tag', 'postTimeRaw'],
                        how='left' 
                    )
                    # st.write(merged_df_tweet)
                    mid = nb_columns // 2
                    order = []
                    for i in range(nb_columns):
                        if i % 2 == 0:
                            order.append(mid + i // 2)
                        else:
                            order.append(mid - (i + 1) // 2)
                    for index, tweet in merged_df_tweet.iterrows():
                        col_index = order[index % nb_columns]
                        postTimeRaw_text = str(tweet['postTimeRaw']).strip()
                        tweetText_text = str(tweet['tweetText']).strip().replace('\n','<br>')
                        tweet_link = str(tweet['tweet_link']).strip()
                        with cols_info[col_index]:
                            st.markdown(f"""
                            <style>
                            .box {{
                                padding: 1em 1em 0 1em;
                                border-radius: 15px;
                                background-color: #FFFFFF;
                                box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                                transition: box-shadow 0.4s ease-in-out, transform 0.3s ease-in-out;
                                display: flex;
                                flex-direction: column;
                                margin: 1em;
                            }}
                            .box:hover {{
                                box-shadow: 0 12px 24px rgba(0, 0, 0, 0.2);
                                transform: translateY(-4px);
                            }}
                            .logo {{
                                padding-bottom: 1em;
                                display: flex;
                                justify-content: space-between;
                            }}
                            .info p{{
                                text-align: left;
                                padding-left: 2.5em;
                                padding-right: 2.5em;
                            }}
                            .foot p{{
                                opacity: 40%;
                                text-align: right;
                                margin-bottom: 0.7em;
                            }}
                            .xlink {{
                                color: black;
                                opacity: 40%;
                                transition: opacity 0.2s ease-in-out;
                            }}
                            .xlink:hover {{
                                color: black;
                                opacity: 70%;
                            }}
                            </style>
                            <div class="box">
                                <div class="logo">
                                    <svg width="20" height="20.7" viewBox="0 0 1200 1227" fill="none" xmlns="http://www.w3.org/2000/svg">
                                        <path d="M714.163 519.284L1160.89 0H1055.03L667.137 450.887L357.328 0H0L468.492 681.821L0 1226.37H105.866L515.491 750.218L842.672 1226.37H1200L714.137 519.284H714.163ZM569.165 687.828L521.697 619.934L144.011 79.6944H306.615L611.412 515.685L658.88 583.579L1055.08 1150.3H892.476L569.165 687.854V687.828Z" fill="black"/>
                                    </svg>
                                    <a href="{tweet_link}" class="xlink" style="color: black;">x.com</a>
                                </div>
                                <div class="info">
                                    <p>{tweetText_text}</p>
                                </div>
                                <div class="foot">
                                    <p>{postTimeRaw_text}</p>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)

    else:
        st.markdown("<h1 style='opacity: 40%;text-align: center;'>Not Found</h1>", unsafe_allow_html=True)
            
