# %%
import snowflake.connector
from snowflake.connector import DictCursor
from app.settings import snowflake_settings


def connect_snowflake():
    """
    Create a Snowflake connection using username/password from environment variables.
    """
    conn = snowflake.connector.connect(
        **snowflake_settings.model_dump(by_alias=True)
    )
    return conn


def run_query(sql: str):
    """
    Run a query and return results as a list of dictionaries.
    """
    with connect_snowflake() as conn:
        with conn.cursor(DictCursor) as cur:
            cur.execute(sql)
            return cur.fetchall()

if __name__ == "__main__":
    sql = """
    SELECT *
    FROM US_OPEN_CENSUS_DATA__NEIGHBORHOOD_INSIGHTS__FREE_DATASET.PUBLIC."2020_CBG_B11"
    ORDER BY CENSUS_BLOCK_GROUP
    LIMIT 30
    """
    results = run_query(sql)
    print(results)
