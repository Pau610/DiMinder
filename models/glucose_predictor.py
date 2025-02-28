import numpy as np
from sklearn.preprocessing import StandardScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Dense, LSTM

class GlucosePredictor:
    def __init__(self):
        self.scaler = StandardScaler()
        self.model = self._build_model()
        
    def _build_model(self):
        model = Sequential([
            LSTM(32, input_shape=(3, 3), return_sequences=True),
            LSTM(16),
            Dense(8, activation='relu'),
            Dense(1)
        ])
        model.compile(optimizer='adam', loss='mse')
        return model
    
    def _prepare_data(self, data):
        features = ['glucose_level', 'carbs', 'insulin']
        X = data[features].values
        X = self.scaler.fit_transform(X)
        
        sequences = []
        for i in range(len(X) - 3):
            sequences.append(X[i:i+3])
        return np.array(sequences)
    
    def predict(self, data):
        if len(data) < 3:
            return []
            
        X = self._prepare_data(data)
        if len(X) == 0:
            return []
            
        predictions = []
        last_sequence = X[-1:]
        
        # Predict next 6 hours (hourly predictions)
        for _ in range(6):
            pred = self.model.predict(last_sequence)
            predictions.append(pred[0][0])
            
            # Update sequence for next prediction
            new_sequence = np.roll(last_sequence[0], -1)
            new_sequence[-1] = pred[0]
            last_sequence = new_sequence.reshape(1, 3, 3)
            
        # Inverse transform predictions
        predictions = np.array(predictions).reshape(-1, 1)
        predictions = self.scaler.inverse_transform(predictions)
        return predictions.flatten()
