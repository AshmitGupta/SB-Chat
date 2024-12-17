// src/App.js

import React from 'react';
import ChatWindow from './ChatWindow';
import { Container, Typography } from '@mui/material';

function App() {
  return (
    <Container maxWidth="md">
      <Typography variant="h4" component="h1" align="center" gutterBottom style={{ marginTop: '20px' }}>
        Service Bulletin Chat Assistant
      </Typography>
      <ChatWindow />
    </Container>
  );
}

export default App;
