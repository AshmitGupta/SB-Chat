// src/ChatWindow.js

import React, { useState, useEffect } from 'react';
import { TextField, Button, List, ListItem, ListItemText, Paper, CircularProgress, Modal, Box } from '@mui/material';
import axios from 'axios';

function ChatWindow() {
  const [input, setInput] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [partInfo, setPartInfo] = useState(null);
  const [modalOpen, setModalOpen] = useState(false);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMessage = { sender: 'User', text: input };
    setMessages([...messages, userMessage]);
    setInput('');
    setLoading(true);

    try {
      const response = await axios.post('http://localhost:8000/query', { query: input });
      
      let assistantMessage = {
        sender: 'Assistant',
        html: response.data.answer
      };

      // Extract part-info if present
      let partInfoContent = null;
      const partInfoRegex = /<div id="part-info">(.*?)<\/div>/s;
      const partInfoMatch = assistantMessage.html.match(partInfoRegex);
      if (partInfoMatch) {
        partInfoContent = partInfoMatch[1];
        assistantMessage.html = assistantMessage.html.replace(partInfoRegex, '');
        setPartInfo(partInfoContent);
      }

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (error) {
      console.error('Error:', error);
      const errorMessage = { sender: 'Assistant', text: 'Sorry, an error occurred while processing your request.' };
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  // Event handler for the "Check Part Availability" button
  const handleButtonClick = (e) => {
    if (e.target.id === 'check-part-availability') {
      setModalOpen(true);
    }
  };

  useEffect(() => {
    // Attach click event listener to the "Check Part Availability" button
    const chatList = document.getElementById('chat-list');
    if (chatList) {
      chatList.addEventListener('click', handleButtonClick);
    }

    return () => {
      if (chatList) {
        chatList.removeEventListener('click', handleButtonClick);
      }
    };
  }, [messages]);

  return (
    <Paper elevation={3} style={{ padding: '20px', marginTop: '20px' }}>
      <List id="chat-list" style={{ maxHeight: '400px', overflow: 'auto' }}>
        {messages.map((msg, index) => (
          <ListItem key={index} alignItems="flex-start">
            <ListItemText
              primary={msg.sender}
              secondary={
                msg.html ? (
                  <div dangerouslySetInnerHTML={{ __html: msg.html }} />
                ) : (
                  msg.text
                )
              }
              primaryTypographyProps={{ fontWeight: 'bold' }}
            />
          </ListItem>
        ))}
        {loading && (
          <ListItem>
            <CircularProgress />
          </ListItem>
        )}
      </List>
      <TextField
        fullWidth
        label="Type your message"
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyPress={handleKeyPress}
        multiline
        minRows={1}
        maxRows={4}
        style={{ marginTop: '10px' }}
      />
      <Button
        variant="contained"
        color="primary"
        onClick={handleSend}
        style={{ marginTop: '10px' }}
        disabled={loading}
      >
        Send
      </Button>

      <Modal
        open={modalOpen}
        onClose={() => setModalOpen(false)}
        aria-labelledby="part-info-modal"
        aria-describedby="part-info-description"
      >
        <Box
          sx={{
            position: 'absolute',
            top: '50%',
            left: '50%',
            transform: 'translate(-50%, -50%)',
            width: '80%',
            bgcolor: 'background.paper',
            boxShadow: 24,
            p: 4,
            maxHeight: '80%',
            overflow: 'auto',
          }}
        >
          <h2 id="part-info-modal">Part Information</h2>
          <div dangerouslySetInnerHTML={{ __html: partInfo }} />
          <Button
            variant="contained"
            color="primary"
            onClick={() => setModalOpen(false)}
            style={{ marginTop: '20px' }}
          >
            Close
          </Button>
        </Box>
      </Modal>
    </Paper>
  );
}

export default ChatWindow;
