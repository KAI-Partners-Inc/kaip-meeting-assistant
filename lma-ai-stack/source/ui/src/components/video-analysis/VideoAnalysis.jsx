// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React, { useState, useEffect } from 'react';
import {
  Box,
  Button,
  Container,
  Header,
  SpaceBetween,
  Tabs,
  TextContent,
  StatusIndicator,
  Alert,
  Link,
  ExpandableSection,
  ColumnLayout,
  Cards,
  Card,
} from '@awsui/components-react';
import { Logger } from 'aws-amplify';

import useAppContext from '../../contexts/app';

const logger = new Logger('VideoAnalysis');

const VideoAnalysis = ({ callId, videoAnalysisData }) => {
  const { currentCredentials } = useAppContext();
  const [activeTab, setActiveTab] = useState('summary');
  const [expandedSections, setExpandedSections] = useState(new Set(['executive']));

  const videoAnalysis = videoAnalysisData ? JSON.parse(videoAnalysisData) : null;

  if (!videoAnalysis) {
    return (
      <Container
        header={
          <Header variant="h3" description="No video analysis available for this meeting">
            Video Analysis
          </Header>
        }
      >
        <Alert type="info">
          This meeting does not include video analysis. To enable video analysis, use the Screen Recording feature when
          starting your meeting.
        </Alert>
      </Container>
    );
  }

  const handleTabChange = ({ detail }) => {
    setActiveTab(detail.activeTabId);
  };

  const toggleSection = (sectionId) => {
    const newExpanded = new Set(expandedSections);
    if (newExpanded.has(sectionId)) {
      newExpanded.delete(sectionId);
    } else {
      newExpanded.add(sectionId);
    }
    setExpandedSections(newExpanded);
  };

  const getPriorityColor = (priority) => {
    switch (priority?.toLowerCase()) {
      case 'high':
        return 'error';
      case 'medium':
        return 'warning';
      case 'low':
        return 'success';
      default:
        return 'pending';
    }
  };

  const tabs = [
    {
      id: 'summary',
      label: 'Summary',
      content: (
        <SpaceBetween size="l">
          <ExpandableSection
            variant="container"
            header="Executive Summary"
            expanded={expandedSections.has('executive')}
            onChange={() => toggleSection('executive')}
          >
            <TextContent>
              <p>{videoAnalysis.video_summary?.executive_summary || 'No executive summary available.'}</p>
            </TextContent>
          </ExpandableSection>

          <ExpandableSection
            variant="container"
            header="Detailed Analysis"
            expanded={expandedSections.has('detailed')}
            onChange={() => toggleSection('detailed')}
          >
            <TextContent>
              <p>{videoAnalysis.video_summary?.detailed_summary || 'No detailed analysis available.'}</p>
            </TextContent>
          </ExpandableSection>

          <ExpandableSection
            variant="container"
            header="Key Insights"
            expanded={expandedSections.has('insights')}
            onChange={() => toggleSection('insights')}
          >
            <SpaceBetween size="s">
              {videoAnalysis.video_summary?.key_insights?.map((insight, index) => (
                <Box key={index} padding="s" backgroundColor="background-container">
                  <TextContent>
                    <p>
                      <strong>{index + 1}.</strong> {insight}
                    </p>
                  </TextContent>
                </Box>
              )) || (
                <TextContent>
                  <p>No key insights available.</p>
                </TextContent>
              )}
            </SpaceBetween>
          </ExpandableSection>

          <ExpandableSection
            variant="container"
            header="Action Items"
            expanded={expandedSections.has('actions')}
            onChange={() => toggleSection('actions')}
          >
            <Cards
              cardDefinition={{
                header: (item) => (
                  <SpaceBetween direction="horizontal" size="xs">
                    <span>{item.action}</span>
                    <StatusIndicator type={getPriorityColor(item.priority)}>{item.priority}</StatusIndicator>
                  </SpaceBetween>
                ),
                sections: [
                  {
                    id: 'assignee',
                    header: 'Assignee',
                    content: (item) => item.assignee || 'TBD',
                  },
                ],
              }}
              cardsPerRow={[{ cards: 1 }, { minWidth: 500, cards: 2 }]}
              items={videoAnalysis.video_summary?.action_items || []}
              loadingText="Loading action items..."
              empty={
                <Box textAlign="center" color="text-body-secondary">
                  <TextContent>
                    <p>No action items available.</p>
                  </TextContent>
                </Box>
              }
            />
          </ExpandableSection>
        </SpaceBetween>
      ),
    },
    {
      id: 'content',
      label: 'Content Analysis',
      content: (
        <SpaceBetween size="l">
          <ExpandableSection
            variant="container"
            header="Screen Content Overview"
            expanded={expandedSections.has('content-overview')}
            onChange={() => toggleSection('content-overview')}
          >
            <ColumnLayout columns={3}>
              <Box>
                <TextContent>
                  <h4>Content Type</h4>
                  <p>{videoAnalysis.video_summary?.analysis_metadata?.screen_content_type || 'Unknown'}</p>
                </TextContent>
              </Box>
              <Box>
                <TextContent>
                  <h4>Primary Activity</h4>
                  <p>{videoAnalysis.video_summary?.analysis_metadata?.primary_activity || 'Unknown'}</p>
                </TextContent>
              </Box>
              <Box>
                <TextContent>
                  <h4>Frames Analyzed</h4>
                  <p>{videoAnalysis.video_summary?.analysis_metadata?.total_frames_analyzed || 0}</p>
                </TextContent>
              </Box>
            </ColumnLayout>
          </ExpandableSection>

          <ExpandableSection
            variant="container"
            header="Text Content Analysis"
            expanded={expandedSections.has('text-analysis')}
            onChange={() => toggleSection('text-analysis')}
          >
            <SpaceBetween size="s">
              <Box>
                <TextContent>
                  <h4>Text Statistics</h4>
                  <p>Total text blocks: {videoAnalysis.screen_analysis?.text_analysis?.total_text_blocks || 0}</p>
                  <p>Unique text elements: {videoAnalysis.screen_analysis?.text_analysis?.unique_text_count || 0}</p>
                </TextContent>
              </Box>

              {videoAnalysis.screen_analysis?.text_analysis?.important_text?.length > 0 && (
                <Box>
                  <TextContent>
                    <h4>Important Text Elements</h4>
                    <ul>
                      {videoAnalysis.screen_analysis.text_analysis.important_text.slice(0, 5).map((text, index) => (
                        <li key={index}>{text}</li>
                      ))}
                    </ul>
                  </TextContent>
                </Box>
              )}
            </SpaceBetween>
          </ExpandableSection>

          <ExpandableSection
            variant="container"
            header="Application Usage"
            expanded={expandedSections.has('applications')}
            onChange={() => toggleSection('applications')}
          >
            <SpaceBetween size="s">
              <Box>
                <TextContent>
                  <h4>Primary Application</h4>
                  <p>{videoAnalysis.screen_analysis?.object_analysis?.primary_application || 'Unknown'}</p>
                </TextContent>
              </Box>

              {videoAnalysis.screen_analysis?.object_analysis?.application_usage && (
                <Box>
                  <TextContent>
                    <h4>Application Usage Breakdown</h4>
                    <ul>
                      {Object.entries(videoAnalysis.screen_analysis.object_analysis.application_usage)
                        .sort(([, a], [, b]) => b - a)
                        .map(([app, count]) => (
                          <li key={app}>
                            {app}: {count} detections
                          </li>
                        ))}
                    </ul>
                  </TextContent>
                </Box>
              )}
            </SpaceBetween>
          </ExpandableSection>
        </SpaceBetween>
      ),
    },
    {
      id: 'patterns',
      label: 'Patterns & Timeline',
      content: (
        <SpaceBetween size="l">
          <ExpandableSection
            variant="container"
            header="Content Patterns"
            expanded={expandedSections.has('patterns')}
            onChange={() => toggleSection('patterns')}
          >
            <ColumnLayout columns={3}>
              <Box>
                <TextContent>
                  <h4>Text-Heavy Frames</h4>
                  <p>
                    {videoAnalysis.screen_analysis?.pattern_analysis?.text_heavy_frames?.percentage?.toFixed(1) || 0}%
                  </p>
                </TextContent>
              </Box>
              <Box>
                <TextContent>
                  <h4>Image-Heavy Frames</h4>
                  <p>
                    {videoAnalysis.screen_analysis?.pattern_analysis?.image_heavy_frames?.percentage?.toFixed(1) || 0}%
                  </p>
                </TextContent>
              </Box>
              <Box>
                <TextContent>
                  <h4>Mixed Content Frames</h4>
                  <p>
                    {videoAnalysis.screen_analysis?.pattern_analysis?.mixed_content_frames?.percentage?.toFixed(1) || 0}
                    %
                  </p>
                </TextContent>
              </Box>
            </ColumnLayout>
          </ExpandableSection>

          <ExpandableSection
            variant="container"
            header="Activity Timeline"
            expanded={expandedSections.has('timeline')}
            onChange={() => toggleSection('timeline')}
          >
            <SpaceBetween size="s">
              {videoAnalysis.screen_analysis?.timeline_analysis?.activity_clusters?.map((cluster, index) => (
                <Box key={index} padding="s" backgroundColor="background-container">
                  <TextContent>
                    <h4>Activity Cluster {index + 1}</h4>
                    <p>Duration: {Math.round(cluster.end_time - cluster.start_time)}s</p>
                    <p>Activities: {cluster.activities.length}</p>
                    {cluster.activities.slice(0, 3).map((activity, actIndex) => (
                      <p key={actIndex} style={{ fontSize: '0.9em', color: '#666' }}>
                        {Math.round(activity.timestamp)}s: {activity.text_count} text, {activity.object_count} objects
                      </p>
                    ))}
                  </TextContent>
                </Box>
              )) || (
                <TextContent>
                  <p>No activity timeline available.</p>
                </TextContent>
              )}
            </SpaceBetween>
          </ExpandableSection>
        </SpaceBetween>
      ),
    },
  ];

  return (
    <Container
      header={
        <Header
          variant="h3"
          description="Analysis of screen content and visual elements from the meeting"
          actions={
            <Button variant="normal" href={`#/screen-recording`} iconAlign="right" iconName="external">
              Record New Meeting
            </Button>
          }
        >
          Video Analysis
        </Header>
      }
    >
      <Tabs tabs={tabs} activeTabId={activeTab} onChange={handleTabChange} ariaLabel="Video analysis tabs" />
    </Container>
  );
};

export default VideoAnalysis;
