import pandas as pd
import numpy as np

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
        
        return data
