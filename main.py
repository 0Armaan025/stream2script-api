# INIT
from flask import Flask
from pytube import YouTube


app = Flask(__name__)



@app.route('/')
def index():
    download_video('https://www.youtube.com/watch?v=TK4N5W22Gts')
    return 'hi arcade people!'


def download_video(link):
    youtubeObject = YouTube(link)
    youtubeObject = youtubeObject.streams.get_highest_resolution()
    try:
        youtubeObject.download()
    except:
        print("An error has occurred")
    print("Download is completed successfully")


if __name__ == '__main__':
    app.run(debug=True)