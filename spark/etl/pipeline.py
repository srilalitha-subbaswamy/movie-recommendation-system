"""Spark ETL pipeline for MovieLens 25M dataset.

Loads raw CSV data, cleans, transforms, and writes to PostgreSQL and Parquet.
"""

import os
import re
import sys

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import FloatType, IntegerType, StringType, StructField, StructType


def create_spark_session() -> SparkSession:
    """Create a configured Spark session."""
    return (
        SparkSession.builder.appName("MovieLens ETL")
        .config("spark.driver.memory", "4g")
        .config("spark.sql.shuffle.partitions", "8")
        .config(
            "spark.jars.packages",
            "org.postgresql:postgresql:42.7.1",
        )
        .getOrCreate()
    )


def load_raw_data(spark: SparkSession, data_dir: str) -> dict:
    """Load raw CSV files into Spark DataFrames."""
    print(f"Loading raw data from {data_dir}...")

    movies_schema = StructType([
        StructField("movieId", IntegerType(), False),
        StructField("title", StringType(), False),
        StructField("genres", StringType(), False),
    ])

    ratings_schema = StructType([
        StructField("userId", IntegerType(), False),
        StructField("movieId", IntegerType(), False),
        StructField("rating", FloatType(), False),
        StructField("timestamp", IntegerType(), False),
    ])

    links_schema = StructType([
        StructField("movieId", IntegerType(), False),
        StructField("imdbId", StringType(), True),
        StructField("tmdbId", IntegerType(), True),
    ])

    movies_df = spark.read.csv(
        os.path.join(data_dir, "movies.csv"),
        schema=movies_schema,
        header=True,
    )
    ratings_df = spark.read.csv(
        os.path.join(data_dir, "ratings.csv"),
        schema=ratings_schema,
        header=True,
    )
    links_df = spark.read.csv(
        os.path.join(data_dir, "links.csv"),
        schema=links_schema,
        header=True,
    )

    print(f"  Movies: {movies_df.count()} rows")
    print(f"  Ratings: {ratings_df.count()} rows")
    print(f"  Links: {links_df.count()} rows")

    return {"movies": movies_df, "ratings": ratings_df, "links": links_df}


def extract_year(title: str) -> int | None:
    """Extract year from movie title like 'Toy Story (1995)'."""
    match = re.search(r"\((\d{4})\)", title)
    return int(match.group(1)) if match else None


def transform_movies(movies_df, links_df):
    """Clean and enrich movie data."""
    print("Transforming movies...")

    # Register UDF for year extraction
    extract_year_udf = F.udf(extract_year, IntegerType())

    # Split genres into array
    movies_transformed = (
        movies_df.withColumn("genres_array", F.split(F.col("genres"), "\\|"))
        .withColumn("year", extract_year_udf(F.col("title")))
        .withColumn(
            "clean_title",
            F.regexp_replace(F.col("title"), r"\s*\(\d{4}\)\s*$", ""),
        )
        .drop("genres")
        .withColumnRenamed("genres_array", "genres")
        .withColumnRenamed("clean_title", "title_clean")
    )

    # Join with links for external IDs
    movies_enriched = movies_transformed.join(links_df, "movieId", "left")

    # Filter out "(no genres listed)"
    movies_enriched = movies_enriched.withColumn(
        "genres",
        F.when(
            F.array_contains(F.col("genres"), "(no genres listed)"),
            F.array(),
        ).otherwise(F.col("genres")),
    )

    return movies_enriched


def compute_movie_stats(ratings_df):
    """Compute aggregate statistics per movie."""
    print("Computing movie statistics...")
    return (
        ratings_df.groupBy("movieId")
        .agg(
            F.avg("rating").alias("avg_rating"),
            F.count("rating").alias("rating_count"),
        )
        .withColumn("avg_rating", F.round("avg_rating", 2))
    )


