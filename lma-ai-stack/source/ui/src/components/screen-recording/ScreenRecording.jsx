// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React, { useState, useRef, useEffect } from 'react';
import {
  Box,
  Button,
  Container,
  Form,
  FormField,
  Header,
  Input,
  SpaceBetween,
  StatusIndicator,
  TextContent,
  Alert,
  Modal,
  Link,
} from '@awsui/components-react';
import { Logger } from 'aws-amplify';

import useAppContext from '../../contexts/app';
import useSettingsContext from '../../contexts/settings';

const logger = new Logger('ScreenRecording');

const ScreenRecording = () => {
  const { setErrorMessage } = useAppContext();
  const settings = useSettingsContext();

  // State management
  const [recording, setRecording] = useState(false);
  const [setStreamingStarted] = useState(false);
  const [meetingTopic, setMeetingTopic] = useState('');
  const [agentName, setAgentName] = useState('');
  const [participantNames, setParticipantNames] = useState('');
  const [recordedMeetingId, setRecordedMeetingId] = useState('');
  const [isFlashing, setIsFlashing] = useState(false);
  const [showDisclaimer, setShowDisclaimer] = useState(false);
  const [videoStream, setVideoStream] = useState(null);
  const [audioStream, setAudioStream] = useState(null);
  const [mediaRecorder, setMediaRecorder] = useState(null);
  const [setRecordedChunks] = useState([]);
  const [recordingStatus, setRecordingStatus] = useState('idle');
  const [recordingDuration, setRecordingDuration] = useState(0);
  const [showVideoPreview, setShowVideoPreview] = useState(false);

  // Refs
  const videoRef = useRef(null);
  const recordingTimerRef = useRef(null);
  const agreeToRecordRef = useRef(false);

  // WebSocket connection
  const [wsConnection, setWsConnection] = useState(null);

  const handleWebSocketMessage = (data) => {
    if (data.type === 'recording_status') {
      setRecordingStatus(data.status);
    } else if (data.type === 'meeting_id') {
      setRecordedMeetingId(data.meetingId);
    }
  };

  const initializeWebSocket = () => {
    try {
      const ws = new WebSocket(settings.WSEndpoint);

      ws.onopen = () => {
        logger.info('WebSocket connection established');
        setWsConnection(ws);
      };

      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        logger.debug('WebSocket message received:', data);
        handleWebSocketMessage(data);
      };

      ws.onerror = (error) => {
        logger.error('WebSocket error:', error);
        setErrorMessage('WebSocket connection error');
      };

      ws.onclose = () => {
        logger.info('WebSocket connection closed');
        setWsConnection(null);
      };
    } catch (error) {
      logger.error('Error initializing WebSocket:', error);
      setErrorMessage('Failed to initialize WebSocket connection');
    }
  };

  const sendMessage = (message) => {
    if (wsConnection && wsConnection.readyState === WebSocket.OPEN) {
      wsConnection.send(message);
    } else {
      logger.warn('WebSocket not connected');
    }
  };

  const getTimestampStr = () => {
    return new Date().toISOString().replace(/[:.]/g, '-');
  };

  const getFinalCallMetadata = () => {
    const meetingPrefix = meetingTopic.replace(/[/?#%+&]/g, '|') || 'Screen Recording';
    setMeetingTopic(meetingPrefix);

    return {
      callId: `${meetingPrefix} - ${getTimestampStr()}`,
      agentId: agentName || 'Screen Recorder',
      fromNumber: participantNames || 'Participants',
      callEvent: 'START',
      recordingType: 'screen_video',
      timestamp: new Date().toISOString(),
    };
  };

  const uploadRecording = async (blob) => {
    try {
      logger.info('Uploading screen recording...');

      // Convert blob to base64 for transmission
      const reader = new FileReader();
      reader.onload = () => {
        const base64Data = reader.result.split(',')[1];

        const uploadData = {
          type: 'screen_recording_upload',
          callId: getFinalCallMetadata().callId,
          videoData: base64Data,
          format: 'webm',
          timestamp: new Date().toISOString(),
        };

        sendMessage(JSON.stringify(uploadData));
      };

      reader.readAsDataURL(blob);
    } catch (error) {
      logger.error('Error uploading recording:', error);
      setErrorMessage(`Failed to upload recording: ${error.message}`);
    }
  };

  useEffect(() => {
    // Initialize WebSocket connection
    if (settings.WSEndpoint && !wsConnection) {
      initializeWebSocket();
    }

    return () => {
      if (wsConnection) {
        wsConnection.close();
      }
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
      }
    };
  }, [settings.WSEndpoint]);

  const startRecording = async () => {
    try {
      logger.info('Starting screen recording...');

      // Get screen capture
      const displayStream = await navigator.mediaDevices.getDisplayMedia({
        video: {
          cursor: 'always',
          displaySurface: 'monitor',
        },
        audio: true,
      });

      // Get microphone audio
      const micStream = await navigator.mediaDevices.getUserMedia({
        video: false,
        audio: {
          echoCancellation: true,
          noiseSuppression: true,
          autoGainControl: true,
        },
      });

      setVideoStream(displayStream);
      setAudioStream(micStream);

      // Create MediaRecorder for video recording
      const options = {
        mimeType: 'video/webm;codecs=vp9,opus',
        videoBitsPerSecond: 2500000, // 2.5 Mbps
      };

      const recorder = new MediaRecorder(displayStream, options);
      const chunks = [];

      recorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          chunks.push(event.data);
        }
      };

      recorder.onstop = () => {
        const blob = new Blob(chunks, { type: 'video/webm' });
        setRecordedChunks(chunks);
        uploadRecording(blob);
      };

      setMediaRecorder(recorder);
      recorder.start(1000); // Record in 1-second chunks

      // Send start message
      const callMetadata = getFinalCallMetadata();
      sendMessage(JSON.stringify(callMetadata));

      setRecording(true);
      setStreamingStarted(true);
      setRecordingStatus('recording');
      setShowVideoPreview(true);

      // Start recording timer
      recordingTimerRef.current = setInterval(() => {
        setRecordingDuration((prev) => prev + 1);
      }, 1000);

      // Start flashing effect
      setIsFlashing(true);

      logger.info('Screen recording started successfully');
    } catch (error) {
      logger.error('Error starting screen recording:', error);
      setErrorMessage(`Failed to start screen recording: ${error.message}`);
    }
  };

  const stopRecording = async () => {
    try {
      logger.info('Stopping screen recording...');

      if (mediaRecorder && mediaRecorder.state !== 'inactive') {
        mediaRecorder.stop();
      }

      if (videoStream) {
        videoStream.getTracks().forEach((track) => track.stop());
        setVideoStream(null);
      }

      if (audioStream) {
        audioStream.getTracks().forEach((track) => track.stop());
        setAudioStream(null);
      }

      // Send end message
      const callMetadata = getFinalCallMetadata();
      callMetadata.callEvent = 'END';
      sendMessage(JSON.stringify(callMetadata));

      setRecording(false);
      setStreamingStarted(false);
      setRecordingStatus('processing');
      setShowVideoPreview(false);
      setIsFlashing(false);

      // Stop recording timer
      if (recordingTimerRef.current) {
        clearInterval(recordingTimerRef.current);
        recordingTimerRef.current = null;
      }

      logger.info('Screen recording stopped successfully');
    } catch (error) {
      logger.error('Error stopping screen recording:', error);
      setErrorMessage(`Failed to stop screen recording: ${error.message}`);
    }
  };

  const formatDuration = (seconds) => {
    const mins = Math.floor(seconds / 60);
    const secs = seconds % 60;
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  };

  const handleStartRecording = () => {
    if (!meetingTopic.trim()) {
      setErrorMessage('Please enter a meeting topic');
      return;
    }

    if (!agreeToRecordRef.current) {
      setShowDisclaimer(true);
      return;
    }

    startRecording();
  };

  const handleStopRecording = () => {
    stopRecording();
  };

  const confirmDisclaimer = () => {
    agreeToRecordRef.current = true;
    setShowDisclaimer(false);
    startRecording();
  };

  return (
    <div className="screen-recording">
      <Container
        header={
          <Header variant="h2" description="Record your screen alongside audio for comprehensive meeting analysis">
            Screen Recording
          </Header>
        }
      >
        <SpaceBetween size="l">
          <Alert type="info" header="Screen Recording Feature">
            This feature allows you to record your screen alongside audio, enabling the meeting assistant to analyze
            both visual content and spoken words for more comprehensive meeting summaries.
          </Alert>

          <Form
            actions={
              <SpaceBetween direction="horizontal" size="xs">
                {!recording ? (
                  <Button variant="primary" onClick={handleStartRecording} disabled={!settings.WSEndpoint}>
                    Start Screen Recording
                  </Button>
                ) : (
                  <Button variant="primary" onClick={handleStopRecording} iconName="stop">
                    Stop Recording
                  </Button>
                )}
              </SpaceBetween>
            }
          >
            <SpaceBetween size="l">
              <FormField label="Meeting Topic" description="Enter a descriptive name for your meeting">
                <Input
                  value={meetingTopic}
                  onChange={({ detail }) => setMeetingTopic(detail.value)}
                  placeholder="e.g., Q4 Planning Meeting"
                  disabled={recording}
                />
              </FormField>

              <FormField label="Your Name" description="Name to associate with your audio">
                <Input
                  value={agentName}
                  onChange={({ detail }) => setAgentName(detail.value)}
                  placeholder="Your name"
                  disabled={recording}
                />
              </FormField>

              <FormField label="Participant Names" description="Names of other meeting participants (optional)">
                <Input
                  value={participantNames}
                  onChange={({ detail }) => setParticipantNames(detail.value)}
                  placeholder="e.g., John, Sarah, Mike"
                  disabled={recording}
                />
              </FormField>

              {recording && (
                <Box>
                  <SpaceBetween direction="horizontal" size="s">
                    <StatusIndicator type={isFlashing ? 'pending' : 'success'}>Recording</StatusIndicator>
                    <TextContent>Duration: {formatDuration(recordingDuration)}</TextContent>
                  </SpaceBetween>
                </Box>
              )}

              {recordingStatus === 'processing' && (
                <Alert type="info">Processing your screen recording and generating analysis...</Alert>
              )}

              {recordedMeetingId && (
                <Box>
                  <SpaceBetween direction="horizontal" size="s">
                    <TextContent>Recording completed:</TextContent>
                    <Link href={`#/calls/${recordedMeetingId}`} external>
                      View Meeting Analysis
                    </Link>
                  </SpaceBetween>
                </Box>
              )}
            </SpaceBetween>
          </Form>

          {showVideoPreview && videoStream && (
            <Box>
              <Header variant="h3">Recording Preview</Header>
              <video
                ref={videoRef}
                autoPlay
                muted
                style={{
                  width: '100%',
                  maxWidth: '600px',
                  border: '1px solid #ccc',
                  borderRadius: '4px',
                }}
              />
            </Box>
          )}
        </SpaceBetween>
      </Container>

      <Modal
        visible={showDisclaimer}
        onDismiss={() => setShowDisclaimer(false)}
        header="Recording Disclaimer"
        size="medium"
      >
        <SpaceBetween size="l">
          <TextContent>
            <p>
              <strong>Important:</strong> You are responsible for complying with legal, corporate, and ethical
              restrictions that apply to recording meetings and calls.
            </p>
            <p>
              This feature will record your screen content and audio. Do not use this solution to record calls if
              otherwise prohibited.
            </p>
            <p>The recording will be processed to generate meeting summaries and insights.</p>
          </TextContent>

          <SpaceBetween direction="horizontal" size="xs">
            <Button variant="link" onClick={() => setShowDisclaimer(false)}>
              Cancel
            </Button>
            <Button variant="primary" onClick={confirmDisclaimer}>
              I Agree - Start Recording
            </Button>
          </SpaceBetween>
        </SpaceBetween>
      </Modal>
    </div>
  );
};

export default ScreenRecording;
