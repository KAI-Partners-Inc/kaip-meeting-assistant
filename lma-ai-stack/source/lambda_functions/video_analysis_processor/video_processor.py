#!/usr/bin/env python3.12
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
""" Video Processing Module for Frame Extraction and Analysis
"""
import cv2
import numpy as np
from typing import List, Dict, Tuple
import tempfile
import os
from aws_lambda_powertools import Logger

LOGGER = Logger(location="%(filename)s:%(lineno)d - %(funcName)s()")


class VideoProcessor:
    """Handles video processing operations including frame extraction"""
    
    def __init__(self, s3_client, rekognition_client):
        self.s3_client = s3_client
        self.rekognition_client = rekognition_client
        self.frame_interval = 5  # Extract frame every 5 seconds
        self.max_frames = 20  # Maximum frames to extract
        
    async def extract_key_frames(self, video_path: str) -> List[Dict]:
        """Extract key frames from video for analysis"""
        try:
            LOGGER.info(f"Extracting frames from video: {video_path}")
            
            # Open video file
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError("Could not open video file")
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            duration = total_frames / fps if fps > 0 else 0
            
            LOGGER.info(f"Video properties - FPS: {fps}, Duration: {duration}s, Total frames: {total_frames}")
            
            frames = []
            frame_count = 0
            extracted_count = 0
            
            # Extract frames at regular intervals
            while cap.isOpened() and extracted_count < self.max_frames:
                ret, frame = cap.read()
                if not ret:
                    break
                
                # Extract frame at intervals
                if frame_count % int(fps * self.frame_interval) == 0:
                    frame_data = await self._process_frame(frame, frame_count, fps)
                    frames.append(frame_data)
                    extracted_count += 1
                
                frame_count += 1
            
            cap.release()
            
            LOGGER.info(f"Extracted {len(frames)} frames from video")
            return frames
            
        except Exception as e:
            LOGGER.error(f"Error extracting frames: {str(e)}")
            raise
    
    async def _process_frame(self, frame: np.ndarray, frame_number: int, fps: float) -> Dict:
        """Process individual frame and extract relevant information"""
        try:
            # Convert frame to RGB (OpenCV uses BGR)
            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            
            # Get frame dimensions
            height, width = frame.shape[:2]
            
            # Calculate timestamp
            timestamp = frame_number / fps if fps > 0 else 0
            
            # Save frame to temporary file for Rekognition
            temp_frame_path = await self._save_frame_temp(frame_rgb)
            
            # Extract text from frame using Rekognition
            text_analysis = await self._extract_text_from_frame(temp_frame_path)
            
            # Detect objects and scenes
            object_analysis = await self._detect_objects_in_frame(temp_frame_path)
            
            # Clean up temp file
            self._cleanup_temp_file(temp_frame_path)
            
            return {
                "frame_number": frame_number,
                "timestamp": timestamp,
                "dimensions": {"width": width, "height": height},
                "text_content": text_analysis,
                "objects_detected": object_analysis,
                "frame_path": temp_frame_path  # Keep for further processing
            }
            
        except Exception as e:
            LOGGER.error(f"Error processing frame {frame_number}: {str(e)}")
            return {
                "frame_number": frame_number,
                "timestamp": frame_number / fps if fps > 0 else 0,
                "error": str(e)
            }
    
    async def _save_frame_temp(self, frame: np.ndarray) -> str:
        """Save frame to temporary file"""
        try:
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.jpg')
            temp_path = temp_file.name
            temp_file.close()
            
            # Save frame as JPEG
            cv2.imwrite(temp_path, cv2.cvtColor(frame, cv2.COLOR_RGB2BGR))
            
            return temp_path
            
        except Exception as e:
            LOGGER.error(f"Error saving frame to temp file: {str(e)}")
            raise
    
    async def _extract_text_from_frame(self, frame_path: str) -> Dict:
        """Extract text from frame using Amazon Rekognition"""
        try:
            with open(frame_path, 'rb') as image_file:
                image_bytes = image_file.read()
            
            response = self.rekognition_client.detect_text(
                Image={'Bytes': image_bytes}
            )
            
            text_blocks = []
            for text_detection in response.get('TextDetections', []):
                if text_detection['Type'] == 'LINE':
                    text_blocks.append({
                        'text': text_detection['DetectedText'],
                        'confidence': text_detection['Confidence'],
                        'geometry': text_detection['Geometry']
                    })
            
            return {
                'text_blocks': text_blocks,
                'total_text': len(text_blocks)
            }
            
        except Exception as e:
            LOGGER.error(f"Error extracting text from frame: {str(e)}")
            return {'text_blocks': [], 'total_text': 0, 'error': str(e)}
    
    async def _detect_objects_in_frame(self, frame_path: str) -> Dict:
        """Detect objects in frame using Amazon Rekognition"""
        try:
            with open(frame_path, 'rb') as image_file:
                image_bytes = image_file.read()
            
            response = self.rekognition_client.detect_labels(
                Image={'Bytes': image_bytes},
                MaxLabels=10,
                MinConfidence=70.0
            )
            
            objects = []
            for label in response.get('Labels', []):
                objects.append({
                    'name': label['Name'],
                    'confidence': label['Confidence'],
                    'instances': len(label.get('Instances', []))
                })
            
            return {
                'objects': objects,
                'total_objects': len(objects)
            }
            
        except Exception as e:
            LOGGER.error(f"Error detecting objects in frame: {str(e)}")
            return {'objects': [], 'total_objects': 0, 'error': str(e)}
    
    def _cleanup_temp_file(self, file_path: str):
        """Clean up temporary file"""
        try:
            if os.path.exists(file_path):
                os.unlink(file_path)
        except Exception as e:
            LOGGER.warning(f"Error cleaning up temp file {file_path}: {str(e)}")
    
    async def analyze_video_metadata(self, video_path: str) -> Dict:
        """Analyze video metadata and properties"""
        try:
            cap = cv2.VideoCapture(video_path)
            if not cap.isOpened():
                raise ValueError("Could not open video file")
            
            # Get video properties
            fps = cap.get(cv2.CAP_PROP_FPS)
            total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
            width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
            height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
            duration = total_frames / fps if fps > 0 else 0
            
            cap.release()
            
            return {
                'duration_seconds': duration,
                'fps': fps,
                'total_frames': total_frames,
                'resolution': f"{width}x{height}",
                'width': width,
                'height': height
            }
            
        except Exception as e:
            LOGGER.error(f"Error analyzing video metadata: {str(e)}")
            raise 