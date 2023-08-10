import os
import json
import deepl
import requests

from cs50 import SQL
from deepgram import Deepgram
from flask import Flask, flash, redirect, render_template, request, session, send_from_directory
from flask_session import Session
from helpers import login_required, transcription, elevenlabs_voice, elevenlabs_create
from werkzeug.security import check_password_hash, generate_password_hash
from tempfile import mkdtemp


# Configure application
app = Flask(__name__)


# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)


# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///finalproject.db")


# Asign API KEYs
DEEPGRAM_KEY = '123456789'

ELEVENLABS_KEY = '123456789'

DEEPL_KEY = "123456789"


@app.route('/')
@login_required
def index():
    return render_template("index.html")


@app.route('/register', methods =["GET", "POST"])
async def register():
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash('Please, provide a username.')
            return redirect("/register")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash('Please, provide a password.')
            return redirect("/register")

        # Ensure confirmation was submitted
        elif not request.form.get("confirmation"):
            flash('Please, provide a confirmation.')
            return redirect("/register")

        # Ensure password and confirmation match
        elif request.form.get("password") != request.form.get("confirmation"):
            flash('Password and confirmation do not match.')
            return redirect("/register")

        else:
            # Query database for username
            rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

            # Check if username already exists and register
            if len(rows) == 1:
                flash('Username already exists.')
                return redirect("/register")

            else:
                username = request.form.get("username")
                hash = generate_password_hash(request.form.get("password"))
                db.execute("INSERT INTO users (username, hash) VALUES(?, ?)", username, hash)

            # Redirect user to Log in
            return redirect("/login")


    # User reached route via GET
    else:
        return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    # session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            flash('Please, provide a username.')
            return redirect("/login")

        # Ensure password was submitted
        elif not request.form.get("password"):
            flash('Please, provide a password.')
            return redirect("/login")

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            flash('Provide valid username and password.')
            return redirect("/login")

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/logout")
def logout():
    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route('/createvoice', methods =["GET", "POST"])
async def createvoice():
    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure file was submitted
        if request.files['audiofile'].filename == '':
            flash('Please, provide a file.')
            return redirect("/createvoice")

        # Ensure name was submitted
        elif not request.form.get("voicename"):
            flash('Please, provide a name.')
            return redirect("/createvoice")

        else:
            voice_name = request.form.get("voicename")
            file = request.files['audiofile']

            # Save file
            file.save(f'files/{file.filename}')
            audiofile = f'./files/{file.filename}'
            audio = open(audiofile, 'rb')

            # Create and store custom voice
            response = elevenlabs_create(ELEVENLABS_KEY = ELEVENLABS_KEY, voice_name = voice_name, audio = audio)
            resp_json = response.json()
            voice_id = resp_json['voice_id']

            db.execute("INSERT INTO voices (user_id, voice_name, voice_id) VALUES(?, ?, ?)", session.get("user_id"), voice_name, voice_id)

            return redirect("/")


    # User reached route via GET
    else:
        return render_template("createvoice.html")


