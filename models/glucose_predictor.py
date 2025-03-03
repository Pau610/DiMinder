import numpy as np
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LinearRegression

class GlucosePredictor:
    def __init__(self):
        self.scaler = StandardScaler()
        self.model = LinearRegression()

    def _prepare_data(self, data):
        features = ['glucose_level', 'carbs', 'insulin']
        X = data[features].values
        X = self.scaler.fit_transform(X)

        sequences = []
        targets = []
        for i in range(len(X) - 3):
            sequences.append(X[i:i+3].flatten())
            targets.append(X[i+3, 0])  # Next glucose level

        return np.array(sequences), np.array(targets)

    def predict(self, data):
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
        pred_array = np.hstack([pred_array, np.zeros((len(pred_array), 2))])  # Add dummy columns for inverse_transform
        pred_array = self.scaler.inverse_transform(pred_array)[:, 0]  # Get only glucose values

        return pred_array