# video_translation.py

# Import necessary libraries
import whisper
import moviepy.editor as mp
from moviepy.video.tools.subtitles import SubtitlesClip
import pysrt
import os
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

def embed_subtitles(video_file, srt_file, output_file):
    # Load video clip
    clip = mp.VideoFileClip(video_file)
    video_width, video_height = clip.size  # Get the video dimensions
    print(f"Video dimensions: width={video_width}, height={video_height}")

    # Generate a subtitles clip
    generator = lambda txt: mp.TextClip(
        txt,
        font='Helvetica',  # Use 'Arial' if 'Helvetica' isn't available #.Hiragino-Kaku-Gothic-Interface-W0 is available for japanese and english characters
        fontsize=48,
        color='white',
        # bg_color='black', 
        method='caption',
        size=(video_width, None),  # Adjust size as needed
        align='center',
        interline=-10,
        transparent=True
    )

    subtitles = SubtitlesClip(srt_file, generator)

    # Overlay subtitles onto the video
    result = mp.CompositeVideoClip(
        [clip, subtitles.set_position(('center', 'bottom'))],
        size=clip.size
    )

    # Include the original audio track
    result.audio = clip.audio

    # Write the result to a file
    result.write_videofile(
        output_file,
        codec='libx264',
        audio_codec='aac',
        temp_audiofile='temp-audio.m4a',
        remove_temp=True
    )

    # Close clips
    clip.close()
    result.close()

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
