import shap
import numpy as np
from sklearn.ensemble import RandomForestRegressor

def train_explanation_model(feature_matrix, topsis_scores):
    """
    Trains a small regression model to map criteria scores to TOPSIS scores.
    feature_matrix: 2D array-like of shape (n_samples, n_features)
    topsis_scores: 1D array-like of shape (n_samples,)
    
    Returns: trained model
    """
    # Use a Random Forest as it generally captures non-linear TOPSIS interactions well
    # and works seamlessly with SHAP TreeExplainer.
    model = RandomForestRegressor(n_estimators=50, random_state=42)
    model.fit(feature_matrix, topsis_scores)
    return model

def compute_shap_values(model, ticket_features, feature_names):
    """
    Generates SHAP values for a specific ticket or multiple tickets.
    model: trained sklearn model
    ticket_features: 2D array-like of shape (1, n_features) or (n_samples, n_features)
    feature_names: list of strings
    
    Returns: list of dicts mapping feature names to their SHAP values
    """
    explainer = shap.TreeExplainer(model)
    shap_values = explainer.shap_values(ticket_features)
    
    # If single ticket was passed, wrap it to handle uniformly
    if len(np.shape(shap_values)) == 1:
        shap_values = [shap_values]
        
    results = []
    for sv in shap_values:
        sv_dict = {name: val for name, val in zip(feature_names, sv)}
        results.append(sv_dict)
        
    return results

def generate_nlg_message(shap_values_dict, ticket_status):
    """
    Generates a human-readable explanation based on SHAP values.
    shap_values_dict: dict mapping feature names to their SHAP values, 
                      e.g., {'infra_criticality': 0.1, 'safety_risk': 0.2, 'equity': 0.0, 'resource_cost': -0.1}
    ticket_status: string, either 'Scheduled' or 'Deferred'
    """
    # Identify the strongest positive and negative contributors
    sorted_features = sorted(shap_values_dict.items(), key=lambda x: x[1], reverse=True)
    top_positive = [f for f, v in sorted_features if v > 0.05]
    top_negative = [f for f, v in sorted_features if v < -0.05]
    
    if ticket_status == 'Scheduled':
        if 'safety_risk' in top_positive or 'infra_criticality' in top_positive:
            return "Your request has been prioritized for immediate action due to high risks to public safety and critical infrastructure. Teams are deployed."
        elif 'equity' in top_positive:
            return "Your request has been approved. We are actively prioritizing service balancing in your ward to ensure equal civic maintenance."
        else:
            return "Your request has been prioritized and scheduled for today's dispatch based on standard municipal evaluation."
            
    elif ticket_status == 'Deferred':
        if 'resource_cost' in top_negative:
            return "Your request is verified. Due to high resource requirements, it has been scheduled for the next budget cycle window."
        elif 'safety_risk' in top_negative:
            # Meaning it didn't score high enough on safety
            return "Your request is logged. Emergency teams are currently deployed to higher public health risks, your issue is deferred to the next available window."
        else:
            return "Your request is logged. Due to current municipal capacity constraints, it is deferred but remains in our active queue."
            
    return "Status update unavailable."
