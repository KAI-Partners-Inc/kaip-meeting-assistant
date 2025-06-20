// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React from 'react';
import { Container, Header, Link, SpaceBetween } from '@awsui/components-react';

const ToolsPanel = () => (
  <Container
    header={
      <Header
        variant="h4"
        info={
          <Link variant="info" target="_blank" href="https://amazon.com/live-meeting-assistant">
            Info
          </Link>
        }
      >
        Screen Recording Help
      </Header>
    }
  >
    <SpaceBetween size="l">
      <div>
        <h4>How to use Screen Recording</h4>
        <p>
          The Screen Recording feature allows you to capture both your screen content and audio during meetings.
          This enables the meeting assistant to provide comprehensive analysis including:
        </p>
        <ul>
          <li>Visual content analysis (presentations, documents, applications)</li>
          <li>Text extraction from screen content</li>
          <li>Application usage patterns</li>
          <li>Combined audio and visual insights</li>
        </ul>
      </div>
      
      <div>
        <h4>Best Practices</h4>
        <ul>
          <li>Ensure good lighting and clear screen content</li>
          <li>Close unnecessary applications to reduce clutter</li>
          <li>Use high-quality audio equipment for better transcription</li>
          <li>Test your setup before important meetings</li>
        </ul>
      </div>
      
      <div>
        <h4>Privacy & Security</h4>
        <p>
          Your recordings are processed securely and stored according to your organization's policies.
          Always obtain consent before recording meetings with participants.
        </p>
      </div>
    </SpaceBetween>
  </Container>
);

export default ToolsPanel; 