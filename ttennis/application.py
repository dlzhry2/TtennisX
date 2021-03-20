import os
import csv
import datetime

from cs50 import SQL
from flask import Flask, flash, jsonify, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required, usd

# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True

# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

# Custom filter
app.jinja_env.filters["usd"] = usd

# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///tabletennis.db")


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    """Show homepage with power rankings"""
    if request.method == "POST":

        if not request.form.get('topx'):
            return apology("must specify top x players", 403)

        # Variable for top x players
        w = int(request.form.get("topx"))

        # Variables for gender and year to be used for csv file and a dictionary for later
        gender = str(request.form.get("gender"))
        year = str(request.form.get("year"))
        rank_dict = []
        # Ensure user's search is valid
        if not request.form.get("gender"):
            return apology("must provide a gender", 403)

        if not request.form.get("year"):
            return apology("must provide a year", 403)

        elif w < 1:
            return apology("must search for at least one player", 403)

        elif w > 200:
            return apology("max search = 200", 403)

        csv_name = "rankings/" + year + gender + ".csv"

        # Open up the relevant csv file and copy data into a dict object
        with open(csv_name, newline='') as rankingcsv:
            rankinglist = csv.DictReader(rankingcsv)

            for row in rankinglist:
                rank_dict.append(row)

        y = 0

        # Include other variables for search function
        x = [2014, 2015, 2016, 2017, 2018, 2019, 2020]
        z = len(x)

        return render_template("indexsearch.html", rank_dict=rank_dict, y=y, x=x, z=z, w=w, year=year, gender=gender)

    else:
        # For now just offering data for the following years
        x = [2014, 2015, 2016, 2017, 2018, 2019, 2020]
        y = 0
        z = len(x)
        return render_template("index.html", x=x, y=y, z=z)


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    # Forget any user_id
    session.clear()

    # If user has actually submitted some information as opposed to GET
    if request.method == "POST":

        # Return the information submitted as variables for this function
        username = request.form.get("username")
        password = request.form.get("password")
        confirmation = request.form.get("confirmation")

        # Carry out query to check if username exists
        rows = db.execute("SELECT * FROM users WHERE username = :username",
                          username=request.form.get("username"))

        # Check username provided
        if not username:
            return apology("must provide username", 403)

        # Check password provided
        elif not password:
            return apology("must provide password", 403)

        # Check a confirmation provided
        elif not confirmation:
            return apology("must confirm password", 403)

        # Check that passwords match
        elif password != confirmation:
            return apology("passwords do not match", 403)

        # Check if username already exists
        elif len(rows) != 0:
            return apology("username already exists!", 403)

        elif ' ' in username:
            return apology("username contained forbidden characters", 403)

        # Create variables for username and password and insert this into db
        username = request.form.get("username")
        passx = generate_password_hash(password)
        db.execute("INSERT INTO users (username, hash) VALUES (?, ?)", username, passx)

        # Return user to root
        flash("Registration successful")
        return render_template("login.html", username=username)

    else:
        return render_template("register.html")


@app.route("/change", methods=["GET", "POST"])
@login_required
def change():
    """Allow user to change password"""
    if request.method == "POST":

        # Check the current password is correct
        rows = db.execute("SELECT * FROM users WHERE id = :id", id=session["user_id"])
        if not check_password_hash(rows[0]['hash'], request.form.get("password")):
            return apology("password entered is incorrect", 403)

        # Validate against null value
        if not request.form.get("newpassword"):
            return apology("you must enter a new password", 403)

        if not request.form.get("confirm"):
            return apology("you must confirm the new password", 403)

        # Validation if the newpasswords do not match
        if request.form.get("newpassword") != request.form.get("confirm"):
            return apology("passwords do not match", 403)

        # Having passed through validation the password must be updated
        passx = generate_password_hash(request.form.get("newpassword"))
        db.execute("UPDATE users SET hash = ? WHERE id = ?", passx, session["user_id"])
        flash("Password changed successfully")
        return redirect("/")

    else:
        return render_template("change.html")


