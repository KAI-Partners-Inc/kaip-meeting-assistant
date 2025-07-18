#!/usr/bin/env python3.12
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
""" Screen Content Analysis Module
"""
from typing import List, Dict, Set
from collections import Counter, defaultdict
import re
from aws_lambda_powertools import Logger

LOGGER = Logger(location="%(filename)s:%(lineno)d - %(funcName)s()")


class ScreenAnalyzer:
    """Analyzes screen content from video frames to extract meaningful insights"""
    
    def __init__(self, rekognition_client):
        self.rekognition_client = rekognition_client
        self.application_keywords = {
            'presentation': ['powerpoint', 'slides', 'presentation', 'deck'],
            'document': ['word', 'document', 'text', 'paragraph', 'page'],
            'spreadsheet': ['excel', 'spreadsheet', 'table', 'cell', 'row', 'column'],
            'browser': ['chrome', 'firefox', 'safari', 'browser', 'web', 'url'],
            'meeting': ['zoom', 'teams', 'meet', 'webex', 'conference', 'video'],
            'code': ['code', 'programming', 'development', 'terminal', 'console'],
            'design': ['photoshop', 'illustrator', 'design', 'graphic', 'image']
        }
        
    async def analyze_frames(self, frames: List[Dict]) -> Dict:
        """Analyze all frames and generate comprehensive screen analysis"""
        try:
            LOGGER.info(f"Analyzing {len(frames)} frames for screen content")
            
            if not frames:
                # Return basic analysis when no frames are available
                return await self._create_basic_analysis()
            
            # Extract text content across all frames
            text_analysis = await self._analyze_text_content(frames)
            
            # Analyze objects and applications
            object_analysis = await self._analyze_objects_and_applications(frames)
            
            # Detect screen patterns and activities
            pattern_analysis = await self._detect_screen_patterns(frames)
            
            # Generate screen activity timeline
            timeline_analysis = await self._generate_activity_timeline(frames)
            
            # Identify key screen elements
            element_analysis = await self._identify_key_elements(frames)
            
            return {
                "text_analysis": text_analysis,
                "object_analysis": object_analysis,
                "pattern_analysis": pattern_analysis,
                "timeline_analysis": timeline_analysis,
                "element_analysis": element_analysis,
                "summary": await self._generate_screen_summary(frames)
            }
            
        except Exception as e:
            LOGGER.error(f"Error analyzing frames: {str(e)}")
            return await self._create_basic_analysis()
    
    async def _create_basic_analysis(self) -> Dict:
        """Create a basic analysis when no frame data is available"""
        return {
            "text_analysis": {
                "total_text_blocks": 0,
                "unique_text_count": 0,
                "common_text": [],
                "important_text": [],
                "text_by_timestamp": {},
                "text_density": 0,
                "note": "No frame data available for text analysis"
            },
            "object_analysis": {
                "total_objects_detected": 0,
                "unique_objects": 0,
                "common_objects": [],
                "application_usage": {},
                "primary_application": None,
                "note": "No frame data available for object analysis"
            },
            "pattern_analysis": {
                "static_content": {"count": 0, "percentage": 0},
                "dynamic_content": {"count": 0, "percentage": 0},
                "text_heavy_frames": {"count": 0, "percentage": 0},
                "image_heavy_frames": {"count": 0, "percentage": 0},
                "mixed_content_frames": {"count": 0, "percentage": 0},
                "note": "No frame data available for pattern analysis"
            },
            "timeline_analysis": {
                "activities": [],
                "activity_clusters": [],
                "total_activities": 0,
                "note": "No frame data available for timeline analysis"
            },
            "element_analysis": {
                "key_elements": [],
                "element_frequency": {},
                "note": "No frame data available for element analysis"
            },
            "summary": {
                "screen_content_type": "unknown",
                "primary_activities": [],
                "content_complexity": "unknown",
                "note": "Basic analysis - full analysis requires frame extraction"
            }
        }
    
    async def _analyze_text_content(self, frames: List[Dict]) -> Dict:
        """Analyze text content across all frames"""
        try:
            all_text = []
            text_by_timestamp = {}
            
            for frame in frames:
                timestamp = frame.get('timestamp', 0)
                text_content = frame.get('text_content', {})
                
                # Collect all text blocks
                for text_block in text_content.get('text_blocks', []):
                    text = text_block.get('text', '').strip()
                    if text and len(text) > 2:  # Filter out very short text
                        all_text.append({
                            'text': text,
                            'timestamp': timestamp,
                            'confidence': text_block.get('confidence', 0)
                        })
                
                text_by_timestamp[timestamp] = text_content.get('text_blocks', [])
            
            # Analyze text patterns
            text_frequency = Counter([item['text'] for item in all_text])
            common_text = text_frequency.most_common(10)
            
            # Identify potential headings, titles, or important text
            important_text = [text for text, count in common_text if count > 1]
            
            return {
                "total_text_blocks": len(all_text),
                "unique_text_count": len(text_frequency),
                "common_text": common_text,
                "important_text": important_text,
                "text_by_timestamp": text_by_timestamp,
                "text_density": len(all_text) / len(frames) if frames else 0
            }
            
        except Exception as e:
            LOGGER.error(f"Error analyzing text content: {str(e)}")
            return {"error": str(e)}
    
    async def _analyze_objects_and_applications(self, frames: List[Dict]) -> Dict:
        """Analyze objects and identify applications being used"""
        try:
            all_objects = []
            application_usage = defaultdict(int)
            
            for frame in frames:
                objects_detected = frame.get('objects_detected', {})
                
                for obj in objects_detected.get('objects', []):
                    object_name = obj.get('name', '').lower()
                    all_objects.append(object_name)
                    
                    # Check if object indicates application usage
                    for app_type, keywords in self.application_keywords.items():
                        if any(keyword in object_name for keyword in keywords):
                            application_usage[app_type] += 1
            
            # Count object frequencies
            object_frequency = Counter(all_objects)
            common_objects = object_frequency.most_common(15)
            
            # Identify primary applications
            primary_apps = sorted(application_usage.items(), key=lambda x: x[1], reverse=True)
            
            return {
                "total_objects_detected": len(all_objects),
                "unique_objects": len(object_frequency),
                "common_objects": common_objects,
                "application_usage": dict(primary_apps),
                "primary_application": primary_apps[0][0] if primary_apps else None
            }
            
        except Exception as e:
            LOGGER.error(f"Error analyzing objects and applications: {str(e)}")
            return {"error": str(e)}
    
    async def _detect_screen_patterns(self, frames: List[Dict]) -> Dict:
        """Detect patterns in screen content and user behavior"""
        try:
            patterns = {
                "static_content": 0,
                "dynamic_content": 0,
                "text_heavy_frames": 0,
                "image_heavy_frames": 0,
                "mixed_content_frames": 0
            }
            
            text_density_threshold = 3  # Frames with more than 3 text blocks
            object_density_threshold = 5  # Frames with more than 5 objects
            
            for frame in frames:
                text_count = frame.get('text_content', {}).get('total_text', 0)
                object_count = frame.get('objects_detected', {}).get('total_objects', 0)
                
                # Categorize frame content
                if text_count > text_density_threshold:
                    patterns["text_heavy_frames"] += 1
                elif object_count > object_density_threshold:
                    patterns["image_heavy_frames"] += 1
                else:
                    patterns["mixed_content_frames"] += 1
                
                # Detect static vs dynamic content (simplified)
                if text_count > 0 and object_count > 0:
                    patterns["mixed_content_frames"] += 1
                elif text_count > 0:
                    patterns["static_content"] += 1
                else:
                    patterns["dynamic_content"] += 1
            
            # Calculate percentages
            total_frames = len(frames)
            if total_frames > 0:
                for key in patterns:
                    patterns[key] = {
                        "count": patterns[key],
                        "percentage": (patterns[key] / total_frames) * 100
                    }
            
            return patterns
            
        except Exception as e:
            LOGGER.error(f"Error detecting screen patterns: {str(e)}")
            return {"error": str(e)}
    
    async def _generate_activity_timeline(self, frames: List[Dict]) -> Dict:
        """Generate timeline of screen activities"""
        try:
            timeline = []
            
            for frame in frames:
                timestamp = frame.get('timestamp', 0)
                text_content = frame.get('text_content', {})
                objects_detected = frame.get('objects_detected', {})
                
                activity = {
                    "timestamp": timestamp,
                    "text_count": text_content.get('total_text', 0),
                    "object_count": objects_detected.get('total_objects', 0),
                    "activity_type": self._determine_activity_type(text_content, objects_detected)
                }
                timeline.append(activity)
            
            # Identify activity clusters
            activity_clusters = self._identify_activity_clusters(timeline)
            
            return {
                "activities": timeline,
                "activity_clusters": activity_clusters,
                "total_activities": len(timeline)
            }
            
        except Exception as e:
            LOGGER.error(f"Error generating activity timeline: {str(e)}")
            return {"error": str(e)}
    
    async def _identify_key_elements(self, frames: List[Dict]) -> Dict:
        """Identify key screen elements and their frequency"""
        try:
            key_elements = []
            element_frequency = defaultdict(int)
            
            for frame in frames:
                text_content = frame.get('text_content', {})
                objects_detected = frame.get('objects_detected', {})
                
                # Collect text elements
                for text_block in text_content.get('text_blocks', []):
                    text = text_block.get('text', '').strip()
                    if text and len(text) > 5:  # Focus on longer text
                        element_frequency[text] += 1
                
                # Collect object elements
                for obj in objects_detected.get('objects', []):
                    obj_name = obj.get('name', '').strip()
                    if obj_name:
                        element_frequency[obj_name] += 1
            
            # Get most frequent elements
            sorted_elements = sorted(element_frequency.items(), key=lambda x: x[1], reverse=True)
            key_elements = [{"element": elem, "frequency": freq} for elem, freq in sorted_elements[:10]]
            
            return {
                "key_elements": key_elements,
                "element_frequency": dict(element_frequency)
            }
            
        except Exception as e:
            LOGGER.error(f"Error identifying key elements: {str(e)}")
            return {"error": str(e)}
    
    async def _generate_screen_summary(self, frames: List[Dict]) -> Dict:
        """Generate a comprehensive summary of screen content"""
        try:
            if not frames:
                return {
                    "screen_content_type": "unknown",
                    "primary_activities": [],
                    "content_complexity": "unknown"
                }
            
            # Analyze content types
            text_frames = sum(1 for f in frames if f.get('text_content', {}).get('total_text', 0) > 0)
            object_frames = sum(1 for f in frames if f.get('objects_detected', {}).get('total_objects', 0) > 0)
            
            # Determine content type
            if text_frames > len(frames) * 0.7:
                content_type = "text_heavy"
            elif object_frames > len(frames) * 0.7:
                content_type = "visual_heavy"
            else:
                content_type = "mixed_content"
            
            # Identify primary activities
            activities = []
            for frame in frames:
                activity = self._determine_activity_type(
                    frame.get('text_content', {}),
                    frame.get('objects_detected', {})
                )
                if activity not in activities:
                    activities.append(activity)
            
            # Determine complexity
            total_elements = sum(
                f.get('text_content', {}).get('total_text', 0) + 
                f.get('objects_detected', {}).get('total_objects', 0)
                for f in frames
            )
            
            if total_elements > len(frames) * 10:
                complexity = "high"
            elif total_elements > len(frames) * 5:
                complexity = "medium"
            else:
                complexity = "low"
            
            return {
                "screen_content_type": content_type,
                "primary_activities": activities[:5],
                "content_complexity": complexity
            }
            
        except Exception as e:
            LOGGER.error(f"Error generating screen summary: {str(e)}")
            return {"error": str(e)}
    
    def _determine_activity_type(self, text_content: Dict, objects_detected: Dict) -> str:
        """Determine the type of activity based on content"""
        text_count = text_content.get('total_text', 0)
        object_count = objects_detected.get('total_objects', 0)
        
        if text_count > 5:
            return "text_heavy"
        elif object_count > 5:
            return "visual_heavy"
        elif text_count > 0 and object_count > 0:
            return "mixed"
        else:
            return "minimal"
    
    def _identify_activity_clusters(self, timeline: List[Dict]) -> List[Dict]:
        """Identify clusters of similar activities"""
        try:
            clusters = []
            current_cluster = []
            
            for activity in timeline:
                if not current_cluster:
                    current_cluster = [activity]
                elif activity['activity_type'] == current_cluster[-1]['activity_type']:
                    current_cluster.append(activity)
                else:
                    if len(current_cluster) > 1:
                        clusters.append({
                            "activity_type": current_cluster[0]['activity_type'],
                            "start_time": current_cluster[0]['timestamp'],
                            "end_time": current_cluster[-1]['timestamp'],
                            "duration": current_cluster[-1]['timestamp'] - current_cluster[0]['timestamp'],
                            "activity_count": len(current_cluster)
                        })
                    current_cluster = [activity]
            
            # Add final cluster
            if len(current_cluster) > 1:
                clusters.append({
                    "activity_type": current_cluster[0]['activity_type'],
                    "start_time": current_cluster[0]['timestamp'],
                    "end_time": current_cluster[-1]['timestamp'],
                    "duration": current_cluster[-1]['timestamp'] - current_cluster[0]['timestamp'],
                    "activity_count": len(current_cluster)
                })
            
            return clusters
            
        except Exception as e:
            LOGGER.error(f"Error identifying activity clusters: {str(e)}")
            return [] 