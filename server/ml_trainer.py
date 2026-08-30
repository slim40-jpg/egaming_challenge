# ml_trainer.py - Complete ML Training Pipeline
import json
import pickle
import numpy as np
import pandas as pd
from sklearn.tree import DecisionTreeClassifier
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.preprocessing import LabelEncoder, StandardScaler
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.tree import export_text, plot_tree
import matplotlib.pyplot as plt
import os
from datetime import datetime

class GameStateMLTrainer:
    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.label_encoder = LabelEncoder()
        self.feature_names = []
        self.model_file = 'game_state_model.pkl'
        self.training_stats = {}
        
    # ============================================================
    # FEATURE EXTRACTION
    # ============================================================
    
    def extract_features(self, telemetry_data):
        """Convert telemetry to feature vector"""
        features = {}
        
        # 1. Process name features (one-hot encoded)
        process = telemetry_data.get('process_name', 'unknown').lower()
        game_processes = [
            'fifa24.exe', 'fc24.exe', 'fifa.exe',
            'mugen.exe', 'mugen', 'dbz',
            'leagueoflegends.exe', 'lol.exe',
            'csgo.exe', 'valorant.exe',
            'rocketleague.exe', 'fortnite.exe'
        ]
        for proc in game_processes:
            features[f'process_{proc.replace(".exe", "").replace(" ", "_")}'] = 1 if proc in process else 0
        
        # 2. Window title features
        title = telemetry_data.get('window_title', '').lower()
        match_keywords = ['vs', 'match', 'goal', 'score', 'round', 'fight', 'versus', 'win', 'loss']
        for keyword in match_keywords:
            features[f'title_has_{keyword}'] = 1 if keyword in title else 0
        
        menu_keywords = ['menu', 'main menu', 'settings', 'options', 'lobby', 'queue']
        for keyword in menu_keywords:
            features[f'title_has_{keyword}'] = 1 if keyword in title else 0
        
        # 3. Numeric features
        features['cpu_usage'] = telemetry_data.get('cpu_usage', 0) / 100.0
        features['gpu_usage'] = telemetry_data.get('gpu_usage', 0) / 100.0
        features['ram_usage'] = telemetry_data.get('ram_usage', 0) / 100.0
        
        # 4. Resource ratios
        features['cpu_gpu_ratio'] = features['cpu_usage'] / (features['gpu_usage'] + 0.01)
        
        # 5. Boolean features
        features['is_fullscreen'] = 1 if telemetry_data.get('is_fullscreen', False) else 0
        features['has_active_window'] = 1 if telemetry_data.get('active_window', '') else 0
        
        return features
    
    # ============================================================
    # LOAD AND PREPARE DATA
    # ============================================================
    
    def load_training_data(self, data_file='training_data.json'):
        """Load training data from JSON file"""
        try:
            with open(data_file, 'r') as f:
                data = json.load(f)
            print(f"[ML] Loaded {len(data)} samples from {data_file}")
            return data
        except FileNotFoundError:
            print(f"[ML] No training data found. Please collect data first.")
            return []
    
    def prepare_data(self, training_data):
        """Convert training data to features and labels"""
        X = []
        y = []
        
        for item in training_data:
            features = self.extract_features(item['telemetry'])
            X.append(list(features.values()))
            y.append(item['label'])
        
        # Convert to numpy arrays
        X = np.array(X)
        y = np.array(y)
        
        # Store feature names
        self.feature_names = list(features.keys())
        
        return X, y
    
    # ============================================================
    # TRAIN MODEL
    # ============================================================
    
    def train(self, training_data, test_size=0.2):
        """
        Train Decision Tree Classifier with 80/20 split
        """
        print("\n" + "="*50)
        print("   TRAINING DECISION TREE CLASSIFIER")
        print("="*50)
        
        # Prepare data
        X, y = self.prepare_data(training_data)
        print(f"[ML] Total samples: {len(X)}")
        print(f"[ML] Features: {len(self.feature_names)}")
        print(f"[ML] Classes: {set(y)}")
        
        # Encode labels
        y_encoded = self.label_encoder.fit_transform(y)
        self.training_stats['classes'] = list(self.label_encoder.classes_)
        
        # Split data: 80% training, 20% testing
        X_train, X_test, y_train, y_test = train_test_split(
            X, y_encoded, test_size=test_size, random_state=42, stratify=y_encoded
        )
        
        print(f"\n[ML] Training samples: {len(X_train)} (80%)")
        print(f"[ML] Testing samples: {len(X_test)} (20%)")
        
        # Create Decision Tree Classifier
        self.model = DecisionTreeClassifier(
            max_depth=10,
            min_samples_split=5,
            min_samples_leaf=2,
            random_state=42,
            class_weight='balanced'
        )
        
        # Train the model
        self.model.fit(X_train, y_train)
        
        # Evaluate on test set
        y_pred = self.model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        
        # Store stats
        self.training_stats['accuracy'] = accuracy
        self.training_stats['train_size'] = len(X_train)
        self.training_stats['test_size'] = len(X_test)
        self.training_stats['total_samples'] = len(X)
        
        # Print results
        print(f"\n[ML] ✅ Model trained successfully!")
        print(f"[ML] 📊 Accuracy: {accuracy*100:.2f}%")
        
        # Detailed classification report
        print("\n" + "="*50)
        print("   CLASSIFICATION REPORT")
        print("="*50)
        print(classification_report(y_test, y_pred, target_names=self.label_encoder.classes_))
        
        # Confusion Matrix
        print("\n" + "="*50)
        print("   CONFUSION MATRIX")
        print("="*50)
        cm = confusion_matrix(y_test, y_pred)
        df_cm = pd.DataFrame(cm, index=self.label_encoder.classes_, columns=self.label_encoder.classes_)
        print(df_cm)
        
        # Feature Importance
        print("\n" + "="*50)
        print("   TOP 10 MOST IMPORTANT FEATURES")
        print("="*50)
        feature_importance = self.model.feature_importances_
        sorted_idx = np.argsort(feature_importance)[::-1]
        
        for i in range(min(10, len(self.feature_names))):
            idx = sorted_idx[i]
            print(f"  {i+1}. {self.feature_names[idx]}: {feature_importance[idx]*100:.1f}%")
        
        # Cross-validation
        cv_scores = cross_val_score(self.model, X, y_encoded, cv=5)
        print(f"\n[ML] Cross-validation (5-fold) scores: {cv_scores}")
        print(f"[ML] Mean CV accuracy: {cv_scores.mean()*100:.2f}%")
        
        self.training_stats['cv_scores'] = cv_scores.tolist()
        
        # Save model
        self.save_model()
        
        # Visualize tree (optional)
        self.visualize_tree()
        
        return accuracy
    
    # ============================================================
    # PREDICT
    # ============================================================
    
    def predict(self, telemetry_data):
        """Predict game state from telemetry data"""
        if self.model is None:
            return {'state': 'UNKNOWN', 'confidence': 0}
        
        features = self.extract_features(telemetry_data)
        X = np.array([list(features.values())])
        
        # Predict
        y_pred = self.model.predict(X)
        label = self.label_encoder.inverse_transform(y_pred)[0]
        
        # Get probability
        y_proba = self.model.predict_proba(X)
        confidence = max(y_proba[0])
        
        return {
            'state': label,
            'confidence': round(confidence * 100, 2),
            'features': features
        }
    
    # ============================================================
    # SAVE / LOAD MODEL
    # ============================================================
    
    def save_model(self):
        data = {
            'model': self.model,
            'feature_names': self.feature_names,
            'label_encoder': self.label_encoder,
            'scaler': self.scaler,
            'training_stats': self.training_stats,
            'date': datetime.now().isoformat()
        }
        with open(self.model_file, 'wb') as f:
            pickle.dump(data, f)
        print(f"\n[ML] 💾 Model saved to {self.model_file}")
    
    def load_model(self):
        try:
            with open(self.model_file, 'rb') as f:
                data = pickle.load(f)
                self.model = data['model']
                self.feature_names = data['feature_names']
                self.label_encoder = data['label_encoder']
                self.training_stats = data.get('training_stats', {})
            print(f"[ML] ✅ Model loaded from {self.model_file}")
            print(f"[ML] 📊 Last accuracy: {self.training_stats.get('accuracy', 0)*100:.2f}%")
            return True
        except:
            print(f"[ML] ❌ No model found. Please train first.")
            return False
    
    def visualize_tree(self):
        """Visualize the decision tree"""
        try:
            # Show tree structure as text
            tree_text = export_text(self.model, feature_names=self.feature_names, max_depth=3)
            print("\n" + "="*50)
            print("   DECISION TREE (First 3 levels)")
            print("="*50)
            print(tree_text)
        except:
            pass
    
    # ============================================================
    # GENERATE TRAINING DATA TEMPLATE
    # ============================================================
    
    def create_training_template(self):
        """Create a template for collecting training data"""
        template = {
            "training_data": [
                {
                    "telemetry": {
                        "process_name": "fifa24.exe",
                        "window_title": "FIFA 24 - Main Menu",
                        "cpu_usage": 15.5,
                        "gpu_usage": 10.2,
                        "ram_usage": 45.3,
                        "is_fullscreen": False,
                        "active_window": "FIFA 24"
                    },
                    "label": "MENU"
                },
                {
                    "telemetry": {
                        "process_name": "fifa24.exe",
                        "window_title": "FIFA 24 - Match - Real Madrid vs Barcelona",
                        "cpu_usage": 65.8,
                        "gpu_usage": 85.3,
                        "ram_usage": 62.1,
                        "is_fullscreen": True,
                        "active_window": "FIFA 24"
                    },
                    "label": "IN_MATCH"
                }
            ]
        }
        
        with open('training_data_template.json', 'w') as f:
            json.dump(template, f, indent=2)
        
        print("[ML] 📝 Created training_data_template.json")
        print("   Edit this file to add your own training data!")