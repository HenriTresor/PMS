import React, { useState, useEffect } from "react";
import "./App.css";

function App() {
  const [logs, setLogs] = useState([]);
  const [activeTab, setActiveTab] = useState("dashboard");
  const [paymentData, setPaymentData] = useState({
    plateNumber: "",
    amount: "",
    cardId: "",
  });

  // Mock data fetch - in real app, this would call your backend API
  useEffect(() => {
    const fetchLogs = async () => {
      // Simulate API call
      const mockLogs = [
        {
          plate_number: "RAB234D",
          check_in_time: "2023-05-15 08:30:00",
          check_out_time: "",
          amount_paid: "1500",
          payment_status: "1",
          unauthorized_exit: "0",
        },
        {
          plate_number: "RAC123B",
          check_in_time: "2023-05-15 09:15:00",
          check_out_time: "2023-05-15 10:30:00",
          amount_paid: "750",
          payment_status: "1",
          unauthorized_exit: "0",
        },
        {
          plate_number: "RAD456C",
          check_in_time: "2023-05-15 10:00:00",
          check_out_time: "",
          amount_paid: "0",
          payment_status: "0",
          unauthorized_exit: "1",
        },
      ];
      setLogs(mockLogs);
    };

    fetchLogs();
    const interval = setInterval(fetchLogs, 5000); // Refresh every 5 seconds
    return () => clearInterval(interval);
  }, []);

  const handlePaymentSubmit = (e) => {
    e.preventDefault();
    // In real app, this would call your backend API
    alert(
      `Payment processed: ${paymentData.amount} FRW for plate ${paymentData.plateNumber}`
    );
    setPaymentData({
      plateNumber: "",
      amount: "",
      cardId: "",
    });
  };

  const handleInputChange = (e) => {
    const { name, value } = e.target;
    setPaymentData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

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
            className={activeTab === "payments" ? "active" : ""}
            onClick={() => setActiveTab("payments")}
          >
            Process Payment
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
                <p>{logs.filter((log) => !log.check_out_time).length}</p>
              </div>
              <div className="stat-card">
                <h3>Today's Revenue</h3>
                <p>
                  {logs.reduce(
                    (sum, log) => sum + parseFloat(log.amount_paid || 0),
                    0
                  )}{" "}
                  FRW
                </p>
              </div>
              <div className="stat-card">
                <h3>Unauthorized Exits</h3>
                <p>
                  {logs.filter((log) => log.unauthorized_exit === "1").length}
                </p>
              </div>
            </div>

            <div className="activity-feed">
              <h2>Recent Activity</h2>
              <ul>
                {logs.slice(0, 5).map((log, index) => (
                  <li
                    key={index}
                    className={log.unauthorized_exit === "1" ? "alert" : ""}
                  >
                    <span className="plate">{log.plate_number}</span>
                    {log.unauthorized_exit === "1" ? (
                      <span className="event">
                        Unauthorized exit at {log.check_out_time}
                      </span>
                    ) : log.check_out_time ? (
                      <span className="event">
                        Checked out at {log.check_out_time}
                      </span>
                    ) : (
                      <span className="event">
                        Checked in at {log.check_in_time}
                      </span>
                    )}
                    <span
                      className={`status ${
                        log.payment_status === "1" ? "paid" : "unpaid"
                      }`}
                    >
                      {log.payment_status === "1" ? "PAID" : "UNPAID"}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>
        )}

        {activeTab === "payments" && (
          <div className="payment-form">
            <h2>Process Payment</h2>
            <form onSubmit={handlePaymentSubmit}>
              <div className="form-group">
                <label>License Plate Number</label>
                <input
                  type="text"
                  name="plateNumber"
                  value={paymentData.plateNumber}
                  onChange={handleInputChange}
                  placeholder="RAB234D"
                  required
                  pattern="[A-Z]{3}\d{3}[A-Z]"
                  title="Format: ABC123D"
                />
              </div>
              <div className="form-group">
                <label>RFID Card ID</label>
                <input
                  type="text"
                  name="cardId"
                  value={paymentData.cardId}
                  onChange={handleInputChange}
                  required
                />
              </div>
              <div className="form-group">
                <label>Amount (FRW)</label>
                <input
                  type="number"
                  name="amount"
                  value={paymentData.amount}
                  onChange={handleInputChange}
                  min="500"
                  step="500"
                  required
                />
              </div>
              <button type="submit" className="submit-btn">
                Process Payment
              </button>
            </form>
          </div>
        )}

        {activeTab === "logs" && (
          <div className="logs-table">
            <h2>System Logs</h2>
            <table>
              <thead>
                <tr>
                  <th>Plate Number</th>
                  <th>Check-In Time</th>
                  <th>Check-Out Time</th>
                  <th>Amount Paid</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody>
                {logs.map((log, index) => (
                  <tr
                    key={index}
                    className={
                      log.unauthorized_exit === "1" ? "unauthorized" : ""
                    }
                  >
                    <td>{log.plate_number}</td>
                    <td>{log.check_in_time}</td>
                    <td>{log.check_out_time || "Still parked"}</td>
                    <td>{log.amount_paid} FRW</td>
                    <td>
                      <span
                        className={`status-badge ${
                          log.payment_status === "1" ? "paid" : "unpaid"
                        }`}
                      >
                        {log.payment_status === "1" ? "Paid" : "Unpaid"}
                        {log.unauthorized_exit === "1" &&
                          " (Unauthorized exit)"}
                      </span>
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
