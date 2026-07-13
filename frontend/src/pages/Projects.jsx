import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { projectsApi } from "../api";
import { useAuth } from "../context/AuthContext";

export default function Projects() {
  const [projects, setProjects] = useState([]);
  const [form, setForm] = useState({ name: "", description: "", region: "" });
  const { user, logout } = useAuth();

  const loadProjects = async () => {
    const { data } = await projectsApi.list();
    setProjects(data);
  };

  useEffect(() => {
    loadProjects();
  }, []);

  const handleCreate = async (e) => {
    e.preventDefault();
    await projectsApi.create(form);
    setForm({ name: "", description: "", region: "" });
    loadProjects();
  };

  return (
    <div style={{ maxWidth: 800, margin: "40px auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between" }}>
        <h2>Projects</h2>
        <div>
          <span style={{ marginRight: 10 }}>
            {user?.full_name} ({user?.role})
          </span>
          <button onClick={logout}>Logout</button>
        </div>
      </div>

      <form onSubmit={handleCreate} style={{ marginBottom: 30 }}>
        <input
          placeholder="Project name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          required
          style={{ marginRight: 8, padding: 6 }}
        />
        <input
          placeholder="Region"
          value={form.region}
          onChange={(e) => setForm({ ...form, region: e.target.value })}
          style={{ marginRight: 8, padding: 6 }}
        />
        <input
          placeholder="Description"
          value={form.description}
          onChange={(e) => setForm({ ...form, description: e.target.value })}
          style={{ marginRight: 8, padding: 6 }}
        />
        <button type="submit">Create project</button>
      </form>

      <ul>
        {projects.map((p) => (
          <li key={p.id} style={{ marginBottom: 8 }}>
            <Link to={`/projects/${p.id}/sites`}>{p.name}</Link> — {p.region || "no region"}
          </li>
        ))}
      </ul>
    </div>
  );
}
