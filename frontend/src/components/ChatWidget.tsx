import { useState, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import axios from 'axios';
import ProductCard from './ProductCard';
import './ChatWidget.css';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
}

interface SearchProduct {
  product_id: string;
  name: string;
  price: number;
  short_description: string;
  image_file_path: string;
}

interface StoredUser {
  id: number;
  name: string;
  email: string;
}

// Single FastAPI backend serves all endpoints (chat, products, auth, images)
const CHAT_API = 'http://localhost:8000';
const API_BASE = 'http://localhost:8000';

const WELCOME_MESSAGE: Message = {
  id: 'welcome',
  role: 'assistant',
  content: 'Hello! Welcome to Campus Customs. How can I help you today?',
};

function getStoredUser(): StoredUser | null {
  try {
    const raw = localStorage.getItem('user');
    if (!raw) return null;
    const parsed = JSON.parse(raw);
    if (parsed && typeof parsed.id === 'number') {
      return { id: parsed.id, name: parsed.name, email: parsed.email };
    }
    return null;
  } catch {
    return null;
  }
}

export default function ChatWidget() {
  const location = useLocation();

  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<Message[]>([WELCOME_MESSAGE]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [searchProducts, setSearchProducts] = useState<SearchProduct[]>([]);
  const loadedForUserId = useRef<number | 'guest' | 'unset'>('unset');

  // Load (or clear) chat history whenever the logged-in identity changes.
  // Runs on every navigation so login/logout are detected without a remount,
  // since ChatWidget lives at the App level and persists across routes.
  useEffect(() => {
    const user = getStoredUser();
    const currentKey = user ? user.id : 'guest';

    if (loadedForUserId.current === currentKey) {
      return; // already loaded for this identity
    }
    loadedForUserId.current = currentKey;

    if (!user) {
      // Logged out / guest: reset to a fresh greeting, never show a
      // previous logged-in user's history.
      setMessages([WELCOME_MESSAGE]);
      setSearchProducts([]);
      return;
    }

    // Logged in: fetch and restore this user's saved history.
    axios
      .get(`${CHAT_API}/api/chat/history/${user.id}`)
      .then((res) => {
        const history = res.data.messages || [];
        if (history.length === 0) {
          setMessages([WELCOME_MESSAGE]);
          return;
        }
        const restored: Message[] = history.map((m: any, idx: number) => ({
          id: `history-${idx}`,
          role: m.role,
          content: m.content,
        }));
        setMessages(restored);

        // Restore product cards from the most recent assistant message
        // that had any, so a returning shopper sees their last results.
        for (let i = history.length - 1; i >= 0; i--) {
          if (history[i].products && history[i].products.length > 0) {
            setSearchProducts(history[i].products);
            break;
          }
        }
      })
      .catch(() => {
        setMessages([WELCOME_MESSAGE]);
      });
  }, [location.pathname]);

  // Build current page/product context for the agent (Problem 8).
  const buildPageContext = async () => {
    const productMatch = location.pathname.match(/^\/products\/([^/]+)$/);
    const productId = productMatch ? productMatch[1] : undefined;
    if (productId) {
      try {
        const res = await axios.get(`${API_BASE}/api/products/${productId}`);
        const p = res.data;
        return {
          page_type: 'product_detail',
          product: {
            product_id: p.product_id,
            name: p.name,
            price: p.price,
            description: p.description,
            garment_type: p.garment_type,
            colors: p.colors || [],
          },
        };
      } catch {
        return { page_type: 'product_detail' };
      }
    }
    if (location.pathname === '/products') {
      return { page_type: 'products_list' };
    }
    return { page_type: 'general' };
  };

  const handleSend = async () => {
    if (input.trim() && !isLoading) {
      const userMessage: Message = {
        id: Date.now().toString(),
        role: 'user',
        content: input,
      };
      setMessages((prev) => [...prev, userMessage]);
      setInput('');
      setIsLoading(true);
      setSearchProducts([]); // Clear previous search results

      try {
        const user = getStoredUser();
        const pageContext = await buildPageContext();

        const response = await fetch(`${CHAT_API}/api/chat`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: userMessage.content,
            user_id: user ? user.id : null,
            page_context: pageContext,
          }),
        });

        if (!response.ok) {
          throw new Error('Failed to get response from chatbot');
        }

        const data = await response.json();
        const botMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: data.reply,
        };
        setMessages((prev) => [...prev, botMessage]);

        // Update search products if any were returned
        if (data.products && data.products.length > 0) {
          setSearchProducts(data.products);
        }
      } catch (error) {
        const errorMessage: Message = {
          id: (Date.now() + 1).toString(),
          role: 'assistant',
          content: 'Sorry, I encountered an error. Please try again.',
        };
        setMessages((prev) => [...prev, errorMessage]);
      } finally {
        setIsLoading(false);
      }
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (!isLoading) {
        handleSend();
      }
    }
  };

  // Resets the CURRENT visible conversation only. For logged-in users this
  // does not delete their persisted chat_messages rows - reloading the page
  // (or navigating away and back) will restore their saved history again,
  // since Problem 8 persistence is untouched by this control.
  const handleClearChat = () => {
    setMessages([WELCOME_MESSAGE]);
    setSearchProducts([]);
  };

  return (
    <>
      {searchProducts.length > 0 && (
        <div className="search-results-section">
          <div className="search-results-header">
            <h2>Search Results</h2>
            <button
              className="close-results"
              onClick={() => setSearchProducts([])}
              aria-label="Close search results"
            >
              ✕
            </button>
          </div>
          <div className="products-grid">
            {searchProducts.map((product) => (
              <ProductCard
                key={product.product_id}
                product_id={product.product_id}
                name={product.name}
                price={product.price}
                short_description={product.short_description}
                image_file_path={product.image_file_path}
              />
            ))}
          </div>
        </div>
      )}

      <div className="chat-widget">
        {isOpen && (
          <div className="chat-window">
            <div className="chat-header">
              <h3>Campus Customs Assistant</h3>
              <div className="chat-header-actions">
                <button
                  className="clear-chat-button"
                  onClick={handleClearChat}
                  aria-label="Clear chat"
                  title="Clear current conversation"
                >
                  Clear chat
                </button>
                <button
                  className="close-button"
                  onClick={() => setIsOpen(false)}
                  aria-label="Close chat"
                >
                  ✕
                </button>
              </div>
            </div>
            <div className="chat-messages">
              {messages.map((message) => (
                <div key={message.id} className={`message ${message.role}`}>
                  <p>{message.content}</p>
                </div>
              ))}
              {isLoading && (
                <div className="message assistant thinking">
                  <p className="thinking-indicator">
                    <span className="thinking-dot" />
                    <span className="thinking-dot" />
                    <span className="thinking-dot" />
                    Campus Customs is thinking...
                  </p>
                </div>
              )}
            </div>
            <div className="chat-input-area">
              <textarea
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Type your message..."
                rows={2}
                disabled={isLoading}
              />
              <button onClick={handleSend} className="send-button" disabled={isLoading || !input.trim()}>
                {isLoading ? 'Sending...' : 'Send'}
              </button>
            </div>
          </div>
        )}
        <button
          className="chat-toggle-button"
          onClick={() => setIsOpen(!isOpen)}
          aria-label="Toggle chat"
        >
          💬
        </button>
      </div>
    </>
  );
}
