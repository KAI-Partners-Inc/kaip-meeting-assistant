// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0
import React from 'react';
import { Route, Switch } from 'react-router-dom';

import ScreenRecordingLayout from '../components/screen-recording-layout/ScreenRecordingLayout';
import { SCREEN_RECORDING_PATH } from './constants';

const ScreenRecordingRoutes = () => (
  <Switch>
    <Route path={SCREEN_RECORDING_PATH}>
      <ScreenRecordingLayout />
    </Route>
  </Switch>
);

export default ScreenRecordingRoutes;
