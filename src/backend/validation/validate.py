from typing import Optional
from pydantic import BaseModel, validator, ValidationError
from datetime import datetime
import pandas as pd

# Import logging configuration
from config.logging.modern_log import LoggingConfig

logger = LoggingConfig(level="DEBUG", level_console="INFO").get_logger()

class TweetData(BaseModel):
    username: str
    tweetText: str
    scrapeTime: datetime
    tag: Optional[str]
    postTimeRaw: str
    postTime: datetime
    year: int
    month: int
    day: int

    @validator('postTime')
    def validate_post_time(cls, v):
        if v.year < 2020 or v > datetime.now():
            raise ValueError("postTime is out of valid range")
        return v

    @validator('month')
    def validate_month(cls, v):
        if not 1 <= v <= 12:
            raise ValueError("month must be between 1 and 12")
        return v

    @validator('day')
    def validate_day(cls, v):
        if not 1 <= v <= 31:
            raise ValueError("day must be between 1 and 31")
        return v

class ValidationPydantic:
    def __init__(self, model: type[BaseModel]):
        self.model = model

    def validate(self, df: pd.DataFrame) -> bool:
        all_valid = True 

        for idx, row in df.iterrows():
            data_dict = row.to_dict()
            try:
                self.model(**data_dict)
            except ValidationError as e:
                all_valid = False
                logger.error(f"Validation error in row {idx}:")
                logger.error(e.json(indent=2))

        return all_valid