@app.route("/players", methods=["GET", "POST"])
@login_required
def players():
    """Allow user to view all players and link to create new"""
    if request.method == "POST":

        # Get the variable to order by
       filter = str(request.form.get("filter"))

       # Different order if filtering by names
       if filter == "name":
           players = db.execute("SELECT * FROM players ORDER BY {} ASC".format(filter))
           y = 0
           x = len(players)
           return render_template("players.html", x=x, players=players, y=y)

       else:
           players = db.execute("SELECT * FROM players ORDER BY {} DESC".format(filter))
           y = 0
           x = len(players)
           return render_template("players.html", x=x, players=players, y=y)

    else:

        # Return a table with all entries in the players table
        players = db.execute("SELECT * FROM players")
        y = 0
        x = len(players)
        return render_template("players.html", x=x, players=players, y=y)

@app.route("/createplayers", methods=["GET", "POST"])
@login_required
def createplayers():
    """Allow user to make new players"""
    if request.method == "POST":

        # Validation to ensure correct usage
        if not request.form.get("name"):
            return apology("must provide name", 403)

        elif not request.form.get("gender"):
            return apology("must provide gender", 403)

        elif not request.form.get("dob"):
            return apology("must provide dob", 403)

        elif len(request.form.get("name")) > 245:
            return apology("name provided exceeds max size", 403)

        elif len(request.form.get("dob")) != 10:
            return apology("please provide date in dd/mm/yyyy format", 403)

        # Ensure a record for that player does not already exist
        rows = db.execute("SELECT * FROM players WHERE name= :name", name=request.form.get("name"))

        if len(rows) != 0:
            return apology("a record for this player already exists", 403)

        # If validation passes, create variables based on the user's input
        name = request.form.get("name")
        gender = request.form.get("gender")
        dob = request.form.get("dob")

        db.execute("INSERT INTO players (name, gender, dob) VALUES (?, ?, ?)", name, gender, dob)
        flash("Player created successfully")
        return render_template("createplayers.html")

    else:
        return render_template("createplayers.html")

@app.route("/leagues", methods=["GET", "POST"])
@login_required
def leagues():
    """Allow user select and view leagues and a link to create new"""

    if request.method == "POST":

        # Get the name and years for this league
        l = request.form.get('league')
        leaguetitle = db.execute("SELECT * FROM leagues WHERE id = :id", id=l)

        # Same code as GET to populate search
        leagues = db.execute("SELECT * FROM leagues")
        y = 0
        x = len(leagues)

        # Validate to ensure correct usages
        if not request.form.get("league"):
            return apology("must select league", 403)

        # Find the relevant table for that particular league and return it
        leagues1 = '"' + str(request.form.get('league')) + '"'
        leaguetable = db.execute("SELECT * FROM {} ORDER BY points DESC, pd DESC, playername".format(leagues1))

        z = 0
        w = len(leaguetable)

        return render_template('leaguessearch.html', x=x, y=y, leaguetable=leaguetable, leaguetitle=leaguetitle, z=z, w=w, leagues=leagues)

    else:
        leagues = db.execute("SELECT * FROM leagues")
        y = 0
        x = len(leagues)
        return render_template("leagues.html", leagues=leagues, y=y, x=x)

