import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from stock_prediction.data_handling import StockUtils

class ModelPredictor:
    def __init__(self, model, scaler, testing_symbols, technical_indicators, params):
        """
        Initialize the ModelPredictor class.
        
        Args:
        - model: Trained ML model.
        - testing_symbols: List of stock symbols for testing.
        - technical_indicators: List of technical indicators to use.
        - params: Dictionary of parameters including 'outputsize', 'min_max_order', 'min_threshold',
                  'max_threshold', and 'window_size'.
        """
        self.model = model
        self.scaler = scaler
        self.testing_symbols = testing_symbols
        self.technical_indicators = technical_indicators

        self.outputsize = params.get('outputsize', 5000)
        self.min_max_order = params.get('min_max_order', 5)
        self.min_threshold = params.get('min_threshold', 0.00001)
        self.max_threshold = params.get('max_threshold', 0.99999)
        self.window_size = params.get('window_size', 5)

    def evaluate_model(self, df):
        """
        Evaluate the model on the entire DataFrame and add predictions.
        """
        df_clean = df.dropna(subset=self.technical_indicators)
        X = df_clean[self.technical_indicators]

        # Apply the same scaling to the test data
        X = self.scaler.fit_transform(X)

        y_pred_proba = self.model.predict_proba(X)[:, 1]

        y_pred = -1 * np.ones_like(y_pred_proba)

        y_pred[y_pred_proba < self.min_threshold] = 0
        y_pred[y_pred_proba > self.max_threshold] = 1

        df_clean = df_clean.copy()
        df_clean['predicted_target'] = y_pred
        df_clean['predicted_probability'] = y_pred_proba

        df = df.merge(df_clean[['predicted_target', 'predicted_probability']], left_index=True, right_index=True, how='left')
        df = df.dropna(subset=['predicted_target', 'predicted_probability'])

        return df

    def filter_predictions(self, df):
        """
        Modify predicted minima and maxima that are too close to each other by setting them to neutral.
        """
        df = df.sort_values(by='date').reset_index(drop=True)

        last_minima_idx = -self.window_size - 1
        last_maxima_idx = -self.window_size - 1

        for idx, row in df.iterrows():
            if row['predicted_target'] == 0:
                if idx - last_minima_idx > self.window_size:
                    last_minima_idx = idx
                else:
                    df.at[idx, 'predicted_target'] = -1  # Set to neutral

            elif row['predicted_target'] == 1:
                if idx - last_maxima_idx > self.window_size:
                    last_maxima_idx = idx
                else:
                    df.at[idx, 'predicted_target'] = -1  # Set to neutral

        return df

    def plot_stock_predictions(self, axs, df, stock_symbol, index):
        """
        Plot the stock price and predictions for a given stock symbol.
        """
        df['date'] = pd.to_datetime(df['date'], format='%d/%m/%Y')
        x = df['date']
        y = df["close"]
        axs[index].plot(x, y, ls='-', color="black", label=f"{stock_symbol} Daily")

        minima_points = df[df['predicted_target'] == 0]
        axs[index].scatter(minima_points['date'], minima_points['close'], marker='o', color="green", label="Predicted Minima", s=50)

        maxima_points = df[df['predicted_target'] == 1]
        axs[index].scatter(maxima_points['date'], maxima_points['close'], marker='o', color="blue", label="Predicted Maxima", s=50)

        axs[index].scatter(df['date'], df.get('loc_min', pd.Series()), marker='x', color="red", label="True Minima", s=20)
        axs[index].scatter(df['date'], df.get('loc_max', pd.Series()), marker='x', color="orange", label="True Maxima", s=20)

        axs[index].set_xlabel("Date")
        axs[index].set_ylabel("Close (USD)")
        axs[index].legend()
        axs[index].set_title(f"Predictions for {stock_symbol}")
        axs[index].tick_params(axis='x', rotation=45)
        axs[index].grid(True)
    
    def test(self, plot_graph=False):
        """
        High-level method to evaluate the model on test data and optionally plot the results.
        """
        fig, axs = plt.subplots(len(self.testing_symbols), 1, figsize=(12, 6 * len(self.testing_symbols)))

        if len(self.testing_symbols) == 1:
            axs = [axs]  # Ensure axs is iterable when there's only one subplot

        for index, symbol in enumerate(self.testing_symbols):
            print(f"Processing stock: {symbol}")
            stock_utils_new = StockUtils(symbol=symbol)
            df_new_stock = stock_utils_new.get_indicators(
                self.technical_indicators, 
                outputsize=self.outputsize,
                min_max_order=self.min_max_order
            )
            df_predictions = self.evaluate_model(df_new_stock)
            df_predictions = self.filter_predictions(df_predictions)

            if plot_graph:
                self.plot_stock_predictions(axs, df_predictions, symbol, index)

        if plot_graph:
            plt.tight_layout()
            plt.show()

        return df_predictions