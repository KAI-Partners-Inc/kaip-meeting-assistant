#!/usr/bin/env python3.12
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
""" Video Analysis and Screen Recording Summarization Lambda Function
"""
import asyncio
import json
import os
import tempfile
import time

from typing import TYPE_CHECKING, Dict, List, Optional
from datetime import datetime

# third-party imports from Lambda layer
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext
import boto3
from botocore.config import Config as BotoCoreConfig

# AWS services
from botocore.exceptions import ClientError

# local imports
from video_processor import VideoProcessor
from screen_analyzer import ScreenAnalyzer
from summary_generator import VideoSummaryGenerator

# pylint: disable=import-error
from appsync_utils import AppsyncAioGqlClient
# pylint: enable=import-error

if TYPE_CHECKING:
    from mypy_boto3_s3.client import S3Client
    from mypy_boto3_rekognition.client import RekognitionClient
    from mypy_boto3_bedrock.client import BedrockClient
    from boto3 import Session as Boto3Session
else:
    Boto3Session = object
    S3Client = object
    RekognitionClient = object
    BedrockClient = object

# Environment variables
APPSYNC_GRAPHQL_URL = os.environ["APPSYNC_GRAPHQL_URL"]
VIDEO_SUMMARY_BUCKET = os.environ.get("VIDEO_SUMMARY_BUCKET", "")
VIDEO_SUMMARY_PREFIX = os.environ.get("VIDEO_SUMMARY_PREFIX", "lma-video-recordings/")
ASYNC_TRANSCRIPT_SUMMARY_ORCHESTRATOR_ARN = os.environ.get("ASYNC_TRANSCRIPT_SUMMARY_ORCHESTRATOR_ARN", "")

# AWS clients
BOTO3_SESSION: Boto3Session = boto3.Session()
CLIENT_CONFIG = BotoCoreConfig(
    retries={"mode": "adaptive", "max_attempts": 3},
)

S3_CLIENT: S3Client = BOTO3_SESSION.client("s3", config=CLIENT_CONFIG)
REKOGNITION_CLIENT: RekognitionClient = BOTO3_SESSION.client("rekognition", config=CLIENT_CONFIG)
BEDROCK_CLIENT: BedrockClient = BOTO3_SESSION.client("bedrock-runtime", config=CLIENT_CONFIG)
LAMBDA_CLIENT = BOTO3_SESSION.client("lambda", config=CLIENT_CONFIG)

APPSYNC_CLIENT = AppsyncAioGqlClient(
    url=APPSYNC_GRAPHQL_URL, fetch_schema_from_transport=True)

LOGGER = Logger(location="%(filename)s:%(lineno)d - %(funcName)s()")

EVENT_LOOP = asyncio.get_event_loop()

lambda_client = boto3.client("lambda")
CALL_EVENT_PROCESSOR_ARN = os.environ.get("CALL_EVENT_PROCESSOR_ARN")

def emit_add_s3_recording_url_event(call_id, video_bucket, video_key):
    """Emit ADD_S3_RECORDING_URL event to call event processor Lambda"""
    if not (CALL_EVENT_PROCESSOR_ARN and call_id and video_bucket and video_key):
        LOGGER.error(f"Missing required info to emit ADD_S3_RECORDING_URL: ARN={CALL_EVENT_PROCESSOR_ARN}, call_id={call_id}, video_bucket={video_bucket}, video_key={video_key}")
        return
    recording_url = f"s3://{video_bucket}/{video_key}"
    event = {
        "EventType": "ADD_S3_RECORDING_URL",
        "CallId": call_id,
        "RecordingUrl": recording_url
    }
    try:
        lambda_client.invoke(
            FunctionName=CALL_EVENT_PROCESSOR_ARN,
            InvocationType="Event",
            Payload=json.dumps(event)
        )
        LOGGER.debug(f"Emitted ADD_S3_RECORDING_URL event for call_id={call_id}")
    except Exception as e:
        LOGGER.error(f"Failed to emit ADD_S3_RECORDING_URL event: {e}")


