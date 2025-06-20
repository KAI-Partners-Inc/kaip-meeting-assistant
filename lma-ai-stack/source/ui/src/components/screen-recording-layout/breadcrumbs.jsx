// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React from 'react';
import { BreadcrumbGroup } from '@awsui/components-react';

const Breadcrumbs = () => (
  <BreadcrumbGroup
    items={[
      {
        text: 'Meeting Analytics',
        href: '#/',
      },
      {
        text: 'Screen Recording',
        href: '#/screen-recording',
      },
    ]}
  />
);

export default Breadcrumbs; 