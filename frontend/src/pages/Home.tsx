import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import axios from 'axios';
import handsomeDan from '../assets/handsome-dan-transparent.png';
import './Home.css';

interface Product {
  product_id: string;
  name: string;
  price: number;
  image_file_path: string;
}

const API_BASE = 'http://localhost:8000';

export default function Home() {
  const [featuredProducts, setFeaturedProducts] = useState<Product[]>([]);

  useEffect(() => {
    const fetchFeatured = async () => {
      try {
        const response = await axios.get(`${API_BASE}/api/products?limit=3`);
        setFeaturedProducts(response.data.products);
      } catch (error) {
        console.error('Failed to load featured products:', error);
      }
    };
    fetchFeatured();
  }, []);

  return (
    <div className="home-page">
      <section className="hero-section yale-crest-bg">
        <div className="hero-content">
          <div className="hero-text">
            <span className="hero-eyebrow">Boola Boola · Est. for Yale Bulldogs</span>
            <h1>Campus Customs</h1>
            <p className="hero-tagline">Premium Yale merchandise designed for your pride</p>
            <Link to="/products" className="cta-button">Shop Now</Link>
          </div>
          <div className="hero-image">
            <img src={handsomeDan} alt="Handsome Dan - Yale Bulldog" />
          </div>
        </div>
      </section>

      <section className="featured-section">
        <div className="featured-container">
          <h2>Featured Products</h2>
          <div className="featured-grid">
            {featuredProducts.map((product) => (
              <Link key={product.product_id} to={`/products/${product.product_id}`} className="featured-card-link">
                <div className="featured-card">
                  <img src={`${API_BASE}/images/${product.image_file_path.split('/').pop()}`} alt={product.name} />
                  <h3>{product.name}</h3>
                  <p className="featured-price">${product.price.toFixed(2)}</p>
                </div>
              </Link>
            ))}
          </div>
          <div className="view-all">
            <Link to="/products" className="view-all-link">View All Products</Link>
          </div>
        </div>
      </section>

      <section className="highlights-section">
        <div className="highlights-container">
          <div className="highlight">
            <h3>Yale Quality</h3>
            <p>Premium merchandise celebrating Yale spirit and tradition</p>
          </div>
          <div className="highlight">
            <h3>Authentic Design</h3>
            <p>Exclusive collections for students, alumni, and supporters</p>
          </div>
          <div className="highlight">
            <h3>Community First</h3>
            <p>Supporting the Yale community with apparel that matters</p>
          </div>
        </div>
      </section>

      <section className="categories-section">
        <div className="categories-container">
          <h2>Shop by Style</h2>
          <div className="categories-grid">
            <Link to="/products?filter=t-shirt" className="category-card">
              <div className="category-label">T-Shirts</div>
            </Link>
            <Link to="/products?filter=hoodie" className="category-card">
              <div className="category-label">Hoodies & Sweatshirts</div>
            </Link>
            <Link to="/products?filter=crewneck" className="category-card">
              <div className="category-label">Crewnecks</div>
            </Link>
            <Link to="/products?filter=quarter-zip" className="category-card">
              <div className="category-label">Quarter-Zip Pullovers</div>
            </Link>
            <Link to="/products?filter=jacket" className="category-card">
              <div className="category-label">Jackets & Fleece</div>
            </Link>
          </div>
        </div>
      </section>

      <section className="about-preview-section">
        <div className="about-preview-container">
          <h2>Your Yale Story Starts Here</h2>
          <p>
            Campus Customs creates authentic Yale merchandise for students, alumni, and supporters.
            We're dedicated to celebrating our community through quality apparel and thoughtful design.
          </p>
          <Link to="/about" className="learn-more-link">Learn More About Us</Link>
        </div>
      </section>
    </div>
  );
}