@app.route("/createleague", methods=["GET", "POST"])
@login_required
def createleague():
    """Allow user to create new league"""

    if request.method == "POST":

        # If the form submitted contains all the details of the league
        if not request.form.get("playersnumber"):
            if not request.form.get('name'):
                return apology("no name provided", 403)

            if not request.form.get("startyear"):
                return apology("no start year provided", 403)

            if not request.form.get("endyear"):
                return apology("no end year provided", 403)

            # Ensure that this league does not already exist
            rows = db.execute("SELECT * FROM leagues WHERE name= :name AND startyear= :startyear AND endyear= :endyear",
                              name=request.form.get("name"), startyear=request.form.get('startyear'), endyear=request.form.get('endyear'))

            if len(rows) != 0:
                return apology("a record for this league already exists", 403)

            # Ensure that all the player fields are provided and no names duplicated
            x = int(request.form.get('playernumber'))
            allplayers = list()

            for y in range(x):
                name = "player" + str(y)
                if not request.form.get(name):
                    return apology("not all players assigned", 403)

                if str(request.form.get(name)) in allplayers:
                    return apology("cannot add the same player twice", 403)

                allplayers.append(request.form.get(name))

            # With all validation passed need to add information to leagues table
            name = str(request.form.get("name"))
            startyear = int(request.form.get("startyear"))
            endyear = int(request.form.get("endyear"))

            db.execute("INSERT INTO leagues (name, startyear, endyear) VALUES (?, ?, ?)", name, startyear, endyear)

            # Create a new table using the id key of the new league
            id1 = db.execute("SELECT id FROM leagues WHERE name= :name", name=name)
            id = "'" + str(id1[0]['id']) + "'"
            db.execute("CREATE TABLE {} ('id' INTEGER PRIMARY KEY, 'playername' varchar(245) NOT NULL, 'gamesplayed' int NOT NULL DEFAULT 0, 'gameswon' int NOT NULL DEFAULT 0, 'gameslost' int NOT NULL DEFAULT 0, 'pf' int NOT NULL DEFAULT 0, 'pa' int NOT NULL DEFAULT 0, 'pd' int NOT NULL DEFAULT 0, 'points' int NOT NULL DEFAULT 0)".format(id))

            # Insert a row for each player into this table
            for y in range(x):
                db.execute("INSERT INTO {} (playername) VALUES(?)".format(id), allplayers[y])

            # Flash message and return html
            flash("League created successfully")
            return render_template("createleague.html")

        # If the form submitted just contains the number of players
        else:
            nplayers = int(request.form.get("playersnumber"))
            players = db.execute("SELECT name FROM players")

            if nplayers > 50 or nplayers < 2:
                return apology("players in league must be between 2 and 50", 403)

            if nplayers > len(players):
                return apology("not enough players available to fulfill request", 403)

            y = 0
            z = 0
            x = len(players)
            return render_template("createleague2.html", nplayers=nplayers, x=x, y=y, players=players, z=z)

    else:
        return render_template('createleague.html')

