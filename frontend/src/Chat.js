import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import io from 'socket.io-client';
import './Chat.css';
import { ErrorBoundary, useErrorBoundary } from 'react-error-boundary';

const socket = io('http://localhost:5000',
    {
        reconnection: true,
        reconnectionAttempts: 5,
        reconnectionDelay: 1000,
    }
);

// Función para generar un color hexadecimal basado en el nombre del usuario
const getUserColor = (userName) => {
  let hash = 0;
  for (let i = 0; i < userName.length; i++) {
    hash = userName.charCodeAt(i) + ((hash << 5) - hash);
  }
  let color = "#";
  for (let i = 0; i < 3; i++) {
    const value = (hash >> (i * 8)) & 0xff;
    color += ("00" + value.toString(16)).slice(-2);
  }
  return color;
};


// Función para determinar si el texto debe ser claro u oscuro basado en el fondo
const getTextColorBasedOnBackground = (bgColor) => {
  // Elimina el símbolo "#" si está presente
  const color = bgColor.substring(1);
  const rgb = parseInt(color, 16); // Convierte de hexadecimal a decimal
  const r = (rgb >> 16) & 0xff;
  const g = (rgb >> 8) & 0xff;
  const b = (rgb >> 0) & 0xff;

  // Calcula el brillo del color (luminancia)
  const brightness = 0.299 * r + 0.587 * g + 0.114 * b;
  return brightness > 150 ? 'black' : 'white'; // Texto oscuro si el fondo es claro, y viceversa
};


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
      console.log("Mensaje recibido:", data);  // Añade esta línea para verificar la recepción
      setMessages((prevMessages) => [...prevMessages, data]);
    };
  
    socket.on('receive_message', handleMessageReceive);
  
    // Limpiar la suscripción al desmontar el componente
    return () => {
      socket.off('receive_message', handleMessageReceive);
    };
  }, [roomId, showBoundary]);

  useEffect(() => {
    const chatBox = document.querySelector('.chat-box');
    chatBox.scrollTop = chatBox.scrollHeight;
  }, [messages]);
  

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
        {messages.map((msg, index) => {
          const bgColor = getUserColor(msg.user_name);
          const textColor = getTextColorBasedOnBackground(bgColor);
          return (
            <div
              key={index}
              className="user-message"
              style={{ backgroundColor: bgColor }}
            >
              <div
                className="message-author"
                style={{ color: textColor }}
              >
                {msg.user_name}
              </div>
              <div
                className="message-content"
                style={{ color: textColor }}
              >
                {msg.message}
              </div>
            </div>
          );
        })}
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
