
import asyncio
import details
import kds
from amazon_transcribe.client import TranscribeStreamingClient
from amazon_transcribe.handlers import TranscriptResultStreamHandler
from amazon_transcribe.model import TranscriptEvent
import sounddevice as sd

# globals
current_speaker = "none"


class MyEventHandler(TranscriptResultStreamHandler):
    async def handle_transcript_event(self, transcript_event: TranscriptEvent):
        for result in transcript_event.transcript.results:
            print(f'Transcribe result: {result}')
            kds.send_add_transcript_segment(current_speaker, result)


async def write_audio(transcribe_stream, recording_stream):
    loop = asyncio.get_event_loop()
    input_queue = asyncio.Queue()

    def callback(indata, frame_count, time_info, status):
        loop.call_soon_threadsafe(
            input_queue.put_nowait, (bytes(indata), status))

    with sd.RawInputStream(
        channels=1,
        samplerate=16000,
        callback=callback,
        blocksize=3200,  # roughly 100ms of audio data
        dtype='int16'
    ):
        while details.start:
            indata, status = await input_queue.get()
            await transcribe_stream.input_stream.send_audio_event(audio_chunk=indata)
            recording_stream.write(indata)
        await transcribe_stream.input_stream.end_stream()
        recording_stream.close()


async def transcribe():
    print("Transcribe starting")
    kds.send_start_meeting()

    if details.transcribe_language_code in ["identify-language", "identify-multiple-languages"]:
        print("WARNING: Language identification option has been selected, but is not supported in Virtual Participant")
        if details.transcribe_preferred_language == "None":
            language_code = "en-US"
        else:
            language_code = details.transcribe_preferred_language
    else:
        language_code = details.transcribe_language_code

    print(f"Using Transcribe language code: {language_code}")

    transcribe_stream = await TranscribeStreamingClient(region="us-east-1").start_stream_transcription(
        language_code=language_code,
        media_sample_rate_hz=16000,
        media_encoding="pcm",
    )
    recording_stream = open(details.tmp_recording_filename, "wb")
    await asyncio.gather(
        write_audio(transcribe_stream, recording_stream),
        MyEventHandler(transcribe_stream.output_stream).handle_events()
    )
    print("Transcribe stopped")


async def speaker_change(speaker):
    global current_speaker
    current_speaker = speaker
    print(f"Speaker: {current_speaker}")
