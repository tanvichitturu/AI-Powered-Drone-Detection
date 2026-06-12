import numpy as np
class KalmanFilter:
    def __init__(self, dt=1.0):
        self.dt = dt
        # State: [x, y, z, vx, vy, vz]
        self.state = np.zeros(6)
        self.F = np.array([
    [1, 0, 0, dt, 0,  0 ],
    [0, 1, 0, 0,  dt, 0 ],
    [0, 0, 1, 0,  0,  dt],
    [0, 0, 0, 1,  0,  0 ],
    [0, 0, 0, 0,  1,  0 ],
    [0, 0, 0, 0,  0,  1 ]
], dtype=float)
        self.H = np.array([
    [1, 0, 0, 0, 0, 0],
    [0, 1, 0, 0, 0, 0],
    [0, 0, 1, 0, 0, 0]
], dtype=float)
        self.Q = np.eye(6) * 0.1
        self.R = np.eye(3) * 1.0
        self.P = np.eye(6) * 1.0

    def initialize(self, first_measurement):
        # Set initial position from first measurement
        self.state[:3] = first_measurement
        self.state[3:6] = 0  # assume starts at rest
    
    def predict(self):
        # Predict next state using physics
        self.state = self.F @ self.state
        
        # Update uncertainty
        self.P = self.F @ self.P @ self.F.T + self.Q
        
        return self.state[:3]  # return predicted x, y, z
    
    def update(self, measurement):
        # Compute Kalman Gain
        S = self.H @ self.P @ self.H.T + self.R
        K = self.P @ self.H.T @ np.linalg.inv(S)
        
        # Update state with measurement
        innovation = measurement - self.H @ self.state
        self.state = self.state + K @ innovation
        
        # Update uncertainty
        self.P = (np.eye(6) - K @ self.H) @ self.P
        
        return self.state[:3]  # return updated x, y, z
    
    def predict_future(self, n_steps):
        # Save current state
        saved_state = self.state.copy()
        saved_P = self.P.copy()
        
        # Predict N steps into future
        future_positions = []
        for _ in range(n_steps):
            pos = self.predict()
            future_positions.append(pos.copy())
        
        # Restore current state
        self.state = saved_state
        self.P = saved_P
        
        return np.array(future_positions)

