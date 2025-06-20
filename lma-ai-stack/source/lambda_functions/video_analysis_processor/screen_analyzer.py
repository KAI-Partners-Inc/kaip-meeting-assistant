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
            raise
    
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
                    "key_text": [block.get('text', '')[:50] for block in text_content.get('text_blocks', [])[:3]],
                    "key_objects": [obj.get('name', '') for obj in objects_detected.get('objects', [])[:3]]
                }
                
                timeline.append(activity)
            
            # Identify activity clusters
            activity_clusters = self._identify_activity_clusters(timeline)
            
            return {
                "timeline": timeline,
                "activity_clusters": activity_clusters,
                "total_activities": len(timeline)
            }
            
        except Exception as e:
            LOGGER.error(f"Error generating activity timeline: {str(e)}")
            return {"error": str(e)}
    
    async def _identify_key_elements(self, frames: List[Dict]) -> Dict:
        """Identify key screen elements and UI components"""
        try:
            ui_elements = {
                "buttons": [],
                "menus": [],
                "tabs": [],
                "forms": [],
                "charts": [],
                "tables": []
            }
            
            # Analyze text content for UI patterns
            for frame in frames:
                text_blocks = frame.get('text_content', {}).get('text_blocks', [])
                
                for text_block in text_blocks:
                    text = text_block.get('text', '').lower()
                    
                    # Simple pattern matching for UI elements
                    if any(word in text for word in ['button', 'click', 'submit', 'save']):
                        ui_elements["buttons"].append(text)
                    elif any(word in text for word in ['menu', 'file', 'edit', 'view']):
                        ui_elements["menus"].append(text)
                    elif any(word in text for word in ['tab', 'page', 'section']):
                        ui_elements["tabs"].append(text)
                    elif any(word in text for word in ['form', 'input', 'field', 'enter']):
                        ui_elements["forms"].append(text)
                    elif any(word in text for word in ['chart', 'graph', 'plot', 'data']):
                        ui_elements["charts"].append(text)
                    elif any(word in text for word in ['table', 'row', 'column', 'cell']):
                        ui_elements["tables"].append(text)
            
            # Count occurrences
            element_counts = {key: len(value) for key, value in ui_elements.items()}
            
            return {
                "ui_elements": ui_elements,
                "element_counts": element_counts,
                "most_common_elements": sorted(element_counts.items(), key=lambda x: x[1], reverse=True)
            }
            
        except Exception as e:
            LOGGER.error(f"Error identifying key elements: {str(e)}")
            return {"error": str(e)}
    
    async def _generate_screen_summary(self, frames: List[Dict]) -> Dict:
        """Generate a summary of screen content analysis"""
        try:
            total_frames = len(frames)
            if total_frames == 0:
                return {"error": "No frames to analyze"}
            
            # Calculate overall statistics
            total_text_blocks = sum(frame.get('text_content', {}).get('total_text', 0) for frame in frames)
            total_objects = sum(frame.get('objects_detected', {}).get('total_objects', 0) for frame in frames)
            
            # Determine content type
            if total_text_blocks > total_objects * 2:
                content_type = "text-heavy"
            elif total_objects > total_text_blocks * 2:
                content_type = "visual-heavy"
            else:
                content_type = "mixed"
            
            # Identify primary activity
            activities = []
            for frame in frames:
                text_count = frame.get('text_content', {}).get('total_text', 0)
                object_count = frame.get('objects_detected', {}).get('total_objects', 0)
                
                if text_count > 5:
                    activities.append("reading/documentation")
                elif object_count > 5:
                    activities.append("visual_analysis")
                else:
                    activities.append("general_browsing")
            
            activity_counter = Counter(activities)
            primary_activity = activity_counter.most_common(1)[0][0] if activity_counter else "unknown"
            
            return {
                "total_frames_analyzed": total_frames,
                "average_text_per_frame": total_text_blocks / total_frames if total_frames > 0 else 0,
                "average_objects_per_frame": total_objects / total_frames if total_frames > 0 else 0,
                "content_type": content_type,
                "primary_activity": primary_activity,
                "activity_distribution": dict(activity_counter)
            }
            
        except Exception as e:
            LOGGER.error(f"Error generating screen summary: {str(e)}")
            return {"error": str(e)}
    
    def _identify_activity_clusters(self, timeline: List[Dict]) -> List[Dict]:
        """Identify clusters of similar activities"""
        try:
            clusters = []
            current_cluster = {
                "start_time": timeline[0]["timestamp"] if timeline else 0,
                "end_time": 0,
                "activities": []
            }
            
            for i, activity in enumerate(timeline):
                # Simple clustering based on activity similarity
                if i > 0:
                    prev_activity = timeline[i-1]
                    time_diff = activity["timestamp"] - prev_activity["timestamp"]
                    
                    # Start new cluster if significant time gap or activity change
                    if time_diff > 30 or abs(activity["text_count"] - prev_activity["text_count"]) > 5:
                        # End current cluster
                        current_cluster["end_time"] = prev_activity["timestamp"]
                        clusters.append(current_cluster)
                        
                        # Start new cluster
                        current_cluster = {
                            "start_time": activity["timestamp"],
                            "end_time": 0,
                            "activities": []
                        }
                
                current_cluster["activities"].append(activity)
            
            # Add final cluster
            if current_cluster["activities"]:
                current_cluster["end_time"] = timeline[-1]["timestamp"] if timeline else 0
                clusters.append(current_cluster)
            
            return clusters
            
        except Exception as e:
            LOGGER.error(f"Error identifying activity clusters: {str(e)}")
            return [] 