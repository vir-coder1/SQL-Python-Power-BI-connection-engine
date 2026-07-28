import sqlite3
import pandas as pd

# File configuration
INPUT_CSV = "Sample - Superstore.csv"
DB_FILE = "company_data.db"
OUTPUT_CSV = "forecast_summary.csv"


def run_pipeline():
    # Load and clean raw dataset
    df = pd.read_csv(INPUT_CSV, encoding="latin1")

    # Standardize column names to clean snake_case
    df.columns = (
        df.columns.str.lower().str.replace(" ", "_").str.replace("-", "_")
    )

    # Format dates consistently for SQLite string operations
    df["order_date"] = pd.to_datetime(
        df["order_date"], format="mixed"
    ).dt.strftime("%Y-%m-%d")

    # Layer 1 & 2: Push to SQLite and aggregate monthly totals
    with sqlite3.connect(DB_FILE) as conn:
        df.to_sql("raw_sales", conn, if_exists="replace", index=False)

        query = """
            SELECT 
                strftime('%Y-%m-01', order_date) AS month,
                category,
                ROUND(SUM(sales), 2) AS actual_sales
            FROM raw_sales
            GROUP BY 1, 2
            ORDER BY month ASC;
        """
        monthly_sales = pd.read_sql_query(query, conn)

    # Apply 3-month rolling average forecast (+ 5% growth baseline)
    monthly_sales["month"] = pd.to_datetime(monthly_sales["month"])
    monthly_sales = monthly_sales.sort_values(["category", "month"])

    monthly_sales["forecast_sales"] = (
        monthly_sales.groupby("category")["actual_sales"]
        .transform(lambda x: x.rolling(window=3, min_periods=1).mean() * 1.05)
        .round(2)
    )

    # Export summarized data layer
    monthly_sales["month"] = monthly_sales["month"].dt.strftime("%Y-%m-%d")
    monthly_sales.to_csv(OUTPUT_CSV, index=False)

    print(f"Pipeline executed successfully. Saved {len(monthly_sales)} rows to {OUTPUT_CSV}")


if __name__ == "__main__":
    run_pipeline()
