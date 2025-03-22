// App.js
import React, { useState } from 'react';
import { BrowserRouter as Router, Route, Routes, Link } from 'react-router-dom';
import Home from './Home';   // Página inicial
import Chat from './Chat';   // Página del chat
import Navbar from './Navbar';

const App = () => {

  const [isNavbarVisible, setIsNavbarVisible] = useState(false);

  const toggleNavbar = () => {
    setIsNavbarVisible(!isNavbarVisible);
  };

  return (
    <Router>
      <div className='app-root'>
        {/* Navbar */}
        <Navbar isVisible={isNavbarVisible} onToggle={toggleNavbar} />

        {/* Definición de las rutas */}
        <div className="main-content">
          <Routes>
            <Route path="/" element={<Home />} />
            <Route path="/chat/:roomId" element={<Chat />} />
            <Route path="*" element={<h1>404 - Página no encontrada</h1>} />

          </Routes>
        </div>
       
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

