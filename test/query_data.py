import pandas as pd

data = pd.read_parquet("data/part.parquet", engine="pyarrow")

print(data.head())