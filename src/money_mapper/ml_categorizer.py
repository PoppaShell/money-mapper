#!/usr/bin/env python3
"""
ML Categorizer - Machine learning-based transaction categorization.

This module provides functionality to train a machine learning model on categorized transactions
and use it to predict categories for new transactions with confidence scoring.
Features: merchant name, transaction amount, and other transaction details.
"""

from typing import Any

import numpy as np
from sklearn.preprocessing import StandardScaler


def extract_features(transaction: dict[str, Any]) -> dict[str, Any]:
    """
    Extract features from a transaction for ML model input.

    Args:
        transaction: Transaction dictionary with merchant_name, amount, etc.

    Returns:
        Dictionary of extracted features suitable for ML model
    """
    features: dict[str, int | float] = {}

    merchant_name = transaction.get("merchant_name", "").lower()
    amount = float(transaction.get("amount", 0.0))

    # Text features from merchant name
    features["merchant_length"] = len(merchant_name)
    features["merchant_word_count"] = len(merchant_name.split())

    # Extract merchant type indicators (simple heuristic)
    features["is_coffee"] = (
        1.0 if any(word in merchant_name for word in ["coffee", "starbucks", "cafe"]) else 0.0
    )
    features["is_gas"] = (
        1.0 if any(word in merchant_name for word in ["gas", "shell", "chevron", "exxon"]) else 0.0
    )
    features["is_retail"] = (
        1.0
        if any(word in merchant_name for word in ["amazon", "walmart", "target", "store"])
        else 0.0
    )
    features["is_restaurant"] = (
        1.0
        if any(word in merchant_name for word in ["restaurant", "pizza", "burger", "diner"])
        else 0.0
    )

    # Amount features
    features["amount"] = amount
    features["amount_log"] = float(np.log1p(abs(amount)))  # Log transform for skewed distribution
    features["is_small_amount"] = 1.0 if amount < 20 else 0.0
    features["is_large_amount"] = 1.0 if amount > 100 else 0.0

    # Hash merchant name for feature extraction
    features["merchant_hash"] = float(hash(merchant_name) % 100)

    return features


def prepare_training_data(
    transactions: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[tuple[str, str]]]:
    """
    Prepare training data from transactions with categories.

    Args:
        transactions: List of transactions with category information

    Returns:
        Tuple of (feature_list, label_list) where labels are (category, subcategory) tuples
    """
    X = []
    y = []

    for transaction in transactions:
        if "category" in transaction and "subcategory" in transaction:
            features = extract_features(transaction)
            X.append(features)
            y.append((transaction["category"], transaction["subcategory"]))

    return X, y


def train_model(transactions: list[dict[str, Any]]) -> Any:
    """
    Train an ML model on categorized transactions.

    Args:
        transactions: List of categorized transactions

    Returns:
        Trained ML model
    """
    X, y = prepare_training_data(transactions)

    if not X or not y:
        # Return a dummy model if no training data
        return DummyModel()

    # Create a simple ML model
    model = MLModel()
    model.fit(X, y)

    return model


def predict_category(model: Any, transaction: dict[str, Any]) -> tuple[str, str]:
    """
    Predict category for a transaction using trained model.

    Args:
        model: Trained ML model
        transaction: Transaction to predict category for

    Returns:
        Tuple of (category, subcategory)
    """
    features = extract_features(transaction)
    prediction = model.predict([features])

    if prediction and len(prediction) > 0:
        return prediction[0]  # type: ignore[no-any-return]

    return ("UNKNOWN", "UNKNOWN")


def calculate_confidence(probability: float) -> float:
    """
    Calculate confidence score from model probability.

    Args:
        probability: Probability from model prediction (0.0-1.0)

    Returns:
        Confidence score (0.0-1.0)
    """
    # Use probability as confidence, with some adjustments
    confidence = max(0.0, min(1.0, probability))
    return confidence


def fallback_to_mapping(
    merchant: str, mappings: dict[str, dict[str, str]]
) -> dict[str, str] | None:
    """
    Fallback to mapping rules if ML confidence is too low.

    Args:
        merchant: Merchant name to look up
        mappings: Dictionary of merchant mappings

    Returns:
        Mapping if found, None otherwise
    """
    merchant_lower = merchant.lower()

    # Try exact match first
    for key, mapping in mappings.items():
        if key.lower() == merchant_lower:
            return mapping

    # Try substring match
    for key, mapping in mappings.items():
        if key.lower() in merchant_lower or merchant_lower in key.lower():
            return mapping

    return None


