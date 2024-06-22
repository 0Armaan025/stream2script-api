from flask import Flask
from pytube import YouTube
from moviepy.editor import VideoFileClip, ImageClip
import whisper
from pydub import AudioSegment
from fpdf import FPDF
import os


# so basically I am having 3.9.2 here
# it's 3.11.7 pyenv

app = Flask(__name__)
# WHAT IS THIS

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

def get_text_from_audio(audio_path):
    model = whisper.load_model("base")  # Choose the model size you prefer
    result = model.transcribe(audio_path)
    return result['text']

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

def get_video_length(video_path):
    video = VideoFileClip(video_path)
    duration = video.duration  # duration in seconds
    return duration

@app.route('/')
def index():
    video_link = 'https://www.youtube.com/watch?v=xVVurVNciG4'
    download_video(video_link)
    video_path = 'video.mp4'

    duration = get_video_length(video_path)
    if duration > 20 * 60:
        chunk_length = 120 * 1000  # 120 seconds in milliseconds
        interval = 120  # 120 seconds
    elif duration > 15 * 60:
        chunk_length = 90 * 1000  # 90 seconds in milliseconds
        interval = 90  # 90 seconds
    elif duration > 10 * 60:
        chunk_length = 60 * 1000  # 60 seconds in milliseconds
        interval = 60  # 60 seconds
    elif duration > 5 * 60:
        chunk_length = 30 * 1000  # 30 seconds in milliseconds
        interval = 30  # 30 seconds
    else:
        chunk_length = 10 * 1000  # 10 seconds in milliseconds
        interval = 10  # 10 seconds

    audio_path = convert_to_mp3(video_path)
    audio_chunks = extract_audio_chunks(audio_path, chunk_length=chunk_length)

    text_chunks = []
    for i, chunk in enumerate(audio_chunks):
        chunk_path = f"chunk_{i}.wav"
        chunk.export(chunk_path, format="wav")
        text_chunks.append(get_text_from_audio(chunk_path))
        os.remove(chunk_path)  # Clean up the temporary chunk file

    image_paths = extract_images(video_path, interval=interval)
    create_pdf(text_chunks, image_paths)

    return 'PDF created successfully!'

if __name__ == '__main__':
    app.run(debug=True)
