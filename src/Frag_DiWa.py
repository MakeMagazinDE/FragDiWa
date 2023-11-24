import vlc
import pygame
import sounddevice as sd
import wave
import os
import time
import requests
import json
from google.cloud import speech
from google.cloud import texttospeech
from google.oauth2 import service_account

# INPUT PARAMETER
Dialog_Gesamt = [{'role': 'system', 'content': 'Du bist DiWa, der hilfreicher Sprachassistent. Wichtig: nenne bei Aufzählungen nicht "Erster", "Zweiter", oder  1., 2., und so weiter, sondern nur die Information durch Komma getrennt.'}]
Instance = vlc.Instance('--input-repeat=99', '--fullscreen')
Media_1 = Instance.media_new('/home/pi/Desktop/Frag_DiWa_Hallo.mp4')
Media_2 = Instance.media_new('/home/pi/Desktop/Frag_DiWa_Denken.mp4')
Media_3 = Instance.media_new('/home/pi/Desktop/Frag_DiWa_Antwort.mp4')
Media_4 = Instance.media_new('/home/pi/Desktop/Frag_DiWa_Goodbye.mp4')
keyword_paths = ['/home/pi/Desktop/Hallo-Diwa_de_raspberry-pi_v2_2_0.ppn']
wake_word_access_key='HIER_PICOVOICE_API_KEY_EINGEBEN'
model_path= '/home/pi/Desktop/porcupine_params_de.pv'
Wake_Word_Detection_path = '/home/pi/Desktop/Wake_Word_Detection.wav'
lang_code = 'de-DE'
credentials = service_account.Credentials.from_service_account_file('/home/pi/Desktop/google_client_secret.json')
Start_Ton = '/home/pi/Desktop/Start.wav'
Stop_Ton = '/home/pi/Desktop/Stop.wav'
Aufnahmedauer = 5
wav_Input_Pfad = '/home/pi/Desktop/input.wav'
wav_Output_Pfad = '/home/pi/Desktop/output.wav'
ChatGPT_API = 'Bearer HIER_CHATGPT_API_KEY_EINGEBEN'
Antwortgeschwindigkeit= 1.2

VLC_player = Instance.media_player_new()
VLC_player.video_set_mouse_input(True)
VLC_player.video_set_scale(0.7)
VLC_player.set_media(Media_2)
VLC_player.play()

pygame.mixer.init()

