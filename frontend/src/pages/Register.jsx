import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

const ROLES = [
  "renewable_energy_planner",
  "gis_analyst",
  "project_manager",
  "investor_developer",
  "government_regulator",
];

export default function Register() {
  const [form, setForm] = useState({
    full_name: "",
    email: "",
    password: "",
    role: ROLES[0],
    organization: "",
  });
  const [error, setError] = useState("");
  const { register } = useAuth();
  const navigate = useNavigate();

  const handleChange = (e) => setForm({ ...form, [e.target.name]: e.target.value });

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError("");
    try {
      await register(form);
      navigate("/projects");
    } catch (err) {
      setError(err.response?.data?.detail || "Registration failed");
    }
  };

  return (
    <div style={{ maxWidth: 420, margin: "60px auto" }}>
      <h2>Create an account</h2>
      <form onSubmit={handleSubmit}>
        <input
          name="full_name"
          placeholder="Full name"
          value={form.full_name}
          onChange={handleChange}
          required
          style={{ width: "100%", marginBottom: 10, padding: 8 }}
        />
        <input
          name="email"
          type="email"
          placeholder="Email"
          value={form.email}
          onChange={handleChange}
          required
          style={{ width: "100%", marginBottom: 10, padding: 8 }}
        />
        <input
          name="password"
          type="password"
          placeholder="Password (min 8 chars)"
          value={form.password}
          onChange={handleChange}
          required
          minLength={8}
          style={{ width: "100%", marginBottom: 10, padding: 8 }}
        />
        <input
          name="organization"
          placeholder="Organization (optional)"
          value={form.organization}
          onChange={handleChange}
          style={{ width: "100%", marginBottom: 10, padding: 8 }}
        />
        <select name="role" value={form.role} onChange={handleChange} style={{ width: "100%", marginBottom: 10, padding: 8 }}>
          {ROLES.map((r) => (
            <option key={r} value={r}>
              {r.replaceAll("_", " ")}
            </option>
          ))}
        </select>
        {error && <p style={{ color: "red" }}>{error}</p>}
        <button type="submit" style={{ width: "100%", padding: 10 }}>
          Register
        </button>
      </form>
      <p style={{ marginTop: 10 }}>
        Already have an account? <Link to="/login">Sign in</Link>
      </p>
    </div>
  );
}
