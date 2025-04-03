import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import './Navbar.css';
import sharedConfig from './shared_config/case_config.json';

const Navbar = ({ isVisible, onToggle }) => {

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
        <pre>{sharedConfig.caso_sebastian}</pre>
      </div>
    </>
  );
};

export default Navbar;