@app.route("/speechtospeech", methods =["GET", "POST"])
async def speechtospeech():

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # User reached route via POST from TRANSLATION
        if request.form.get("translation"):

            # Ensure voice was selected
            if not request.form.get("voice_name"):

                translated_text = request.form.get("translation")

                total_voices = db.execute("SELECT COUNT(voice_name) FROM voices WHERE user_id = 1 OR user_id = ?", session.get("user_id"))[0]["COUNT(voice_name)"]
                voices = []

                for i in range(total_voices):
                    voice_name = db.execute("SELECT voice_name FROM voices WHERE user_id = 1 OR user_id = ?", session.get("user_id"))[i]["voice_name"]
                    voices.append(voice_name)

                flash('Please, select a voice name.')
                return render_template("audio.html", translated_text=translated_text, voices=voices)

            else:
                translated_text = request.form.get("translation")

                # Text to speech (ElevenLabs)
                voice_name = request.form.get("voice_name")
                voice_ID = db.execute("SELECT voice_id FROM voices WHERE voice_name = ?", voice_name)[0]["voice_id"]
                language = 'en'

                response = elevenlabs_voice(ELEVENLABS_KEY = ELEVENLABS_KEY, translated_text = translated_text, voice_ID = voice_ID)

                # Create audio file
                with open('files/audio.mp3', 'wb') as f:
                    f.write(response.content)

                # Download audio file
                return render_template("downloadaudio.html", translated_text = translated_text)

        # User reached route via POST from TRANSCRIPTION
        if request.form.get("message"):

            text = request.form.get("message")

            # Translate (DeepL)
            translator = deepl.Translator(DEEPL_KEY)
            result = translator.translate_text(text, target_lang="EN-US")
            translated_text = result.text

            total_voices = db.execute("SELECT COUNT(voice_name) FROM voices WHERE user_id = 1 OR user_id = ?", session.get("user_id"))[0]["COUNT(voice_name)"]
            voices = []

            for i in range(total_voices):
                voice_name = db.execute("SELECT voice_name FROM voices WHERE user_id = 1 OR user_id = ?", session.get("user_id"))[i]["voice_name"]
                voices.append(voice_name)

            return render_template("audio.html", text=text, translated_text=translated_text, voices=voices)

        # User reached route via POST from FILE
        else:
            # Ensure file was submitted
            if request.files['mainfile'].filename == '':
                flash('Please, provide a file.')
                return redirect("/speechtospeech")

            else:
                # Save file
                file = request.files['mainfile']
                file.save(f'files/{file.filename}')

                audiofile = f'./files/{file.filename}'
                audio = open(audiofile, 'rb')

                text = await transcription(DEEPGRAM_KEY, audio)

                return render_template("text2.html", text=text)

    # User reached route via GET
    else:
        return render_template("speechtospeech.html")


@app.route("/speechtotext", methods =["GET", "POST"])
async def speechtotext():

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # User reached route via POST from MESSAGE
        if request.form.get("message"):

            text = request.form.get("message")

            # Create text file
            with open('files/transcription.txt', 'w', encoding='utf-8') as f:
                f.write(text)

            return render_template("downloadtext.html", text=text)

        # User reached route via POST from FILE
        else:

            # Ensure file was submitted
            if request.files['mainfile'].filename == '':
                flash('Please, provide a file.')
                return redirect("/speechtotext")

            else:
                # Save file
                file = request.files['mainfile']
                file.save(f'files/{file.filename}')

                audiofile = f'./files/{file.filename}'
                audio = open(audiofile, 'rb')

                text = await transcription(DEEPGRAM_KEY, audio)

                return render_template("text.html", text=text)


    # User reached route via GET
    else:
        return render_template("speechtotext.html")


@app.route("/texttospeech", methods =["GET", "POST"])
async def texttospeech():

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # User reached route via POST from MESSAGE
        if not request.form.get("voice_name"):
            flash('Please, select a voice name.')
            return redirect("/texttospeech")

        elif not request.form.get("message"):
            flash('Please, provide a sample text.')
            return redirect("/texttospeech")

        else:
           # Text to speech (ElevenLabs)
            translated_text = request.form.get("message")
            voice_name = request.form.get("voice_name")
            voice_ID = db.execute("SELECT voice_id FROM voices WHERE voice_name = ?", voice_name)[0]["voice_id"]
            language = 'en'

            response = elevenlabs_voice(ELEVENLABS_KEY = ELEVENLABS_KEY, translated_text = translated_text, voice_ID = voice_ID)

            # Create audio file
            with open('files/audio.mp3', 'wb') as f:
                f.write(response.content)

            # Download audio file
            return render_template("downloadaudio.html", translated_text = translated_text)


    # User reached route via GET
    else:
        total_voices = db.execute("SELECT COUNT(voice_name) FROM voices WHERE user_id = 1 OR user_id = ?", session.get("user_id"))[0]["COUNT(voice_name)"]
        print(total_voices)

        voices = []

        for i in range(total_voices):
            voice_name = db.execute("SELECT voice_name FROM voices WHERE user_id = 1 OR user_id = ?", session.get("user_id"))[i]["voice_name"]
            voices.append(voice_name)

        return render_template("texttospeech.html", voices=voices)


@app.route('/downloadtext')
def downloadtext():
    return send_from_directory('./files','transcription.txt', as_attachment=True)

@app.route('/downloadaudio')
def downloadaudio():
    return send_from_directory('./files','audio.mp3', as_attachment=True)
