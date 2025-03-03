import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression
from datetime import datetime, timedelta

class GlucosePredictor:
    def __init__(self):
        self.scaler = StandardScaler()
        self.model = LinearRegression()
        self.short_term_model = LinearRegression()  # 用于实时预测

    def _prepare_data(self, data, sequence_length=3):
        features = ['glucose_level', 'carbs', 'insulin']
        X = data[features].values
        X = self.scaler.fit_transform(X)

        sequences = []
        targets = []
        for i in range(len(X) - sequence_length):
            sequences.append(X[i:i+sequence_length].flatten())
            targets.append(X[i+sequence_length, 0])  # Next glucose level

        return np.array(sequences), np.array(targets)

    def predict(self, data):
        """Predict next 6 hours of glucose levels"""
        if len(data) < 3:
            return []

        X, y = self._prepare_data(data)
        if len(X) == 0:
            return []

        # Fit the model with available data
        self.model.fit(X, y)

        # Prepare last sequence for prediction
        last_sequence = data[['glucose_level', 'carbs', 'insulin']].values[-3:]
        last_sequence = self.scaler.transform(last_sequence)
        last_sequence = last_sequence.flatten().reshape(1, -1)

        # Predict next 6 hours
        predictions = []
        current_sequence = last_sequence.copy()

        for _ in range(6):
            pred = self.model.predict(current_sequence)[0]
            predictions.append(pred)

            # Update sequence for next prediction
            new_row = np.array([pred, 0, 0])  # Assuming no future carbs/insulin
            current_sequence = np.roll(current_sequence, -3)
            current_sequence[0, -3:] = new_row

        # Inverse transform predictions
        pred_array = np.array(predictions).reshape(-1, 1)
        pred_array = np.hstack([pred_array, np.zeros((len(pred_array), 2))])
        pred_array = self.scaler.inverse_transform(pred_array)[:, 0]

        return pred_array

    def predict_real_time(self, data, minutes=30):
        """Predict glucose levels for the next 30 minutes in 5-minute intervals"""
        if len(data) < 12:  # Need at least 1 hour of data
            return []

        # Prepare recent data for short-term prediction
        recent_data = data.sort_values('timestamp').tail(12)
        X = recent_data[['glucose_level', 'carbs', 'insulin']].values
        X = self.scaler.fit_transform(X)

        # Train short-term model
        sequences, targets = [], []
        for i in range(len(X) - 2):
            sequences.append(X[i:i+2].flatten())
            targets.append(X[i+2, 0])

        if len(sequences) == 0:
            return []

        self.short_term_model.fit(sequences, targets)

        # Generate predictions for next 30 minutes (6 five-minute intervals)
        predictions = []
        current_sequence = X[-2:].flatten().reshape(1, -1)

        for _ in range(6):
            pred = self.short_term_model.predict(current_sequence)[0]
            predictions.append(pred)

            # Update sequence
            new_row = np.array([pred, 0, 0])
            current_sequence = np.roll(current_sequence, -3)
            current_sequence[0, -3:] = new_row

        # Inverse transform predictions
        pred_array = np.array(predictions).reshape(-1, 1)
        pred_array = np.hstack([pred_array, np.zeros((len(pred_array), 2))])
        pred_array = self.scaler.inverse_transform(pred_array)[:, 0]

        return pred_array

    def get_prediction_intervals(self, predictions, confidence=0.95):
        """Calculate prediction intervals"""
        std_dev = np.std(predictions)
        z_score = 1.96  # 95% confidence interval

        lower_bound = predictions - (z_score * std_dev)
        upper_bound = predictions + (z_score * std_dev)

        return lower_bound, upper_bound