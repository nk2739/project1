#!/usr/bin/env python2.7
# coding:utf-8
"""
Columbia W4111 Intro to databases
Example webserver

To run locally

    python server.py

Go to http://localhost:8111 in your browser


A debugger such as "pdb" may be helpful for debugging.
Read about it online.
"""

import os
from time import time
from datetime import datetime
import traceback
import random
from sqlalchemy import *
from sqlalchemy.pool import NullPool
from flask import Flask, request, render_template, g, redirect, Response, flash, session, abort, url_for, escape

tmpl_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')
app = Flask(__name__, template_folder=tmpl_dir)
app.secret_key = b'_5#y2L"F4Q8z\n\xec]/'

# XXX: The Database URI should be in the format of: 
#
#     postgresql://USER:PASSWORD@<IP_OF_POSTGRE_SQL_SERVER>/<DB_NAME>
#
# For example, if you had username ewu2493, password foobar, then the following line would be:
#
#     DATABASEURI = "postgresql://ewu2493:foobar@<IP_OF_POSTGRE_SQL_SERVER>/postgres"
#
# For your convenience, we already set it to the class database

# Use the DB credentials you received by e-mail
DB_USER = "nk2739"
DB_PASSWORD = "4f0akxy0"

DB_SERVER = "w4111.cisxo09blonu.us-east-1.rds.amazonaws.com"

DATABASEURI = "postgresql://" + DB_USER + ":" + DB_PASSWORD + "@" + DB_SERVER + "/w4111"

# This line creates a database engine that knows how to connect to the URI above
engine = create_engine(DATABASEURI)


@app.before_request
def before_request():
    """
    This function is run at the beginning of every web request
    (every time you enter an address in the web browser).
    We use it to setup a database connection that can be used throughout the request

    The variable g is globally accessible
    """
    try:
        g.conn = engine.connect()
    except:
        print "uh oh, problem connecting to database"
        traceback.print_exc()
        g.conn = None


@app.teardown_request
def teardown_request(exception):
    """
    At the end of the web request, this makes sure to close the database connection.
    If you don't the database could run out of memory!
    """
    try:
        g.conn.close()
    except Exception as e:
        pass


