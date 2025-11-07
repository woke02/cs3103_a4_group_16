import json
import os
import matplotlib.pyplot as plt
import numpy as np

# Define the results directory and graphs directory
RESULTS_DIR = "./results"
GRAPHS_DIR = "./graphs"

# Create graphs directory if it doesn't exist
os.makedirs(GRAPHS_DIR, exist_ok=True)

def load_results():
    """Load all test case results from JSON files."""
    results = {
        'reliable': {},
        'unreliable': {}
    }
    
    for i in range(1, 9):  # Test cases 1 to 8
        # Load reliable results
        reliable_file = os.path.join(RESULTS_DIR, f"tc{i}_reliable.json")
        if os.path.exists(reliable_file):
            with open(reliable_file, 'r') as f:
                results['reliable'][i] = json.load(f)
        
        # Load unreliable results
        unreliable_file = os.path.join(RESULTS_DIR, f"tc{i}_unreliable.json")
        if os.path.exists(unreliable_file):
            with open(unreliable_file, 'r') as f:
                results['unreliable'][i] = json.load(f)
    
    return results

def plot_all_metrics_grid(results, test_case_range, filename_suffix):
    """Create a 2x2 grid showing all four metrics for a specific range of test cases."""
    all_test_cases = sorted(results['reliable'].keys())
    test_cases = [tc for tc in all_test_cases if tc in test_case_range]
    
    metrics = [
        ('overall_delivery_ratio', 'Delivery Ratio (%)', 'Packet Delivery Ratio'),
        ('average_latency_ms', 'Latency (ms)', 'Average Latency'),
        ('jitter_ms', 'Jitter (ms)', 'Jitter'),
        ('throughput', 'Throughput (byte/s)', 'Throughput')
    ]
    
    fig, axes = plt.subplots(2, 2, figsize=(16, 9))
    
    for idx, (metric_key, ylabel, title) in enumerate(metrics):
        ax = axes[idx // 2, idx % 2]
        
        reliable_values = [int(results['reliable'][tc].get(metric_key, 0)) if metric_key == 'throughput' else results['reliable'][tc].get(metric_key, 0) for tc in test_cases]
        unreliable_values = [int(results['unreliable'][tc].get(metric_key, 0)) if metric_key == 'throughput' else results['unreliable'][tc].get(metric_key, 0) for tc in test_cases]
        
        x = np.arange(len(test_cases))
        width = 0.35
        
        bars1 = ax.bar(x - width/2, reliable_values, width, label='Reliable', 
                       alpha=0.8, color='#2E86AB')
        bars2 = ax.bar(x + width/2, unreliable_values, width, label='Unreliable', 
                       alpha=0.8, color='#A23B72')
        
        ax.set_ylabel(ylabel, fontsize=16, fontweight='bold')
        ax.set_title(title, fontsize=16, fontweight='bold', pad=10)
        ax.set_xticks(x)
        ax.set_xticklabels([f'TC{tc}' for tc in test_cases])
        ax.legend(fontsize=14)
        ax.grid(axis='y', alpha=0.3, linestyle='--')
        
        # Add value labels on bars for better readability
        for bars in [bars1, bars2]:
            for bar in bars:
                height = bar.get_height()
                if height > 0:
                    ax.text(bar.get_x() + bar.get_width()/2., height,
                           f'{height:.0f}' if metric_key == 'throughput' else f'{height:.1f}',
                           ha='center', va='bottom', fontsize=12)
    
    plt.tight_layout()
    output_filename = f'all_metrics_comparison_{filename_suffix}.png'
    plt.savefig(os.path.join(GRAPHS_DIR, output_filename), 
                dpi=300, bbox_inches='tight')
    plt.close()
    print(f"Saved: {output_filename}")

def main():
    print("Loading test results...")
    results = load_results()
    
    print(f"\nFound {len(results['reliable'])} reliable test cases")
    print(f"Found {len(results['unreliable'])} unreliable test cases")
    
    print("\nGenerating graphs...")
    
    plot_all_metrics_grid(results, range(1, 6), 'tc1-tc5')
    
    plot_all_metrics_grid(results, range(6, 9), 'tc6-tc8')
    
if __name__ == "__main__":
    main()
