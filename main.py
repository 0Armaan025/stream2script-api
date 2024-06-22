from flask import Flask
from pytube import YouTube
from moviepy.editor import *
import speech_recognition as sr
from pydub import AudioSegment
from fpdf import FPDF
import os

app = Flask(__name__)

def download_video(link):
    youtubeObject = YouTube(link)
    youtubeObject = youtubeObject.streams.get_highest_resolution()
    try:
        youtubeObject.download(filename='video.mp4')
    except Exception as e:
        print(f"An error has occurred: {e}")
    print("Download is completed successfully")

def convert_to_mp3(video_path):
    video = VideoFileClip(video_path)
    audio_path = "example.mp3"
    video.audio.write_audiofile(audio_path)
    return audio_path

def get_text_from_audio_chunk(audio_chunk_path):
    r = sr.Recognizer()
    with sr.AudioFile(audio_chunk_path) as source:
        audio_text = r.record(source)
        try:
            text = r.recognize_google(audio_text)
        except sr.UnknownValueError:
            text = "[Unintelligible]"
    return text

def extract_audio_chunks(audio_path, chunk_length=5000):
    sound = AudioSegment.from_mp3(audio_path)
    chunks = [sound[i:i + chunk_length] for i in range(0, len(sound), chunk_length)]
    return chunks

def extract_images(video_path, interval=5):
    video = VideoFileClip(video_path)
    duration = int(video.duration)
    image_paths = []

    for timestamp in range(0, duration, interval):
        frame = video.get_frame(timestamp)
        image_path = f"frame_{timestamp}.jpg"
        frame_image = ImageClip(frame)
        frame_image.save_frame(image_path)
        image_paths.append(image_path)

    return image_paths

def create_pdf(text_chunks, image_paths):
    pdf = FPDF()
    pdf.set_auto_page_break(auto=True, margin=15)
    pdf.set_font("Arial", size=12)

    for i, image_path in enumerate(image_paths):
        pdf.add_page()

        if i < len(text_chunks):
            text_chunk = text_chunks[i]
            pdf.multi_cell(0, 10, text_chunk)

        if os.path.exists(image_path):
            pdf.image(image_path, x=10, y=80, w=100)

    pdf.output("output.pdf")

@app.route('/')
def index():
    video_link = 'https://www.youtube.com/watch?v=YycJFPHPw4s'
    download_video(video_link)
    video_path = 'video.mp4'

    audio_path = convert_to_mp3(video_path)
    audio_chunks = extract_audio_chunks(audio_path, chunk_length=5000)

    text_chunks = []
    for i, chunk in enumerate(audio_chunks):
        chunk_path = f"chunk_{i}.wav"
        chunk.export(chunk_path, format="wav")
        text_chunks.append(get_text_from_audio_chunk(chunk_path))
        os.remove(chunk_path) 

    image_paths = extract_images(video_path, interval=5)
    create_pdf(text_chunks, image_paths)

    return 'PDF created successfully!'

if __name__ == '__main__':
    app.run(debug=True)
