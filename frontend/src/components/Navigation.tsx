import { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import './Navigation.css';

interface User {
  id: number;
  name: string;
  first_name: string;
  email: string;
}

export default function Navigation() {
  const [user, setUser] = useState<User | null>(null);

  useEffect(() => {
    const savedUser = localStorage.getItem('user');
    if (savedUser) {
      try {
        setUser(JSON.parse(savedUser));
      } catch {
        localStorage.removeItem('user');
      }
    }
  }, []);

  const handleLogout = () => {
    localStorage.removeItem('user');
    setUser(null);
    window.location.href = '/';
  };

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <Link to="/" className="navbar-brand">
          <span className="brand-crest" aria-hidden="true">Y</span>
          <span className="brand-text">Campus Customs</span>
        </Link>
        <ul className="nav-menu">
          <li className="nav-item">
            <Link to="/" className="nav-link">Home</Link>
          </li>
          <li className="nav-item">
            <Link to="/products" className="nav-link">Products</Link>
          </li>
          <li className="nav-item">
            <Link to="/about" className="nav-link">About Us</Link>
          </li>
          {user ? (
            <>
              <li className="nav-item user-info">
                <span className="welcome-text">Hi, {user.first_name}</span>
              </li>
              <li className="nav-item">
                <button className="nav-link logout-btn" onClick={handleLogout}>Log out</button>
              </li>
            </>
          ) : (
            <>
              <li className="nav-item">
                <Link to="/login" className="nav-link">Log in</Link>
              </li>
              <li className="nav-item">
                <Link to="/create-account" className="nav-link signup">Create account</Link>
              </li>
            </>
          )}
        </ul>
      </div>
    </nav>
  );
}
