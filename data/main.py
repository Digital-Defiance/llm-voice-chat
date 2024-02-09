
from pyspark.sql import SparkSession
from functools import cache
from pydantic_settings import BaseSettings
import numpy as np
from data.worker import celery_app


class SparkSettings(BaseSettings):
    driver_memory: str = "2g"
    executor_memory: str = "2g"

    class Config:
        env_prefix = "SPARK_"

    
spark_settings = SparkSettings()

class TrainSettings(BaseSettings):
    n_slices: int = 60

    class Config:
        env_prefix = "TRAIN_"


train_settings = TrainSettings()


@celery_app.task(name='prepare_data')
def prepare_data(idx: int, context_window_size: int):
    print(f"Slice of index {idx} has been requested.")

    
    print("Starting spark session")
    spark = SparkSession.builder \
                .master("local[*]") \
                .appName("DATA_WORKER") \
                .config("spark.driver.memory", spark_settings.driver_memory) \
                .config("spark.executor.memory", spark_settings.executor_memory) \
                .getOrCreate()
    print("Started spark session")

    train_slices = spark.read.parquet("/data/train.parquet").randomSplit(
        [1.]*train_settings.n_slices
    )
    
    print("Generated random split.")

    
    print("Collecting slice...")
    rating, text = [], []
    for row in train_slices[idx].collect():
        rating.append(row.rating)
        text.append(row.text)
    print("Slice has been collected.")
    text_bw = np.array(text)[:, :context_window_size]
    rating_b5 = np.array(rating)

    # transform to index of along last dimension
    rating_b = np.argmax(rating_b5 == 1, axis=-1)
    return rating_b, text_bw




