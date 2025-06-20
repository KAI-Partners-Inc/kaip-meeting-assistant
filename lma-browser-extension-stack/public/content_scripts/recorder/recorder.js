chrome.runtime.onMessage.addListener(async function (request, sender, sendResponse) {
  if (request.action === "StartTranscription") {
    console.log("Received recorder start streaming message", request);
    startStreaming();
  } else if (request.action === "StopTranscription") {
    console.log("Received recorder stop streaming message", request);
    stopStreaming();
  }
}); 

/* globals */
let audioProcessor = undefined;
let samplingRate = 44100;
let audioContext;
let displayStream;
let micStream;
let mediaRecorder;
let recordedChunks = [];
let screenRecordingEnabled = true; // Can be controlled via extension settings
let recordingStartTime;
let frameCaptureInterval;
let capturedFrames = [];

/* Helper funcs */
const bytesToBase64DataUrl = async (bytes, type = "application/octet-stream") => {
  return await new Promise((resolve, reject) => {
    const reader = Object.assign(new FileReader(), {
      onload: () => resolve(reader.result),
      onerror: () => reject(reader.error),
    });
    reader.readAsDataURL(new File([bytes], "", { type }));
  });
}

const pcmEncode = (input) => {
  const buffer = new ArrayBuffer(input.length * 2);
  const view = new DataView(buffer);
  for (let i = 0; i < input.length; i += 1) {
    const s = Math.max(-1, Math.min(1, input[i]));
    view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return buffer;
};

const convertToMono = (audioSource) => {
  const splitter = audioContext.createChannelSplitter(2);
  const merger = audioContext.createChannelMerger(1);
  audioSource.connect(splitter);
  splitter.connect(merger, 0, 0);
  splitter.connect(merger, 1, 0);
  return merger;
};

const captureScreenFrame = async () => {
  try {
    if (displayStream && displayStream.getVideoTracks().length > 0) {
      const videoTrack = displayStream.getVideoTracks()[0];
      const imageCapture = new ImageCapture(videoTrack);
      const blob = await imageCapture.grabFrame();
      
      const timestamp = Date.now() - recordingStartTime;
      const frameData = {
        timestamp: timestamp,
        data: await bytesToBase64DataUrl(blob, 'image/jpeg'),
        width: blob.width,
        height: blob.height
      };
      
      capturedFrames.push(frameData);
      
      // Keep only last 50 frames to manage memory
      if (capturedFrames.length > 50) {
        capturedFrames = capturedFrames.slice(-50);
      }
      
      console.log(`Captured frame at ${timestamp}ms`);
    }
  } catch (error) {
    console.log('Error capturing screen frame:', error);
  }
};

const startScreenRecording = async () => {
  try {
    if (!screenRecordingEnabled) return;
    
    console.log("Starting screen recording...");
    recordingStartTime = Date.now();
    capturedFrames = [];
    
    // Create MediaRecorder for video recording
    const options = {
      mimeType: 'video/webm;codecs=vp9,opus',
      videoBitsPerSecond: 2500000 // 2.5 Mbps
    };
    
    mediaRecorder = new MediaRecorder(displayStream, options);
    
    mediaRecorder.ondataavailable = (event) => {
      if (event.data.size > 0) {
        recordedChunks.push(event.data);
      }
    };
    
    mediaRecorder.onstop = async () => {
      console.log("Screen recording stopped, processing...");
      await processScreenRecording();
    };
    
    mediaRecorder.start(1000); // Record in 1-second chunks
    
    // Start frame capture every 5 seconds
    frameCaptureInterval = setInterval(captureScreenFrame, 5000);
    
    console.log("Screen recording started successfully");
    
  } catch (error) {
    console.log('Error starting screen recording:', error);
  }
};

const processScreenRecording = async () => {
  try {
    if (recordedChunks.length === 0) return;
    
    const videoBlob = new Blob(recordedChunks, { type: 'video/webm' });
    const videoBase64 = await bytesToBase64DataUrl(videoBlob, 'video/webm');
    
    // Send screen recording data to service worker
    const screenData = {
      action: "ScreenRecordingData",
      videoData: videoBase64,
      frames: capturedFrames,
      duration: Date.now() - recordingStartTime,
      format: 'webm'
    };
    
    chrome.runtime.sendMessage(screenData);
    console.log("Screen recording data sent to service worker");
    
    // Clear data
    recordedChunks = [];
    capturedFrames = [];
    
  } catch (error) {
    console.log('Error processing screen recording:', error);
  }
};

const stopStreaming = async () => {
  console.log("recorder stop streaming");
  
  // Stop screen recording
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop();
  }
  
  if (frameCaptureInterval) {
    clearInterval(frameCaptureInterval);
    frameCaptureInterval = null;
  }
  
  if (audioProcessor && audioProcessor.port) {
    audioProcessor.port.postMessage({
      message: 'UPDATE_RECORDING_STATE',
      setRecording: false,
    });
    audioProcessor.port.close();
    audioProcessor.disconnect();
    audioProcessor = null;

    displayStream.getTracks().forEach((track) => {
      track.stop();
    });

    micStream.getTracks().forEach((track) => {
      track.stop();
    });

    if (audioContext) {
      audioContext.close().then(() => {
        chrome.runtime.sendMessage({ action: "TranscriptionStopped" });
        console.log('AudioContext closed.');
        audioContext = null;
      });
    }
  }
}

