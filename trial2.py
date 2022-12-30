from pydub import AudioSegment
import os
import shutil
from dotenv import load_dotenv
import tempfile
import uuid
import sys
from moviepy.editor import VideoFileClip, AudioFileClip, CompositeVideoClip
from moviepy.video.tools.subtitles import SubtitlesClip, TextClip
import fire
import html
import json
import ffmpeg
from google.cloud import speech_v1p1beta1 as speech
from google.cloud import storage
from google.cloud import translate_v2 as translate
from google.cloud import texttospeech
import time


os.environ["GOOGLE_APPLICATION_CREDENTIALS"]="key.json"


#function 1
def decode_audio(inFile, outFile):
    if not outFile[-4:] != "wav":
        outFile += ".wav"
    AudioSegment.from_file(inFile).set_channels(
        1).export(outFile, format="wav")





#function 2
def get_transcripts_json(gcsPath, langCode, phraseHints=[], speakerCount=1, enhancedModel=None):
    # Helper function for simplifying Google speech client response
    def _jsonify(result):
        json = []
        for section in result.results:
            data = {
                "transcript": section.alternatives[0].transcript,
                "words": []
            }
            for word in section.alternatives[0].words:
                data["words"].append({
                    "word": word.word,
                    "start_time": word.start_time.total_seconds(),
                    "end_time": word.end_time.total_seconds(),
                    "speaker_tag": word.speaker_tag
                })
            json.append(data)
        return json

    client = speech.SpeechClient.from_service_account_file('key.json') 
    audio = speech.RecognitionAudio(uri=gcsPath)

    diarize = speakerCount if speakerCount > 1 else False
    print(f"Diarizing: {diarize}")
    diarizationConfig = speech.SpeakerDiarizationConfig(
        enable_speaker_diarization=speakerCount if speakerCount > 1 else False,
    )

    # In English only, we can use the optimized video model
    if langCode == "en":
        enhancedModel = "video"

    config = speech.RecognitionConfig(
        language_code="en-US" if langCode == "en" else langCode,
        enable_automatic_punctuation=True,
        enable_word_time_offsets=True,
        speech_contexts=[{
            "phrases": phraseHints,
            "boost": 15
        }],
        diarization_config=diarizationConfig,
        profanity_filter=True,
        use_enhanced=True if enhancedModel else False,
        model="video" if enhancedModel else None

    )
    res = client.long_running_recognize(config=config, audio=audio).result()

    return _jsonify(res)






# function 3
def parse_sentence_with_speaker(json, lang):
    # Special case for parsing japanese words
    def get_word(word, lang):
        if lang == "ja":
            return word.split('|')[0]
        return word

    sentences = []
    sentence = {}
    for result in json:
        for i, word in enumerate(result['words']):
            wordText = get_word(word['word'], lang)
            if not sentence:
                sentence = {
                    lang: [wordText],
                    'speaker': word['speaker_tag'],
                    'start_time': word['start_time'],
                    'end_time': word['end_time']
                }
            # If we have a new speaker, save the sentence and create a new one:
            elif word['speaker_tag'] != sentence['speaker']:
                sentence[lang] = ' '.join(sentence[lang])
                sentences.append(sentence)
                sentence = {
                    lang: [wordText],
                    'speaker': word['speaker_tag'],
                    'start_time': word['start_time'],
                    'end_time': word['end_time']
                }
            else:
                sentence[lang].append(wordText)
                sentence['end_time'] = word['end_time']

            # If there's greater than one second gap, assume this is a new sentence
            if i+1 < len(result['words']) and word['end_time'] < result['words'][i+1]['start_time']:
                sentence[lang] = ' '.join(sentence[lang])
                sentences.append(sentence)
                sentence = {}
        if sentence:
            sentence[lang] = ' '.join(sentence[lang])
            sentences.append(sentence)
            sentence = {}

    return sentences





# fun 4
def translate_text(input, targetLang, sourceLang=None):
    translate_client = translate.Client()
    result = translate_client.translate(
        input, target_language=targetLang, source_language=sourceLang)

    return html.unescape(result['translatedText'])





# fun 5
def speak(text, languageCode, voiceName=None, speakingRate=1):
    # Instantiates a client
    client = texttospeech.TextToSpeechClient()

    # Set the text input to be synthesized
    synthesis_input = texttospeech.SynthesisInput(text=text)

    # Build the voice request, select the language code ("en-US") and the ssml
    # voice gender ("neutral")
    if not voiceName:
        voice = texttospeech.VoiceSelectionParams(
            language_code=languageCode, ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
        )
    else:
        voice = texttospeech.VoiceSelectionParams(
            language_code=languageCode, name=voiceName
        )

    # Select the type of audio file you want returned
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.MP3,
        speaking_rate=speakingRate
    )

    response = client.synthesize_speech(
        input=synthesis_input,
        voice=voice,
        audio_config=audio_config
    )

    return response.audio_content




# fun 6
def speakUnderDuration(text, languageCode, durationSecs, voiceName=None):
    baseAudio = speak(text, languageCode, voiceName=voiceName)
    assert len(baseAudio)
    f = tempfile.NamedTemporaryFile(mode="w+b")
    f.write(baseAudio)
    f.flush()
    baseDuration = AudioSegment.from_mp3(f.name).duration_seconds
    f.close()
    ratio = baseDuration / durationSecs

    # if the audio fits, return it
    if ratio <= 1:
        return baseAudio

    # If the base audio is too long to fit in the segment...

    # round to one decimal point and go a little faster to be safe,
    ratio = round(ratio, 1)
    if ratio > 4:
        ratio = 4
    return speak(text, languageCode, voiceName=voiceName, speakingRate=ratio)