@app.route("/recordresults", methods=["GET", "POST"])
@login_required
def recordresults():
    """Allow user to record match scores"""

    if request.method == "POST":

        # When the league name has been provided
        if request.form.get('league'):

            # Get the list of possible players using the league id provided
            leagueid = request.form.get("league")
            leaguename = db.execute("SELECT * FROM leagues WHERE id= :id", id=leagueid)

            # Use this version for SQL query
            leagueid1 = '"' + str(leagueid) + '"'
            players = db.execute("SELECT playername FROM {}".format(leagueid1))

            y = 0
            x = len(players)

            return render_template("recordresults1.html", players=players, y=y, x=x, leaguename=leaguename, leagueid=leagueid)

        # Following three cases ensure that player names are provided
        if request.form.get('leaguecarry') and request.form.get('player1') and not request.form.get('player2'):
            return apology("must provide name for player 2", 403)

        if request.form.get('leaguecarry') and request.form.get('player2') and not request.form.get('player1'):
            return apology("must provide name for player 1", 403)

        if request.form.get('leaguecarry') and not request.form.get('player2') and not request.form.get('player1'):
            return apology("must provide names for both players", 403)

        # Case for when players are provided for scoring
        if request.form.get('leaguecarry') and request.form.get('player2') and request.form.get('player1'):

            if request.form.get('player1') == request.form.get('player2'):
                return apology("cannot play a match with one player", 403)

            leagueid = request.form.get("leaguecarry")
            leaguename = db.execute("SELECT * FROM leagues WHERE id= :id", id=leagueid)
            player1 = request.form.get('player1')
            player2 = request.form.get('player2')

            return render_template("recordresults2.html", leagueid=leagueid, leaguename=leaguename, player1=player1, player2=player2)

        # Score submitted- case for when not enough sets played
        if request.form.get('leaguecarrycarry') and (int(request.form.get('p1set1')) != 3 and int(request.form.get('p2set1')) != 3):
            return apology("matches must be best of 5 sets", 403)

        # Case for when sets entered correctly but not enough games
        if request.form.get('leaguecarrycarry') and int(request.form.get('p1game3')) == 0 and int(request.form.get('p2game3')) == 0:
            return apology("matches must be best of 5 sets", 403)

        if request.form.get('leaguecarrycarry') and (int(request.form.get('p1set1')) < 0 or int(request.form.get('p2set1')) < 0):
            return apology('cannot record negative set number', 403)

        # Case for scores being equal
        if request.form.get('leaguecarrycarry') and request.form.get('p1set1') == request.form.get('p2set1'):
            return apology('game must have a winner', 403)

        # Case for no date provided
        if request.form.get('leaguecarrycarry') and not request.form.get('date'):
            return apology('no date provided', 403)

        # If validation passes update players table with new data

        # If player 1 was the winner
        if request.form.get('p1set1') > request.form.get('p2set1'):
            name = str(request.form.get('player1carry'))
            playerstats = db.execute("SELECT * FROM players WHERE name= :name", name=name)

            # Create variable with values for games, wins + 1
            games = int(playerstats[0]['games']) + 1
            wins =  int(playerstats[0]['wins']) + 1

            # Update the table
            db.execute("UPDATE players SET games = ?, wins = ? WHERE name=?", games, wins, name)

            # Update the ratio columns for both players
            ratio = db.execute("SELECT * FROM players WHERE name= :name", name=name)

            if ratio[0]['wins'] == 0 and ratio[0]['losses'] == 0:
                db.execute("UPDATE players SET winratio=0 WHERE name= :name", name=name)

            elif ratio[0]['wins'] == 0 and ratio[0]['losses'] > 0:
                db.execute("UPDATE players SET winratio=0 WHERE name= :name", name=name)

            elif ratio[0]['wins'] > 0 and ratio[0]['losses'] == 0:
                db.execute("UPDATE players SET winratio=1 WHERE name= :name", name=name)

            # Case where the ratio needs to be calculated
            else:
                new_ratio = round(float(ratio[0]['wins'] / (ratio[0]['wins'] + ratio[0]['losses'])), 2)
                db.execute("UPDATE players SET winratio=? WHERE name=?", new_ratio, name)

            # Same thing for player 2
            name2 = str(request.form.get('player2carry'))
            playerstats2 = db.execute("SELECT * FROM players WHERE name= :name2", name2=name2)

            games2 = int(playerstats2[0]['games']) + 1
            losses =  int(playerstats2[0]['losses']) + 1
            db.execute("UPDATE players SET games = ?, losses = ? WHERE name=?", games2, losses, name2)

            # Work out new ratio
            ratio2 = db.execute("SELECT * FROM players WHERE name= :name2", name2=name2)

            if ratio2[0]['wins'] == 0 and ratio2[0]['losses'] == 0:
                db.execute("UPDATE players SET winratio=0 WHERE name= :name2", name2=name2)

            elif ratio2[0]['wins'] == 0 and ratio2[0]['losses'] > 0:
                db.execute("UPDATE players SET winratio=0 WHERE name= :name2", name2=name2)

            elif ratio2[0]['wins'] > 0 and ratio2[0]['losses'] == 0:
                db.execute("UPDATE players SET winratio=1 WHERE name= :name2", name2=name2)

            else:
                new_ratio2 = round(float(ratio2[0]['wins'] / (ratio2[0]['wins'] + ratio2[0]['losses'])), 2)
                db.execute("UPDATE players SET winratio=? WHERE name=?", new_ratio2, name2)

        # If player 2 was the winner
        if request.form.get('p2set1') > request.form.get('p1set1'):
            name = str(request.form.get('player2carry'))
            playerstats = db.execute("SELECT * FROM players WHERE name= :name", name=name)

            # Create variable with values for games, wins + 1
            games = int(playerstats[0]['games']) + 1
            wins =  int(playerstats[0]['wins']) + 1

            # Update the table
            db.execute("UPDATE players SET games = ?, wins = ? WHERE name=?", games, wins, name)

            # Update the ratio columns for both players
            ratio = db.execute("SELECT * FROM players WHERE name= :name", name=name)

            if ratio[0]['wins'] == 0 and ratio[0]['losses'] == 0:
                db.execute("UPDATE players SET winratio=0 WHERE name= :name", name=name)

            elif ratio[0]['wins'] == 0 and ratio[0]['losses'] > 0:
                db.execute("UPDATE players SET winratio=0 WHERE name= :name", name=name)

            elif ratio[0]['wins'] > 0 and ratio[0]['losses'] == 0:
                db.execute("UPDATE players SET winratio=1 WHERE name= :name", name=name)

            # Case where the ratio needs to be calculated
            else:
                new_ratio = round(float(ratio[0]['wins'] / (ratio[0]['wins'] + ratio[0]['losses'])), 2)
                db.execute("UPDATE players SET winratio=? WHERE name=?", new_ratio, name)

            # Same thing for player 2
            name2 = str(request.form.get('player1carry'))
            playerstats2 = db.execute("SELECT * FROM players WHERE name= :name2", name2=name2)

            games2 = int(playerstats2[0]['games']) + 1
            losses =  int(playerstats2[0]['losses']) + 1
            db.execute("UPDATE players SET games = ?, losses = ? WHERE name=?", games2, losses, name2)

            # Work out new ratio
            ratio2 = db.execute("SELECT * FROM players WHERE name= :name2", name2=name2)

            if ratio2[0]['wins'] == 0 and ratio2[0]['losses'] == 0:
                db.execute("UPDATE players SET winratio=0 WHERE name= :name2", name2=name2)

            elif ratio2[0]['wins'] == 0 and ratio2[0]['losses'] > 0:
                db.execute("UPDATE players SET winratio=0 WHERE name= :name2", name2=name2)

            elif ratio2[0]['wins'] > 0 and ratio2[0]['losses'] == 0:
                db.execute("UPDATE players SET winratio=1 WHERE name= :name2", name2=name2)

            else:
                new_ratio2 = round(float(ratio2[0]['wins'] / (ratio2[0]['wins'] + ratio2[0]['losses'])), 2)
                db.execute("UPDATE players SET winratio=? WHERE name=?", new_ratio2, name2)

        # Need to update the relevant league table with points and other stats
        id = '"' + str(request.form.get('leaguecarrycarry')) + '"'

        # Case for when player 1 is the winner
        if request.form.get('p1set1') > request.form.get('p2set1'):
            name = str(request.form.get('player1carry'))
            table = db.execute("SELECT * FROM {} WHERE playername= :name".format(id), name=name)

            # Use existing data to calculate new values for the league table
            games = table[0]['gamesplayed'] + 1
            gameswon = table[0]['gameswon'] + 1
            points = table[0]['points'] + 3

            db.execute('UPDATE {} SET gamesplayed=?, gameswon=?, points=? WHERE playername=?'.format(id), games, gameswon, points, name)

            # Update relevant columns for player 2
            name2 = str(request.form.get('player2carry'))
            table2 = db.execute("SELECT * FROM {} WHERE playername= :name2".format(id), name2=name2)

            # Use existing data to calculate new values for the league table
            games2 = table2[0]['gamesplayed'] + 1
            gameslost2 = table2[0]['gameslost'] + 1

            db.execute('UPDATE {} SET gamesplayed=?, gameslost=? WHERE playername=?'.format(id), games2, gameslost2, name2)

           # Case for when player 2 is the winner
        if request.form.get('p2set1') > request.form.get('p1set1'):
            name = str(request.form.get('player2carry'))
            table = db.execute("SELECT * FROM {} WHERE playername= :name".format(id), name=name)

            # Use existing data to calculate new values for the league table
            games = table[0]['gamesplayed'] + 1
            gameswon = table[0]['gameswon'] + 1
            points = table[0]['points'] + 3

            db.execute('UPDATE {} SET gamesplayed=?, gameswon=?, points=? WHERE playername=?'.format(id), games, gameswon, points, name)

            # Update relevant columns for player 1
            name2 = str(request.form.get('player1carry'))
            table2 = db.execute("SELECT * FROM {} WHERE playername= :name2".format(id), name2=name2)

            # Use existing data to calculate new values for the league table
            games2 = table2[0]['gamesplayed'] + 1
            gameslost2 = table2[0]['gameslost'] + 1

            db.execute('UPDATE {} SET gamesplayed=?, gameslost=? WHERE playername=?'.format(id), games2, gameslost2, name2)

        # Work out pf and pa fields ensuring that the are no non int values
        if not request.form.get('p1game4') and not request.form.get('p2game4') and not request.form.get('p1game5') and not request.form.get('p2game5'):
             p1pf = int(request.form.get('p1game1')) + int(request.form.get('p1game2')) + int(request.form.get('p1game3'))
             p1pa = int(request.form.get('p2game1')) + int(request.form.get('p2game2')) + int(request.form.get('p2game3'))

        elif not request.form.get('p1game5') and not request.form.get('p2game5'):
             p1pf = int(request.form.get('p1game1')) + int(request.form.get('p1game2')) + int(request.form.get('p1game3')) + int(request.form.get('p1game4'))
             p1pa = int(request.form.get('p2game1')) + int(request.form.get('p2game2')) + int(request.form.get('p2game3')) + int(request.form.get('p2game4'))

        else:
            p1pf = int(request.form.get('p1game1')) + int(request.form.get('p1game2')) + int(request.form.get('p1game3')) + int(request.form.get('p1game4')) + int(request.form.get('p1game5'))
            p1pa = int(request.form.get('p2game1')) + int(request.form.get('p2game2')) + int(request.form.get('p2game3')) + int(request.form.get('p2game4')) + int(request.form.get('p2game5'))

        name = request.form.get('player1carry')
        name2 = request.form.get('player2carry')

        table = db.execute("SELECT * FROM {} WHERE playername= :name".format(id), name=name)
        table2 = db.execute("SELECT * FROM {} WHERE playername= :name2".format(id), name2=name2)

        # Generate new pf and pa for player 1 and update the table
        new_p1pf = table[0]['pf'] + p1pf
        new_p1pa = table[0]['pa'] + p1pa
        db.execute('UPDATE {} SET pf=?, pa=? WHERE playername=?'.format(id), new_p1pf, new_p1pa, name)

        # Generate new pf and pa for player 2 and update tables
        new_p2pf = table2[0]['pf'] + p1pa
        new_p2pa = table2[0]['pa'] + p1pf
        db.execute('UPDATE {} SET pf=?, pa=? WHERE playername=?'.format(id), new_p2pf, new_p2pa, name2)

        # Use the new calculated pa and pf values to calculate pd
        table3 = db.execute("SELECT * FROM {} WHERE playername= :name".format(id), name=name)
        table4 = db.execute("SELECT * FROM {} WHERE playername= :name2".format(id), name2=name2)

        pd1 = int(table3[0]['pf']) - int(table3[0]['pa'])
        pd2 = int(table4[0]['pf']) - int(table4[0]['pa'])
        db.execute('UPDATE {} SET pd=? WHERE playername=?'.format(id), pd1, name)
        db.execute('UPDATE {} SET pd=? WHERE playername=?'.format(id), pd2, name2)

        # Finally input all the information recorded into the results table
        db.execute("INSERT INTO results (league_id, date, player1, player2, p1set, p2set, p1g1, p2g1, p1g2, p2g2, p1g3, p2g3, p1g4, p2g4, p1g5, p2g5) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", request.form.get('leaguecarrycarry'), request.form.get('date'), request.form.get('player1carry'), request.form.get('player2carry'), request.form.get('p1set1'), request.form.get('p2set1'), request.form.get('p1game1'), request.form.get('p2game1'), request.form.get('p1game2'), request.form.get('p2game2'), request.form.get('p1game3'), request.form.get('p2game3'), request.form.get('p1game4'), request.form.get('p2game4'), request.form.get('p1game5'), request.form.get('p2game5'))

        flash("Results recorded successfully")
        leagues = db.execute("SELECT * FROM leagues")
        y = 0
        x = len(leagues)
        return render_template("recordresults.html", leagues=leagues, y=y, x=x)

    else:
        leagues = db.execute("SELECT * FROM leagues")
        y = 0
        x = len(leagues)
        return render_template("recordresults.html", leagues=leagues, y=y, x=x)

@app.route("/viewresults", methods=["GET", "POST"])
@login_required
def viewresults():
    """Allow user view match scores"""

    if request.method == "POST":
        leagueid = request.form.get("league")

        # Create a variable for the league name to be used in the html
        name = db.execute("SELECT * FROM leagues WHERE id= :id", id=leagueid)
        leagues = db.execute("SELECT * FROM leagues")

        # Create a dict with the sorted list of results for the relevant league
        results = db.execute("SELECT * FROM results WHERE league_id= :id ORDER BY date DESC", id=leagueid)
        y, x, z = 0, len(results), len(leagues)

        return render_template("results1.html", name=name, results=results, y=y, x=x, leagues=leagues, z=z)

    else:
        leagues = db.execute("SELECT * FROM leagues")
        results = db.execute("SELECT * FROM results ORDER BY date DESC")
        y, x, z = 0, len(leagues), len(results)
        names = list()

        for n in range(z):
            id = int(results[n]['league_id'])
            name = db.execute("SELECT name FROM leagues WHERE id= :id", id=id)
            names.append(name[0]['name'])

        return render_template('results.html', leagues=leagues, results=results, y=y, x=x, z=z, names=names)

def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
