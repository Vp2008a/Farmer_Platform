import pandas as pd
from prophet import Prophet
from datetime import datetime, timedelta
import os

def predict_price(commodity, district):
    """
    Predict future prices and return historical data using Prophet model
    """
    try:
        # Load the CSV file
        csv_path = os.path.join('farmprj', 'data', 'mandibhav.csv')
        df = pd.read_csv(csv_path)
        
        # Filter data for specific commodity and district
        mask = (df['Commodity'] == commodity) & (df['District'] == district)
        data = df[mask].copy()
        
        if len(data) < 10:  # Need minimum data points
            return None
            
        # Prepare data for Prophet
        data['ds'] = pd.to_datetime(data['Arrival_Date'], format='%d/%m/%Y')
        data['y'] = data['Modal_Price']
        
        # Sort data by date
        data = data.sort_values('ds')
        
        # Initialize and fit the model
        model = Prophet(yearly_seasonality=True, 
                       weekly_seasonality=True,
                       daily_seasonality=False)
        model.fit(data[['ds', 'y']])
        
        # Create future dates for prediction (next 30 days)
        future_dates = model.make_future_dataframe(periods=30)
        forecast = model.predict(future_dates)
        
        # Prepare the response with both historical and predicted data
        response = {
            'historical_data': [],
            'predicted_data': []
        }
        
        # Add historical data
        for _, row in data.iterrows():
            response['historical_data'].append({
                'date': row['ds'].strftime('%Y-%m-%d'),
                'price': float(row['y'])
            })
        
        # Add predictions (only for future dates)
        last_historical_date = data['ds'].max()
        
        for _, row in forecast.iterrows():
            if row['ds'] > last_historical_date:
                response['predicted_data'].append({
                    'date': row['ds'].strftime('%Y-%m-%d'),
                    'price': round(row['yhat'], 2),
                    'price_lower': round(row['yhat_lower'], 2),
                    'price_upper': round(row['yhat_upper'], 2)
                })
        
        return response
        
    except Exception as e:
        print(f"Prediction error: {e}")
        return None 