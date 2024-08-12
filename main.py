from sklearn.model_selection import train_test_split
from sklearn.linear_model import LogisticRegression
from sklearn import metrics
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import classification_report
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns

from stock_utils import StockUtils

class StockPredictionModel:
    def __init__(self, training_symbols, testing_symbols, technical_indicators, outputsize=5000):
        self.training_symbols = training_symbols
        self.testing_symbols = testing_symbols
        self.technical_indicators = technical_indicators
        self.outputsize = outputsize
        self.model = None
        self.scaler = StandardScaler()
    
    def gather_stock_data(self, stock_symbols):
        """
        Combine stock data for all symbols into a single DataFrame.
        """
        combined_df = pd.DataFrame()
        for symbol in stock_symbols:
            stock_utils = StockUtils(symbol=symbol, outputsize=self.outputsize)
            df = stock_utils.get_indicators(self.technical_indicators)
            df['symbol'] = symbol  # Add a column to identify the stock
            combined_df = pd.concat([combined_df, df], ignore_index=True)
        return combined_df

    def prepare_training_data(self, df):
        """
        Prepare the training data by selecting relevant rows and setting the target variable.
        """
        data = df[(df['loc_min'] > 0) | (df['loc_max'] > 0)].reset_index(drop=True)
        data['target'] = [1 if x > 0 else 0 for x in data['loc_max']]
        data = data[self.technical_indicators + ['target']]
        return data.dropna(axis=0)

    def display_model_coefficients(self, model, feature_names, show_graph=False):
        """
        Display the coefficients of the trained model, optionally with a graphical representation.
        """
        feature_names = [f for f in feature_names if f != 'target']
        coefficients = model.coef_[0]
        coef_df = pd.DataFrame({'Feature': feature_names, 'Coefficient': coefficients})
        coef_df['Coefficient'] = coef_df['Coefficient'].round(3)
        print(coef_df[['Feature', 'Coefficient']])
        
        if show_graph:
            norm = plt.Normalize(coef_df['Coefficient'].min(), coef_df['Coefficient'].max())
            sm = plt.cm.ScalarMappable(cmap='coolwarm', norm=norm)
            coef_df['Color'] = coef_df['Coefficient'].apply(lambda x: sm.to_rgba(x))

            fig, ax = plt.subplots(figsize=(10, 6))
            coef_df.sort_values(by='Coefficient', ascending=False, inplace=True)
            bars = ax.barh(coef_df['Feature'], coef_df['Coefficient'], color=coef_df['Color'])
            ax.set_xlabel('Coefficient Value')
            ax.set_title('Feature Coefficients')

            cbar = plt.colorbar(sm, ax=ax)
            cbar.set_label('Coefficient Value')
            plt.show()

    def train_model(self, training_df, threshold=0.5, show_intercept=True, show_coefficients=True):
        """
        Train a logistic regression model on the training data.
        """
        X = training_df[self.technical_indicators]
        y = training_df['target']

        # Apply scaling to the features
        X = self.scaler.fit_transform(X)

        # Train on all available data
        model = LogisticRegression(random_state=16)
        model.fit(X, y)
        
        if show_intercept:
            print("Intercept:", round(model.intercept_[0], 3))

        if show_coefficients:
            self.display_model_coefficients(model, self.technical_indicators, show_graph=False)

        self.model = model
        return model

    def evaluate_model(self, df, threshold=0.001):
        """
        Evaluate the model on the entire DataFrame and add predictions.
        """
        df_clean = df.dropna(subset=self.technical_indicators)
        X = df_clean[self.technical_indicators]

        # Apply the same scaling to the test data
        X = self.scaler.transform(X)

        y_pred_proba = self.model.predict_proba(X)[:, 1]
        y_pred = (y_pred_proba >= threshold).astype(int)

        df_clean = df_clean.copy()  # Ensure we are working on a copy to avoid warnings
        df_clean['predicted_target'] = y_pred
        df_clean['predicted_probability'] = y_pred_proba

        df = df.merge(df_clean[['predicted_target', 'predicted_probability']], left_index=True, right_index=True, how='left')
        df = df.dropna(subset=['predicted_target', 'predicted_probability'])

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
        axs[index].scatter(minima_points['date'], minima_points['close'], marker='o', color="green", label="Predicted Minima (0)", s=50)
        axs[index].scatter(df['date'], df['loc_min'], marker='o', color="red", label="True Minima (0)", s=50)

        axs[index].set_xlabel("Date")
        axs[index].set_ylabel("Close (USD)")
        axs[index].legend()
        axs[index].set_title(f"Predictions for {stock_symbol}")
        axs[index].tick_params(axis='x', rotation=45)
        axs[index].grid(True)

    def run(self):
        """
        Run the complete pipeline: gather data, train the model, and visualize predictions.
        """
        combined_df = self.gather_stock_data(self.training_symbols)
        training_df = self.prepare_training_data(combined_df)
        self.train_model(training_df)

        fig, axs = plt.subplots(len(self.testing_symbols), 1, figsize=(12, 6 * len(self.testing_symbols)))

        if len(self.testing_symbols) == 1:
            axs = [axs]  # Ensure axs is iterable when there's only one subplot

        for index, symbol in enumerate(self.testing_symbols):
            print(f"Processing stock: {symbol}")
            stock_utils_new = StockUtils(symbol=symbol, outputsize=self.outputsize)
            df_new_stock = stock_utils_new.get_indicators(self.technical_indicators)
            df_predictions = self.evaluate_model(df_new_stock)
            self.plot_stock_predictions(axs, df_predictions, symbol, index)

        plt.tight_layout()
        plt.show()

# Example usage
training_symbols = ['AAPL', 'WMT', 'MSFT']
testing_symbols = ['GOOG', 'NFLX']
technical_indicators = ["normalized_value", "2_reg", "3_reg", "5_reg", "10_reg", "20_reg", "50_reg", "adx", "ema", "sma"]

model = StockPredictionModel(training_symbols, testing_symbols, technical_indicators, outputsize=2000)
model.run()

# # List of technical indicators to fetch
# technical_indicators = ["normalized_value", "2_reg", "3_reg", "5_reg", "10_reg", "20_reg", "50_reg", "adx", "ema", "sma"]

# # Instantiate the StockUtils class
# stock_utils = StockUtils(symbol='AAPL', outputsize=2000)

# # Fetch the desired indicators
# df_stock_indicators = stock_utils.get_indicators(technical_indicators)

# # Display the fetched data
# print(df_stock_indicators)

# stock_utils.plot_graph()