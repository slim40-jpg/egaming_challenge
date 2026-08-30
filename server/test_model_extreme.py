# test_model_extreme.py - Extreme test for hierarchical match end detector
import json
import random
import numpy as np
from game_state_model import GameStateClassifier

def generate_extreme_telemetry(scenario_type):
    """
    Generate extreme test scenarios to stress-test the model
    """
    base_telemetry = {
        'resource_sync_score': 0.5,
        'gpu_drop_ratio': 0.0,
        'activity_drop_score': 25.0,
        'cpu_drop_ratio': 0.0,
        'gpu_delta_1s_pp': 0.0,
        'gpu_derivative_pp_s': 0.0,
        'gpu_delta_5s_pp': 0.0,
        'gpu_delta_3s_pp': 0.0,
        'stable_after_drop': 0,
        'cpu_variance_5s': 50.0,
        'fullscreen_changed': 0,
        'foreground_changed': 0,
        'window_seconds': 5,
        'ram_variance_5s': 500.0,
        'ram_growth_rate_mb_s': 0.0,
        'ram_delta_5s_mb': 0.0,
        'ram_delta_1s_mb': 0.0,
        'cpu_delta_5s_pp': 0.0,
        'cpu_delta_3s_pp': 0.0,
        'cpu_delta_1s_pp': 0.0
    }
    
    telemetry = base_telemetry.copy()
    
    if scenario_type == "extreme_match":
        # Extreme match: very high GPU, stable
        telemetry.update({
            'gpu_delta_1s_pp': random.uniform(2, 15),
            'gpu_delta_3s_pp': random.uniform(0, 20),
            'gpu_delta_5s_pp': random.uniform(-5, 25),
            'gpu_derivative_pp_s': random.uniform(0, 10),
            'gpu_drop_ratio': random.uniform(0.01, 0.15),
            'gpu_variance_5s': random.uniform(100, 250),
            'cpu_delta_1s_pp': random.uniform(0, 10),
            'cpu_delta_3s_pp': random.uniform(-5, 15),
            'cpu_delta_5s_pp': random.uniform(-10, 20),
            'cpu_derivative_pp_s': random.uniform(0, 8),
            'cpu_drop_ratio': random.uniform(0.01, 0.10),
            'cpu_variance_5s': random.uniform(20, 80),
            'ram_delta_1s_mb': random.uniform(5, 30),
            'ram_delta_5s_mb': random.uniform(10, 50),
            'ram_growth_rate_mb_s': random.uniform(2, 20),
            'ram_variance_5s': random.uniform(300, 1200),
            'resource_sync_score': random.uniform(0.7, 0.95),
            'activity_drop_score': random.uniform(5, 30),
            'stable_after_drop': 0,
            'window_seconds': random.randint(5, 10),
            'fullscreen_changed': 0,
            'foreground_changed': 0
        })
        
    elif scenario_type == "extreme_drop":
        # Extreme GPU drop (match ended)
        telemetry.update({
            'gpu_delta_1s_pp': random.uniform(-50, -20),
            'gpu_delta_3s_pp': random.uniform(-80, -30),
            'gpu_delta_5s_pp': random.uniform(-100, -40),
            'gpu_derivative_pp_s': random.uniform(-40, -15),
            'gpu_drop_ratio': random.uniform(0.6, 0.95),
            'gpu_variance_5s': random.uniform(300, 600),
            'cpu_delta_1s_pp': random.uniform(-30, -8),
            'cpu_delta_3s_pp': random.uniform(-45, -12),
            'cpu_delta_5s_pp': random.uniform(-55, -15),
            'cpu_derivative_pp_s': random.uniform(-25, -5),
            'cpu_drop_ratio': random.uniform(0.35, 0.75),
            'cpu_variance_5s': random.uniform(100, 300),
            'ram_delta_1s_mb': random.uniform(-80, -20),
            'ram_delta_5s_mb': random.uniform(-200, -50),
            'ram_growth_rate_mb_s': random.uniform(-60, -15),
            'ram_variance_5s': random.uniform(1500, 6000),
            'resource_sync_score': random.uniform(0.6, 0.85),
            'activity_drop_score': random.uniform(60, 100),
            'stable_after_drop': 1,
            'window_seconds': random.randint(3, 6),
            'fullscreen_changed': 1,
            'foreground_changed': 0
        })
        
    elif scenario_type == "extreme_menu":
        # Menu/low activity
        telemetry.update({
            'gpu_delta_1s_pp': random.uniform(-15, 5),
            'gpu_delta_3s_pp': random.uniform(-20, 10),
            'gpu_delta_5s_pp': random.uniform(-25, 15),
            'gpu_derivative_pp_s': random.uniform(-10, 8),
            'gpu_drop_ratio': random.uniform(0.3, 0.6),
            'gpu_variance_5s': random.uniform(50, 200),
            'cpu_delta_1s_pp': random.uniform(-10, 5),
            'cpu_delta_3s_pp': random.uniform(-15, 10),
            'cpu_delta_5s_pp': random.uniform(-20, 15),
            'cpu_derivative_pp_s': random.uniform(-8, 5),
            'cpu_drop_ratio': random.uniform(0.15, 0.4),
            'cpu_variance_5s': random.uniform(20, 80),
            'ram_delta_1s_mb': random.uniform(-20, 15),
            'ram_delta_5s_mb': random.uniform(-40, 30),
            'ram_growth_rate_mb_s': random.uniform(-15, 10),
            'ram_variance_5s': random.uniform(200, 800),
            'resource_sync_score': random.uniform(0.2, 0.5),
            'activity_drop_score': random.uniform(20, 50),
            'stable_after_drop': 0,
            'window_seconds': random.randint(8, 12),
            'fullscreen_changed': 0,
            'foreground_changed': 1
        })
        
    elif scenario_type == "extreme_loading":
        # Loading screen (spikes)
        telemetry.update({
            'gpu_delta_1s_pp': random.uniform(-15, 30),
            'gpu_delta_3s_pp': random.uniform(-25, 50),
            'gpu_delta_5s_pp': random.uniform(-35, 60),
            'gpu_derivative_pp_s': random.uniform(-12, 25),
            'gpu_drop_ratio': random.uniform(0.1, 0.4),
            'gpu_variance_5s': random.uniform(100, 400),
            'cpu_delta_1s_pp': random.uniform(-10, 25),
            'cpu_delta_3s_pp': random.uniform(-15, 40),
            'cpu_delta_5s_pp': random.uniform(-20, 50),
            'cpu_derivative_pp_s': random.uniform(-8, 20),
            'cpu_drop_ratio': random.uniform(0.05, 0.25),
            'cpu_variance_5s': random.uniform(30, 150),
            'ram_delta_1s_mb': random.uniform(-30, 50),
            'ram_delta_5s_mb': random.uniform(-60, 100),
            'ram_growth_rate_mb_s': random.uniform(-20, 40),
            'ram_variance_5s': random.uniform(500, 2500),
            'resource_sync_score': random.uniform(0.3, 0.6),
            'activity_drop_score': random.uniform(30, 60),
            'stable_after_drop': 0,
            'window_seconds': random.randint(4, 8),
            'fullscreen_changed': 0,
            'foreground_changed': 1
        })
    
    return telemetry

