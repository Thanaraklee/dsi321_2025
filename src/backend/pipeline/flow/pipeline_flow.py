from prefect import flow
from task.extract import extract_data
from task.transform import transform_data
from task.load import load_data


@flow(name="Data Pipeline Flow")
def data_pipeline():
    extract_data()
    transform_data()
    load_data()

if __name__ == "__main__":
    data_pipeline()