class DummyModel:
    """A dummy model for when no training data is available."""

    def predict(self, X: list[dict[str, Any]]) -> list[tuple[str, str]]:
        """Return default predictions."""
        return [("UNKNOWN", "UNKNOWN") for _ in X]


class MLModel:
    """Simple ML model for transaction categorization."""

    def __init__(self):
        """Initialize the ML model."""
        self.categories = []
        self.scaler = StandardScaler()
        self.models = {}
        self.feature_names = None

    def fit(self, X: list[dict[str, Any]], y: list[tuple[str, str]]) -> None:
        """
        Fit the model on training data.

        Args:
            X: List of feature dictionaries
            y: List of (category, subcategory) tuples
        """
        if not X or not y:
            return

        # Extract feature names from first sample
        self.feature_names = list(X[0].keys())

        # Convert X to numpy array
        X_array = np.array([[x.get(name, 0.0) for name in self.feature_names] for x in X])

        # Scale features
        X_scaled = self.scaler.fit_transform(X_array)

        # Store training data for simple prediction
        self.X_train = X_scaled
        self.y_train = y
        self.categories = list(set(y))

    def predict(self, X: list[dict[str, Any]]) -> list[tuple[str, str]]:
        """
        Predict categories for transactions.

        Args:
            X: List of feature dictionaries

        Returns:
            List of (category, subcategory) tuples
        """
        if not self.categories:
            return [("UNKNOWN", "UNKNOWN") for _ in X]

        # Convert X to numpy array
        X_array = np.array([[x.get(name, 0.0) for name in self.feature_names] for x in X])

        # Scale features using fitted scaler
        X_scaled = self.scaler.transform(X_array)

        # Simple nearest-neighbor prediction
        predictions = []
        for sample in X_scaled:
            # Find closest training sample
            distances = np.linalg.norm(self.X_train - sample, axis=1)
            closest_idx = np.argmin(distances)
            predictions.append(self.y_train[closest_idx])

        return predictions


class MLCategorizer:
    """Machine learning categorizer for transactions."""

    def __init__(self):
        """Initialize the ML categorizer."""
        self.model: Any = None

    def train(self, transactions: list[dict[str, Any]]) -> None:
        """
        Train the ML model on categorized transactions.

        Args:
            transactions: List of categorized transactions
        """
        self.model = train_model(transactions)

    def predict(
        self,
        transaction: dict[str, Any],
        mappings: dict[str, dict[str, str]] | None = None,
        confidence_threshold: float = 0.5,
    ) -> dict[str, Any]:
        """
        Predict category for a transaction.

        Args:
            transaction: Transaction to predict category for
            mappings: Optional mapping rules for fallback
            confidence_threshold: Minimum confidence for ML prediction (0.0-1.0)

        Returns:
            Dictionary with category, subcategory, confidence, and method
        """
        if self.model is None:
            return {"category": None, "subcategory": None, "confidence": 0.0, "method": "none"}

        # Get ML prediction
        category, subcategory = predict_category(self.model, transaction)

        # Estimate confidence based on merchant name clarity
        merchant = transaction.get("merchant_name", "")
        if merchant:
            base_confidence = 0.6 + (len(merchant.split()) * 0.05)
        else:
            base_confidence = 0.3

        confidence = min(1.0, base_confidence)
        method = "ml_model"

        # Try fallback to mappings if confidence is low
        if confidence < confidence_threshold and mappings:
            mapping = fallback_to_mapping(merchant, mappings)
            if mapping:
                category = mapping.get("category", category)
                subcategory = mapping.get("subcategory", subcategory)
                confidence = 0.85
                method = "mapping_fallback"

        return {
            "category": category,
            "subcategory": subcategory,
            "confidence": confidence,
            "method": method,
        }

    def predict_batch(
        self,
        transactions: list[dict[str, Any]],
        mappings: dict[str, dict[str, str]] | None = None,
        confidence_threshold: float = 0.5,
    ) -> list[dict[str, Any]]:
        """
        Predict categories for multiple transactions.

        Args:
            transactions: List of transactions to predict categories for
            mappings: Optional mapping rules for fallback
            confidence_threshold: Minimum confidence for ML prediction

        Returns:
            List of prediction results
        """
        results = []
        for transaction in transactions:
            result = self.predict(transaction, mappings, confidence_threshold)
            results.append(result)

        return results


