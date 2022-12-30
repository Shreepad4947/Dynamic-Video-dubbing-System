import speech_recognition as sr
import translators as ts
from gtts import gTTS
import os
import moviepy.editor as mpe
import pyttsx3
r = sr.Recognizer()

# TRANSLATION
# file_audio = sr.AudioFile('Output/abcd.wav')

# with file_audio as source:
#    audio_text = r.record(source)


# eng = r.recognize_google(audio_text)
# print(eng)

# trans = ts.google(eng, from_language='en', to_language='fr')
# print(trans)

# TTS

trans1 = "Tout le monde a un moment de retour en arri\u00e8re, vous avez un moment o\u00f9 vous pouvez aller de l'avant ou vous pouvez abandonner. Mais la chose que vous devez garder \u00e0 l'esprit avant d'abandonner, c'est que si vous abandonnez la garantie, cela n'arrivera jamais. C'est la garantie de cesser de fumer que cela n'arrivera jamais. Pas question sous le soleil, la seule possibilit\u00e9 que cela puisse arriver est si vous n'abandonnez jamais quoi qu'il arrive"

myobj = gTTS(text=trans1, lang='fr', slow=False)
engine = pyttsx3.init() 
engine.setProperty('rate', 145)
voices = engine.getProperty('voices') 
for voice in voices:
    print("Voice: %s" % voice.name)
    print(" - ID: %s" % voice.id)
    print(" - Languages: %s" % voice.languages)
    print(" - Gender: %s" % voice.gender)
    print(" - Age: %s" % voice.age)
    print("\n")
engine.setProperty('voice', voices[0].id)   #changing index, changes voices. 1 for female
engine.setProperty('gender', 'male')
engine.setProperty('Languages', 'fr')
# engine.say("Tout le monde a un moment de retour en arri\u00e8re, vous avez un moment o\u00f9 vous pouvez aller de l'avant ou vous pouvez abandonner. Mais la chose que vous devez garder \u00e0 l'esprit avant d'abandonner, c'est que si vous abandonnez la garantie, cela n'arrivera jamais. C'est la garantie de cesser de fumer que cela n'arrivera jamais. Pas question sous le soleil, la seule possibilit\u00e9 que cela puisse arriver est si vous n'abandonnez jamais quoi qu'il arrive")
# engine.runAndWait()
# engine.stop()


engine.save_to_file(trans1, 'test.mp3')
engine.runAndWait()


# myobj.save("Output/translated.mp3")



#merge


my_clip = mpe.VideoFileClip("input/Test.mp4")
audio_background = mpe.AudioFileClip("test.mp3")
final_clip = my_clip.set_audio(audio_background)
final_clip.write_videofile("Output/dubbed.mp4",fps=25)
