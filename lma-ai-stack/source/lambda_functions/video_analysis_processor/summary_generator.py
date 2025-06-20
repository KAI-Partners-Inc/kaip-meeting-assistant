#!/usr/bin/env python3.12
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0
""" Video Summary Generator using Amazon Bedrock
"""
import json
from typing import Dict, List, Optional
from aws_lambda_powertools import Logger

LOGGER = Logger(location="%(filename)s:%(lineno)d - %(funcName)s()")


class VideoSummaryGenerator:
    """Generates comprehensive summaries combining screen content and transcript analysis"""
    
    def __init__(self, bedrock_client):
        self.bedrock_client = bedrock_client
        self.model_id = "anthropic.claude-3-sonnet-20240229-v1:0"
        
    async def generate_summary(self, screen_analysis: Dict, transcript_data: Optional[Dict] = None) -> Dict:
        """Generate comprehensive summary combining screen and transcript analysis"""
        try:
            LOGGER.info("Generating comprehensive video summary")
            
            # Prepare analysis data
            analysis_data = self._prepare_analysis_data(screen_analysis, transcript_data)
            
            # Generate different types of summaries
            executive_summary = await self._generate_executive_summary(analysis_data)
            detailed_summary = await self._generate_detailed_summary(analysis_data)
            key_insights = await self._generate_key_insights(analysis_data)
            action_items = await self._generate_action_items(analysis_data)
            
            return {
                "executive_summary": executive_summary,
                "detailed_summary": detailed_summary,
                "key_insights": key_insights,
                "action_items": action_items,
                "analysis_metadata": {
                    "screen_content_type": screen_analysis.get("summary", {}).get("content_type", "unknown"),
                    "primary_activity": screen_analysis.get("summary", {}).get("primary_activity", "unknown"),
                    "total_frames_analyzed": screen_analysis.get("summary", {}).get("total_frames_analyzed", 0)
                }
            }
            
        except Exception as e:
            LOGGER.error(f"Error generating summary: {str(e)}")
            raise
    
    def _prepare_analysis_data(self, screen_analysis: Dict, transcript_data: Optional[Dict]) -> Dict:
        """Prepare and structure analysis data for summary generation"""
        try:
            # Extract key information from screen analysis
            screen_summary = screen_analysis.get("summary", {})
            text_analysis = screen_analysis.get("text_analysis", {})
            object_analysis = screen_analysis.get("object_analysis", {})
            pattern_analysis = screen_analysis.get("pattern_analysis", {})
            
            # Extract transcript information
            transcript_summary = ""
            transcript_key_points = []
            if transcript_data:
                transcript_summary = transcript_data.get("summary", "")
                transcript_key_points = transcript_data.get("key_points", [])
            
            return {
                "screen_content": {
                    "content_type": screen_summary.get("content_type", "unknown"),
                    "primary_activity": screen_summary.get("primary_activity", "unknown"),
                    "total_frames": screen_summary.get("total_frames_analyzed", 0),
                    "text_density": screen_summary.get("average_text_per_frame", 0),
                    "object_density": screen_summary.get("average_objects_per_frame", 0)
                },
                "text_content": {
                    "total_text_blocks": text_analysis.get("total_text_blocks", 0),
                    "important_text": text_analysis.get("important_text", []),
                    "common_text": text_analysis.get("common_text", [])
                },
                "applications": {
                    "primary_application": object_analysis.get("primary_application"),
                    "application_usage": object_analysis.get("application_usage", {}),
                    "common_objects": object_analysis.get("common_objects", [])
                },
                "patterns": {
                    "text_heavy_frames": pattern_analysis.get("text_heavy_frames", {}).get("percentage", 0),
                    "image_heavy_frames": pattern_analysis.get("image_heavy_frames", {}).get("percentage", 0),
                    "mixed_content_frames": pattern_analysis.get("mixed_content_frames", {}).get("percentage", 0)
                },
                "transcript": {
                    "summary": transcript_summary,
                    "key_points": transcript_key_points
                }
            }
            
        except Exception as e:
            LOGGER.error(f"Error preparing analysis data: {str(e)}")
            raise
    
    async def _generate_executive_summary(self, analysis_data: Dict) -> str:
        """Generate executive summary of the meeting"""
        try:
            prompt = self._create_executive_summary_prompt(analysis_data)
            response = await self._call_bedrock_model(prompt)
            return response
            
        except Exception as e:
            LOGGER.error(f"Error generating executive summary: {str(e)}")
            return "Unable to generate executive summary due to processing error."
    
    async def _generate_detailed_summary(self, analysis_data: Dict) -> str:
        """Generate detailed summary with technical insights"""
        try:
            prompt = self._create_detailed_summary_prompt(analysis_data)
            response = await self._call_bedrock_model(prompt)
            return response
            
        except Exception as e:
            LOGGER.error(f"Error generating detailed summary: {str(e)}")
            return "Unable to generate detailed summary due to processing error."
    
    async def _generate_key_insights(self, analysis_data: Dict) -> List[str]:
        """Generate key insights from the analysis"""
        try:
            prompt = self._create_key_insights_prompt(analysis_data)
            response = await self._call_bedrock_model(prompt)
            
            # Parse response into list of insights
            insights = self._parse_insights_response(response)
            return insights
            
        except Exception as e:
            LOGGER.error(f"Error generating key insights: {str(e)}")
            return ["Unable to generate key insights due to processing error."]
    
    async def _generate_action_items(self, analysis_data: Dict) -> List[Dict]:
        """Generate actionable items from the analysis"""
        try:
            prompt = self._create_action_items_prompt(analysis_data)
            response = await self._call_bedrock_model(prompt)
            
            # Parse response into structured action items
            action_items = self._parse_action_items_response(response)
            return action_items
            
        except Exception as e:
            LOGGER.error(f"Error generating action items: {str(e)}")
            return [{"action": "Review meeting recording for additional context", "priority": "medium"}]
    
    def _create_executive_summary_prompt(self, analysis_data: Dict) -> str:
        """Create prompt for executive summary generation"""
        return f"""
        You are an AI assistant analyzing a meeting recording that includes both screen content and audio transcript.
        
        Based on the following analysis data, generate a concise executive summary (2-3 paragraphs) that covers:
        1. The main purpose and content of the meeting
        2. Key applications and tools used
        3. Important topics discussed
        4. Overall meeting effectiveness and engagement
        
        Analysis Data:
        - Screen Content Type: {analysis_data['screen_content']['content_type']}
        - Primary Activity: {analysis_data['screen_content']['primary_activity']}
        - Total Frames Analyzed: {analysis_data['screen_content']['total_frames']}
        - Primary Application: {analysis_data['applications']['primary_application']}
        - Important Text Elements: {analysis_data['text_content']['important_text'][:5]}
        - Transcript Summary: {analysis_data['transcript']['summary'][:200]}...
        
        Generate a professional, business-focused executive summary that would be suitable for stakeholders.
        """
    
    def _create_detailed_summary_prompt(self, analysis_data: Dict) -> str:
        """Create prompt for detailed summary generation"""
        return f"""
        You are an AI assistant providing a detailed technical analysis of a meeting recording.
        
        Generate a comprehensive detailed summary (4-6 paragraphs) that includes:
        1. Technical analysis of screen content and applications used
        2. Content patterns and user behavior analysis
        3. Integration of visual and audio content
        4. Specific details about tools, documents, and applications
        5. Meeting flow and engagement patterns
        
        Analysis Data:
        - Screen Content: {json.dumps(analysis_data['screen_content'], indent=2)}
        - Text Analysis: {json.dumps(analysis_data['text_content'], indent=2)}
        - Application Usage: {json.dumps(analysis_data['applications'], indent=2)}
        - Content Patterns: {json.dumps(analysis_data['patterns'], indent=2)}
        - Transcript Data: {json.dumps(analysis_data['transcript'], indent=2)}
        
        Provide a detailed, technical summary that would be useful for meeting participants and technical teams.
        """
    
    def _create_key_insights_prompt(self, analysis_data: Dict) -> str:
        """Create prompt for key insights generation"""
        return f"""
        You are an AI assistant extracting key insights from a meeting recording analysis.
        
        Based on the following data, generate 5-7 key insights about the meeting:
        1. Focus on actionable insights
        2. Identify patterns and trends
        3. Highlight important content and applications
        4. Note engagement and effectiveness indicators
        
        Analysis Data:
        {json.dumps(analysis_data, indent=2)}
        
        Return the insights as a numbered list, with each insight being 1-2 sentences long.
        """
    
    def _create_action_items_prompt(self, analysis_data: Dict) -> str:
        """Create prompt for action items generation"""
        return f"""
        You are an AI assistant generating actionable items from a meeting recording analysis.
        
        Based on the following data, generate 3-5 specific action items with priorities:
        1. Focus on follow-up actions needed
        2. Identify areas requiring attention
        3. Suggest improvements for future meetings
        
        Analysis Data:
        {json.dumps(analysis_data, indent=2)}
        
        Return the action items in JSON format:
        [
            {{"action": "description of action", "priority": "high/medium/low", "assignee": "suggested assignee"}},
            ...
        ]
        """
    
    async def _call_bedrock_model(self, prompt: str) -> str:
        """Call Bedrock model with the given prompt"""
        try:
            request_body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 2000,
                "messages": [
                    {
                        "role": "user",
                        "content": prompt
                    }
                ]
            }
            
            response = self.bedrock_client.invoke_model(
                modelId=self.model_id,
                body=json.dumps(request_body)
            )
            
            response_body = json.loads(response['body'].read())
            return response_body['content'][0]['text']
            
        except Exception as e:
            LOGGER.error(f"Error calling Bedrock model: {str(e)}")
            raise
    
    def _parse_insights_response(self, response: str) -> List[str]:
        """Parse insights response into a list"""
        try:
            # Split by numbered items or bullet points
            lines = response.strip().split('\n')
            insights = []
            
            for line in lines:
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                    # Remove numbering/bullets and clean up
                    insight = line.lstrip('0123456789.-• ').strip()
                    if insight:
                        insights.append(insight)
            
            return insights if insights else [response.strip()]
            
        except Exception as e:
            LOGGER.error(f"Error parsing insights response: {str(e)}")
            return [response.strip()]
    
    def _parse_action_items_response(self, response: str) -> List[Dict]:
        """Parse action items response into structured format"""
        try:
            # Try to parse as JSON first
            if response.strip().startswith('['):
                return json.loads(response)
            
            # Fallback parsing for non-JSON responses
            lines = response.strip().split('\n')
            action_items = []
            
            for line in lines:
                line = line.strip()
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                    action = line.lstrip('0123456789.-• ').strip()
                    if action:
                        action_items.append({
                            "action": action,
                            "priority": "medium",
                            "assignee": "TBD"
                        })
            
            return action_items if action_items else [{"action": response.strip(), "priority": "medium", "assignee": "TBD"}]
            
        except Exception as e:
            LOGGER.error(f"Error parsing action items response: {str(e)}")
            return [{"action": response.strip(), "priority": "medium", "assignee": "TBD"}] 