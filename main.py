from flask import Flask, request, jsonify, send_file
from pytube import YouTube
from moviepy.editor import VideoFileClip, ImageClip
import whisper
from pydub import AudioSegment
from fpdf import FPDF
import os
import anthropic
from dotenv import load_dotenv
import logging
from flask_cors import CORS 

# Load environment variables
load_dotenv()


client = anthropic.Anthropic()


app = Flask(__name__)
CORS(app)


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
        pdf.add_font('DejaVuSans', '', 'DejaVuSans.ttf', uni=True)
        pdf.set_font('DejaVuSans', size=12)

        for i, (text_chunk, image_path) in enumerate(zip(text_chunks, image_paths)):
            pdf.add_page()

            
            if summarized_chunks and i < len(summarized_chunks):
                summarized_chunk = summarized_chunks[i]
                pdf.set_font("DejaVuSans", size=16)
                pdf.cell(0, 10, "Summary", 0, 1, 'C')
                pdf.set_font("DejaVuSans", size=12)
                pdf.ln(10)  

                
                words = summarized_chunk.split()
                for j in range(0, len(words), 80):
                    pdf.multi_cell(0, 10, "Summary: " + ' '.join(words[j:j+80]))
                    pdf.ln(5)  

       
            pdf.multi_cell(0, 10, text_chunk)
            pdf.ln(5)

            
            if os.path.exists(image_path):
                pdf.image(image_path, x=10, y=pdf.get_y(), w=190)
                pdf.ln(10)  

        output_pdf_path = "output.pdf"
        pdf.output(output_pdf_path)
        cleanup_files()
        return output_pdf_path  
    except Exception as e:
        logging.error(f"Error in creating PDF: {e}")
        return None

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
    return 'Welcome to the Video to PDF converter!'

@app.route('/get-pdf')
def get_pdf():
    video_link = request.args.get('video_link')
    if not video_link:
        return 'Please provide a YouTube video link.', 400
    
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
    output_pdf_path = create_pdf(text_chunks, image_paths)

    if output_pdf_path:
        return send_file(output_pdf_path, as_attachment=True)
    else:
        return "Failed to generate PDF.", 500

@app.route('/summarize')
def summarize():
    youtube_url = request.args.get('video_link')
    if not youtube_url:
        return 'Please provide a YouTube video link.', 400

    download_video(youtube_url)
    video_path = 'video.mp4'

    duration = get_video_length(video_path)
    chunk_length = 2 * 60 * 1000  
    interval = 2 * 60  

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
    output_pdf_path = create_pdf(text_chunks, image_paths, summarized_chunks=summarized_chunks)

    if output_pdf_path:
        return send_file(output_pdf_path, as_attachment=True)
    else:
        return "Failed to generate PDF.", 500

def cleanup_files():
    try:
        
        for filename in os.listdir('.'):
            if filename.startswith('frame_') and filename.endswith('.jpg'):
                os.remove(filename)
                print(f"Deleted: {filename}")

        
        if os.path.exists('example.mp3'):
            os.remove('example.mp3')
            print("Deleted: example.mp3")

        
        if os.path.exists('video.mp4'):
            os.remove('video.mp4')
            print("Deleted: video.mp4")

        print("Cleanup completed successfully.")
    except Exception as e:
        print(f"Error during cleanup: {e}")


if __name__ == '__main__':
    app.run(debug=True)
