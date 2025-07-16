from google.auth import default
from googleapiclient.discovery import build
import datetime
from fetch_video_list import *
from google.oauth2.service_account import Credentials
import os
import json

load_dotenv()

# Google Sheets setup
scope = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]

# Load credentials
credentials = Credentials.from_service_account_file(
    "credentials.json", scopes=scopes
)

# Initialize the Sheets API
service = build("sheets", "v4", credentials=credentials)
spreadsheet_id = os.getenv('SPREADSHEET_ID')

def log_to_sheet(video, approver_email, outcome, gender=None, product=None, rejection_reason=None):
    
    """Logs video approval outcome to Google Sheets."""
    posted_at = (
        video["posted_at"].strftime("%Y-%m-%d %H:%M:%S")
        if isinstance(video["posted_at"], datetime.datetime)
        else video["posted_at"]
    )
    values = [[
        video["id"],
        video["profile_username"],
        video["download_link"],
        video["post_url"],
        posted_at,
        video.get('recommendation_method', 'manual'),
        approver_email,
        outcome,
        gender if gender else "Not Selected",
        product if product else "Not Selected",
        datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        rejection_reason
    ]]
    body = {"values": values}
    
    # print('Log to Sheets: ')
    # print(body)
    # print()

    # print(f"Active scopes: {credentials.scopes}")
    # print(f"Using email: {credentials.service_account_email}")
    # print()
    
    try:
        result = service.spreadsheets().values().append(
            spreadsheetId=spreadsheet_id,
            range="Sheet1",
            valueInputOption="RAW",
            body=body
        ).execute()
        print("Data successfully appended:", result)
        del body
    except Exception as e:
        print(f"An error occurred: {e}")
        del body

def get_next_video():
    """
    Retrieves the next video from the updated video list.
    If no videos remain, returns None.

    Args:
        fetch_video_list_fn: Function to fetch the video list.

    Returns:
        dict: The next video or None if no videos are left.
    """
    # Fetch the updated video list
    video_list = fetch_video_list_fn()

    # Return the first video if the list is not empty
    if video_list:
        return video_list[0]
    else:
        return None

def fetch_video_by_id(video_id):
    query = f"""
    SELECT distinct id, profile_username, download_link, posted_at, post_url
    FROM `insider-lake-sensitive.unfolded_br.unfolded__mighty_scout_campaign_media`
    WHERE id = cast({video_id} as string)
    """
    query_job = client.query(query)
    results = query_job.result()

    for row in results:
        return {
            "id": row.id,
            "profile_username": row.profile_username,
            "download_link": row.download_link,
            "posted_at": row.posted_at,
            "post_url": row.post_url
        }
    return None
