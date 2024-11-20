# video_translation.py

# Import necessary libraries
import os

# Get the absolute path to the directory containing this script
current_dir = os.path.dirname(os.path.abspath(__file__))

# Construct the absolute path to the ffmpeg binary
ffmpeg_binary = os.path.join(current_dir, 'bin', 'ffmpeg')

# Set FFMPEG_BINARY to the absolute path of the ffmpeg binary
os.environ['FFMPEG_BINARY'] = ffmpeg_binary

# Add the directory containing ffmpeg to PATH
os.environ['PATH'] = os.path.dirname(ffmpeg_binary) + os.pathsep + os.environ.get('PATH', '')

# Check if ffmpeg exists at the specified path
if not os.path.exists(ffmpeg_binary):
    print(f"FFmpeg binary not found at {ffmpeg_binary}")
else:
    print(f"FFmpeg binary found at {ffmpeg_binary}")
 
 
# for imagemagick path settings 
from moviepy.config import change_settings 
IMAGEMAGICK_BINARY = "/usr/bin/convert"  # Replace with the actual path from `which convert`
change_settings({"IMAGEMAGICK_BINARY": IMAGEMAGICK_BINARY})
# testing if convert binary can be used. DELETE once confirmed
from moviepy.editor import TextClip

try:
    text = TextClip("Hello World", fontsize=50, color="white", font="Arial", method="text")
    text.save_frame("/tmp/test_frame.png")
    print("TextClip successfully used ImageMagick!")
except Exception as e:
    print(f"Error using TextClip: {e}")
    
print(f"IMAGEMAGICK_BINARY is set to: {IMAGEMAGICK_BINARY}")

  
import whisper
import moviepy.editor as mp
#import ffmpeg
# import moviepy.config as mpconfig
# mpconfig.FFMPEG_BINARY = './bin/ffmpeg'
from moviepy.video.tools.subtitles import SubtitlesClip
import pysrt
from dotenv import load_dotenv
from openai import OpenAI

#from memory_profiler import profile

# Set your OpenAI API key

# Retrieve OpenAI API key directly from environment variable
api_key = os.getenv("OPENAI_API_KEY")
client = OpenAI(api_key=api_key)

if not api_key:
    raise ValueError("API key is not set. Please set the OPENAI_API_KEY environment variable.")


# Your existing functions with minimal changes
def extract_audio(video_file, audio_file):
    if not os.path.exists(audio_file):
        clip = mp.VideoFileClip(video_file)
        clip.audio.write_audiofile(audio_file)
        clip.close()
    else:
        print(f"Audio file '{audio_file}' already exists. Skipping extraction.")

# Load the Whisper model
# whisper_cache_dir = os.getenv('WHISPER_CACHE_DIR', '/app/.cache')
# model = whisper.load_model('small', download_root=whisper_cache_dir)
model = whisper.load_model('small')

def transcribe_audio(audio_file, source_language, model_size='small'):
    
    if (source_language=="japanese"):
        source_language="ja"
        
    elif (source_language=="english"):
        source_language="en"
    # Transcribe the audio
    result = model.transcribe(
        audio_file,
        language=source_language,  # Use the source_language parameter
        task='transcribe'          # Get transcription without translation
    )
    return result['segments']

def translate_text(segments, source_language, target_language):
    translated_segments = []
    for segment in segments:
        original_text = segment['text'].strip()

        # Use OpenAI GPT-4 to translate
        response = client.chat.completions.create(
            model='gpt-4o-mini',  # Use the appropriate model
            messages=[
                {"role": "system", "content": f"You are a professional translator specializing in {source_language} to {target_language} translation. Translate the following text accurately. Do not include any additional commentary."},
                {"role": "user", "content": original_text}
            ],
            temperature=0.7,
            max_tokens=500
        )
        translated_text = response.choices[0].message.content.strip()

        # Append the translated text with the original timing
        translated_segments.append({
            'start': segment['start'],
            'end': segment['end'],
            'text': translated_text
        })
    return translated_segments

def write_srt(translated_segments, srt_file):
    subs = pysrt.SubRipFile()
    for i, segment in enumerate(translated_segments):
        # Create a new subtitle item
        sub = pysrt.SubRipItem()
        sub.index = i + 1
        sub.start.seconds = segment['start']
        sub.end.seconds = segment['end']
        sub.text = segment['text']
        subs.append(sub)
    # Save to SRT file
    subs.save(srt_file, encoding='utf-8')

