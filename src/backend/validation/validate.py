from typing import Optional
from pydantic import BaseModel, field_validator, ValidationError
from datetime import datetime
import pandas as pd
from rich.panel import Panel
from rich.console import Console
# Import logging configuration
from config.logging.modern_log import LoggingConfig

logger = LoggingConfig(level="DEBUG", level_console="INFO").get_logger()

class TweetData(BaseModel):
    username: str
    tweetText: str
    scrapeTime: datetime
    tag: Optional[str]
    postTimeRaw: datetime
    postTime: datetime
    year: int
    month: int
    day: int

    @field_validator('postTime')
    def validate_post_time(cls, v):
        if v.year < 2020 or v > datetime.now():
            raise ValueError("postTime is out of valid range")
        return v

    @field_validator('month')
    def validate_month(cls, v):
        if not 1 <= v <= 12:
            raise ValueError("month must be between 1 and 12")
        return v

    @field_validator('day')
    def validate_day(cls, v):
        if not 1 <= v <= 31:
            raise ValueError("day must be between 1 and 31")
        return v

class ValidationPydantic:
    def __init__(self, model: type[BaseModel]):
        self.model = model
        self.console = Console()

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
        
        # Validation
        dataset_checks = {
            f"Record Count (≥1000) records: {len(df)}": len(df) >= 1000,
            f"Time Span (≥24 hours) min: {pd.to_datetime(df['postTime']).min()} max: {pd.to_datetime(df['postTime']).max()}": self._check_time_span(df),
            f"No Missing Values missing: {df.isnull().sum().sum()}": df.isnull().sum().sum() == 0,
            f"No 'object' dtype columns columns: {', '.join(f'{k}: {v}' for k, v in df.dtypes.items() if v == 'object')}": not any(df.dtypes == 'object'),
            f"No Duplicate Rows duplicates: {df.duplicated().sum()}": df.duplicated().sum() == 0,
        }

        failed_checks = [k for k, v in dataset_checks.items() if not v]
        if failed_checks:
            all_valid = False
            panel_content = "\n".join(f"[bold red]✘[/bold red] {k}" if not v else f"[green]✔ {k}[/green]" 
                                      for k, v in dataset_checks.items())
            panel = Panel(panel_content, title="Dataset Validation Summary", border_style="bold red")
            self.console.print(panel)
            logger.error("Dataset-level validation failed.")
            return False
        else:
            panel_content = "\n".join(f"[green]✔ {k}[/green]" for k in dataset_checks)
            panel = Panel(panel_content, title="Dataset Validation Summary", border_style="bold green")
            self.console.print(panel)
        return all_valid

    def _check_time_span(self, df: pd.DataFrame) -> bool:
        if 'postTime' not in df.columns:
            return False
        try:
            min_time = pd.to_datetime(df['postTime']).min()
            max_time = pd.to_datetime(df['postTime']).max()
            return (max_time - min_time) >= pd.Timedelta(hours=24)
        except Exception as e:
            logger.error(f"Time span check failed: {e}")
            return False

if __name__ == "__main__":
    # Example usage
    data = pd.read_csv('data/tweet_data.csv')
    validator = ValidationPydantic(TweetData)
    is_valid = validator.validate(data)