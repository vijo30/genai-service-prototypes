// App.js
import React from 'react';
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';
import Home from './Home';   // Página inicial
import Chat from './Chat';   // Página del chat

const App = () => {
  return (
    <Router>
      <div>
        {/* Barra de navegación (opcional) */}
        <nav>
          <ul>
            <li>
              <Link to="/">Home</Link>
            </li>
          </ul>
        </nav>

        {/* Definición de las rutas */}
        <Routes>
          <Route path="/" element={<Home />} />
          <Route path="/chat/:roomId" element={<Chat />} />
          <Route path="*" element={<h1>404 - Página no encontrada</h1>} />

        </Routes>
      </div>
    </Router>
  );
};

export const useCallbackWithErrorHandling = (callback) => {
  const [state, setState] = useState();

  return (...args) => {
    try {
      callback(...args);
    } catch(e) {
      setState(() => {
        throw e;
      });
    }
  }
}


export default App;

