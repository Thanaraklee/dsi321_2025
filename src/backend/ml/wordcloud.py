import os, json
from dotenv import load_dotenv
from google import genai
from google.genai import types
from src.backend.ml.config_ml import instruction, prompt_template
import pandas as pd
import hashlib

# Import path configuration
from config.path_config import lakefs_s3_path_ml, lakefs_s3_path
# Import LakeFS loader
from src.backend.load.lakefs_loader import LakeFSLoader
# Import modern logging configuration
from config.logging.modern_log import LoggingConfig

logger = LoggingConfig(level="DEBUG", level_console="INFO").get_logger()

load_dotenv()

class WordCloud:
    def __init__(self):
        self.client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))
    
    def classify_messages(self, tweets_eles: list, faq_topic: str, faq_subtopic: str, issue_topic: str, issue_subtopic: str ) -> dict:
        prompt_formatted = prompt_template.format(
            faq_topic = faq_topic,
            faq_subtopic = faq_subtopic,
            issue_topic = issue_topic,
            issue_subtopic = issue_subtopic,
            messages="\n".join([f"{row['index']}: {row['tweetText']}" for row in tweets_eles]),
        )
        response = self.client.models.generate_content(
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
    
    def remove_stop_words_from_text(self, text, stop_words):
        if isinstance(text, list):
            return [word for word in text if word not in stop_words]
        elif isinstance(text, str):
            return ' '.join(word for word in text.split() if word not in stop_words)
        return text
    
    def classify(self, df: pd.DataFrame):
        df['tweetText'] = df['tweetText'].str.replace(r'#\S+', '', regex=True).str.strip()
        df.sort_values(by=['postTimeRaw'], ascending=True, inplace=True)
        df.drop_duplicates(subset="tweetText", inplace=True)
        df['index'] = df.index + 1
        df_dict:dict = df[['postTimeRaw', 'tweetText', 'index']].to_dict(orient='records')
        step = 20
        prev_stop = 0

        all_response = []
        faq_topic, faq_subtopic = set(), set()
        issue_topic, issue_subtopic = set(), set()
        
        for ind in range(step, len(df_dict) + step, step):
            start = prev_stop
            stop = ind
            prev_stop = stop
            rows = df_dict[start:stop]
            logger.info(f"Processing rows {start} to {stop}")
            
            response = self.classify_messages(tweets_eles=rows, faq_topic=faq_topic, faq_subtopic=faq_subtopic, issue_topic=issue_topic, issue_subtopic=issue_subtopic)
            
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
        logger.info(f"df.columns: {df.columns.tolist()}")
        logger.info(f"faqs_df.columns: {faqs_df.columns.tolist()}")
        faqs_df = faqs_df.merge(
            df[['index', 'tag', 'username', 'postTimeRaw', 'year', 'month', 'day']],
            how='left',
            on='index'
        )

        stop_word = list(
            set(
                word
                for tags in df['tag'].dropna()
                for word in tags.split("#")
                if word.strip() 
            )
        )


        faqs_df['topic'] = faqs_df['topic'].apply(lambda x: self.remove_stop_words_from_text(x, stop_word))
        faqs_df['subtopic'] = faqs_df['subtopic'].apply(lambda x: self.remove_stop_words_from_text(x, stop_word))
        faqs_df = faqs_df.rename(columns={
            "text": "tweetText"
            })
        faqs_df.drop(columns=['index'], inplace=True)
        return faqs_df

if __name__ == "__main__":
    word_cloud = WordCloud()
    faqs_df = word_cloud.classify()
    load_lakefs = LakeFSLoader()
    load_lakefs.load(faqs_df, lakefs_s3_path_ml, repo_name="tweets-repo-wordcloud")
