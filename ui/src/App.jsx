import React, { useState, useEffect } from "react";
import "./App.css";

function App() {
  const [logs, setLogs] = useState([]);
  const [activeTab, setActiveTab] = useState("dashboard");
  const [unauthorized, setUnauthorized] = useState(0)
  const [revenue, setRevenue]  = useState(0)
  const [vehicles, setVehicles] = useState(0)
  const [recentActivity, setRecentActivity] = useState([])

  useEffect(() => {
    const fetchData = async () => {
      try {
        const vehiclesRes = await fetch(`http://localhost:8000/vehicles-in-parking`);
        const systemLogsRes = await fetch(`http://localhost:8000/system-logs`);
        const unauthorizedRes = await fetch(`http://localhost:8000/unauthorized-attempts`);
        const revenueRes = await fetch(`http://localhost:8000/today-revenue`);
        const recentActivityRes = await fetch(`http://localhost:8000/recent-activity`);
  
        const vehiclesData = await vehiclesRes.json();
        const logsData = await systemLogsRes.json();
        const unauthorizedData = await unauthorizedRes.json();
        const revenueData = await revenueRes.json();
        const recentActivityData = await recentActivityRes.json();
  
        setVehicles(vehiclesData.length);
        setLogs(logsData);
        setUnauthorized(unauthorizedData.unauthorized_access);
        setRevenue(revenueData.revenue_today);
        setRecentActivity(recentActivityData);
      } catch (error) {
        console.log("Error fetching data:", error.message);
      }
    };
  
    fetchData();
  }, []);
  

  return (
    <div className="app-container">
      <header className="app-header">
        <h1>Automated Parking Management System</h1>
        <nav className="tabs">
          <button
            className={activeTab === "dashboard" ? "active" : ""}
            onClick={() => setActiveTab("dashboard")}
          >
            Dashboard
          </button>
          <button
            className={activeTab === "logs" ? "active" : ""}
            onClick={() => setActiveTab("logs")}
          >
            System Logs
          </button>
        </nav>
      </header>

      <main className="app-main">
        {activeTab === "dashboard" && (
          <div className="dashboard">
          <div className="stats-container">
              <div className="stat-card">
                <h3>Current Vehicles</h3>
                <p>{vehicles}</p>
              </div>
              <div className="stat-card">
                <h3>Today's Revenue</h3>
                <p>{revenue} FRW</p>
              </div>
              <div className="stat-card">
                <h3>Unauthorized Exits</h3>
                <p>{unauthorized}</p>
              </div>
            </div>
            <div className="activity-feed">
              <h2>Recent Activity</h2>
              <ul>
                {recentActivity.map((log, index) => (
                  <li key={index} className={log.status === "UNPAID" ? "alert" : ""}>
                    <span className="plate">{log.plate_number}</span>
                    <span className="event">{log.action}</span>
                    <span className={`status ${log.status === "PAID" ? "paid" : "unpaid"}`}>
                      {log.status}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {activeTab === "logs" && (
          <div className="logs-table">
            <h2>System Logs</h2>
            <table>
            <thead>
              <tr>
                <th>Type</th>
                <th>Plate Number</th>
                <th>Time</th>
                <th>Amount</th>
                <th>Entry/Exit</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {logs.map((log, index) => (
                <tr
                  key={index}
                  className={log.type === "alert" ? "unauthorized" : ""}
                >
                  <td>{log.type === "alert" ? "Alert" : "Plate Log"}</td>
                  <td>{log.plate_number || "Unknown"}</td>
                  <td>{log.timestamp}</td>
                  <td>
                    {log.type === "plate_log" && log.entry_exit === "exit" || log.amount >0
                      ? `${log.amount} RWF`
                      : "-"}
                  </td>
                  <td>
                    {log.entry_exit || log.message}
                  </td>
                  <td>
                    {log.type === "alert" ? (
                      <span className="status-badge unauthorized">
                        {log.alert_type}
                      </span>
                    ) : (
                      <span
                        className={`status-badge ${
                          log.payment_status === 1 ? "paid" : "unpaid"
                        }`}
                      >
                        {log.payment_status === 1 ? "Paid" : "Unpaid"}
                      </span>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>


          </div>
        )}
      </main>

      <footer className="app-footer">
        <p>Automated Parking Management System © {new Date().getFullYear()}</p>
      </footer>
    </div>
  );
}

export default App;
