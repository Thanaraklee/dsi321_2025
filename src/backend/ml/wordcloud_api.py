from fastapi import FastAPI
from typing import List, Optional
import os, json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from src.backend.ml.config_ml import instruction, prompt_template
import uvicorn
import pandas as pd
from src.frontend.config_streamlit import random_color

load_dotenv()

app = FastAPI()
client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

faq_topic, faq_subtopic = set(), set()
issue_topic, issue_subtopic = set(), set()

def classify_messages(
    tweets_eles: list,
    faq_topic: str = faq_topic,
    faq_subtopic: str = faq_subtopic,
    issue_topic: str = issue_topic,
    issue_subtopic: str = issue_subtopic
    ) -> dict:
    prompt_formatted = prompt_template.format(
        faq_topic = faq_topic,
        faq_subtopic = faq_subtopic,
        issue_topic = issue_topic,
        issue_subtopic = issue_subtopic,
        messages="\n".join([f"{row['index']}: {row['tweetText']}" for row in tweets_eles]),
    )
    response = client.models.generate_content(
        model="gemini-2.0-flash",
        contents=prompt_formatted,
        config=types.GenerateContentConfig(
            system_instruction=instruction,
            temperature=0.2, # low temperature for more deterministic output kub
        ),
    )
    response_text = response.text
    response_json = response_text[response_text.index("{"): response_text.rindex("}") + 1]
    response_json = response_json.replace("{{", "{").replace("}}", "}")
    response_json = json.loads(response_json, strict=False)
    return response_json

def remove_stopwords(word_list, stopwords):
    return [word for word in word_list if word not in stopwords]

@app.post("/classify/")
def classify(data_json: dict):
    df = pd.DataFrame(data_json['df'])
    df['tweetText'] = df['tweetText'].str.replace(r'#\S+', '', regex=True).str.strip()
    df['postTimeRaw'] = pd.to_datetime(df['postTimeRaw'], errors='coerce') 
    df.sort_values(by=['postTimeRaw'], ascending=True, inplace=True)
    df.drop_duplicates(subset="tweetText")
    df['index'] = df.index + 1
    df['postTimeRaw'] = df['postTimeRaw'].dt.strftime('%Y-%m-%d')
    df_dict:dict = df[['postTimeRaw', 'tweetText', 'index']].to_dict(orient='records')
    step = 50
    prev_stop = 0

    all_response = []

    for ind in range(step, len(df_dict) + step, step):
        start = prev_stop
        stop = ind
        prev_stop = stop
        rows = df_dict[start:stop]
        print(f"Processing rows {start} to {stop}")
        
        response = classify_messages(rows)
        
        # Update the set with new issues and FAQs
        for row in response['issue']:
            for topic in row['topic']:
                issue_topic.add(topic)
            for subtopic in row['subtopic']:
                issue_subtopic.add(subtopic)
        for row in response['faq']:
            for topic in row['topic']:
                faq_topic.add(topic)
            for subtopic in row['subtopic']:
                faq_subtopic.add(subtopic)
        
        all_response.append(response)
    faqs = [faq for response in all_response for faq in response['faq']]
    faqs_df = pd.DataFrame(faqs)
    stop_word = list(
        set(
            word
            for tags in df['tag'].dropna()
            for word in tags.split("#")
            if word.strip() 
        )
    )

    all_faq_topics_list = faqs_df['topic'].explode().values.tolist()
    all_faq_subtopics_list = faqs_df['subtopic'].explode().values.tolist()

    if data_json['topic']:
        filtered_faq_topics = remove_stopwords(all_faq_topics_list, stop_word)
        result = [
            {
                "name": topic, 
                "value": filtered_faq_topics.count(topic),
                "textStyle": {
                    "color": random_color() 
                }
            }
            for topic in set(filtered_faq_topics)
        ]
    else:
        filtered_faq_subtopics = remove_stopwords(all_faq_subtopics_list, stop_word)
        result = [
            {
                "name": topic, 
                "value": filtered_faq_subtopics.count(topic),
                "textStyle": {
                    "color": random_color() 
                }
            } 
            for topic in set(filtered_faq_subtopics)
        ]

    return result

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)