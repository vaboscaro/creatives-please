from flask import Flask, redirect, url_for, request, session, render_template
from authlib.integrations.flask_client import OAuth
from utils import *
from fetch_video_list import *
from functools import wraps
from flask import session, redirect, url_for
from pytz import timezone
from datetime import datetime
import json
from dotenv import load_dotenv
import os

app = Flask(__name__)
app.secret_key = os.getenv('FLASK_SECRET')
app.config['SESSION_TYPE'] = 'filesystem'

video_list = None

# Initialize OAuth
oauth = OAuth(app)
google = oauth.register(
    name='google',
    client_id=os.getenv("GOOGLE_CLIENT_ID"),
    client_secret=os.getenv("GOOGLE_CLIENT_SECRET"),
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    client_kwargs={
        'scope': 'openid email profile https://www.googleapis.com/auth/spreadsheets',
    },
    jwks_uri='https://www.googleapis.com/oauth2/v3/certs',  # Add this line
    userinfo_endpoint='https://openidconnect.googleapis.com/v1/userinfo'  # Optional, for user info
)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user' not in session:  # Replace 'user' with the key used for storing user info in the session
            return redirect(url_for('login'))  # Redirect to the login page
        return f(*args, **kwargs)
    return decorated_function


@app.route('/content_review/<_ComputedKey>', methods=['POST'])
@login_required
def content_review(_ComputedKey):

    action = request.form.get("action")
    print(f"Action is: {action}")

    user_email = session.get('user', {}).get('email', 'default_email@example.com')
    selected_answers = request.form.get('selected_answers', '{}')  # Get JSON string of selected answers
    try:
        selected_answers = json.loads(selected_answers)  # Parse JSON into a Python dict
    except json.JSONDecodeError:
        selected_answers = {}

    video = fetch_video_by_id(_ComputedKey)

    log_to_sheet(
        video,
        user_email,
        action,
        gender=selected_answers.get('gender', None),
        product=selected_answers.get('product', None)
    )
    
    # Fetch the next video_id (logic depends on your data structure)
    next_video = get_next_video()  # Implement this helper function
    if next_video:
        return redirect(url_for("video_page", video_id=next_video["id"]))
    else:
        return redirect(url_for("end_page"))  # No more videos available

@app.route('/review/<video_id>', methods=['POST'])
@login_required
def review(video_id):

    action = request.form.get("action")
    print(f"Action is: {action}")

    user_email = session.get('user', {}).get('email', 'default_email@example.com')
    selected_answers = request.form.get('selected_answers', '{}')  # Get JSON string of selected answers
    
    try:
        selected_answers = json.loads(selected_answers)  # Parse JSON into a Python dict
    except json.JSONDecodeError:
        selected_answers = {}

    video = fetch_video_by_id(video_id)
    # videos_category = selected_answers.get("categories", "Todos")

    log_to_sheet(
        video,
        user_email,
        action,
        gender=selected_answers.get('gender', None),
        product=selected_answers.get('product', None),
        rejection_reason=selected_answers.get('rejection_reason'),
        theme=selected_answers.get('theme', None),
        url=selected_answers.get("url", None)
    )
    
    # Fetch the next video_id (logic depends on your data structure)
    next_video = get_next_video()  # Implement this helper function
    if next_video:
        return redirect(url_for("video_page", video_id=next_video["id"]))
    else:
        return redirect(url_for("end_page"))  # No more videos available

@app.route('/login')
def login():
    session.clear()  # Clear any old session data
    redirect_uri = url_for('callback', _external=True)
    return oauth.google.authorize_redirect(redirect_uri)


@app.route('/callback')
def callback():
    token = oauth.google.authorize_access_token()
    user_info = oauth.google.get('userinfo').json()

    # Debugging
    app.logger.debug(f"Token: {token}")
    app.logger.debug(f"User Info: {user_info}")

    # Set user data in the session
    session['user'] = user_info
    session['email'] = user_info.get('email')

    # Fetch the first video (or any logic to determine the starting video)
    video_list = fetch_video_list_fn()
    if video_list:
        first_video_id = video_list[0]['id']
        return redirect(url_for('video_page', video_id=first_video_id))
    else:
        # Redirect to the end page if no videos are available
        return redirect(url_for('end_page'))

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('login'))

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/video_list')
@login_required
def video_list_page():
    videos = fetch_video_list_fn()  # Assuming fetch_video_list() returns all videos
    return render_template('video_list_page.html', videos=videos)

@app.route('/video_page/<video_id>', methods=['GET'])
@login_required
def video_page(video_id=None):
    
    if not video_id:
        return redirect(url_for("end_page"))
    
    video = fetch_video_by_id(video_id)
    user_email = session.get('user', {}).get('email', 'default_email@example.com')
    posted_at = video.get('posted_at', None)

    products = fetch_distinct_products_cached()
    urls = fetch_distinct_urls_cached()

    return render_template(
        'video.html',
        video_url=video['download_link'],
        username=video['profile_username'],
        user_email=user_email,
        posted_at=posted_at,
        video_id=video['id'],
        products=products,
        urls=urls
    )

@app.route('/content_approval/<video_id>', methods=['GET'])
@login_required
def content_approval(video_id=None):
    if not video_id:
        return redirect(url_for("end_page"))
    video = fetch_video_by_id(video_id)

    user_email = session.get('user', {}).get('email', 'default_email@example.com')

    # Handle the `posted_at` field safely
    posted_at = video.get('posted_at', None)

    return render_template(
        'content_approval.html',
        video_url=video['download_link'],
        username=video['profile_username'],
        user_email=user_email,
        posted_at=posted_at,
        video_id=video['id']
    )

@app.route('/end')
def end_page():
    """Displays the end page."""
    return render_template('end.html')

@app.route("/start_video_review", methods=["GET"])
@login_required
def start_video_review():
    """Redirects to the first available video for review."""
    video_list = fetch_video_list_fn()  # Fetch the video list (or a similar function)
    if video_list:
        first_video = video_list[0]  # Get the first available video
        return redirect(url_for("video_page", video_id=first_video["id"]))
    else:
        return redirect(url_for("end_page"))  # Redirect to the end page if no videos available

if __name__ == '__main__':
    app.run(debug=True)
