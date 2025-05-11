import React, { useState, useEffect, useRef } from 'react';
import { useParams } from 'react-router-dom';
import io from 'socket.io-client';
import './Chat.css';
import { ErrorBoundary, useErrorBoundary } from 'react-error-boundary';

const apiUrl = process.env.REACT_APP_API_BASE_URL;


const url = `https://${apiUrl}/api`

const socket = io(url,
  {
    withCredentials: true,
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
  const [username, setUsername] = useState('');
  const { showBoundary } = useErrorBoundary(); // Se usa para mostrar el error
  const [isUsernameSet, setIsUsernameSet] = useState(false);

  const chatRef = useRef(null); // Referencia al contenedor de mensajes
  const messagesEndRef = useRef(null); // Referencia al final del chat
  const isUserScrolling = useRef(false); // Para rastrear si el usuario está haciendo scroll manualmente

  // Función para desplazarse al final del chat
  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  // Listener para detectar scroll manual
  const handleScroll = () => {
    if (chatRef.current) {
      const { scrollTop, scrollHeight, clientHeight } = chatRef.current;
      // Si el usuario está cerca del final, considera que quiere el scroll automático
      isUserScrolling.current = !(scrollTop + clientHeight >= scrollHeight - 50);
    }
  };

  // Efecto: Escuchar eventos de scroll
  useEffect(() => {
    const chatContainer = chatRef.current;
    if (chatContainer) {
      chatContainer.addEventListener('scroll', handleScroll);
    }
    return () => {
      if (chatContainer) {
        chatContainer.removeEventListener('scroll', handleScroll);
      }
    };
  }, []);

  // Efecto: Desplazarse al final cuando llegan mensajes nuevos (si no hay scroll manual)
  useEffect(() => {
    console.log('Estado de mensajes actualizado:', messages);
    if (!isUserScrolling.current) {
      scrollToBottom();
    }
  }, [messages]);

  useEffect(() => {
    const savedUsername = localStorage.getItem('username');
    if (savedUsername) {
      setUsername(savedUsername);
      setIsUsernameSet(true);
    }
  }, []);

  const getMessages = async () => {
    try {
      const response = await fetch(`${url}/chat/${roomId}`);
      if (!response.ok) {
        throw new Error('Failed to fetch chat data');
      }
      const data = await response.json();
      console.log('Mensajes recibidos de la API:', data.messages);
      setMessages(data.messages);
    } catch (error) {
      console.error('Error fetching messages:', error);
      showBoundary(error); // Muestra el error al ErrorBoundary
    }
  };


  useEffect( () => {
    console.log('Componente Chat montado o roomId cambiado:', roomId, 'isUsernameSet:', isUsernameSet);

    getMessages();

    if (isUsernameSet) {
      socket.emit('join', { room_id: roomId });
      console.log('Emitiendo "join" para la sala:', roomId);

      socket.on('connect', () => {
        console.log('Socket.IO connected');
        socket.emit('join', { room_id: roomId }); // Emit join again on reconnect
      });

      socket.on('disconnect', () => {
        console.log('Socket.IO disconnected');
      });

      const handleMessageReceive = (data) => {
        console.log('Mensaje recibido por Socket:', data);
        setMessages((prevMessages) => [...prevMessages, data]);
      };

      socket.on('receive_message', handleMessageReceive);

      return () => {
        socket.off('receive_message', handleMessageReceive);
        console.log('Desmontando el listener de "receive_message"');
      };
    }
  }, [roomId, isUsernameSet]);

  const handleSend = (e) => {
    e.preventDefault();
    if (!input) return;

    socket.emit('send_message', { room_id: roomId, user_name: username, message: input });
    setInput('');
  };

  const handleSetUsername = async (e) => {
    e.preventDefault();
    if (username.trim()) {
      try {
        // Send username to the backend
        const response = await fetch(`${url}/set_username`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({ username }),
          credentials: 'include', // Ensures session cookie is sent
        });

        if (!response.ok) {
          throw new Error('Failed to set username on the server.');
        }

        const data = await response.json();

        // Update frontend state with the confirmed username
        if (data.message === 'Username set successfully') {
          setIsUsernameSet(true);
          setUsername(data.username); // Use the username returned by the backend
          localStorage.setItem('username', data.username); // Sync with localStorage
        }
      } catch (error) {
        console.error('Error setting username:', error);
      }
    }
  };

if (!isUsernameSet) {
  return (
    <div className="username-container">
      <form onSubmit={handleSetUsername}>
        <label htmlFor="username">Enter your username:</label>
        <input
          required
          type="text"
          id="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="Elige un nombre de usuario..."
        />
        <button type="submit">Unirse al Chat</button>
      </form>
    </div>
  );
}

  const handleExportChat = () => {
    if (messages.length === 0) {
      alert("No messages to export!");
      return;
    }

    const csvHeader = "Username,Message,Timestamp\n";
    const csvRows = messages.map(msg => {
      const userName = msg.user_name.replace(/"/g, '""');
      const message = msg.message.replace(/"/g, '""');
      const timestamp = new Date(msg.timestamp).toISOString();
      return `"${userName}","${message}","${timestamp}"`;
    });

    const csvContent = csvHeader + csvRows.join("\n");
    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `chat-${roomId}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="chat-container">
      <div className="chat-header">
        <h2>Sala: {roomId}</h2>
        <button onClick={handleExportChat}>Exportar Chat</button>


      </div>


      <div className="chat-box" ref={chatRef} onScroll={handleScroll}>

      <h2>Chat</h2>
        {messages.map((msg, index) => {
          const bgColor = getUserColor(msg.user_name);
          const textColor = getTextColorBasedOnBackground(bgColor);
          const formattedTime = new Date(msg.timestamp).toLocaleString();
          return (
            <div key={index} className="user-message" style={{ backgroundColor: bgColor }}>
              <div className="message-author" style={{ color: textColor }}>
                {msg.user_name} <span className="message-time">{formattedTime}</span>
              </div>
              <div className="message-content"style={{ color: textColor }}>
                {msg.message}
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
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