def Dialogschleife(Dialog_Gesamt):
    Dialog = True
    while Dialog:
        def record_audio(file_path, threshold=0.01, sample_rate=44100, channels=1, duration=Aufnahmedauer):
            ###############################################################################################################
            # Spracheingabe
            print("Recording...")
            VLC_player.set_media(Media_2)
            VLC_player.play()
            # https://mixkit.co/free-sound-effects/tones/
            sound = pygame.mixer.Sound(Start_Ton)
            playing = sound.play()
            audio_data = sd.rec(int(sample_rate * duration), samplerate=sample_rate, channels=channels, dtype='int16')
            sd.wait()
            sound = pygame.mixer.Sound(Stop_Ton)
            playing = sound.play()
            print("Recording finished.")
                 
            # Spracheingabe als WAV Datei speichern
            with wave.open(file_path, 'wb') as wf:
                wf.setnchannels(channels)
                wf.setsampwidth(2)  # 2 bytes for 16-bit audio (int16)
                wf.setframerate(sample_rate)
                wf.writeframes(audio_data.tobytes())
                
        if __name__ == "__main__":
            record_audio(wav_Input_Pfad)               
        print("Audio saved as WAV:", wav_Input_Pfad)
        print()
               
        ###############################################################################################################
        # Aufnahme Speech-to-text

        client = speech.SpeechClient(credentials=credentials)
        # The name of the audio file to transcribe
        gcs_uri = wav_Input_Pfad
        with open(gcs_uri, 'rb') as f:
            audio_data = f.read()
        audio = speech.RecognitionAudio(content=audio_data)
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=44100,
            language_code=lang_code,
            enable_automatic_punctuation=True,
        )
        # Detects speech in the audio file
        response = client.recognize(config=config, audio=audio)
        if(response.results == []):
            print("Keine Spracheingabe")
            Anfrage = "Diwa Pause"
        elif not (response.results == []):
            for result in response.results:
                Anfrage = result.alternatives[0].transcript
            print(Anfrage)    
        
        Send_Request = True

        #Pause
        if Anfrage == "Diwa Pause" or Anfrage == "Diva Pause.":
            Dialog_Gesamt = [{'role': 'system', 'content': 'Du bist DiWa, der hilfreicher Sprachassistent. Wenn ich Dir eine Rolle gebe, dann bleibe so lange in der Rolle, bis ich Dir eine neue Rolle gebe. Du musst aber nicht sagen, welche Rolle Du spielst. Und sage bei Aufzählungen nicht Erster, Zweiter, und so weiter, sondern sage mir nur die Information.'}]
            Dialog = False
            Send_Request = False
            VLC_player.set_media(Media_2)
            VLC_player.play()

        # Ende
        if "beenden" in Anfrage:
            Dialog = False
            Send_Request = False
            VLC_player.set_media(Media_4)
            VLC_player.audio_set_volume(100)
            VLC_player.play()
            time.sleep(3.0)
            VLC_player.release()
            recorder.delete()
            porcupine.delete()
            if wav_file is not None:
                wav_file.close()
            break
            #os.system("sudo shutdown -h now")

        Dialog_Gesamt.append({'role': 'user', 'content': Anfrage})   

        ###############################################################################################################
        # ChatGPT Anfrage senden
        
        if Send_Request:
            url = "https://api.openai.com/v1/chat/completions?messages=<array>&max_tokens=<integer>&model=<string>"

            payload = json.dumps({
              "messages": Dialog_Gesamt,
              "temperature": 0.7,
              "max_tokens": 300,
              "model": "gpt-3.5-turbo"
            })
            headers = {
              'Content-Type': 'application/json',
              'Authorization': ChatGPT_API
            }

            response = requests.request("POST", url, headers=headers, data=payload)
            json_string = response.json()
            response_json = json_string['choices'][0]['message']['content']
            Letzter_Punkt = response_json.rfind('.')
            if (Letzter_Punkt > 0):
                Antwort = response_json[0:Letzter_Punkt+1]
                Punkt = response_json.find('.')
                Antwort_kurz = response_json[0:Punkt+1]
                Dialog_Gesamt.append({'role': 'assistant', 'content': Antwort_kurz})
            else:
                Antwort = response_json
                Dialog_Gesamt.append({'role': 'assistant', 'content': Antwort})
            print(Antwort)
            
            ######################################################################################
            # Text to Speech
            print("Text to Speech")
            client = texttospeech.TextToSpeechClient(credentials=credentials)
            # Set the text input to be synthesized
            synthesis_input = texttospeech.SynthesisInput(text=Antwort)

            voice = texttospeech.VoiceSelectionParams(language_code=lang_code, name = "de-DE-Neural2-B", ssml_gender=texttospeech.SsmlVoiceGender.MALE)
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                speaking_rate=Antwortgeschwindigkeit  # Adjust the speaking rate here. There are as well 'pitch' and 'rate'
            )

            # Perform the text-to-speech request on the text input with the selected voice parameters and audio file type
            response = client.synthesize_speech(
                input=synthesis_input, voice=voice, audio_config=audio_config
            )            
            with open(wav_Output_Pfad, "wb") as out:
                # Write the response to the output file.
                out.write(response.audio_content)
            
            ###########################################################################################
            # Ausgabe
            sound = pygame.mixer.Sound(wav_Output_Pfad)
            playing = sound.play()
            VLC_player.set_media(Media_3)
            VLC_player.audio_set_volume(0)

            while playing.get_busy():
                pygame.time.delay(100)
                VLC_player.play()
            
            print("***** Neue Anfrage *****")
            VLC_player.set_media(Media_2)
            VLC_player.play()

# Wake Word Detection ########################################################
from datetime import datetime
import struct
from pvrecorder import PvRecorder
import pvporcupine
import tempfile

from dotenv import load_dotenv
load_dotenv()

try:
    porcupine = pvporcupine.create(
        access_key=wake_word_access_key,
        keyword_paths=keyword_paths,
        model_path=model_path
    )
except pvporcupine.PorcupineActivationError as e:
    print("AccessKey activation error")
    raise e
except pvporcupine.PorcupineError as e:
    print("Failed to initialize Porcupine")
    raise e

keywords = list()
for x in keyword_paths:
    keyword_phrase_part = os.path.basename(x).replace('.ppn', '').split('_')
    print(keyword_phrase_part)
    if len(keyword_phrase_part) > 6:
        keywords.append(' '.join(keyword_phrase_part[0:-6]))
    else:
        keywords.append(keyword_phrase_part[0])

    print('Porcupine version: %s' % porcupine.version)

    recorder = PvRecorder(
        frame_length=porcupine.frame_length,
        device_index=-1)
    recorder.start()

    wav_file = None
    wav_file = wave.open(Wake_Word_Detection_path, "w")
    wav_file.setnchannels(1)
    wav_file.setsampwidth(2)
    wav_file.setframerate(16000)

    print('Listening ... (press Ctrl+C to exit)')

    try:
        while True:
            pcm = recorder.read()
            result = porcupine.process(pcm)

            if wav_file is not None:
                wav_file.writeframes(struct.pack("h" * len(pcm), *pcm))
                #print("Warten auf Wake Word ...")

            if result >= 0:
                print('[%s] Detected %s' % (str(datetime.now()), keywords[result]))
                VLC_player.set_media(Media_1)
                VLC_player.play()
                time.sleep(3.0)
                Dialogschleife(Dialog_Gesamt)

    except KeyboardInterrupt:
        print('Stopping ...')
    finally:
        recorder.delete()
        porcupine.delete()
        if wav_file is not None:
            wav_file.close()

if __name__ == '__main__':
    main()
