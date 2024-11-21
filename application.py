from flask import Flask, request, jsonify, send_from_directory
from werkzeug.utils import secure_filename
from flask_cors import CORS
from flask_mail import Mail, Message
import threading
import os
from process_video import main as process_video

import logging

logging.basicConfig(level=logging.INFO)

app = Flask(__name__)
CORS(app, resources={r"/*": {"origins": ["https://trustvideotranslate.com", "https://api.trustvideotranslate.com"]}})

# Error handler for unhandled exceptions
@app.errorhandler(Exception)
def handle_exception(e):
    logging.exception("An error occurred: %s", e)
    return "Internal Server Error", 500

# Configuration
app.config['UPLOAD_FOLDER'] = 'uploads'
app.config['TRANSLATED_FOLDER'] = 'static/translated_videos'
app.config['ALLOWED_EXTENSIONS'] = {'mp4', 'mov'}
app.config['MAX_CONTENT_LENGTH'] = 1 * 1024 * 1024 * 1024  # 1GB max file size

# Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'traccoon1999@gmail.com'
app.config['MAIL_PASSWORD'] = 'gnvc cauk csja ifun'

mail = Mail(app)

# Ensure directories exist
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['TRANSLATED_FOLDER'], exist_ok=True)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

# Main route
@app.route('/', methods=['GET'])
def home():
    logging.info("Home route accessed")
    return "Hello, your Flask app is running!"

@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    email = request.form.get('email')
    source_language = request.form.get('sourceLanguage')
    target_language = request.form.get('targetLanguage')
    title = request.form.get('title')

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    if file and allowed_file(file.filename):
        # Secure the file name and replace spaces with hyphens
        filename = secure_filename(file.filename.replace(" ", "-"))
        input_video_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(input_video_path)

        # Generate a unique output filename
        output_filename = f"translated_{filename}"
        output_video_path = os.path.join(app.config['TRANSLATED_FOLDER'], output_filename)

        # Start background processing
        threading.Thread(target=process_video_task, args=(
            input_video_path,
            output_video_path,
            source_language,
            target_language,
            title,
            email
        )).start()

        return jsonify({'message': '翻訳が開始しました！メールにて送信するのでしばらくお待ちください。'}), 202
    else:
        return jsonify({'error': 'Invalid file type'}), 400

def process_video_task(input_video_path, output_video_path, source_language, target_language, title, email):
    logging.info("Starting video processing task")
    try:
        # Call your existing video translation code
        process_video(
            input_video_path=input_video_path,
            output_video_file=output_video_path,
            source_language=source_language,
            target_language=target_language,
            title=title
        )

        # Generate a download link for the video
        video_filename = os.path.basename(output_video_path)
        video_download_link = f"https://api.trustvideotranslate.com/static/translated_videos/{video_filename}"

        # Move the SRT file to the translated folder
        srt_filename = os.path.splitext(video_filename)[0] + ".srt"
        srt_file_path = os.path.splitext(input_video_path)[0] + ".srt"  # Match the logic in process_video.py
        if os.path.exists(srt_file_path):
            translated_srt_path = os.path.join(app.config['TRANSLATED_FOLDER'], srt_filename)
            os.rename(srt_file_path, translated_srt_path)
            srt_download_link = f"https://api.trustvideotranslate.com/static/translated_videos/{srt_filename}"
        else:
            srt_download_link = None
            logging.warning("SRT file not found for video: %s", input_video_path)

        # Send email notification
        with app.app_context():
            send_email(email, video_download_link, srt_download_link)

    except Exception as e:
        logging.error("Error processing video: %s", e)

def send_email(recipient, video_download_link, srt_download_link=None):
    msg = Message(
        'Your Translated Video and Subtitles are Ready',
        sender='traccoon1999@gmail.com',
        recipients=[recipient]
    )
    msg.body = (
        f"こんにちは,\n\n翻訳動画が完成いたしました。以下のリンクからダウンロードできます:\n\n"
        f"動画: {video_download_link}\n"
    )
    if srt_download_link:
        msg.body += f"字幕ファイル: {srt_download_link}\n"
    else:
        msg.body += "字幕ファイルが生成されませんでした。\n"
    msg.body += "\nありがとうございました！\n\nTrust動画翻訳チーム一同"
    mail.send(msg)

@app.route('/static/translated_videos/<path:filename>')
def serve_translated_videos(filename):
    return send_from_directory(app.config['TRANSLATED_FOLDER'], filename)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5001))
    app.run(host='0.0.0.0', port=port)