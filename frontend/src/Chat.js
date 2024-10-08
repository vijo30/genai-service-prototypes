import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import io from 'socket.io-client';
import './Chat.css';
import { ErrorBoundary, useErrorBoundary } from 'react-error-boundary';

const socket = io('http://localhost:5000');

// Componente de fallback para el ErrorBoundary
const ErrorFallback = ({ error, resetErrorBoundary }) => (
  <div role="alert">
    <p>Something went wrong:</p>
    <pre>{error.message}</pre>
    <button onClick={resetErrorBoundary}>Try again</button>
  </div>
);

const Chat = () => {
  const { roomId } = useParams();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [userName, setUserName] = useState('');
  const { showBoundary } = useErrorBoundary(); // Se usa para mostrar el error

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await fetch(`http://localhost:5000/api/chat/${roomId}`);
        if (!response.ok) {
          throw new Error('Failed to fetch chat data');
        }
        const data = await response.json();
        setUserName(data.user_name);
        setMessages(data.messages);
      } catch (error) {
        showBoundary(error); // Muestra el error al ErrorBoundary
      }
    };
  
    fetchData();
  
    socket.emit('join', { room_id: roomId });
  
    const handleMessageReceive = (data) => {
      setMessages((prevMessages) => [...prevMessages, data]);
    };
  
    socket.on('receive_message', handleMessageReceive);
  
    // Limpiar la suscripción al desmontar el componente
    return () => {
      socket.off('receive_message', handleMessageReceive);
    };
  }, [roomId, showBoundary]);
  

  const handleSend = (e) => {
    e.preventDefault();
    if (!input) return;

    socket.emit('send_message', { room_id: roomId, user_name: userName, message: input });
    setInput('');
  };

  return (
    <div className="chat-container">
      <h2>Sala: {roomId}</h2>
      <div className="chat-box">
        {messages.map((msg, index) => (
          <div key={index} className={msg.user_name === 'Bot' ? 'bot-message' : 'user-message'}>
            <div className="message-author">{msg.user_name}</div>
            <div className="message-content">{msg.message}</div>
          </div>
        ))}
      </div>
      <form onSubmit={handleSend} className="chat-input">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Escribe tu mensaje..."
        />
        <button type="submit">Enviar</button>
      </form>
    </div>
  );
};

const ChatWithErrorBoundary = () => {
  return (
    <ErrorBoundary FallbackComponent={ErrorFallback}>
      <Chat />
    </ErrorBoundary>
  );
};

export default ChatWithErrorBoundary;
