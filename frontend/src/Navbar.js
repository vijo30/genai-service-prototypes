import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import './Navbar.css';

const Navbar = ({ isVisible, onToggle }) => {
  const [text, setText] = useState('Cargando...');

  useEffect(() => {
    fetch('/caso-sebastian.txt')
      .then((response) => response.text())
      .then((data) => setText(data))
      .catch((error) => {
        console.error('Error al cargar el archivo de texto:', error);
        setText('Error al cargar el contenido.');
      });
  }, []);

  return (
    <>
      {/* Botón para mostrar/ocultar la navbar (siempre visible) */}
      <button className="navbar-toggle" onClick={onToggle}>
        {isVisible ? '←' : '→'} {/* Usar Unicode o íconos de FontAwesome */}
      </button>

      {/* Contenido de la navbar */}
      <div className={`navbar ${isVisible ? 'visible' : ''}`}>
        {/* Enlace a Home */}
        <Link to="/" className="navbar-home-link">
          Inicio
        </Link>

        {/* Texto del caso Sebastián */}
        <pre>{text}</pre>
      </div>
    </>
  );
};

export default Navbar;