async def wait_for_recording_url(call_id, max_retries=10, delay=300):
    """Poll AppSync until RecordingUrl is set for the call."""
    for attempt in range(max_retries):
        query = """
        query GetCall($CallId: ID!) {
            getCall(CallId: $CallId) {
                RecordingUrl
            }
        }
        """
        variables = {"CallId": call_id}
        result = await APPSYNC_CLIENT.execute(query, variable_values=variables)
        recording_url = result.get("getCall", {}).get("RecordingUrl")
        if recording_url:
            return recording_url
        if attempt < max_retries - 1:
            LOGGER.debug(f"RecordingUrl not set yet for call {call_id}, retrying ({attempt+1}/{max_retries})...")
            time.sleep(delay)
    LOGGER.error(f"RecordingUrl was not set for call {call_id} after {max_retries} retries.")
    return None

def emit_end_event(call_id, video_bucket, video_key):
    """Emit END event to call event processor Lambda"""
    if not (CALL_EVENT_PROCESSOR_ARN and call_id and video_bucket and video_key):
        LOGGER.error(f"Missing required info to emit END event: ARN={CALL_EVENT_PROCESSOR_ARN}, call_id={call_id}, video_bucket={video_bucket}, video_key={video_key}")
        return
    event = {
        "EventType": "END",
        "CallId": call_id,
        "VideoBucket": video_bucket,
        "VideoKey": video_key
    }
    try:
        lambda_client.invoke(
            FunctionName=CALL_EVENT_PROCESSOR_ARN,
            InvocationType="Event",
            Payload=json.dumps(event)
        )
        LOGGER.debug(f"Emitted END event for call_id={call_id}")
    except Exception as e:
        LOGGER.error(f"Failed to emit END event: {e}")


class VideoAnalysisProcessor:
    """Processes video recordings and generates summaries alongside transcript analysis"""
    
    def __init__(self, call_id: str, video_bucket: str, video_key: str, transcript_data: Optional[Dict] = None):
        self.call_id = call_id
        self.video_bucket = video_bucket
        self.video_key = video_key
        self.transcript_data = transcript_data or {}
        self.video_processor = VideoProcessor(S3_CLIENT, REKOGNITION_CLIENT)
        self.screen_analyzer = ScreenAnalyzer(REKOGNITION_CLIENT)
        self.summary_generator = VideoSummaryGenerator(BEDROCK_CLIENT)
        
    async def process_video(self) -> Dict:
        """Main processing pipeline for video analysis"""
        try:
            LOGGER.debug(f"Starting video analysis for call: {self.call_id}")
            
            # Process video from S3
            video_analysis = await self.video_processor.process_video_from_s3(
                self.video_bucket, self.video_key
            )
            
            # For now, create a basic screen analysis since we don't have frames
            screen_analysis = {
                "analysis_type": "basic",
                "frames_analyzed": 0,
                "text_content": video_analysis.get("text_content", {}),
                "objects_detected": video_analysis.get("objects_detected", {}),
                "note": "Full frame analysis requires AWS MediaConvert integration"
            }
            
            # Generate video summary
            video_summary = await self.summary_generator.generate_summary(
                screen_analysis, self.transcript_data
            )
            
            # Store results
            await self._store_results(video_summary, screen_analysis)
            
            LOGGER.debug(f"Video analysis completed for call: {self.call_id}")
            return {
                "call_id": self.call_id,
                "video_summary": video_summary,
                "screen_analysis": screen_analysis,
                "status": "completed"
            }
            
        except Exception as e:
            LOGGER.error(f"Error processing video for call {self.call_id}: {str(e)}")
            return {
                "call_id": self.call_id,
                "error": str(e),
                "status": "failed"
            }
    
    async def _store_results(self, video_summary: Dict, screen_analysis: Dict):
        """Store analysis results in S3 and update database"""
        try:
            # Prepare results data
            results_data = {
                "call_id": self.call_id,
                "timestamp": datetime.utcnow().isoformat(),
                "video_summary": video_summary,
                "screen_analysis": screen_analysis,
                "metadata": {
                    "video_source": f"s3://{self.video_bucket}/{self.video_key}",
                    "processing_version": "1.0",
                    "analysis_type": "basic_metadata"
                }
            }
            
            # Store in S3
            results_key = f"{VIDEO_SUMMARY_PREFIX}{self.call_id}/video-analysis.json"
            S3_CLIENT.put_object(
                Bucket=VIDEO_SUMMARY_BUCKET,
                Key=results_key,
                Body=json.dumps(results_data, indent=2),
                ContentType="application/json"
            )
            
            # Update AppSync with video analysis results
            await self._update_appsync_results(results_data)
            
            LOGGER.debug(f"Stored video analysis results for call: {self.call_id}")

            # Invoke orchestrator Lambda after successful S3 write
            if ASYNC_TRANSCRIPT_SUMMARY_ORCHESTRATOR_ARN:
                try:
                    payload = {
                        "CallId": self.call_id,
                        # Add any other fields needed by orchestrator
                    }
                    LAMBDA_CLIENT.invoke(
                        FunctionName=ASYNC_TRANSCRIPT_SUMMARY_ORCHESTRATOR_ARN,
                        InvocationType='Event',
                        Payload=json.dumps(payload)
                    )
                    LOGGER.debug(f"Invoked orchestrator Lambda for call: {self.call_id}")
                except Exception as invoke_err:
                    LOGGER.error(f"Failed to invoke orchestrator Lambda: {invoke_err}")

            # After successful S3 upload, call the helper:
            emit_add_s3_recording_url_event(self.call_id, self.video_bucket, self.video_key)
            # Wait for RecordingUrl to be set in the call record
            recording_url = await wait_for_recording_url(self.call_id)
            if recording_url:
                emit_end_event(self.call_id, self.video_bucket, self.video_key)
            else:
                LOGGER.error(f"Could not emit END event because RecordingUrl was not set for call {self.call_id}")
            
        except Exception as e:
            LOGGER.error(f"Error storing results: {str(e)}")
            raise
    
    async def _update_appsync_results(self, results_data: Dict):
        """Update AppSync with video analysis results"""
        try:
            # GraphQL mutation to update call with video analysis
            mutation = """
            mutation UpdateCallWithVideoAnalysis($callId: String!, $videoAnalysis: String!) {
                updateCallWithVideoAnalysis(callId: $callId, videoAnalysis: $videoAnalysis) {
                    callId
                    success
                }
            }
            """
            
            variables = {
                "callId": self.call_id,
                "videoAnalysis": json.dumps(results_data)
            }
            
            result = await APPSYNC_CLIENT.execute(mutation, variable_values=variables)
            LOGGER.debug(f"Updated AppSync with video analysis for call: {self.call_id}")
            
        except Exception as e:
            LOGGER.error(f"Error updating AppSync: {str(e)}")
            # Don't fail the entire process if AppSync update fails


