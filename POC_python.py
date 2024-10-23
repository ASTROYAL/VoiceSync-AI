import os

import openai
import requests
import streamlit as st
from google.cloud import speech, texttospeech
from moviepy.editor import AudioFileClip, VideoFileClip
from pydub import AudioSegment


def main():
    st.title("PoC: Replace Video Audio with AI-Generated Voice")

    # Video file uploader
    uploaded_video = st.file_uploader("Upload a video file", type=["mp4"])

    # Use session state to store audio segments
    if 'segments' not in st.session_state:
        st.session_state.segments = []

    if uploaded_video is not None:
        # Save the uploaded video to a temporary file
        video_path = "uploaded_video.mp4"
        with open(video_path, "wb") as f:
            f.write(uploaded_video.read())

        # Extract the audio from the video
        video = VideoFileClip(video_path)
        audio = video.audio
        audio.write_audiofile("extracted_audio.wav")
        st.audio("extracted_audio.wav", format="audio/wav")

        # Split audio into smaller segments
        if st.button("Split Audio"):
            st.session_state.segments = split_audio("extracted_audio.wav", 30000)  # Split into 30-second segments (30000 ms)
            st.text(f"Split Audio into {len(st.session_state.segments)} segments.")
            for segment in st.session_state.segments:
                st.audio(segment, format="audio/wav")

        # Transcribe each audio segment
        if st.button("Transcribe Audio"):
            if st.session_state.segments:  # Ensure segments are available before transcribing
                transcription = ""
                for segment in st.session_state.segments:
                    segment_transcription = transcribe_audio(segment)
                    transcription += segment_transcription + " "
                st.text(f"Transcription: {transcription}")
            else:
                st.warning("Please split the audio into segments first.")

            # Correct transcription using GPT-4
            if st.button("Correct Transcription"):
                if transcription:  # Ensure transcription is available before correcting
                    corrected_transcription = correct_transcription(transcription)
                    st.text(f"Corrected Transcription: {corrected_transcription}")

                    # Generate new audio using Google Text-to-Speech
                    if st.button("Generate AI Voice"):
                        generate_audio(corrected_transcription)
                        st.audio("generated_audio.mp3", format="audio/mp3")

                        # Replace the audio in the original video
                        if st.button("Replace Audio and Download Video"):
                            final_video_path = replace_audio_in_video(video_path, "generated_audio.mp3")
                            st.video(final_video_path)
                            with open(final_video_path, "rb") as f:
                                st.download_button("Download Video", data=f, file_name="final_video.mp4")

# Google Speech-to-Text API Function
def transcribe_audio(audio_file):
    client = speech.SpeechClient()
    with open(audio_file, "rb") as file:
        audio_data = file.read()
    audio = speech.RecognitionAudio(content=audio_data)
    config = speech.RecognitionConfig(language_code="en-US")
    response = client.recognize(config=config, audio=audio)
    transcription = " ".join([result.alternatives[0].transcript for result in response.results])
    return transcription

# GPT-4 for transcription correction
def correct_transcription(transcription):
    openai.api_key = "YOUR_OPENAI_API_KEY"  # Replace with your actual OpenAI key
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "Correct grammatical mistakes and remove filler words."},
            {"role": "user", "content": transcription}
        ]
    )
    return response.choices[0].message['content']

# Google Text-to-Speech API for audio generation
def generate_audio(text):
    client = texttospeech.TextToSpeechClient()
    input_text = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US", name="en-US-Standard-J", ssml_gender=texttospeech.SsmlVoiceGender.MALE
    )
    audio_config = texttospeech.AudioConfig(audio_encoding=texttospeech.AudioEncoding.MP3)
    response = client.synthesize_speech(input=input_text, voice=voice, audio_config=audio_config)
    with open("generated_audio.mp3", "wb") as out:
        out.write(response.audio_content)

# Function to replace audio in the video
def replace_audio_in_video(video_path, audio_path):
    video = VideoFileClip(video_path)
    new_audio = AudioFileClip(audio_path)
    final_video = video.set_audio(new_audio)
    final_video_path = "final_video_with_new_audio.mp4"
    final_video.write_videofile(final_video_path)
    return final_video_path

# Function to split audio into smaller segments
def split_audio(audio_file, segment_length_ms):
    audio = AudioSegment.from_wav(audio_file)
    segments = []

    for i in range(0, len(audio), segment_length_ms):
        segment = audio[i:i + segment_length_ms]
        segment_file = f"segment_{i // segment_length_ms}.wav"
        segment.export(segment_file, format="wav")
        segments.append(segment_file)
    
    return segments

if __name__ == "__main__":
    main()
