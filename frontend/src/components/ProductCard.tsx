import { Link } from 'react-router-dom';

interface ProductCardProps {
  product_id: string;
  name: string;
  price: number;
  short_description: string;
  image_file_path: string;
  in_stock?: boolean;
}

const API_BASE = 'http://localhost:8000';

export default function ProductCard({
  product_id,
  name,
  price,
  short_description,
  image_file_path,
  in_stock,
}: ProductCardProps) {
  return (
    <Link to={`/products/${product_id}`} className="product-card-link">
      <div className="product-card">
        <div className="product-image-wrapper">
          <img
            src={`${API_BASE}/images/${image_file_path.split('/').pop()}`}
            alt={name}
            className="product-image"
            onError={(e) => {
              (e.target as HTMLImageElement).src = `${API_BASE}/images/placeholder.jpg`;
            }}
          />
          {in_stock === false && <span className="stock-badge out">Out of Stock</span>}
          {in_stock === true && <span className="stock-badge in">In Stock</span>}
        </div>
        <div className="product-info">
          <h3>{name}</h3>
          <p className="product-description">{short_description}</p>
          <div className="product-footer">
            <span className="product-price">${price.toFixed(2)}</span>
            <span className="view-details">View Details →</span>
          </div>
        </div>
      </div>
    </Link>
  );
}
