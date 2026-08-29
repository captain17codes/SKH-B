import pytest
import numpy as np
from prioritization import run_prioritization
from allocation import knapsack_allocate
from explain import train_explanation_model, compute_shap_values, generate_nlg_message

def test_fuzzy_topsis_prioritization():
    # 3 Tickets: 
    # Ticket 1 (Emergency): High safety risk, high criticality, high cost.
    # Ticket 2 (Routine): Low safety risk, low criticality, low cost.
    # Ticket 3 (Equity): Moderate safety risk, high equity weight, low cost.
    # Criteria order: [infra_criticality, safety_risk, equity, resource_cost]
    tickets_data = [
        {'id': 't1', 'scores': [[0.7, 0.8, 0.9], [0.8, 0.9, 1.0], [0.1, 0.2, 0.3], [0.7, 0.8, 0.9]]}, # High cost (bad)
        {'id': 't2', 'scores': [[0.1, 0.2, 0.3], [0.1, 0.2, 0.3], [0.2, 0.3, 0.4], [0.1, 0.2, 0.3]]}, # Low cost (good)
        {'id': 't3', 'scores': [[0.3, 0.4, 0.5], [0.4, 0.5, 0.6], [0.8, 0.9, 1.0], [0.2, 0.3, 0.4]]}  # Mod cost
    ]
    
    criteria_config = {
        'types': ['benefit', 'benefit', 'benefit', 'cost'],
        # Weights: Safety and Infra are most important
        'weights': [
            [0.6, 0.8, 1.0], # infra
            [0.8, 0.9, 1.0], # safety
            [0.3, 0.5, 0.7], # equity
            [0.4, 0.6, 0.8]  # cost
        ]
    }
    
    results = run_prioritization(tickets_data, criteria_config)
    
    assert len(results) == 3
    # Check if t1 or t3 got prioritized over t2
    # Even though t1 has high cost, its safety and infra are so high it should score well,
    # or t3 might win because of low cost and high equity.
    scores = {res['id']: res['topsis_score'] for res in results}
    
    # All scores should be between 0 and 1
    assert all(0 <= score <= 1 for score in scores.values())
    
    # Check sorting
    assert results[0]['topsis_score'] >= results[1]['topsis_score']
    assert results[1]['topsis_score'] >= results[2]['topsis_score']

def test_knapsack_allocation():
    # Let's say we have 4 tickets
    tickets = [
        {'id': 't1', 'budget_cost': 500, 'workforce_hours': 10, 'topsis_score': 0.9},
        {'id': 't2', 'budget_cost': 200, 'workforce_hours': 5,  'topsis_score': 0.5},
        {'id': 't3', 'budget_cost': 300, 'workforce_hours': 4,  'topsis_score': 0.6},
        {'id': 't4', 'budget_cost': 800, 'workforce_hours': 12, 'topsis_score': 0.95}
    ]
    
    # Constraints that allow either (t1 + t2) or (t3 + t2) but NOT t4
    best_combination, best_score = knapsack_allocate(tickets, daily_budget=700, daily_workforce=15)
    
    # The optimal subset under budget=700, workforce=15:
    # t1 (500, 10, 0.9) + t2 (200, 5, 0.5) = (700, 15, 1.4)
    # t2 (200, 5, 0.5) + t3 (300, 4, 0.6) = (500, 9, 1.1)
    # t4 is too expensive (800 > 700)
    # Therefore, expected is t1 and t2
    
    assert set(best_combination) == {'t1', 't2'}
    assert np.isclose(best_score, 1.4)

def test_shap_explainability():
    # Mock data to train the explainer
    # Features: [infra, safety, equity, cost] (using crisp values for simplicity of model training)
    X = np.array([
        [0.8, 0.9, 0.2, 0.8],
        [0.2, 0.1, 0.3, 0.2],
        [0.4, 0.5, 0.9, 0.3],
        [0.9, 0.8, 0.1, 0.9]
    ])
    # Mock TOPSIS scores
    y = np.array([0.85, 0.20, 0.65, 0.80])
    
    model = train_explanation_model(X, y)
    
    # Generate SHAP for a high safety ticket
    ticket_features = np.array([[0.9, 0.95, 0.1, 0.7]])
    feature_names = ['infra_criticality', 'safety_risk', 'equity', 'resource_cost']
    
    shap_vals = compute_shap_values(model, ticket_features, feature_names)
    assert len(shap_vals) == 1
    
    sv = shap_vals[0]
    assert all(key in sv for key in feature_names)
    
    # Test NLG for scheduled
    sv_scheduled = {'infra_criticality': 0.1, 'safety_risk': 0.2, 'equity': 0.0, 'resource_cost': -0.01}
    msg = generate_nlg_message(sv_scheduled, 'Scheduled')
    assert "public safety" in msg
    
    # Test NLG for deferred due to cost
    sv_deferred = {'infra_criticality': 0.0, 'safety_risk': 0.0, 'equity': 0.0, 'resource_cost': -0.2}
    msg_def = generate_nlg_message(sv_deferred, 'Deferred')
    assert "resource requirements" in msg_def
