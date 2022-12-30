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
# import avconv
# print(os.environ["PATH"].split(os.pathsep))


#function 1
def decode_audio(inFile, outFile):
    if not outFile[-4:] != "wav":
        outFile += ".wav"
    AudioSegment.from_file(inFile).set_channels(
        1).export(outFile, format="wav")




# function 2
def get_transcripts_json(langCode, phraseHints=[], speakerCount=1, enhancedModel=None):
 
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

    # client = speech.SpeechClient()  
    
    file_name = "htf.mp3"

    with open(file_name, 'rb') as f:
         mp3_data = f.read()

    client = speech.SpeechClient.from_service_account_file('key.json')
    audio = speech.RecognitionAudio(content= mp3_data)

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




#fun 3
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








# fn = os.path.join("Output", "audio" + ".wav")

decode_audio("Test.mp4", "output.wav")
# print(f"Wrote {fn}")

tmpFile = os.path.join("tmp", str(uuid.uuid4()) + ".wav")

#call fun 2
transcripts = get_transcripts_json(os.path.join(
            "Output", tmpFile),"en-US",
            phraseHints=[],
            speakerCount=1)
json.dump(transcripts, open(os.path.join(
            "Output", "transcript.json"), "w"))
print(transcripts)





#call fun 3
# sentences = parse_sentence_with_speaker(transcripts, "en-US")

# fn = os.path.join(os.path.join(
#             "Output", tmpFile), "transcript" + ".json")
# with open(fn, "w") as f:
#     json.dump(sentences, f)
# print(f"Wrote {fn}")
# print("Deleting cloud file...")
# # blob.delete()