@app.route('/')
def home():
    """
    If session has attribute "admin_user", this means user "session['admin_user'] has already logged in,
    the page will be directed to user's home page, otherwise it will be directed to the login page.
    """
    if 'admin_user' in session:
        return redirect('/user_page/' + session['admin_user'] + '/private')
    else:
        return render_template('login.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    """
    If user submit the login form, this function will check if the (username, password) pair is in the users relation
    """
    if request.method == "POST":
        username = request.form['username']
        password = request.form['password']
        check_login_cmd = "SELECT * FROM users WHERE name=:username AND password=:password"
        cursor = g.conn.execute(text(check_login_cmd), username=username, password=password)
        try:
            cursor.next()
            session["admin_user"] = username
            return redirect('/user_page/' + username + '/private')
        except:
            flash("Wrong Username or Password!")
        finally:
            cursor.close()
    return render_template("login.html")


@app.route('/sign_up', methods=['GET', 'POST'])
def sign_up():
    if request.method == "GET":
        return render_template("sign_up.html", sign_up=False)
    else:
        # Check if the username is valid and if the passwords in two box are consistent.
        # If so, add it to the users table in the database.
        username = request.form["username"]
        username_exist_cmd = "SELECT * FROM users WHERE name=:username"
        cursor = g.conn.execute(text(username_exist_cmd), username=username)
        try:
            cursor.next()
            flash("The Username Already Exists!")
            return render_template("sign_up.html", sign_up=False)
        except:
            email = request.form['email']
            password = request.form['password']
            confirm_password = request.form['confirmPassword']
            if password != confirm_password:
                flash("Passwords Are Not Consistent!")
            else:
                # All the sign up information is valid.
                # Now we will generate a uid for the new user
                # We should also confirm the uniqueness, i.e. we should confirm that the uid is not used before.

                add_new_user_cmd = "INSERT INTO users VALUES (:username, :email, :password)"
                g.conn.execute(text(add_new_user_cmd), username=username, email=email, password=password)
                session['admin_user'] = username
                return render_template("sign_up.html", admin_user=username, sign_up=True)
            return render_template("sign_up.html", username=username, email=email, password=password,
                                   confirm_password=confirm_password, sign_up=False)
        finally:
            cursor.close()


@app.route('/logout')
def logout():
    session.pop('admin_user', None)
    return redirect('/')


@app.route('/user_page/<user>/<mode>', methods=['GET', 'POST'])
def user_page(user, mode):
    """
    This part will show the user page in two ways -- public and private.
    The private page is for log in user.
    The public page is for the login user to see other users.
    :param user: string
    :param mode: string, must be 'private' or 'public', or an exception will be raised.
    :return:
    """
    if request.method == "POST":
        if request.form['isFriend'] == "disconnect":
            add_new_friend_cmd = "INSERT INTO friends VALUES (:admin_user, :user)"
            g.conn.execute(text(add_new_friend_cmd), admin_user=session['admin_user'], user=user)
        elif request.form['isFriend'] == "add friend":
            delete_friend_cmd = """
                DELETE FROM friends 
                WHERE uname1 = :admin_user AND uname2 = :user OR uname1 = :user AND uname2 = :admin_user
                """
            g.conn.execute(text(delete_friend_cmd), admin_user=session['admin_user'], user=user)
        else:
            raise Exception("request.form['isFriend'] must be 'disconnect' or 'add friend'")

    if mode in ['public', 'private']:
        email_cmd = "SELECT email FROM users WHERE name = :user"
        cursor = g.conn.execute(text(email_cmd), user=user)
        email = cursor.next()['email']

        favorite_team_cmd = "SELECT tname FROM favoriteteam WHERE uname = :user"
        cursor = g.conn.execute(text(favorite_team_cmd), user=user)
        teams = [row['tname'] for row in cursor]

        favorite_player_cmd = """
            SELECT P.pid, P.name
            FROM players AS P, favoriteplayer AS F
            WHERE F.uname = :user AND F.pid = P.pid
            """
        cursor = g.conn.execute(text(favorite_player_cmd), user=user)
        players = [row for row in cursor]

        subscribe_cmd = """
            SELECT home_tname, away_tname, date
            FROM subscribematch 
            WHERE uname = :user
            """
        cursor = g.conn.execute(text(subscribe_cmd), user=user)
        subscribe_matches = [row for row in cursor]
        if mode == 'public':
            is_friend_cmd = """
                SELECT * 
                FROM friends
                WHERE uname1 = :user AND uname2 = :admin_user OR uname1 = :admin_user AND uname2 = :user
                """
            cursor = g.conn.execute(text(is_friend_cmd), admin_user=session['admin_user'], user=user)
            try:
                cursor.next()
                is_friend = "disconnect"
            except:
                is_friend = "add friend"
            cursor.close()
            return render_template("user_page.html", mode=mode, admin_user=session['admin_user'],
                                   user=user, email=email, teams=teams, players=players,
                                   subscribe_matches=subscribe_matches, is_friend=is_friend)
        else:
            friend_cmd = """
                SELECT uname2
                FROM friends
                WHERE uname1 = :user
                UNION 
                SELECT uname1
                FROM friends
                WHERE uname2 = :user
                """
            cursor = g.conn.execute(text(friend_cmd), user=user)
            friends = [row[0] for row in cursor]

            potential_friend_cmd = """
                SELECT uname
                FROM favoriteplayer
                WHERE pid IN (SELECT fp.pid FROM favoriteplayer AS fp WHERE fp.uname = :user)
                UNION 
                SELECT uname
                FROM favoriteteam
                WHERE tname IN (SELECT ft.tname FROM favoriteteam AS ft where ft.uname = :user)
                LIMIT 5
                """
            cursor = g.conn.execute(text(potential_friend_cmd), user=user)
            potential_friends = [row[0] for row in cursor]

            cursor.close()
            return render_template("user_page.html", mode=mode, user=user, email=email, teams=teams, players=players,
                                   subscribe_matches=subscribe_matches, friends=friends,
                                   potential_friends=potential_friends)
    else:
        raise Exception('Mode must be either private or public!')


@app.route('/team_page/<team>', methods=["GET", "POST"])
def team_page(team):
    if request.method == "POST":
        if request.form['favorite'] == "un-favorite":
            add_favorite_team_cmd = "INSERT INTO favoriteteam VALUES (:admin_user, :team)"
            g.conn.execute(text(add_favorite_team_cmd), admin_user=session['admin_user'], team=team)
        elif request.form['favorite'] == "favorite":
            delete_favorite_team_cmd = "DELETE FROM favoriteteam WHERE uname = :admin_user AND tname = :team"
            g.conn.execute(text(delete_favorite_team_cmd), admin_user=session['admin_user'], team=team)
        else:
            raise Exception("request.form['favorite'] must be either 'un-favorite' or 'favorite'")

    team_info_cmd = "SELECT * FROM teams WHERE name = :team"
    cursor = g.conn.execute(text(team_info_cmd), team=team)
    team_info = cursor.next()

    is_favorite_cmd = "SELECT * FROM favoriteteam WHERE uname = :admin_user AND tname = :team"
    cursor = g.conn.execute(text(is_favorite_cmd), admin_user=session['admin_user'], team=team)
    try:
        cursor.next()
        is_favorite = "un-favorite"
    except:
        is_favorite = "favorite"

    team_players_cmd = "SELECT pid, name FROM players WHERE tname = :team"
    cursor = g.conn.execute(text(team_players_cmd), team=team)
    team_players = [row for row in cursor]

    team_coach_cmd = "SELECT cid, name FROM coaches WHERE tname = :team"
    cursor = g.conn.execute(text(team_coach_cmd), team=team)
    team_coach = cursor.next()

    team_matches_cmd = """
        SELECT home_tname, away_tname, date
        FROM matches
        WHERE home_tname = :team OR away_tname = :team
        """
    cursor = g.conn.execute(text(team_matches_cmd), team=team)
    team_matches = [row for row in cursor]

    cursor.close()
    return render_template("team_page.html", admin_user=session['admin_user'], team_info=team_info,
                           team_palyers=team_players, team_coach=team_coach, team_matches=team_matches,
                           is_favorite=is_favorite)


@app.route('/player_page/<player>', methods=["GET", "POST"])
def player_page(player):
    if request.method == "POST":
        if request.form['favorite'] == "un-favorite":
            add_favorite_player_cmd = "INSERT INTO favoriteplayer VALUES (:admin_user, :player)"
            g.conn.execute(text(add_favorite_player_cmd), admin_user=session['admin_user'], player=player)
        elif request.form['favorite'] == "favorite":
            delete_favorite_player_cmd = "DELETE FROM favoriteplayer WHERE uname = :admin_user AND pid = :player"
            g.conn.execute(text(delete_favorite_player_cmd), admin_user=session['admin_user'], player=player)
        else:
            raise Exception("request.form['favorite'] must be either 'un-favorite' or 'favorite'")

    player_info_cmd = "SELECT * FROM players WHERE pid = :player"
    cursor = g.conn.execute(text(player_info_cmd), player=player)
    player_info = cursor.next()

    is_favorite_cmd = "SELECT * FROM favoriteplayer WHERE uname = :admin_user AND pid = :player"
    cursor = g.conn.execute(text(is_favorite_cmd), admin_user=session['admin_user'], player=player)
    try:
        cursor.next()
        is_favorite = "un-favorite"
    except:
        is_favorite = "favorite"
    cursor.close()
    return render_template("player_page.html", admin_user=session['admin_user'], player_info=player_info,
                           is_favorite=is_favorite)


@app.route('/coach_page/<coach>')
def coach_page(coach):
    coach_info_cmd = "SELECT * FROM coaches WHERE cid = :coach"
    cursor = g.conn.execute(text(coach_info_cmd), coach=coach)
    coach_info = cursor.next()
    cursor.close()
    return render_template("coach_page.html", admin_user=session['admin_user'], coach_info=coach_info)


@app.route('/all_matches_page', methods=["GET", "POST"])
def all_matches_page():
    matches = []
    if request.method == "POST":
        home_team = request.form.get('home_team')
        away_team = request.form.get('away_team')
        select_matches_cmd = ""
        if home_team and away_team:
            select_matches_cmd = """
                SELECT * 
                FROM matches
                WHERE home_tname = :home_team AND away_tname = :away_team
                """
        elif home_team and not away_team:
            select_matches_cmd = """
                SELECT * 
                FROM matches
                WHERE home_tname = :home_team
                """
        elif not home_team and away_team:
            select_matches_cmd = """
                SELECT * 
                FROM matches
                WHERE away_tname = :away_team
                """
        select_matches_cmd += "ORDER BY date DESC"
        cursor = g.conn.execute(text(select_matches_cmd), home_team=home_team,
                                away_team=away_team)
        matches = [row for row in cursor]

    all_teams_cmd = "SELECT name FROM teams"
    cursor = g.conn.execute(text(all_teams_cmd))
    teams = [row['name'] for row in cursor]
    cursor.close()
    return render_template("all_matches_page.html", teams=teams, matches=matches, admin_user=session['admin_user'])


@app.route('/match_page/<home_team>/<away_team>/<date>', methods=["GET", "POST"])
def match_page(home_team, away_team, date):
    if request.method == "POST":
        if request.form.get('comment'):
            timestamp = datetime.fromtimestamp(time()).strftime('%Y/%m/%d %H:%M')
            add_comment_cmd = "INSERT INTO comments VALUES (:home_team, :away_team, :date, :timestamp, :content, :admin_user)"
            g.conn.execute(text(add_comment_cmd), home_team=home_team, away_team=away_team, date=date,
                           timestamp=timestamp, content=request.form['comment'], admin_user=session['admin_user'])

        is_subscribed = request.form.get('subscribe')
        if is_subscribed:
            if is_subscribed == "subscribe":
                delete_subscribe_match_cmd = """
                    DELETE FROM subscribematch
                    WHERE home_tname = :home_team AND away_tname = :away_team AND date = :date AND uname = :admin_user
                    """
                g.conn.execute(text(delete_subscribe_match_cmd), home_team=home_team, away_team=away_team, date=date,
                               admin_user=session['admin_user'])
            elif is_subscribed == "unsubscribe":
                add_subscribe_match_cmd = "INSERT INTO subscribematch VALUES (:admin_user, :home_team, :away_team, :date)"
                g.conn.execute(text(add_subscribe_match_cmd), home_team=home_team, away_team=away_team, date=date,
                               admin_user=session['admin_user'])
            else:
                raise Exception("request.form.get('subscribe') must be either 'subscribe' or 'unsubscribe'")

    is_subscribed_cmd = """
        SELECT * FROM subscribematch 
        WHERE home_tname = :home_team AND away_tname = :away_team AND date = :date AND uname = :admin_user
        """
    cursor = g.conn.execute(text(is_subscribed_cmd), admin_user=session['admin_user'], home_team=home_team,
                            away_team=away_team, date=date)
    try:
        cursor.next()
        is_subscribed = "unsubscribe"
    except:
        is_subscribed = "subscribe"

    comments_cmd = """
        SELECT uname, timestamp, content
        FROM comments
        WHERE home_tname = :home_team AND away_tname = :away_team AND date = :date
        ORDER BY timestamp DESC 
        """
    cursor = g.conn.execute(text(comments_cmd), home_team=home_team, away_team=away_team, date=date)
    comments = [row for row in cursor]

    cursor.close()
    return render_template("match_page.html", admin_user=session['admin_user'], home_team=home_team,
                           away_team=away_team, date=date, is_subscribed=is_subscribed, comments=comments)


@app.route('/all_teams_page')
def all_teams_page():
    all_teams_cmd = "SELECT name FROM teams"
    cursor = g.conn.execute(text(all_teams_cmd))
    teams = [row['name'] for row in cursor]
    cursor.close()
    return render_template("all_teams_page.html", teams=teams, admin_user=session['admin_user'])


@app.route('/all_players_page', methods=["GET", "POST"])
def all_players_page():
    search = []
    if request.method == "POST":
        search_cmd = "SELECT pid, name FROM players WHERE name LIKE '%" + request.form['search'] + "%'"
        cursor = g.conn.execute(text(search_cmd))
        search = [row for row in cursor]

    top_10 = {}
    for criterion in ['ppg', 'rpg', 'apg', 'bpg']:
        top_10_cmd = "SELECT pid, name FROM players ORDER BY " + criterion + " DESC LIMIT 10"
        cursor = g.conn.execute(text(top_10_cmd))
        top_10[criterion] = [row for row in cursor]

    cursor.close()
    return render_template("all_players_page.html", admin_user=session['admin_user'], top_10=top_10, search=search)


if __name__ == "__main__":
    import click

    app.secret_key = os.urandom(12)


    @click.command()
    @click.option('--debug', is_flag=True)
    @click.option('--threaded', is_flag=True)
    @click.argument('HOST', default='0.0.0.0')
    @click.argument('PORT', default=8111, type=int)
    def run(debug, threaded, host, port):
        """
        This function handles command line parameters.
        Run the server using

            python server.py

        Show the help text using

            python server.py --help

        """

        HOST, PORT = host, port
        print "running on %s:%d" % (HOST, PORT)
        app.run(host=HOST, port=PORT, debug=True, threaded=threaded)


    run()
