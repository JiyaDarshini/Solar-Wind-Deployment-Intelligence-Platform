import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { sitesApi } from "../api";

export default function Sites() {
  const { projectId } = useParams();
  const [sites, setSites] = useState([]);
  const [form, setForm] = useState({ name: "", latitude: "", longitude: "", region: "" });
  const [busySiteId, setBusySiteId] = useState(null);

  const loadSites = async () => {
    const { data } = await sitesApi.listForProject(projectId);
    setSites(data);
  };

  useEffect(() => {
    loadSites();
  }, [projectId]);

  const handleCreate = async (e) => {
    e.preventDefault();
    await sitesApi.create(projectId, {
      ...form,
      latitude: parseFloat(form.latitude),
      longitude: parseFloat(form.longitude),
    });
    setForm({ name: "", latitude: "", longitude: "", region: "" });
    loadSites();
  };

  const handleEnrich = async (siteId) => {
    setBusySiteId(siteId);
    try {
      await sitesApi.enrichEnvironmental(siteId);
      await loadSites();
    } finally {
      setBusySiteId(null);
    }
  };

  return (
    <div style={{ maxWidth: 900, margin: "40px auto" }}>
      <Link to="/projects">&larr; Back to projects</Link>
      <h2>Sites</h2>

      <form onSubmit={handleCreate} style={{ marginBottom: 30 }}>
        <input
          placeholder="Site name"
          value={form.name}
          onChange={(e) => setForm({ ...form, name: e.target.value })}
          required
          style={{ marginRight: 8, padding: 6 }}
        />
        <input
          placeholder="Latitude"
          value={form.latitude}
          onChange={(e) => setForm({ ...form, latitude: e.target.value })}
          required
          style={{ marginRight: 8, padding: 6, width: 100 }}
        />
        <input
          placeholder="Longitude"
          value={form.longitude}
          onChange={(e) => setForm({ ...form, longitude: e.target.value })}
          required
          style={{ marginRight: 8, padding: 6, width: 100 }}
        />
        <input
          placeholder="Region"
          value={form.region}
          onChange={(e) => setForm({ ...form, region: e.target.value })}
          style={{ marginRight: 8, padding: 6 }}
        />
        <button type="submit">Register site</button>
      </form>

      <table border="1" cellPadding="6" style={{ width: "100%", borderCollapse: "collapse" }}>
        <thead>
          <tr>
            <th>Name</th>
            <th>Coordinates</th>
            <th>Solar (kWh/m²/day)</th>
            <th>Wind (m/s)</th>
            <th>Temp (°C)</th>
            <th>Rainfall (mm/yr)</th>
            <th>Infrastructure</th>
            <th></th>
          </tr>
        </thead>
        <tbody>
          {sites.map((s) => (
            <tr key={s.id}>
              <td>{s.name}</td>
              <td>
                {s.latitude.toFixed(3)}, {s.longitude.toFixed(3)}
              </td>
              <td>{s.avg_solar_irradiance_kwh_m2_day ?? "—"}</td>
              <td>{s.avg_wind_speed_m_s ?? "—"}</td>
              <td>{s.avg_temperature_c ?? "—"}</td>
              <td>{s.annual_rainfall_mm ?? "—"}</td>
              <td>{s.existing_infrastructure ?? "—"}</td>
              <td>
                <button disabled={busySiteId === s.id} onClick={() => handleEnrich(s.id)}>
                  {busySiteId === s.id ? "Fetching..." : "Fetch environmental data"}
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
