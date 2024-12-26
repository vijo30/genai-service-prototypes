import React, { createContext, useState } from 'react';
import './Home.css';
import { Link, useNavigate } from 'react-router-dom';

const apiUrl = process.env.REACT_APP_API_BASE_URL;

const url = `https://${apiUrl}`

const Home = () => {
  const [roomId, setRoomId] = useState('');
  const navigate = useNavigate();
  

  const handleCreateRoom = async () => {
    const response = await fetch(`${url}/api/create_room`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
    });
    const data = await response.json();
    setRoomId(data.room_id);
    
    navigate(`/chat/${data.room_id}`);
  };



  return (
    
    <div className="home-container">
      <div className="room-selection">
        <button onClick={handleCreateRoom}>Crear Nueva Sala</button>
          
        <input
          type="text"
          placeholder="Ingresa Room ID"
          value={roomId}
          onChange={(e) => setRoomId(e.target.value)}
        />
        <Link to={`/chat/${roomId}`}>
          <button type="button">Unirse a Sala</button>
        </Link>

      </div>
    </div>
  );
};

export default Home;

