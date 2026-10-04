import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import axios from 'axios';
import './ProductDetail.css';

interface Product {
  product_id: string;
  name: string;
  price: number;
  description: string;
  image_file_path: string;
  garment_type: string;
  colors: string[];
  search_tags: string[];
}

interface InventoryItem {
  size: string;
  quantity: number;
}


const API_BASE = 'http://localhost:8000';

export default function ProductDetail() {
  const { productId } = useParams<{ productId: string }>();
  const [product, setProduct] = useState<Product | null>(null);
  const [inventory, setInventory] = useState<InventoryItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const fetchProductAndInventory = async () => {
      try {
        const [productRes, inventoryRes] = await Promise.all([
          axios.get(`${API_BASE}/api/products/${productId}`),
          axios.get(`${API_BASE}/api/inventory/${productId}`),
        ]);
        setProduct(productRes.data);
        setInventory(inventoryRes.data.inventory);
        setLoading(false);
      } catch (err) {
        setError('Failed to load product details.');
        setLoading(false);
      }
    };

    if (productId) {
      fetchProductAndInventory();
    }
  }, [productId]);

  if (loading) {
    return <div className="product-detail-page"><p className="loading">Loading product details...</p></div>;
  }

  if (error || !product) {
    return (
      <div className="product-detail-page">
        <p className="error">{error || 'Product not found.'}</p>
        <Link to="/products" className="back-link">← Back to Products</Link>
      </div>
    );
  }

  return (
    <div className="product-detail-page">
      <Link to="/products" className="back-link">← Back to Products</Link>

      <div className="product-detail-container">
        <div className="product-image-section">
          <img
            src={`${API_BASE}/images/${product.image_file_path.split('/').pop()}`}
            alt={product.name}
            className="product-detail-image"
          />
        </div>

        <div className="product-details-section">
          <h1>{product.name}</h1>

          <div className="product-meta">
            <span className="garment-type">{product.garment_type}</span>
            <span className="product-price">${product.price.toFixed(2)}</span>
          </div>

          <p className="product-full-description">{product.description}</p>

          {product.colors && product.colors.length > 0 && (
            <div className="product-colors">
              <h3>Available Colors:</h3>
              <ul>
                {product.colors.map((color) => (
                  <li key={color}>{color}</li>
                ))}
              </ul>
            </div>
          )}

          <div className="inventory-section">
            <h3>Available Sizes & Stock</h3>
            {inventory.length > 0 ? (
              <table className="inventory-table">
                <thead>
                  <tr>
                    <th>Size</th>
                    <th>Quantity</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {inventory.map((item) => (
                    <tr key={item.size}>
                      <td className="size-cell">{item.size}</td>
                      <td>{item.quantity}</td>
                      <td>
                        {item.quantity > 0 ? (
                          <span className="status-in-stock">In Stock</span>
                        ) : (
                          <span className="status-out-of-stock">Out of Stock</span>
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <p>No inventory information available.</p>
            )}
          </div>

          {product.search_tags && product.search_tags.length > 0 && (
            <div className="product-tags">
              <h3>Tags:</h3>
              <div className="tags-container">
                {product.search_tags.map((tag) => (
                  <span key={tag} className="tag">{tag}</span>
                ))}
              </div>
            </div>
          )}

          <button className="add-to-cart-button">Add to Cart (Coming Soon)</button>
        </div>
      </div>
    </div>
  );
}
