"""ALS collaborative filtering model training with MLflow tracking.

Trains a Spark ALS model on the MovieLens dataset, performs hyperparameter
tuning via cross-validation, and exports the trained model artifacts.
"""

import os
import sys

import mlflow
import mlflow.spark
from pyspark.ml.evaluation import RegressionEvaluator
from pyspark.ml.recommendation import ALS
from pyspark.ml.tuning import CrossValidator, ParamGridBuilder
from pyspark.sql import SparkSession


def create_spark_session() -> SparkSession:
    """Create a Spark session for model training."""
    return (
        SparkSession.builder.appName("ALS Training")
        .config("spark.driver.memory", "4g")
        .config("spark.sql.shuffle.partitions", "8")
        .getOrCreate()
    )


def load_training_data(spark: SparkSession, data_dir: str):
    """Load train/validation/test splits from Parquet."""
    print("Loading training data...")
    train = spark.read.parquet(os.path.join(data_dir, "ratings_train"))
    val = spark.read.parquet(os.path.join(data_dir, "ratings_val"))
    test = spark.read.parquet(os.path.join(data_dir, "ratings_test"))

    print(f"  Train: {train.count()} ratings")
    print(f"  Validation: {val.count()} ratings")
    print(f"  Test: {test.count()} ratings")

    return train, val, test


def train_als_model(train_df, val_df, run_tuning: bool = False):
    """Train ALS model with optional hyperparameter tuning.

    Args:
        train_df: Training data with userId, movieId, rating columns.
        val_df: Validation data for evaluation.
        run_tuning: If True, run cross-validation grid search.

    Returns:
        Trained ALS model and evaluation metrics.
    """
    evaluator = RegressionEvaluator(
        metricName="rmse",
        labelCol="rating",
        predictionCol="prediction",
    )

    if run_tuning:
        print("Running hyperparameter tuning...")
        als = ALS(
            userCol="userId",
            itemCol="movieId",
            ratingCol="rating",
            coldStartStrategy="drop",
            nonnegative=True,
        )

        param_grid = (
            ParamGridBuilder()
            .addGrid(als.rank, [50, 100])
            .addGrid(als.maxIter, [10, 15])
            .addGrid(als.regParam, [0.05, 0.1, 0.2])
            .build()
        )

        cv = CrossValidator(
            estimator=als,
            estimatorParamMaps=param_grid,
            evaluator=evaluator,
            numFolds=3,
            parallelism=2,
        )

        cv_model = cv.fit(train_df)
        model = cv_model.bestModel

        # Log best parameters
        print(f"  Best rank: {model.rank}")
        print(f"  Best maxIter: {model._java_obj.parent().getMaxIter()}")
        print(f"  Best regParam: {model._java_obj.parent().getRegParam()}")
    else:
        print("Training ALS with default parameters...")
        als = ALS(
            rank=100,
            maxIter=15,
            regParam=0.1,
            userCol="userId",
            itemCol="movieId",
            ratingCol="rating",
            coldStartStrategy="drop",
            nonnegative=True,
        )
        model = als.fit(train_df)

    # Evaluate on validation set
    val_predictions = model.transform(val_df)
    val_rmse = evaluator.evaluate(val_predictions)
    print(f"  Validation RMSE: {val_rmse:.4f}")

    return model, {"val_rmse": val_rmse}


def export_factor_matrices(model, output_dir: str) -> None:
    """Export user and item factor matrices for fast inference."""
    print(f"Exporting factor matrices to {output_dir}...")
    os.makedirs(output_dir, exist_ok=True)

    # Extract user and item factors
    user_factors = model.userFactors
    item_factors = model.itemFactors

    user_factors.write.mode("overwrite").parquet(
        os.path.join(output_dir, "user_factors")
    )
    item_factors.write.mode("overwrite").parquet(
        os.path.join(output_dir, "item_factors")
    )

    print(f"  User factors: {user_factors.count()} users")
    print(f"  Item factors: {item_factors.count()} items")


def run_training(
    data_dir: str = "data/processed",
    model_dir: str = "models/als",
    run_tuning: bool = False,
) -> None:
    """Run the full ALS training pipeline with MLflow tracking."""
    print("=" * 60)
    print("ALS Model Training Pipeline")
    print("=" * 60)

    mlflow_uri = os.getenv("MLFLOW_TRACKING_URI", "mlruns")
    mlflow.set_tracking_uri(mlflow_uri)
    mlflow.set_experiment("als-training")

    spark = create_spark_session()

    try:
        train, val, test = load_training_data(spark, data_dir)

        with mlflow.start_run(run_name="als-training"):
            # Log parameters
            mlflow.log_param("algorithm", "ALS")
            mlflow.log_param("run_tuning", run_tuning)
            mlflow.log_param("train_size", train.count())
            mlflow.log_param("val_size", val.count())

            # Train model
            model, metrics = train_als_model(train, val, run_tuning=run_tuning)

            # Log model parameters
            mlflow.log_param("rank", model.rank)
            mlflow.log_metrics(metrics)

            # Evaluate on test set
            evaluator = RegressionEvaluator(
                metricName="rmse",
                labelCol="rating",
                predictionCol="prediction",
            )
            test_predictions = model.transform(test)
            test_rmse = evaluator.evaluate(test_predictions)
            mlflow.log_metric("test_rmse", test_rmse)
            print(f"  Test RMSE: {test_rmse:.4f}")

            # Export factor matrices
            export_factor_matrices(model, model_dir)

            # Log model to MLflow
            mlflow.spark.log_model(model, "als-model")

            print("")
            print("=" * 60)
            print("ALS Training completed successfully!")
            print(f"  Model saved to: {model_dir}")
            print(f"  MLflow run: {mlflow.active_run().info.run_id}")
            print("=" * 60)

    finally:
        spark.stop()


if __name__ == "__main__":
    data_dir = sys.argv[1] if len(sys.argv) > 1 else "data/processed"
    model_dir = sys.argv[2] if len(sys.argv) > 2 else "models/als"
    run_tuning = "--tune" in sys.argv
    run_training(data_dir, model_dir, run_tuning)