# Step 5: Generate Subtitle Images with Pillow
def generate_subtitle_image(txt, video_width):
    from PIL import Image, ImageDraw, ImageFont
    import os
    import time

    # Load the font
    font_path = os.path.join(os.path.dirname(__file__), "fonts", "NotoSansJP-VariableFont_wght.ttf")
    font = ImageFont.truetype(font_path, size=48)  # Font size 48

    # Get text dimensions
    text_bbox = font.getbbox(txt)
    text_width = text_bbox[2] - text_bbox[0]
    text_height = text_bbox[3] - text_bbox[1]

    # Create a transparent image
    img = Image.new("RGBA", (video_width, text_height + 40), (0, 0, 0, 0))

    draw = ImageDraw.Draw(img)

    # Simulating bold text by drawing the same text multiple times (slight offset)
    bold_offset = 1  # Adjust for more or less boldness

    # Adding a black outline around the text
    outline_offset = 2  # Thickness of the outline
    for x in range(-outline_offset, outline_offset + 1):
        for y in range(-outline_offset, outline_offset + 1):
            if x != 0 or y != 0:  # Avoid overwriting the center with black
                draw.text(
                    ((video_width - text_width) // 2 + x, 20 + y),
                    txt,
                    font=font,
                    fill="black"  # Black outline
                )

    # Draw the white text in the center to simulate boldness
    for x in range(-bold_offset, bold_offset + 1):
        for y in range(-bold_offset, bold_offset + 1):
            draw.text(
                ((video_width - text_width) // 2 + x, 20 + y),
                txt,
                font=font,
                fill="white"  # White text
            )

    # Save the image to a temporary file
    temp_file = f"temp_subtitle_{time.time()}.png"
    img.save(temp_file)
    return temp_file


# Step 6: Embed Subtitles into the Video
def embed_subtitles(video_file, srt_file, output_file):
    clip = mp.VideoFileClip(video_file)
    video_width, _ = clip.size
    
    subtitles = []
    srt = pysrt.open(srt_file, encoding='utf-8')
    
    for sub in srt:
        subtitle_image_path = generate_subtitle_image(sub.text, video_width)
        subtitle_clip = (
            mp.ImageClip(subtitle_image_path)
            .set_start(sub.start.ordinal / 1000)  # Convert ms to seconds
            .set_duration((sub.end.ordinal - sub.start.ordinal) / 1000)  # Duration in seconds
            .set_position(('center', 'bottom'))
        )
        subtitles.append(subtitle_clip)
    
    final_clip = mp.CompositeVideoClip([clip] + subtitles)
    final_clip.write_videofile(output_file, codec='libx264', audio_codec='aac')

# Main Execution function accepting parameters
def main(input_video_path, output_video_file, source_language, target_language, title):
    # Define paths based on input video path
    audio_file = input_video_path + '.wav'
    srt_file = input_video_path + '.srt'

    # Step 1: Extract audio from the video
    print("Extracting audio...")
    extract_audio(input_video_path, audio_file)

    # Step 2: Transcribe the audio
    print("Transcribing audio...")
    segments = transcribe_audio(audio_file, source_language)

    # Step 3: Translate the transcribed text
    print("Translating text...")
    translated_segments = translate_text(segments, source_language, target_language)

    # Step 4: Write to SRT file
    print("Generating SRT file...")
    write_srt(translated_segments, srt_file)

    # Step 5: Embed subtitles into the video
    print("Embedding subtitles into video...")
    embed_subtitles(input_video_path, srt_file, output_video_file)

    print(f"Subtitle file '{srt_file}' and video file '{output_video_file}' have been created.")

    # Clean up temporary files
    if os.path.exists(audio_file):
        os.remove(audio_file)
    if os.path.exists(srt_file):
        os.remove(srt_file)

# This allows the script to be run independently for testing
if __name__ == "__main__":
    # Example usage with hardcoded values
    main(
        input_video_path='hidad_dub.mp4',
        output_video_file='hidadEN.mp4',
        source_language='ja',
        target_language='en',
        title='Sample Video'
    )