const startStreaming = async (sendResponse) => {
  try {
    audioContext = new window.AudioContext({
      sampleRate: 8000
    });
    /* Get display media works */
    displayStream = await navigator.mediaDevices.getDisplayMedia({
      preferCurrentTab: true,
      video: true,
      audio: {
        noiseSuppression: true,
        autoGainControl: true,
        echoCancellation: true,
      }
    });

    // hook up the stop streaming event
    displayStream.getAudioTracks()[0].onended = () => {
      stopStreaming();
    };

    micStream = await navigator.mediaDevices.getUserMedia({
      video: false,
      audio: {
        noiseSuppression: true,
        autoGainControl: true,
        echoCancellation: true,
      }
    });

    samplingRate = audioContext.sampleRate;
    console.log("Sending sampling rate:", samplingRate);
    chrome.runtime.sendMessage({ action: "SamplingRate", samplingRate: samplingRate });

    let displayAudioSource = audioContext.createMediaStreamSource(displayStream);
    let micAudioSource = audioContext.createMediaStreamSource(micStream);

    let monoDisplaySource = convertToMono(displayAudioSource);
    let monoMicSource = convertToMono(micAudioSource);

    let channelMerger = audioContext.createChannelMerger(2);
    monoMicSource.connect(channelMerger, 0, 0);
    monoDisplaySource.connect(channelMerger, 0, 1);

    try {
      await audioContext.audioWorklet.addModule('audio-worklet.js');
    } catch (error) {
      console.log(`Add module error ${error}`);
    }

    audioProcessor = new AudioWorkletNode(audioContext, 'recording-processor');
    audioProcessor.port.onmessageerror = (error) => {
      console.log(`Error receving message from worklet ${error}`);
    };

    audioProcessor.port.onmessage = async (event) => {
      // this is pcm audio
      //sendMessage(event.data);
      let base64AudioData = await bytesToBase64DataUrl(event.data);
      let payload = { action: "AudioData", audio: base64AudioData };
      chrome.runtime.sendMessage(payload);
    };
    channelMerger.connect(audioProcessor);
    
    // Start screen recording after audio setup is complete
    await startScreenRecording();

    // buffer[0] - display stream,  buffer[1] - mic stream
    /*audioProcessor.port.onmessage = async (event) => {
      let audioData = new Uint8Array(
        interleave(event.data.buffer[0], event.data.buffer[1]),
      );
      let base64AudioData = await bytesToBase64DataUrl(audioData);
      // send audio to service worker:
      let payload = { action: "AudioData", audio: base64AudioData };
      chrome.runtime.sendMessage(payload);
    };*/
  } catch (error) {
    // console.error("Error in recorder", error);
    await stopStreaming();
  }
};

console.log("Inside the recorder.js");