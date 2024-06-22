from flask import Flask, request, jsonify
from pytube import YouTube
from moviepy.editor import VideoFileClip, ImageClip
import whisper
from pydub import AudioSegment
from fpdf import FPDF
import os
import anthropic
from dotenv import load_dotenv
import logging

# Load environment variables
load_dotenv()

# Initialize Anthropics client
client = anthropic.Anthropic()

# Initialize Flask app
app = Flask(__name__)

# Configure logging
logging.basicConfig(level=logging.INFO)

def summarize_content(content):
    try:
        message = client.messages.create(
            model="claude-3-opus-20240229",
            max_tokens=1000,
            temperature=0,
            system="You are a cool content summarizer",
            messages=[
                {
                    "role": "user",
                    "content": f"Please summarize this: {content}"
                }
            ]
        )
        
        summarized_content = message.content[0].text
        return summarized_content
    except Exception as e:
        logging.error(f"Error in summarizing content: {e}")
        return "Error in summarizing content."

def download_video(link, filename='video.mp4'):
    if not os.path.exists(filename):
        try:
            youtubeObject = YouTube(link)
            youtubeObject = youtubeObject.streams.get_highest_resolution()
            youtubeObject.download(filename=filename)
            logging.info("Download is completed successfully")
        except Exception as e:
            logging.error(f"An error has occurred: {e}")
    else:
        logging.info("Video already downloaded")

def convert_to_mp3(video_path):
    audio_path = "example.mp3"
    if not os.path.exists(audio_path):
        try:
            video = VideoFileClip(video_path)
            video.audio.write_audiofile(audio_path)
        except Exception as e:
            logging.error(f"Error converting video to mp3: {e}")
    return audio_path

def get_text_from_audio(audio_path):
    try:
        model = whisper.load_model("base")
        result = model.transcribe(audio_path)
        return result['text']
    except Exception as e:
        logging.error(f"Error in transcribing audio: {e}")
        return "Error in transcribing audio."

def extract_audio_chunks(audio_path, chunk_length=5000):
    try:
        sound = AudioSegment.from_mp3(audio_path)
        chunks = [sound[i:i + chunk_length] for i in range(0, len(sound), chunk_length)]
        return chunks
    except Exception as e:
        logging.error(f"Error in extracting audio chunks: {e}")
        return []

def extract_images(video_path, interval=5):
    try:
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
    except Exception as e:
        logging.error(f"Error in extracting images: {e}")
        return []

def create_pdf(text_chunks, image_paths, summarized_chunks=None):
    try:
        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=15)
        pdf.set_font("Arial", size=12)

        for i, image_path in enumerate(image_paths):
            pdf.add_page()

            # Add header
            pdf.set_font("Arial", "B", 16)
            pdf.cell(0, 10, "Summary", 0, 1, 'C')
            pdf.set_font("Arial", size=12)
            pdf.ln(10)  # Add a line break

            # Add summarized content if available
            if summarized_chunks and i < len(summarized_chunks):
                summarized_chunk = summarized_chunks[i]
                # Limit summary to 80 words
                summarized_chunk = ' '.join(summarized_chunk.split()[:80])
                pdf.multi_cell(0, 10, "Summary: " + summarized_chunk)
                pdf.ln(5)  # Add a line break after summary

            # Add text content
            if i < len(text_chunks):
                text_chunk = text_chunks[i]
                pdf.multi_cell(0, 10, text_chunk)
                pdf.ln(5)  # Add a line break after text

            # Add image
            if os.path.exists(image_path):
                pdf.image(image_path, x=10, y=pdf.get_y(), w=190)
                pdf.ln(10)  # Add a line break after image

        pdf.output("output.pdf")
    except Exception as e:
        logging.error(f"Error in creating PDF: {e}")

def get_video_length(video_path):
    try:
        video = VideoFileClip(video_path)
        duration = video.duration
        return duration
    except Exception as e:
        logging.error(f"Error in getting video length: {e}")
        return 0



@app.route('/')
def index():
    video_link = 'https://www.youtube.com/watch?v=CTnJyZZNOjU'
    download_video(video_link)
    video_path = 'video.mp4'

    duration = get_video_length(video_path)
    if duration > 20 * 60:
        chunk_length = 120 * 1000
        interval = 120
    elif duration > 15 * 60:
        chunk_length = 90 * 1000
        interval = 90
    elif duration > 10 * 60:
        chunk_length = 60 * 1000
        interval = 60
    elif duration > 5 * 60:
        chunk_length = 30 * 1000
        interval = 30
    else:
        chunk_length = 10 * 1000
        interval = 10

    audio_path = convert_to_mp3(video_path)
    audio_chunks = extract_audio_chunks(audio_path, chunk_length=chunk_length)

    text_chunks = []
    for i, chunk in enumerate(audio_chunks):
        chunk_path = f"chunk_{i}.wav"
        chunk.export(chunk_path, format="wav")
        text_chunks.append(get_text_from_audio(chunk_path))
        os.remove(chunk_path)

    image_paths = extract_images(video_path, interval=interval)
    create_pdf(text_chunks, image_paths)

    

    return 'PDF created successfully!'

@app.route('/summarize')
def summarize():
    video_link = 'https://www.youtube.com/watch?v=CTnJyZZNOjU'
    download_video(video_link)
    video_path = 'video.mp4'

    duration = get_video_length(video_path)
    chunk_length = 2 * 60 * 1000  # 2 minutes chunks
    interval = 2 * 60  # 2 minutes

    audio_path = convert_to_mp3(video_path)
    audio_chunks = extract_audio_chunks(audio_path, chunk_length=chunk_length)

    text_chunks = []
    summarized_chunks = []
    for i, chunk in enumerate(audio_chunks):
        chunk_path = f"chunk_{i}.wav"
        chunk.export(chunk_path, format="wav")
        text = get_text_from_audio(chunk_path)
        text_chunks.append(text)
        summarized_chunks.append(summarize_content(text))
        os.remove(chunk_path)

    image_paths = extract_images(video_path, interval=interval)
    create_pdf(text_chunks, image_paths, summarized_chunks=summarized_chunks)

    

    return 'Summarized PDF created successfully!'

if __name__ == '__main__':
    app.run(debug=True)
