from google.cloud import speech_v1p1beta1 as speech
from google.cloud import texttospeech
import os
import tempfile
from pydub import AudioSegment
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip
from moviepy.video.tools.subtitles import SubtitlesClip, TextClip
os.environ["GOOGLE_APPLICATION_CREDENTIALS"]="key.json"

# def speak(text, languageCode, voiceName=None, speakingRate=1):
  
#     # Instantiates a client
#     client = texttospeech.TextToSpeechClient()

#     # Set the text input to be synthesized
#     synthesis_input = texttospeech.SynthesisInput(text=text)

#     # Build the voice request, select the language code ("en-US") and the ssml
#     # voice gender ("neutral")
#     if not voiceName:
#         voice = texttospeech.VoiceSelectionParams(
#             language_code=languageCode, ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
#         )
#     else:
#         voice = texttospeech.VoiceSelectionParams(
#             language_code=languageCode, name=voiceName
#         )

#     # Select the type of audio file you want returned
#     audio_config = texttospeech.AudioConfig(
#         audio_encoding=texttospeech.AudioEncoding.MP3,
#         speaking_rate=speakingRate
#     )

#     # Perform the text-to-speech request on the text input with the selected
#     # voice parameters and audio file type
#     response = client.synthesize_speech(
#         input=synthesis_input,
#         voice=voice,
#         audio_config=audio_config
#     )
    
#     return response.audio_content




# def speakUnderDuration(text, languageCode, durationSecs, voiceName=None):
  
#     baseAudio = speak(text, languageCode, voiceName=voiceName)
    
#     assert len(baseAudio)
#     # f = tempfile.NamedTemporaryFile(mode="w+b")
#     with open(os.path.join("new.mp3"), 'wb') as d: 
#       d.write(baseAudio)
#       d.flush()
#       baseDuration = AudioSegment.from_mp3(file=d.name).duration_seconds
#       print(baseDuration)
#       d.close()
#     ratio = baseDuration / durationSecs
#     if ratio <= 1:
#         return baseAudio
#     ratio = round(ratio, 1)
#     if ratio > 4:
#         ratio = 10
#     return speak(text, languageCode, voiceName=voiceName, speakingRate=ratio)


def stitch_audio(sentences, audioDir, movieFile, outFile, srtPath=None, overlayGain=30):
   
    # Files in the audioDir should be labeled 0.wav, 1.wav, etc.
    audioFiles = os.listdir(audioDir)
    audioFiles.sort(key=lambda x: int(x.split('.')[0]))

    # Grab the computer-generated audio file
    segments = [AudioSegment.from_mp3(
        os.path.join(audioDir, x)) for x in audioFiles]
    # Also, grab the original audio
    dubbed = AudioSegment.from_file(movieFile)
    
    
    
    # Place each computer-generated audio at the correct timestamp
    for sentence, segment in zip(sentences, segments):
        dubbed = dubbed.overlay(
            segment, position=sentence['start_time'] * 1000, gain_during_overlay=overlayGain)
    # Write the final audio to a temporary output file

    audioFile = tempfile.NamedTemporaryFile()
    dubbed.export(audioFile)
    audioFile.flush()

    # with open(os.path.join("checkAudio.wav"), 'wb') as d: 
    #    d.write(audioFile)

    # Add the new audio to the video and save it
    clip = VideoFileClip(movieFile)
    audio = AudioFileClip("Output/audioClips/en-US/0.mp3")
    clip = clip.set_audio(audio)
    clip.write_videofile("Output/dubbedVideos/dubbed.mp4",fps=25)



sentences = [{'fr': "Ça va Charlotte, tu n'as pas l'air en forme. Vous avez raison. Je ne me sens pas bien du tout. Je suis malade qu'est-ce qui tu es arrivé ma chère, j'ai mal à la tête. J'ai un rhume et je tousse est-ce que tu as pris des comprimés.", 'speaker': 0, 'start_time': 0.0, 'end_time': 25.1, 'en-US': "It's okay Charlotte, you don't look well. You are right. I don't feel well at all. I'm sick what happened my dear, I have a headache. I have a cold and coughing did you take any pills."}, {'fr': 'Non, je préfère aller voir le médecin. Il me donnera un traitement à', 'speaker': 0, 'start_time': 26.4, 'end_time': 32.8, 'en-US': "No, I'd rather go see the doctor. He will give me treatment at"}]

print(f"Dubbing audio for fr")
outFile = os.path.join("Output", "final" + ".mp4")
stitch_audio(sentences, os.path.join(
            "Output/audioClips/en-US"), "french.mp4", outFile, srtPath=None)

print("Done")