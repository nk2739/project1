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
    If session has attribute "username", this means user "session['username'] has already logged in,
    the page will be directed to user's home page, otherwise it will be directed to the login page.
    """
    if 'username' in session:
        return redirect('/user_page/' + session['username'] + '/private')
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
            session["username"] = username
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
            check_password = request.form['check_password']
            if not email:
                flash("E-mail Must Not Be Null!")
            elif not request.form["password"]:
                flash("Password Must Not Be Null!")
            elif not request.form["check_password"]:
                flash("Please Check Your Password!")
            elif request.form["password"] != request.form["check_password"]:
                flash("Passwords Are Not Consistent!")
            else:
                # All the sign up information is valid.
                # Now we will generate a uid for the new user
                # We should also check the uniqueness, i.e. we should check that the uid is not used before.
                while True:
                    uid = random.randint(10000, 99999)
                    try:
                        uid_exist_cmd = "SELECT * FROM users WHERE uid=:uid"
                        cursor = g.conn.execute(text(uid_exist_cmd), uid=uid)
                        cursor.next()
                    except:
                        # Insert the new user into the users table
                        add_new_user_cmd = "INSERT INTO users VALUES (:uid, :username, :email, :password)"
                        g.conn.execute(text(add_new_user_cmd), uid=uid, username=username, email=email,
                                       password=password)
                        break
                session['username'] = username
                return render_template("sign_up.html", username=username, sign_up=True)
            return render_template("sign_up.html", username=username, email=email, password=password,
                                   check_password=check_password, sign_up=False)
        finally:
            cursor.close()


@app.route('/logout', methods=['POST'])
def logout():
    session.pop('username', None)
    return redirect('/')


@app.route('/user_page/<username>/<mode>')
def user_page(username, mode):
    if mode in 'public':
        return render_template("user_page.html", mode=mode)
    elif mode == 'private':
        favorite_team_cmd = """
        SELECT T.name
        FROM users AS U, teams AS T, favoriteteam AS F
        WHERE U.name = :username AND U.uid = F.uid AND F.tid = T.tid
        LIMIT 5
        """
        cursor = g.conn.execute(text(favorite_team_cmd), username=username)
        teams = [row['name'] for row in cursor]

        favorite_player_cmd = """
        SELECT P.name
        FROM users AS U, players AS P, favoriteplayer AS F
        WHERE U.name = :username AND U.uid = F.uid AND F.pid = P.pid
        LIMIT 5
        """
        cursor = g.conn.execute(text(favorite_player_cmd), username=username)
        players = [row['name'] for row in cursor]

        subscribe_cmd = """
        SELECT T1.name, T2.name, S.date
        FROM users AS U, subscribematch AS S, teams AS T1, teams AS T2
        WHERE U.name = :username AND T1.tid = S.home_tid AND T2.tid = S.away_tid AND S.uid = U.uid
        """
        cursor = g.conn.execute(text(subscribe_cmd), username=username)
        matches = [row for row in cursor]

        friend_cmd = """
        SELECT U2.name
        FROM users AS U1, users AS U2, friends AS F
        WHERE U1.name = :username AND U1.uid = F.uid1 AND U2.uid = F.uid2
        UNION 
        SELECT U1.name
        FROM users AS U1, users AS U2, friends AS F
        WHERE U2.name = :username AND U1.uid = F.uid1 AND U2.uid = F.uid2
        """
        cursor = g.conn.execute(text(friend_cmd), username=username)
        friends = [row['name'] for row in cursor]

        cursor.close()
        return render_template("user_page.html", mode=mode, username=username, teams=teams, players=players,
                               matches=matches, friends=friends)
    else:
        raise Exception('Mode must be either private or public!')


@app.route('/team_page')
def team_page():
    return render_template("team_page.html")


@app.route('/player_page')
def player_page():
    return render_template("player_page.html")


@app.route('/coach_page')
def coach_page():
    return render_template("coach_page.html")


@app.route('/all_matches_page')
def all_matches_page():
    return render_template("all_matches_page.html")


@app.route('/single_match_page')
def single_match_page():
    return render_template("single_match_page.html")


@app.route('/all_teams_page')
def all_teams_page():
    return render_template("all_teams_page.html")


@app.route('/all_players_page')
def all_players_page():
    return render_template("all_players_page.html")


@app.route('/other_user_page')
def other_user_page():
    return render_template("other_user_page.html")


@app.route('/index')
def index():
    return render_template("index.html")


# Example of adding new data to the database
@app.route('/add', methods=['POST'])
def add():
    name = request.form['name']
    print name
    cmd = 'INSERT INTO test(name) VALUES (:name1), (:name2)';
    g.conn.execute(text(cmd), name1=name, name2=name);
    return redirect('/')


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
