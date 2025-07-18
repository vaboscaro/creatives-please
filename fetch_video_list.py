from google.cloud import bigquery
from google.oauth2 import service_account
from query import *
import datetime
from dotenv import load_dotenv
import os
import json
import time

load_dotenv()

credentials_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

scopes = [
    "https://www.googleapis.com/auth/bigquery",
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets"
]

with open(credentials_path, 'r') as f:
    service_account_credentials = json.load(f)

# Load the service account credentials
credentials = service_account.Credentials.from_service_account_info(
    service_account_credentials,
    scopes=scopes
)

# Create a BigQuery client with explicit credentials
client = bigquery.Client(
    credentials=credentials, 
    project=credentials.project_id,
)

_last_fetch_time = 0
_cached_products = []

def fetch_distinct_products_cached(ttl_seconds=3600):
    global _last_fetch_time, _cached_products
    now = time.time()

    if now - _last_fetch_time > ttl_seconds:
        print("Refreshing product list from BigQuery")
        product_query = """
            SELECT DISTINCT product_title
            FROM insider-lake-sensitive.integrated_br.gsheets_capomastro_products
            ORDER BY product_title
        """
        query_job = client.query(product_query)
        result = query_job.result()
        _cached_products = [row.product_title for row in result]
        _last_fetch_time = now

    return _cached_products

def fetch_video_list_fn():

    query_job = client.query(query_str)  # Make an API request.
    results = query_job.result()  # Wait for the query to finish.

    # Convert results to a list of dictionaries for easier processing.
    video_list = []
    for row in results:
        video_list.append({
            "id": row.get("id"),
            "profile_username": row.get("profile_username"),
            "download_link": row.get("download_link"),
            "post_url": row.get("post_url"),
            "posted_at": row.get("posted_at"),
            "recommendation_method": row.get("recommendation_method", "manual"),
        })

    return video_list