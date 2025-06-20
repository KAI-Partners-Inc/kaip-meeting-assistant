#!/usr/bin/env python3.12
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
""" Video Analysis and Screen Recording Summarization Lambda Function
"""
import asyncio
import json
import os
import tempfile
from typing import Dict, List, Optional
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
S3_BUCKET_NAME = os.environ.get("S3_BUCKET_NAME")
VIDEO_FILE_PREFIX = os.environ.get("VIDEO_FILE_PREFIX", "lma-video-recordings/")
RECORDINGS_BUCKET_NAME = os.environ.get("RECORDINGS_BUCKET_NAME")

# AWS clients
BOTO3_SESSION: Boto3Session = boto3.Session()
CLIENT_CONFIG = BotoCoreConfig(
    retries={"mode": "adaptive", "max_attempts": 3},
)

S3_CLIENT: S3Client = BOTO3_SESSION.client("s3", config=CLIENT_CONFIG)
REKOGNITION_CLIENT: RekognitionClient = BOTO3_SESSION.client("rekognition", config=CLIENT_CONFIG)
BEDROCK_CLIENT: BedrockClient = BOTO3_SESSION.client("bedrock-runtime", config=CLIENT_CONFIG)

APPSYNC_CLIENT = AppsyncAioGqlClient(
    url=APPSYNC_GRAPHQL_URL, fetch_schema_from_transport=True)

LOGGER = Logger(location="%(filename)s:%(lineno)d - %(funcName)s()")

EVENT_LOOP = asyncio.get_event_loop()


class VideoAnalysisProcessor:
    """Processes video recordings and generates summaries alongside transcript analysis"""
    
    def __init__(self, call_id: str, video_url: str, transcript_data: Optional[Dict] = None):
        self.call_id = call_id
        self.video_url = video_url
        self.transcript_data = transcript_data or {}
        self.video_processor = VideoProcessor(S3_CLIENT, REKOGNITION_CLIENT)
        self.screen_analyzer = ScreenAnalyzer(REKOGNITION_CLIENT)
        self.summary_generator = VideoSummaryGenerator(BEDROCK_CLIENT)
        
    async def process_video(self) -> Dict:
        """Main processing pipeline for video analysis"""
        try:
            LOGGER.info(f"Starting video analysis for call: {self.call_id}")
            
            # Download video from S3
            video_path = await self._download_video()
            
            # Extract frames for analysis
            frames = await self.video_processor.extract_key_frames(video_path)
            
            # Analyze screen content
            screen_analysis = await self.screen_analyzer.analyze_frames(frames)
            
            # Generate video summary
            video_summary = await self.summary_generator.generate_summary(
                screen_analysis, self.transcript_data
            )
            
            # Store results
            await self._store_results(video_summary, screen_analysis)
            
            # Cleanup
            self._cleanup_temp_files(video_path)
            
            LOGGER.info(f"Video analysis completed for call: {self.call_id}")
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
    
    async def _download_video(self) -> str:
        """Download video file from S3 to local temp storage"""
        try:
            # Extract key from video URL
            video_key = self.video_url.split('.com/')[-1]
            
            # Create temp file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.mp4')
            temp_path = temp_file.name
            temp_file.close()
            
            # Download from S3
            S3_CLIENT.download_file(
                RECORDINGS_BUCKET_NAME,
                video_key,
                temp_path
            )
            
            LOGGER.info(f"Downloaded video to: {temp_path}")
            return temp_path
            
        except Exception as e:
            LOGGER.error(f"Error downloading video: {str(e)}")
            raise
    
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
                    "video_url": self.video_url,
                    "processing_version": "1.0"
                }
            }
            
            # Store in S3
            results_key = f"{VIDEO_FILE_PREFIX}{self.call_id}/video-analysis.json"
            S3_CLIENT.put_object(
                Bucket=S3_BUCKET_NAME,
                Key=results_key,
                Body=json.dumps(results_data, indent=2),
                ContentType="application/json"
            )
            
            # Update AppSync with video analysis results
            await self._update_appsync_results(results_data)
            
            LOGGER.info(f"Stored video analysis results for call: {self.call_id}")
            
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
                    videoAnalysis
                    updatedAt
                }
            }
            """
            
            variables = {
                "callId": self.call_id,
                "videoAnalysis": json.dumps(results_data)
            }
            
            await APPSYNC_CLIENT.execute(mutation, variables)
            LOGGER.info(f"Updated AppSync with video analysis for call: {self.call_id}")
            
        except Exception as e:
            LOGGER.error(f"Error updating AppSync: {str(e)}")
            # Don't raise - this is not critical for the main processing
    
    def _cleanup_temp_files(self, video_path: str):
        """Clean up temporary files"""
        try:
            if os.path.exists(video_path):
                os.unlink(video_path)
                LOGGER.info(f"Cleaned up temp file: {video_path}")
        except Exception as e:
            LOGGER.warning(f"Error cleaning up temp file: {str(e)}")


async def process_video_event(event: Dict) -> Dict:
    """Process video analysis event"""
    try:
        # Extract event data
        call_id = event.get("callId")
        video_url = event.get("videoUrl")
        transcript_data = event.get("transcriptData")
        
        if not call_id or not video_url:
            raise ValueError("Missing required fields: callId and videoUrl")
        
        # Create processor and run analysis
        processor = VideoAnalysisProcessor(call_id, video_url, transcript_data)
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