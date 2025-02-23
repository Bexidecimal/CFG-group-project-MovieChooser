#  This file will house Flask API code, manage routing and integrate with front-end

import math
from random import random
from decouple import config
from flask import Flask, render_template, request, session, redirect, url_for, jsonify
from TMDB_API import TMDB
from database import db_utils
from database import auth_utils
from search import search_by_title
from db_config import DB_CONFIG
import mysql.connector
from mysql.connector import Error


# Print database connection info for debugging
# print(f"Connecting to database on host {DB_CONFIG['host']}, port {DB_CONFIG['port']}")
# print(f"Using user {DB_CONFIG['user']} and password {DB_CONFIG['password']}")


# Asking flask to use this file to run the request server side
app = Flask(__name__)

app.secret_key = 'my_secret'
# app.config['SESSION_PERMANENT'] = False # Delete cookie when browser closes

'''app routing:
The ROOT ADDRESS for our application is "/" our first function "home()" will manage the logic for the landing page
using the app route decorator "app.route" binds the function and its logic to this root url
running on port address http://127.0.0.1:5000/'''

# Hashed out as revealing database connection info is a security risk
'''@app.route('/debug') # Debugging route - testing database connection
def debug():
    return {
        "host": DB_CONFIG['host'],
        "user": DB_CONFIG['user'],
        "password": DB_CONFIG['password'],
        "database": DB_CONFIG['database'],
        "port": DB_CONFIG['port']
    }'''

@app.route("/")
def home():
    api_key = config("API_KEY")
    api = TMDB(api_key)

    popular = api.popular_films()
    upcoming = api.upcoming_films()
    top_rated = api.top_rated()
    username = session.get("user")
    
    # print("Popular films response:", popular)  # Debugging line
    
    # Check if popular is not None
    if popular is None:
        popular_results = []  # Set to an empty list if no results
    else:
        popular_results = popular.get("results", [])  # Safely get results

    # Check if upcoming is not None
    if upcoming is None:
        upcoming_results = []  # Set to an empty list if no results
    else:
        upcoming_results = upcoming.get("results", [])

    # Check if top_rated is not None
    if top_rated is None:
        top_rated_results = []  # Set to an empty list if no results
    else:
        top_rated_results = top_rated.get("results", [])

    context = {
        "popular_movies": popular_results,
        "upcoming_movies": upcoming_results,
        "top_rated": top_rated_results,
        "username": username,
        "backdrop": popular_results[math.floor(random() * len(popular_results))] if popular_results else None,
    }
    return render_template("index_2.html", **context)


@app.route("/login")
def login():
    context = {}
    return render_template("login.html", **context)

@app.route("/signup")
def signup():
    context = {}
    return render_template("signup.html", **context)

@app.route("/links")
def links():
    context = {}
    return render_template("links_2.html", **context)

@app.route("/about_us")
def about_us():
    context = {}
    return render_template("about_us.html", **context)

@app.route("/create_user", methods=["POST"])
def create_user():
    context = {}
    username = request.form.get("username")
    password = request.form.get("password")
    db_utils.add_user(username, username, password, 20)
    return render_template("signup_welcome.html", username=username)


"""
    def age_certifications(self, certification):
        url = f"{certification}/movie/list"
        response = requests.get(url)
        certifications = response.json()["certifications"]["GB"]  # should return the certifications from the GB array
        return self.call_api(url)


"""

@app.route("/logout")
def logout():
    context = {}
    session.clear()
    return redirect(url_for("home"))

@app.route("/sign_in", methods=["POST"])
def sign_in():
    context = {}
    username = request.form.get("username")
    password = request.form.get("password")
    user_id = auth_utils.validate_user_login(username, password)
    if user_id:
        session["user"] = username
        session["user_id"] = user_id
        return redirect(url_for('home'))
    else:
        context = {
            "failure_message": "Login failed"
        }
        return render_template("login.html", **context)