# fun 7
def toSrt(transcripts, charsPerLine=60):

    def _srtTime(seconds):
        millisecs = seconds * 1000
        seconds, millisecs = divmod(millisecs, 1000)
        minutes, seconds = divmod(seconds, 60)
        hours, minutes = divmod(minutes, 60)
        return "%d:%d:%d,%d" % (hours, minutes, seconds, millisecs)

    def _toSrt(words, startTime, endTime, index):
        return f"{index}\n" + _srtTime(startTime) + " --> " + _srtTime(endTime) + f"\n{words}"

    startTime = None
    sentence = ""
    srt = []
    index = 1
    for word in [word for x in transcripts for word in x['words']]:
        if not startTime:
            startTime = word['start_time']

        sentence += " " + word['word']

        if len(sentence) > charsPerLine:
            srt.append(_toSrt(sentence, startTime, word['end_time'], index))
            index += 1
            sentence = ""
            startTime = None

    if len(sentence):
        srt.append(_toSrt(sentence, startTime, word['end_time'], index))

    return '\n\n'.join(srt)




# fun 8
def stitch_audio(sentences, audioDir, movieFile, outFile, srtPath=None, overlayGain=-30):

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

    # Add the new audio to the video and save it
    clip = VideoFileClip(movieFile)
    audio = AudioFileClip(audioFile.name)
    clip = clip.set_audio(audio)

    # Add transcripts, if supplied
    if srtPath:
        width, height = clip.size[0] * 0.75, clip.size[1] * 0.20
        def generator(txt): return TextClip(txt, font='Georgia-Regular',
                                            size=[width, height], color='black', method="caption")
        subtitles = SubtitlesClip(
            srtPath, generator).set_pos(("center", "bottom"))
        clip = CompositeVideoClip([clip, subtitles])

    clip.write_videofile(outFile, codec='libx264', audio_codec='aac')
    audioFile.close()










outputFiles = os.listdir("Output")

#call fun 1
decode_audio("Test.mp4", "output.wav")

#call fun 2
if not f"transcript.json" in outputFiles:
    storageBucket = os.environ["videodubs"]
# if not storageBucket:
#      raise Exception(
#     "Specify variable STORAGE_BUCKET in .env or as an arg")

print("Transcribing audio")
print("Uploading to the cloud...")
storage_client = storage.Client()
bucket = storage_client.get_bucket("videodubs")

tmpFile = os.path.join("tmp.wav")
blob = bucket.blob(tmpFile)
# Temporary upload audio file to the cloud
blob.upload_from_filename(os.path.join(
       "output" + ".wav"), content_type="audio/wav")

print("Transcribing...")
transcripts = get_transcripts_json("gs://videodubs/tmp.wav" , "en-US",
            phraseHints=[],
            speakerCount=1)
json.dump(transcripts, open(os.path.join(
            "Output", "transcript.json"), "w"))
            

# call fun 3
sentences = parse_sentence_with_speaker(transcripts, "en-US")
fn = os.path.join("Output", "transcript" + ".json")
with open(fn, "w") as f:
            json.dump(sentences, f)
print(f"Wrote {fn}")
print("Deleting cloud file...")
blob.delete()


# 
srtPath = os.path.join("Output", "subtitles.srt") if False else None
if False:
        transcripts = json.load(
            open(os.path.join("Output", "transcript.json")))
        subtitles = toSrt(transcripts)
        with open(srtPath, "w") as f:
            f.write(subtitles)
        print(
            f"Wrote srt subtitles to")

sentences = json.load(open(os.path.join("Output", "transcript" + ".json")))
sentence = sentences[0]

print(sentences)

if not False:
        for lang in ["fr"]:
            print(f"Translating to {lang}")
            for sentence in sentences:
                sentence[lang] = translate_text(
                    sentence["en-US"], lang, "en-US")

        # Write the translations to json
        fn = os.path.join("Output", "transcript" + ".json")
        with open(fn, "w") as f:
            json.dump(sentences, f)



audioDir = os.path.join("Output", "audioClips")

if not "audioClips" in outputFiles:
        os.mkdir("audioDir")

    # whether or not to also dub the source language
if False:
        targetLangs += [srcLang]

for lang in ["fr"]:
        languageDir = os.path.join(audioDir, lang)
        if os.path.exists(languageDir):
            if not False:
                continue
            shutil.rmtree(languageDir)
        os.mkdir(languageDir)
        print(f"Synthesizing audio for {lang}")
        for i, sentence in enumerate(sentences):
            voiceName = None
            audio = speakUnderDuration(
                sentence[lang], lang, sentence['end_time'] -
                sentence['start_time'],
                voiceName=voiceName)
            with open(os.path.join(languageDir, f"{i}.mp3"), 'wb') as f:
                f.write(audio)

dubbedDir = os.path.join("Output", "dubbedVideos")

if not "dubbedVideos" in outputFiles:
        os.mkdir(dubbedDir)

for lang in ["fr"]:
        print(f"Dubbing audio for {lang}")
        outFile = os.path.join(dubbedDir, lang + ".mp4")
        stitch_audio(sentences, os.path.join(
            audioDir, lang), "Test.mp4", outFile, srtPath=srtPath)

print("Done")