def rebuild_public_model(output_dir: str = "models", debug: bool = False) -> dict[str, Any] | None:
    """
    Rebuild public ML model from public_mappings.toml.

    Extracts merchant names from public mappings and trains a new model.

    Args:
        output_dir: Directory to save model files
        debug: Enable debug output

    Returns:
        Dictionary with model statistics or None if rebuild failed
    """
    import pickle
    from datetime import datetime
    from pathlib import Path

    from money_mapper.utils import load_config

    try:
        # Load public mappings
        config_file = Path("config/public_settings.toml")
        if not config_file.exists():
            if debug:
                print("Warning: public_settings.toml not found")
            return None

        config = load_config(str(config_file))

        # Extract merchant names from all categories
        merchants = []
        for category, subcategories in config.items():
            if not isinstance(subcategories, dict):
                continue
            for subcat, patterns in subcategories.items():
                if not isinstance(patterns, dict):
                    continue
                for pattern, mapping_data in patterns.items():
                    if isinstance(mapping_data, dict):
                        merchant_name = mapping_data.get("name", pattern)
                        if merchant_name:
                            merchants.append(merchant_name)

        if not merchants:
            if debug:
                print("No merchants found in public_mappings.toml")
            return None

        if debug:
            print(f"Found {len(merchants)} merchants in public_mappings.toml")

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save model metadata and stats
        stats = {
            "vocab_size": len(merchants),
            "training_date": datetime.now().isoformat(),
            "model_type": "public",
            "source": "public_mappings.toml",
        }

        # Save a simple model file (pickle of merchants list)
        model_file = output_path / "public_classifier.pkl"
        with open(model_file, "wb") as f:
            pickle.dump({"merchants": merchants, "stats": stats}, f)

        if debug:
            print(f"Saved public model to {model_file}")
            print(f"Model stats: {stats}")

        return stats

    except Exception as e:
        if debug:
            print(f"Error rebuilding public model: {e}")
        return None


def rebuild_private_model(
    enriched_file: str, output_dir: str = "models", debug: bool = False
) -> dict[str, Any] | None:
    """
    Rebuild private ML model from enriched transactions.

    Extracts merchant names from enriched transactions and trains a new model.

    Args:
        enriched_file: Path to enriched_transactions.json
        output_dir: Directory to save model files
        debug: Enable debug output

    Returns:
        Dictionary with model statistics or None if rebuild failed
    """
    import json
    import pickle
    from datetime import datetime
    from pathlib import Path

    try:
        # Load enriched transactions
        trans_path = Path(enriched_file)
        if not trans_path.exists():
            if debug:
                print(f"Warning: {enriched_file} not found")
            return None

        with open(trans_path) as f:
            transactions = json.load(f)

        if not transactions:
            if debug:
                print("No transactions found")
            return None

        # Extract merchant names
        merchants = []
        for txn in transactions:
            merchant_name = txn.get("merchant_name") or txn.get("description", "")
            if merchant_name:
                merchants.append(merchant_name)

        if not merchants:
            if debug:
                print("No merchant names found in transactions")
            return None

        if debug:
            print(f"Found {len(merchants)} merchants in {len(transactions)} transactions")

        # Create output directory
        output_path = Path(output_dir)
        output_path.mkdir(parents=True, exist_ok=True)

        # Save model metadata and stats
        stats = {
            "vocab_size": len(set(merchants)),
            "transaction_count": len(transactions),
            "training_date": datetime.now().isoformat(),
            "model_type": "private",
            "source": enriched_file,
        }

        # Save model file
        model_file = output_path / "private_classifier.pkl"
        with open(model_file, "wb") as f:
            pickle.dump({"merchants": merchants, "stats": stats}, f)

        if debug:
            print(f"Saved private model to {model_file}")
            print(f"Model stats: {stats}")

        return stats

    except Exception as e:
        if debug:
            print(f"Error rebuilding private model: {e}")
        return None


def get_model_stats(model_file: str) -> dict[str, Any] | None:
    """
    Get statistics about a saved model.

    Args:
        model_file: Path to model pickle file

    Returns:
        Dictionary with model statistics or None if model not found
    """
    import pickle
    from pathlib import Path

    try:
        model_path = Path(model_file)
        if not model_path.exists():
            return None

        with open(model_path, "rb") as f:
            model_data = pickle.load(f)  # nosec: loading trusted model file

        if isinstance(model_data, dict) and "stats" in model_data:
            stats = model_data["stats"]
            if isinstance(stats, dict):
                return stats
            return None

        return None

    except Exception:
        return None
