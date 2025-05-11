import streamlit as st 
import os
import pandas as pd 

# Import path configuration
from config.path_config import lakefs_s3_path


st.title('Tweet Sentiment Analysis')

def data_from_lakefs(lakefs_endpoint: str = "http://localhost:8001/"):
    storage_options = {
        "key": os.getenv("ACCESS_KEY"),
        "secret": os.getenv("SECRET_KEY"),
        "client_kwargs": {
            "endpoint_url": lakefs_endpoint
        }
    }
    df = pd.read_parquet(
        lakefs_s3_path,
        storage_options=storage_options,
        engine='pyarrow',
    )
    return df

df = data_from_lakefs()
st.dataframe(df)