@app.route("/toggle-favourites", methods=["POST"])
def toggle_favourites():
    """
    When you click on "add to favourites" Check if the movie is in the favourite list
    if not already in DB add as a favourite, if unhighlighting the "add to favourite" remove from DB
    """
    data = {
        "is_favourite" : False
    }
    movie_id = request.json.get("movie_id")
    if movie_id and session.get("user_id"):
        user_id = session["user_id"]

        if db_utils.is_favourite(user_id, movie_id):
            db_utils.remove_from_favourites(user_id, movie_id)
        else:
            db_utils.save_favourite(user_id, movie_id)
            data["is_favourite"] = True

    return jsonify(data)

@app.route("/saved_films")
def saved_films():
    api_key = config("API_KEY")
    api = TMDB(api_key)

    favourites = db_utils.get_favourites(session["user_id"])

    saved_movies = []
    for movie_id in favourites:
        saved_movies.append(api.get_movie_details(movie_id))

    context = {
        "saved_movies" : saved_movies
    }
    return render_template("saved_films.html", **context)

@app.route("/results", methods=["POST"])
def results():
    """Performs the search and shows the results"""
    # instantiating the TMDB class from TMDB_API.py which performs the search on the movie title from the data entered in the form
    api_key = config("API_KEY")
    api = TMDB(api_key)

    if request.form.get("search"):
        # Main search page after searching by title
        title = request.form.get("search")
        movie_id, results = search_by_title(api, title)
    else:
        # Searching on movie
        movie_id = request.form.get("movie_id")
        title = ""
        results = api.get_movie_details(movie_id)

    if movie_id:
        # 1 result fetch additional data
        context = {
            "movie_id": movie_id,
            "result": results["results"][0] if results.get("results") else results,
            "recommendations" : api.recommended_movie(movie_id)
        }
    elif results.get("results"):
        context = {"results": results["results"]}
    else:
        return render_template("not_found.html", search=title)

    return render_template("results.html", **context)


@app.route("/chosen_movie/<int:movie_id>")
def chosen_movie(movie_id):
    api_key = config("API_KEY")
    api = TMDB(api_key)
    user_id = session.get("user_id")
    context = {
        "movie": api.get_movie_details(movie_id),
        "reviews": api.reviews(movie_id),
        "actors": api.actors(movie_id),
        "provider" : api.provider(movie_id),
        "movie_videos" : api.movie_videos(movie_id),
        "recommendations": api.recommended_movie(movie_id),
        "is_favourite" : db_utils.is_favourite(user_id, movie_id)
    }
    return render_template("chosen_movie.html", **context)


@app.context_processor
def chosen_movie_processor():
    def actor_photo(person_id):
        api_key = config("API_KEY")
        api = TMDB(api_key)
        images = api.person_image(person_id)
        return images["profiles"][0] if images.get("profiles") and images["profiles"] else {}
    return dict(actor_photo=actor_photo)


@app.route("/actor/<int:person_id>")
def actor(person_id):
    api_key = config("API_KEY")
    api = TMDB(api_key)
    context = {
        "credits": api.movie_credits(person_id),
        "person": api.person_details(person_id),
    }
    return render_template("actor.html", **context)

# telling the script to run if running this file and using the debugger to ensure it runs correctly and if not it will
# tell us immediately

# Route to test database connection
@app.route('/testdb')
def test_db():
    try:
        connection = mysql.connector.connect(
            host=DB_CONFIG['host'],
            user=DB_CONFIG['user'],
            password=DB_CONFIG['password'],
            database=DB_CONFIG['database'],
            port=DB_CONFIG['port']
        )
        if connection.is_connected():
            db_info = connection.get_server_info()
            return f"Successfully connected to the database. MySQL server version: {db_info}"
    except Error as e:
        return f"Error connecting to database: {e}"
    finally:
        if 'connection' in locals() and connection.is_connected():
            connection.close()

# Run the app
if __name__ == "__main__":
    app.run(debug=True)