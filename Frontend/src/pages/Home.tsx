import React from "react";
import { Link } from "react-router-dom";

const Home: React.FC = () => {
  return (
    <div className="container">
      <h1>Welcome to the Soapbox Race!</h1>
      <p>
        This is the official website for the annual Soapbox Race event. Get
        ready for a thrilling day of racing, fun, and excitement!
      </p>
      <div className="button-group">
        <Link to="/races" className="button">
          View Races
        </Link>
        <Link to="/teams" className="button">
          Meet the Teams
        </Link>
        <Link to="/rules" className="button">
          Rules & Regulations
        </Link>
        <Link to="/contact" className="button">
          Contact Us
        </Link>
      </div>
    </div>
  );
};

export default Home;
