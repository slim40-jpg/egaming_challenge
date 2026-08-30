# train.py - Train hierarchical match end detection model
import pandas as pd
import os
from game_state_model import GameStateClassifier

def find_dataset_file():
    """Find the dataset file in various locations"""
    print("\n🔍 Searching for dataset file...")
    
    possible_names = [
        'general_match_end_dataset_5000.csv',
        'general_match_end_dataset.csv',
        'match_end_dataset.csv',
        'game_state_dataset.csv',
    ]
    
    search_paths = [
        '.', '..', '../..', 'server', '../server', '../../server',
        'data', '../data',
        os.path.dirname(__file__),
        os.path.join(os.path.dirname(__file__), '..'),
        os.path.join(os.path.dirname(__file__), 'data'),
    ]
    
    for path in search_paths:
        for name in possible_names:
            filepath = os.path.join(path, name)
            if os.path.exists(filepath):
                print(f"✅ Found dataset: {filepath}")
                return filepath
    
    # Try to find any CSV with match_ended
    print("\n🔍 Searching for any CSV with 'match_ended' column...")
    for path in search_paths:
        if os.path.exists(path):
            for file in os.listdir(path):
                if file.endswith('.csv'):
                    filepath = os.path.join(path, file)
                    try:
                        df = pd.read_csv(filepath, nrows=5)
                        if 'match_ended' in df.columns:
                            print(f"✅ Found dataset with match_ended: {filepath}")
                            return filepath
                    except:
                        continue
    return None

def generate_synthetic_data():
    """Generate synthetic training data for demonstration"""
    print("\n" + "="*60)
    print("   GENERATING SYNTHETIC DATA")
    print("="*60)
    
    import numpy as np
    np.random.seed(42)
    num_samples = 2000
    data = []
    
    for i in range(num_samples):
        match_ended = 1 if np.random.random() < 0.4 else 0
        
        if match_ended:
            gpu_delta_1s = np.random.uniform(-40, -10)
            gpu_delta_3s = np.random.uniform(-60, -20)
            gpu_delta_5s = np.random.uniform(-80, -30)
            gpu_derivative = np.random.uniform(-30, -10)
            gpu_drop_ratio = np.random.uniform(0.4, 0.9)
            gpu_variance = np.random.uniform(150, 500)
            cpu_delta_1s = np.random.uniform(-25, -5)
            cpu_delta_3s = np.random.uniform(-35, -10)
            cpu_delta_5s = np.random.uniform(-45, -15)
            cpu_derivative = np.random.uniform(-25, -5)
            cpu_drop_ratio = np.random.uniform(0.2, 0.6)
            cpu_variance = np.random.uniform(50, 400)
            ram_delta_1s = np.random.uniform(-80, -20)
            ram_delta_5s = np.random.uniform(-150, -50)
            ram_growth_rate = np.random.uniform(-60, -20)
            ram_variance = np.random.uniform(1000, 6000)
            activity_drop_score = np.random.uniform(60, 100)
            stable_after_drop = 1
            fullscreen_changed = 1
        else:
            gpu_delta_1s = np.random.uniform(-5, 15)
            gpu_delta_3s = np.random.uniform(-10, 10)
            gpu_delta_5s = np.random.uniform(-15, 10)
            gpu_derivative = np.random.uniform(-5, 5)
            gpu_drop_ratio = np.random.uniform(0, 0.3)
            gpu_variance = np.random.uniform(20, 150)
            cpu_delta_1s = np.random.uniform(-5, 15)
            cpu_delta_3s = np.random.uniform(-10, 10)
            cpu_delta_5s = np.random.uniform(-15, 10)
            cpu_derivative = np.random.uniform(-5, 5)
            cpu_drop_ratio = np.random.uniform(0, 0.2)
            cpu_variance = np.random.uniform(10, 100)
            ram_delta_1s = np.random.uniform(-20, 40)
            ram_delta_5s = np.random.uniform(-30, 50)
            ram_growth_rate = np.random.uniform(-10, 20)
            ram_variance = np.random.uniform(100, 2000)
            activity_drop_score = np.random.uniform(0, 40)
            stable_after_drop = 0
            fullscreen_changed = 0
        
        data.append({
            'gpu_delta_1s_pp': gpu_delta_1s,
            'gpu_delta_3s_pp': gpu_delta_1s + np.random.uniform(-5, 5),
            'gpu_delta_5s_pp': gpu_delta_1s + np.random.uniform(-10, 5),
            'gpu_derivative_pp_s': gpu_derivative,
            'gpu_drop_ratio': gpu_drop_ratio,
            'gpu_variance_5s': gpu_variance,
            'cpu_delta_1s_pp': cpu_delta_1s,
            'cpu_delta_3s_pp': cpu_delta_1s + np.random.uniform(-5, 5),
            'cpu_delta_5s_pp': cpu_delta_1s + np.random.uniform(-10, 5),
            'cpu_derivative_pp_s': cpu_derivative,
            'cpu_drop_ratio': cpu_drop_ratio,
            'cpu_variance_5s': cpu_variance,
            'ram_delta_1s_mb': ram_delta_1s,
            'ram_delta_5s_mb': ram_delta_1s + np.random.uniform(-30, 30),
            'ram_growth_rate_mb_s': ram_growth_rate,
            'ram_variance_5s': ram_variance,
            'resource_sync_score': np.random.uniform(0.3, 0.9),
            'activity_drop_score': activity_drop_score,
            'stable_after_drop': stable_after_drop,
            'window_seconds': np.random.randint(3, 11),
            'foreground_changed': np.random.randint(0, 2),
            'fullscreen_changed': fullscreen_changed,
            'match_ended': match_ended
        })
    
    df = pd.DataFrame(data)
    output_file = 'synthetic_match_end_data.csv'
    df.to_csv(output_file, index=False)
    print(f"✅ Generated {len(df)} synthetic samples -> {output_file}")
    return df

def main():
    print("\n" + "="*60)
    print("   🧠 HIERARCHICAL MATCH END DETECTOR - TRAINING")
    print("="*60)
    
    # Initialize classifier (will try to load existing model)
    classifier = GameStateClassifier()
    
    # Find dataset
    dataset_file = find_dataset_file()
    
    if dataset_file is None:
        print("\n❌ Dataset file not found!")
        print("\n📁 Searching in these locations:")
        print("   - Current directory")
        print("   - Parent directory")
        print("   - Server directory")
        print("   - Data directory")
        
        print("\n📊 Would you like to generate synthetic data instead? (y/n)")
        choice = input().strip().lower()
        if choice in ['y', 'yes']:
            df = generate_synthetic_data()
            dataset_file = 'synthetic_match_end_data.csv'
        else:
            print("\n❌ Training cancelled.")
            return
    
    # Train the hierarchical model
    print("\n🚀 Starting hierarchical training...")
    try:
        # Remove old model file to avoid confusion
        old_model = 'game_state_model.pkl'
        if os.path.exists(old_model):
            os.remove(old_model)
            print(f"🗑️ Removed old model file: {old_model}")
        
        classifier.train_from_csv(dataset_file)
        print("\n" + "="*60)
        print("   ✅ TRAINING COMPLETE!")
        print("="*60)
        print(f"   Model saved to: {classifier.model_file}")
        print("   Categories: heavy, medium, light")
        print("   First node: Decision Tree (category)")
        print("   Second node: RandomForest per category (match state)")
    except Exception as e:
        print(f"❌ Training failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()