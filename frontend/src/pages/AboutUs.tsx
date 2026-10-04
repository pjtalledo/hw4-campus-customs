import './AboutUs.css';

export default function AboutUs() {
  return (
    <div className="about-us-page">
      <div className="about-container">
        <h1>About Campus Customs</h1>

        <section className="about-section">
          <h2>Our Mission</h2>
          <p>
            Campus Customs is committed to celebrating and connecting the Yale community through authentic,
            high-quality merchandise. We believe that what you wear tells a story, and we're here to help
            you tell yours.
          </p>
        </section>

        <section className="about-section">
          <h2>Who We Are</h2>
          <p>
            Founded by students and alumni who understood the power of community spirit, Campus Customs
            has grown into a trusted destination for Yale merchandise. We work directly with our community
            to understand what matters to you, and we source products that reflect the values and pride
            of Yale.
          </p>
          <p>
            Every product in our catalogue is carefully selected to ensure it meets our standards for
            quality, comfort, and authenticity. From classic designs that have stood the test of time
            to exciting new collaborations, we have something for everyone.
          </p>
        </section>

        <section className="about-section">
          <h2>Our Values</h2>
          <div className="values-grid">
            <div className="value-card">
              <h3>Community</h3>
              <p>We celebrate the bonds that connect us and strengthen our Yale community.</p>
            </div>
            <div className="value-card">
              <h3>Quality</h3>
              <p>Excellence in every product, every interaction, and every detail.</p>
            </div>
            <div className="value-card">
              <h3>Authenticity</h3>
              <p>We stay true to what makes Yale special and authentic.</p>
            </div>
            <div className="value-card">
              <h3>Accessibility</h3>
              <p>We make great merchandise available to everyone in our community.</p>
            </div>
          </div>
        </section>

        <section className="about-section">
          <h2>Get in Touch</h2>
          <p>
            Have questions or suggestions? We'd love to hear from you! Contact us at support@campuscustoms.yale.edu
            or visit us during our office hours.
          </p>
        </section>
      </div>
    </div>
  );
}