def main():
    print("="*60)
    print("   🚀 EXTREME TEST - HIERARCHICAL MATCH DETECTOR")
    print("="*60)
    
    # Load the hierarchical model
    classifier = GameStateClassifier()
    if not classifier.load_model():
        print("❌ Model not loaded. Please train first.")
        return
    
    print("\n📊 Model loaded successfully!")
    print(f"   Categories: {list(classifier.match_models.keys())}")
    if classifier.category_model:
        print(f"   Category model: DecisionTree (features: {len(classifier.category_feature_names)})")
    print()
    
    # Test scenarios
    scenarios = [
        "extreme_match",
        "extreme_drop",
        "extreme_menu",
        "extreme_loading"
    ]
    
    scenario_names = {
        "extreme_match": "🎯 EXTREME MATCH (High GPU, Stable)",
        "extreme_drop": "💥 EXTREME DROP (Match Ended!)",
        "extreme_menu": "📋 EXTREME MENU (Low Activity)",
        "extreme_loading": "🔄 EXTREME LOADING (Spikes)"
    }
    
    expected_states = {
        "extreme_match": "IN_MATCH",
        "extreme_drop": "POST_MATCH",
        "extreme_menu": "IN_MATCH",
        "extreme_loading": "IN_MATCH"
    }
    
    print("📊 Testing Extreme Scenarios:\n")
    print("="*60)
    
    results = {
        'total': 0,
        'correct': 0,
        'by_scenario': {}
    }
    
    # Test each scenario multiple times with variations
    for scenario in scenarios:
        print(f"\n📌 {scenario_names[scenario]}")
        print(f"   Expected: {expected_states[scenario]}")
        print("-" * 40)
        
        scenario_correct = 0
        scenario_total = 20  # Test 20 variations per scenario
        
        for i in range(scenario_total):
            telemetry = generate_extreme_telemetry(scenario)
            
            try:
                result = classifier.predict_from_telemetry(telemetry)
                
                state = result.get('state', 'UNKNOWN')
                conf = result.get('confidence', 0)
                category = result.get('category', 'unknown')
                cat_conf = result.get('category_confidence', 0)
                is_correct = (state == expected_states[scenario])
                
                if is_correct:
                    scenario_correct += 1
                
                # Print occasional details
                if i % 5 == 0 or i == scenario_total - 1:
                    status = "✅" if is_correct else "❌"
                    print(f"   {i+1:2d}. {status} {state:10} (conf: {conf:5.1f}%) - {category:8} (cat: {cat_conf:5.1f}%)")
                    
            except Exception as e:
                print(f"   {i+1:2d}. ❌ ERROR: {e}")
        
        accuracy = (scenario_correct / scenario_total) * 100
        results['by_scenario'][scenario] = {
            'correct': scenario_correct,
            'total': scenario_total,
            'accuracy': accuracy
        }
        results['total'] += scenario_total
        results['correct'] += scenario_correct
        
        print(f"\n   Accuracy: {accuracy:.1f}% ({scenario_correct}/{scenario_total})")
    
    # Summary
    print("\n" + "="*60)
    print("   📊 SUMMARY")
    print("="*60)
    
    for scenario, stats in results['by_scenario'].items():
        name = scenario_names.get(scenario, scenario)
        print(f"   {name:30} {stats['accuracy']:5.1f}% ({stats['correct']}/{stats['total']})")
    
    total_accuracy = (results['correct'] / results['total']) * 100
    print("-" * 40)
    print(f"   TOTAL ACCURACY: {total_accuracy:.1f}% ({results['correct']}/{results['total']})")
    
    print("\n" + "="*60)
    print("   ✅ EXTREME TEST COMPLETE!")
    print("="*60)
    
    # Also run the original test cases
    print("\n" + "="*60)
    print("   📋 ORIGINAL TEST CASES (For reference)")
    print("="*60)
    
    # Simple test cases
    simple_tests = [
        {
            'name': '🎮 CS2 - Active Match',
            'telemetry': {
                'resource_sync_score': 0.85,
                'gpu_drop_ratio': 0.05,
                'activity_drop_score': 10.0,
                'cpu_drop_ratio': 0.02,
                'gpu_delta_1s_pp': 5.0,
                'gpu_derivative_pp_s': 2.0,
                'gpu_delta_5s_pp': 3.0,
                'gpu_delta_3s_pp': 4.0,
                'stable_after_drop': 0,
                'cpu_variance_5s': 30.0,
                'fullscreen_changed': 0,
                'foreground_changed': 0,
                'window_seconds': 10,
                'ram_variance_5s': 200.0,
                'ram_growth_rate_mb_s': 5.0,
                'ram_delta_5s_mb': 10.0,
                'ram_delta_1s_mb': 5.0,
                'cpu_delta_5s_pp': 3.0,
                'cpu_delta_3s_pp': 4.0,
                'cpu_delta_1s_pp': 5.0
            }
        },
        {
            'name': '🎮 CS2 - Match Ended!',
            'telemetry': {
                'resource_sync_score': 0.75,
                'gpu_drop_ratio': 0.75,
                'activity_drop_score': 85.0,
                'cpu_drop_ratio': 0.45,
                'gpu_delta_1s_pp': -25.0,
                'gpu_derivative_pp_s': -28.0,
                'gpu_delta_5s_pp': -60.0,
                'gpu_delta_3s_pp': -45.0,
                'stable_after_drop': 1,
                'cpu_variance_5s': 150.0,
                'fullscreen_changed': 1,
                'foreground_changed': 0,
                'window_seconds': 5,
                'ram_variance_5s': 3000.0,
                'ram_growth_rate_mb_s': -50.0,
                'ram_delta_5s_mb': -80.0,
                'ram_delta_1s_mb': -40.0,
                'cpu_delta_5s_pp': -25.0,
                'cpu_delta_3s_pp': -20.0,
                'cpu_delta_1s_pp': -15.0
            }
        }
    ]
    
    print("\n")
    for test in simple_tests:
        result = classifier.predict_from_telemetry(test['telemetry'])
        state = result.get('state', 'UNKNOWN')
        conf = result.get('confidence', 0)
        category = result.get('category', 'unknown')
        print(f"{test['name']:30} → {state:10} ({conf:5.1f}%) - {category}")

if __name__ == '__main__':
    main()