import React, { useState, useEffect } from 'react';
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
        setMessages(data.messages);
      } catch (error) {
        showBoundary(error); // Muestra el error al ErrorBoundary
    }
  };


  

  useEffect( () => {
    
    getMessages();
    
    if (isUsernameSet) {
        socket.emit('join', { room_id: roomId });
  
        const handleMessageReceive = (data) => {
          setMessages((prevMessages) => [...prevMessages, data]);
        };
  
        socket.on('receive_message', handleMessageReceive);
        
  
        return () => {
          socket.off('receive_message', handleMessageReceive);
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
        <div className='chat-case'>

            <h2>Caso Actual: CASO “SEBASTIÁN”</h2>
            <p>Creo que me fue bien en la prueba de matemáticas. Eso sí, en la parte de álgebra lineal tan bien no me fue, pero creo que salvé con las otras preguntas. 
                Justo estaba por salir a tomarme unas cervezas a la casa de una amiga, cuando me llamó Sebastián, mi mejor amigo, para decirme que estaba complicado con el examen de contabilidad; que había estudiado harto pero que creía que no iba a lograr la nota para aprobar el curso. Lo entiendo, el curso es bastante difícil. Es cierto que yo me eximí, pero de que lo pasé mal durante el semestre con los ejercicios y las solemnes, lo pasé mal. 
                Durante la conversación, Sebastián se notaba muy nervioso y angustiado; tan angustiado que yo mismo comencé a angustiarme. No es para menos, si reprueba el curso se atrasa un año y no tendrá dinero para pagar el cuota de la carrera (Sebastián estudia con gratuidad completa). Muchas veces hemos discutido esto con los papás de Sebastián cuando estamos almorzando o cenando en su casa. Ellos son una familia esforzada: ambos papás trabajan para poder sacar adelante a la Francisca y a Sebastián. No entienden por qué han puesto esta regla de financiar sólo los 5 años que dura la carrera (de acuerdo al plan de estudios), cuando todos sabemos que la mayoría de los estudiantes no logra terminarla en ese tiempo. 
                A pesar de todo el esfuerzo que realizan, los papás de Sebastián, Alberto y Alejandra, son muy generosos y acogedores. Me recibieron durante un par de meses en plena pandemia, cuando tenía problemas con mi propia familia, sin poner complicaciones cuando Sebastián preguntó si acaso podía quedarme con ellos un tiempo. En ese tiempo me di cuenta de que Alberto, Alejandra, Sebastián y Francisca son una familia trabajadora y honrada, que no quiere nada regalado.   
                Durante mi estadía con la familia de Sebastián, estudiamos juntos en múltiples ocasiones. Con el tiempo, él me ayudó en los ramos que más me costaban, y viceversa. Pero había un ramo con el cual Sebastián batallaba incesantemente: contabilidad. Volví a mi casa, arreglé las cosas con mi familia y, en unos meses, la pandemia comenzó a menguar: había menos restricciones para moverse y era más fácil salir de la casa, pero, por seguridad, los ramos los seguíamos teniendo online. Por eso no me extrañó que, visiblemente incómodo, Sebastián me pidiera que lo ayudara a contestar el examen de contabilidad. Me imagino la angustia y vergüenza que debe haber tenido para pedírmelo. Ahí entendí por qué me había llamado por teléfono y no había venido a la casa para hablar un tema tan importante.
                Le pregunté a Sebastián por qué tenía tanta vergüenza. Me dijo que, al hablar con su papá, éste le dijo que no podía darse el lujo de reprobar un ramo, que tenía que pasarlo sí o sí, estudiando día y noche, o de otro modo la familia se vería en serios problemas financieros. Pero le dejó muy claro, también que: “en esta familia nos ganamos las cosas, nadie nos regaló nada y no hacemos las cosas a medias o tomando atajos; trabaja duro y verás los resultados”. Y Alejandra, su mamá, le sugirió que hablara conmigo, para que lo ayudara. Después de todo, Sebastián me había ayudado “en las malas”, ¿por qué no iba a hacer lo mismo por él? Sebastián me dijo que estaba muy confundido, sabe que lo que pide me compromete, pero no ve mucha salida al problema. 
                Ni a Sebastián ni a mí nos gusta esto de la copia. De hecho, muchas veces hemos peleado con algunos compañeros porque nos hemos sentido perjudicados por su comportamiento: “ustedes sacan mejor nota que nosotros que no copiamos”, es lo que siempre les decimos. Incluso lo hemos hablado con varios profesores, porque nos molesta mucho que las conductas deshonestas finalmente sean premiadas. Parece que nos gusta vivir en un país en el que “hacerse el vivo” es una cualidad positiva. Los docentes siempre nos han dicho que, al final, por mucho que nuestros compañeros saquen mejores notas, serán siempre peores profesionales que nosotros: primero porque saldremos de la carrera literalmente sabiendo más (y, por consiguiente, mejor preparados); en segundo lugar, porque la honestidad y el trabajo esforzado son virtudes tremendamente deseables en el ámbito laboral. De todas formas, siempre quedamos con la sensación desagradable de que los compañeros que hacen trampa nos pasan a llevar. 
                En fin, me complica mucho la situación de Sebastián y francamente estoy confundido. Y yo que estaba tan contento por el examen de matemáticas. Ahora estoy metido en un lío. Este periodo de exámenes no lo olvidaré fácilmente. Realmente no sé qué hacer. Me siento muy angustiado.” 
            </p>
            
        </div>

        
        <div className="chat-box">
        
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
