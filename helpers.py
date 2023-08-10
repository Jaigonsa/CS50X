import os
import requests
import urllib.parse

from flask import redirect, render_template, request, session
from functools import wraps
from deepgram import Deepgram


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if session.get("user_id") is None:
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


# Transcription (Speech to text) with DEEPGRAM
async def transcription(DEEPGRAM_KEY, audio):
    deepgram = Deepgram(DEEPGRAM_KEY)
    source = {'buffer': audio, 'mimetype': 'audio/mpeg'}
    transcription_options = {'punctuate': True, 'diarize': False, 'paragraphs': True, 'language': 'es'}
    response = await deepgram.transcription.prerecorded(source, transcription_options)
    transcript = response['results']['channels'][0]['alternatives'][0]['paragraphs']['transcript']
    return transcript


# Reading (Speech to text) with ELEVENLABS
def elevenlabs_voice(ELEVENLABS_KEY, translated_text, voice_ID):
    url = 'https://api.elevenlabs.io/v1/text-to-speech/%s'%voice_ID
    headers = {
        'accept': 'audio/mpeg',
        'xi-api-key': ELEVENLABS_KEY,
        'Content-Type': 'application/json'
    }
    data = {
        'text': translated_text
    }
    response = requests.post(url, headers=headers, json=data)
    return response


# Create voice with ELEVENLABS
def elevenlabs_create(ELEVENLABS_KEY, voice_name, audio):
    url = 'https://api.elevenlabs.io/v1/voices/add'
    headers = {
        'accept': 'application/json',
        'xi-api-key': ELEVENLABS_KEY,
        }
    data = {
        'name': voice_name,
        }

    files = {
        'files': audio,
        }
    response = requests.post(url, headers=headers, data=data, files=files)

    return response