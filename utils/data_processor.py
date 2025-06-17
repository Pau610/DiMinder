import pandas as pd
import numpy as np
from datetime import datetime, timedelta

class DataProcessor:
    def __init__(self):
        # Default parameters for insulin calculation
        self.carb_ratio = 15  # 1 unit per 15g carbs
        self.correction_factor = 50  # 1 unit reduces glucose by 50 mg/dL
        self.target_glucose = 120  # Target blood glucose level

    def calculate_insulin_dose(self, current_glucose, carbs):
        """Calculate recommended insulin dose based on current glucose and carbs"""
        # Carb coverage
        carb_dose = carbs / self.carb_ratio

        # Correction dose
        correction_dose = 0
        if current_glucose > self.target_glucose:
            correction_dose = (current_glucose - self.target_glucose) / self.correction_factor

        total_dose = carb_dose + correction_dose
        return max(0, round(total_dose, 1))

    def process_glucose_data(self, data):
        """Process and clean glucose data"""
        if data.empty:
            return pd.DataFrame()

        # Sort by timestamp
        data = data.sort_values('timestamp')

        # Remove duplicates
        data = data.drop_duplicates(subset=['timestamp'])

        # Fill missing values
        data['glucose_level'] = data['glucose_level'].fillna(method='ffill')
        data['carbs'] = data['carbs'].fillna(0)
        data['insulin'] = data['insulin'].fillna(0)

        # Fill new columns with default values if they don't exist
        if 'insulin_type' not in data.columns:
            data['insulin_type'] = ''
        if 'injection_site' not in data.columns:
            data['injection_site'] = ''

        return data

    def predict_insulin_needs(self, data, future_hours=24):
        """Predict future insulin needs based on historical patterns"""
        if len(data) < 24:  # Need at least 24 hours of data
            return []

        # Get recent data patterns
        hourly_insulin = data.set_index('timestamp').resample('h')['insulin'].mean()
        hourly_pattern = hourly_insulin.groupby(hourly_insulin.index.hour).mean()

        # Generate predictions
        predictions = []
        current_hour = datetime.now().hour

        for i in range(future_hours):
            hour = (current_hour + i) % 24
            predicted_insulin = hourly_pattern.get(hour, hourly_pattern.mean())
            predictions.append(predicted_insulin)

        return predictions

    def analyze_injection_sites(self, data):
        """Analyze insulin injection site rotation patterns"""
        if 'injection_site' not in data.columns or data.empty:
            return {}

        site_stats = data.groupby('injection_site').agg({
            'insulin': ['count', 'mean']
        }).round(1)

        return site_stats.to_dict()