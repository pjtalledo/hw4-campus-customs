import { useEffect, useMemo, useState } from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import axios from 'axios';
import ProductCard from '../components/ProductCard';
import './Products.css';

interface Product {
  product_id: string;
  name: string;
  price: number;
  description: string;
  short_description: string;
  image_file_path: string;
  garment_type: string;
  in_stock: boolean;
}

const API_BASE = 'http://localhost:8000';

// Groups the real (messy) garment_type strings from the database into a
// small set of shopper-friendly categories. Grounded entirely in actual
// catalogue values - no invented categories are shown unless a real product
// maps to them (see availableCategories below).
function categorize(garmentType: string): string {
  const t = (garmentType || '').toLowerCase();
  if (t.includes('hoodie') || t.includes('hooded')) return 'Hoodies';
  if (t.includes('t-shirt') || t.includes('tee')) return 'T-Shirts';
  if (t.includes('jacket')) return 'Jackets';
  if (t.includes('quarter-zip')) return 'Quarter-Zips';
  if (t.includes('crewneck') || t.includes('sweatshirt') || t.includes('mockneck')) return 'Crewnecks & Sweatshirts';
  if (t.includes('performance shirt')) return 'Performance Shirts';
  return 'Other';
}

const ALL_CATEGORIES = 'All Products';
const ALL_PRICES = 0; // 0 = no max price cap
const AVAILABILITY_ALL = 'all';
const AVAILABILITY_IN_STOCK = 'in_stock';

export default function Products() {
  const [products, setProducts] = useState<Product[]>([]);
  const [filteredProducts, setFilteredProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchTerm, setSearchTerm] = useState('');
  const [category, setCategory] = useState(ALL_CATEGORIES);
  const [maxPrice, setMaxPrice] = useState(ALL_PRICES);
  const [availability, setAvailability] = useState(AVAILABILITY_ALL);
  const [searchParams] = useSearchParams();

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        const response = await axios.get(`${API_BASE}/api/products`);
        setProducts(response.data.products);
        setLoading(false);
      } catch (err) {
        setError('Failed to load products. Make sure the backend is running.');
        setLoading(false);
      }
    };

    fetchProducts();
  }, []);

  // Real price ceiling from the loaded catalogue, used to size the price slider.
  const priceCeiling = useMemo(() => {
    if (products.length === 0) return 100;
    return Math.ceil(Math.max(...products.map((p) => p.price)));
  }, [products]);

  // Categories derived only from products that actually exist.
  const availableCategories = useMemo(() => {
    const set = new Set(products.map((p) => categorize(p.garment_type)));
    return [ALL_CATEGORIES, ...Array.from(set).sort()];
  }, [products]);

  useEffect(() => {
    const filterParam = searchParams.get('filter') || '';
    const searchLower = searchTerm.toLowerCase();

    let filtered = products.filter((product) => {
      const matchesSearch = !searchTerm ||
        product.name.toLowerCase().includes(searchLower) ||
        product.short_description.toLowerCase().includes(searchLower);

      const matchesUrlFilter = !filterParam ||
        product.garment_type?.toLowerCase().includes(filterParam.toLowerCase()) ||
        product.name.toLowerCase().includes(filterParam.toLowerCase());

      const matchesCategory = category === ALL_CATEGORIES || categorize(product.garment_type) === category;

      const matchesPrice = maxPrice === ALL_PRICES || product.price <= maxPrice;

      const matchesAvailability = availability === AVAILABILITY_ALL || product.in_stock === true;

      return matchesSearch && matchesUrlFilter && matchesCategory && matchesPrice && matchesAvailability;
    });

    setFilteredProducts(filtered);
  }, [products, searchTerm, searchParams, category, maxPrice, availability]);

  const hasActiveFilters = Boolean(
    searchTerm || category !== ALL_CATEGORIES || maxPrice !== ALL_PRICES || availability !== AVAILABILITY_ALL
  );

  const clearAllFilters = () => {
    setSearchTerm('');
    setCategory(ALL_CATEGORIES);
    setMaxPrice(ALL_PRICES);
    setAvailability(AVAILABILITY_ALL);
  };

  if (loading) {
    return <div className="products-page"><p className="loading">Loading products...</p></div>;
  }

  if (error) {
    return <div className="products-page"><p className="error">{error}</p></div>;
  }

  const filterParam = searchParams.get('filter');

  return (
    <div className="products-page">
      <section className="products-header yale-crest-bg">
        <div className="products-header-content">
          <h1>Our Products</h1>
          <p className="products-subtitle">Authentic Yale merchandise for students, alumni, and supporters</p>
        </div>
      </section>

      <div className="products-controls">
        <input
          type="text"
          placeholder="Search products..."
          className="search-input"
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
        />

        <div className="filter-row">
          <label className="filter-field">
            <span>Category</span>
            <select value={category} onChange={(e) => setCategory(e.target.value)}>
              {availableCategories.map((c) => (
                <option key={c} value={c}>{c}</option>
              ))}
            </select>
          </label>

          <label className="filter-field">
            <span>Max Price: {maxPrice === ALL_PRICES ? 'Any' : `$${maxPrice}`}</span>
            <input
              type="range"
              min={0}
              max={priceCeiling}
              step={1}
              value={maxPrice === ALL_PRICES ? priceCeiling : maxPrice}
              onChange={(e) => setMaxPrice(Number(e.target.value))}
            />
          </label>

          <label className="filter-field">
            <span>Availability</span>
            <select value={availability} onChange={(e) => setAvailability(e.target.value)}>
              <option value={AVAILABILITY_ALL}>All</option>
              <option value={AVAILABILITY_IN_STOCK}>In Stock</option>
            </select>
          </label>

          {hasActiveFilters && (
            <button type="button" className="clear-filters-btn" onClick={clearAllFilters}>
              Clear Filters
            </button>
          )}
        </div>

        <div className="results-summary">
          <span className="results-count">{filteredProducts.length} product{filteredProducts.length === 1 ? '' : 's'}</span>
          {(searchTerm || filterParam || category !== ALL_CATEGORIES || maxPrice !== ALL_PRICES || availability !== AVAILABILITY_ALL) && (
            <div className="filter-info">
              {filterParam && <span className="filter-badge">Filter: {filterParam}</span>}
              {searchTerm && <span className="search-badge">Search: {searchTerm}</span>}
              {category !== ALL_CATEGORIES && <span className="filter-badge">{category}</span>}
              {maxPrice !== ALL_PRICES && <span className="filter-badge">Under ${maxPrice}</span>}
              {availability === AVAILABILITY_IN_STOCK && <span className="filter-badge">In Stock</span>}
              {filterParam && <Link to="/products" className="clear-filters">Clear URL filter</Link>}
            </div>
          )}
        </div>
      </div>

      {filteredProducts.length === 0 ? (
        <div className="no-results">
          <p>No products match your current filters.</p>
          {hasActiveFilters && (
            <button type="button" className="clear-filters-btn" onClick={clearAllFilters}>
              Clear Filters
            </button>
          )}
        </div>
      ) : (
        <div className="products-grid">
          {filteredProducts.map((product) => (
            <ProductCard
              key={product.product_id}
              product_id={product.product_id}
              name={product.name}
              price={product.price}
              short_description={product.short_description}
              image_file_path={product.image_file_path}
              in_stock={product.in_stock}
            />
          ))}
        </div>
      )}
    </div>
  );
}