def compute_user_stats(ratings_df):
    """Compute aggregate statistics per user."""
    print("Computing user statistics...")
    return (
        ratings_df.groupBy("userId")
        .agg(
            F.avg("rating").alias("avg_rating"),
            F.count("rating").alias("rating_count"),
        )
        .withColumn("avg_rating", F.round("avg_rating", 2))
    )


def create_train_test_split(ratings_df, train_ratio=0.8, val_ratio=0.1):
    """Split ratings by timestamp into train/validation/test sets."""
    print("Creating train/validation/test splits...")

    # Add timestamp rank per user
    from pyspark.sql.window import Window

    window = Window.partitionBy("userId").orderBy("timestamp")
    ratings_ranked = ratings_df.withColumn(
        "rank_pct",
        F.percent_rank().over(window),
    )

    train = ratings_ranked.filter(F.col("rank_pct") <= train_ratio)
    val = ratings_ranked.filter(
        (F.col("rank_pct") > train_ratio)
        & (F.col("rank_pct") <= train_ratio + val_ratio)
    )
    test = ratings_ranked.filter(F.col("rank_pct") > train_ratio + val_ratio)

    print(f"  Train: {train.count()} ratings")
    print(f"  Validation: {val.count()} ratings")
    print(f"  Test: {test.count()} ratings")

    return train.drop("rank_pct"), val.drop("rank_pct"), test.drop("rank_pct")


def write_to_parquet(dataframes: dict, output_dir: str) -> None:
    """Write processed DataFrames to Parquet files."""
    print(f"Writing Parquet files to {output_dir}...")
    os.makedirs(output_dir, exist_ok=True)

    for name, df in dataframes.items():
        path = os.path.join(output_dir, name)
        df.write.mode("overwrite").parquet(path)
        print(f"  {name}: written to {path}")


def write_to_postgres(dataframes: dict, jdbc_url: str, properties: dict) -> None:
    """Write processed DataFrames to PostgreSQL."""
    print("Writing to PostgreSQL...")

    for name, df in dataframes.items():
        print(f"  Writing {name}...")
        df.write.jdbc(
            url=jdbc_url,
            table=name,
            mode="overwrite",
            properties=properties,
        )


def run_pipeline(data_dir: str = "data/raw/ml-25m", output_dir: str = "data/processed") -> None:
    """Run the full ETL pipeline."""
    print("=" * 60)
    print("MovieLens 25M ETL Pipeline")
    print("=" * 60)

    spark = create_spark_session()

    try:
        # Load raw data
        raw = load_raw_data(spark, data_dir)

        # Transform movies
        movies_enriched = transform_movies(raw["movies"], raw["links"])
        movie_stats = compute_movie_stats(raw["ratings"])
        user_stats = compute_user_stats(raw["ratings"])

        # Join movie stats
        movies_final = movies_enriched.join(movie_stats, "movieId", "left").fillna(
            {"avg_rating": 0.0, "rating_count": 0}
        )

        # Create train/test splits
        train, val, test = create_train_test_split(raw["ratings"])

        # Write to Parquet
        write_to_parquet(
            {
                "movies": movies_final,
                "ratings_train": train,
                "ratings_val": val,
                "ratings_test": test,
                "user_stats": user_stats,
            },
            output_dir,
        )

        # Write to PostgreSQL if configured
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            jdbc_url = db_url.replace("+asyncpg", "").replace(
                "postgresql://", "jdbc:postgresql://"
            )
            properties = {
                "user": os.getenv("POSTGRES_USER", "recsys"),
                "password": os.getenv("POSTGRES_PASSWORD", "changeme"),
                "driver": "org.postgresql.Driver",
            }
            write_to_postgres(
                {"movies": movies_final, "users": user_stats},
                jdbc_url,
                properties,
            )

        print("")
        print("=" * 60)
        print("ETL Pipeline completed successfully!")
        print("=" * 60)

    finally:
        spark.stop()


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data/raw/ml-25m"
    output_dir = sys.argv[2] if len(sys.argv) > 2 else "data/processed"
    run_pipeline(data_dir, output_dir)