async def process_video_event(event: Dict) -> Dict:
    """Process video analysis event"""
    try:
        # LOGGER.debug(f"Incoming event: {json.dumps(event)}")
        # Extract event data (support both lowerCamelCase and UpperCamelCase)
        call_id = event.get("callId") or event.get("CallId")
        video_bucket = event.get("videoBucket") or event.get("VideoBucket")
        video_key = event.get("videoKey") or event.get("VideoKey")
        transcript_data = event.get("transcriptData") or event.get("TranscriptData")
        LOGGER.debug(f"Variables: call_id: {call_id} video_bucket: {video_bucket} video_key: {video_key} transcript_data: {transcript_data}")
        
        if not call_id or not video_bucket or not video_key:
            raise ValueError("Missing required fields: callId, videoBucket, and videoKey")
        
        # Create processor and run analysis
        processor = VideoAnalysisProcessor(call_id, video_bucket, video_key, transcript_data)
        result = await processor.process_video()
        
        return result
        
    except Exception as e:
        LOGGER.error(f"Error processing video event: {str(e)}")
        return {
            "error": str(e),
            "status": "failed"
        }


@LOGGER.inject_lambda_context
def handler(event, context: LambdaContext):
    """Lambda handler for video analysis processing"""
    # pylint: disable=unused-argument
    LOGGER.debug("lambda event", extra={"event": event})
    
    # Process the event
    result = EVENT_LOOP.run_until_complete(process_video_event(event))
    
    LOGGER.debug("video analysis result", extra={"result": result})
    if result.get("status") == "failed":
        LOGGER.error("Video analysis failed", extra={"error": result.get("error")})
        raise Exception(f"Video analysis failed: {result.get('error')}")
    
    return result 