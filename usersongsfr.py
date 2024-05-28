from flask import Flask, session, redirect, request, url_for, render_template
from requests import post, get
from dotenv import load_dotenv
import os
import base64

app = Flask(__name__)

# app.config['SESSION_COOKIE_NAME'] = 'Spotify Cookie'
app.secret_key = '3948q*$)(W)j'

load_dotenv()
client_id = os.getenv("CLIENT_ID")
client_secret = os.getenv("CLIENT_SECRET")
server_url = os.getenv("SERVER_URL")


@app.route('/')
def login():
    uri = "https://accounts.spotify.com/authorize?"
    redirect_uri = server_url + '/redirect'
    scope = 'user-top-read'
    spotify_authorization_url = f"{uri}client_id={client_id}&response_type=code&redirect_uri={redirect_uri}&scope={scope}"
    return redirect(spotify_authorization_url)


@app.route('/redirect')
def get_access_token():
    code = request.args.get('code')
    url = 'https://accounts.spotify.com/api/token'
    auth_str = client_id + ":" + client_secret
    auth_utf = auth_str.encode('utf-8')
    auth_encoded = str(base64.b64encode(auth_utf), 'utf-8')
    body = {
        "grant_type": 'authorization_code',
        "code": code,
        "redirect_uri": server_url + '/redirect'
    }
    headers = {
        "content-type": 'application/x-www-form-urlencoded',
        "Authorization": 'Basic ' + auth_encoded
    }
    result = post(url, headers=headers, data=body).json()
    token = result['access_token']
    session['token'] = token
    return redirect(url_for('get_user_top_songs'))


@app.route('/top-songs')
def get_user_top_songs():
    # branie top piosenek

    how_many_songs = 20
    term = 'medium'  # short/medium/long

    token = session.get('token')
    url = f'https://api.spotify.com/v1/me/top/tracks?time_range={term}_term&limit={how_many_songs}'
    headers = {
        'Authorization': 'Bearer ' + token
    }
    top_songs_result = get(url, headers=headers).json()['items']

    top_songs_info = []
    top_songs_ids = []
    top_songs_artist_ids = []
    for nr, song in enumerate(top_songs_result):
        top_songs_info.append(
            {
                'id': song['id'],
                'top': nr + 1,
                'title': song['name'],
                'artists': [artist['name'] for artist in song['artists']],
                'popularity': song['popularity'],
                'image_url': song['album']['images'][0]['url'],
                'url': song['external_urls']['spotify'],
            }
        )
        top_songs_ids.append(song['id'])
        top_songs_artist_ids.append(song['artists'][0]['id'])

    # tworzenie tekstu dla zapytania o analize utworów
    top_songs_ids_text = ''
    for songid in top_songs_ids:
        top_songs_ids_text += songid + ','

    # branie audioanalizy dla utworów
    url = f"https://api.spotify.com/v1/audio-features?ids={top_songs_ids_text}"
    analized_songs = get(url, headers=headers).json()['audio_features']

    # tworzenie tekstu zapytania o artystów
    top_songs_artist_ids_text = ''
    for artist in top_songs_artist_ids:
        top_songs_artist_ids_text += artist + ','

    # branie genre artystów
    url = f'https://api.spotify.com/v1/artists?ids={top_songs_artist_ids_text}'
    artists_info = get(url, headers=headers).json()['artists']
    # dictionary dostępnych gatunków:
    animal_genre = {
        'panda': ['k-pop', 'j-pop'],
        'zebra': ['pop', 'alt z'],
        'rhino': ['rock', 'metal', 'punk'],
        'sloth': ['jazz'],
        'parrot': ['dance pop', 'dance'],
        'snake': ['electronic'],
        'cat': ['lo-fi', 'chill', 'background music'],
        'gorilla': ['rap', 'trap'],
        'monkey': ['hip hop', 'hip'],
        'horse': ['country'],
        'swan': ['classical']
    }

    def genre_to_animal(genres):
        for genre in genres:
            genre.lower()
            words = genre.split(' ')
            for word in words:
                for animal, genres in animal_genre.items():
                    if genre in genres or word in genres:
                        return animal
        return 'default'

    # dodawanie rzeczy z analizy i od artystow do songs_info
    for a, song in enumerate(top_songs_info):
        if analized_songs[a] is not None:
            # zamiana bpm na czas[ms]/skok (120bpm = 2bps = 1 skok / sekunde)
            song['tempo'] = 120 / (int(analized_songs[a]['tempo'])) * 1000
        else:
            song['tempo'] = '0'
        if artists_info[a] is not None:
            song['animal'] = f"{genre_to_animal(artists_info[a]['genres'])}.png"
        else:
            song['animal'] = 'default'

    session['top_info'] = top_songs_info
    return render_template('zoo.html', data=top_songs_info)
    # return top_songs_info


@app.route('/song/<top>')
def song_details(top):
    song_info = session['top_info'][int(top) - 1]
    return render_template('song.html', data=song_info)
